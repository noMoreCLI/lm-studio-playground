"""
Tests for app.use_cases.simple_chat: message building, system prompt, provider call, error handling.
"""

import pytest


class TestSimpleChatRun:
    """Test run(messages, user_message) behavior with mocked config and provider."""

    def test_run_appends_user_message_and_injects_system_prompt(self, monkeypatch):
        """run() builds full_messages with system prompt first (from config) and user message last."""
        from app.use_cases import simple_chat

        sent_messages = []

        def fake_complete(self, messages, **kwargs):
            sent_messages.append(messages)
            return "Hi", {"prompt_tokens": 1, "completion_tokens": 2}, {}

        class FakeProvider:
            complete = fake_complete

        def fake_get_provider():
            return FakeProvider()

        monkeypatch.setattr(simple_chat, "get_provider", fake_get_provider)
        monkeypatch.setattr(
            simple_chat.app_config,
            "get_active_connection",
            lambda: {
                "base_url": "http://x",
                "model": "m",
                "api_key": "k",
                "system_prompt": "You are helpful.",
                "temperature": 0.7,
                "max_tokens": 1024,
            },
        )

        result = simple_chat.run([{"role": "user", "content": "Hello"}], "World")

        assert result["content"] == "Hi"
        assert result["usage"] == {"prompt_tokens": 1, "completion_tokens": 2}
        assert len(sent_messages) == 1
        msgs = sent_messages[0]
        assert msgs[0]["role"] == "system" and msgs[0]["content"] == "You are helpful."
        assert msgs[1]["role"] == "user" and msgs[1]["content"] == "Hello"
        assert msgs[2]["role"] == "user" and msgs[2]["content"] == "World"

    def test_run_updates_existing_system_message_if_present(self, monkeypatch):
        """When messages already start with system, run() replaces it with config system_prompt."""
        from app.use_cases import simple_chat

        sent_messages = []

        def fake_complete(messages, **kwargs):
            sent_messages.append(messages)
            return "Ok", {}, {}

        class FakeProvider:
            def complete(self, messages, **kwargs):
                sent_messages.append(messages)
                return "Ok", {}, {}

        monkeypatch.setattr(simple_chat, "get_provider", lambda: FakeProvider())
        monkeypatch.setattr(
            simple_chat.app_config,
            "get_active_connection",
            lambda: {
                "base_url": "http://x",
                "model": "m",
                "api_key": "k",
                "system_prompt": "New system prompt",
                "temperature": 0.7,
                "max_tokens": 1024,
            },
        )

        simple_chat.run([{"role": "system", "content": "Old"}, {"role": "user", "content": "Hi"}], "There")

        assert sent_messages[0][0]["role"] == "system" and sent_messages[0][0]["content"] == "New system prompt"
        assert sent_messages[0][1]["role"] == "user" and sent_messages[0][1]["content"] == "Hi"
        assert sent_messages[0][2]["role"] == "user" and sent_messages[0][2]["content"] == "There"

    def test_run_includes_raw_request_with_model_temperature_max_tokens(self, monkeypatch):
        """Result includes raw_request with model, messages, temperature, max_tokens from connection."""
        from app.use_cases import simple_chat

        class FakeProvider:
            def complete(self, messages, **kwargs):
                return "Done", {"prompt_tokens": 0, "completion_tokens": 0}, {}

        monkeypatch.setattr(simple_chat, "get_provider", lambda: FakeProvider())
        monkeypatch.setattr(
            simple_chat.app_config,
            "get_active_connection",
            lambda: {
                "base_url": "http://x",
                "model": "my-model",
                "api_key": "k",
                "system_prompt": "",
                "temperature": 0.5,
                "max_tokens": 512,
            },
        )

        result = simple_chat.run([], "Hello")

        assert result["raw_request"]["model"] == "my-model"
        assert result["raw_request"]["temperature"] == 0.5
        assert result["raw_request"]["max_tokens"] == 512
        assert result["raw_request"]["messages"][-1]["content"] == "Hello"

    def test_run_returns_error_when_provider_returns_error_in_raw_response(self, monkeypatch):
        """When provider returns raw_response with 'error' key, run() returns result with error key."""
        from app.use_cases import simple_chat

        class FakeProvider:
            def complete(self, messages, **kwargs):
                return "", {"prompt_tokens": 0, "completion_tokens": 0}, {"error": "Connection refused"}

        monkeypatch.setattr(simple_chat, "get_provider", lambda: FakeProvider())
        monkeypatch.setattr(
            simple_chat.app_config,
            "get_active_connection",
            lambda: {
                "base_url": "http://x",
                "model": "m",
                "api_key": "k",
                "system_prompt": "",
                "temperature": 0.7,
                "max_tokens": 1024,
            },
        )

        result = simple_chat.run([], "Hi")

        assert result["content"] == ""
        assert result["error"] == "Connection refused"
        assert "raw_request" in result
        assert result["raw_response"]["error"] == "Connection refused"
