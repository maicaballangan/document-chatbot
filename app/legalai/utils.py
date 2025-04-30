import json
import logging
import re

import redis
from llama_index.core import ChatPromptTemplate
from llama_index.core import load_index_from_storage
from llama_index.core import StorageContext
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.llms import MessageRole
from llama_index.core.postprocessor import LLMRerank
from llama_index.core.prompts.base import PromptTemplate
from llama_index.core.prompts.prompt_type import PromptType
from llama_index.core.schema import NodeWithScore
from llama_index.core.tools import QueryEngineTool
from llama_index.storage.docstore.redis import RedisDocumentStore
from llama_index.storage.index_store.redis import RedisIndexStore
from llama_index.storage.kvstore.redis import RedisKVStore
from llama_index.vector_stores.redis import RedisVectorStore

from .prompts.general_prompts import GENERAL_FILES_PROMPT
from .prompts.general_prompts import QA_PROMPT_STR
from .prompts.general_prompts import RERANK_PROMPT
from .prompts.policy_prompt import POLICY_GENERAL_PROMPT
from app.core.config import settings
from app.core.enums import ProductType
from app.legalai.llm_config import document_schema

# Configure logger
logger = logging.getLogger(__name__)

# Redis connection setup
REDIS_CLIENT = redis.Redis.from_url(settings.REDIS_URL)
REDIS_KV_STORE = RedisKVStore.from_redis_client(REDIS_CLIENT)


def load_engines(
    summary_id: str, vector_id: str, product: ProductType | None
) -> tuple[QueryEngineTool, QueryEngineTool]:
    """
    Load query engines for document interaction.

    Parameters:
        summary_id: ID for the summary index
        vector_id: ID for the vector index
        product: Type of product (POLICY or GENERAL)

    Returns:
        Tuple containing summary and vector query engines
    """
    if not summary_id or not vector_id:
        logger.error('Summary ID and Vector ID must be provided.')
        raise ValueError('Summary ID and Vector ID cannot be empty.')

    # Setup storage contexts
    SUMMARY_STORAGE_CONTEXT = StorageContext.from_defaults(
        docstore=RedisDocumentStore(redis_kvstore=REDIS_KV_STORE, namespace='document_summary'),
        index_store=RedisIndexStore(redis_kvstore=REDIS_KV_STORE, namespace='document_summary'),
    )

    VECTOR_STORAGE_CONTEXT = StorageContext.from_defaults(
        docstore=RedisDocumentStore(redis_kvstore=REDIS_KV_STORE, namespace='document_vector'),
        index_store=RedisIndexStore(redis_kvstore=REDIS_KV_STORE, namespace='document_vector'),
        vector_store=RedisVectorStore(redis_client=REDIS_CLIENT, index_schema=document_schema),
    )

    # Load indices from storage
    summary_index = load_index_from_storage(storage_context=SUMMARY_STORAGE_CONTEXT, index_id=summary_id)
    vector_index = load_index_from_storage(storage_context=VECTOR_STORAGE_CONTEXT, index_id=vector_id)

    # Configure reranker for better results
    re_rank = LLMRerank(
        choice_batch_size=5,
        top_n=3,
        choice_select_prompt=PromptTemplate(RERANK_PROMPT, prompt_type=PromptType.CHOICE_SELECT),
        parse_choice_select_answer_fn=default_parse_choice_select_answer_fn,
    )

    match product:
        case ProductType.POLICY:
            system_prompt = POLICY_GENERAL_PROMPT
        case ProductType.GENERAL:
            system_prompt = GENERAL_FILES_PROMPT

    # Configure vector query engine
    if product is None:
        vector_query_engine = vector_index.as_query_engine(similarity_top_k=10)
    else:
        # Set up chat template for better context
        chat_text_qa_msgs = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=system_prompt,
            ),
            ChatMessage(role=MessageRole.USER, content=QA_PROMPT_STR),
        ]
        text_qa_template = ChatPromptTemplate(chat_text_qa_msgs)

        # Create vector query engine with advanced settings
        vector_query_engine = vector_index.as_query_engine(
            similarity_top_k=10, node_postprocessors=[re_rank], chat_text_qa_msgs=text_qa_template
        )

    # Configure summary query engine
    summary_query_engine = summary_index.as_query_engine(response_mode='tree_summarize', use_async=True)

    return summary_query_engine, vector_query_engine


