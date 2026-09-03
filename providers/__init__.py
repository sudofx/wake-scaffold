def get_provider(name: str, model: str = None, fallback_models: list[str] = None):
    """
    Factory: returns a ModelProvider instance for the given backend
    name. This is the single place that knows about all providers —
    everything else in the project just calls generate().

    fallback_models is Gemini-specific (per-model free-tier quota
    buckets — see providers/gemini.py) and silently ignored by every
    other provider.
    """
    name = name.lower()

    if name == "gemini":
        from .gemini import GeminiProvider
        kwargs = {}
        if model:
            kwargs["model"] = model
        if fallback_models:
            kwargs["fallback_models"] = fallback_models
        return GeminiProvider(**kwargs)

    if name == "anthropic":
        from .anthropic import AnthropicProvider
        return AnthropicProvider(model=model) if model else AnthropicProvider()

    if name == "openai":
        from .openai import OpenAIProvider
        return OpenAIProvider(model=model) if model else OpenAIProvider()

    if name == "ollama":
        from .ollama import OllamaProvider
        return OllamaProvider(model=model) if model else OllamaProvider()

    if name == "mock":
        from .mock import MockProvider
        return MockProvider()

    raise ValueError(f"Unknown provider: {name}")
