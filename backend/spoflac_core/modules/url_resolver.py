"""Unified URL resolver + metadata fetcher.

Design
------
Pass *any* supported track URL (Spotify, Tidal, Qobuz, Amazon, SoundCloud,
Deezer …) to URLResolver.resolve() and get back a single, consistent dict:

    {
        'metadata':        dict,
        'sl_result':       dict,
        'spotify_id':      str | None,
        'source_platform': str,
        'metadata_source': str,
    }

Metadata priority
-----------------
1. Spotify API  (full: title, artist, album, ISRC, cover, duration, …)
2. song.link entity data  (title, artistName, thumbnailUrl — always present)

Download decisions and fallback chains can then be based purely on
sl_result['tidal_url'], sl_result['qobuz_url'], etc.
"""
from __future__ import annotations

import re
import unicodedata
import urllib.parse
from typing import Optional

import requests

from spoflac_core.modules.songlink import SongLinkClient
from spoflac_core.modules.spotify import SpotifyClient
from spoflac_core.modules.url_detector import URLDetector

_LRCLIB_API = "https://lrclib.net/api/get"


def _fetch_lyrics_lrclib(title: str, artist: str, album: str = '', duration_ms: int = 0) -> str | None:
    """
    Fetch plain-text lyrics from lrclib.net — free, no auth required.
    Uses track_name + artist_name + optional album_name + duration (seconds).
    """
    params: dict = {
        'track_name': title,
        'artist_name': artist,
    }
    if album:
        params['album_name'] = album
    if duration_ms:
        params['duration'] = round(duration_ms / 1000)

    print(f" [lyrics/lrclib] Querying: {title} — {artist} ({params.get('duration', '?')}s)")
    try:
        resp = requests.get(_LRCLIB_API, params=params, timeout=10,
                            headers={'User-Agent': 'spotiflac/1.0 (github.com/spotiflac)'})
        print(f" [lyrics/lrclib] HTTP {resp.status_code}")
        if resp.status_code == 404:
            print(f" [lyrics/lrclib] No lyrics found (404)")
            return None
        if resp.status_code != 200:
            print(f" [lyrics/lrclib] Failed — {resp.text[:200]}")
            return None
        data = resp.json()
    except Exception as exc:
        print(f" [lyrics/lrclib] Request error: {exc}")
        return None

    # Prefer synced (LRC) lyrics — stored with [mm:ss.xx] timestamps.
    # Modern players (foobar2000, MusicBee, Poweramp, AIMP, VLC, etc.) parse
    # LRC format from the LYRICS/USLT tag and show scrolling highlighted lines.
    synced = (data.get('syncedLyrics') or '').strip()
    if synced:
        print(f" [lyrics/lrclib] ✅ Got synced/timestamped lyrics ({len(synced)} chars)")
        return synced

    # Fall back to plain text when no synced version exists
    plain = (data.get('plainLyrics') or '').strip()
    if plain:
        print(f" [lyrics/lrclib] ✅ Got plain lyrics ({len(plain)} chars) — no synced version")
        return plain

    print(f" [lyrics/lrclib] Response had no usable lyrics text")
    return None


# ── Unicode-block → aksharamukha script name map ──────────────────────────────
# Each entry: (aksharamukha_name, unicode_start, unicode_end)
_SCRIPT_BLOCKS = [
    ('Devanagari', 0x0900, 0x097F),   # Hindi, Marathi, Sanskrit, Nepali, …
    ('Bengali',    0x0980, 0x09FF),
    ('Gurmukhi',   0x0A00, 0x0A7F),   # Punjabi
    ('Gujarati',   0x0A80, 0x0AFF),
    ('Oriya',      0x0B00, 0x0B7F),
    ('Tamil',      0x0B80, 0x0BFF),
    ('Telugu',     0x0C00, 0x0C7F),
    ('Kannada',    0x0C80, 0x0CFF),
    ('Malayalam',  0x0D00, 0x0D7F),
    ('Sinhala',    0x0D80, 0x0DFF),
    ('Thai',       0x0E00, 0x0E7F),
    ('Lao',        0x0E80, 0x0EFF),
    ('Tibetan',    0x0F00, 0x0FFF),
    ('Burmese',    0x1000, 0x109F),
    ('Khmer',      0x1780, 0x17FF),
    ('Arabic',     0x0600, 0x06FF),
    ('Hebrew',     0x0590, 0x05FF),
    ('Cyrillic',   0x0400, 0x04FF),
    ('Greek',      0x0370, 0x03FF),
]

