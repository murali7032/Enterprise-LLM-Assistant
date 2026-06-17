from openai import OpenAI

from app.core.config import settings


class OpenAIClient:

    def __init__(self):

        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY
        )

    def generate(
        self,
        prompt: str,
        model: str
    ) -> str:

        response = self.client.chat.completions.create(

            model=model,

            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=settings.TEMPERATURE

        )

        return response.choices[0].message.content