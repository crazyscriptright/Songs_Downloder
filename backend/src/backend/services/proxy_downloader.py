"""
Proxy download service — multi-provider fallback downloader.

Follows the pattern from info.js (Userscript):
  1. Primary SaveNow provider with multiple base URL fallbacks
  2. Alternative provider fallback (dubs.io)
  3. Progress polling mechanism

All functions accept a progress_callback for status updates
(to keep state out of this module — downloader.py passes the callback).

Usage:
    result = download_with_proxy_fallback(
        url="https://soundcloud.com/artist/track",
        format_type="flac",
        api_key="...",
        progress_callback=lambda s: print(s)
    )
    if result["success"]:
        print(result["download_url"])
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Callable

import requests

from backend.core import config

logger = logging.getLogger(__name__)


_DEFAULT_PROXY_API_BASES: list[str] = [
    "https://p.savenow.to",
    "https://p.lbserver.xyz",
]

_DEFAULT_DUBS_START: str = "https://dubs.io/wp-json/tools/v1/download-video"
_DEFAULT_DUBS_STATUS: str = "https://dubs.io/wp-json/tools/v1/status-video"

POLL_INTERVAL_SEC: int = 3
MAX_POLLS: int = 60          # 60 * 3s = 3 min timeout
PROVIDER_TIMEOUT_SEC: int = 25

def _fetch_json_with_timeout(url: str, timeout: int = PROVIDER_TIMEOUT_SEC,
                              **kwargs: Any) -> dict[str, Any]:
    """
    Fetch JSON from *url* with a timeout.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.
        **kwargs: Extra arguments forwarded to ``requests.get()``
                  (e.g. ``params`` for query string).

    Returns:
        Parsed JSON response dict.

    Raises:
        ``requests.RequestException`` on HTTP error or timeout.

    Mirrors info.js fetchJsonWithTimeout().
    """
    resp = requests.get(url, timeout=timeout, **kwargs)
    resp.raise_for_status()
    return resp.json()


def _try_savenow_provider(
    base_url: str,
    target_url: str,
    format_type: str,
    api_key: str,
) -> dict[str, Any] | None:
    """
    Attempt to initiate a download via the SaveNow API at *base_url*.

    Args:
        base_url: One of PROXY_API_BASES, e.g. ``"https://p.savenow.to"``.
        target_url: The media URL to download (YouTube, SoundCloud, JioSaavn…).
        format_type: ``"flac"`` for audio, ``"mp4"`` or quality string for video.
        api_key: The ``VIDEO_DOWNLOAD_API_KEY``.

    Returns:
        The API response dict on success (contains ``progress_url`` etc.),
        or ``None`` if the provider is unavailable / returns an error.

    Mirrors info.js trySaveNowProvider().
    """
    params: dict[str, str] = {
        "copyright": "0",
        "allow_extended_duration": "1",
        "format": format_type,
        "url": target_url,
        "api": api_key,
        "add_info": "1",
    }
    full_url = f"{base_url.rstrip('/')}/ajax/download.php"
    try:
        data = _fetch_json_with_timeout(full_url, params=params, timeout=PROVIDER_TIMEOUT_SEC)
        if data.get("success") and data.get("progress_url"):
            return data
        logger.debug("SaveNow at %s returned failure: %s", base_url, data.get("message"))
        return None
    except requests.RequestException as exc:
        logger.debug("SaveNow at %s failed: %s", base_url, exc)
        return None


def _try_dubs_provider(
    target_url: str,
    format_type: str,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> str | None:
    """
    Attempt to download via the dubs.io alternative provider.

    This provider uses a two-step flow:
      1. ``POST /download-video`` → returns a ``progressId``
      2. Poll ``/status-video`` until ``finished`` is true

    Args:
        target_url: The media URL to download.
        format_type: Format string for the download.
        progress_callback: Optional callback for status updates.

    Returns:
        The final download URL on success, or ``None`` on failure.

    Mirrors info.js tryDubsProvider().
    """
    video_id = None
    match = re.search(r'(?:v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})', target_url)
    if match:
        video_id = match.group(1)

    if not video_id:
        logger.debug("dubs.io: could not extract video ID from %s", target_url)
        return None

    start_endpoint = config.DUBS_START_ENDPOINT or _DEFAULT_DUBS_START
    status_endpoint = config.DUBS_STATUS_ENDPOINT or _DEFAULT_DUBS_STATUS

    start_params: dict[str, str] = {
        "id": video_id,
        "format": format_type,
    }
    try:
        start_data = _fetch_json_with_timeout(
            start_endpoint, params=start_params, timeout=PROVIDER_TIMEOUT_SEC
        )
        if not start_data.get("success") or not start_data.get("progressId"):
            logger.debug("dubs.io start failed: %s", start_data.get("message"))
            return None

        progress_id = start_data["progressId"]

        for _ in range(MAX_POLLS):
            try:
                st = _fetch_json_with_timeout(
                    status_endpoint,
                    params={"id": progress_id},
                    timeout=20,
                )
            except requests.RequestException:
                time.sleep(POLL_INTERVAL_SEC)
                continue

            raw_progress = int(st.get("progress", 0))  # 0..1000 scale
            pct = min(raw_progress / 10, 100)

            if progress_callback:
                progress_callback({
                    "status": "downloading",
                    "progress": pct,
                    "eta": f"dubs.io {pct:.0f}%",
                    "speed": "Proxy API",
                })

            if st.get("finished") and st.get("downloadUrl"):
                return str(st["downloadUrl"])

            time.sleep(POLL_INTERVAL_SEC)

        logger.debug("dubs.io polling timed out")
        return None

    except requests.RequestException as exc:
        logger.debug("dubs.io provider failed: %s", exc)
        return None


def _poll_progress(
    progress_url: str,
    interval: int = POLL_INTERVAL_SEC,
    max_polls: int = MAX_POLLS,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> str | None:
    """
    Poll *progress_url* until the download is ready.

    Args:
        progress_url: URL returned by the SaveNow provider.
        interval: Seconds between polls.
        max_polls: Maximum number of poll attempts.
        progress_callback: Called with ``{"progress": pct, "eta": text, ...}``.

    Returns:
        The final download URL on success, or ``None`` on timeout/error.

    Mirrors info.js pollProgressUrl().
    """
    for _ in range(max_polls):
        try:
            data = _fetch_json_with_timeout(progress_url, timeout=15)
        except requests.RequestException:
            time.sleep(interval)
            continue

        raw_progress = int(data.get("progress", 0))  # 0..1000
        pct = min(raw_progress / 10, 100)
        text = data.get("text", "Processing")

        if progress_callback:
            progress_callback({
                "status": "downloading",
                "progress": pct,
                "eta": f"{text}…",
                "speed": "Proxy API",
            })

        # progress >= 1000 means complete (scale is 0-1000 with the SaveNow API)
        if raw_progress >= 1000 and data.get("download_url"):
            return str(data["download_url"])

        time.sleep(interval)

    return None


def download_with_proxy_fallback(
    target_url: str,
    format_type: str,
    api_key: str,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """
    Orchestrate proxy download with full fallback chain.

    1. Try SaveNow at each base URL in ``PROXY_API_BASES``
    2. If all SaveNow fail, try dubs.io alternative provider
    3. Return ``{success, download_url, file_path?, error?}``

    This function does NOT save files to disk — it returns the download URL.
    The caller is responsible for downloading the file and embedding metadata.

    Args:
        target_url: The media URL to download.
        format_type: ``"flac"`` for audio, quality/format for video.
        api_key: The ``VIDEO_DOWNLOAD_API_KEY``.
        progress_callback: Optional callback for status updates.

    Returns:
        Dict with keys:
        - ``success`` (bool)
        - ``download_url`` (str | None)
        - ``provider`` (str) — which provider served the download
        - ``error`` (str | None)
        - ``alternative_download_urls`` (list[str])
    """
    if progress_callback:
        progress_callback({
            "status": "downloading",
            "progress": 0,
            "eta": "Initiating proxy download…",
            "speed": "0 KB/s",
        })

    proxy_bases: list[str] = config.PROXY_API_BASES or _DEFAULT_PROXY_API_BASES

    # Filter to a single provider when PROXY_DOWNLOADER is set for testing.
    downloader_mode = (config.PROXY_DOWNLOADER or "").strip().lower()
    if downloader_mode == "proxy1":
        proxy_bases = [proxy_bases[0]] if proxy_bases else []
    elif downloader_mode == "proxy2":
        proxy_bases = [proxy_bases[1]] if len(proxy_bases) > 1 else []
    elif downloader_mode == "dubs":
        proxy_bases = []

    logger.info("PROXY_DOWNLOADER=%s, active bases: %s", downloader_mode or "all", proxy_bases or ["dubs.io"])

    last_result: dict[str, Any] | None = None
    for base_url in proxy_bases:
        if progress_callback:
            progress_callback({
                "status": "downloading",
                "progress": 0,
                "eta": f"Trying {base_url}…",
                "speed": "Proxy API",
            })

        last_result = _try_savenow_provider(base_url, target_url, format_type, api_key)
        if last_result and last_result.get("progress_url"):
            progress_url = str(last_result["progress_url"])
            download_url = _poll_progress(
                progress_url,
                progress_callback=progress_callback,
            )
            if download_url:
                alt_urls: list[str] = list(last_result.get("alternative_download_urls", []) or [])
                return {
                    "success": True,
                    "download_url": download_url,
                    "provider": f"savenow ({base_url})",
                    "error": None,
                    "alternative_download_urls": alt_urls,
                    "source_download_url": download_url,
                }

    if progress_callback:
        progress_callback({
            "status": "downloading",
            "progress": 0,
            "eta": "SaveNow failed, trying dubs.io…",
            "speed": "Proxy API",
        })

    dubs_url = _try_dubs_provider(target_url, format_type, progress_callback)
    if dubs_url:
        return {
            "success": True,
            "download_url": dubs_url,
            "provider": "dubs.io",
            "error": None,
            "alternative_download_urls": [],
            "source_download_url": dubs_url,
        }

    error_msg = "All proxy providers failed"
    if progress_callback:
        progress_callback({
            "status": "error",
            "progress": 0,
            "eta": "N/A",
            "speed": "0 KB/s",
            "error": error_msg,
        })

    return {
        "success": False,
        "download_url": None,
        "provider": "none",
        "error": error_msg,
        "alternative_download_urls": [],
    }
