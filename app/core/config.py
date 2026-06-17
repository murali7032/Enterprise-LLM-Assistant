from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    LLM_PROVIDER: str = "gemini"

    OPENAI_API_KEY: str = ""

    GEMINI_API_KEY: str = ""

    MODEL_NAME: str = "gemini-2.5-flash"

    TEMPERATURE: float = 0.2

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()