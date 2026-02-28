# API Configuration
TIDAL_APIS = [
    "https://triton.squid.wtf",
    "https://hifi-one.spotisaver.net",
    "https://hifi-two.spotisaver.net",
    "https://tidal.kinoplus.online",
    "https://tidal-api.binimum.org"
]

QOBUZ_STANDARD_APIS = [
    "https://dab.yeet.su/api/stream",
    "https://dabmusic.xyz/api/stream",
    "https://qobuz.squid.wtf/api/download-music"
]

QOBUZ_JUMO_API = "https://jumo-dl.pages.dev/get"
QOBUZ_SEARCH_API = "https://www.qobuz.com/api.json/0.2/track/search"
QOBUZ_APP_ID = "798273057"

AMAZON_API = "https://amazon.afkarxyz.fun/api/track"

SONGLINK_API = "https://api.song.link/v1-alpha.1/links"
DEEZER_API = "https://api.deezer.com/track"

SPOTIFY_TOKEN_URL = "https://open.spotify.com/api/token"
SPOTIFY_HOME_URL = "https://open.spotify.com"
SPOTIFY_CLIENT_TOKEN_URL = "https://clienttoken.spotify.com/v1/clienttoken"
SPOTIFY_GRAPHQL_URL = "https://api-partner.spotify.com/pathfinder/v2/query"

# TOTP Secrets (Version 61)
TOTP_SECRET_V61 = [
    44, 55, 47, 42, 70, 40, 34, 114, 76, 74, 50, 111, 120, 97, 75, 76, 94, 102, 43, 69, 49, 120, 118, 80, 64, 78
]

# User Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"

# Rate Limiting
SONGLINK_MIN_DELAY = 7  # seconds between calls
SONGLINK_RETRY_DELAY = 15  # seconds on 429

# Quality Settings
TIDAL_QUALITY = {
    'HI_RES': 'HI_RES',
    'LOSSLESS': 'LOSSLESS'
}

QOBUZ_QUALITY = {
    'HI_RES': '27',
    'STANDARD_24BIT': '7',
    'LOSSLESS': '6'
}

# SpotDL (YouTube fallback)
SPOTDL_ENABLED = True  # Set to False to disable SpotDL fallback

# Default Settings
DEFAULT_OUTPUT_DIR = "./downloads"
DEFAULT_SERVICE = "auto"  # auto, tidal, qobuz, amazon, spotdl
DEFAULT_QUALITY = "HI_RES"
