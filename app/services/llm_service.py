from app.providers.llm_provider import (
    LLMProvider
)


class LLMService:

    def __init__(
        self,
        provider: LLMProvider
    ):

        self.provider = provider

    def generate(
        self,
        prompt: str
    ) -> str:

        return self.provider.generate(prompt)