def _detect_script(text: str) -> str | None:
    """
    Return the dominant Unicode script name (aksharamukha-compatible) in text,
    or None if the text is already Latin/ASCII or contains no detectable script.
    """
    counts: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        for name, start, end in _SCRIPT_BLOCKS:
            if start <= cp <= end:
                counts[name] = counts.get(name, 0) + 1
                break
    if not counts:
        return None
    return max(counts, key=lambda k: counts[k])


_LRC_LINE_RE = re.compile(r'^(\[\d+:\d+\.\d+\])\s*(.*)')


def _normalize_roman(text: str) -> str:
    """
    Convert ISO-15919 diacritic romanization to natural ASCII.

    ēmannāvō, ēṁ vinnānō!  →  emannavо, em vinnano!

    Strategy: NFKD-decompose (splits char + combining mark), then drop
    all Unicode combining/modifier characters, leaving plain ASCII.
    Also maps a small set of special chars not handled by NFKD.
    """
    _SPECIAL = {
        'ṭ': 't', 'ḍ': 'd', 'ṇ': 'n', 'ṣ': 'sh', 'ś': 'sh',
        'ḥ': 'h', 'ḷ': 'l', 'ẖ': 'h',
        'Ṭ': 'T', 'Ḍ': 'D', 'Ṇ': 'N', 'Ṣ': 'Sh', 'Ś': 'Sh',
    }
    out = []
    for ch in unicodedata.normalize('NFKD', text):
        if ch in _SPECIAL:
            out.append(_SPECIAL[ch])
        elif unicodedata.category(ch).startswith('M'):  # Mark (combining)
            pass  # drop — this strips ā→a, ē→e, ō→o, ṁ→m, etc.
        else:
            out.append(ch)
    return ''.join(out)


def _romanize_lrc_lyrics(lrc_text: str) -> str:
    """
    Parse LRC-formatted (or plain) lyrics and insert a natural romanized copy
    of each non-Latin line immediately below the original at the same timestamp.

    Example input line:
        [00:16.90] ఏమన్నావో, ఏం విన్నానో!
    Becomes:
        [00:16.90] ఏమన్నావో, ఏం విన్నానో!
        [00:16.90] emannavо, em vinnano!

    Lines that are already Latin, empty, or instrumental (♪) are left as-is.
    Falls back gracefully to the original text if aksharamukha is not installed.
    """
    try:
        from aksharamukha import transliterate as aksha
    except ImportError:
        print(" [romanize] aksharamukha not installed — skipping romanization")
        return lrc_text

    result: list[str] = []
    any_romanized = False

    for raw_line in lrc_text.splitlines():
        result.append(raw_line)

        m = _LRC_LINE_RE.match(raw_line)
        if m:
            timestamp, text = m.group(1), m.group(2).strip()
        else:
            # Plain text (no timestamp)
            timestamp, text = None, raw_line.strip()

        if not text or text in ('♪', '\u266a'):
            continue

        script = _detect_script(text)
        if not script:
            continue  # already Latin

        try:
            roman = aksha.process(script, 'ISO', text).strip()
            roman = _normalize_roman(roman)   # strip diacritics → natural ASCII
        except Exception as exc:
            print(f" [romanize] {script} → ISO failed for '{text[:30]}': {exc}")
            continue

        if roman and roman != text:
            line = f"{timestamp} {roman}" if timestamp else roman
            result.append(line)
            any_romanized = True

    if any_romanized:
        print(f" [romanize] ✅ Interleaved romanized lines added")
    else:
        print(f" [romanize] No non-Latin lines found — romanization skipped")

    return '\n'.join(result)

_SONGLINK_SUPPORTED = {
    'spotify', 'tidal', 'qobuz', 'amazon', 'soundcloud', 'deezer',
    'appleMusic', 'youtube', 'youtubeMusic',
}

def _detect_platform(url: str) -> str:
    """Extend URLDetector to also handle SoundCloud and Deezer."""

    platform, _ = URLDetector().get_track_id(url)
    if platform:
        return platform

    url_lower = url.lower()
    if 'soundcloud.com' in url_lower:
        return 'soundcloud'
    if 'deezer.com' in url_lower:
        return 'deezer'
    if 'music.apple.com' in url_lower or 'itunes.apple.com' in url_lower:
        return 'appleMusic'
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    return 'unknown'