def load_tools(summary_id: str, vector_id: str, product: ProductType) -> list[QueryEngineTool]:
    """
    Load tools for use with the agent.

    Parameters:
        summary_id: ID for the summary index
        vector_id: ID for the vector index
        product: Type of product

    Returns:
        List containing summary and vector tools
    """
    # Load the query engines
    summary_query_engine, vector_query_engine = load_engines(summary_id, vector_id, product)

    # Create the tools with appropriate descriptions
    vector_tool = QueryEngineTool.from_defaults(
        query_engine=vector_query_engine,
        description='Useful for retrieving specific context from the document.',
    )

    summary_tool = QueryEngineTool.from_defaults(
        query_engine=summary_query_engine,
        description='Useful for summarization questions related to the document.',
    )

    return [summary_tool, vector_tool]


def default_parse_choice_select_answer_fn(
    answer: str, num_choices: int, raise_error: bool = False
) -> tuple[list[int], list[float]]:
    """
    Parse choice selection answers from LLM response.

    Parameters:
        answer: The raw answer string to parse
        num_choices: The number of choices available
        raise_error: Whether to raise errors on invalid input

    Returns:
        Tuple containing lists of answer numbers and relevance scores
    """
    answer_lines = answer.split('\n')
    answer_nums = []
    answer_relevances = []

    for answer_line in answer_lines:
        line_tokens = answer_line.split(',')
        if len(line_tokens) != 2:
            if raise_error:
                logger.error(f'Invalid answer line: {answer_line}')
                raise ValueError(
                    f'Invalid answer line: {answer_line}. '
                    'Answer line must be of the form: '
                    'answer_num: <int>, answer_relevance: <float>'
                )
            continue

        try:
            # Extract answer number
            answer_num = int(line_tokens[0].split(':')[1].strip())
            if answer_num > num_choices:
                logger.warning(f'Answer number {answer_num} exceeds number of choices {num_choices}.')
                continue

            answer_nums.append(answer_num)

            # Extract relevance score (just the first digits after the colon)
            _answer_relevance = re.findall(r'\d+', line_tokens[1].split(':')[1].strip())[0]
            answer_relevances.append(float(_answer_relevance))
        except ValueError:
            logger.exception('Error parsing choice answer')
            if raise_error:
                raise

    return answer_nums, answer_relevances


def sanitize_function_name(name: str) -> str:
    """
    Sanitize a string for use as a function name or identifier.

    Parameters:
        name: The string to sanitize

    Returns:
        Sanitized string safe for use as an identifier
    """
    sanitized_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    max_length = 56
    return sanitized_name[:max_length]


def format_json_output_list_string(response: str) -> list | None:
    """
    Extract and parse a JSON list from a string response.

    Parameters:
        response: String potentially containing JSON list

    Returns:
        Parsed JSON list or None if not found/invalid
    """
    # Try to find JSON list in code block
    json_part_match = re.search(r'```json\n(\[.*?\])\n```', response, re.DOTALL)

    if json_part_match:
        json_part = json_part_match.group(1)
        try:
            return json.loads(json_part)
        except json.JSONDecodeError:
            logger.exception('Failed to parse JSON list from response')
            return None

    return None


