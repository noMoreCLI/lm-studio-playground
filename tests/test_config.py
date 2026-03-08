"""
Tests for app.config: load, save, connections, migration.

Uses config_isolated fixture so tests run against a temp config file.
"""

import json

import pytest


class TestConfigLoad:
    """Test load() behavior."""

    def test_load_creates_file_with_defaults_when_missing(self, config_isolated, tmp_path):
        """When config.json does not exist, load() creates it with default connection and app settings."""
        cfg = config_isolated.load()
        assert "active_connection_id" in cfg
        assert "connections" in cfg
        assert isinstance(cfg["connections"], list)
        assert len(cfg["connections"]) == 1
        assert cfg["connections"][0]["name"] == "Default"
        assert cfg["connections"][0]["base_url"] == "http://localhost:1234/v1"
        assert cfg.get("webserver_port") == 5000
        assert cfg.get("secret_key") == "dev-secret-key-change-in-production"
        assert (tmp_path / "config.json").exists()
        with open(tmp_path / "config.json") as f:
            on_disk = json.load(f)
        assert on_disk["connections"][0]["base_url"] == "http://localhost:1234/v1"

    def test_load_returns_existing_config(self, config_isolated, tmp_path):
        """When config.json exists, load() returns its data with defaults merged."""
        data = {
            "active_connection_id": "conn-1",
            "connections": [
                {"id": "conn-1", "name": "My Conn", "base_url": "http://custom:9999/v1"},
            ],
            "webserver_port": 3000,
            "secret_key": "test-secret",
        }
        (tmp_path / "config.json").write_text(json.dumps(data), encoding="utf-8")
        cfg = config_isolated.load()
        assert cfg["active_connection_id"] == "conn-1"
        assert cfg["connections"][0]["name"] == "My Conn"
        assert cfg["connections"][0]["base_url"] == "http://custom:9999/v1"
        assert cfg["webserver_port"] == 3000
        assert cfg["secret_key"] == "test-secret"

    def test_load_migrates_flat_config_to_connections(self, config_isolated, tmp_path):
        """Old flat config (base_url, model at top level) is migrated to connections list."""
        flat = {
            "base_url": "http://flat:1111/v1",
            "model": "my-model",
            "system_prompt": "Hello",
            "temperature": 0.5,
            "max_tokens": 512,
            "webserver_port": 4000,
            "secret_key": "flat-secret",
        }
        (tmp_path / "config.json").write_text(json.dumps(flat), encoding="utf-8")
        cfg = config_isolated.load()
        assert "connections" in cfg
        assert len(cfg["connections"]) == 1
        assert cfg["connections"][0]["base_url"] == "http://flat:1111/v1"
        assert cfg["connections"][0]["model"] == "my-model"
        assert cfg["connections"][0]["system_prompt"] == "Hello"
        assert cfg["connections"][0]["temperature"] == 0.5
        assert cfg["connections"][0]["max_tokens"] == 512
        assert cfg["active_connection_id"] == cfg["connections"][0]["id"]
        assert cfg["webserver_port"] == 4000
        assert cfg["secret_key"] == "flat-secret"
        # Migrated format should be persisted
        on_disk = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
        assert "connections" in on_disk and "active_connection_id" in on_disk

    def test_load_on_json_error_returns_defaults(self, config_isolated, tmp_path):
        """When config file is invalid JSON, load() returns default config (does not raise)."""
        (tmp_path / "config.json").write_text("not json {", encoding="utf-8")
        cfg = config_isolated.load()
        assert "connections" in cfg and len(cfg["connections"]) == 1
        assert cfg.get("webserver_port") == 5000


class TestConfigSave:
    """Test save() behavior."""

    def test_save_persists_config(self, config_isolated, tmp_path):
        """save() writes the full config dict to config.json."""
        config_isolated.load()  # ensure file exists
        data = {"active_connection_id": "x", "connections": [], "webserver_port": 5000, "secret_key": "k"}
        config_isolated.save(data)
        on_disk = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
        assert on_disk["active_connection_id"] == "x"
        assert on_disk["connections"] == []