class URLResolver:
    """
    Resolve any track URL to metadata + all platform download URLs.

    Usage
    -----
        resolver = URLResolver()
        result   = resolver.resolve("https://soundcloud.com/artist/track")

        metadata = result['metadata']
        sl       = result['sl_result']
    """

    def __init__(self):
        self._sl  = SongLinkClient()
        self._spy: Optional[SpotifyClient] = None

    def _spotify_client(self) -> SpotifyClient:
        if self._spy is None:
            self._spy = SpotifyClient()
        return self._spy

    def resolve(self, url: str) -> dict:
        """
        Main entry point.

        Parameters
        ----------
        url : str
            Any track URL supported by song.link.

        Returns
        -------
        dict with keys:
            metadata        : dict  — ID3-ready metadata dict (Spotify or fallback)
            sl_result       : dict  — all platform URLs from song.link
            spotify_id      : str | None
            source_platform : str   — detected platform of the input URL
            metadata_source : str   — 'spotify' or 'songlink'
        """
        source_platform = _detect_platform(url)
        print(f" [resolver] Source platform: {source_platform}")

        if source_platform == 'spotify':

            _, spotify_id = URLDetector().get_track_id(url)
            if not spotify_id:
                raise Exception(f"Could not parse Spotify track ID from: {url}")
            sl_result = self._sl.get_all_urls(spotify_id)
        else:

            sl_result = self._sl.resolve_from_url(url)
            spotify_id = sl_result.get('spotify_id')

        metadata: dict | None = None
        metadata_source = 'songlink'

        if spotify_id:
            try:
                spy = self._spotify_client()

                metadata = spy.get_track_metadata(spotify_id)
                metadata_source = 'spotify'
                print(f" [resolver] Spotify metadata: {metadata['artist']} – {metadata['title']}")

                # Fetch lyrics (non-fatal — missing lyrics should never block a download)
                try:
                    lyrics = spy.get_lyrics(spotify_id)
                    if not lyrics:
                        # Spotify API failed/unavailable — try lrclib.net
                        print(f" [resolver] Spotify lyrics unavailable, trying lrclib.net...")
                        lyrics = _fetch_lyrics_lrclib(
                            title=metadata['title'],
                            artist=metadata['artist'],
                            album=metadata.get('album', ''),
                            duration_ms=metadata.get('duration_ms', 0),
                        )
                    if lyrics:
                        lyrics = _romanize_lrc_lyrics(lyrics)
                        metadata['lyrics'] = lyrics
                        print(f" [resolver] ✅ Lyrics ready ({len(lyrics)} chars)")
                    else:
                        print(f" [resolver] ❌ Lyrics not available from any source")
                except Exception as lyr_exc:
                    print(f" [resolver] Lyrics fetch failed ({lyr_exc}) — skipping lyrics")

            except Exception as e:
                print(f" [resolver] Spotify metadata failed ({e}) — using song.link fallback")

        if metadata is None:
            sl_meta = sl_result.get('sl_metadata')
            if sl_meta:
                metadata = sl_meta
                print(f" [resolver] Fallback metadata: {metadata['artist']} – {metadata['title']}")
            else:
                raise Exception(
                    "Could not obtain metadata: Spotify lookup failed and song.link "
                    "returned no entity data for this URL."
                )

        return {
            'metadata':        metadata,
            'sl_result':       sl_result,
            'spotify_id':      spotify_id,
            'source_platform': source_platform,
            'metadata_source': metadata_source,
        }

    def resolve_metadata_only(self, url: str) -> dict:
        """
        Convenience: just return the metadata dict (no download URLs).
        Useful for search previews or tag-only workflows.
        """
        return self.resolve(url)['metadata']

if __name__ == '__main__':
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else \
        'https://soundcloud.com/jinduniverse/high-on-you'

    resolver = URLResolver()
    result = resolver.resolve(test_url)

    print("\n── Result ──────────────────────────────────────────────")
    print(f"Source platform : {result['source_platform']}")
    print(f"Metadata source : {result['metadata_source']}")
    print(f"Spotify ID      : {result['spotify_id']}")
    m = result['metadata']
    print(f"Title           : {m['title']}")
    print(f"Artist          : {m['artist']}")
    print(f"Album           : {m['album']}")
    print(f"ISRC            : {m.get('isrc')}")
    print(f"Cover           : {m.get('cover_url')}")
    sl = result['sl_result']
    print(f"\nTidal URL       : {sl.get('tidal_url')}")
    print(f"Qobuz URL       : {sl.get('qobuz_url')}")
    print(f"Amazon URL      : {sl.get('amazon_url')}")
    print(f"SoundCloud URL  : {sl.get('soundcloud_url')}")
