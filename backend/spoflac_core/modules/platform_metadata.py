"""
Enhanced metadata extraction for YouTube, YouTube Music, JioSaavn, and SoundCloud.
Used as fallback when Spotify metadata is unavailable.

Includes improved title/artist parsing for YouTube Music and lyrics-eng fetching via lrclib.net
"""
import re
from datetime import datetime


# ── Helper functions (defined first so they can be called throughout) ──────

def _parse_youtube_title(title: str, uploader: str) -> tuple[str, str]:
    """
    Parse YouTube title to extract artist and song name.
    
    YouTube often uses format: "Artist - Song Title (Official Video)"
    
    Returns: (song_title, artist_name)
    """
    title = title.strip()
    uploader = uploader.strip()
    
    # Try to split title by common separators
    separators = [' - ', ' – ', ' — ']
    
    for sep in separators:
        if sep in title:
            parts = title.split(sep)
            
            if len(parts) >= 2:
                potential_artist = parts[0].strip()
                potential_title = parts[1].strip()
                
                # Remove common suffixes from song title
                potential_title = re.sub(
                    r'\s*\((Official|Lyrics|Lyric Video|Audio|Video|HD|HQ|Remaster|Extended|Edit|Clean|Explicit).*?\).*',
                    '', potential_title, flags=re.IGNORECASE
                ).strip()
                
                if potential_title and potential_artist:
                    return (potential_title, potential_artist)
    
    # If no separator found, use original title and uploader
    return (title, uploader)


def _clean_artist_name(artist: str) -> str:
    """
    Clean artist name by removing common YouTube suffixes.
    
    Transforms:
    - "Queen Official" → "Queen"
    - "The Weeknd - Topic" → "The Weeknd"
    - "Coldplay VEVO" → "Coldplay"
    """
    artist = artist.strip()
    
    # Remove common suffixes (longest first to avoid partial matches)
    suffixes = [
        ' VEVO Official',
        ' Official Channel',
        ' Channel Official',
        ' - Official',
        ' - Topic',
        ' Official',
        ' Channel',
        ' VEVO',
        ' Music',
        ' Records',
        ' Label',
        ' Audio',
    ]
    
    for suffix in suffixes:
        if artist.lower().endswith(suffix.lower()):
            artist = artist[:-len(suffix)].strip()
            break
    
    return artist


def _detect_genre_from_text(text: str) -> list[str]:
    """
    Detect genre keywords from title/description text.
    Returns list of matched genres.
    """
    genres_map = {
        'pop': ['pop', 'mainstream'],
        'rock': ['rock', 'hard rock', 'alternative rock'],
        'hip-hop': ['hip-hop', 'rap', 'hiphop'],
        'electronic': ['electronic', 'edm', 'house', 'techno', 'synth'],
        'classical': ['classical', 'orchestral', 'symphony'],
        'jazz': ['jazz'],
        'country': ['country', 'folk'],
        'r&b': ['r&b', 'soul', 'rnb'],
    }
    
    text_lower = text.lower()
    found_genres = []
    
    for genre, keywords in genres_map.items():
        for keyword in keywords:
            if keyword in text_lower:
                found_genres.append(genre)
                break
    
    return found_genres if found_genres else ['Other']


def _is_explicit_jiosaavn(track_data: dict) -> bool:
    """Check if JioSaavn track is marked as explicit."""
    explicit = track_data.get('explicit', False)
    if isinstance(explicit, str):
        return explicit.lower() in ('true', '1', 'yes')
    return bool(explicit)


def _parse_soundcloud_date(date_str: str) -> str:
    """
    Parse SoundCloud date format (ISO 8601) to YYYY-MM-DD.
    Example: "2023-01-15T10:30:00Z" → "2023-01-15"
    """
    if not date_str:
        return ''
    try:
        return date_str.split('T')[0]
    except:
        return ''


