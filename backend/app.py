"""
Flask application factory.

Usage:
    gunicorn app:app           (Heroku / production)
    python app.py              (development server)
"""

import os

from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_cors import CORS

from core import config
from core import state
from routes import register_blueprints


def create_app() -> Flask:
    flask_app = Flask(__name__)

    flask_app.config["SECRET_KEY"] = config.SECRET_KEY
    flask_app.config["DOWNLOAD_FOLDER"] = config.DOWNLOAD_FOLDER
    flask_app.config["TEMPLATES_AUTO_RELOAD"] = True

    CORS(flask_app, resources={r"/*": {"origins": "*"}})

    register_blueprints(flask_app)

    return flask_app


# Module-level instance used by gunicorn (`gunicorn app:app`)
app = create_app()

if __name__ == "__main__":
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
