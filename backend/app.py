"""
Flask application factory.

Usage:
    gunicorn app:app           (Heroku / production)
    python app.py              (development server)
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify
from flask_cors import CORS

from core import config
from core import state
from routes import register_blueprints


def create_app() -> Flask:
    flask_app = Flask(__name__)

    # Centralized logging setup
    logging.basicConfig(
        level=logging.DEBUG if config.FLASK_ENV == "development" else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    flask_app.config["SECRET_KEY"] = config.SECRET_KEY
    flask_app.config["DOWNLOAD_FOLDER"] = config.DOWNLOAD_FOLDER
    flask_app.config["TEMPLATES_AUTO_RELOAD"] = True

    CORS(flask_app, resources={r"/*": {"origins": "*"}})

    _register_error_handlers(flask_app)

    register_blueprints(flask_app)

    return flask_app


def _register_error_handlers(app: Flask) -> None:
    """Centralized error handlers for consistent API error responses."""

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({"error": "Unprocessable entity"}), 422

    @app.errorhandler(429)
    def too_many_requests(e):
        return jsonify({"error": "Rate limit exceeded"}), 429

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error("Internal server error: %s", e)
        if config.FLASK_ENV == "development":
            return jsonify({"error": "Internal server error", "detail": str(e)}), 500
        return jsonify({"error": "Internal server error"}), 500


app = create_app()


def main():
    """Run the development server."""
    print(" Universal Music Downloader")
    print(f" Downloads : {config.DOWNLOAD_FOLDER}")
    print(f" Cache file: {config.UNIFIED_CACHE_FILE}")
    print(f" Status    : {config.DOWNLOAD_STATUS_FILE}")
    if os.getenv("DYNO"):
        print("  Running on Heroku (ephemeral /tmp storage)")

    state.load_persistent_data()
    state.cleanup_old_downloads()
    if os.getenv("DYNO"):
        state.cleanup_tmp_directory()

    port = config.PORT
    debug = config.FLASK_ENV == "development"

    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True, use_reloader=debug)


if __name__ == "__main__":
    main()
