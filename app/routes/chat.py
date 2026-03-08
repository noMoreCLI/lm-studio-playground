"""
Chat blueprint: UI and API for talking to the LLM.

- GET /: Renders the chat page.
- GET /api/status: Returns connection status and available models (JSON).
- POST /api/complete: Sends messages + new user message to the LLM, returns completion (JSON).
"""

from flask import Blueprint, jsonify, render_template, request

from app import config as app_config
from app.use_cases.simple_chat import run as run_chat

bp = Blueprint("chat", __name__, url_prefix="/")


@bp.route("/")
def index():
    """Serve the chat page (single-page chat UI)."""
    return render_template("chat.html")


@bp.route("/api/status")
def api_status():
    """
    Check LM Studio (or active connection) and return connection status and model info.
    Returns JSON: connected (bool), base_url, model, models_available, and error if disconnected.
    """
    conn = app_config.get_active_connection()
    base_url = conn.get("base_url", "http://localhost:1234/v1")
    model = conn.get("model") or "local"
    api_key = conn.get("api_key") or "lm-studio"
    try:
        from openai import OpenAI
        client = OpenAI(base_url=base_url, api_key=api_key)
        models = client.models.list()
        model_list = list(getattr(models, "data", None) or [])
        first_id = model_list[0].id if model_list else model
        return jsonify({
            "connected": True,
            "base_url": base_url,
            "model": model or first_id,
            "models_available": [m.id for m in model_list],
        })
    except Exception as e:
        return jsonify({
            "connected": False,
            "base_url": base_url,
            "model": model,
            "error": str(e),
        })


@bp.route("/api/complete", methods=["POST"])
def api_complete():
    """
    Run one chat completion. Expects JSON: messages (list), message (new user text).
    Returns JSON: content, usage, raw_request, raw_response; or error (with 400/200 as appropriate).
    """
    data = request.get_json() or {}
    messages = data.get("messages", [])
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "message is required"}), 400
    try:
        result = run_chat(messages, user_message)
    except Exception as e:
        return jsonify({
            "content": "",
            "usage": {},
            "raw_request": None,
            "raw_response": None,
            "error": str(e),
        }), 200
    if result.get("error"):
        return jsonify({
            "content": "",
            "usage": result.get("usage", {}),
            "raw_request": result.get("raw_request"),
            "raw_response": result.get("raw_response"),
            "error": result["error"],
        }), 200
    return jsonify({
        "content": result["content"],
        "usage": result["usage"],
        "raw_request": result.get("raw_request"),
        "raw_response": result.get("raw_response"),
    })