def _get_soundcloud_artwork(artwork_url: str) -> str:
    """
    Get high-resolution SoundCloud artwork URL.
    SoundCloud returns URLs like: https://a1.sndcdn.com/.../-large.jpg
    We want to request the -t500x500 version for better quality.
    """
    if not artwork_url:
        return ''
    return artwork_url.replace('-large.jpg', '-t500x500.jpg')


def _fetch_lyrics_with_fallbacks(title: str, artist: str, album: str = '',
                                 duration_ms: int = 0, platform: str = '',
                                 original_uploader: str = '') -> str | None:
    """
    Fetch lyrics with multiple fallback attempts using different metadata variations.
    
    Tries in order:
    1. Primary: title + cleaned artist + album + duration
    2. Fallback 1: title + cleaned artist (no album/duration)
    3. Fallback 2: title + original uploader (before cleaning)
    4. Fallback 3: Just title (if artist is very generic)
    """
    
    print(f" [lyrics/{platform}] Metadata: {artist} – {title} ({duration_ms}ms)")
    
    # Attempt 1: Primary with all metadata
    lyrics = fetch_lyrics_for_platform(
        title=title,
        artist=artist,
        album=album,
        duration_ms=duration_ms,
        platform=platform
    )
    if lyrics:
        return lyrics
    
    # Attempt 2: Without album/duration (sometimes too restrictive)
    if album or duration_ms:
        print(f" [lyrics/{platform}] Retry without album/duration...")
        lyrics = fetch_lyrics_for_platform(
            title=title,
            artist=artist,
            album='',
            duration_ms=0,
            platform=platform
        )
        if lyrics:
            return lyrics
    
    # Attempt 3: Try original uploader name (before cleaning)
    if original_uploader and original_uploader != artist:
        print(f" [lyrics/{platform}] Retry with original uploader: {original_uploader}...")
        lyrics = fetch_lyrics_for_platform(
            title=title,
            artist=original_uploader,
            album=album,
            duration_ms=0,
            platform=platform
        )
        if lyrics:
            return lyrics
    
    # Attempt 4: Just title if artist is very generic
    if len(artist) < 3 or artist.lower() in ['unknown artist', 'official', 'channel', 'music']:
        print(f" [lyrics/{platform}] Retry with title only...")
        lyrics = fetch_lyrics_for_platform(
            title=title,
            artist='',
            album='',
            duration_ms=0,
            platform=platform
        )
        if lyrics:
            return lyrics
    
    return None


# ── Advanced metadata extraction helpers ────────────────────────────────

def _extract_featured_artists(title: str) -> tuple[str, list[str]]:
    """
    Extract featured artists from title.
    
    Handles formats:
    - "Song (feat. Artist)"
    - "Song (feat. Artist1 & Artist2)"
    - "Song ft. Artist"
    - "Song featuring Artist"
    - "featuring" at start of title
    
    Returns: (clean_title, [featured_artists])
    """
    
    featured = []
    clean_title = title.strip()
    
    # Regex patterns for featuring - try parentheses first, then without
    patterns = [
        r'\s*\(feat\.?\s+([^)]+)\)',  # (feat. ...)
        r'\s*\(featuring\s+([^)]+)\)',  # (featuring ...)
        r'\s*\(ft\.?\s+([^)]+)\)',  # (ft. ...)
        r'\s*-\s*feat\.?\s+([^,&]+)',  # - feat. (for titles like Song - feat. Artist)
        r'(?:^|\s)feat\.?\s+(.+?)(?:\s*\(|$)',  # feat. ... at start/middle
        r'(?:^|\s)featuring\s+(.+?)(?:\s*\(|$)',  # featuring ... at start/middle
        r'(?:^|\s)ft\.?\s+(.+?)(?:\s*\(|$)',  # ft. ... at start/middle
    ]
    
    for pattern in patterns:
        match = re.search(pattern, clean_title, re.IGNORECASE)
        if match:
            feat_str = match.group(1).strip()
            # Split by & or "and" or "," for multiple artists
            artists = re.split(r'\s+(?:and|&)\s+', feat_str, flags=re.IGNORECASE)
            featured = [a.strip() for a in artists if a.strip() and a.strip().lower() not in ['remix', 'mix']]
            
            # Remove the featuring part from title
            clean_title = re.sub(pattern, '', clean_title, flags=re.IGNORECASE).strip()
            break
    
    return clean_title, featured


