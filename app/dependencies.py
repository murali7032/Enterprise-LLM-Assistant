from functools import lru_cache

from app.agents.agent_service import AgentService
from app.agents.executor import Executor
from app.agents.planner import Planner
from app.agents.tool_router import ToolRouter
from app.cache.redis_cache import RedisSemanticCache
from app.clients.anthropic_client import AnthropicClient
from app.clients.azure_openai_client import AzureOpenAIClient
from app.clients.gemini_client import GeminiClient
from app.clients.ollama_client import OllamaClient
from app.clients.openai_client import OpenAIClient
from app.clients.qdrant_client import QdrantClientWrapper
from app.clients.redis_client import RedisClient
from app.clients.embedding_client import create_embedding_client
from app.core.config import settings
from app.core.exceptions import LLMProviderException
from app.memory.conversation_memory import ConversationMemory
from app.parser.output_parser import OutputParser
from app.prompt.prompt_builder import PromptBuilder
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.azure_openai_provider import AzureOpenAIProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.llm_provider import LLMProvider
from app.providers.ollama_provider import OllamaProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.registry import ProviderRegistry
from app.repositories.document_repository import DocumentRepository
from app.retrieval.retriever import HybridSearch, Reranker, Retriever
from app.security.guardrails import PromptGuardrails
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService
from app.services.llm_service import LLMService
from app.tools.kubernetes_tool import KubernetesTool
from app.tools.shell_tool import ShellTool
from app.tools.sql_tool import SQLTool
from app.tools.weather_tool import WeatherTool


@lru_cache
def get_openai_client() -> OpenAIClient:
    return OpenAIClient()


@lru_cache
def get_gemini_client() -> GeminiClient:
    return GeminiClient()


@lru_cache
def get_anthropic_client() -> AnthropicClient:
    return AnthropicClient()


@lru_cache
def get_ollama_client() -> OllamaClient:
    return OllamaClient()


@lru_cache
def get_azure_openai_client() -> AzureOpenAIClient:
    return AzureOpenAIClient()


@lru_cache
def get_redis_client() -> RedisClient:
    return RedisClient()


@lru_cache
def get_qdrant_client() -> QdrantClientWrapper:
    return QdrantClientWrapper()


@lru_cache
def get_document_repository() -> DocumentRepository:
    return DocumentRepository()


@lru_cache
def get_provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register("openai", lambda: OpenAIProvider(client=get_openai_client()))
    registry.register("gemini", lambda: GeminiProvider(client=get_gemini_client()))
    registry.register("anthropic", lambda: AnthropicProvider(client=get_anthropic_client()))
    registry.register("ollama", lambda: OllamaProvider(client=get_ollama_client()))
    registry.register("azure_openai", lambda: AzureOpenAIProvider(client=get_azure_openai_client()))
    return registry


def get_llm_provider() -> LLMProvider:
    return get_provider_registry().create(settings.LLM_PROVIDER)


@lru_cache
def get_semantic_cache() -> RedisSemanticCache:
    return RedisSemanticCache(redis_client=get_redis_client())


def get_llm_service() -> LLMService:
    return LLMService(provider=get_llm_provider(), cache=get_semantic_cache())


@lru_cache
def get_prompt_builder() -> PromptBuilder:
    return PromptBuilder()


@lru_cache
def get_output_parser() -> OutputParser:
    return OutputParser()


@lru_cache
def get_guardrails() -> PromptGuardrails:
    return PromptGuardrails()


@lru_cache
def get_retriever() -> Retriever:
    return Retriever(
        qdrant_client=get_qdrant_client(),
        hybrid_search=HybridSearch(),
        reranker=Reranker(HybridSearch()),
    )


@lru_cache
def get_conversation_memory() -> ConversationMemory:
    return ConversationMemory()


def get_embedding_client():
    return create_embedding_client(
        openai_client=get_openai_client(),
        gemini_client=get_gemini_client(),
    )


def get_chat_service() -> ChatService:
    return ChatService(
        llm_service=get_llm_service(),
        prompt_builder=get_prompt_builder(),
        output_parser=get_output_parser(),
        guardrails=get_guardrails(),
        retriever=get_retriever(),
        embedding_client=get_embedding_client(),
        memory=get_conversation_memory(),
    )


def get_ingestion_service() -> IngestionService:
    return IngestionService(
        embedding_client=get_embedding_client(),
        qdrant_client=get_qdrant_client(),
        document_repository=get_document_repository(),
    )


def get_document_service() -> DocumentService:
    return DocumentService(
        embedding_client=get_embedding_client(),
        retriever=get_retriever(),
        qdrant_client=get_qdrant_client(),
        document_repository=get_document_repository(),
    )


@lru_cache
def get_tool_router() -> ToolRouter:
    return ToolRouter(
        tools=[
            WeatherTool(),
            SQLTool(),
            KubernetesTool(),
            ShellTool(),
        ]
    )


def get_agent_service() -> AgentService:
    return AgentService(
        planner=Planner(
            llm_service=get_llm_service(),
            prompt_builder=get_prompt_builder(),
            output_parser=get_output_parser(),
        ),
        executor=Executor(tool_router=get_tool_router()),
        tool_router=get_tool_router(),
    )


def validate_provider_configuration() -> None:
    """Fail fast when provider credentials are missing."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "ollama":
        return
    required_keys = {
        "openai": settings.OPENAI_API_KEY,
        "gemini": settings.GEMINI_API_KEY,
        "anthropic": settings.ANTHROPIC_API_KEY,
        "azure_openai": settings.AZURE_OPENAI_API_KEY,
    }
    if provider in required_keys and not required_keys[provider]:
        raise LLMProviderException(f"Missing API key for provider '{provider}'")
