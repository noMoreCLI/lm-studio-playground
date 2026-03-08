"""
Abstract LLM provider interface.

Implementations (e.g. LMStudioProvider) talk to a specific backend and return
(content, usage_dict, raw_response) from complete(). Used by the simple_chat
use case so that different backends can be plugged in without changing route logic.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """
    Interface for LLM providers. Subclasses must implement complete() to run
    a chat completion and return content, usage, and raw response.
    """

    @abstractmethod
    def complete(self, messages, **kwargs):
        """
        Run a single chat completion.

        Args:
            messages: List of dicts with "role" and "content"
                (e.g. [{"role": "user", "content": "Hello"}]).
            **kwargs: Provider-specific options (e.g. model, temperature, max_tokens).

        Returns:
            Tuple of (content: str, usage: dict, raw_response).
            usage should include prompt_tokens and completion_tokens when available.
            raw_response can be a dict or API response object for debugging.
        """
        pass
