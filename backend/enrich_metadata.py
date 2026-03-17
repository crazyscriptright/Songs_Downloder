#!/usr/bin/env python3
r"""
Smart Metadata Enrichment Tool

Takes a single audio file OR an entire folder and enriches it with more metadata based on existing tags:
- Extracts featured artists from title (feat., ft., featuring)
- Detects version type (remix, live, acoustic, cover, etc.)
- Finds genre/mood tags from title and descriptors
- Fetches lyrics with fallback chain (converts non-Latin to Latin)
- Updates ISRC, release date, and other fields
- Preserves all existing good metadata (never overwrites with "Unknown")

Usage:
    # Single file with confirmation:
    python enrich_metadata.py "B:\music\All\Sahara.mp3"
    
    # Single file with auto-update:
    python enrich_metadata.py "B:\music\All\Sahara.mp3" -y
    
    # Entire folder with confirmation:
    python enrich_metadata.py "B:\music\All"
    
    # Entire folder with auto-update:
    python enrich_metadata.py "B:\music\All" -y
    
    # Test with limited files:
    python enrich_metadata.py "B:\music\All" --limit 10 -y
    
    # Resume from file 201 (skip first 200 files):
    python enrich_metadata.py "B:\music\All" --skip 200 -y
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import json
from datetime import datetime
import subprocess
import re
import time
from langdetect import detect, detect_langs, LangDetectException

try:
    import requests
except ImportError:
    requests = None

sys.path.insert(0, str(Path(__file__).parent))

from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.id3 import ID3

from spoflac_core.modules.platform_metadata import (
    _fetch_lyrics_with_fallbacks,
    _extract_featured_artists,
    _detect_version_type,
    _extract_tags_from_text,
)
from spoflac_core.modules.metadata import embed_metadata, has_timestamps
from spoflac_core.modules.url_resolver import _romanize_lrc_lyrics, _detect_script

# Import Picard fallback enricher (optional)
try:
    from picard_fallback_enricher import run_picard_fallback_enrichment, install_requirements as check_picard_requirements
    PICARD_AVAILABLE = check_picard_requirements()
except ImportError:
    PICARD_AVAILABLE = False
    logger.warning("⚠️  Picard fallback enricher not available - install with: pip install musicbrainzngs acoustid")


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def detect_language(text: str) -> Dict[str, Any]:
    """
    Detect language from text using HYBRID approach:
    1. BEST: Check for non-Latin scripts first (Devanagari/Telugu/Tamil/etc.)
       → If found, return that language with high confidence
    2. FALLBACK: Use per-line langdetect + keyword analysis
       → For English/Spanish/French/etc.
    
    This works excellently for Indian regional languages (Hindi/Telugu/Tamil/Kannada/etc.)
    and international languages.
    
    Returns:
        {
            'primary_language': str,  # Most common language (e.g., 'Hindi')
            'all_languages': list,     # All detected languages (e.g., ['Hindi', 'English'])
            'language_distribution': dict  # Percentage breakdown (e.g., {'Hindi': 85, 'English': 15})
        }
    """
    if not text or not text.strip():
        return {
            'primary_language': 'English',
            'all_languages': ['English'],
            'language_distribution': {'English': 100}
        }
    
    # Map scripts to languages
    script_to_language = {
        'Devanagari': 'Hindi',
        'Bengali': 'Bengali',
        'Gurmukhi': 'Punjabi',
        'Gujarati': 'Gujarati',
        'Oriya': 'Odia',
        'Tamil': 'Tamil',
        'Telugu': 'Telugu',
        'Kannada': 'Kannada',
        'Malayalam': 'Malayalam',
        'Thai': 'Thai',
        'Lao': 'Lao',
        'Tibetan': 'Tibetan',
        'Myanmar': 'Burmese',
        'Khmer': 'Khmer',
        'Japanese': 'Japanese',
        'Chinese': 'Chinese',
        'Arabic': 'Arabic',
        'Hebrew': 'Hebrew',
    }
    
    # =================================================================
    # STEP 1: CHECK FOR NON-LATIN SCRIPTS (Most reliable!)
    # =================================================================
    script_counts = {}
    for line in text.split('\n'):
        # Remove timestamps first
        clean_line = re.sub(r'\[\d{1,2}:\d{2}(?:\.\d+)?\]', '', line).strip()
        if clean_line and len(clean_line) > 2:
            script = _detect_script(clean_line)
            if script and script != 'Unknown':
                script_counts[script] = script_counts.get(script, 0) + 1
    
    # If we found a strong script signal (appears in lyrics), use it!
    if script_counts:
        # Most common script
        primary_script = max(script_counts, key=script_counts.get)
        if primary_script in script_to_language:
            lang = script_to_language[primary_script]
            return {
                'primary_language': lang,
                'all_languages': [lang],
                'language_distribution': {lang: 100},
                'detection_method': 'script'
            }
    
    # =================================================================
    # STEP 2: FALLBACK TO LANGDETECT + KEYWORDS (for Latin-based text)
    # =================================================================
    # Remove timestamps from LRC lyrics for analysis
    lines = []
    for line in text.split('\n'):
        # Remove [mm:ss.xx] or [mm:ss] timestamps
        clean_line = re.sub(r'\[\d{1,2}:\d{2}(?:\.\d+)?\]', '', line).strip()
        if clean_line and len(clean_line) > 2:  # Skip very short lines
            lines.append(clean_line)
    
    if not lines:
        return {
            'primary_language': 'English',
            'all_languages': ['English'],
            'language_distribution': {'English': 100},
            'detection_method': 'default'
        }
    
    # Detect language for each line
    detected_langs = {}
    
    for line in lines:
        try:
            # Try langdetect first (most reliable for non-Latin scripts)
            detected_probs = detect_langs(line)
            
            # Take the language with highest probability if >= 0.7 (70% confidence)
            if detected_probs and detected_probs[0].prob >= 0.7:
                lang_code = detected_probs[0].lang
                # Map ISO 639-1 codes to full language names
                lang_name = _map_language_code(lang_code)
                detected_langs[lang_name] = detected_langs.get(lang_name, 0) + 1
            else:
                # If confidence too low, try keyword-based detection
                keyword_lang = detect_language_from_keywords(line)
                if keyword_lang:
                    detected_langs[keyword_lang] = detected_langs.get(keyword_lang, 0) + 1
                else:
                    # Default to English for low-confidence cases
                    detected_langs['English'] = detected_langs.get('English', 0) + 1
        
        except LangDetectException:
            # If langdetect fails completely, try keywords
            keyword_lang = detect_language_from_keywords(line)
            if keyword_lang:
                detected_langs[keyword_lang] = detected_langs.get(keyword_lang, 0) + 1
            else:
                detected_langs['English'] = detected_langs.get('English', 0) + 1
    
    # Calculate distribution percentages
    total_lines = sum(detected_langs.values())
    language_distribution = {
        lang: int((count / total_lines) * 100)
        for lang, count in sorted(detected_langs.items(), key=lambda x: x[1], reverse=True)
    }
    
    # Primary language is the most common
    primary_language = max(detected_langs, key=detected_langs.get)
    all_languages = list(language_distribution.keys())
    
    return {
        'primary_language': primary_language,
        'all_languages': all_languages,
        'language_distribution': language_distribution,
        'detection_method': 'langdetect'
    }


def _map_language_code(code: str) -> str:
    """
    Convert ISO 639-1 language codes to full language names.
    """
    code_to_lang = {
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
    return code_to_lang.get(code, 'Unknown')


def detect_language_from_keywords(text: str) -> Optional[str]:
    """
    Detect language from transliterated text using language-specific keywords.
    
    Useful for transliterated titles like "Jo Tum Mere Ho" (Hindi in Latin chars).
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Hindi keywords (common Hindustani words in transliteration)
    hindi_keywords = {
        'ho', 'hai', 'hao', 'mere', 'tum', 'jo', 'aur', 'ka', 'ke', 'kya', 'nahi', 'naan',
        'main', 'meri', 'mera', 'tera', 'teri', 'tere', 'iska', 'unka', 'unke', 'inke',
        'jab', 'jisse', 'kab', 'kaise', 'kyun', 'kaun', 'kya', 'dhun', 'gana', 'gaana',
        'pyar', 'prem', 'dil', 'dila', 'dile', 'dilli', 'bhaya', 'bhay', 'bhool', 'bhoolna',
        'aap', 'aapka', 'aapke', 'hum', 'humka', 'hamara', 'hamari', 'hamare', 'hamne',
        'raat', 'raati', 'din', 'dina', 'kal', 'aaj', 'aajkal', 'aacha', 'accha', 'badshah',
        'badha', 'badi', 'bada', 'badi', 'chalti', 'chaldi', 'chal', 'chalna', 'chale',
        'dekha', 'dekhi', 'dekho', 'dil', 'dila', 'dilse', 'dilka', 'dilke', 'dole',
        'dol', 'dulhania', 'dukh', 'dukha', 'dupatta', 'dharm', 'dhol', 'dharma',
        'khuda', 'khush', 'khushi', 'khud', 'khudar', 'khusha', 'khuld', 'kumud',
        'lagi', 'lagi', 'lag', 'lagta', 'lagti', 'lagba', 'laag', 'laagta', 'lag',
        'nadi', 'nada', 'naam', 'namrata', 'naari', 'nari', 'nakhra', 'nahal',
        'pagi', 'pag', 'pagdi', 'pagla', 'par', 'para', 'pari', 'parivar', 'parivartan',
        'riddhi', 'radha', 'ragini', 'raag', 'ragi', 'ragga', 'rahta', 'rahti',
        'saccha', 'sachai', 'sach', 'sadhu', 'saathi', 'sadhe', 'sadhai', 'sadhe',
        'taj', 'taja', 'taji', 'tabahi', 'table', 'talab', 'talak', 'talai', 'talash',
        'udit', 'udita', 'udai', 'udal', 'uda', 'udao', 'ujala', 'ujali',
        'vaat', 'vaata', 'vaati', 'vahi', 'vah', 'vaah', 'vaahan', 'vaand', 'vaar',
        'yeh', 'yeha', 'yehi', 'yahan', 'yahaan', 'yahi', 'yad', 'yada', 'yadi', 'yadi',
        'zara', 'zari', 'zarai', 'zarif', 'zarre', 'zastha', 'zau', 'zauga', 'zaua'
    }
    
    # Bengali keywords
    bengali_keywords = {
        'ami', 'amar', 'amra', 'aapni', 'aap', 'tumi', 'tumra', 'sei', 'tar', 'taar',
        'ei', 'er', 'je', 'jei', 'jar', 'jaa', 'jab', 'jokhon', 'tahole', 'kinto',
        'habe', 'hai', 'che', 'chilo', 'holo', 'hobey', 'hobe', 'hoye', 'hoilo',
        'prem', 'bhalobaschi', 'bhalobasi', 'bhay', 'dukh', 'sukh', 'khusi', 'khushi',
        'mon', 'mone', 'dil', 'hridoy', 'praan', 'pran', 'shakti', 'bal', 'bol',
        'naam', 'namer', 'rupso', 'gunsidhanto', 'guno', 'dosha', 'tomar', 'tomara'
    }
    
    # Tamil keywords
    tamil_keywords = {
        'naan', 'nai', 'niir', 'nila', 'nilaa', 'un', 'unai', 'ini', 'ini', 'ithu',
        'athu', 'ivai', 'avai', 'ellai', 'enru', 'yanru', 'eppadi', 'eppo', 'engal',
        'vaa', 'vaai', 'poi', 'paar', 'paarum', 'kathai', 'kathala', 'kalai', 'kalaiye',
        'ceit', 'ceiyai', 'ceiyon', 'tamilai', 'tamil', 'tamizhaga', 'tamizh'
    }
    
    # Telugu keywords
    telugu_keywords = {
        'nenu', 'meeru', 'adi', 'ade', 'aite', 'ayana', 'aama', 'yem', 'yemi', 'yela',
        'eppudi', 'epudu', 'enduku', 'emiti', 'enka', 'emuka', 'ani', 'anedi',
        'premam', 'pream', 'premalanni', 'premata', 'parama', 'paramanatham'
    }
    
    # Punjabi keywords
    punjabi_keywords = {
        'main', 'mera', 'meri', 'mere', 'tusi', 'tera', 'teri', 'tere', 'tussi',
        'eh', 'oh', 'ohi', 'uu', 've', 'vei', 'ki', 'kia', 'kardi', 'kardia',
        'haan', 'hai', 'ho', 'ae', 'si', 'si', 'hoya', 'hoye', 'hove', 'hovea'
    }
    
    # Count keyword matches
    keywords_found = {
        'Hindi': sum(1 for kw in hindi_keywords if kw in text_lower),
        'Bengali': sum(1 for kw in bengali_keywords if kw in text_lower),
        'Tamil': sum(1 for kw in tamil_keywords if kw in text_lower),
        'Telugu': sum(1 for kw in telugu_keywords if kw in text_lower),
        'Punjabi': sum(1 for kw in punjabi_keywords if kw in text_lower),
    }
    
    # Return language with most keyword matches (if any found)
    if any(keywords_found.values()):
        best_match = max(keywords_found, key=keywords_found.get)
        if keywords_found[best_match] > 0:
            return best_match
    
    return None


