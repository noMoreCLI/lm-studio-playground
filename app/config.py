"""
Load and save application config from config.json.

Supports:
- App-level settings: webserver_port, secret_key.
- Per-connection LLM settings: multiple named connections (base_url, model,
  system_prompt, temperature, max_tokens, etc.) with one active connection
  used for chat and status.

Legacy flat config (single base_url, model, etc. at top level) is migrated
automatically to the connections format on load.
"""

import json
import os
import uuid

# App-level defaults (not per-connection)
APP_DEFAULTS = {
    "webserver_port": 5000,
    "secret_key": "dev-secret-key-change-in-production",
}

# Defaults for each connection (LLM-specific)
CONNECTION_DEFAULTS = {
    "base_url": "http://localhost:1234/v1",
    "model": "",
    "api_key": "lm-studio",
    "system_prompt": "You are a helpful assistant.",
    "temperature": 0.7,
    "max_tokens": 1024,
    "provider": "lm_studio",
}

# Legacy flat config key -> connection key (for migration)
DEFAULTS = {
    **APP_DEFAULTS,
    "base_url": CONNECTION_DEFAULTS["base_url"],
    "model": CONNECTION_DEFAULTS["model"],
    "system_prompt": CONNECTION_DEFAULTS["system_prompt"],
    "temperature": CONNECTION_DEFAULTS["temperature"],
    "max_tokens": CONNECTION_DEFAULTS["max_tokens"],
    "provider": CONNECTION_DEFAULTS["provider"],
}


def _config_path():
    """Return the absolute path to config.json (project root, parent of app/)."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "config.json")


def _migrate_flat_to_connections(data):
    """
    If config is old flat format (base_url, model, etc. at top level),
    convert to connections list + app settings. Otherwise return data unchanged.
    """
    if "connections" in data and isinstance(data.get("connections"), list):
        return data
    # Flat format: base_url, model, etc. at top level
    conn = {
        "id": str(uuid.uuid4()),
        "name": "Default",
        **CONNECTION_DEFAULTS,
        "base_url": data.get("base_url", CONNECTION_DEFAULTS["base_url"]),
        "model": data.get("model", CONNECTION_DEFAULTS["model"]) or "",
        "api_key": data.get("api_key", CONNECTION_DEFAULTS["api_key"]),
        "system_prompt": data.get("system_prompt", CONNECTION_DEFAULTS["system_prompt"]),
        "temperature": data.get("temperature", CONNECTION_DEFAULTS["temperature"]),
        "max_tokens": data.get("max_tokens", CONNECTION_DEFAULTS["max_tokens"]),
        "provider": data.get("provider", CONNECTION_DEFAULTS["provider"]),
    }
    return {
        "active_connection_id": conn["id"],
        "connections": [conn],
        "webserver_port": data.get("webserver_port", APP_DEFAULTS["webserver_port"]),
        "secret_key": data.get("secret_key", APP_DEFAULTS["secret_key"]),
    }


def load():
    """
    Load config from config.json. Creates file with defaults if missing.
    Migrates flat config to connections format if needed. Returns full config dict.
    """
    path = _config_path()
    if not os.path.exists(path):
        default_conn = {
            "id": str(uuid.uuid4()),
            "name": "Default",
            **CONNECTION_DEFAULTS,
        }
        data = {
            "active_connection_id": default_conn["id"],
            "connections": [default_conn],
            **APP_DEFAULTS,
        }
        save(data)
        return data
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data = _migrate_flat_to_connections(data)
        # Ensure app-level defaults
        for k, v in APP_DEFAULTS.items():
            if k not in data:
                data[k] = v
        return data
    except (json.JSONDecodeError, OSError):
        default_conn = {
            "id": str(uuid.uuid4()),
            "name": "Default",
            **CONNECTION_DEFAULTS,
        }
        return {
            "active_connection_id": default_conn["id"],
            "connections": [default_conn],
            **APP_DEFAULTS,
        }


def save(config):
    """Persist the full config dict to config.json (overwrites file)."""
    path = _config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get():
    """Return the full config dict, loading from disk if necessary."""
    return load()


def get_connections():
    """Return a list of all connection config dicts."""
    data = load()
    return list(data.get("connections") or [])


def get_connection(connection_id):
    """
    Get a single connection by id, with CONNECTION_DEFAULTS merged in.
    Returns None if connection_id is not found.
    """
    data = load()
    for c in data.get("connections") or []:
        if c.get("id") == connection_id:
            out = CONNECTION_DEFAULTS.copy()
            out.update(c)
            return out
    return None


def get_active_connection():
    """
    Get the currently active connection dict (defaults merged).
    Falls back to the first connection if no active_connection_id or if it is invalid.
    """
    data = load()
    conns = data.get("connections") or []
    active_id = data.get("active_connection_id")
    if active_id:
        for c in conns:
            if c.get("id") == active_id:
                out = CONNECTION_DEFAULTS.copy()
                out.update(c)
                return out
    if conns:
        out = CONNECTION_DEFAULTS.copy()
        out.update(conns[0])
        return out
    return CONNECTION_DEFAULTS.copy()


def set_active_connection(connection_id):
    """
    Set the active connection by id. Saves config. Ignores invalid ids.
    Returns the full config after update.
    """
    config = load()
    conns = config.get("connections") or []
    if any(c.get("id") == connection_id for c in conns):
        config["active_connection_id"] = connection_id
        save(config)
    return config


def update_connection(connection_id, updates):
    """
    Update a connection by id with the given key-value updates. Saves config.
    Returns the updated connection dict (with defaults merged) or None if not found.
    """
    config = load()
    conns = config.get("connections") or []
    for i, c in enumerate(conns):
        if c.get("id") == connection_id:
            conns[i] = {**c, **updates}
            save(config)
            out = CONNECTION_DEFAULTS.copy()
            out.update(conns[i])
            return out
    return None


def create_connection(name="New connection", **overrides):
    """
    Add a new connection with the given name and optional overrides.
    Returns the new connection dict (with defaults merged).
    """
    config = load()
    conns = list(config.get("connections") or [])
    new_id = str(uuid.uuid4())
    new_conn = {
        "id": new_id,
        "name": name,
        **CONNECTION_DEFAULTS,
        **overrides,
    }
    conns.append(new_conn)
    config["connections"] = conns
    save(config)
    out = CONNECTION_DEFAULTS.copy()
    out.update(new_conn)
    return out


def delete_connection(connection_id):
    """
    Remove a connection by id. If it was the active one, active is set to the
    first remaining connection (or cleared). Saves config. Returns the new config.
    """
    config = load()
    conns = [c for c in (config.get("connections") or []) if c.get("id") != connection_id]
    config["connections"] = conns
    if config.get("active_connection_id") == connection_id and conns:
        config["active_connection_id"] = conns[0]["id"]
    elif config.get("active_connection_id") == connection_id:
        config.pop("active_connection_id", None)
    save(config)
    return config


def update(updates):
    """
    Update app-level config keys (e.g. secret_key, webserver_port). Only keys
    present in APP_DEFAULTS are applied. Saves config. Returns the new config.
    """
    config = load()
    # Only allow app-level keys to be updated here
    for k in APP_DEFAULTS:
        if k in updates:
            config[k] = updates[k]
    save(config)
    return config