def _detect_version_type(title: str, description: str = '') -> str:
    """
    Detect song version type from title/description.
    
    Returns: 'remix', 'live', 'acoustic', 'cover', 'alternative', 'extended', 'clean', or 'original'
    """
    combined = (title + ' ' + description).lower()
    
    version_patterns = {
        'remix': [r'\bremix\b', r'\(remix\)', r'remix\s+(?:version|mix)', r'remix\s+mix'],
        'live': [r'\blive\b', r'\(live\)', r'live\s+(?:performance|session|concert|version)'],
        'acoustic': [r'\bacoustic\b', r'\(acoustic\)', r'acoustic\s+version'],
        'cover': [r'\bcover\b', r'\(cover\)', r'cover\s+version'],
        'alternative': [r'\balt\s*mix\b', r'\balternative\s+(?:version|mix)', r'\balt\s+version'],
        'extended': [r'\bextended\s+(?:mix|version)', r'\(extended\)'],
        'clean': [r'\bclean\s+(?:version|edit)', r'\(clean\)', r'\bradio\s+edit'],
    }
    
    for version, patterns in version_patterns.items():
        for pattern in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return version
    
    return 'original'


def _extract_tags_from_text(text: str) -> list[str]:
    """
    Extract tags/keywords from title/description.
    
    Looks for: genre keywords, mood descriptors, instrument types
    Returns list of relevant tags with NO duplicates.
    """
    
    tags = []
    text_lower = text.lower()
    
    # Genre tags - order matters for specificity
    genre_keywords = {
        'synth': ['synth', 'synthpop', 'synthwave'],
        'progressive': ['progressive', 'progressive-rock', 'prog-rock', 'prog rock'],
        'lo-fi': ['lo-fi', 'lofi', 'low-fi', 'lowfi'],
        'pop': ['\\bpop\\b', 'mainstream', 'j-pop', 'k-pop', 'bubblegum pop'],
        'rock': ['\\brock\\b', '\\brock music\\b', 'hard rock', 'alternative rock', 'classic rock'],
        'hip-hop': ['hip-hop', 'hip hop', '\\brap\\b', 'hiphop', '\\brap music\\b'],
        'electronic': ['electronic', 'edm', 'electro', '\\bhouse\\b', 'techno', 'trance'],
        'classical': ['classical', 'orchestral', 'symphony', 'orchestration'],
        'jazz': ['\\bjazz\\b', 'jazz music'],
        'country': ['country', 'folk', 'folksy', 'americana'],
        'r&b': ['r&b', 'rnb', '\\bsoul\\b', 'rhythm and blues'],
        'metal': ['metal', 'metalcore', 'thrash', 'heavy metal', 'death metal'],
        'punk': ['punk', 'punk rock', 'punk-rock'],
    }
    
    for tag, keywords in genre_keywords.items():
        for keyword in keywords:
            if re.search(keyword, text_lower, re.IGNORECASE):
                if tag not in tags:
                    tags.append(tag)
                break  # Found this genre, move to next
    
    # Mood tags
    mood_keywords = {
        'uplifting': ['uplifting', 'upbeat', 'feel-good', 'feel good', 'feel-good'],
        'dark': ['\\bdark\\b', 'gloomy', 'haunting', 'darkwave', 'dark wave'],
        'melancholic': ['melancholic', 'melancholy', '\\bsad\\b', 'sadness'],
        'energetic': ['energetic', '\\benergy\\b', 'high-energy', 'high energy'],
        'chill': ['\\bchill\\b', 'chilling', 'relaxing', 'relaxed', 'peaceful', 'laid-back'],
        'intense': ['intense', 'aggressive', '\\bhard\\b', 'intensity'],
    }
    
    for tag, keywords in mood_keywords.items():
        for keyword in keywords:
            if re.search(keyword, text_lower, re.IGNORECASE):
                if tag not in tags:
                    tags.append(tag)
                break
    
    # Instrument/style tags
    instrument_keywords = {
        'acoustic': ['acoustic', 'unplugged'],
        'orchestral': ['orchestral', 'orchestra', 'orchestration'],
        'experimental': ['experimental', 'avant-garde'],
        'indie': ['indie', 'independent'],
        'ambient': ['ambient', 'atmospheric', 'ambience'],
        'psych': ['psychedelic', 'psych', 'psychedelia', 'psychotropic'],
    }
    
    for tag, keywords in instrument_keywords.items():
        for keyword in keywords:
            if re.search(keyword, text_lower, re.IGNORECASE):
                if tag not in tags:
                    tags.append(tag)
                break
    
    return tags


