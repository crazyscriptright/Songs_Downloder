#!/usr/bin/env python3
"""
Shared API Client
=================
Centralized API calls for JioSaavn and MusicBrainz to eliminate duplication.

Used by:
- picard_fallback_enricher.py
- api_metadata_enricher.py
- enrich_metadata.py
- Any module needing unified API access

Features:
- Shared headers and error handling
- Consistent timeout and retry logic
- Rate limit respect (MusicBrainz)
- Unified response parsing
"""

import logging
import time
from typing import Optional, Dict, Any

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import musicbrainzngs as mb
    HAS_MUSICBRAINZ = True
except ImportError:
    HAS_MUSICBRAINZ = False

from utils.shared_language_utils import (
    map_jiosaavn_language,
    map_musicbrainz_language,
)

logger = logging.getLogger(__name__)

# API Headers
JIOSAAVN_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8'
}

MUSICBRAINZ_HEADERS = {
    'User-Agent': 'SpotiFLAC/1.0 (contact@example.com)'
}


# ============================================================================
# JioSaavn API QUERIES
# ============================================================================

def query_jiosaavn_track(title: str, artist: str = '') -> Optional[Dict[str, Any]]:
    """
    Query JioSaavn for track metadata.
    
    Args:
        title: Track title
        artist: Artist name (optional)
    
    Returns:
        {
            'language': str,
            'title': str,
            'artist': str,
            'album': str,
            'confidence': float
        }
        Or None if not found
    """
    if not HAS_REQUESTS or not title:
        return None
    
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
        
        response = requests.get(
            url,
            params=params,
            headers=JIOSAAVN_HEADERS,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                result = data['results'][0]
                
                lang_name = result.get('language', '').lower()
                detected_lang = map_jiosaavn_language(lang_name)
                
                if detected_lang:
                    return {
                        'language': detected_lang,
                        'title': result.get('title', ''),
                        'artist': result.get('artist', ''),
                        'album': result.get('album', ''),
                        'confidence': 0.95,
                        'method': 'jiosaavn_track'
                    }
        
        return None
    
    except Exception as e:
        logger.debug(f"JioSaavn track query failed: {e}")
        return None


def query_jiosaavn_album(album: str, artist: str = '') -> Optional[Dict[str, Any]]:
    """
    Query JioSaavn for album metadata.
    
    Args:
        album: Album name
        artist: Artist name (optional)
    
    Returns:
        Dict with language and metadata, or None if not found
    """
    if not HAS_REQUESTS or not album:
        return None
    
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
        
        response = requests.get(
            url,
            params=params,
            headers=JIOSAAVN_HEADERS,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                result = data['results'][0]
                
                lang_name = result.get('language', '').lower()
                detected_lang = map_jiosaavn_language(lang_name)
                
                if detected_lang:
                    return {
                        'language': detected_lang,
                        'album': result.get('title', ''),
                        'artist': result.get('artist', ''),
                        'confidence': 0.90,
                        'method': 'jiosaavn_album'
                    }
        
        return None
    
    except Exception as e:
        logger.debug(f"JioSaavn album query failed: {e}")
        return None


# ============================================================================
# MusicBrainz API QUERIES
# ============================================================================

def query_musicbrainz_by_id(mbid: str) -> Optional[Dict[str, Any]]:
    """
    Query MusicBrainz for full recording metadata using MBID.
    
    Args:
        mbid: MusicBrainz recording ID
    
    Returns:
        Dict with genre, release_date, track_number, album, etc.
        Or None if not found
    """
    if not HAS_MUSICBRAINZ:
        return None
    
    try:
        mb.set_useragent('SpotiFLAC', '1.0')
        
        logger.debug(f"Querying MusicBrainz for MBID: {mbid}...")
        
        # Get recording with relationships and releases
        recording = mb.get_recording_by_id(
            mbid,
            includes=['artists', 'releases', 'tags', 'work-rels', 'artist-rels']
        )
        
        if recording and 'recording' in recording:
            rec = recording['recording']
            
            metadata = {
                'mbid': mbid,
                'title': rec.get('title'),
                'artist': rec.get('artist-credit-phrase', ''),
                'genre': None,
                'release_date': None,
                'isrc': None,
                'album': None,
                'track_number': None,
                'method': 'musicbrainz_by_id',
                'confidence': 0.90
            }
            
            # Extract genre from tags (Picard uses folksonomy tags)
            if 'tag-list' in rec:
                genres = []
                for tag in rec['tag-list'][:5]:  # Top 5 tags
                    if tag.get('name'):
                        tag_name = tag['name'].lower()
                        # Skip very common non-genre tags
                        skip_tags = {'seen live', 'live', 'compilations', 'covers', 're-issue', 'reissue'}
                        if tag_name not in skip_tags and len(tag_name) > 3:
                            genres.append(tag['name'])
                
                if genres:
                    metadata['genre'] = ', '.join(genres[:3])
            
            # Extract release date and album from first release
            if 'release-list' in rec and rec['release-list']:
                first_release = rec['release-list'][0]
                metadata['album'] = first_release.get('title')
                
                # Try to get date
                if first_release.get('date'):
                    metadata['release_date'] = first_release['date']
                elif rec.get('first-release-date'):
                    metadata['release_date'] = rec['first-release-date']
                
                # Get track number from release media
                release_id = first_release.get('id')
                if release_id:
                    try:
                        release_data = mb.get_release_by_id(
                            release_id,
                            includes=['recordings']
                        )
                        
                        if 'release' in release_data and 'medium-list' in release_data['release']:
                            for medium in release_data['release']['medium-list']:
                                track_list = medium.get('track-list', [])
                                for track in track_list:
                                    track_recording = track.get('recording', {})
                                    if track_recording.get('id') == mbid:
                                        if track.get('position'):
                                            metadata['track_number'] = str(track['position'])

                                        if track_recording.get('isrc-list'):
                                            metadata['isrc'] = track_recording['isrc-list'][0]
                                        break
                    except Exception as e:
                        logger.debug(f"Could not get release details: {e}")
            
            logger.debug(f"✅ MusicBrainz lookup successful")
            return metadata
        
        return None
    
    except Exception as e:
        logger.debug(f"MusicBrainz lookup failed: {e}")
        return None


def query_musicbrainz_fuzzy(title: str, artist: str = '') -> Optional[Dict[str, Any]]:
    """
    Fuzzy query MusicBrainz for recording matching.
    Better than exact match for typos/variations.
    
    Args:
        title: Track title
        artist: Artist name (optional)
    
    Returns:
        Dict with metadata, or None if not found
    """
    if not HAS_MUSICBRAINZ:
        return None
    
    try:
        mb.set_useragent('SpotiFLAC', '1.0')
        
        logger.debug(f"Fuzzy querying MusicBrainz for: {artist} - {title}")
        
        # Search for recording
        result = mb.search_recordings(
            artist=artist,
            recording=title,
            limit=5
        )
        
        if result and result.get('recording-list'):
            best_hit = None
            best_score = -1
            for hit in result['recording-list'][:5]:
                score = int(hit.get('ext:score', 0))
                if score > best_score:
                    best_score = score
                    best_hit = hit

            if best_hit and best_score >= 70:  # Relaxed threshold for Indian catalog
                mbid = best_hit['id']
                logger.debug(f"✅ Fuzzy match found (score={best_score}): MBID={mbid}")

                metadata = query_musicbrainz_by_id(mbid)
                if metadata:
                    metadata['confidence'] = best_score / 100.0
                return metadata
        
        logger.debug("No fuzzy matches found")
        return None
    
    except Exception as e:
        logger.debug(f"MusicBrainz fuzzy search failed: {e}")
        return None


def query_musicbrainz_recording_language(title: str, artist: str = '') -> Optional[str]:
    """
    Query MusicBrainz specifically for recording language.
    
    Args:
        title: Track title
        artist: Artist name (optional)
    
    Returns:
        Language name (e.g., 'Hindi'), or None if not found
    """
    if not HAS_REQUESTS or not title:
        return None
    
    try:
        headers = MUSICBRAINZ_HEADERS
        
        url = "https://musicbrainz.org/ws/2/recording/"
        params = {
            'query': f'recording:"{title}"' + (f' AND artist:"{artist}"' if artist else ''),
            'fmt': 'json',
            'limit': 3
        }
        
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=8
        )
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
                                detected_lang = map_musicbrainz_language(lang_code)
                                if detected_lang:
                                    return detected_lang
        
        return None
    
    except Exception as e:
        logger.debug(f"MusicBrainz language query failed: {e}")
        return None
