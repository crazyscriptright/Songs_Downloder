"""SongLink API client for URL conversion and ISRC extraction.

Key design: get_all_urls() makes ONE song.link API call and returns every
platform URL + ISRC together.  Downstream code (main.py, flac_download.py)
should call get_all_urls() once and reuse the result across the fallback
loop — never call the API once per service.
"""
import time
import requests
from urllib.parse import quote
from config import SONGLINK_API, DEEZER_API, SONGLINK_MIN_DELAY, SONGLINK_RETRY_DELAY, USER_AGENT


class SongLinkClient:
    def __init__(self):
        self.last_call_time = 0
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})

    # ── internal helpers ────────────────────────────────────────────────────

    def _rate_limit(self):
        """Enforce minimum delay between successive song.link calls."""
        elapsed = time.time() - self.last_call_time
        if elapsed < SONGLINK_MIN_DELAY:
            sleep_time = SONGLINK_MIN_DELAY - elapsed
            print(f"  Rate limiting: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)

    def _fetch_raw(self, source_url: str, retries: int = 3) -> dict:
        """
        Make a single GET request to the song.link API for *any* URL
        (Spotify, Tidal, Qobuz, Amazon, SoundCloud, Deezer …) and return
        the full parsed response dict.  Handles 429 retries internally.
        """
        self._rate_limit()
        api_url = f"{SONGLINK_API}?url={quote(source_url)}"

        for attempt in range(retries):
            try:
                response = self.session.get(api_url, timeout=30)
                self.last_call_time = time.time()

                if response.status_code == 429:
                    wait = SONGLINK_RETRY_DELAY * (attempt + 1)
                    print(f"  Rate limited by song.link, waiting {wait}s (attempt {attempt+1}/{retries})...")
                    time.sleep(wait)
                    continue

                if response.status_code != 200:
                    raise Exception(f"SongLink API error: HTTP {response.status_code}")

                return response.json()

            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    raise Exception(f"SongLink API request failed: {e}")
                time.sleep(3)

        raise Exception(f"SongLink API failed after {retries} attempts")

    def _fetch_songlink(self, spotify_id: str, retries: int = 3) -> dict:
        """Backward-compat wrapper: builds Spotify URL then calls _fetch_raw."""
        spotify_url = f"https://open.spotify.com/track/{spotify_id}"
        print(f" [song.link] Fetching all platform URLs for Spotify ID: {spotify_id}")
        return self._fetch_raw(spotify_url, retries)

    def _deezer_isrc(self, deezer_url: str) -> str | None:
        """Fetch ISRC from Deezer API given a deezer.com/track/{id} URL."""
        try:
            deezer_id = deezer_url.rstrip('/').split('/')[-1]
            response = self.session.get(f"{DEEZER_API}/{deezer_id}", timeout=30)
            if response.status_code != 200:
                return None
            data = response.json()
            return data.get('isrc')
        except Exception:
            return None

    def _parse_response(self, data: dict) -> dict:
        """
        Shared parser for both get_all_urls() and resolve_from_url().
        Extracts every platform URL, ISRC, and Spotify ID from a raw
        song.link response dict.
        """
        import re as _re

        links    = data.get('linksByPlatform', {})
        entities = data.get('entitiesByUniqueId', {})

        def _link(key: str) -> str | None:
            return links.get(key, {}).get('url')

        def _entity_id(entity_uid: str) -> str | None:
            if '::' in entity_uid:
                return entity_uid.split('::', 1)[1]
            return None

        # ── Tidal ─────────────────────────────────────────────────────────
        tidal_url = _link('tidal')
        tidal_id: str | None = None
        if tidal_url:
            parts = tidal_url.split('/track/')
            if len(parts) == 2:
                tidal_id = parts[1].split('?')[0].strip()
            print(f" Tidal URL: {tidal_url}  (id={tidal_id})")
        else:
            print(" No Tidal URL found")

        # ── Amazon ────────────────────────────────────────────────────────
        amazon_url = _link('amazonMusic')
        amazon_asin: str | None = None
        if amazon_url:
            amazon_uid  = links.get('amazonMusic', {}).get('entityUniqueId', '')
            amazon_asin = _entity_id(amazon_uid)
            if not amazon_asin:
                m = _re.search(r'(B[0-9A-Z]{9})', amazon_url)
                if m:
                    amazon_asin = m.group(1)
            print(f" Amazon URL: {amazon_url}  (asin={amazon_asin})")
        else:
            print(" No Amazon URL found")

        # ── Qobuz ─────────────────────────────────────────────────────────
        qobuz_url = _link('qobuz')

        # ── SoundCloud ────────────────────────────────────────────────────
        soundcloud_url = _link('soundcloud')

        # ── Spotify URL + ID ──────────────────────────────────────────────
        spotify_url = _link('spotify')
        spotify_id: str | None = None
        if spotify_url:
            m = _re.search(r'spotify\.com/track/([A-Za-z0-9]+)', spotify_url)
            if not m and 'spotify:track:' in spotify_url:
                spotify_id = spotify_url.split('spotify:track:')[-1].strip()
            elif m:
                spotify_id = m.group(1)
            print(f" Spotify ID: {spotify_id}")
        else:
            print(" No Spotify URL found")

        # ── Deezer + ISRC ─────────────────────────────────────────────────
        deezer_url = _link('deezer')
        isrc: str | None = None
        if deezer_url:
            isrc = self._deezer_isrc(deezer_url)
            if isrc:
                print(f" ISRC: {isrc}")
            else:
                print(" ISRC not found via Deezer")
        else:
            print(" No Deezer URL — skipping ISRC lookup")

        # ── Fallback metadata from song.link entities ─────────────────────
        # Prefer the Spotify entity; fall through to any other entity that
        # carries title + artist info.
        sl_metadata: dict | None = None
        preferred_keys = (
            [f"SPOTIFY_SONG::{spotify_id}"] if spotify_id else []
        ) + list(entities.keys())
        for uid in preferred_keys:
            ent = entities.get(uid, {})
            if ent.get('title') and ent.get('artistName'):
                sl_metadata = {
                    'title':       ent['title'],
                    'artist':      ent['artistName'],
                    'album':       ent.get('albumName', ent['title']),
                    'album_artist': ent['artistName'],
                    'cover_url':   ent.get('thumbnailUrl'),
                    'release_date': '',
                    'track_number': 1,
                    'disc_number':  1,
                    'duration_ms':  0,
                    'isrc':        isrc or '',
                    'copyright':   '',
                    'publisher':   '',
                    'id':          '',
                    'explicit':    False,
                    'genre':       'Other',
                    'spotify_url': f'https://open.spotify.com/track/{spotify_id}' if spotify_id else '',
                    'source_url':  '',
                }
                break

        return {
            'tidal_url':       tidal_url,
            'tidal_id':        tidal_id,
            'amazon_url':      amazon_url,
            'amazon_asin':     amazon_asin,
            'qobuz_url':       qobuz_url,
            'soundcloud_url':  soundcloud_url,
            'deezer_url':      deezer_url,
            'spotify_url':     spotify_url,
            'spotify_id':      spotify_id,
            'isrc':            isrc,
            'sl_metadata':     sl_metadata,   # fallback metadata from song.link
            'raw':             data,
        }

    # ── primary method (use this) ────────────────────────────────────────

    def get_all_urls(self, spotify_id: str) -> dict:
        """
        ONE song.link call (Spotify ID) → returns all platform URLs and ISRC.
        Accepts a Spotify track ID string.  For any other URL use resolve_from_url().
        """
        data = self._fetch_songlink(spotify_id)
        return self._parse_response(data)

    def resolve_from_url(self, source_url: str) -> dict:
        """
        ONE song.link call (any platform URL) → same return shape as
        get_all_urls() but works with Tidal, Qobuz, Amazon, SoundCloud,
        Deezer — anything song.link supports.

        The result always includes 'spotify_id' and 'sl_metadata' so callers
        can fetch Spotify metadata without knowing the platform in advance.
        """
        print(f" [song.link] Resolving: {source_url}")
        data = self._fetch_raw(source_url)
        return self._parse_response(data)

    def get_platform_url(self, spotify_id: str, platform: str = 'tidal') -> str:
        """
        Backward-compatible single-platform URL lookup.
        Internally calls get_all_urls() and extracts the requested platform.
        Prefer calling get_all_urls() directly to avoid paying the API cost
        once per service.
        """
        result = self.get_all_urls(spotify_id)
        mapping = {
            'tidal':       result['tidal_url'],
            'amazonMusic': result['amazon_url'],
            'amazon':      result['amazon_url'],
            'qobuz':       result['qobuz_url'],
            'deezer':      result['deezer_url'],
        }
        url = mapping.get(platform)
        if not url:
            raise Exception(f"{platform.capitalize()} URL not found for track")
        return url

    def get_isrc(self, spotify_id: str) -> str | None:
        """
        Backward-compatible ISRC lookup.
        Internally calls get_all_urls() — prefer reusing an existing
        get_all_urls() result to avoid the extra API call.
        """
        result = self.get_all_urls(spotify_id)
        return result['isrc']


if __name__ == '__main__':
    client = SongLinkClient()
    # Quick test
    # result = client.get_all_urls('2eqUVYJVnlDs8PgOtuOlJm')
    # print(result)
