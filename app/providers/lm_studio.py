"""
LM Studio provider: uses the OpenAI Python client with base_url to talk to
LM Studio's local server (OpenAI-compatible API, typically localhost:1234/v1).
"""

from openai import OpenAI

from app.providers.base import LLMProvider


class LMStudioProvider(LLMProvider):
    """
    LLM provider for LM Studio's local server. Uses the same API shape as OpenAI,
    so the official openai client with base_url works without code changes.
    """

    def __init__(self, base_url, model="", api_key="lm-studio", **kwargs):
        """Set base_url, model (default 'local'), and optional api_key. Builds OpenAI client."""
        self.base_url = base_url
        self.model = model or "local"
        self._client = OpenAI(base_url=base_url, api_key=api_key or "lm-studio", **kwargs)

    def complete(self, messages, **kwargs):
        """
        Run chat completion against LM Studio. Returns (content, usage_dict, raw_response).
        On connection/API errors, returns ("", usage, {"error": str(e)}) instead of raising.
        """
        model = kwargs.pop("model", None) or self.model
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1024)
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **{k: v for k, v in kwargs.items() if k not in ("model", "temperature", "max_tokens")},
            )
        except Exception as e:
            return "", {"prompt_tokens": 0, "completion_tokens": 0}, {"error": str(e)}

        choice = response.choices[0] if response.choices else None
        content = choice.message.content if choice and choice.message else ""
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }
        try:
            raw = response.model_dump() if hasattr(response, "model_dump") else dict(response)
        except Exception:
            raw = {"id": getattr(response, "id", ""), "choices": [], "usage": usage}
        return content, usage, raw
