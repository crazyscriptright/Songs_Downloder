"""
Download deduplication utilities.

Provides canonical config hashing and duplicate detection for completed downloads.
"""
import hashlib
import json
import os
from typing import Any

from core import config
from core import state


# Fields from advanced_options that affect the output file
# Defaults match downloader.py:_build_cmd and download_with_spoflac
_CONFIG_DEFAULTS = {
    "audioFormat": "mp3",
    "audioQuality": "0",
    "keepVideo": False,
    "videoQuality": "1080",
    "videoFPS": "30",
    "videoFormat": "mkv",
    "embedThumbnail": True,
    "embedSubtitles": False,
    "addMetadata": True,
    "customArgs": "",
}


def _extract_relevant_config(advanced_options: dict[str, Any] | None) -> dict[str, Any]:
    """
    Extract and normalize config fields that affect output.

    Returns a dict with all relevant fields filled with defaults where missing.
    """
    if not advanced_options:
        return _CONFIG_DEFAULTS.copy()

    result = {}
    for key, default in _CONFIG_DEFAULTS.items():
        value = advanced_options.get(key, default)
        # Normalize types
        if isinstance(value, bool):
            result[key] = value
        elif isinstance(value, (int, float)):
            result[key] = str(value)
        else:
            result[key] = str(value).strip() if value else default
    return result


def canonical_config_hash(advanced_options: dict[str, Any] | None, thumbnail: str | None) -> str:
    """
    Create a stable hash representing the download configuration.

    Includes all advanced_options fields that affect output + thumbnail URL.
    Returns first 16 chars of SHA256 for compact storage/comparison.
    """
    config = _extract_relevant_config(advanced_options)
    config["thumbnail"] = thumbnail if thumbnail else ""

    # Sort keys for deterministic JSON
    canonical_json = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:16]


def _file_exists_on_disk(download_id: str, filename: str) -> bool:
    """Check if the completed download file still exists on disk and has content."""
    file_path = os.path.join(config.DOWNLOAD_FOLDER, download_id, filename)
    return os.path.isfile(file_path) and os.path.getsize(file_path) > 0


def find_duplicate_download(
    url: str,
    advanced_options: dict[str, Any] | None,
    thumbnail: str | None,
) -> str | None:
    """
    Search for an existing completed download with the same URL and config.

    Returns the download_id of the most recent match, or None if not found.
    Only considers entries with status="complete" and existing file on disk.
    """
    config_hash = canonical_config_hash(advanced_options, thumbnail)

    candidates: list[tuple[str, str]] = []  # (download_id, completed_at)

    for did, entry in state.download_status.items():
        if entry.get("status") != "complete":
            continue
        if entry.get("url") != url:
            continue

        entry_hash = entry.get("config_hash")
        if not entry_hash:
            # Backward compat: compute hash from stored advanced_options
            entry_adv = entry.get("advanced_options")
            entry_thumb = entry.get("thumbnail")
            entry_hash = canonical_config_hash(entry_adv, entry_thumb)

        if entry_hash != config_hash:
            continue

        filename = entry.get("file")
        if not filename or not _file_exists_on_disk(did, filename):
            continue

        completed_at = entry.get("completed_at") or entry.get("timestamp") or ""
        candidates.append((did, completed_at))

    if not candidates:
        return None

    # Return most recent by completion timestamp
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]