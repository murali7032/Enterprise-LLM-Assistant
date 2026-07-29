from collections.abc import AsyncGenerator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agent_service import AgentService
from app.agents.executor import Executor
from app.agents.planner import Planner
from app.agents.tool_router import ToolRouter
from app.cache.redis_cache import RedisSemanticCache
from app.clients.anthropic_client import AnthropicClient
from app.clients.azure_openai_client import AzureOpenAIClient
from app.clients.embedding_client import create_embedding_client
from app.clients.gemini_client import GeminiClient
from app.clients.ollama_client import OllamaClient
from app.clients.openai_client import OpenAIClient
from app.clients.qdrant_client import QdrantClientWrapper
from app.clients.redis_client import RedisClient
from app.core.config import settings
from app.core.exceptions import LLMProviderException
from app.db.database import async_session_factory
from app.memory.conversation_memory import InMemoryConversationMemory
from app.memory.memory_store import ConversationMemoryStore
from app.memory.postgres_conversation_memory import PostgresConversationMemory
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
from app.repositories.in_memory_document_repository import InMemoryDocumentRepository
from app.repositories.postgres_document_repository import PostgresDocumentRepository
from app.repositories.user_repository import (
    InMemoryUserRepository,
    PostgresUserRepository,
    UserRepository,
)
from app.retrieval.retriever import HybridSearch, Reranker, Retriever
from app.security.auth_limits import AuthRateLimiter, LoginLockoutStore
from app.security.guardrails import PromptGuardrails
from app.security.oauth_providers import (
    OAuthProviderRegistry,
    build_default_oauth_registry,
)
from app.security.sessions import InMemorySessionStore, RedisSessionStore, SessionStore
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService
from app.services.llm_service import LLMService
from app.tools.kubernetes_tool import KubernetesTool
from app.tools.k8s_playbook_tool import K8sPlaybookTool
from app.tools.shell_tool import ShellTool
from app.tools.sql_tool import SQLTool
from app.tools.weather_tool import WeatherTool
from app.clients.kubernetes_client import KubernetesClient
from app.repositories.finding_repository import ApprovalStore, FindingStore
from app.services.ops_diagnosis_service import OpsDiagnosisService
from app.services.ops_notifier import OpsNotifier


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
def get_in_memory_document_repository() -> InMemoryDocumentRepository:
    return InMemoryDocumentRepository()


@lru_cache
def get_in_memory_conversation_memory() -> InMemoryConversationMemory:
    return InMemoryConversationMemory()


async def get_db_session() -> AsyncGenerator[AsyncSession | None, None]:
    """Provide a PostgreSQL session per request when enabled."""
    if not settings.USE_POSTGRES:
        yield None
        return
    async with async_session_factory() as session:
        yield session


async def get_document_repository(
    session: AsyncSession | None = Depends(get_db_session),
) -> DocumentRepository:
    """Resolve the document repository implementation."""
    if settings.USE_POSTGRES:
        assert session is not None
        return PostgresDocumentRepository(session=session)
    return get_in_memory_document_repository()


async def get_conversation_memory(
    session: AsyncSession | None = Depends(get_db_session),
) -> ConversationMemoryStore:
    """Resolve the conversation memory implementation."""
    if settings.USE_POSTGRES:
        assert session is not None
        return PostgresConversationMemory(session=session)
    return get_in_memory_conversation_memory()


@lru_cache
def get_provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register("openai", lambda: OpenAIProvider(client=get_openai_client()))
    registry.register("gemini", lambda: GeminiProvider(client=get_gemini_client()))
    registry.register(
        "anthropic", lambda: AnthropicProvider(client=get_anthropic_client())
    )
    registry.register("ollama", lambda: OllamaProvider(client=get_ollama_client()))
    registry.register(
        "azure_openai", lambda: AzureOpenAIProvider(client=get_azure_openai_client())
    )
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


def get_embedding_client():
    return create_embedding_client(
        openai_client=get_openai_client(),
        gemini_client=get_gemini_client(),
    )


def get_chat_service(
    memory: ConversationMemoryStore = Depends(get_conversation_memory),
) -> ChatService:
    return ChatService(
        llm_service=get_llm_service(),
        prompt_builder=get_prompt_builder(),
        output_parser=get_output_parser(),
        guardrails=get_guardrails(),
        retriever=get_retriever(),
        embedding_client=get_embedding_client(),
        memory=memory,
    )


def get_ingestion_service(
    document_repository: DocumentRepository = Depends(get_document_repository),
) -> IngestionService:
    return IngestionService(
        embedding_client=get_embedding_client(),
        qdrant_client=get_qdrant_client(),
        document_repository=document_repository,
    )


def get_document_service(
    document_repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentService:
    return DocumentService(
        embedding_client=get_embedding_client(),
        retriever=get_retriever(),
        qdrant_client=get_qdrant_client(),
        document_repository=document_repository,
    )


@lru_cache
def get_kubernetes_client() -> KubernetesClient:
    return KubernetesClient()


@lru_cache
def get_finding_store() -> FindingStore:
    return FindingStore()


@lru_cache
def get_approval_store() -> ApprovalStore:
    return ApprovalStore()


@lru_cache
def get_ops_notifier() -> OpsNotifier:
    return OpsNotifier()


@lru_cache
def get_tool_router() -> ToolRouter:
    k8s_client = get_kubernetes_client()
    return ToolRouter(
        tools=[
            WeatherTool(),
            SQLTool(),
            KubernetesTool(client=k8s_client),
            K8sPlaybookTool(client=k8s_client),
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
        approval_store=get_approval_store(),
    )


def get_ops_diagnosis_service() -> OpsDiagnosisService:
    return OpsDiagnosisService(
        k8s_tool=KubernetesTool(client=get_kubernetes_client()),
        finding_store=get_finding_store(),
        notifier=get_ops_notifier(),
        llm_service=get_llm_service() if settings.OPS_USE_LLM_HYPOTHESIS else None,
        prompt_builder=get_prompt_builder(),
        output_parser=get_output_parser(),
    )


@lru_cache
def get_in_memory_user_repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@lru_cache
def get_in_memory_session_store() -> InMemorySessionStore:
    return InMemorySessionStore()


@lru_cache
def get_oauth_registry() -> OAuthProviderRegistry:
    return build_default_oauth_registry()


def get_session_store() -> SessionStore:
    """Resolve session backend (Redis in production, memory for local/tests)."""
    if settings.SESSION_BACKEND.lower() == "redis":
        return RedisSessionStore(redis_client=get_redis_client())
    return get_in_memory_session_store()


async def get_user_repository(
    session: AsyncSession | None = Depends(get_db_session),
) -> UserRepository:
    """Resolve user identity store."""
    if settings.USE_POSTGRES:
        assert session is not None
        return PostgresUserRepository(session=session)
    return get_in_memory_user_repository()


@lru_cache
def get_auth_rate_limiter() -> AuthRateLimiter:
    redis_client = (
        get_redis_client() if settings.SESSION_BACKEND.lower() == "redis" else None
    )
    return AuthRateLimiter(redis_client=redis_client)


@lru_cache
def get_login_lockout_store() -> LoginLockoutStore:
    redis_client = (
        get_redis_client() if settings.SESSION_BACKEND.lower() == "redis" else None
    )
    return LoginLockoutStore(redis_client=redis_client)


async def get_auth_service(
    users: UserRepository = Depends(get_user_repository),
    sessions: SessionStore = Depends(get_session_store),
    lockout: LoginLockoutStore = Depends(get_login_lockout_store),
) -> AuthService:
    return AuthService(users=users, sessions=sessions, lockout=lockout)


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
