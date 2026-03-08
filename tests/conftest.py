"""
Pytest fixtures for LM Studio Web tests.

- app: Flask application instance.
- client: Flask test client.
- config_isolated: Patches config path to a temp file so tests don't touch real config.json.
"""

import pytest

from app import create_app


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def config_isolated(monkeypatch, tmp_path):
    """
    Use a temporary config file so load/save don't affect the real config.json.
    Patches app.config._config_path to return tmp_path / "config.json".
    """
    config_path = tmp_path / "config.json"
    import app.config as app_config

    def _config_path():
        return str(config_path)

    monkeypatch.setattr(app_config, "_config_path", _config_path)
    yield app_config
    # No need to revert: monkeypatch auto-reverts after test
