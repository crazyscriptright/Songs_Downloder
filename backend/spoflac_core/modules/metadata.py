"""Audio metadata embedding for FLAC and MP3 files"""
import os
import re
import requests
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TYER, TRCK, TPOS, TPE2, USLT, APIC, TSRC, TCON, TXXX
from mutagen.mp4 import MP4, MP4Cover
from config import USER_AGENT


def has_timestamps(lyrics: str) -> bool:
    """Check if lyrics have timestamp markers (synced/LRC format)."""
    if not lyrics:
        return False
    # Check for LRC format: [mm:ss.xx] or [mm:ss]
    return bool(re.search(r'\[\d{1,2}:\d{2}(?:\.\d{2,3})?\]', lyrics))


def should_override_lyrics(existing_lyrics: str, incoming_lyrics: str) -> bool:
    """
    Smart logic to decide if we should override existing lyrics.
    
    Rules:
    - If incoming has timestamps → Override (timestamps are always better)
    - If incoming is plain text → Don't override (preserve existing)
    - If existing has no lyrics → Always override
    """
    # No existing lyrics - always override
    if not existing_lyrics or not existing_lyrics.strip():
        return True
    
    incoming_has_ts = has_timestamps(incoming_lyrics)
    existing_has_ts = has_timestamps(existing_lyrics)
    
    # Incoming has timestamps → Always override (timestamps > plain text)
    if incoming_has_ts:
        return True
    
    # Incoming is plain text
    if not incoming_has_ts:
        # If existing has timestamps, don't override (keep the better one)
        if existing_has_ts:
            return False
        # Both are plain text - override for freshness
        return True
    
    return False


def _extract_year(metadata) -> str:
    """Get a clean 4-digit year from metadata keys: release_date/date/year."""
    raw_date = metadata.get('release_date') or metadata.get('date') or metadata.get('year')
    if raw_date is None:
        return ''

    year = str(raw_date).strip().split('-')[0]
    return year if (year.isdigit() and len(year) == 4) else ''

def download_cover_art(cover_url, output_path):
    """Download album cover art"""
    if not cover_url:
        return None

    try:
        print(f"Downloading cover art...")
        response = requests.get(cover_url, headers={'User-Agent': USER_AGENT}, timeout=30)

        if response.status_code != 200:
            print(f" Failed to download cover: HTTP {response.status_code}")
            return None

        with open(output_path, 'wb') as f:
            f.write(response.content)

        print(f" Cover art saved")
        return output_path

    except Exception as e:
        print(f" Failed to download cover: {e}")
        return None