# =================================================================
# PHASE 1: EXTERNAL APIS (JioSaavn, MusicBrainz)
# =================================================================

def _detect_language_jiosaavn(title: str, artist: str) -> Dict[str, Any]:
    """
    Query JioSaavn API for language metadata.
    Most accurate for Indian regional music.
    """
    if not requests or not title:
        return {'language': None, 'confidence': 0.0, 'method': 'jiosaavn_failed'}
    
    try:
        url = "https://www.jiosaavn.com/api.php"
        params = {
            'p': 1,
            'q': f"{title} {artist}" if artist else title,
            '_format': 'json',
            '_marker': 0,
            'api_version': 4,
            'ctx': 'wap6dot0',
            'n': 5,
            '__call': 'search.getResults'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                first_result = data['results'][0]
                if 'language' in first_result:
                    lang = first_result['language'].lower()
                    lang_map = {
                        'english': 'English', 'hindi': 'Hindi', 'telugu': 'Telugu',
                        'kannada': 'Kannada', 'tamil': 'Tamil', 'marathi': 'Marathi',
                        'bengali': 'Bengali', 'gujarati': 'Gujarati', 'punjabi': 'Punjabi',
                        'malayalam': 'Malayalam', 'bhojpuri': 'Hindi', 'sadri': 'Hindi',
                        'urdu': 'Urdu', 'odia': 'Odia', 'assamese': 'Assamese'
                    }
                    detected_lang = lang_map.get(lang, 'Unknown')
                    return {
                        'language': detected_lang,
                        'confidence': 0.95,
                        'method': 'jiosaavn_api',
                        'title': first_result.get('title', '')
                    }
        
        return {'language': None, 'confidence': 0.0, 'method': 'jiosaavn_no_results'}
    except Exception as e:
        logger.debug(f"JioSaavn API failed: {e}")
        return {'language': None, 'confidence': 0.0, 'method': f'jiosaavn_error_{str(e)[:20]}'}


def _detect_language_jiosaavn_album(album: str, artist: str) -> Dict[str, Any]:
    """
    JioSaavn album search (alternate method).
    """
    if not requests or not album:
        return {'language': None, 'confidence': 0.0, 'method': 'jiosaavn_album_failed'}
    
    try:
        url = "https://www.jiosaavn.com/api.php"
        params = {
            'p': 1,
            'q': f"{album} {artist}" if artist else album,
            '_format': 'json',
            '_marker': 0,
            'api_version': 4,
            'ctx': 'wap6dot0',
            'n': 3,
            '__call': 'search.getAlbumResults'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                first_result = data['results'][0]
                if 'language' in first_result:
                    lang = first_result['language'].lower()
                    lang_map = {
                        'english': 'English', 'hindi': 'Hindi', 'telugu': 'Telugu',
                        'kannada': 'Kannada', 'tamil': 'Tamil', 'marathi': 'Marathi',
                        'bengali': 'Bengali', 'gujarati': 'Gujarati', 'punjabi': 'Punjabi',
                        'malayalam': 'Malayalam'
                    }
                    detected_lang = lang_map.get(lang, 'Unknown')
                    return {
                        'language': detected_lang,
                        'confidence': 0.90,
                        'method': 'jiosaavn_album',
                        'album': first_result.get('title', '')
                    }
        
        return {'language': None, 'confidence': 0.0, 'method': 'jiosaavn_album_no_results'}
    except Exception as e:
        logger.debug(f"JioSaavn album search failed: {e}")
        return {'language': None, 'confidence': 0.0, 'method': f'jiosaavn_album_error'}


def _detect_language_musicbrainz(title: str, artist: str) -> Dict[str, Any]:
    """
    Query MusicBrainz API for language metadata.
    Free, no rate limit. Has language tags in recordings.
    """
    if not requests or not title:
        return {'language': None, 'confidence': 0.0, 'method': 'musicbrainz_failed'}
    
    try:
        headers = {
            'User-Agent': 'LanguageDetectionApp/1.0 (contact@example.com)'
        }
        
        url = "https://musicbrainz.org/ws/2/recording/"
        params = {
            'query': f'recording:"{title}"' + (f' AND artist:"{artist}"' if artist else ''),
            'fmt': 'json',
            'limit': 3
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=8)
        time.sleep(0.3)  # MusicBrainz rate limit
        
        if response.status_code == 200:
            data = response.json()
            if 'recordings' in data and len(data['recordings']) > 0:
                for recording in data['recordings'][:2]:
                    if 'work-relation-list' in recording:
                        for relation in recording['work-relation-list']:
                            work = relation.get('work', {})
                            if 'language' in work:
                                lang_code = work['language']
                                lang_map = {
                                    'eng': 'English', 'hin': 'Hindi', 'tel': 'Telugu',
                                    'kan': 'Kannada', 'tam': 'Tamil', 'mar': 'Marathi',
                                    'ben': 'Bengali', 'guj': 'Gujarati', 'pan': 'Punjabi',
                                    'mal': 'Malayalam'
                                }
                                detected_lang = lang_map.get(lang_code, 'Unknown')
                                return {
                                    'language': detected_lang,
                                    'confidence': 0.85,
                                    'method': 'musicbrainz'
                                }
        
        return {'language': None, 'confidence': 0.0, 'method': 'musicbrainz_no_match'}
    except Exception as e:
        logger.debug(f"MusicBrainz API failed: {e}")
        return {'language': None, 'confidence': 0.0, 'method': 'musicbrainz_error'}


# =================================================================
# PHASE 4: METADATA-BASED DETECTION
# =================================================================

def _detect_language_from_metadata_patterns(title: str, artist: str, filename: str) -> Dict[str, Any]:
    """
    Detect language from filename, title, and artist patterns.
    Industry indicators: bollywood, tollywood, kollywood, etc.
    """
    text = f"{filename} {title} {artist}".lower()
    
    # Industry + language patterns
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
                return {
                    'language': lang,
                    'confidence': 0.65,
                    'method': 'metadata_patterns'
                }
    
    # Artist-based heuristics (famous Indian artists)
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
            return {
                'language': lang.title(),
                'confidence': 0.72,
                'method': 'artist_heuristic'
            }
    
    return {'language': None, 'confidence': 0.0, 'method': 'metadata_no_match'}


# =================================================================
# GENRE FETCHING FROM EXTERNAL APIs
# =================================================================

def _fetch_genre_from_jiosaavn(title: str, artist: str, album: str = '') -> Dict[str, Any]:
    """
    Query JioSaavn API to fetch genre/category information.
    Useful when file doesn't have genre metadata.
    """
    if not requests or not title:
        return {'genre': None, 'confidence': 0.0, 'method': 'jiosaavn_genre_failed'}
    
    try:
        url = "https://www.jiosaavn.com/api.php"
        query = f"{title} {artist}" if artist else title
        params = {
            'p': 1,
            'q': query,
            '_format': 'json',
            '_marker': 0,
            'api_version': 4,
            'ctx': 'wap6dot0',
            'n': 5,
            '__call': 'search.getResults'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                first_result = data['results'][0]
                
                # Try to get category/genre
                genres = []
                
                # JioSaavn has 'category' field
                if 'category' in first_result:
                    category = first_result['category'].lower()
                    # Map JioSaavn categories to genres
                    category_map = {
                        'pop': 'Pop', 'rock': 'Rock', 'metal': 'Metal',
                        'jazz': 'Jazz', 'blues': 'Blues', 'folk': 'Folk',
                        'classical': 'Classical', 'instrumental': 'Instrumental',
                        'indie': 'Indie', 'alternative': 'Alternative',
                        'dance': 'Dance', 'electronic': 'Electronic', 'edm': 'EDM',
                        'hip-hop': 'Hip-Hop', 'hiphop': 'Hip-Hop', 'rap': 'Rap',
                        'r&b': 'R&B', 'soul': 'Soul', 'funk': 'Funk',
                        'reggae': 'Reggae', 'country': 'Country', 'western': 'Western',
                        'bollywood': 'Bollywood', 'devotional': 'Devotional',
                        'sufi': 'Sufi', 'qawwali': 'Qawwali', 'ghazal': 'Ghazal',
                        'odia': 'Odia', 'puranic': 'Puranic', 'bhajan': 'Bhajan',
                        'alaap': 'Alaap', 'raag': 'Raag', 'instrumental music': 'Instrumental'
                    }
                    if category in category_map:
                        genres.append(category_map[category])
                
                # Try 'language' field too
                if 'language' in first_result:
                    language = first_result['language'].lower()
                    # Language to regional genre mapping
                    lang_to_genre = {
                        'hindi': 'Hindi', 'english': 'English', 'tamil': 'Tamil',
                        'telugu': 'Telugu', 'kannada': 'Kannada', 'malayalam': 'Malayalam',
                        'marathi': 'Marathi', 'bengali': 'Bengali', 'gujarati': 'Gujarati',
                        'punjabi': 'Punjabi', 'odia': 'Odia'
                    }
                    if language in lang_to_genre:
                        genres.append(lang_to_genre[language])
                
                if genres:
                    return {
                        'genre': ', '.join(genres),  # Combine genres
                        'confidence': 0.85,
                        'method': 'jiosaavn_api'
                    }
        
        return {'genre': None, 'confidence': 0.0, 'method': 'jiosaavn_genre_no_results'}
    
    except Exception as e:
        logger.debug(f"JioSaavn genre fetch failed: {e}")
        return {'genre': None, 'confidence': 0.0, 'method': f'jiosaavn_genre_error'}


def _fetch_genre_from_musicbrainz(title: str, artist: str) -> Dict[str, Any]:
    """
    Query MusicBrainz API to fetch genre information.
    Useful when file doesn't have genre metadata.
    """
    if not requests or not title:
        return {'genre': None, 'confidence': 0.0, 'method': 'musicbrainz_genre_failed'}
    
    try:
        headers = {
            'User-Agent': 'LanguageDetectionApp/1.0 (contact@example.com)'
        }
        
        url = "https://musicbrainz.org/ws/2/recording/"
        params = {
            'query': f'recording:"{title}"' + (f' AND artist:"{artist}"' if artist else ''),
            'fmt': 'json',
            'limit': 3
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=8)
        time.sleep(0.3)  # MusicBrainz rate limit
        
        if response.status_code == 200:
            data = response.json()
            if 'recordings' in data and len(data['recordings']) > 0:
                for recording in data['recordings'][:2]:
                    # Check for genre/tag-list
                    genres = []
                    
                    if 'tag-list' in recording:
                        for tag in recording['tag-list'][:3]:  # Top 3 tags
                            if 'name' in tag:
                                genres.append(tag['name'])
                    
                    if 'work-relation-list' in recording:
                        for relation in recording['work-relation-list']:
                            work = relation.get('work', {})
                            if 'tag-list' in work:
                                for tag in work['tag-list'][:2]:
                                    if 'name' in tag:
                                        genres.append(tag['name'])
                    
                    if genres:
                        # Deduplicate
                        genres = list(dict.fromkeys(genres))
                        return {
                            'genre': ', '.join(genres[:3]),  # Top 3 genres
                            'confidence': 0.8,
                            'method': 'musicbrainz_api'
                        }
        
        return {'genre': None, 'confidence': 0.0, 'method': 'musicbrainz_genre_no_results'}
    
    except Exception as e:
        logger.debug(f"MusicBrainz genre fetch failed: {e}")
        return {'genre': None, 'confidence': 0.0, 'method': 'musicbrainz_genre_error'}


# =================================================================
# MASTER: MULTI-PHASE DETECTION WITH FALLBACKS
# =================================================================

def detect_language_with_phases(
    title: str = '',
    artist: str = '',
    album: str = '',
    filename: str = '',
    lyrics: str = ''
) -> Dict[str, Any]:
    """
    Multi-phase language detection with intelligent fallback chain:
    
    PHASE 1: External APIs (JioSaavn, MusicBrainz) - MOST RELIABLE
    PHASE 2: Lyrics-based (langdetect + keywords)
    PHASE 3: Voice recognition (Whisper) - OPTIONAL
    PHASE 4: Metadata patterns & artist heuristics
    
    Returns:
        {
            'primary_language': str,
            'all_languages': list,
            'language_distribution': dict,
            'detection_method': str,
            'confidence': float
        }
    """
    best_result = None
    best_confidence = 0.0
    
    # PHASE 1: Try JioSaavn API (most accurate for Indian music)
    if title and artist:
        logger.debug("   [PHASE 1] Querying JioSaavn API...")
        result = _detect_language_jiosaavn(title, artist)
        if result['language'] and result['confidence'] > best_confidence:
            best_result = result
            best_confidence = result['confidence']
            if best_confidence >= 0.9:
                return {
                    'primary_language': result['language'],
                    'all_languages': [result['language']],
                    'language_distribution': {result['language']: 100},
                    'detection_method': result['method'],
                    'confidence': result['confidence']
                }
    
    # PHASE 1B: Try JioSaavn Album Search (alternate query)
    if album and artist and best_confidence < 0.85:
        logger.debug("   [PHASE 1] Trying JioSaavn album search...")
        result = _detect_language_jiosaavn_album(album, artist)
        if result['language'] and result['confidence'] > best_confidence:
            best_result = result
            best_confidence = result['confidence']
    
    # PHASE 1C: Try MusicBrainz
    if title and best_confidence < 0.85:
        logger.debug("   [PHASE 1] Querying MusicBrainz API...")
        result = _detect_language_musicbrainz(title, artist)
        if result['language'] and result['confidence'] > best_confidence:
            best_result = result
            best_confidence = result['confidence']
    
    # PHASE 2: Lyrics-based detection (fallback)
    if lyrics and best_confidence < 0.75:
        logger.debug("   [PHASE 2] Analyzing lyrics...")
        result = detect_language(lyrics)  # Uses langdetect + keywords
        lang_confidence = result.get('confidence', 0.0)
        if lang_confidence > best_confidence:
            best_result = result
            best_confidence = lang_confidence
    
    # PHASE 4: Metadata-based detection (final fallback)
    if best_confidence < 0.65:
        logger.debug("   [PHASE 4] Checking metadata patterns...")
        result = _detect_language_from_metadata_patterns(title or '', artist or '', filename or '')
        if result['language'] and result['confidence'] > best_confidence:
            best_result = result
            best_confidence = result['confidence']
    
    # If we found something, return it
    if best_result and best_confidence > 0:
        # Ensure all required fields
        if 'primary_language' not in best_result:
            best_result['primary_language'] = best_result.get('language', 'Unknown')
        if 'all_languages' not in best_result:
            best_result['all_languages'] = [best_result['primary_language']]
        if 'language_distribution' not in best_result:
            best_result['language_distribution'] = {best_result['primary_language']: 100}
        if 'confidence' not in best_result:
            best_result['confidence'] = best_confidence
        
        return best_result
    
    # Fallback to English if nothing detected
    return {
        'primary_language': 'English',
        'all_languages': ['English'],
        'language_distribution': {'English': 100},
        'detection_method': 'default_english',
        'confidence': 0.0
    }


def detect_genre_with_phases(
    title: str = '',
    artist: str = '',
    album: str = '',
    filename: str = ''
) -> Dict[str, Any]:
    """
    Multi-phase genre detection with intelligent fallback chain:
    
    PHASE 1: External APIs (JioSaavn, MusicBrainz) - MOST RELIABLE
    PHASE 2: Metadata patterns from filename/title
    
    Returns:
        {
            'genre': str,
            'detection_method': str,
            'confidence': float
        }
    """
    best_result = None
    best_confidence = 0.0
    
    # PHASE 1: Try JioSaavn API (most accurate for Indian music with categories)
    if title and artist:
        logger.debug("      [PHASE 1] Querying JioSaavn for genre...")
        result = _fetch_genre_from_jiosaavn(title, artist, album)
        if result['genre'] and result['confidence'] > best_confidence:
            best_result = result
            best_confidence = result['confidence']
            if best_confidence >= 0.85:
                return {
                    'genre': result['genre'],
                    'detection_method': result['method'],
                    'confidence': result['confidence']
                }
    
    # PHASE 1B: Try MusicBrainz (good for western music)
    if title and best_confidence < 0.8:
        logger.debug("      [PHASE 1] Querying MusicBrainz for genre...")
        result = _fetch_genre_from_musicbrainz(title, artist)
        if result['genre'] and result['confidence'] > best_confidence:
            best_result = result
            best_confidence = result['confidence']
    
    # Return best result if found
    if best_result and best_confidence > 0:
        return {
            'genre': best_result['genre'],
            'detection_method': best_result['method'],
            'confidence': best_confidence
        }
    
    # Fallback - no genre found
    return {
        'genre': None,
        'detection_method': 'no_genre_found',
        'confidence': 0.0
    }


def read_metadata_with_ffprobe(file_path: Path) -> Optional[Dict[str, Any]]:
    """Try to read metadata using ffprobe as fallback."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(file_path)],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            tags = data.get('format', {}).get('tags', {})
            duration_ms = int(float(data.get('format', {}).get('duration', 0)) * 1000)
            
            return {
                'title': tags.get('title', '').strip(),
                'artist': tags.get('artist', '').strip(),
                'album': tags.get('album', '').strip(),
                'genre': tags.get('genre', '').strip(),
                'date': tags.get('date', '').strip(),
                'duration_ms': duration_ms,
            }
    except Exception as e:
        logger.debug(f"ffprobe read failed: {e}")
        return None
    
    return None


def read_existing_metadata(file_path: Path) -> Dict[str, Any]:
    """Read existing metadata from audio file."""
    metadata = {
        'title': '',
        'artist': '',
        'album': '',
        'duration_ms': 0,
        'genre': '',
        'date': '',
        'track_number': 0,
        'album_artist': '',
    }
    
    try:
        if file_path.suffix.lower() == '.mp3':
            from mutagen.id3 import ID3
            try:
                tags = ID3(str(file_path))
            except:
                tags = None
            
            audio = MP3(file_path)
            metadata['duration_ms'] = int(audio.info.length * 1000)
            
            if tags:
                # Get title (TIT2)
                if 'TIT2' in tags:
                    metadata['title'] = str(tags['TIT2']).strip()
                # Get artist (TPE1)
                if 'TPE1' in tags:
                    metadata['artist'] = str(tags['TPE1']).strip()
                # Get album (TALB)
                if 'TALB' in tags:
                    metadata['album'] = str(tags['TALB']).strip()
                # Get album artist (TPE2)
                if 'TPE2' in tags:
                    metadata['album_artist'] = str(tags['TPE2']).strip()
                # Get genre (TCON)
                if 'TCON' in tags:
                    metadata['genre'] = str(tags['TCON']).strip()
                # Get date (TDRC)
                if 'TDRC' in tags:
                    metadata['date'] = str(tags['TDRC']).strip()
                # Get track number (TRCK)
                if 'TRCK' in tags:
                    try:
                        metadata['track_number'] = int(str(tags['TRCK']).split('/')[0])
                    except:
                        pass
        
        elif file_path.suffix.lower() == '.flac':
            audio = FLAC(file_path)
            metadata['title'] = (audio.get('title') or [''])[0].strip()
            metadata['artist'] = (audio.get('artist') or [''])[0].strip()
            metadata['album'] = (audio.get('album') or [''])[0].strip()
            metadata['album_artist'] = (audio.get('albumartist') or [''])[0].strip()
            metadata['genre'] = (audio.get('genre') or [''])[0].strip()
            metadata['date'] = (audio.get('date') or [''])[0].strip()
            metadata['track_number'] = int((audio.get('tracknumber') or ['0'])[0].split('/')[0]) if audio.get('tracknumber') else 0
            metadata['duration_ms'] = int(audio.info.length * 1000)
        
        elif file_path.suffix.lower() in {'.m4a', '.mp4'}:
            audio = MP4(file_path)
            metadata['title'] = str((audio.get('\xa9nam') or [''])[0]).strip()
            metadata['artist'] = str((audio.get('\xa9ART') or [''])[0]).strip()
            metadata['album'] = str((audio.get('\xa9alb') or [''])[0]).strip()
            metadata['album_artist'] = str((audio.get('aART') or [''])[0]).strip()
            metadata['genre'] = str((audio.get('\xa9gen') or [''])[0]).strip()
            metadata['date'] = str((audio.get('\xa9day') or [''])[0]).strip()
            metadata['duration_ms'] = int(audio.info.length * 1000)
        
        logger.info(f"✅ Read metadata from file")
        return metadata
    
    except Exception as e:
        logger.error(f"❌ Error reading metadata: {e}")
        return metadata


def enrich_metadata(file_path: Path, existing_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich metadata based on existing data.
    
    IMPORTANT: Only enriches MISSING fields - preserves all existing good data!
    """
    title = existing_metadata.get('title', '').strip()
    artist = existing_metadata.get('artist', '').strip()
    album = existing_metadata.get('album', '').strip()
    duration_ms = existing_metadata.get('duration_ms', 0)
    
    enriched = {
        **existing_metadata,
        'featured_artists': [],
        'version_type': 'original',
        'tags': [],
        'genre': existing_metadata.get('genre', None),  # Preserve or fetch
        'language': 'English',
        'lyrics-eng': None,
    }
    
    logger.info("\n" + "="*70)
    logger.info("METADATA ENRICHMENT")
    logger.info("="*70)
    logger.info(f"🎵 Title:  {title or '(empty)'}")
    logger.info(f"👤 Artist: {artist or '(empty)'}")
    logger.info(f"💿 Album:  {album or '(empty)'}")
    logger.info(f"🎸 Genre:  {enriched['genre'] or '(missing - will fetch)'}")
    
    # Check if we have basic metadata to work with
    has_good_data = bool(title and artist)
    
    if not has_good_data:
        logger.warning("\n⚠️  WARNING: Missing title or artist - skipping enrichment")
        logger.warning("   (File needs at least title + artist to fetch lyrics and metadata)")
        return enriched
    
    # 1. Extract featured artists from title
    logger.info("\n[1/6] Extracting featured artists...")
    clean_title, featured_artists = _extract_featured_artists(title)
    if featured_artists:
        enriched['title'] = clean_title
        enriched['featured_artists'] = featured_artists
        logger.info(f"   ✅ Found featured artists: {', '.join(featured_artists)}")
    else:
        logger.info(f"   ℹ️  No featured artists detected")
    
    # 2. Detect version type
    logger.info("\n[2/6] Detecting version type...")
    version_type = _detect_version_type(title, album)
    enriched['version_type'] = version_type
    logger.info(f"   ✅ Version type: {version_type}")
    
    # 3. Extract tags from title and album
    logger.info("\n[3/6] Extracting genre/mood tags from metadata...")
    tags = _extract_tags_from_text(f"{title} {album}")
    if tags:
        enriched['tags'] = list(dict.fromkeys(tags))  # Deduplicate while preserving order
        logger.info(f"   ✅ Found tags: {', '.join(tags)}")
    else:
        logger.info(f"   ℹ️  No tags extracted from text")
    
    # 4. Fetch genre from external APIs (if missing)
    logger.info("\n[4/6] Fetching genre (multi-phase API lookup)...")
    if not enriched['genre']:
        genre_result = detect_genre_with_phases(
            title=clean_title or title,
            artist=artist,
            album=album,
            filename=file_path.name
        )
        if genre_result['genre']:
            enriched['genre'] = genre_result['genre']
            detection_method = genre_result.get('detection_method', 'unknown')
            confidence = genre_result.get('confidence', 0.0)
            logger.info(f"   ✅ Found genre: {genre_result['genre']} ({detection_method}, {confidence*100:.0f}% confidence)")
        else:
            logger.info(f"   ℹ️  No genre found in external APIs")
    else:
        logger.info(f"   ℹ️  Genre already present: {enriched['genre']}")
    
    # 5. Fetch lyrics
    logger.info("\n[5/6] Fetching lyrics...")
    lyrics = _fetch_lyrics_with_fallbacks(
        title=clean_title or title,
        artist=artist,
        album=album,
        duration_ms=duration_ms,
        platform='local'
    )
    
    # DETECT LANGUAGE using multi-phase approach
    logger.info("   🔍 Detecting language (multi-phase)...")
    filename = file_path.name
    lang_result = detect_language_with_phases(
        title=clean_title or title,
        artist=artist,
        album=album,
        filename=filename,
        lyrics=lyrics or ''
    )
    
    enriched['language'] = lang_result['primary_language']
    enriched['language_detected_from'] = lang_result.get('detection_method', 'unknown')
    enriched['all_detected_languages'] = lang_result['all_languages']
    enriched['language_distribution'] = lang_result['language_distribution']
    enriched['detection_method'] = lang_result.get('detection_method', 'unknown')
    enriched['language_confidence'] = lang_result.get('confidence', 0.0)
    
    if lyrics:
        # Convert non-Latin scripts to Latin (Hindi, Telugu, etc. → Roman characters)
        logger.info("   🔤 Converting non-Latin scripts to Latin...")
        lyrics = _romanize_lrc_lyrics(lyrics)
        enriched['lyrics-eng'] = lyrics
        
        # Show lyrics type (synced or plain)
        is_synced = has_timestamps(lyrics)
        lyrics_type = "synced/LRC" if is_synced else "plain text"
        logger.info(f"   ✅ Found lyrics ({len(lyrics)} characters) - {lyrics_type}")
    else:
        logger.info(f"   ℹ️  No lyrics found (language detected from metadata)")
    
    # 6. Display summary
    logger.info("\n[6/6] Summary...")
    logger.info(f"   ✅ Featured artists: {len(enriched['featured_artists'])}")
    logger.info(f"   ✅ Version type: {enriched['version_type']}")
    logger.info(f"   ✅ Tags: {len(enriched['tags'])} ({', '.join(enriched['tags'][:3])}{'...' if len(enriched['tags']) > 3 else ''})")
    logger.info(f"   ✅ Genre: {enriched['genre'] or '(not found)'}")
    logger.info(f"   ✅ Track #: {enriched.get('track_number', 'N/A')}")
    logger.info(f"   ✅ Lyrics: {'Yes' if enriched['lyrics-eng'] else 'No'}")
    
    # Show language detection results with distribution
    primary = enriched['language']
    detection_method = enriched.get('detection_method', 'unknown')
    confidence = enriched.get('language_confidence', 0.0)
    all_langs = enriched.get('all_detected_languages', [primary])
    
    # Map detection method to phase
    phase_map = {
        'jiosaavn_api': 'PHASE 1 (JioSaavn API)',
        'jiosaavn_album': 'PHASE 1 (JioSaavn Album)',
        'musicbrainz': 'PHASE 1 (MusicBrainz)',
        'lyrics_langdetect': 'PHASE 2 (Lyrics)',
        'metadata_patterns': 'PHASE 4 (Metadata)',
        'artist_heuristic': 'PHASE 4 (Artist)',
        'default_english': 'Default'
    }
    
    phase = phase_map.get(detection_method, detection_method)
    
    if confidence > 0:
        other_langs = ', '.join(all_langs[1:]) if len(all_langs) > 1 else 'none'
        logger.info(f"   🌐 Language: {primary} ({phase}, {confidence*100:.0f}% confidence)")
        if other_langs != 'none':
            logger.info(f"      Additional detected: {other_langs}")
    else:
        logger.info(f"   🌐 Language: {primary} ({phase})")
    
    # ===================================================================
    # PICARD FALLBACK: Fill any remaining gaps using MusicBrainz + AcoustID
    # ===================================================================
    if PICARD_AVAILABLE:
        logger.info("\n[PICARD] Running Picard fallback enrichment...")
        picard_result = run_picard_fallback_enrichment(file_path, enriched)
        
        if picard_result['metadata_enriched']:
            logger.info(f"   ✅ Picard filled {len(picard_result['filled_fields'])} fields: {', '.join(picard_result['filled_fields'])}")
            enriched['picard_enriched'] = True
            enriched['picard_method'] = picard_result.get('method', 'unknown')
        elif picard_result['ran']:
            logger.info(f"   ℹ️  Picard ran but no new fields to fill")
    
    return enriched


def update_file_metadata(file_path: Path, enriched_metadata: Dict[str, Any]):
    """Update audio file with enriched metadata."""
    try:
        logger.info("\n" + "="*70)
        logger.info("UPDATING FILE")
        logger.info("="*70)
        
        # Use the existing embed_metadata function
        embed_metadata(str(file_path), enriched_metadata)
        
        logger.info(f"✅ Successfully updated: {file_path.name}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error updating file: {e}")
        return False


def show_metadata_diff(before: Dict[str, Any], after: Dict[str, Any]):
    """Show what changed in metadata."""
    logger.info("\n" + "="*70)
    logger.info("METADATA CHANGES")
    logger.info("="*70)
    
    changes = []
    
    # Check new fields added
    if after.get('featured_artists') and not before.get('featured_artists'):
        changes.append(f"✨ Added featured artists: {', '.join(after['featured_artists'])}")
    
    if after.get('version_type', 'original') != 'original' and after.get('version_type') != before.get('version_type'):
        changes.append(f"✨ Set version type: {after['version_type']}")
    
    if after.get('tags') and not before.get('tags'):
        changes.append(f"✨ Added tags: {', '.join(after['tags'])}")
    
    if after.get('lyrics-eng') and not before.get('lyrics-eng'):
        changes.append(f"✨ Added lyrics: {len(after['lyrics-eng'])} characters")
    
    if after.get('language') and after.get('language') != before.get('language'):
        distribution = after.get('language_distribution', {})
        detection_method = after.get('detection_method', 'unknown')
        if distribution:
            if detection_method == 'script':
                dist_str = ', '.join([f"{lang} {pct}%" for lang, pct in distribution.items()])
                changes.append(f"🌐 Language: {after.get('language')} ({dist_str}, detected via script)")
            else:
                dist_str = ', '.join([f"{lang} {pct}%" for lang, pct in distribution.items()])
                changes.append(f"🌐 Language: {after.get('language')} ({dist_str})")
        else:
            changes.append(f"🌐 Language: {after.get('language')}")
    
    # Show preserved metadata
    preserved = []
    if before.get('title'):
        preserved.append(f"📝 Title: {before['title']} (preserved)")
    if before.get('artist'):
        preserved.append(f"👤 Artist: {before['artist']} (preserved)")
    if before.get('album'):
        preserved.append(f"💿 Album: {before['album']} (preserved)")
    
    if preserved:
        for item in preserved:
            logger.info(item)
    
    if not changes:
        logger.info("ℹ️  No new metadata to add (existing data is good)")
    else:
        for change in changes:
            logger.info(change)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExample:")
        print('  python enrich_metadata.py "B:\\music\\All\\Sahara.mp3"')
        print('  python enrich_metadata.py "B:\\music\\All\\Sahara.mp3" -y  # Auto-update')
        print('  python enrich_metadata.py "B:\\music\\All"             # Process entire folder')
        print('  python enrich_metadata.py "B:\\music\\All" -y          # Auto-update folder')
        print('  python enrich_metadata.py "B:\\music\\All" --limit 10  # Test with 10 files')
        print('  python enrich_metadata.py "B:\\music\\All" --skip 200 -y  # Resume from file 201')
        sys.exit(1)
    
    path = Path(sys.argv[1])
    auto_yes = '-y' in sys.argv
    limit = None
    skip = None
    
    # Parse --limit if provided
    if '--limit' in sys.argv:
        try:
            limit_idx = sys.argv.index('--limit')
            limit = int(sys.argv[limit_idx + 1])
        except (IndexError, ValueError):
            logger.error("Invalid limit value")
            sys.exit(1)
    
    # Parse --skip if provided
    if '--skip' in sys.argv:
        try:
            skip_idx = sys.argv.index('--skip')
            skip = int(sys.argv[skip_idx + 1])
        except (IndexError, ValueError):
            logger.error("Invalid skip value")
            sys.exit(1)
    
    # Validate path exists
    if not path.exists():
        logger.error(f"❌ Path not found: {path}")
        sys.exit(1)
    
    # Handle folder
    if path.is_dir():
        process_folder(path, auto_yes=auto_yes, limit=limit, skip=skip)
    # Handle single file
    elif path.is_file():
        process_file(path, auto_yes=auto_yes)
    else:
        logger.error(f"❌ Invalid path: {path}")
        sys.exit(1)


def get_audio_files(folder_path: Path) -> list[Path]:
    """Get all audio files from folder (recursive)."""
    extensions = {'.mp3', '.flac', '.m4a', '.aac', '.wav'}
    audio_files = [f for f in folder_path.rglob('*') if f.suffix.lower() in extensions]
    return sorted(audio_files)


def process_folder(folder_path: Path, auto_yes: bool = False, limit: Optional[int] = None, skip: Optional[int] = None):
    """Process all audio files in a folder."""
    print("\n" + "="*70)
    print("BATCH METADATA ENRICHMENT")
    print("="*70)
    print(f"📁 Folder: {folder_path}")
    if skip:
        print(f"⏭️  Skip: {skip} files (starting from file {skip + 1})")
    if limit:
        print(f"🔢 Limit: {limit} files")
    print(f"✅ Auto-update: {auto_yes}")
    print()
    
    # Get audio files
    audio_files = get_audio_files(folder_path)
    if not audio_files:
        logger.error("❌ No audio files found!")
        return
    
    logger.info(f"📁 Found {len(audio_files)} audio files total")
    
    # Apply skip if specified
    if skip:
        if skip >= len(audio_files):
            logger.error(f"❌ Skip value ({skip}) is greater than total files ({len(audio_files)})")
            return
        audio_files = audio_files[skip:]
        logger.info(f"⏭️  Skipped first {skip} files, {len(audio_files)} files remaining")
    
    # Apply limit if specified
    if limit:
        audio_files = audio_files[:limit]
        logger.info(f"Processing {limit} files...")
    
    # Ask for confirmation if not auto_yes
    if not auto_yes:
        print("\n" + "="*70)
        print(f"⚠️  PREVIEW: Will process {len(audio_files)} files")
        print("="*70)
        if len(audio_files) <= 10:
            for idx, f in enumerate(audio_files, 1):
                print(f"  {idx}. {f.name}")
        else:
            for idx, f in enumerate(audio_files[:5], 1):
                print(f"  {idx}. {f.name}")
            print(f"  ... and {len(audio_files) - 5} more files")
        
        response = input("\n❓ Continue with enrichment? (yes/no): ").strip().lower()
        if response not in {'yes', 'y'}:
            logger.info("❌ Cancelled by user")
            return
    
    # Process each file
    success_count = 0
    skip_count = 0
    fail_count = 0
    start_number = (skip or 0) + 1  # Actual file number for display
    
    for idx, file_path in enumerate(audio_files, 1):
        actual_file_number = start_number + idx - 1
        logger.info(f"\n[{actual_file_number}/{len(audio_files) + (skip or 0)}] 🎵 {file_path.name}")
        
        try:
            # Read existing metadata
            existing_metadata = read_existing_metadata(file_path)
            
            # Enrich metadata
            enriched_metadata = enrich_metadata(file_path, existing_metadata)
            
            # Update file silently in batch mode
            if update_file_metadata(file_path, enriched_metadata):
                logger.info(f"   ✅ Enriched successfully!")
                success_count += 1
            else:
                logger.warning(f"   ❌ Failed to update")
                fail_count += 1
        
        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
            fail_count += 1
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"✅ Enriched:  {success_count}")
    print(f"❌ Failed:    {fail_count}")
    print(f"📊 Total:     {len(audio_files)}")
    print("="*70 + "\n")


def process_file(file_path: Path, auto_yes: bool = False):
    """Process a single audio file."""
    
    if file_path.suffix.lower() not in {'.mp3', '.flac', '.m4a', '.mp4', '.aac'}:
        logger.error(f"❌ Unsupported format: {file_path.suffix}")
        sys.exit(1)
    
    logger.info(f"\n📂 File: {file_path}")
    logger.info(f"📊 Size: {file_path.stat().st_size / (1024*1024):.2f} MB")
    
    # 1. Read existing metadata
    logger.info("\n[STEP 1] Reading existing metadata...")
    existing_metadata = read_existing_metadata(file_path)
    
    # 2. Enrich metadata
    logger.info("\n[STEP 2] Enriching metadata...")
    enriched_metadata = enrich_metadata(file_path, existing_metadata)
    
    # 3. Show what will change
    show_metadata_diff(existing_metadata, enriched_metadata)
    
    # 4. Ask for confirmation (skip if auto_yes)
    if not auto_yes:
        logger.info("\n" + "="*70)
        response = input("\n❓ Update file with enriched metadata? (yes/no): ").strip().lower()
        
        if response not in {'yes', 'y'}:
            logger.info("❌ Cancelled by user")
            return
    else:
        logger.info("\n✅ Auto-update enabled (-y), proceeding without confirmation")
    
    # 5. Update file
    success = update_file_metadata(file_path, enriched_metadata)
    
    if success:
        logger.info("\n" + "="*70)
        logger.info("✅ ENRICHMENT COMPLETE!")
        logger.info("="*70)
        logger.info(f"\n🎵 File updated successfully: {file_path.name}")
        logger.info("\nYou can now play the file with lyrics and enhanced metadata.")
    else:
        logger.error("\n❌ Failed to update file")
        sys.exit(1)


if __name__ == '__main__':
    main()
