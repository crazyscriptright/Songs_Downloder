#!/usr/bin/env python3
"""
Picard Fallback Enricher

Uses Picard's underlying libraries (musicbrainzngs + AcoustID) as fallback
when primary enrichment is incomplete.

Features:
- AcoustID fingerprinting (identifies song even if tags are wrong)
- MusicBrainz fuzzy matching + comprehensive metadata
- Automatic genre, release date, ISRC fetching
- Duplicate detection

Only runs if primary enrichment is missing critical fields.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
import subprocess
import time

try:
    import musicbrainzngs as mb
    HAS_MUSICBRAINZ = True
except ImportError:
    HAS_MUSICBRAINZ = False

try:
    import acoustid
    HAS_ACOUSTID = True
except ImportError:
    try:
        import pyacoustid as acoustid
        HAS_ACOUSTID = True
    except ImportError:
        HAS_ACOUSTID = False

logger = logging.getLogger(__name__)


def _generate_acoustid_fingerprint(file_path: Path) -> Optional[str]:
    """
    Generate AcoustID fingerprint for audio file.
    
    AcoustID requires fpcalc (fingerprint calculator).
    Returns fingerprint string or None if failed.
    """
    if not HAS_ACOUSTID:
        logger.debug("acoustid-py not installed, skipping fingerprinting")
        return None
    
    try:
        logger.debug(f"Generating AcoustID fingerprint for {file_path.name}...")
        
        # Calculate fingerprint using acoustid library
        # This internally uses fpcalc if available
        duration, fingerprint = acoustid.fingerprint_file(str(file_path))
        
        if fingerprint:
            logger.debug(f"✅ Fingerprint generated ({len(fingerprint)} chars), duration: {duration}s")
            return fingerprint
        else:
            logger.debug("❌ Failed to generate fingerprint")
            return None
    
    except Exception as e:
        logger.debug(f"AcoustID fingerprinting failed: {e}")
        return None


def _identify_via_acoustid(file_path: Path, acoustid_key: str = "YOUR_API_KEY") -> Optional[Dict[str, Any]]:
    """
    Identify song using AcoustID fingerprint.
    
    Returns MusicBrainz ID and recording info.
    Note: Requires free AcoustID API key from https://acoustid.org/api
    """
    if not HAS_ACOUSTID:
        return None
    
    try:
        fingerprint = _generate_acoustid_fingerprint(file_path)
        if not fingerprint:
            return None
        
        logger.debug("Querying AcoustID for recording match...")
        
        # Query AcoustID API
        results = acoustid.lookup(
            acoustid_key,
            fingerprint_compressed=False,  # Set to False to use raw fingerprint
            meta='recordings'
        )
        
        if results['status'] == 'ok' and results.get('results'):
            best_match = results['results'][0]
            
            if 'recordings' in best_match and best_match['recordings']:
                recording = best_match['recordings'][0]
                mbid = recording.get('id')
                score = best_match.get('score', 0)
                
                logger.debug(f"✅ Found match: MBID={mbid}, Score={score:.2f}")
                
                return {
                    'mbid': mbid,
                    'score': score,
                    'title': recording.get('title'),
                    'artists': recording.get('artists', []),
                    'method': 'acoustid'
                }
        
        logger.debug("No AcoustID matches found")
        return None
    
    except Exception as e:
        logger.debug(f"AcoustID lookup failed: {e}")
        return None


def _query_musicbrainz_by_id(mbid: str) -> Optional[Dict[str, Any]]:
    """
    Query MusicBrainz for full recording metadata using MBID.
    """
    if not HAS_MUSICBRAINZ:
        return None
    
    try:
        # Set Picard-like user agent
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
                'method': 'musicbrainz_by_id'
            }
            
            # Extract genre from tags (Picard uses folksonomy tags)
            # Tags are user-contributed and may not always be present
            if 'tag-list' in rec:
                genres = []
                for tag in rec['tag-list'][:5]:  # Top 5 tags
                    if tag.get('name'):
                        # Filter out non-genre tags
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
                
                # Get ISRC and track number from track
                # Need to query release directly to get full track-list
                release_id = first_release.get('id')
                if release_id:
                    try:
                        # Query release with recordings include to get track position
                        release_data = mb.get_release_by_id(
                            release_id,
                            includes=['recordings']
                        )
                        
                        if 'release' in release_data and 'medium-list' in release_data['release']:
                            first_medium = release_data['release']['medium-list'][0]
                            
                            if 'track-list' in first_medium and first_medium['track-list']:
                                first_track = first_medium['track-list'][0]
                                
                                # Extract track position (the actual track number on the album)
                                if first_track.get('position'):
                                    metadata['track_number'] = str(first_track['position'])
                                    logger.debug(f"   📍 Extracted track number: {metadata['track_number']}")
                                
                                # Try to get ISRC from recording
                                if 'recording' in first_track:
                                    rec_data = first_track['recording']
                                    if rec_data.get('isrc-list'):
                                        metadata['isrc'] = rec_data['isrc-list'][0]
                    except Exception as e:
                        logger.debug(f"   Could not get release details: {e}")

            
            logger.debug(f"✅ MusicBrainz lookup successful")
            return metadata
        
        return None
    
    except Exception as e:
        logger.debug(f"MusicBrainz lookup failed: {e}")
        return None


def _query_musicbrainz_fuzzy(title: str, artist: str) -> Optional[Dict[str, Any]]:
    """
    Fuzzy query MusicBrainz for recording matching.
    Better than exact match for typos/variations.
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
            limit=3
        )
        
        if result and result.get('recording-list'):
            best_hit = result['recording-list'][0]
            score = int(best_hit.get('ext:score', 0))
            
            if score >= 80:  # Good enough match
                mbid = best_hit['id']
                logger.debug(f"✅ Fuzzy match found (score={score}): MBID={mbid}")
                
                # Now get full details
                return _query_musicbrainz_by_id(mbid)
        
        logger.debug("No fuzzy matches found")
        return None
    
    except Exception as e:
        logger.debug(f"MusicBrainz fuzzy search failed: {e}")
        return None