def format_json_output(response: str) -> dict | None:
    """
    Extract and parse JSON from a string response with various formatting.

    Parameters:
        response: String potentially containing JSON

    Returns:
        Parsed JSON object or None if not found/invalid
    """
    # Replace single quotes with double quotes for valid JSON (avoiding contractions)
    response = re.sub(r"(?<=[:\[{,])\s*'([^']*?)'\s*(?=[:,\]}])", r'"\1"', response)

    # Try to find JSON inside a code block
    json_part_match = re.search(r'```json\n([\[\{\s\S]*?[\]\}])\n```', response, re.DOTALL)

    if json_part_match:
        logger.debug('Found JSON inside code block')
        json_part = json_part_match.group(1)
    else:
        logger.debug('No code block JSON, checking for raw JSON')
        # Look for raw JSON structures
        json_part_match_normal = re.search(r'([\[\{\s\S]*[\]\}])', response, re.DOTALL)

        if json_part_match_normal:
            logger.debug('Found raw JSON in response')
            json_part = json_part_match_normal.group(1).strip()
        else:
            logger.debug('No JSON found in response')
            logger.debug(response)
            return None

    # Try to parse the found JSON
    try:
        return json.loads(json_part)
    except json.JSONDecodeError:
        logger.exception('Error decoding JSON')
        logger.debug(f'Problematic JSON string:\n{json_part}')
        return None


def format_dict_output(output_dict: dict, sections: list[str], section_names: list[str]) -> list[dict]:
    """
    Format policy data into a structured list.

    Parameters:
        output_dict: Raw policy data dictionary
        sections: List of section keys
        section_names: List of section names

    Returns:
        Formatted list of policy sections
    """
    new_dict = {sections[i]: output_dict.get(sections[i], []) for i in range(len(sections))}
    output_list = []
    for i, (key, val) in enumerate(new_dict.items()):
        if i >= len(section_names):
            continue
        content = [f'{k}: {v}' for k, v in val.items()] if isinstance(val, dict) else [val]
        content = [str(u).replace('{', '').replace('}', '') for u in content]
        output_list.append({'code': key, 'headline': section_names[i], 'content': ['; '.join(content)]})
    return output_list


def format_dict_output_commercial(output_dict: dict) -> list[dict]:
    sections = [
        'coverage_of_buildings',
        'water_damage_sub-limits',
        'mitigation_limit_of_liability',
        'cosmetic_damage',
        'hail_and_wind_damage',
        'roof_deprecation_schedule',
        'replacement_cost_value',
    ]
    section_names = [
        'Coverage of buildings',
        'Water damage sub-limits',
        'Mitigation - Limit of Liability',
        'Cosmetic damage',
        'Hail or Wind Exclusions or Limitations',
        'Roof deprecation schedule',
        'RCV/ACV',
    ]
    return format_dict_output(output_dict, sections, section_names)


def format_dict_output_residential(output_dict: dict) -> list[dict]:
    sections = [
        'property_coverages',
        'water_damage_sub-limits',
        'mitigation_limit_of_liability',
        'mold_sub-limits',
        'hail_and_wind_damage',
        'roof_deprecation_schedule',
        'matching_limitations',
        'replacement_cost_value',
    ]
    section_names = [
        'Property coverages',
        'Water damage sub-limits',
        'Mitigation - Limit of Liability',
        'Mold sub-limits',
        'Hail or Wind Exclusions or Limitations',
        'Roof deprecation schedule',
        'Matching limitations',
        'RCV/ACV',
    ]
    return format_dict_output(output_dict, sections, section_names)


def get_source_info(self, nodes: list[NodeWithScore]) -> dict:
    """
    Extract source information from nodes.

    Parameters:
        nodes: List of nodes with relevance scores

    Returns:
        Dictionary containing source information
    """
    # Get the highest-scoring node if available
    source_node = None if not nodes else nodes[0]

    if source_node is not None:
        page_number = source_node.metadata.get('page')
        page_content = source_node.text
        document_name = source_node.metadata.get('document_name')
    else:
        page_number = None
        page_content = None
        document_name = None

    # Format the source information
    source_info = (
        {
            'page_number': page_number,
            'page_content': page_content,
            'document_name': document_name,
        },
    )
    return source_info
