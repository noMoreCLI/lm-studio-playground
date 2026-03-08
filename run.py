"""
Entry point for the LM Studio Web application.

Creates the Flask app, loads config (including webserver_port from config.json),
and runs the development server. Run with: python run.py
"""

from app import create_app, config as app_config

app = create_app()

if __name__ == "__main__":
    cfg = app_config.get()
    port = int(cfg.get("webserver_port", 5000))
    app.run(debug=True, port=port)
