"""
Tests for settings blueprint: GET /settings, POST /settings (set_active, add, delete, save_connection, save_app).
"""

import pytest


class TestSettingsRoutes:
    """Test settings routes; uses config_isolated so config changes don't touch real config.json."""

    def test_settings_get_returns_200_and_renders_page(self, client, config_isolated):
        """GET /settings returns 200 and renders settings page."""
        config_isolated.load()  # ensure config exists
        resp = client.get("/settings/")
        # Flask may redirect /settings to /settings/ (308); accept 200 or follow redirect
        assert resp.status_code == 200
        assert b"settings" in resp.data.lower() or b"<!DOCTYPE" in resp.data or b"connection" in resp.data.lower()

    def test_settings_post_set_active_redirects_and_updates_config(self, client, config_isolated, tmp_path):
        """POST with action=set_active sets active connection and redirects to /settings."""
        import json

        config_isolated.load()
        conns = config_isolated.get_connections()
        if len(conns) < 2:
            config_isolated.create_connection("Second")
            conns = config_isolated.get_connections()
        second_id = [c["id"] for c in conns if c["id"] != conns[0]["id"]][0] if len(conns) > 1 else conns[0]["id"]

        resp = client.post(
            "/settings/",
            data={"action": "set_active", "connection_id": second_id},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303, 308)
        assert "settings" in resp.location or resp.location.endswith("/settings")
        assert config_isolated.get_active_connection()["id"] == second_id

    def test_settings_post_add_connection_redirects_and_creates_connection(self, client, config_isolated):
        """POST with action=add_connection creates a new connection and redirects with edit=id."""
        config_isolated.load()
        initial_count = len(config_isolated.get_connections())

        resp = client.post("/settings", data={"action": "add_connection"}, follow_redirects=True)
        assert resp.status_code == 200
        assert len(config_isolated.get_connections()) == initial_count + 1

    def test_settings_post_save_connection_updates_connection(self, client, config_isolated):
        """POST with action=save_connection and form fields updates the connection."""
        config_isolated.load()
        conn = config_isolated.get_connections()[0]
        cid = conn["id"]

        resp = client.post(
            "/settings/",
            data={
                "action": "save_connection",
                "connection_id": cid,
                "name": "Updated Name",
                "base_url": "http://updated:9999/v1",
                "model": "new-model",
                "temperature": 0.4,
                "max_tokens": 512,
            },
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)
        updated = config_isolated.get_connection(cid)
        assert updated["name"] == "Updated Name"
        assert updated["base_url"] == "http://updated:9999/v1"
        assert updated["model"] == "new-model"
        assert updated["temperature"] == 0.4
        assert updated["max_tokens"] == 512

    def test_settings_post_save_app_updates_secret_key(self, client, config_isolated):
        """POST with action=save_app updates app-level secret_key."""
        config_isolated.load()

        resp = client.post(
            "/settings/",
            data={"action": "save_app", "secret_key": "new-secret-key"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303, 308)
        assert config_isolated.get().get("secret_key") == "new-secret-key"

    def test_settings_post_delete_connection_removes_connection(self, client, config_isolated):
        """POST with action=delete_connection removes the connection."""
        config_isolated.load()
        config_isolated.create_connection("ToDelete")
        conns = config_isolated.get_connections()
        to_delete_id = next(c["id"] for c in conns if c["name"] == "ToDelete")

        resp = client.post(
            "/settings/",
            data={"action": "delete_connection", "connection_id": to_delete_id},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303, 308)
        assert config_isolated.get_connection(to_delete_id) is None
        assert len(config_isolated.get_connections()) == len(conns) - 1