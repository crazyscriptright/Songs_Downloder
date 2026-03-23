#!/usr/bin/env python3
r"""
API Metadata Enricher (Refactored)
===================================
Unified metadata enrichment for API download routes using shared utilities.

Integrates:
- Multi-phase language detection (JioSaavn → MusicBrainz → langdetect → metadata)
- Automatic lyrics fetching with fallbacks
- Non-Latin script romanization (Devanagari/Telugu/Tamil → Latin)
- Seamless embedding during downloads

Used by:
- routes/download.py (general downloads)
- routes/flac_download.py (FLAC conversion)
- services/downloader.py (background downloads)

Usage:
    from services.api_metadata_enricher import enrich_for_download
    
    enriched = enrich_for_download(
        title="Jo Tum Mere Ho",
        artist="Anuv Jain",
        album="",
        filename="Jo Tum Mere Ho.mp3",
        duration_ms=300000
    )
    # Returns: enriched dict with language, lyrics, featured_artists, etc.
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from langdetect import detect, detect_langs, LangDetectException
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False

from spoflac_core.modules.platform_metadata import (
    _fetch_lyrics_with_fallbacks,
    _extract_featured_artists,
    _detect_version_type,
    _extract_tags_from_text,
)
from spoflac_core.modules.url_resolver import _romanize_lrc_lyrics, _detect_script
from utils.shared_language_utils import map_jiosaavn_language, map_iso_639_1_language, map_musicbrainz_language
from utils.shared_api_client import query_jiosaavn_track, query_jiosaavn_album, query_musicbrainz_recording_language


# ============================================================================
# PHASE 1: EXTERNAL APIs (JioSaavn, MusicBrainz) - Using Shared Client
# ============================================================================

def _detect_language_jiosaavn(title: str, artist: str) -> Dict[str, Any]:
    """Query JioSaavn API for language metadata (via shared client)."""
    result = query_jiosaavn_track(title, artist)
    if result and result['language']:
        return {
            'language': result['language'],
            'confidence': result['confidence'],
            'method': 'jiosaavn_api'
        }
    return {'language': None, 'confidence': 0.0, 'method': 'jiosaavn_failed'}


def _detect_language_jiosaavn_album(album: str, artist: str) -> Dict[str, Any]:
    """JioSaavn album search (via shared client)."""
    result = query_jiosaavn_album(album, artist)
    if result and result['language']:
        return {
            'language': result['language'],
            'confidence': result['confidence'],
            'method': 'jiosaavn_album'
        }
    return {'language': None, 'confidence': 0.0, 'method': 'jiosaavn_album_failed'}


def _detect_language_musicbrainz(title: str, artist: str) -> Dict[str, Any]:
    """Query MusicBrainz API for language metadata (via shared client)."""
    lang = query_musicbrainz_recording_language(title, artist)
    if lang:
        return {
            'language': lang,
            'confidence': 0.85,
            'method': 'musicbrainz'
        }
    return {'language': None, 'confidence': 0.0, 'method': 'musicbrainz_failed'}


# ============================================================================
# PHASE 2: LYRICS-BASED DETECTION
# ============================================================================

def _detect_language_from_keywords(text: str) -> Optional[str]:
    """Detect language from transliterated text using language-specific keywords."""
    if not text or not HAS_LANGDETECT:
        return None
    
    text_lower = text.lower()
    
    hindi_keywords = {
        'ho', 'hai', 'mere', 'tum', 'jo', 'aur', 'ka', 'ke', 'kya', 'nahi',
        'main', 'meri', 'mera', 'tera', 'teri', 'tere', 'jab', 'kab', 'kaise',
        'pyar', 'prem', 'dil', 'bhay', 'bhool', 'raat', 'din', 'kal', 'aaj'
    }
    
    keywords_found = {'Hindi': sum(1 for kw in hindi_keywords if kw in text_lower)}
    
    if keywords_found['Hindi'] > 0:
        return 'Hindi'
    
    return None


def _detect_language_from_lyrics(lyrics: str) -> Dict[str, Any]:
    """Detect language from lyrics using langdetect and keyword matching."""
    if not lyrics or not HAS_LANGDETECT:
        return {'language': None, 'confidence': 0.0}
    
    # Remove timestamps
    lines = []
    for line in lyrics.split('\n'):
        clean_line = re.sub(r'\[\d{1,2}:\d{2}(?:\.\d+)?\]', '', line).strip()
        if clean_line and len(clean_line) > 2:
            lines.append(clean_line)
    
    if not lines:
        return {'language': None, 'confidence': 0.0}
    
    detected_langs = {}
    
    for line in lines:
        try:
            detected_probs = detect_langs(line)
            if detected_probs and detected_probs[0].prob >= 0.7:
                lang_code = detected_probs[0].lang
                lang_name = map_iso_639_1_language(lang_code)
                detected_langs[lang_name] = detected_langs.get(lang_name, 0) + 1
            else:
                keyword_lang = _detect_language_from_keywords(line)
                if keyword_lang:
                    detected_langs[keyword_lang] = detected_langs.get(keyword_lang, 0) + 1
                else:
                    detected_langs['English'] = detected_langs.get('English', 0) + 1
        except LangDetectException:
            keyword_lang = _detect_language_from_keywords(line)
            if keyword_lang:
                detected_langs[keyword_lang] = detected_langs.get(keyword_lang, 0) + 1
            else:
                detected_langs['English'] = detected_langs.get('English', 0) + 1
    
    if detected_langs:
        total = sum(detected_langs.values())
        primary = max(detected_langs, key=detected_langs.get)
        return {
            'language': primary,
            'confidence': detected_langs[primary] / total if total > 0 else 0.0
        }
    
    return {'language': None, 'confidence': 0.0}


# ============================================================================
# PHASE 4: METADATA-BASED DETECTION
# ============================================================================

def _detect_language_from_metadata_patterns(title: str, artist: str, filename: str) -> Dict[str, Any]:
    """Detect language from filename, title, and artist patterns."""
    text = f"{filename} {title} {artist}".lower()
    
    patterns = {
        'Hindi': [r'\b(bollywood|hindi\s+song|hindustani)\b'],
        'Telugu': [r'\b(tollywood|telugu\s+song)\b'],
        'Tamil': [r'\b(kollywood|tamil\s+song)\b'],
        'Kannada': [r'\b(sandalwood|kannada\s+song)\b'],
        'Punjabi': [r'\b(punjabi|pollywood)\b'],
        'Marathi': [r'\b(marathi)\b'],
        'Bengali': [r'\b(bengali|tolly|bangla)\b'],
        'Malayalam': [r'\b(malayalam|mollywood)\b'],
    }
    
    for lang, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text):
                return {'language': lang, 'confidence': 0.65}
    
    artist_map = {
        'hindi': ['sonu nigam', 'arijit singh', 'shreya ghoshal', 'kumar sanu', 'udit narayan'],
        'telugu': ['sp balasubrahmanyam', 'ghantasala', 'p susheela'],
        'tamil': ['ar rahman', 'sid sriram', 'yuvan shankar'],
        'kannada': ['puneeth rajkumar', 'kiccha sudeep'],
        'punjabi': ['diljit dosanjh', 'gurdas maan', 'sidhu moose wala'],
        'marathi': ['asha bhosle', 'suresh wadkar']
    }
    
    artist_lower = artist.lower()
    for lang, artists in artist_map.items():
        if any(famous_artist in artist_lower for famous_artist in artists):
            return {'language': lang.title(), 'confidence': 0.72}
    
    return {'language': None, 'confidence': 0.0}


# ============================================================================
# MASTER: MULTI-PHASE DETECTION WITH FALLBACKS
# ============================================================================

def detect_language_with_phases(
    title: str = '',
    artist: str = '',
    album: str = '',
    filename: str = '',
    lyrics: str = ''
) -> Dict[str, Any]:
    """
    Multi-phase language detection with intelligent fallback chain.
    
    PHASE 1: External APIs (JioSaavn, MusicBrainz)
    PHASE 2: Lyrics-based (langdetect + keywords)
    PHASE 4: Metadata patterns & artist heuristics
    
    Returns:
        {
            'language': str,
            'confidence': float,
            'detected_from': str  # 'api', 'lyrics', 'metadata', or 'default'
        }
    """
    best_result = None
    best_confidence = 0.0
    
    # PHASE 1: Try JioSaavn API
    if title and artist:
        result = _detect_language_jiosaavn(title, artist)
        if result['language'] and result['confidence'] > best_confidence:
            best_result = result
            best_confidence = result['confidence']
            if best_confidence >= 0.9:
                return {
                    'language': result['language'],
                    'confidence': result['confidence'],
                    'detected_from': 'api'
                }
    
    # PHASE 1B: Try JioSaavn Album Search
    if album and artist and best_confidence < 0.85:
        result = _detect_language_jiosaavn_album(album, artist)
        if result['language'] and result['confidence'] > best_confidence:
            best_result = result
            best_confidence = result['confidence']
    
    # PHASE 1C: Try MusicBrainz
    if title and best_confidence < 0.85:
        result = _detect_language_musicbrainz(title, artist)
        if result['language'] and result['confidence'] > best_confidence:
            best_result = result
            best_confidence = result['confidence']
    
    # PHASE 2: Lyrics-based detection
    if lyrics and best_confidence < 0.75:
        result = _detect_language_from_lyrics(lyrics)
        if result['language'] and result['confidence'] > best_confidence:
            best_result = result
            best_confidence = result['confidence']
            best_result['detected_from'] = 'lyrics'
    
    # PHASE 4: Metadata-based detection
    if best_confidence < 0.65:
        result = _detect_language_from_metadata_patterns(title or '', artist or '', filename or '')
        if result['language'] and result['confidence'] > best_confidence:
            best_result = result
            best_confidence = result['confidence']
            best_result['detected_from'] = 'metadata'
    
    # If we found something, return it
    if best_result and best_confidence > 0:
        if 'detected_from' not in best_result:
            best_result['detected_from'] = 'api'
        return best_result
    
    # Fallback to English
    return {
        'language': 'English',
        'confidence': 0.0,
        'detected_from': 'default'
    }


# ============================================================================
# MAIN API: UNIFIED ENRICHMENT
# ============================================================================

def enrich_for_download(
    title: str,
    artist: str,
    album: str = '',
    filename: str = '',
    duration_ms: int = 0,
    existing_metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Enrich metadata for a downloaded song.
    
    This is called AFTER the file is downloaded but BEFORE it's returned to the user.
    It enriches the track_metadata dict with:
    - Detected language (multi-phase)
    - Fetched lyrics (with romanization)
    - Featured artists
    - Version type
    - Tags
    
    Args:
        title: Track title
        artist: Track artist
        album: Album name
        filename: Filename (for pattern detection)
        duration_ms: Track duration in milliseconds
        existing_metadata: Dict of existing metadata to preserve
    
    Returns:
        Dict with enriched metadata ready to embed
    """
    if existing_metadata is None:
        existing_metadata = {}
    
    enriched = {
        **existing_metadata,
        'featured_artists': [],
        'version_type': 'original',
        'tags': [],
        'language': 'English',
        'lyrics-eng': None,
    }

    # HARDENING: ensure album_artist exists for downstream embedding
    existing_album_artist = str(enriched.get('album_artist', '')).strip()
    if not existing_album_artist and artist:
        primary_artist = re.split(r',|&|\bfeat\.?\b|\bft\.?\b|\bwith\b', artist, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        if primary_artist:
            enriched['album_artist'] = primary_artist
    
    # Clean title to remove featured artists markers for searching
    clean_title, featured_artists = _extract_featured_artists(title)
    if featured_artists:
        enriched['featured_artists'] = featured_artists
    
    # Detect version type
    version_type = _detect_version_type(title, album)
    enriched['version_type'] = version_type
    
    # Extract tags
    tags = _extract_tags_from_text(f"{title} {album}")
    if tags:
        enriched['tags'] = list(dict.fromkeys(tags))
    
    # Fetch lyrics
    try:
        lyrics = _fetch_lyrics_with_fallbacks(
            title=clean_title or title,
            artist=artist,
            album=album,
            duration_ms=duration_ms,
            platform='local'
        )
        
        # Detect language using multi-phase approach
        if lyrics:
            lang_result = detect_language_with_phases(
                title=clean_title or title,
                artist=artist,
                album=album,
                filename=filename,
                lyrics=lyrics
            )
            
            # Romanize non-Latin scripts
            lyrics = _romanize_lrc_lyrics(lyrics)
            enriched['lyrics-eng'] = lyrics
        else:
            # No lyrics, detect language from metadata only
            lang_result = detect_language_with_phases(
                title=clean_title or title,
                artist=artist,
                album=album,
                filename=filename,
                lyrics=''
            )
        
        enriched['language'] = lang_result['language']
        enriched['language_detected_from'] = lang_result.get('detected_from', 'api')
        enriched['language_confidence'] = lang_result.get('confidence', 0.0)
    
    except Exception as e:
        # On any error, just use English as default
        enriched['language'] = 'English'
        enriched['language_detected_from'] = 'default'
        enriched['language_confidence'] = 0.0
    
    return enriched


def enrich_track_metadata(track_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function: enrich a complete track_metadata dict.
    
    Used when you already have a track_metadata dict from URL resolution.
    
    Args:
        track_metadata: Dict with title, artist, album, etc.
    
    Returns:
        Updated track_metadata dict with language, lyrics, featured_artists, etc.
    """
    enriched = enrich_for_download(
        title=track_metadata.get('title', ''),
        artist=track_metadata.get('artist', ''),
        album=track_metadata.get('album', ''),
        filename=track_metadata.get('filename', ''),
        duration_ms=track_metadata.get('duration_ms', 0),
        existing_metadata=track_metadata
    )
    return enriched
