"""
Every model backend implements this one method. The wake loop only
ever calls `generate()` — it never knows or cares which provider is
underneath. This is what keeps the memory system portable across
Claude, Gemini, GPT, local Ollama models, or anything else.
"""

from abc import ABC, abstractmethod


class ModelProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Send a system prompt + user prompt, return the model's text
        response as a plain string.

        Implementations should NOT use provider-specific memory,
        threads, or assistant features — this call should be
        stateless from the provider's point of view. All state lives
        in the memory/ files, not in the provider.
        """
        raise NotImplementedError
