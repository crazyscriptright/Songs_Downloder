"""Routes package — registers all Flask Blueprints."""

from backend.routes.search import search_bp
from backend.routes.download import download_bp
from backend.routes.preview import preview_bp
from backend.routes.proxy import proxy_bp
from backend.routes.flac_download import flac_bp
from backend.routes.ytdlp_test import ytdlp_bp


def register_blueprints(app):
    app.register_blueprint(search_bp)
    app.register_blueprint(download_bp)
    app.register_blueprint(preview_bp)
    app.register_blueprint(proxy_bp)
    app.register_blueprint(flac_bp)
    app.register_blueprint(ytdlp_bp)
