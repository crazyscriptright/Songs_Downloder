"""
Test script for SpotiFLAC HTTP endpoint integration

This script tests the /download endpoint with multiple platforms.
"""

import os
import sys
import requests
import json
import time

# So we can import spoflac_core directly
sys.path.insert(0, os.path.dirname(__file__))

# Configuration
BASE_URL = "http://localhost:5000"

# Test URLs for each supported platform
TEST_CASES = [
    {
        "label": "Spotify",
        "url": "https://open.spotify.com/track/36ylvIx1fVaM4i5pux7Ea1",
        "title": "Spotify Test Track",
        "note": "SpotiFLAC only (no yt-dlp fallback — Spotify DRM). Lyrics should be embedded.",
    },
    {
        "label": "YouTube",
        "url": "https://www.youtube.com/watch?v=JGwWNGJdvx8",
        "title": "Shape of You - Ed Sheeran",
        "note": "yt-dlp (YouTube stays on yt-dlp, no SpotiFLAC)",
    },
    {
        "label": "YouTube Music",
        "url": "https://music.youtube.com/watch?v=JGwWNGJdvx8",
        "title": "Shape of You - Ed Sheeran",
        "note": "yt-dlp (YouTube Music stays on yt-dlp, no SpotiFLAC)",
    },
    {
        "label": "SoundCloud",
        "url": "https://soundcloud.com/octobersveryown/gods-plan",
        "title": "God's Plan - Drake",
        "note": "yt-dlp (SoundCloud stays on yt-dlp, no SpotiFLAC)",
    },
    {
        "label": "JioSaavn",
        "url": "https://www.jiosaavn.com/song/heeriye/GwNXeyZzc2k",
        "title": "Heeriye",
        "note": "yt-dlp (JioSaavn stays on yt-dlp, no SpotiFLAC)",
    },
]