class TestConfigGetters:
    """Test get(), get_connections(), get_connection(), get_active_connection()."""

    def test_get_returns_full_config(self, config_isolated):
        """get() returns the same as load()."""
        config_isolated.load()
        assert config_isolated.get() == config_isolated.load()

    def test_get_connections_returns_list(self, config_isolated, tmp_path):
        """get_connections() returns list of connection dicts."""
        data = {
            "active_connection_id": "a",
            "connections": [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}],
            "webserver_port": 5000,
            "secret_key": "s",
        }
        (tmp_path / "config.json").write_text(json.dumps(data), encoding="utf-8")
        conns = config_isolated.get_connections()
        assert len(conns) == 2
        assert conns[0]["id"] == "a" and conns[0]["name"] == "A"
        assert conns[1]["id"] == "b" and conns[1]["name"] == "B"

    def test_get_connection_returns_merged_defaults(self, config_isolated, tmp_path):
        """get_connection(id) returns connection with CONNECTION_DEFAULTS merged; None if not found."""
        data = {
            "active_connection_id": "c1",
            "connections": [{"id": "c1", "name": "Only", "temperature": 0.3}],
            "webserver_port": 5000,
            "secret_key": "s",
        }
        (tmp_path / "config.json").write_text(json.dumps(data), encoding="utf-8")
        c = config_isolated.get_connection("c1")
        assert c is not None
        assert c["name"] == "Only"
        assert c["temperature"] == 0.3
        assert c["base_url"] == "http://localhost:1234/v1"
        assert config_isolated.get_connection("nonexistent") is None

    def test_get_active_connection_returns_active_with_defaults(self, config_isolated, tmp_path):
        """get_active_connection() returns the active connection dict with defaults merged."""
        data = {
            "active_connection_id": "active",
            "connections": [{"id": "active", "name": "Active", "max_tokens": 2048}],
            "webserver_port": 5000,
            "secret_key": "s",
        }
        (tmp_path / "config.json").write_text(json.dumps(data), encoding="utf-8")
        active = config_isolated.get_active_connection()
        assert active["id"] == "active"
        assert active["name"] == "Active"
        assert active["max_tokens"] == 2048
        assert active["base_url"] == "http://localhost:1234/v1"

    def test_get_active_connection_fallback_when_no_connections(self, config_isolated, tmp_path):
        """When connections list is empty, get_active_connection() returns CONNECTION_DEFAULTS copy."""
        data = {"connections": [], "webserver_port": 5000, "secret_key": "s"}
        (tmp_path / "config.json").write_text(json.dumps(data), encoding="utf-8")
        active = config_isolated.get_active_connection()
        assert active["base_url"] == "http://localhost:1234/v1"
        assert "id" not in active or active.get("id") is None

    def test_get_active_connection_fallback_when_active_id_invalid(self, config_isolated, tmp_path):
        """When active_connection_id does not match any connection, fallback to first and persist."""
        data = {
            "active_connection_id": "invalid-id",
            "connections": [{"id": "real", "name": "Real"}],
            "webserver_port": 5000,
            "secret_key": "s",
        }
        (tmp_path / "config.json").write_text(json.dumps(data), encoding="utf-8")
        active = config_isolated.get_active_connection()
        assert active["id"] == "real"
        on_disk = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
        assert on_disk["active_connection_id"] == "real"


class TestConfigSetters:
    """Test set_active_connection, update_connection, create_connection, delete_connection, update."""

    def test_set_active_connection_saves(self, config_isolated, tmp_path):
        """set_active_connection(id) updates active_connection_id and saves; ignores invalid id."""
        data = {
            "active_connection_id": "first",
            "connections": [{"id": "first", "name": "1"}, {"id": "second", "name": "2"}],
            "webserver_port": 5000,
            "secret_key": "s",
        }
        (tmp_path / "config.json").write_text(json.dumps(data), encoding="utf-8")
        config_isolated.set_active_connection("second")
        on_disk = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
        assert on_disk["active_connection_id"] == "second"
        config_isolated.set_active_connection("nonexistent")
        on_disk = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
        assert on_disk["active_connection_id"] == "second"  # unchanged

    def test_update_connection_updates_and_saves(self, config_isolated, tmp_path):
        """update_connection(id, updates) modifies connection and saves; returns None if not found."""
        data = {
            "active_connection_id": "c1",
            "connections": [{"id": "c1", "name": "Old", "base_url": "http://old/v1"}],
            "webserver_port": 5000,
            "secret_key": "s",
        }
        (tmp_path / "config.json").write_text(json.dumps(data), encoding="utf-8")
        out = config_isolated.update_connection("c1", {"name": "New", "base_url": "http://new/v1"})
        assert out["name"] == "New"
        assert out["base_url"] == "http://new/v1"
        on_disk = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
        assert on_disk["connections"][0]["name"] == "New"
        assert config_isolated.update_connection("bad", {"name": "X"}) is None

    def test_create_connection_appends_and_saves(self, config_isolated, tmp_path):
        """create_connection(name, **overrides) adds a new connection and saves."""
        data = {
            "active_connection_id": "only",
            "connections": [{"id": "only", "name": "Only"}],
            "webserver_port": 5000,
            "secret_key": "s",
        }
        (tmp_path / "config.json").write_text(json.dumps(data), encoding="utf-8")
        new = config_isolated.create_connection("New connection", base_url="http://new/v1")
        assert new["name"] == "New connection"
        assert new["base_url"] == "http://new/v1"
        assert "id" in new
        conns = config_isolated.get_connections()
        assert len(conns) == 2
        assert any(c["name"] == "New connection" for c in conns)

    def test_delete_connection_removes_and_resets_active_if_needed(self, config_isolated, tmp_path):
        """delete_connection(id) removes connection; if it was active, active becomes first remaining."""
        data = {
            "active_connection_id": "b",
            "connections": [
                {"id": "a", "name": "A"},
                {"id": "b", "name": "B"},
                {"id": "c", "name": "C"},
            ],
            "webserver_port": 5000,
            "secret_key": "s",
        }
        (tmp_path / "config.json").write_text(json.dumps(data), encoding="utf-8")
        config_isolated.delete_connection("b")
        cfg = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
        assert len(cfg["connections"]) == 2
        assert cfg["active_connection_id"] == "a"
        config_isolated.delete_connection("a")
        config_isolated.delete_connection("c")
        cfg = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
        assert cfg["connections"] == []
        assert "active_connection_id" not in cfg or cfg.get("active_connection_id") is None

    def test_update_app_level_saves(self, config_isolated, tmp_path):
        """update(updates) applies only APP_DEFAULTS keys and saves."""
        data = {
            "active_connection_id": "x",
            "connections": [{"id": "x", "name": "X"}],
            "webserver_port": 5000,
            "secret_key": "old",
        }
        (tmp_path / "config.json").write_text(json.dumps(data), encoding="utf-8")
        config_isolated.update({"secret_key": "new-secret", "webserver_port": 9999})
        cfg = config_isolated.load()
        assert cfg["secret_key"] == "new-secret"
        assert cfg["webserver_port"] == 9999
