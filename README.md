# LM Studio Web

A simple Flask web app to explore and test a local LLM served by [LM Studio](https://lmstudio.ai/) on your Mac. It provides a chat page and a settings page, with parameters (system prompt, temperature, max tokens, etc.) visible and configurable. You can define multiple **connections** (e.g. different base URLs or models) and switch the active one from the Settings page.

## Project structure

- **`run.py`** — Entry point: creates the app and runs the dev server (port from config).
- **`app/`**
  - **`__init__.py`** — Flask app factory: creates app, sets secret key, registers blueprints.
  - **`config.py`** — Load/save `config.json`; app-level settings and per-connection LLM settings (connections list, active connection).
  - **`routes/chat.py`** — Chat blueprint: `/` (chat UI), `/api/status` (connection/model info), `/api/complete` (POST, run completion).
  - **`routes/settings.py`** — Settings blueprint: `/settings` (manage connections and app settings).
  - **`use_cases/simple_chat.py`** — One round of chat: build messages (incl. system prompt), call provider, return content/usage/raw.
  - **`providers/base.py`** — Abstract `LLMProvider` interface (`complete(messages, **kwargs)`).
  - **`providers/lm_studio.py`** — `LMStudioProvider`: OpenAI client with `base_url` for LM Studio’s local API.
- **`config.json`** — Persisted app and connection settings (created with defaults if missing).
- **`templates/`** — Flask HTML templates (e.g. `chat.html`, `settings.html`).

## Prerequisites

- Python 3.10+
- [LM Studio](https://lmstudio.ai/) installed and running on your Mac
- A model loaded in LM Studio with the **local server** started (Developer tab → Start Server, default port 1234)

## Setup

1. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. (Optional) Adjust settings before first run: edit `config.json` in the project root (see **Config** below), or start the app and use the Settings page.

## Run the app

```bash
python run.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

- **Chat** (`/`): Send messages to your local model, see conversation history, token usage, and raw request/response. Uses the **active connection** from Settings.
- **Settings** (`/settings`): Manage **connections** (add, delete, set active, edit). For each connection: base URL, model, API key, system prompt, temperature, max tokens. Also app-level options (e.g. secret key, webserver port). Values are saved to `config.json`.

## Config

Application settings are stored in **`config.json`** in the project root (same folder as `run.py`). If the file does not exist, it is created with defaults on first run.

**App-level** (top-level keys):

- **webserver_port**: Port for the Flask dev server (default `5000`).
- **secret_key**: Flask secret key for sessions (default `dev-secret-key-change-in-production`).

**Connections** (list of connection objects; one is **active**):

- **active_connection_id**: ID of the connection used for Chat and status.
- **connections**: Array of connection objects. Each has:
  - **id**, **name**: Unique id and display name.
  - **base_url**: LM Studio’s OpenAI-compatible API (default `http://localhost:1234/v1`).
  - **model**: Model identifier as shown in LM Studio. Leave empty to use the currently loaded model.
  - **api_key**: Sent to the API (default `lm-studio`).
  - **system_prompt**, **temperature**, **max_tokens**: Used for each completion.
  - **provider**: Reserved for future use (e.g. adding other LLM backends).

Example:

```json
{
  "active_connection_id": "default-lm-studio",
  "connections": [
    {
      "id": "default-lm-studio",
      "name": "LM Studio (local)",
      "base_url": "http://localhost:1234/v1",
      "model": "",
      "api_key": "lm-studio",
      "system_prompt": "You are a helpful assistant.",
      "temperature": 0.7,
      "max_tokens": 1024,
      "provider": "lm_studio"
    }
  ],
  "webserver_port": 5000,
  "secret_key": "dev-secret-key-change-in-production"
}
```

An older flat config (single `base_url`, `model`, etc. at top level) is automatically migrated to this structure when the app loads.

## Running LM Studio’s server

1. Open LM Studio.
2. Load a model (or use one already loaded).
3. Go to the **Developer** tab.
4. Click **Start Server** (default port 1234).

The app uses the OpenAI-compatible endpoint at `http://localhost:1234/v1`. If the server is not running, the Chat page will show “Disconnected” and requests will fail with a clear error.