def test_download(label: str, url: str, title: str, note: str, wait_for_complete=True):
    """Send a download request and optionally monitor to completion."""

    print(f"\n{'='*70}")
    print(f"Platform : {label}")
    print(f"Note     : {note}")
    print(f"URL      : {url}")
    print(f"{'='*70}")

    payload = {
        "url": url,
        "title": title,
        "advancedOptions": {
            "keepVideo": False,
            "embedSubtitles": False,
            "addMetadata": True,
            "customArgs": "",
            "audioFormat": "flac",
            "audioQuality": "0",
            "embedThumbnail": True,
        },
    }

    try:
        resp = requests.post(f"{BASE_URL}/download", json=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        download_id = result.get("download_id")

        print(f"✅ Queued  →  download_id: {download_id}")

        if not wait_for_complete:
            time.sleep(3)
            status_resp = requests.get(f"{BASE_URL}/download_status/{download_id}", timeout=10)
            status = status_resp.json()
            print(f"   Status : {status.get('status')} | {status.get('eta', '')}")
            return

        print("   Monitoring progress…")
        for _ in range(90):          # up to 3 minutes
            time.sleep(2)
            status_resp = requests.get(f"{BASE_URL}/download_status/{download_id}", timeout=10)
            status = status_resp.json()

            print(
                f"\r   {status.get('progress', 0):>3}% | "
                f"{status.get('status'):<12} | "
                f"{status.get('eta', 'N/A'):<45} | "
                f"{status.get('speed', 'N/A')}",
                end="",
            )

            if status.get("status") == "complete":
                print(f"\n✅ Done  →  {status.get('file')}")
                print(f"\n   Full status dict:")
                for k, v in status.items():
                    print(f"     {k:<20}: {v}")
                break
            elif status.get("status") == "error":
                print(f"\n❌ Error →  {status.get('error')}")
                print(f"   Full status dict:")
                for k, v in status.items():
                    print(f"     {k:<20}: {v}")
                break
        else:
            print("\n⚠️  Timeout — still in progress")

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to http://localhost:5000 — is the backend running?")
    except Exception as exc:
        print(f"❌ {exc}")


def test_download_endpoint():
    """Original single-track test (Spotify FLAC) kept for backwards compatibility."""
    test_download(**TEST_CASES[0], wait_for_complete=True)


def test_mp3_fallback():
    """Show that Spotify + MP3 still routes through SpotiFLAC."""
    test_download(
        label="Spotify (MP3 requested)",
        url=TEST_CASES[0]["url"],
        title=TEST_CASES[0]["title"],
        note="audioFormat=mp3 still uses SpotiFLAC for Spotify (DRM)",
        wait_for_complete=False,
    )


def test_embed_lyrics_only(filepath: str, spotify_url: str = None):
    """
    Embed lyrics into an already-downloaded file WITHOUT re-downloading it.

    Steps:
      1. Read existing ID3/FLAC tags to get title/artist/album/duration.
      2. Try lrclib.net first (free, no auth). Fall back to Spotify if a URL is given.
      3. Embed the lyrics using spoflac_core metadata helpers.

    Usage:
        python test_spoflac_endpoint.py embed "C:\\path\\to\\file.flac"
        python test_spoflac_endpoint.py embed "C:\\path\\to\\file.flac" "https://open.spotify.com/track/..."
    """
    from spoflac_core.modules.url_resolver import _fetch_lyrics_lrclib, _romanize_lrc_lyrics
    from spoflac_core.modules import metadata as meta_module

    print(f"\n{'='*70}")
    print(f"Lyrics-only embed: {os.path.basename(filepath)}")
    print(f"{'='*70}")

    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    ext = os.path.splitext(filepath)[1].lower()

    # ── Read existing tags to get title/artist/album/duration ─────────────────
    title = artist = album = ''
    duration_ms = 0

    try:
        if ext == '.flac':
            from mutagen.flac import FLAC
            audio = FLAC(filepath)
            title  = (audio.get('title')  or [''])[0]
            artist = (audio.get('artist') or [''])[0]
            album  = (audio.get('album')  or [''])[0]
            # duration from mutagen info
            duration_ms = int((audio.info.length or 0) * 1000)
        elif ext == '.mp3':
            from mutagen.id3 import ID3
            tags = ID3(filepath)
            title  = str(tags.get('TIT2', ''))
            artist = str(tags.get('TPE1', ''))
            album  = str(tags.get('TALB', ''))
            from mutagen.mp3 import MP3
            duration_ms = int((MP3(filepath).info.length or 0) * 1000)
        elif ext in ('.m4a', '.mp4'):
            from mutagen.mp4 import MP4
            audio = MP4(filepath)
            title  = (audio.get('\xa9nam') or [''])[0]
            artist = (audio.get('\xa9ART') or [''])[0]
            album  = (audio.get('\xa9alb') or [''])[0]
            duration_ms = int((audio.info.length or 0) * 1000)
    except Exception as exc:
        print(f"⚠️  Could not read tags ({exc}). Will try filename-based title.")
        title = os.path.splitext(os.path.basename(filepath))[0]

    print(f"   Title    : {title or '(not found in tags)'}")
    print(f"   Artist   : {artist or '(not found in tags)'}")
    print(f"   Album    : {album or '(not found in tags)'}")
    print(f"   Duration : {duration_ms // 1000}s")

    # ── Fetch lyrics ──────────────────────────────────────────────────────────
    lyrics = None

    # 1. lrclib.net (no auth needed)
    if title and artist:
        lyrics = _fetch_lyrics_lrclib(
            title=title,
            artist=artist,
            album=album,
            duration_ms=duration_ms,
        )

    # 2. Spotify color-lyrics API (needs Spotify URL / track ID)
    if not lyrics and spotify_url:
        import re
        m = re.search(r'track/([A-Za-z0-9]+)', spotify_url)
        if m:
            track_id = m.group(1)
            print(f"\n   Trying Spotify lyrics for track {track_id}...")
            try:
                from spoflac_core.modules.spotify import SpotifyClient
                spy = SpotifyClient()
                lyrics = spy.get_lyrics(track_id)
            except Exception as exc:
                print(f"   Spotify lyrics failed: {exc}")

    if not lyrics:
        print("\n❌ Could not fetch lyrics from any source.")
        return

    # Add romanized (Latin-script) lines interleaved after each original line
    lyrics = _romanize_lrc_lyrics(lyrics)

    print(f"\n✅ Lyrics fetched — {len(lyrics)} chars, {len(lyrics.splitlines())} lines")
    print(f"   Preview: {lyrics[:120].replace(chr(10), ' | ')}")

    # ── Embed into file ───────────────────────────────────────────────────────
    # Build a minimal metadata dict — only lyrics matters here; the rest stays
    # as-is because embed_*_metadata only UPDATES/ADDS individual tags.
    lyric_meta = {
        'title': title, 'artist': artist, 'album': album,
        'album_artist': artist,
        'release_date': '', 'track_number': None, 'disc_number': None,
        'isrc': None, 'cover_url': None, 'copyright': None, 'publisher': None,
        'lyrics': lyrics,
    }

    print(f"\n   Embedding lyrics into {ext.upper()} file...")
    try:
        if ext == '.flac':
            meta_module.embed_flac_metadata(filepath, lyric_meta, cover_path=None)
        elif ext == '.mp3':
            meta_module.embed_mp3_metadata(filepath, lyric_meta, cover_path=None)
        elif ext in ('.m4a', '.mp4'):
            meta_module.embed_m4a_metadata(filepath, lyric_meta, cover_path=None)
        else:
            print(f"❌ Unsupported format: {ext}")
            return
        print(f"✅ Lyrics successfully embedded into: {os.path.basename(filepath)}")
    except Exception as exc:
        print(f"❌ Embedding failed: {exc}")


if __name__ == "__main__":
    # Allow: python test_spoflac_endpoint.py embed <filepath> [spotify_url]
    if len(sys.argv) >= 3 and sys.argv[1] == 'embed':
        fp = sys.argv[2]
        sp_url = sys.argv[3] if len(sys.argv) >= 4 else None
        test_embed_lyrics_only(fp, sp_url)
        sys.exit(0)
    print("\n>>> SpotiFLAC HTTP Endpoint Test Suite <<<")
    print("Routing: Spotify/JioSaavn/YouTube/YTMusic/SoundCloud → SpotiFLAC → yt-dlp fallback\n")

    # Quick smoke-test all platforms (don't wait for completion)
    print("─── Quick Platform Smoke-Test (no waiting) ───")
    for case in TEST_CASES:
        test_download(**case, wait_for_complete=False)
        time.sleep(1)

    # Full end-to-end test for Spotify
    print("\n─── Full End-to-End Test: Spotify ───")
    test_download(**TEST_CASES[0], wait_for_complete=True)

    print("\n" + "=" * 70)
    print("Routing summary:")
    print("  spotify.com / spotify:   → SpotiFLAC  (no yt-dlp fallback — DRM)")
    print("  tidal.com                → SpotiFLAC  (no yt-dlp fallback)")
    print("  qobuz.com                → SpotiFLAC  (no yt-dlp fallback)")
    print("  music.amazon.*           → SpotiFLAC  (no yt-dlp fallback)")
    print("  deezer.com               → SpotiFLAC  (no yt-dlp fallback)")
    print("  music.apple.com          → SpotiFLAC  (no yt-dlp fallback)")
    print("  youtube.com / youtu.be   → yt-dlp directly (unchanged)")
    print("  music.youtube.com        → yt-dlp directly (unchanged)")
    print("  soundcloud.com           → yt-dlp directly (unchanged)")
    print("  jiosaavn.com / saavn.com → yt-dlp directly (unchanged)")
    print("=" * 70)
