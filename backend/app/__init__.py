from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from flask_cors import CORS

from .config import Config
from .routes import api_bp


def create_app() -> Flask:
    """Application factory for the Resume Analyzer API."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS so frontend deployments can call the API from another domain.
    # Lock this down in production by setting CORS_ORIGINS.
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(_error):
        max_size_mb = app.config.get("MAX_CONTENT_LENGTH", 0) / (1024 * 1024)
        return (
            jsonify(
                {
                    "error": f"Upload too large. Maximum total request size is {max_size_mb:.0f} MB.",
                }
            ),
            413,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        # Keep 4xx/5xx responses as JSON without swallowing their status code.
        return jsonify({"error": error.description}), error.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        # Never leak a stack trace as HTML; the frontend always expects JSON.
        app.logger.exception("Unhandled error while serving request")
        return jsonify({"error": f"Unexpected server error: {error}"}), 500

    app.register_blueprint(api_bp, url_prefix="/api")

    return app
