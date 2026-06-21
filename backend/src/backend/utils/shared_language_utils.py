#!/usr/bin/env python3
"""
Shared Language Utilities
=========================
Centralized language code mappings and conversions for reuse across modules.

Used by:
- picard_fallback_enricher.py
- api_metadata_enricher.py
- Any module doing language detection/mapping
"""

# JioSaavn language names to standard English names
JIOSAAVN_LANG_MAP = {
    'english': 'English',
    'hindi': 'Hindi',
    'telugu': 'Telugu',
    'kannada': 'Kannada',
    'tamil': 'Tamil',
    'marathi': 'Marathi',
    'bengali': 'Bengali',
    'gujarati': 'Gujarati',
    'punjabi': 'Punjabi',
    'malayalam': 'Malayalam',
    'bhojpuri': 'Hindi',
    'sadri': 'Hindi',
    'urdu': 'Urdu',
    'odia': 'Odia',
    'assamese': 'Assamese',
}

# MusicBrainz ISO 639-3 language codes to standard English names
MUSICBRAINZ_LANG_MAP = {
    'eng': 'English',
    'hin': 'Hindi',
    'tel': 'Telugu',
    'kan': 'Kannada',
    'tam': 'Tamil',
    'mar': 'Marathi',
    'ben': 'Bengali',
    'guj': 'Gujarati',
    'pan': 'Punjabi',
    'mal': 'Malayalam',
    'urd': 'Urdu',
}

# ISO 639-1 two-letter codes to language names (for langdetect library)
ISO_639_1_LANG_MAP = {
    'en': 'English',
    'hi': 'Hindi',
    'bn': 'Bengali',
    'te': 'Telugu',
    'ta': 'Tamil',
    'pa': 'Punjabi',
    'gu': 'Gujarati',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'or': 'Odia',
    'ur': 'Urdu',
    'ar': 'Arabic',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'zh': 'Chinese',
    'ja': 'Japanese',
    'ko': 'Korean',
    'th': 'Thai',
    'vi': 'Vietnamese',
}


def map_jiosaavn_language(lang_name: str) -> str:
    """
    Convert JioSaavn language name to standard English name.
    
    Args:
        lang_name: Language name from JioSaavn API (e.g., 'english', 'hindi')
    
    Returns:
        Standard language name (e.g., 'English', 'Hindi'), or None if not found
    """
    if not lang_name:
        return None
    return JIOSAAVN_LANG_MAP.get(lang_name.lower(), None)


def map_musicbrainz_language(lang_code: str) -> str:
    """
    Convert MusicBrainz ISO 639-3 language code to standard English name.
    
    Args:
        lang_code: ISO 639-3 code from MusicBrainz (e.g., 'eng', 'hin')
    
    Returns:
        Standard language name (e.g., 'English', 'Hindi'), or None if not found
    """
    if not lang_code:
        return None
    return MUSICBRAINZ_LANG_MAP.get(lang_code.lower(), None)


def map_iso_639_1_language(code: str) -> str:
    """
    Convert ISO 639-1 two-letter code to language name.
    
    Args:
        code: Two-letter ISO 639-1 code (e.g., 'en', 'hi')
    
    Returns:
        Language name (e.g., 'English', 'Hindi'), or 'Unknown' if not found
    """
    if not code:
        return 'Unknown'
    return ISO_639_1_LANG_MAP.get(code.lower(), 'Unknown')


def get_all_language_codes() -> list:
    """Get list of all known language codes and names for reference."""
    return list(set(
        list(JIOSAAVN_LANG_MAP.values()) +
        list(MUSICBRAINZ_LANG_MAP.values()) +
        list(ISO_639_1_LANG_MAP.values())
    ))
