from dotenv import load_dotenv
import os

load_dotenv()


class Settings:

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    MODEL_PROVIDER = os.getenv(
        "MODEL_PROVIDER",
        "openai"
    )

    MODEL_NAME = os.getenv(
        "MODEL_NAME",
        "gpt-4o-mini"
    )

    TEMPERATURE = float(
        os.getenv("TEMPERATURE", 0.2)
    )


settings = Settings()