def _parse_jiosaavn_tags(track_data: dict) -> list[str]:
    """Extract tags from JioSaavn track data."""
    tags = []
    
    # From language field
    if track_data.get('language'):
        lang = track_data['language'].lower()
        if lang not in ['english', 'other']:
            tags.append(lang)
    
    # From year (can indicate era)
    try:
        year = int(track_data.get('year', 0))
        if year:
            if year < 2000:
                tags.append('classic')
            elif 2000 <= year < 2010:
                tags.append('2000s')
            elif 2010 <= year < 2020:
                tags.append('2010s')
    except:
        pass
    
    return tags


def _extract_isrc_from_text(text: str) -> str:
    """
    Try to extract ISRC code from text (format: XX-XXX-YY-NNNNN).
    Returns ISRC code or empty string.
    """
    if not text:
        return ''
    
    # ISRC format: XX-XXX-YY-NNNNN (2 country + 3 registrant + 2 year + 5 number)
    isrc_pattern = r'[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}'
    match = re.search(isrc_pattern, text)
    
    if match:
        isrc = match.group(0)
        # Format with hyphens
        return f"{isrc[:2]}-{isrc[2:5]}-{isrc[5:7]}-{isrc[7:]}"
    
    return ''


# ── Main metadata extractors ────────────────────────────────────────────────

