import os
import requests
from .base import ModelProvider


class OllamaProvider(ModelProvider):
    """
    Local, free, no API key. Requires Ollama running (default
    http://localhost:11434) with a model already pulled, e.g.:
        ollama pull llama3.3
    """

    def __init__(self, model: str = "llama3.3"):
        self.model = model
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = requests.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
            },
            timeout=300,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
