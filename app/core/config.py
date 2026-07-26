from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_NAME: str = "Enterprise LLM Platform"
    DEBUG: bool = False
    LLM_PROVIDER: str = "openai"
    MODEL_NAME: str = "gpt-4o-mini"
    TEMPERATURE: float = 0.2
    MAX_TOKENS: int = 4096

    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600
    CACHE_ENABLED: bool = True

    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "documents"
    EMBEDDING_PROVIDER: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/llm_platform"
    USE_POSTGRES: bool = False

    CHUNK_SIZE: int = 100
    CHUNK_OVERLAP: int = 10
    TOP_K: int = 5
    TOP_N: int = 3

    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_BACKOFF_SECONDS: float = 1.0
    REQUEST_TIMEOUT_SECONDS: float = 60.0
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RESET_TIMEOUT: float = 30.0

    JWT_SECRET_KEY: str = Field(default="change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Browser sessions (opaque id in HttpOnly cookie → Redis/memory store)
    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_TTL_SECONDS: int = 60 * 60 * 24 * 14  # 14 days
    SESSION_COOKIE_SECURE: bool = False  # set True behind HTTPS in production
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_BACKEND: str = "memory"  # "memory" | "redis"
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    AUTH_DEV_TOKEN_ENABLED: bool = False  # open JWT mint; enable only for local/tests
    AUTH_MIN_PASSWORD_LENGTH: int = 8
    AUTH_LOGIN_MAX_FAILURES: int = 5
    AUTH_LOCKOUT_SECONDS: int = 900
    AUTH_RATE_LIMIT_REQUESTS: int = 20
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60
    DEFAULT_USER_ROLE: str = "user"
    APP_PUBLIC_URL: str = "http://localhost:8000"

    # OAuth (Google first; leave blank to disable)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    OAUTH_STATE_TTL_SECONDS: int = 600

    LOG_LEVEL: str = "INFO"
    METRICS_ENABLED: bool = True

    MEMORY_ENABLED: bool = True
    MEMORY_MAX_MESSAGES: int = 10
    MEMORY_MAX_CHARS: int = 8000

    EPHEMERAL_CHAT_DOCUMENTS: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
