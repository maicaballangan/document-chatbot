import json
import logging
import uuid
from collections.abc import Generator

from fastapi import BackgroundTasks
from llama_index.core import VectorStoreIndex
from llama_index.core.agent.react.base import ReActAgent
from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.objects import ObjectIndex

from .llm_config import llm_config
from .utils import format_dict_output_commercial
from .utils import format_dict_output_residential
from .utils import format_json_output
from .utils import get_source_info
from .utils import load_engines
from .utils import load_tools
from app.core.enums import ChatRole
from app.core.enums import ProductType
from app.jobs.background_tasks import save_chat
from app.legalai.prompts.general_prompts import (
    NORMAL_STREAM_RESPONSE,
)
from app.legalai.prompts.policy_prompt import IDEALIZED_POLICY_PROMPT_COMMERCIAL
from app.legalai.prompts.policy_prompt import IDEALIZED_POLICY_PROMPT_RESIDENTIAL
from app.legalai.prompts.policy_prompt import POLICY_STREAM_RESPONSE
from app.legalai.prompts.policy_prompt import POLICY_TYPE_PROMPT
from app.legalai.prompts.policy_prompt import REPORT_CARD_PROMPT
from app.models.chat import Chat
from app.models.chat import ChatAgentCreateInput

# Get a logger instance for this module
logger = logging.getLogger(__name__)

SIMILARITY_TOP_K = 10


class NewAI:
    """Main AI class handling LLM interactions, chat responses, and policy analysis."""

    def _create_agent(self, tools_list: list, chat_history: list[Chat], system_prompt: str) -> ReActAgent:
        """
        Create and configure a ReActAgent with the given tools, chat history, and system prompt.

        Parameters:
            tools_list: A list of tool objects that the agent can use
            chat_history: A list of previous chat messages with content and role
            system_prompt: Instructions or context for the agent's behavior

        Returns:
            A configured ReActAgent ready to process queries
        """
        # Create object index and retriever for tools
        obj_index = ObjectIndex.from_objects(tools_list, index_cls=VectorStoreIndex)
        obj_retriever = obj_index.as_retriever(similarity_top_k=SIMILARITY_TOP_K)

        # Convert chat history to the required format
        formatted_messages = [ChatMessage(content=item.content, role=item.role.value) for item in chat_history]

        # Create the chat formatter with system instructions
        react_chat_formatter = ReActChatFormatter.from_context(system_prompt)

        # Create and return the agent
        return ReActAgent.from_tools(
            llm=llm_config.get_llm(),
            tool_retriever=obj_retriever,
            react_chat_formatter=react_chat_formatter,
            chat_history=formatted_messages,
            max_iterations=1000,
            verbose=True,
        )

    def chat_stream_response(
        self,
        documents_json: dict,
        latest_user_new_chat: str,
        chat_history: list[Chat],
        session_id: uuid.UUID,
        response_to: uuid.UUID,
        product: ProductType,
        bg_tasks: BackgroundTasks,
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response for user chat queries.

        Parameters:
            documents_json: Dictionary containing document information
            latest_user_new_chat: The latest message from the user
            chat_history: List of previous chat messages
            session_id: Unique session identifier
            response_to: ID of the message being responded to
            product: Type of product (POLICY or GENERAL)
            bg_tasks: Background tasks object for asynchronous operations

        Yields:
            Streaming response data
        """
        logger.info(f'Starting chat stream response for session {session_id}')

        # Signal stream start
        yield f'event: stream-start\ndata: {json.dumps({"chat_stream_ref_id": str(session_id)})}\n\n'

        # Load tools for each document
        tools = []
        for document in documents_json:
            tool = load_tools(document['summary_id'], document['vector_id'], product)
            tools.extend(tool)

        # Select the appropriate system prompt based on product type
        match product:
            case ProductType.POLICY:
                system_prompt = POLICY_STREAM_RESPONSE
            case ProductType.GENERAL:
                system_prompt = NORMAL_STREAM_RESPONSE

        logger.debug('Creating agent with system prompt and tools')
        try:
            # Create the agent
            agent = self._create_agent(tools, chat_history, system_prompt)

            # Process the user query
            query_string = latest_user_new_chat
            logger.info(f'Processing query: {query_string[:50]}...')

            # Get the response
            response = agent.chat(query_string)
            response.is_dummy_stream = True

            # Stream the tokens to the client
            for token in response.response_gen:
                yield f"data: {json.dumps({'text': token})}\n\n"

            # Extract source information from the response
            source_info = get_source_info(response.source_nodes)

            # Create chat record
            chat = ChatAgentCreateInput(
                session_id=session_id,
                content=response.response,
                response_to=response_to,
                role=ChatRole.ASSISTANT,
                source_info=json.dumps(source_info),
            )

            # Save chat in background
            bg_tasks.add_task(save_chat, chat)

            # Signal stream end with chat data
            yield f'event: stream-end\ndata: {chat.model_dump_json()}\n\n'

        except Exception as e:
            logger.error(f'Error in chat_stream_response: {e!s}', exc_info=True)
            raise

    def summary_the_policy(self, document_id: str, summary_id: str, vector_id: str) -> tuple[str, list[dict], dict]:
        """
        Generate summary for a policy document.

        Parameters:
            document_id: ID of the document
            summary_id: ID for summary index
            vector_id: ID for vector index

        Returns:
            Tuple containing policy type, summary dictionary, and report card dictionary
        """
        logger.info(f'Starting policy summary generation for document_id: {document_id}')

        try:
            # Generate query engines
            logger.debug('Generating query engines')
            summary_query_engine, vector_query_engine = load_engines(summary_id, vector_id, None)

            # Determine policy type
            response1 = vector_query_engine.query(POLICY_TYPE_PROMPT)
            logger.debug(f'Policy type response: {response1.response[:100]}...')
            policy_type_response = format_json_output(response=response1.response)

            # Process based on policy type
            if (
                policy_type_response
                and 'commercial' in policy_type_response
                and policy_type_response['commercial'] is True
            ):
                # Handle commercial policy
                policy_type = 'commercial'
                logger.info('Processing as commercial policy')
                response2 = vector_query_engine.query(IDEALIZED_POLICY_PROMPT_COMMERCIAL)
                logger.debug(f'Commercial policy response: {response2.response[:100]}...')
                output_dict = format_json_output(response2.response)
                summary_dict = format_dict_output_commercial(output_dict)
            else:
                # Handle residential policy
                policy_type = 'residential'
                logger.info('Processing as residential policy')
                response3 = vector_query_engine.query(IDEALIZED_POLICY_PROMPT_RESIDENTIAL)
                logger.debug(f'Residential policy response: {response3.response[:100]}...')
                output_dict = format_json_output(response3.response)
                summary_dict = format_dict_output_residential(output_dict)

            # Generate report card
            response4 = summary_query_engine.query(REPORT_CARD_PROMPT)
            logger.debug(f'Report card response: {response4.response[:100]}...')
            report_card_dict = format_json_output(response=response4.response)

            logger.info(f'Successfully generated policy summary for document_id: {document_id}')
            return policy_type, summary_dict, report_card_dict

        except Exception as e:
            logger.error(f'Error in summary_the_policy: {e!s}', exc_info=True)
            raise