def embed_flac_metadata(filepath, metadata, cover_path=None):
    """Embed metadata into FLAC file"""
    print("Embedding metadata into FLAC...")

    try:
        audio = FLAC(filepath)

        # Only update fields if they have values (don't overwrite with empty/Unknown)
        if metadata.get('title') and metadata['title'] not in ['Unknown Title', '']:
            audio['TITLE'] = metadata['title']
        
        if metadata.get('artist') and metadata['artist'] not in ['Unknown Artist', '']:
            audio['ARTIST'] = metadata['artist']
        
        if metadata.get('album') and metadata['album'] not in ['Unknown Album', '']:
            audio['ALBUM'] = metadata['album']
        
        if metadata.get('album_artist') and metadata['album_artist'] not in ['Unknown Artist', '']:
            audio['ALBUMARTIST'] = metadata['album_artist']
        
        year = _extract_year(metadata)
        if year:
            audio['DATE'] = year

        if metadata.get('track_number') and metadata['track_number'] not in [0, '0']:
            audio['TRACKNUMBER'] = str(metadata['track_number'])
        
        if metadata.get('disc_number') and metadata['disc_number'] not in [0, '0']:
            audio['DISCNUMBER'] = str(metadata['disc_number'])

        if metadata.get('copyright'):
            audio['COPYRIGHT'] = metadata['copyright']
        if metadata.get('publisher'):
            audio['PUBLISHER'] = metadata['publisher']
        if metadata.get('isrc') and metadata['isrc'] not in ['', 'Unknown']:
            audio['ISRC'] = metadata['isrc']
        
        # Genre
        if metadata.get('genre') and metadata['genre'] not in ['Unknown', '']:
            audio['GENRE'] = metadata['genre']
        
        # Explicit flag
        if metadata.get('explicit'):
            audio['EXPLICIT'] = 'Yes'
        
        # Spotify URL
        if metadata.get('spotify_url'):
            audio['SPOTIFY_URL'] = metadata['spotify_url']
        
        # Source URL (for non-Spotify platforms)
        if metadata.get('source_url') and not metadata.get('spotify_url'):
            audio['SOURCE_URL'] = metadata['source_url']
        
        # Featured artists
        if metadata.get('featured_artists'):
            audio['FEATURED_ARTISTS'] = ', '.join(metadata['featured_artists'])
        
        # Version type
        if metadata.get('version_type') and metadata['version_type'] != 'original':
            audio['VERSION_TYPE'] = metadata['version_type']
        
        # Tags
        if metadata.get('tags'):
            audio['TAGS'] = ', '.join(metadata['tags'])
        
        # Language
        if metadata.get('language') and metadata['language'] not in ['Unknown', '']:
            audio['LANGUAGE'] = metadata['language']
        
        # Year (DATE)
        if year:
            audio['DATE'] = year
        
        lyrics_val = metadata.get('lyrics-eng') or metadata.get('lyrics')
        if lyrics_val:
            # Check if we should override existing lyrics
            existing_lyrics = (audio.get('LYRICS') or [''])[0] if audio.get('LYRICS') else ''
            if should_override_lyrics(existing_lyrics, lyrics_val):
                audio['LYRICS'] = lyrics_val
                has_ts = has_timestamps(lyrics_val)
                ts_label = '(synced)' if has_ts else '(plain text)'
                print(f" [metadata] Lyrics embedded into FLAC ({len(lyrics_val)} chars) {ts_label}")
            else:
                print(f" [metadata] Kept existing lyrics (incoming plain text, existing synced)")
        else:
            print(" [metadata] No lyrics to embed (FLAC)")

        if cover_path and os.path.exists(cover_path):
            with open(cover_path, 'rb') as f:
                image_data = f.read()

            picture = Picture()
            picture.type = 3
            picture.mime = 'image/jpeg'
            picture.desc = 'Cover'
            picture.data = image_data

            audio.clear_pictures()
            audio.add_picture(picture)

        audio.save()
        print(" FLAC metadata embedded")

    except Exception as e:
        print(f" Failed to embed FLAC metadata: {e}")
        audio.save()
        print(" FLAC metadata embedded")

    except Exception as e:
        print(f" Failed to embed FLAC metadata: {e}")

