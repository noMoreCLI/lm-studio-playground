"""
Settings blueprint: manage app config and per-connection LLM settings.

GET /settings/: Renders settings page with connections list and form for the
  active or selected connection (and app-level options).
POST /settings/: Handles form actions: set_active, add_connection,
  delete_connection, save_connection, save_app. All persist to config.json.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import config as app_config

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.route("/", methods=["GET", "POST"])
def index():
    """
    Settings page: list connections, set active, add/delete/edit connections,
    and save app-level settings (e.g. secret_key). Query param ?edit=<id>
    selects which connection to show in the form.
    """
    if request.method == "POST":
        action = request.form.get("action", "save_connection")
        connection_id = request.form.get("connection_id", "").strip()

        if action == "set_active" and connection_id:
            app_config.set_active_connection(connection_id)
            flash("Active connection updated.")
            return redirect(url_for("settings.index"))

        if action == "add_connection":
            conn = app_config.create_connection(name="New connection")
            app_config.set_active_connection(conn["id"])
            flash("Connection added. Configure it below.")
            return redirect(url_for("settings.index", edit=conn["id"]))

        if action == "delete_connection" and connection_id:
            app_config.delete_connection(connection_id)
            flash("Connection removed.")
            return redirect(url_for("settings.index"))

        if action == "save_connection" and connection_id:
            try:
                temperature = float(
                    request.form.get("temperature", app_config.CONNECTION_DEFAULTS["temperature"])
                )
            except (TypeError, ValueError):
                temperature = app_config.CONNECTION_DEFAULTS["temperature"]
            try:
                max_tokens = int(
                    request.form.get("max_tokens", app_config.CONNECTION_DEFAULTS["max_tokens"])
                )
            except (TypeError, ValueError):
                max_tokens = app_config.CONNECTION_DEFAULTS["max_tokens"]
            updates = {
                "name": request.form.get("name", "").strip() or "Unnamed",
                "base_url": request.form.get("base_url", "").strip()
                or app_config.CONNECTION_DEFAULTS["base_url"],
                "model": request.form.get("model", "").strip(),
                "api_key": request.form.get("api_key", "").strip()
                or app_config.CONNECTION_DEFAULTS["api_key"],
                "system_prompt": request.form.get("system_prompt", "").strip()
                or app_config.CONNECTION_DEFAULTS["system_prompt"],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            app_config.update_connection(connection_id, updates)
            flash("Connection saved.")
            return redirect(url_for("settings.index", edit=connection_id))

        # App-level: secret_key
        if action == "save_app":
            cfg = app_config.get()
            secret_key = request.form.get("secret_key", "").strip()
            app_config.update({
                "secret_key": secret_key or cfg.get("secret_key") or app_config.APP_DEFAULTS["secret_key"],
            })
            flash("App settings saved.")
            return redirect(url_for("settings.index"))

    config = app_config.get()
    connections = app_config.get_connections()
    active = app_config.get_active_connection()
    edit_id = request.args.get("edit") or (active.get("id") if active else None)
    edit_connection = app_config.get_connection(edit_id) if edit_id else active

    return render_template(
        "settings.html",
        config=config,
        connections=connections,
        active_connection=active,
        edit_connection=edit_connection,
        connection_defaults=app_config.CONNECTION_DEFAULTS,
        app_defaults=app_config.APP_DEFAULTS,
    )
