"""
Central configuration — all environment variables and constants in one place.
All other modules import from here; nothing reads os.getenv directly.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Environment ────────────────────────────────────────────────────────────────
IS_HEROKU: bool = bool(os.getenv("DYNO"))

# ── Paths ──────────────────────────────────────────────────────────────────────
CACHE_DIR: str = "/tmp" if IS_HEROKU else "."

DOWNLOAD_FOLDER: str = (
    "/tmp/downloads"
    if IS_HEROKU
    else os.path.join(os.path.expanduser("~"), "Downloads", "Music")
)

UNIFIED_CACHE_FILE: str = os.path.join(CACHE_DIR, "music_api_cache.json")
DOWNLOAD_QUEUE_FILE: str = os.path.join(CACHE_DIR, "download_queue.json")
DOWNLOAD_STATUS_FILE: str = os.path.join(CACHE_DIR, "download_status.json")

# ── Flask ──────────────────────────────────────────────────────────────────────
SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5000")
FLASK_ENV: str = os.getenv("FLASK_ENV", "production")
PORT: int = int(os.getenv("PORT", 5000))

# ── Feature flags ──────────────────────────────────────────────────────────────
# Set FORCE_PROXY_API=true in .env to always use proxy API instead of yt-dlp
FORCE_PROXY_API: bool = os.getenv("FORCE_PROXY_API", "false").lower() == "true"

# ── API keys ───────────────────────────────────────────────────────────────────
VIDEO_DOWNLOAD_API_KEY: str = os.getenv("VIDEO_DOWNLOAD_API_KEY", "")

# ── Cache TTLs ─────────────────────────────────────────────────────────────────
PREVIEW_CACHE_TTL: int = 300          # seconds (5 min)
PREVIEW_CACHE_MAX_SIZE: int = 60      # max entries in preview LRU cache
API_CACHE_HOURS: int = 2              # YouTube Music API token cache lifetime
