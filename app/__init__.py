"""
Flask app factory.

Creates and configures the Flask application: template/static paths, secret key
(from env or config.json), and registration of the chat and settings blueprints.
"""

import os

from flask import Flask


def create_app():
    """
    Create and configure the Flask application.

    Returns:
        Flask: Configured app with chat (/) and settings (/settings) blueprints.
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
        static_folder="static",
        static_url_path="/static",
    )
    from app import config as app_config
    app.secret_key = (
        os.environ.get("SECRET_KEY")
        or app_config.get().get("secret_key")
        or app_config.DEFAULTS["secret_key"]
    )
    from app.routes import chat, settings
    app.register_blueprint(chat.bp)
    app.register_blueprint(settings.bp)
    return app
