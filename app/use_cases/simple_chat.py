"""
Simple chat use case: one round of conversation with the active LLM connection.

Builds the full message list (including system prompt from config), calls the
provider (e.g. LM Studio), and returns content, usage, and raw request/response
for display and debugging.
"""

from app import config as app_config
from app.providers.lm_studio import LMStudioProvider


def get_provider():
    """
    Build and return an LLM provider instance from the current active connection
    (base_url, model, api_key). Currently always returns LMStudioProvider.
    """
    conn = app_config.get_active_connection()
    return LMStudioProvider(
        base_url=conn["base_url"],
        model=conn.get("model") or "local",
        api_key=conn.get("api_key") or "lm-studio",
    )


def run(messages, user_message):
    """
    Run one round of chat: append user message, call LLM, return result.

    Args:
        messages: List of {"role": "user"|"assistant"|"system", "content": "..."} (conversation so far).
        user_message: New user message to append.

    Returns:
        dict with keys: content, usage, raw_request, raw_response, error (optional).
    """
    conn = app_config.get_active_connection()
    full_messages = list(messages)
    if conn.get("system_prompt"):
        system = {"role": "system", "content": conn["system_prompt"]}
        if not full_messages or full_messages[0].get("role") != "system":
            full_messages.insert(0, system)
        else:
            full_messages[0] = system
    full_messages.append({"role": "user", "content": user_message})

    raw_request = {
        "model": conn.get("model") or "local",
        "messages": full_messages,
        "temperature": conn.get("temperature", 0.7),
        "max_tokens": conn.get("max_tokens", 1024),
    }

    provider = get_provider()
    content, usage, raw_response = provider.complete(
        full_messages,
        model=raw_request["model"],
        temperature=raw_request["temperature"],
        max_tokens=raw_request["max_tokens"],
    )

    if isinstance(raw_response, dict) and "error" in raw_response:
        return {
            "content": "",
            "usage": usage,
            "raw_request": raw_request,
            "raw_response": raw_response,
            "error": raw_response["error"],
        }

    return {
        "content": content,
        "usage": usage,
        "raw_request": raw_request,
        "raw_response": raw_response,
    }
