"""Audio metadata embedding for FLAC and MP3 files"""
import os
import requests
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, TPOS, TPE2, USLT, APIC, TSRC
from mutagen.mp4 import MP4, MP4Cover
from config import USER_AGENT

def download_cover_art(cover_url, output_path):
    """Download album cover art"""
    if not cover_url:
        return None

    try:
        print(f"Downloading cover art...")
        response = requests.get(cover_url, headers={'User-Agent': USER_AGENT}, timeout=30)

        if response.status_code != 200:
            print(f"⚠ Failed to download cover: HTTP {response.status_code}")
            return None

        with open(output_path, 'wb') as f:
            f.write(response.content)

        print(f"✓ Cover art saved")
        return output_path

    except Exception as e:
        print(f"⚠ Failed to download cover: {e}")
        return None

def embed_flac_metadata(filepath, metadata, cover_path=None):
    """Embed metadata into FLAC file"""
    print("Embedding metadata into FLAC...")

    try:
        audio = FLAC(filepath)

        audio['TITLE'] = metadata.get('title', '')
        audio['ARTIST'] = metadata.get('artist', '')
        audio['ALBUM'] = metadata.get('album', '')
        audio['ALBUMARTIST'] = metadata.get('album_artist', '')
        audio['DATE'] = metadata.get('release_date', '')[:4]

        if metadata.get('track_number'):
            audio['TRACKNUMBER'] = str(metadata['track_number'])
        if metadata.get('disc_number'):
            audio['DISCNUMBER'] = str(metadata['disc_number'])

        if metadata.get('copyright'):
            audio['COPYRIGHT'] = metadata['copyright']
        if metadata.get('publisher'):
            audio['PUBLISHER'] = metadata['publisher']
        if metadata.get('isrc'):
            audio['ISRC'] = metadata['isrc']
        if metadata.get('lyrics'):
            audio['LYRICS'] = metadata['lyrics']

        audio['DESCRIPTION'] = 'Downloaded with  Python -'

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
        print("✓ FLAC metadata embedded")

    except Exception as e:
        print(f"⚠ Failed to embed FLAC metadata: {e}")

def embed_mp3_metadata(filepath, metadata, cover_path=None):
    """Embed metadata into MP3 file using ID3v2"""
    print("Embedding metadata into MP3...")

    try:
        audio = ID3(filepath)

        audio.add(TIT2(encoding=3, text=metadata.get('title', '')))
        audio.add(TPE1(encoding=3, text=metadata.get('artist', '')))
        audio.add(TALB(encoding=3, text=metadata.get('album', '')))
        audio.add(TPE2(encoding=3, text=metadata.get('album_artist', '')))
        audio.add(TDRC(encoding=3, text=metadata.get('release_date', '')[:4]))

        if metadata.get('track_number'):
            audio.add(TRCK(encoding=3, text=str(metadata['track_number'])))
        if metadata.get('disc_number'):
            audio.add(TPOS(encoding=3, text=str(metadata['disc_number'])))

        if metadata.get('isrc'):
            audio.add(TSRC(encoding=3, text=metadata['isrc']))

        if metadata.get('lyrics'):
            audio.add(USLT(encoding=3, lang='eng', desc='', text=metadata['lyrics']))

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
        print("✓ MP3 metadata embedded")

    except Exception as e:
        print(f"⚠ Failed to embed MP3 metadata: {e}")

def embed_m4a_metadata(filepath, metadata, cover_path=None):
    """Embed metadata into M4A/MP4 file"""
    print("Embedding metadata into M4A...")

    try:
        audio = MP4(filepath)

        audio['\xa9nam'] = metadata.get('title', '')
        audio['\xa9ART'] = metadata.get('artist', '')
        audio['\xa9alb'] = metadata.get('album', '')
        audio['aART'] = metadata.get('album_artist', '')
        audio['\xa9day'] = metadata.get('release_date', '')[:4]

        if metadata.get('track_number'):
            audio['trkn'] = [(metadata['track_number'], 0)]
        if metadata.get('disc_number'):
            audio['disk'] = [(metadata['disc_number'], 0)]

        if cover_path and os.path.exists(cover_path):
            with open(cover_path, 'rb') as f:
                image_data = f.read()

            audio['covr'] = [MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)]

        audio.save()
        print("✓ M4A metadata embedded")

    except Exception as e:
        print(f"⚠ Failed to embed M4A metadata: {e}")

def embed_metadata(filepath, metadata):
    """Auto-detect format and embed metadata"""
    ext = os.path.splitext(filepath)[1].lower()

    cover_path = None
    if metadata.get('cover_url'):
        cover_path = filepath + '.cover.jpg'
        download_cover_art(metadata['cover_url'], cover_path)

    if ext == '.flac':
        embed_flac_metadata(filepath, metadata, cover_path)
    elif ext == '.mp3':
        embed_mp3_metadata(filepath, metadata, cover_path)
    elif ext in ['.m4a', '.mp4']:
        embed_m4a_metadata(filepath, metadata, cover_path)
    else:
        print(f"⚠ Unsupported format for metadata: {ext}")

    if cover_path and os.path.exists(cover_path):
        os.remove(cover_path)

if __name__ == '__main__':

    pass
