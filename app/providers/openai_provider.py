from app.clients.openai_client import OpenAIClient

from app.core.config import settings

from app.providers.llm_provider import LLMProvider


class OpenAIProvider(
    LLMProvider
):

    def __init__(self):

        self.client = OpenAIClient()

    def generate(
        self,
        prompt: str
    ) -> str:

        return self.client.generate(

            prompt=prompt,

            model=settings.MODEL_NAME

        )