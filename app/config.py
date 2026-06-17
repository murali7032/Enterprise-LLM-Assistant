from dotenv import load_dotenv
import os

load_dotenv()


class Settings:

    MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai")

    MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")

    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.2))

    TOP_K = int(os.getenv("TOP_K", 20))

    TOP_N = int(os.getenv("TOP_N", 5))


settings = Settings()