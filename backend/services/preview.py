"""
Fast audio preview service.

Priority:
  1. yt-dlp download            (downloads lowest-quality audio to a temp
                                 file and serves it directly — most reliable)
  2. SoundCloud native API      (~300 ms fallback, returns CDN URL → proxied)
  3. JioSaavn saavn.dev API     (~400 ms fallback, returns CDN URL → proxied)
"""

import glob
import hashlib
import os
import subprocess
import tempfile
import time

import requests
from urllib.parse import quote_plus
from typing import Optional

_PREVIEW_TMP_DIR = os.path.join(
    os.environ.get("TMPDIR", tempfile.gettempdir()),
    "spotiflac_previews",
)
_PREVIEW_FILE_MAX_AGE = 600

def get_soundcloud_stream_fast(track_url: str, client_id: str) -> Optional[str]:
    """
    Resolve a SoundCloud track page URL → direct progressive MP3 CDN URL.
    Uses api-v2.soundcloud.com — no yt-dlp needed (~300 ms).
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        resolve_url = (
            f"https://api-v2.soundcloud.com/resolve"
            f"?url={quote_plus(track_url)}&client_id={client_id}"
        )
        r = requests.get(resolve_url, headers=headers, timeout=8)
        r.raise_for_status()
        track_data = r.json()

        track_id = track_data.get("id")
        if not track_id:
            print("[preview/sc] No track ID in resolve response")
            return None

        streams_url = (
            f"https://api-v2.soundcloud.com/tracks/{track_id}/streams"
            f"?client_id={client_id}"
        )
        rs = requests.get(streams_url, headers=headers, timeout=8)
        rs.raise_for_status()
        streams = rs.json()

        for key in ("http_mp3_128", "preview_mp3_128", "hls_mp3_128"):
            if streams.get(key):
                print(f"[preview/sc] stream key: {key}")
                return streams[key]

        for key, val in streams.items():
            if key.startswith("http_") and val:
                print(f"[preview/sc] fallback stream key: {key}")
                return val

        print("[preview/sc] no usable stream keys")
        return None

    except Exception as exc:
        print(f"[preview/sc] error: {exc}")
        return None

_SAAVN_APIS = [
    "https://saavn.dev/api/songs",
    "https://jiosaavn-api-2.vercel.app/api/songs",
]

def get_jiosaavn_stream_fast(song_url: str) -> Optional[str]:
    """
    Resolve a JioSaavn song page URL → direct 96 kbps audio URL.
    Uses saavn.dev public API — no yt-dlp needed (~400 ms).
    """
    for base_url in _SAAVN_APIS:
        try:
            r = requests.get(base_url, params={"link": song_url}, timeout=8)
            if r.status_code != 200:
                continue

            data = r.json()
            songs = data.get("data") or []
            if not isinstance(songs, list) or not songs:
                continue

            dl_urls = songs[0].get("downloadUrl") or []
            if not dl_urls:
                continue

            def _kbps(entry: dict) -> int:
                try:
                    return int(entry.get("quality", "999kbps").replace("kbps", "").strip())
                except ValueError:
                    return 999

            stream_url = sorted(dl_urls, key=_kbps)[0]
            url = stream_url.get("url") or stream_url.get("link")
            if url:
                print(f"[preview/saavn] stream from {base_url}")
                return url

        except Exception as exc:
            print(f"[preview/saavn] {base_url}: {exc}")

    print("[preview/saavn] all APIs failed")
    return None

def download_preview_audio(url: str, timeout: int = 40) -> Optional[str]:
    """
    Download the audio at the lowest available quality to a temp file and
    return the local file path.  Much more reliable than yt-dlp -g (get-url)
    because no CDN authentication tokens or CORS issues can block playback.

    Files are reused if they are less than ``_PREVIEW_FILE_MAX_AGE`` seconds
    old.  All files older than that in the temp dir are pruned on each call.
    """
    os.makedirs(_PREVIEW_TMP_DIR, exist_ok=True)

    url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
    prefix = os.path.join(_PREVIEW_TMP_DIR, f"prev_{url_hash}")

    existing = glob.glob(f"{prefix}.*")
    if existing:
        fpath = existing[0]
        age = time.time() - os.path.getmtime(fpath)
        if os.path.getsize(fpath) > 0 and age < _PREVIEW_FILE_MAX_AGE:
            print(f"[preview/dl] reusing cached: {os.path.basename(fpath)}")
            return fpath

    for f in glob.glob(os.path.join(_PREVIEW_TMP_DIR, "prev_*")):
        try:
            if time.time() - os.path.getmtime(f) > _PREVIEW_FILE_MAX_AGE:
                os.remove(f)
        except OSError:
            pass

    out_template = f"{prefix}.%(ext)s"
    cmd = [
        "yt-dlp",
        "--format", "ba[abr<=96]/ba[abr<=128]/worstaudio",
        "--no-playlist",
        "--socket-timeout", "10",
        "--output", out_template,
        "--no-warnings",
        "--quiet",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            files = glob.glob(f"{prefix}.*")
            if files:
                fpath = files[0]
                if os.path.getsize(fpath) > 0:
                    print(f"[preview/dl] downloaded: {os.path.basename(fpath)}")
                    return fpath
            print("[preview/dl] yt-dlp succeeded but no output file found")
        else:
            err = (result.stderr or result.stdout or "unknown error")[:300]
            print(f"[preview/dl] yt-dlp failed (exit {result.returncode}): {err}")
        return None
    except subprocess.TimeoutExpired:
        print(f"[preview/dl] timed out after {timeout}s")
        return None
    except FileNotFoundError:
        print("[preview/dl] yt-dlp not found in PATH")
        return None
    except Exception as exc:
        print(f"[preview/dl] exception: {exc}")
        return None
