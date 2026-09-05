# gemini.py

import os
from .base import ModelProvider


def _is_transient(e: Exception) -> bool:
    """Same definition wake.py uses for its own retry logic: 503
    (overloaded) and 429 (rate/quota) are worth trying something else
    for; anything else (bad key, malformed request, etc.) will just
    fail the same way again."""
    text = str(e)
    return any(marker in text for marker in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))


class GeminiProvider(ModelProvider):
    """
    Google's free-tier daily request quota
    (GenerateRequestsPerDayPerProjectPerModel-FreeTier) is tracked per
    MODEL, not per project or per key — confirmed by the quotaId in
    Gemini's own 429 error payloads. That means a 429 (or a 503
    "experiencing high demand") on one model doesn't mean the account
    is out of requests, just that this one model's bucket is empty or
    congested. Trying a second, separate free model on the exact same
    key costs nothing and draws from an entirely separate daily
    allowance — so on a transient error, this tries each model in
    `fallback_models` in turn before giving up.
    """

    # Both current (as of Sept 2026), free-tier, GA models distinct
    # from the default primary — see config.yaml to override.
    DEFAULT_FALLBACKS = ["gemini-2.0-flash-lite", "gemini-1.5-flash"]

    def __init__(self, model: str = "gemini-2.0-flash", fallback_models: list[str] = None):
        from google import genai  # pip install google-genai
        from google.genai import types

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=api_key)
        self.types = types  # Store for later use

        if fallback_models is None:
            fallback_models = self.DEFAULT_FALLBACKS
        # Primary model first, then fallbacks, de-duplicated but
        # order-preserving (a fallback equal to the primary would just
        # retry the same exhausted quota bucket, which defeats the
        # point).
        seen = set()
        self.models = []
        for m in [model, *fallback_models]:
            if m and m not in seen:
                self.models.append(m)
                seen.add(m)

    def _extract_text_from_response(self, response) -> str:
        """Safely extract text from a Gemini response, handling various
        response formats and malformed responses."""
        if response is None:
            return None
            
        # Try the simple text attribute first
        if hasattr(response, 'text') and response.text:
            return response.text
        
        # Try candidates (used when response.text is empty but content exists)
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    parts_text = ''.join(part.text for part in candidate.content.parts if part.text)
                    if parts_text:
                        return parts_text
        
        # Try accessing content directly
        if hasattr(response, 'content') and response.content:
            if hasattr(response.content, 'parts') and response.content.parts:
                parts_text = ''.join(part.text for part in response.content.parts if part.text)
                if parts_text:
                    return parts_text
        
        return None

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        last_exc = None
        for model_name in self.models:
            try:
                # Use chat API instead of generate_content to avoid AFC warnings
                # and handle responses more robustly
                chat = self.client.chats.create(model=model_name)
                response = chat.send_message(
                    f"{system_prompt}\n\n{user_prompt}",
                    config=self.types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=8192,
                    )
                )
                
                # Safely extract text from the response
                text = self._extract_text_from_response(response)
                if text:
                    return text
                
                # If we got here, response had no text - try the next model
                print(f"Warning: No text in response from {model_name}", flush=True)
                continue
                
            except Exception as e:
                last_exc = e
                if not _is_transient(e):
                    raise
                # Transient error on this model's own quota bucket —
                # move straight to the next free model (a different
                # bucket, so no backoff needed for that reason alone).
                # wake.py's generate_with_retry still wraps this whole
                # method for same-model backoff/retry if every model
                # here is exhausted or congested.
                continue
        
        # If we get here, all models failed
        if last_exc:
            raise RuntimeError(f"All Gemini models failed. Last error: {last_exc}") from last_exc
        else:
            raise RuntimeError(f"All Gemini models returned empty responses: {self.models}")