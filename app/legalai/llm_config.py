import random

from llama_index.core import Settings
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.gemini import Gemini
from llama_index.llms.openai import OpenAI
from redisvl.schema import IndexSchema

from app.core.config import settings


class LLMConfig:
    def __init__(self):
        keys_string = settings.OPENAI_API_KEY
        self.key_list = keys_string.split('###')

    def random_key(self):
        selected_key = random.choice(self.key_list)  # noqa
        return selected_key

    def get_embedding(self):
        EMBEDDING_MODEL = {
            'openai': OpenAIEmbedding(
                model=settings.OPENAI_EMBEDDING_MODEL,
                api_key=settings.OPENAI_API_KEY,
            ),
            'google': GeminiEmbedding(model=settings.GOOGLE_EMBEDDING_MODEL, api_key=settings.GOOGLE_API_KEY),
        }

        return EMBEDDING_MODEL.get('openai')

    def get_llm(self):
        # Configure the language model (LLM)
        GEMINI = Gemini(
            model=settings.GOOGLE_LLM,
            api_key=settings.GOOGLE_API_KEY,
            max_tokens=2000,
        )

        OPENAI = OpenAI(
            model=settings.OPENAI_LLM,
            api_key=settings.OPENAI_API_KEY,
            max_tokens=2000,
        )

        LLM_RUNNING = {
            'google': GEMINI,
            'openai': OPENAI,
        }

        return LLM_RUNNING.get(settings.SELECTED_LLM, LLM_RUNNING['openai'])


llm_config = LLMConfig()

Settings.llm = llm_config.get_llm()
Settings.embed_model = llm_config.get_embedding()


document_schema = IndexSchema.from_dict({
    # customize basic index specs
    'index': {
        'name': 'document',
        'prefix': 'document',
        'key_separator': ':',
    },
    # customize fields that are indexed
    'fields': [
        # required fields for llamaindex
        {'type': 'tag', 'name': 'id'},
        {'type': 'tag', 'name': 'doc_id'},
        {'type': 'text', 'name': 'text'},
        # custom metadata fields
        {'type': 'numeric', 'name': 'page'},
        {'type': 'tag', 'name': 'document_name'},
        # custom vector field definition for embeddings
        {
            'type': 'vector',
            'name': 'vector',
            'attrs': {
                'dims': 1536,
                'algorithm': 'hnsw',
                'distance_metric': 'cosine',
            },
        },
    ],
})
