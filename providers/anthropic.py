import os
from .base import ModelProvider


class AnthropicProvider(ModelProvider):
    def __init__(self, model: str = "claude-sonnet-4-6"):
        import anthropic  # pip install anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(
            block.text for block in response.content if block.type == "text"
        )
