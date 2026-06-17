from app.providers.llm_provider import (
    LLMProvider
)


class OpenAIProvider(
    LLMProvider
):

    def generate(
        self,
        prompt: str
    ) -> str:

        return (
            f"Dummy OpenAI Response : {prompt}"
        )