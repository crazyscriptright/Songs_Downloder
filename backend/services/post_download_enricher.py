"""
Shared post-download enrichment service.

Runs two steps for a downloaded audio file:
1) Metadata enrichment from enrich_metadata.py
2) Artwork fix/fill from fix_album_art.py

All operations are best-effort and never raise to callers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".mp4", ".aac", ".wav"}


def _derive_title_artist_from_stem(path: Path) -> tuple[str, str]:
    stem = path.stem.strip()
    if " - " in stem:
        artist, title = stem.split(" - ", 1)
        return title.strip(), artist.strip()
    return stem, ""


def run_post_download_enrichment(file_path: str | Path, metadata_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Enrich metadata and fix/fill album art for a downloaded audio file.

    Returns diagnostic result dict and never raises exceptions.
    """
    path = Path(file_path)

    result: dict[str, Any] = {
        "ran": False,
        "metadata_enriched": False,
        "artwork_updated": False,
        "errors": [],
        "file": str(path),
        "language": None,
        "detection_method": None,
    }

    if not path.exists():
        result["errors"].append("file_not_found")
        return result

    if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        result["errors"].append("unsupported_extension")
        return result

    result["ran"] = True

    try:
        from enrich_metadata import read_existing_metadata, enrich_metadata as build_enriched, update_file_metadata

        existing_metadata = read_existing_metadata(path)

        context = metadata_context or {}
        fallback_title, fallback_artist = _derive_title_artist_from_stem(path)

        if not existing_metadata.get("title"):
            existing_metadata["title"] = (context.get("title") or fallback_title or "").strip()
        if not existing_metadata.get("artist"):
            existing_metadata["artist"] = (context.get("artist") or fallback_artist or "").strip()
        if not existing_metadata.get("album"):
            existing_metadata["album"] = (context.get("album") or "").strip()

        enriched_metadata = build_enriched(path, existing_metadata)
        result["metadata_enriched"] = bool(update_file_metadata(path, enriched_metadata))
        result["language"] = enriched_metadata.get("language")
        result["detection_method"] = enriched_metadata.get("detection_method")
    except Exception as exc:
        result["errors"].append(f"metadata_enrichment_failed: {exc}")

    try:
        from fix_album_art import (
            _get_tag,
            embed_artwork_to_file,
            fetch_artwork_from_apis,
            get_artwork_from_file,
            is_square_artwork,
            resize_artwork_to_square,
        )

        artwork_bytes, _ = get_artwork_from_file(path)
        needs_artwork = (not artwork_bytes) or (not is_square_artwork(artwork_bytes, tolerance=0.05))

        if needs_artwork:
            title = _get_tag(path, "title") or path.stem
            artist = _get_tag(path, "artist") or ""
            album = _get_tag(path, "album") or ""

            fresh_artwork = fetch_artwork_from_apis(title=title, artist=artist, album=album)
            if fresh_artwork:
                square_artwork = resize_artwork_to_square(fresh_artwork, target_size=1080)
                if square_artwork:
                    result["artwork_updated"] = bool(embed_artwork_to_file(path, square_artwork))
    except Exception as exc:
        result["errors"].append(f"artwork_update_failed: {exc}")

    if result["errors"]:
        logger.warning("Post-download enrichment completed with warnings for %s: %s", path.name, result["errors"])

    return result
