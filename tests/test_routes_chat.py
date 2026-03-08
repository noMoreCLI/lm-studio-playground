"""
Tests for chat blueprint: GET /, GET /api/status, POST /api/complete.
"""

import pytest


class TestChatRoutes:
    """Test chat routes with mocked config and use case."""

    def test_index_returns_200_and_renders_chat_template(self, client):
        """GET / returns 200 and renders the chat page."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"chat" in resp.data.lower() or b"<!DOCTYPE" in resp.data or b"<html" in resp.data

    def test_api_status_returns_json_with_connected_or_error(self, client, monkeypatch):
        """GET /api/status returns JSON with connected, base_url, model; or error when disconnected."""
        from app.routes import chat as chat_route

        monkeypatch.setattr(
            chat_route.app_config,
            "get_active_connection",
            lambda: {
                "base_url": "http://test:1234/v1",
                "model": "test-model",
                "api_key": "test-key",
            },
        )
        # Mock OpenAI client so we don't hit real LM Studio
        mock_models = type("Models", (), {"data": [type("M", (), {"id": "test-model"})()]})()
        mock_list = lambda: mock_models
        mock_client = type("Client", (), {"models": type("Models", (), {"list": mock_list})()})()

        def fake_openai(*args, **kwargs):
            return mock_client

        # The route does "from openai import OpenAI" inside api_status(), so patch at the source
        import openai as openai_module
        monkeypatch.setattr(openai_module, "OpenAI", fake_openai)

        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "connected" in data
        assert data["base_url"] == "http://test:1234/v1"
        assert "model" in data
        if data["connected"]:
            assert "models_available" in data
        else:
            assert "error" in data

    def test_api_complete_requires_message(self, client):
        """POST /api/complete without message returns 400 and error JSON."""
        resp = client.post("/api/complete", json={}, content_type="application/json")
        assert resp.status_code == 400
        assert resp.get_json().get("error") == "message is required"

        resp2 = client.post(
            "/api/complete",
            json={"messages": [], "message": "   "},
            content_type="application/json",
        )
        assert resp2.status_code == 400

    def test_api_complete_returns_content_on_success(self, client, monkeypatch):
        """POST /api/complete with valid message returns 200 and content/usage when run_chat succeeds."""
        from app.routes import chat as chat_route

        monkeypatch.setattr(
            chat_route,
            "run_chat",
            lambda messages, user_message: {
                "content": "Assistant reply",
                "usage": {"prompt_tokens": 1, "completion_tokens": 2},
                "raw_request": {},
                "raw_response": {},
            },
        )

        resp = client.post(
            "/api/complete",
            json={"messages": [], "message": "Hello"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["content"] == "Assistant reply"
        assert data["usage"] == {"prompt_tokens": 1, "completion_tokens": 2}
        assert "error" not in data or data.get("error") is None

    def test_api_complete_returns_200_with_error_key_when_run_chat_returns_error(self, client, monkeypatch):
        """When run_chat returns result with 'error' key, response is 200 with error in JSON."""
        from app.routes import chat as chat_route

        monkeypatch.setattr(
            chat_route,
            "run_chat",
            lambda messages, user_message: {
                "content": "",
                "usage": {},
                "raw_request": None,
                "raw_response": {"error": "Connection refused"},
                "error": "Connection refused",
            },
        )

        resp = client.post(
            "/api/complete",
            json={"messages": [], "message": "Hi"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json().get("error") == "Connection refused"

    def test_api_complete_returns_200_with_error_when_run_chat_raises(self, client, monkeypatch):
        """When run_chat raises, response is 200 with error message in JSON."""
        from app.routes import chat as chat_route

        def run_chat_raise(messages, user_message):
            raise ValueError("Something broke")

        monkeypatch.setattr(chat_route, "run_chat", run_chat_raise)

        resp = client.post(
            "/api/complete",
            json={"messages": [], "message": "Hi"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("error") == "Something broke"
        assert data.get("content") == ""
