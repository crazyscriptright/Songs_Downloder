"""Routes package — registers all Flask Blueprints."""

from routes.search import search_bp
from routes.download import download_bp
from routes.preview import preview_bp
from routes.proxy import proxy_bp
from routes.flac_download import flac_bp


def register_blueprints(app):
    app.register_blueprint(search_bp)
    app.register_blueprint(download_bp)
    app.register_blueprint(preview_bp)
    app.register_blueprint(proxy_bp)
    app.register_blueprint(flac_bp)
