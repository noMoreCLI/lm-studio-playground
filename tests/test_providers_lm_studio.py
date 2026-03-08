"""
Tests for app.providers.lm_studio: LMStudioProvider complete() with mocked OpenAI client.
"""

from types import SimpleNamespace

import pytest


class TestLMStudioProvider:
    """Test LMStudioProvider initialization and complete()."""

    def test_complete_returns_content_usage_raw_on_success(self, monkeypatch):
        """When OpenAI client returns a valid response, complete() returns (content, usage, raw)."""
        from app.providers.lm_studio import LMStudioProvider

        msg = SimpleNamespace(content="Hello back")
        choice = SimpleNamespace(message=msg)
        usage_obj = SimpleNamespace(prompt_tokens=2, completion_tokens=3, total_tokens=5)
        fake_response = SimpleNamespace(
            choices=[choice],
            usage=usage_obj,
            model_dump=lambda: {},
        )

        def fake_create(**kwargs):
            assert kwargs.get("messages") == [{"role": "user", "content": "Hi"}]
            return fake_response

        mock_client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)),
        )
        monkeypatch.setattr("app.providers.lm_studio.OpenAI", lambda *a, **kw: mock_client)

        provider = LMStudioProvider(base_url="http://localhost:1234/v1", model="local")
        content, usage, raw = provider.complete(
            [{"role": "user", "content": "Hi"}],
            model="local",
            temperature=0.7,
            max_tokens=1024,
        )

        assert content == "Hello back"
        assert usage == {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}
        assert isinstance(raw, dict)

    def test_complete_returns_error_tuple_on_exception(self, monkeypatch):
        """When OpenAI client raises, complete() returns ("", usage, {"error": str(e)})."""
        from app.providers.lm_studio import LMStudioProvider

        def fake_create(*args, **kwargs):
            raise ConnectionError("Connection refused")

        mock_client = type("Client", (), {"chat": type("Chat", (), {
            "completions": type("Completions", (), {"create": fake_create})(),
        })()})()
        monkeypatch.setattr("app.providers.lm_studio.OpenAI", lambda *a, **kw: mock_client)

        provider = LMStudioProvider(base_url="http://localhost:1234/v1")
        content, usage, raw = provider.complete([{"role": "user", "content": "Hi"}])

        assert content == ""
        assert usage == {"prompt_tokens": 0, "completion_tokens": 0}
        assert raw.get("error") == "Connection refused"

    def test_init_defaults_model_and_api_key(self, monkeypatch):
        """LMStudioProvider(model='', api_key=None) uses 'local' and 'lm-studio'."""
        from app.providers.lm_studio import LMStudioProvider

        calls = []

        def track_openai(*args, **kwargs):
            calls.append(kwargs)
            return type("Client", (), {"chat": type("Chat", (), {
                "completions": type("Completions", (), {
                    "create": lambda *a, **kw: None,
                })(),
            })()})()

        monkeypatch.setattr("app.providers.lm_studio.OpenAI", track_openai)

        p = LMStudioProvider(base_url="http://x", model="")
        assert p.model == "local"
        assert len(calls) >= 1
        assert calls[0].get("api_key") == "lm-studio"
        assert calls[0].get("base_url") == "http://x"

        p2 = LMStudioProvider(base_url="http://y", api_key="custom-key")
        assert any(c.get("api_key") == "custom-key" for c in calls)