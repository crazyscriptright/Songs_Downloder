"""
Central configuration — all environment variables and constants in one place.
All other modules import from here; nothing reads os.getenv directly.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# Detect if running on Heroku to adjust paths, caching, and storage behaviour.
IS_HEROKU: bool = bool(os.getenv("DYNO"))

# Base directory for cache and temporary files.
CACHE_DIR: str = "/tmp" if IS_HEROKU else "."

# Root directory where completed downloads are saved.
DOWNLOAD_FOLDER: str = (
    "/tmp/downloads"
    if IS_HEROKU
    else os.path.join(os.path.expanduser("~"), "Downloads", "Music")
)

# Paths for persistent JSON state files used for crash recovery.
UNIFIED_CACHE_FILE: str = os.path.join(CACHE_DIR, "music_api_cache.json")
DOWNLOAD_QUEUE_FILE: str = os.path.join(CACHE_DIR, "download_queue.json")
DOWNLOAD_STATUS_FILE: str = os.path.join(CACHE_DIR, "download_status.json")

# Secret key for Flask session signing. Change in production.
SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")

# Frontend origin for CORS and redirects.
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5000")

# Flask environment mode: development, production, or testing.
FLASK_ENV: str = os.getenv("FLASK_ENV", "production")

# Port the backend server listens on.
PORT: int = int(os.getenv("PORT", 5000))

# Force all downloads through the proxy API instead of yt-dlp. Overrides per-source method settings.
FORCE_PROXY_API: bool = os.getenv("FORCE_PROXY_API", "false").lower() == "true"

# Per-source download method: "YT-DLP" (local) or "PROXY" (remote API).
SOURCE_DOWNLOAD_METHOD: dict[str, str] = {
    "youtube":    os.getenv("SOURCE_YOUTUBE",    "YT-DLP").upper(),
    "soundcloud": os.getenv("SOURCE_SOUNDCLOUD", "YT-DLP").upper(),
    "jiosaavn":   os.getenv("SOURCE_JIOSAAVN",   "YT-DLP").upper(),
}

# Outbound HTTP proxy for general API requests.
HTTP_PROXY: str | None = os.getenv("HTTP_PROXY") or None
# Outbound HTTPS proxy for general API requests.
HTTPS_PROXY: str | None = os.getenv("HTTPS_PROXY") or None
# Dedicated proxy for JioSaavn API requests (often geo-restricted).
JIOSAAVN_PROXY: str | None = os.getenv("JIOSAAVN_PROXY") or None

# Temporary file directory for intermediate processing.
TMPDIR: str = os.getenv("TMPDIR", "/tmp")

# Fallback proxy API bases tried in order when the primary download method fails.
PROXY_API_BASES: list[str] = [
    os.getenv("PROXY_API_BASE_1", "https://p.savenow.to"),
    os.getenv("PROXY_API_BASE_2", "https://p.lbserver.xyz"),
]

# Selects which proxy provider to use for testing: "proxy1", "proxy2", "dubs", or unset for all.
PROXY_DOWNLOADER: str | None = os.getenv("PROXY_DOWNLOADER") or None

# Alternative provider endpoint to initiate a download when SaveNow is unavailable.
DUBS_START_ENDPOINT: str = os.getenv("DUBS_START_ENDPOINT",
    "https://dubs.io/wp-json/tools/v1/download-video")
# Alternative provider endpoint to poll download progress until completion.
DUBS_STATUS_ENDPOINT: str = os.getenv("DUBS_STATUS_ENDPOINT",
    "https://dubs.io/wp-json/tools/v1/status-video")

# API key for the proxy download service.
VIDEO_DOWNLOAD_API_KEY: str = os.getenv("VIDEO_DOWNLOAD_API_KEY", "")

# Preview metadata cache TTL in seconds (5 min).
PREVIEW_CACHE_TTL: int = 300
# Maximum entries in the preview LRU cache.
PREVIEW_CACHE_MAX_SIZE: int = 60
# YouTube Music API token cache lifetime in hours.
API_CACHE_HOURS: int = 2

# User-Agent header sent in all HTTP requests to platform APIs.
USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/144.0.0.0 Safari/537.36"
)

# Tidal download API endpoints tried in order (community-hosted).
TIDAL_APIS: list[str] = [
    "https://triton.squid.wtf",
    "https://hifi-one.spotisaver.net",
    "https://hifi-two.spotisaver.net",
]
# Tidal audio quality presets: HI_RES or LOSSLESS.
TIDAL_QUALITY: dict[str, str] = {"HI_RES": "HI_RES", "LOSSLESS": "LOSSLESS"}

# Qobuz download API endpoints tried in order (community-hosted).
QOBUZ_STANDARD_APIS: list[str] = [
    "https://dab.yeet.su/api/stream",
    "https://dabmusic.xyz/api/stream",
]
# Fallback Qobuz download API via jumo-dl.
QOBUZ_JUMO_API:    str = "https://jumo-dl.pages.dev/get"
# Qobuz search API endpoint for track lookup.
QOBUZ_SEARCH_API:  str = "https://www.qobuz.com/api.json/0.2/track/search"
# Qobuz application ID required for API authentication.
QOBUZ_APP_ID:      str = "798273057"
# Qobuz audio quality presets mapped to API format codes.
QOBUZ_QUALITY: dict[str, str] = {
    "HI_RES": "27",
    "STANDARD_24BIT": "7",
    "LOSSLESS": "6",
}

# Amazon Music download API endpoints tried in order (community-hosted).
AMAZON_APIS: list[str] = [
    "https://amzn.afkarxyz.fun/api/track",     # v7.1.0 current endpoint
    "https://amazon.squid.wtf/api/track",
    "https://amazon.afkarxyz.app/api/track",
    "https://amazon.afkarxyz.fun/api/track",
]

# Song.link API for cross-platform track link resolution.
SONGLINK_API:       str = "https://api.song.link/v1-alpha.1/links"
# Deezer API for track metadata lookup.
DEEZER_API:         str = "https://api.deezer.com/track"
# Minimum delay in seconds between Song.link API calls to avoid rate limits.
SONGLINK_MIN_DELAY: int = 7
# Retry delay in seconds after a Song.link 429 rate-limit response.
SONGLINK_RETRY_DELAY: int = 15

# Default download service when none is specified.
DEFAULT_SERVICE:    str = "auto"
# Default audio quality when none is specified.
DEFAULT_QUALITY:    str = "HI_RES"
# Default output directory for downloads.
DEFAULT_OUTPUT_DIR: str = os.path.join(os.path.expanduser("~"), "Downloads", "Music")

# Spotify web-player token endpoint for API authentication.
SPOTIFY_TOKEN_URL:        str = "https://open.spotify.com/api/token"
# Spotify home page URL used for cookie-based session bootstrapping.
SPOTIFY_HOME_URL:         str = "https://open.spotify.com"
# Spotify client token endpoint for API authentication.
SPOTIFY_CLIENT_TOKEN_URL: str = "https://clienttoken.spotify.com/v1/clienttoken"
# Spotify GraphQL endpoint for metadata queries.
SPOTIFY_GRAPHQL_URL:      str = "https://api-partner.spotify.com/pathfinder/v2/query"
# Spotify lyrics endpoint — {track_id} is substituted at request time.
SPOTIFY_LYRICS_URL:       str = "https://spclient.wg.spotify.com/color-lyrics/v2/track/{track_id}?format=json&vocalRemoval=false"
# TOTP secret (version 61) used to authenticate the Spotify web-player token request.
TOTP_SECRET_V61: list[int] = [
    44, 55, 47, 42, 70, 40, 34, 114, 76, 74, 50, 111, 120, 97, 75,
    76, 94, 102, 43, 69, 49, 120, 118, 80, 64, 78,
]

# Maps yt-dlp error message patterns to user-facing strings matched case-insensitively.
USER_ERROR_MAP: dict[str, str] = {
    "requested format is not available": "This song's format is not available. Try a different song or source.",
    "video unavailable": "This video is no longer available.",
    "private video": "This video is private and cannot be downloaded.",
    "this video is not available": "This video is not available for download.",
    "unable to download": "Unable to download this content. It may be restricted.",
    "http error": "A server error occurred. Please try again later.",
    "is not a valid url": "The provided URL is not valid.",
    "unsupported url": "This URL is not supported for download.",
    "no suitable formats": "No suitable formats found for this content.",
    "sign in to confirm": "This content requires authentication and cannot be downloaded.",
    "members-only content": "This is members-only content and cannot be downloaded.",
    "not supported": "This content is not supported for download.",
    "unsupported site": "This website is not supported for download.",
    "no video formats found": "No video formats found for this content.",
}
