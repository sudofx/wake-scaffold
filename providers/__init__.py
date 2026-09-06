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
        try:
            from .gemini import GeminiProvider
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "Gemini provider requires the google-genai package; "
                "install it with: pip install google-genai"
            ) from error
        kwargs = {}
        if model:
            kwargs["model"] = model
        if fallback_models:
            kwargs["fallback_models"] = fallback_models
        return GeminiProvider(**kwargs)

    if name == "anthropic":
        try:
            from .anthropic import AnthropicProvider
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "Anthropic provider requires the anthropic package; "
                "install it with: pip install anthropic"
            ) from error
        return AnthropicProvider(model=model) if model else AnthropicProvider()

    if name == "openai":
        try:
            from .openai import OpenAIProvider
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "OpenAI provider requires the openai package; "
                "install it with: pip install openai"
            ) from error
        return OpenAIProvider(model=model) if model else OpenAIProvider()

    if name == "ollama":
        from .ollama import OllamaProvider
        return OllamaProvider(model=model) if model else OllamaProvider()

    if name == "mock":
        from .mock import MockProvider
        return MockProvider()

    raise ValueError(f"Unknown provider: {name}")