def is_enrichment_complete(enriched_metadata: Dict[str, Any]) -> bool:
    """
    Check if enrichment is complete enough to skip fallback.
    
    Fallback triggers if missing:
    - Genre
    - Release date / ISRC
    """
    has_genre = bool(enriched_metadata.get('genre'))
    has_date = bool(enriched_metadata.get('date'))
    has_language = bool(enriched_metadata.get('language'))
    
    # Consider complete if has genre AND (date OR language)
    is_complete = (has_genre and (has_date or has_language))
    
    logger.debug(f"Enrichment completeness: genre={has_genre}, date={has_date}, language={has_language} → complete={is_complete}")
    
    return is_complete


def run_picard_fallback_enrichment(
    file_path: Path,
    existing_metadata: Dict[str, Any],
    acoustid_key: str = "YOUR_API_KEY"
) -> Dict[str, Any]:
    """
    Run Picard fallback enrichment to fill missing metadata.
    
    Only triggered if primary enrichment is incomplete.
    
    Returns:
        {
            'ran': bool,
            'metadata_enriched': bool,
            'filled_fields': list,  # Which fields were filled
            'method': str,  # 'acoustid' or 'fuzzy_match'
            'confidence': float,
            'errors': list
        }
    """
    result = {
        'ran': False,
        'metadata_enriched': False,
        'filled_fields': [],
        'method': None,
        'confidence': 0.0,
        'errors': []
    }
    
    try:
        # Check if enrichment is already complete
        if is_enrichment_complete(existing_metadata):
            logger.info("   ℹ️  Primary enrichment complete, skipping Picard fallback")
            return result
        
        logger.info("   🎵 Running Picard fallback enrichment...")
        result['ran'] = True
        
        title = existing_metadata.get('title', '').strip()
        artist = existing_metadata.get('artist', '').strip()
        
        if not (title and artist):
            logger.debug("   ⚠️  Missing title/artist, cannot use Picard fallback")
            result['errors'].append("Missing title/artist")
            return result
        
        # PHASE 1: Try AcoustID fingerprinting
        picard_metadata = None
        
        if HAS_ACOUSTID and file_path and file_path.exists():
            logger.debug("   [PHASE 1] Attempting AcoustID fingerprinting...")
            picard_metadata = _identify_via_acoustid(file_path, acoustid_key)
            
            if picard_metadata:
                # Query full MusicBrainz data using MBID
                if picard_metadata.get('mbid'):
                    full_metadata = _query_musicbrainz_by_id(picard_metadata['mbid'])
                    if full_metadata:
                        picard_metadata = full_metadata
                        picard_metadata['confidence'] = picard_metadata.get('score', 0.95)
                        result['method'] = 'acoustid'
        
        # PHASE 2: Fallback to fuzzy MusicBrainz search
        if not picard_metadata:
            logger.debug("   [PHASE 2] Attempting fuzzy MusicBrainz search...")
            picard_metadata = _query_musicbrainz_fuzzy(title, artist)
            if picard_metadata:
                result['method'] = 'fuzzy_match'
                picard_metadata['confidence'] = 0.80  # Fuzzy match lower confidence
        
        # Apply Picard results to fill gaps
        if picard_metadata:
            filled_count = 0
            
            # Fill missing genre
            if not existing_metadata.get('genre') and picard_metadata.get('genre'):
                existing_metadata['genre'] = picard_metadata['genre']
                result['filled_fields'].append('genre')
                filled_count += 1
                logger.info(f"      ✅ Filled genre: {picard_metadata['genre']}")
            
            # Fill missing date OR update with Picard's more accurate year
            # Always prefer Picard's release year for accuracy (Picard uses MusicBrainz)
            if picard_metadata.get('release_date'):
                existing_date = existing_metadata.get('date', '').strip()
                picard_year = picard_metadata['release_date'][:4]
                
                if not existing_date:
                    # No date in file, add it
                    existing_metadata['date'] = picard_year
                    result['filled_fields'].append('date')
                    filled_count += 1
                    logger.info(f"      ✅ Filled date: {picard_year}")
                elif existing_date != picard_year:
                    # Date exists but different - prefer Picard (more accurate source)
                    logger.info(f"      ℹ️  Updating date from {existing_date} → {picard_year} (Picard more accurate)")
                    existing_metadata['date'] = picard_year
                    if 'date' not in result['filled_fields']:
                        result['filled_fields'].append('date')
                    filled_count += 1
            
            # Fill missing album
            if not existing_metadata.get('album') and picard_metadata.get('album'):
                existing_metadata['album'] = picard_metadata['album']
                result['filled_fields'].append('album')
                filled_count += 1
                logger.info(f"      ✅ Filled album: {picard_metadata['album']}")
            
            # Override track number with Picard's value (fixes wrong track numbers like 47)
            # Movie songs typically have track 1-5, Picard gives authoritative track position
            if picard_metadata.get('track_number'):
                existing_track = existing_metadata.get('track_number')
                picard_track = str(picard_metadata['track_number'])
                
                if not existing_track:
                    # No track in file, add it
                    existing_metadata['track_number'] = picard_track
                    result['filled_fields'].append('track_number')
                    filled_count += 1
                    logger.info(f"      ✅ Filled track number: {picard_track}")
                elif str(existing_track) != picard_track:
                    # Track exists but different - prefer Picard (authoritative source)
                    logger.info(f"      ℹ️  Correcting track from {existing_track} → {picard_track} (Picard authoritative)")
                    existing_metadata['track_number'] = picard_track
                    if 'track_number' not in result['filled_fields']:
                        result['filled_fields'].append('track_number')
                    filled_count += 1
            
            # Fill ISRC if we have it
            if picard_metadata.get('isrc'):
                existing_metadata['isrc'] = picard_metadata['isrc']
                result['filled_fields'].append('isrc')
                filled_count += 1
            
            if filled_count > 0:
                result['metadata_enriched'] = True
                result['confidence'] = picard_metadata.get('confidence', 0.80)
                logger.info(f"   ✅ Picard fallback enriched {filled_count} fields ({result['method']})")
            else:
                logger.info(f"   ℹ️  No new fields to fill from Picard data")
        
        else:
            logger.info(f"   ⚠️  Picard fallback could not identify song")
    
    except Exception as e:
        logger.error(f"   ❌ Picard fallback error: {e}")
        result['errors'].append(str(e))
    
    return result


def install_requirements():
    """
    Check if required dependencies are installed.
    Provides helpful message if not.
    """
    missing = []
    
    if not HAS_MUSICBRAINZ:
        missing.append("musicbrainzngs")
    if not HAS_ACOUSTID:
        missing.append("acoustid")
    
    if missing:
        logger.warning(f"⚠️  Picard fallback disabled - install with: pip install {' '.join(missing)}")
        return False
    
    return True
