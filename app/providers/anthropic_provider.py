from app.providers.llm_provider import LLMProvider

class AnthropicProvider(LLMProvider):

    def generate(self, prompt: str) -> str:

        return f"Dummy Anthropic Response: {prompt}"