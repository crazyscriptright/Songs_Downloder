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

# ── SpotiFLAC / spoflac_core platform constants ─────────────────────────────────
# These are read by spoflac_core/modules/* via `from config import …`
# when spoflac_core is imported as a proper sub-package.

USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/144.0.0.0 Safari/537.36"
)

# Tidal
TIDAL_APIS: list[str] = [
    "https://triton.squid.wtf",
    "https://hifi-one.spotisaver.net",
    "https://hifi-two.spotisaver.net",
]
TIDAL_QUALITY: dict[str, str] = {"HI_RES": "HI_RES", "LOSSLESS": "LOSSLESS"}

# Qobuz
QOBUZ_STANDARD_APIS: list[str] = [
    "https://dab.yeet.su/api/stream",
    "https://dabmusic.xyz/api/stream",
]
QOBUZ_JUMO_API:    str = "https://jumo-dl.pages.dev/get"
QOBUZ_SEARCH_API:  str = "https://www.qobuz.com/api.json/0.2/track/search"
QOBUZ_APP_ID:      str = "798273057"
QOBUZ_QUALITY: dict[str, str] = {
    "HI_RES": "27",
    "STANDARD_24BIT": "7",
    "LOSSLESS": "6",
}

# Amazon Music — try these in order; add/remove as services go up/down
AMAZON_APIS: list[str] = [
    "https://amzn.afkarxyz.fun/api/track",     # v7.1.0 current endpoint
    "https://amazon.squid.wtf/api/track",
    "https://amazon.afkarxyz.app/api/track",
    "https://amazon.afkarxyz.fun/api/track",
]

# Song.link / Deezer
SONGLINK_API:       str = "https://api.song.link/v1-alpha.1/links"
DEEZER_API:         str = "https://api.deezer.com/track"
SONGLINK_MIN_DELAY: int = 7    # seconds between calls
SONGLINK_RETRY_DELAY: int = 15  # seconds on 429

# Download defaults (used by routes/flac_download.py)
DEFAULT_SERVICE:    str = "auto"        # auto | tidal | qobuz | amazon | soundcloud
DEFAULT_QUALITY:    str = "HI_RES"      # HI_RES | LOSSLESS | 27 | 7 | 6
DEFAULT_OUTPUT_DIR: str = os.path.join(os.path.expanduser("~"), "Downloads", "Music")

# Spotify (web-player token endpoint)
SPOTIFY_TOKEN_URL:        str = "https://open.spotify.com/api/token"
SPOTIFY_HOME_URL:         str = "https://open.spotify.com"
SPOTIFY_CLIENT_TOKEN_URL: str = "https://clienttoken.spotify.com/v1/clienttoken"
SPOTIFY_GRAPHQL_URL:      str = "https://api-partner.spotify.com/pathfinder/v2/query"
# TOTP secret (version 61) — used to authenticate the web-player token request
TOTP_SECRET_V61: list[int] = [
    44, 55, 47, 42, 70, 40, 34, 114, 76, 74, 50, 111, 120, 97, 75,
    76, 94, 102, 43, 69, 49, 120, 118, 80, 64, 78,
]

# FLAC download defaults
DEFAULT_OUTPUT_DIR: str = str(DOWNLOAD_FOLDER)   # reuse existing path
DEFAULT_SERVICE:    str = "auto"                  # auto | tidal | qobuz | amazon | soundcloud
DEFAULT_QUALITY:    str = "HI_RES"
