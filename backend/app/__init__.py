from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge
from flask_cors import CORS

from .config import Config
from .routes import api_bp


def create_app() -> Flask:
    """Application factory for the Resume Analyzer API."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS so frontend deployments can call the API from another domain.
    CORS(app)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(_error):
        max_size_mb = app.config.get("MAX_CONTENT_LENGTH", 0) / (1024 * 1024)
        return (
            jsonify(
                {
                    "error": f"File too large. Maximum allowed size is {max_size_mb:.0f} MB.",
                }
            ),
            413,
        )

    app.register_blueprint(api_bp, url_prefix="/api")

    return app