def embed_mp3_metadata(filepath, metadata, cover_path=None):
    """Embed metadata into MP3 file using ID3v2"""
    print("Embedding metadata into MP3...")

    try:
        try:
            audio = ID3(filepath)
        except Exception:
            from mutagen.mp3 import MP3
            mp3_file = MP3(filepath)
            mp3_file.add_tags()
            audio = mp3_file.tags
        
        # Only update fields if they have values (don't overwrite with empty/Unknown)
        if metadata.get('title') and metadata['title'] not in ['Unknown Title', '']:
            audio.add(TIT2(encoding=3, text=metadata['title']))
        
        if metadata.get('artist') and metadata['artist'] not in ['Unknown Artist', '']:
            audio.add(TPE1(encoding=3, text=metadata['artist']))
        
        if metadata.get('album') and metadata['album'] not in ['Unknown Album', '']:
            audio.add(TALB(encoding=3, text=metadata['album']))
        
        if metadata.get('album_artist') and metadata['album_artist'] not in ['Unknown Artist', '']:
            audio.add(TPE2(encoding=3, text=metadata['album_artist']))
        
        year = _extract_year(metadata)
        if year:
            audio.delall('TDRC')
            audio.delall('TYER')
            audio.add(TDRC(encoding=3, text=year))
            audio.add(TYER(encoding=3, text=year))

        if metadata.get('track_number') and metadata['track_number'] not in [0, '0']:
            audio.add(TRCK(encoding=3, text=str(metadata['track_number'])))
        
        if metadata.get('disc_number') and metadata['disc_number'] not in [0, '0']:
            audio.add(TPOS(encoding=3, text=str(metadata['disc_number'])))

        if metadata.get('isrc') and metadata['isrc'] not in ['', 'Unknown']:
            audio.add(TSRC(encoding=3, text=metadata['isrc']))
        
        # Genre
        if metadata.get('genre') and metadata['genre'] not in ['Unknown', '']:
            audio.add(TCON(encoding=3, text=metadata['genre']))
        
        # Explicit flag
        if metadata.get('explicit'):
            audio.add(TXXX(encoding=3, desc='EXPLICIT', text=['Yes']))
        
        # Spotify URL
        if metadata.get('spotify_url'):
            audio.add(TXXX(encoding=3, desc='SPOTIFY_URL', text=[metadata['spotify_url']]))
        
        # Source URL (for non-Spotify platforms)
        if metadata.get('source_url') and not metadata.get('spotify_url'):
            audio.add(TXXX(encoding=3, desc='SOURCE_URL', text=[metadata['source_url']]))
        
        # Featured artists
        if metadata.get('featured_artists'):
            featured_str = ', '.join(metadata['featured_artists'])
            audio.add(TXXX(encoding=3, desc='FEATURED_ARTISTS', text=[featured_str]))
        
        # Version type
        if metadata.get('version_type') and metadata['version_type'] != 'original':
            audio.add(TXXX(encoding=3, desc='VERSION_TYPE', text=[metadata['version_type']]))
        
        # Tags
        if metadata.get('tags'):
            tags_str = ', '.join(metadata['tags'])
            audio.add(TXXX(encoding=3, desc='TAGS', text=[tags_str]))
        
        # Language
        if metadata.get('language') and metadata['language'] not in ['Unknown', '']:
            audio.add(TXXX(encoding=3, desc='LANGUAGE', text=[metadata['language']]))

        lyrics_val = metadata.get('lyrics-eng') or metadata.get('LYRICS')
        if lyrics_val:
            # Check if we should override existing lyrics
            existing_lyrics = ''
            if audio:
                for frame in audio.getall('USLT'):
                    if frame.desc.lower() == '':
                        existing_lyrics = frame.text
                        break
            
            if should_override_lyrics(existing_lyrics, lyrics_val):
                audio.add(USLT(encoding=3, lang='eng', desc='', text=lyrics_val))
                has_ts = has_timestamps(lyrics_val)
                ts_label = '(synced)' if has_ts else '(plain text)'
                print(f" [metadata] Lyrics embedded into MP3 ({len(lyrics_val)} chars) {ts_label}")
            else:
                print(f" [metadata] Kept existing lyrics (incoming plain text, existing synced)")
        else:
            print(" [metadata] No lyrics to embed (MP3)")

        if cover_path and os.path.exists(cover_path):
            with open(cover_path, 'rb') as f:
                image_data = f.read()

            audio.add(APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=image_data
            ))

        audio.save()
        print(" MP3 metadata embedded")

    except Exception as e:
        print(f" Failed to embed MP3 metadata: {e}")

