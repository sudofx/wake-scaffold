import os
from .base import ModelProvider


class GeminiProvider(ModelProvider):
    def __init__(self, model: str = "gemini-3.6-flash"):
        from google import genai  # pip install google-genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config={"system_instruction": system_prompt},
        )
        return response.text