def extract_youtube_metadata(video_info: dict, title: str = '', artist: str = '') -> dict:
    """
    Extract enhanced metadata from YouTube/YouTube Music video info.
    
    Features:
    - Smart title parsing: extracts artist from "Artist - Song Title" format
    - Artist name cleaning: removes "Official", "VEVO", "Topic" suffixes
    - Featured artist extraction: "Song (feat. Artist)" → featured_artists field
    - Version detection: remix, live, acoustic, cover, etc.
    - Tag extraction: genres and moods from title/description
    - Lyrics fetching with fallbacks via lrclib.net
    
    Input: video_info dict (from yt-dlp or YouTube API)
    Output: Standardized metadata dict with all available fields
    """
    title_val = title or video_info.get('title', 'Unknown Title')
    artist_val = artist or video_info.get('uploader', video_info.get('channel', 'Unknown Artist'))
    
    # Parse YouTube title format "Artist - Song Title" if present
    parsed_title, parsed_artist = _parse_youtube_title(title_val, artist_val)
    
    # Clean artist name (remove "Official", "Channel", etc.)
    cleaned_artist = _clean_artist_name(parsed_artist)
    
    # Detect version type FIRST (before removing version info from title)
    description = video_info.get('description', '')
    version_type = _detect_version_type(parsed_title, description)
    
    # Remove version and suffix info from title (e.g., "(Official Video)" or "(Remix)") but keep featured artists
    # Only remove content within parentheses, not everything after them
    clean_title = re.sub(
        r'\s*\((Official|Lyrics|Lyric Video|Audio|Video|HD|HQ|Remaster|Extended|Edit|Clean|Explicit|Remix|Live|Acoustic|Cover).*?\)',
        '', parsed_title, flags=re.IGNORECASE
    ).strip()
    
    # Extract featured artists from cleaned title
    clean_title, featured_artists = _extract_featured_artists(clean_title)
    
    # Extract tags
    tags = _extract_tags_from_text(clean_title + ' ' + description)
    
    metadata = {
        'title': clean_title,
        'artist': cleaned_artist,
        'featured_artists': featured_artists,
        'album': video_info.get('album', clean_title or 'YouTube'),
        'album_artist': cleaned_artist,
        'release_date': '',
        'track_number': 1,
        'disc_number': 1,
        'duration_ms': 0,
        'isrc': '',
        'cover_url': None,
        'copyright': '',
        'publisher': '',
        'explicit': False,
        'genre': 'Other',
        'tags': tags,
        'version_type': version_type,
        'spotify_url': '',
        'source_url': video_info.get('webpage_url', ''),
        'lyrics-eng': None,
    }
    
    # Extract duration
    if video_info.get('duration'):
        metadata['duration_ms'] = video_info['duration'] * 1000
    
    # Extract upload date (YYYYMMDD format from yt-dlp)
    if video_info.get('upload_date'):
        try:
            date_str = video_info['upload_date']
            metadata['release_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except:
            pass
    
    # Extract thumbnail as cover art (prefer highest resolution)
    if video_info.get('thumbnail'):
        metadata['cover_url'] = video_info['thumbnail']
    
    # Detect genre from title/description
    genres = _detect_genre_from_text(clean_title + ' ' + description)
    if genres:
        metadata['genre'] = genres[0]
        # Add additional genres as tags if not already present
        for g in genres[1:]:
            if g not in tags and g != 'Other':
                tags.append(g)
    
    metadata['tags'] = tags
    
    # Publisher/Channel info
    if video_info.get('uploader_id'):
        metadata['publisher'] = video_info.get('uploader', 'YouTube')
    
    # Fetch lyrics with fallbacks
    metadata['lyrics-eng'] = _fetch_lyrics_with_fallbacks(
        title=parsed_title,
        artist=cleaned_artist,
        album=metadata['album'],
        duration_ms=metadata['duration_ms'],
        platform='youtube',
        original_uploader=parsed_artist  # Try original too if cleaned doesn't match
    )
    
    return metadata


def extract_jiosaavn_metadata(track_data: dict) -> dict:
    """
    Extract enhanced metadata from JioSaavn API response.
    Includes featured artists, version detection, and tags.
    """
    title_val = track_data.get('song', 'Unknown Title')
    artist_val = ', '.join([a.get('name', '') for a in track_data.get('artists', [])]) if track_data.get('artists') else 'Unknown Artist'
    album_val = track_data.get('album', 'Unknown Album')
    duration_ms = int(track_data.get('duration', 0)) * 1000 if track_data.get('duration') else 0
    
    # Extract featured artists from title
    clean_title, featured_artists = _extract_featured_artists(title_val)
    
    # Remove version suffixes from title (e.g., "(Remix)" or "(Live)")
    clean_title = re.sub(
        r'\s*\((Official|Lyrics|Lyric Video|Audio|Video|HD|HQ|Remaster|Extended|Edit|Clean|Explicit|Remix|Live|Acoustic|Cover).*?\)',
        '', clean_title, flags=re.IGNORECASE
    ).strip()
    
    # Detect version type
    version_type = _detect_version_type(title_val)
    
    # Extract tags
    tags = _parse_jiosaavn_tags(track_data)
    extracted_tags = _extract_tags_from_text(clean_title)
    
    # Deduplicate tags
    for tag in extracted_tags:
        if tag not in tags:
            tags.append(tag)
    
    metadata = {
        'title': clean_title,
        'artist': artist_val,
        'featured_artists': featured_artists,
        'album': album_val,
        'album_artist': artist_val,
        'release_date': track_data.get('date_release', track_data.get('release_date', '')),
        'track_number': int(track_data.get('position', 1)) if track_data.get('position') else 1,
        'disc_number': 1,
        'duration_ms': duration_ms,
        'isrc': track_data.get('isrc', ''),
        'cover_url': track_data.get('image', ''),
        'copyright': track_data.get('copyright', ''),
        'publisher': track_data.get('label', 'JioSaavn'),
        'explicit': _is_explicit_jiosaavn(track_data),
        'genre': track_data.get('language', 'Other'),
        'tags': tags,
        'version_type': version_type,
        'spotify_url': '',
        'source_url': track_data.get('permaUrl', f"https://www.jiosaavn.com/song/{track_data.get('id', '')}/"),
        'lyrics-eng': None,
    }
    
    # Fetch lyrics for JioSaavn platform
    metadata['lyrics-eng'] = fetch_lyrics_for_platform(
        title=clean_title,
        artist=artist_val,
        album=album_val,
        duration_ms=duration_ms,
        platform='jiosaavn'
    )
    
    return metadata


def extract_soundcloud_metadata(track_data: dict) -> dict:
    """
    Extract enhanced metadata from SoundCloud API response.
    Includes featured artists, version detection, and tags.
    """
    title_val = track_data.get('title', 'Unknown Title')
    artist_val = track_data.get('user', {}).get('username', 'Unknown Artist') if track_data.get('user') else 'Unknown Artist'
    duration_ms = track_data.get('duration', 0)  # SoundCloud already returns ms
    description = track_data.get('description', '')
    
    # Extract featured artists from title
    clean_title, featured_artists = _extract_featured_artists(title_val)
    
    # Remove version suffixes from title (e.g., "(Live Session)" or "(Remix)")
    clean_title = re.sub(
        r'\s*\((Official|Lyrics|Lyric Video|Audio|Video|HD|HQ|Remaster|Extended|Edit|Clean|Explicit|Remix|Live|Acoustic|Cover).*?\)',
        '', clean_title, flags=re.IGNORECASE
    ).strip()
    
    # Detect version type
    version_type = _detect_version_type(title_val, description)
    
    # Extract tags - combine SoundCloud built-in tags with extracted tags, then normalize and deduplicate
    tags = track_data.get('tags', []) if isinstance(track_data.get('tags'), list) else []
    extracted_tags = _extract_tags_from_text(clean_title + ' ' + description)
    
    # Normalize tag names to standard spellings (e.g., 'lofi' -> 'lo-fi', 'rnb' -> 'r&b')
    def normalize_tag(tag: str) -> str:
        tag_lower = tag.lower()
        normalizations = {
            'lofi': 'lo-fi',
            'lowfi': 'lo-fi',
            'rnb': 'r&b',
            'hiphop': 'hip-hop',
            'hiphop': 'hip-hop',
        }
        return normalizations.get(tag_lower, tag_lower)
    
    # Apply normalization and deduplicate
    combined_tags = []
    for tag in tags + extracted_tags:
        normalized = normalize_tag(tag)
        if normalized and normalized not in combined_tags:
            combined_tags.append(normalized)
    
    metadata = {
        'title': clean_title,
        'artist': artist_val,
        'featured_artists': featured_artists,
        'album': clean_title,
        'album_artist': artist_val,
        'release_date': _parse_soundcloud_date(track_data.get('created_at', '')),
        'track_number': 1,
        'disc_number': 1,
        'duration_ms': duration_ms,
        'isrc': '',
        'cover_url': _get_soundcloud_artwork(track_data.get('artwork_url')),
        'copyright': '',
        'publisher': track_data.get('user', {}).get('username', 'SoundCloud') if track_data.get('user') else 'SoundCloud',
        'explicit': track_data.get('tag_list', '').lower().count('explicit') > 0,
        'genre': track_data.get('genre', 'Other'),
        'tags': combined_tags,
        'version_type': version_type,
        'spotify_url': '',
        'source_url': track_data.get('permalink_url', f"https://soundcloud.com/{track_data.get('user', {}).get('username', '')}/{track_data.get('slug', '')}"),
        'lyrics-eng': None,
    }
    
    # Fetch lyrics for SoundCloud platform
    metadata['lyrics-eng'] = fetch_lyrics_for_platform(
        title=clean_title,
        artist=artist_val,
        album=clean_title,
        duration_ms=duration_ms,
        platform='soundcloud'
    )
    
    return metadata



def normalize_metadata_dict(metadata: dict) -> dict:
    """
    Ensure all metadata fields are present and properly typed.
    Fills in defaults for missing fields.
    """
    defaults = {
        'title': 'Unknown Title',
        'artist': 'Unknown Artist',
        'featured_artists': [],
        'album': 'Unknown Album',
        'album_artist': 'Unknown Artist',
        'release_date': '',
        'track_number': 1,
        'disc_number': 1,
        'duration_ms': 0,
        'isrc': '',
        'cover_url': None,
        'copyright': '',
        'publisher': '',
        'explicit': False,
        'genre': 'Other',
        'tags': [],
        'version_type': 'original',
        'spotify_url': '',
        'source_url': '',
        'lyrics-eng': None,
    }
    
    # Merge with defaults
    result = {**defaults, **{k: v for k, v in metadata.items() if v is not None}}
    
    # Type conversions
    result['explicit'] = bool(result.get('explicit', False))
    result['featured_artists'] = list(result.get('featured_artists', []))
    result['tags'] = list(result.get('tags', []))
    
    if isinstance(result.get('release_date'), str):
        result['release_date'] = result['release_date'][:10]  # YYYY-MM-DD
    
    return result



# ── Lyrics Fetching ───────────────────────────────────────────────────────

def has_timestamps(lyrics: str) -> bool:
    """Check if lyrics have timestamp markers (synced/LRC format)."""
    if not lyrics:
        return False
    # Check for LRC format: [mm:ss.xx] or [mm:ss]
    import re
    return bool(re.search(r'\[\d{1,2}:\d{2}(?:\.\d{2,3})?\]', lyrics))


def fetch_lyrics_for_platform(title: str, artist: str, album: str = '',
                            duration_ms: int = 0, platform: str = '') -> str | None:
    """
    Fetch lyrics for any platform using multiple APIs with fallback.
    
    Priority:
    1. Try all APIs for SYNCED (timestamp-based) lyrics first
    2. Fall back to plain text lyrics only if no synced found
    
    Returns synced/plain lyrics string or None.
    """
    
    # First pass: Try each API for timestamped/synced lyrics
    print(f" [lyrics/{platform}] Searching for synced lyrics...")
    
    sources_to_try = [
        ('lrclib.net', _fetch_lyrics_lrclib_internal),
        ('Genius', _fetch_lyrics_genius),
    ]
    
    # Try each source for synced lyrics first
    for source_name, fetch_func in sources_to_try:
        lyrics = fetch_func(title, artist, album, duration_ms)
        if lyrics and has_timestamps(lyrics):
            print(f" [lyrics/{platform}] ✅ Got synced lyrics from {source_name} ({len(lyrics)} chars)")
            return lyrics
    
    # Second pass: Fall back to plain text if no synced found
    print(f" [lyrics/{platform}] No synced lyrics found, trying plain text...")
    for source_name, fetch_func in sources_to_try:
        lyrics = fetch_func(title, artist, album, duration_ms)
        if lyrics:
            print(f" [lyrics/{platform}] ✅ Got plain lyrics from {source_name} ({len(lyrics)} chars)")
            return lyrics
    
    print(f" [lyrics/{platform}] ❌ No lyrics found from any source")
    return None


def _fetch_lyrics_genius(title: str, artist: str, album: str = '',
                        duration_ms: int = 0) -> str | None:
    """
    Fetch lyrics from Genius (free, no auth required for public API).
    Returns plain lyrics (no timestamps).
    """
    import requests
    
    try:
        # Genius API search endpoint (public)
        search_url = "https://genius.com/api/search"
        
        query = f"{artist} {title}".strip()
        params = {'q': query}
        
        resp = requests.get(search_url, params=params, timeout=10,
                          headers={'User-Agent': 'spotiflac/1.0'})
        
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        hits = data.get('response', {}).get('hits', [])
        
        if not hits:
            return None
        
        # Get first match URL
        url = hits[0]['result']['url']
        
        # Scrape the Genius page for lyrics
        page_resp = requests.get(url, timeout=10,
                                headers={'User-Agent': 'spotiflac/1.0'})
        
        if page_resp.status_code != 200:
            return None
        
        # Parse lyrics (basic HTML scraping)
        import re
        lyrics_div = re.search(r'<div>([^<]*(?:<br[^>]*>)?[^<]*)*</div>', page_resp.text)
        
        if lyrics_div:
            # Extract text and replace <br> with newlines
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(page_resp.text, 'html.parser')
            lyrics_divs = soup.find_all('div', {'data-lyrics-container': 'true'})
            if lyrics_divs:
                lyrics = '\n'.join([div.get_text() for div in lyrics_divs])
                return lyrics.strip() if lyrics.strip() else None
        
        return None
    
    except Exception as e:
        return None


def _fetch_lyrics_musixmatch(title: str, artist: str, album: str = '',
                            duration_ms: int = 0) -> str | None:
    """
    Fetch lyrics from MusixMatch (free, unofficial API).
    Returns plain lyrics (no timestamps).
    """
    import requests
    
    try:
        # MusixMatch free API endpoint
        search_url = "https://www.musixmatch.com/search"
        
        query = f"{artist} {title}".strip()
        params = {'q': query, 'type': 'track'}
        
        resp = requests.get(search_url, params=params, timeout=10,
                          headers={'User-Agent': 'spotiflac/1.0'})
        
        if resp.status_code != 200:
            return None
        
        # Extract lyrics URL from response  
        import re
        match = re.search(r'data-url="(/lyrics/([^"]+))"', resp.text)
        
        if not match:
            return None
        
        lyrics_url = f"https://www.musixmatch.com{match.group(1)}"
        
        # Fetch the lyrics page
        page_resp = requests.get(lyrics_url, timeout=10,
                                headers={'User-Agent': 'spotiflac/1.0'})
        
        if page_resp.status_code != 200:
            return None
        
        # Parse lyrics (basic HTML scraping)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(page_resp.text, 'html.parser')
        
        lyrics_divs = soup.find_all('p', {'class': 'mxm-lyrics__line'})
        if lyrics_divs:
            lyrics = '\n'.join([div.get_text() for div in lyrics_divs])
            return lyrics.strip() if lyrics.strip() else None
        
        return None
    
    except Exception as e:
        return None


def _fetch_lyrics_lrclib_internal(title: str, artist: str, album: str = '',
                                  duration_ms: int = 0) -> str | None:
    """
    Internal lrclib.net fetcher (avoids circular imports with url_resolver).
    Returns synced lyrics first, then plain text.
    """
    import requests
    
    _LRCLIB_API = "https://lrclib.net/api/get"
    
    params = {
        'track_name': title,
        'artist_name': artist,
    }
    if album:
        params['album_name'] = album
    if duration_ms:
        params['duration'] = round(duration_ms / 1000)
    
    try:
        resp = requests.get(_LRCLIB_API, params=params, timeout=10,
                          headers={'User-Agent': 'spotiflac/1.0'})
        
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        
        # Prefer synced lyrics
        synced = (data.get('syncedLyrics') or '').strip()
        if synced:
            return synced
        
        # Fall back to plain text
        plain = (data.get('plainLyrics') or '').strip()
        if plain:
            return plain
        
        return None
    
    except Exception as e:
        return None