def embed_m4a_metadata(filepath, metadata, cover_path=None):
    """Embed metadata into M4A/MP4 file"""
    print("Embedding metadata into M4A...")

    try:
        audio = MP4(filepath)

        # Only update fields if they have values (don't overwrite with empty/Unknown)
        if metadata.get('title') and metadata['title'] not in ['Unknown Title', '']:
            audio['\xa9nam'] = metadata['title']
        
        if metadata.get('artist') and metadata['artist'] not in ['Unknown Artist', '']:
            audio['\xa9ART'] = metadata['artist']
        
        if metadata.get('album') and metadata['album'] not in ['Unknown Album', '']:
            audio['\xa9alb'] = metadata['album']
        
        if metadata.get('album_artist') and metadata['album_artist'] not in ['Unknown Artist', '']:
            audio['aART'] = metadata['album_artist']
        
        year = _extract_year(metadata)
        if year:
            audio['\xa9day'] = year

        if metadata.get('track_number') and metadata['track_number'] not in [0, '0']:
            audio['trkn'] = [(metadata['track_number'], 0)]
        
        if metadata.get('disc_number') and metadata['disc_number'] not in [0, '0']:
            audio['disk'] = [(metadata['disc_number'], 0)]

        if cover_path and os.path.exists(cover_path):
            with open(cover_path, 'rb') as f:
                image_data = f.read()

            audio['covr'] = [MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)]
        
        # Genre
        if metadata.get('genre') and metadata['genre'] not in ['Unknown', '']:
            audio['©gen'] = metadata['genre']
        
        # Explicit flag
        if metadata.get('explicit'):
            audio['----:com.apple.itunes:EXPLICIT'] = [b'Yes']
        
        # Spotify URL
        if metadata.get('spotify_url'):
            audio['----:com.apple.itunes:SPOTIFY_URL'] = [metadata['spotify_url'].encode('utf-8')]
        
        # Source URL (for non-Spotify platforms)
        if metadata.get('source_url') and not metadata.get('spotify_url'):
            audio['----:com.apple.itunes:SOURCE_URL'] = [metadata['source_url'].encode('utf-8')]
        
        # Featured artists
        if metadata.get('featured_artists'):
            featured_str = ', '.join(metadata['featured_artists'])
            audio['----:com.apple.itunes:FEATURED_ARTISTS'] = [featured_str.encode('utf-8')]
        
        # Version type
        if metadata.get('version_type') and metadata['version_type'] != 'original':
            audio['----:com.apple.itunes:VERSION_TYPE'] = [metadata['version_type'].encode('utf-8')]
        
        # Tags
        if metadata.get('tags'):
            tags_str = ', '.join(metadata['tags'])
            audio['----:com.apple.itunes:TAGS'] = [tags_str.encode('utf-8')]
        
        # Language
        if metadata.get('language') and metadata['language'] not in ['Unknown', '']:
            audio['----:com.apple.itunes:LANGUAGE'] = [metadata['language'].encode('utf-8')]

        lyrics_val = metadata.get('lyrics-eng') or metadata.get('LYRICS')
        if lyrics_val:
            # Check if we should override existing lyrics
            existing_lyrics = str((audio.get('©lyr') or [''])[0]) if audio.get('©lyr') else ''
            
            if should_override_lyrics(existing_lyrics, lyrics_val):
                audio['©lyr'] = lyrics_val
                has_ts = has_timestamps(lyrics_val)
                ts_label = '(synced)' if has_ts else '(plain text)'
                print(f" [metadata] Lyrics embedded into M4A ({len(lyrics_val)} chars) {ts_label}")
            else:
                print(f" [metadata] Kept existing lyrics (incoming plain text, existing synced)")
        else:
            print(" [metadata] No lyrics to embed (M4A)")

        audio.save()
        print(" M4A metadata embedded")

    except Exception as e:
        print(f" Failed to embed M4A metadata: {e}")

def embed_metadata(filepath, metadata):
    """Auto-detect format and embed metadata"""
    ext = os.path.splitext(filepath)[1].lower()

    cover_path = None
    if metadata.get('cover_url'):
        cover_path = filepath + '.cover.jpg'
        result = download_cover_art(metadata['cover_url'], cover_path)  # ← capture return
        if not result:
            cover_path = None  # ← don't pass a non-existent path downstream

    if ext == '.flac':
        embed_flac_metadata(filepath, metadata, cover_path)
    elif ext == '.mp3':
        embed_mp3_metadata(filepath, metadata, cover_path)
    elif ext in ['.m4a', '.mp4']:
        embed_m4a_metadata(filepath, metadata, cover_path)
    else:
        print(f" Unsupported format for metadata: {ext}")

    if cover_path and os.path.exists(cover_path):
        os.remove(cover_path)

if __name__ == '__main__':

    pass
