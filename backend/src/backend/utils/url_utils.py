"""URL detection and validation helpers."""

import re
from typing import Optional

_MUSIC_URL_PATTERNS = [
    r"youtube\.com/watch",
    r"youtu\.be/",
    r"music\.youtube\.com",
    r"jiosaavn\.com/",
    r"saavn\.com/",
    r"soundcloud\.com/",
    r"spotify\.com/",
    r"gaana\.com/",
    r"wynk\.in/",
]

_SUPPORTED_PATTERNS = [
    r"youtube\.com/watch",
    r"youtu\.be/",
    r"music\.youtube\.com",
    r"soundcloud\.com/",
    r"jiosaavn\.com/",
    r"saavn\.com/",
    r"spotify\.com/",
]

def is_url(query: str) -> bool:
    """Return True if *query* looks like a supported music platform URL."""
    return any(re.search(p, query, re.IGNORECASE) for p in _MUSIC_URL_PATTERNS)

def detect_source(url: str) -> str:
    """Return a human-readable source name for a URL."""
    url_l = url.lower()
    if "soundcloud.com" in url_l:
        return "SoundCloud"
    if "jiosaavn.com" in url_l or "saavn.com" in url_l:
        return "JioSaavn"
    if "spotify.com" in url_l:
        return "Spotify"
    return "YouTube"

def validate_url_simple(url: str) -> dict:
    """
    Check whether *url* belongs to a supported platform.

    Returns a dict with at minimum ``is_valid`` (bool).
    On success also includes: url, source, type, is_playlist, playlist_id.
    """
    for pattern in _SUPPORTED_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            source = detect_source(url)
            is_playlist = bool(re.search(r"[?&]list=([^&]+)", url))
            playlist_id: Optional[str] = None
            if is_playlist:
                m = re.search(r"[?&]list=([^&]+)", url)
                if m:
                    playlist_id = m.group(1)
            return {
                "is_valid": True,
                "url": url,
                "source": source,
                "type": "direct_url",
                "is_playlist": is_playlist,
                "playlist_id": playlist_id,
            }

    return {
        "is_valid": False,
        "error": (
            "Unsupported URL — only YouTube, SoundCloud, JioSaavn, and Spotify are supported"
        ),
        "url": url,
    }

def extract_video_id(url: str) -> Optional[str]:
    """Extract an 11-character YouTube video ID from a URL."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:embed\/)([0-9A-Za-z_-]{11})",
        r"(?:watch\?v=)([0-9A-Za-z_-]{11})",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None
