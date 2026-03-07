"""Spotify metadata fetcher using TOTP authentication"""
import os
import requests
import pyotp
import base64
import json
import re
from datetime import datetime, timedelta
from config import (
    SPOTIFY_TOKEN_URL, SPOTIFY_HOME_URL, SPOTIFY_CLIENT_TOKEN_URL,
    SPOTIFY_GRAPHQL_URL, TOTP_SECRET_V61, USER_AGENT
)

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CACHE_FILENAME = "music_api_cache.json"

if os.getenv("DYNO"):
    CACHE_FILE = f"/tmp/{_CACHE_FILENAME}"
else:
    CACHE_FILE = os.path.join(_BACKEND_DIR, _CACHE_FILENAME)
CACHE_DURATION_HOURS = 2

class SpotifyClient:
    def __init__(self):
        self.access_token = None
        self.client_token = None
        self.client_id = None
        self.client_version = None
        self.device_id = None
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})

    def load_cache(self):
        """Load Spotify tokens from music_api_cache.json if still valid (< 2 h)."""
        try:
            if not os.path.exists(CACHE_FILE):
                return False
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            if 'spotify' not in cache_data:
                return False
            entry = cache_data['spotify']
            cached_time = datetime.fromisoformat(entry['timestamp'])
            expiry_time = cached_time + timedelta(hours=CACHE_DURATION_HOURS)
            if datetime.now() < expiry_time:
                time_left = expiry_time - datetime.now()
                hours, remainder = divmod(int(time_left.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                self.access_token  = entry['tokens']['access_token']
                self.client_token  = entry['tokens']['client_token']
                self.client_id     = entry['tokens']['client_id']
                self.client_version = entry['tokens']['client_version']
                self.device_id     = entry['tokens'].get('device_id', '')
                print(f" Using cached Spotify tokens (expires in {hours}h {minutes}m)")
                return True
            else:
                print(f" Spotify cache expired — refreshing tokens")
                return False
        except Exception as e:
            print(f" Error loading Spotify cache: {e}")
            return False

    def save_cache(self):
        """Persist current tokens into music_api_cache.json (atomic, race-condition-safe)."""
        try:
            from utils.atomic_write import atomic_json_read_modify_write

            tokens = {
                'access_token':  self.access_token,
                'client_token':  self.client_token,
                'client_id':     self.client_id,
                'client_version': self.client_version,
                'device_id':     self.device_id or '',
            }

            def _updater(cache_data: dict) -> dict:
                cache_data['spotify'] = {
                    'timestamp': datetime.now().isoformat(),
                    'tokens': tokens,
                }
                return cache_data

            atomic_json_read_modify_write(CACHE_FILE, _updater, ensure_ascii=False)
            print(f" Spotify tokens cached (valid for {CACHE_DURATION_HOURS}h)")
        except Exception as e:
            print(f" Error saving Spotify cache: {e}")

    def generate_totp(self):
        """Generate TOTP code from XOR-encoded secret (Version 61)"""

        transformed = bytes([b ^ ((i % 33) + 9) for i, b in enumerate(TOTP_SECRET_V61)])

        int_string = ''.join(str(b) for b in transformed)

        hex_bytes = int_string.encode('utf-8')
        secret = base64.b32encode(hex_bytes).decode('utf-8').rstrip('=')

        totp = pyotp.TOTP(secret)
        return totp.now(), 61

    def get_access_token(self):
        """Fetch Spotify access token using TOTP"""
        totp_code, version = self.generate_totp()

        params = {
            'reason': 'init',
            'productType': 'web-player',
            'totp': totp_code,
            'totpVer': version,
            'totpServer': totp_code
        }

        response = self.session.get(SPOTIFY_TOKEN_URL, params=params)

        if response.status_code != 200:
            raise Exception(f"Failed to get access token: HTTP {response.status_code}\nResponse: {response.text[:200]}")

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse access token response as JSON: {e}\nResponse content: {response.text[:500]}")

        self.access_token = data.get('accessToken')
        self.client_id = data.get('clientId')

        if not self.access_token:
            raise Exception(f"No access token in response. Response: {json.dumps(data, indent=2)}")

        if 'sp_t' in self.session.cookies:
            self.device_id = self.session.cookies['sp_t']

        print(f" Access token acquired")
        return data

    def get_client_version(self):
        """Extract client version from Spotify homepage"""
        response = self.session.get(SPOTIFY_HOME_URL)

        match = re.search(r'<script id="appServerConfig">([^<]+)</script>', response.text)
        if match:
            encoded_data = match.group(1)
            decoded = base64.b64decode(encoded_data).decode('utf-8')
            config = json.loads(decoded)
            self.client_version = config.get('clientVersion', '1.2.85.433.g369f2f9c')
            print(f" Client version: {self.client_version}")
        else:
            self.client_version = '1.2.85.433.g369f2f9c'
            print(f" Using fallback client version: {self.client_version}")

    def get_client_token(self):
        """Get Spotify client token — loads from cache first, fetches fresh if expired."""

        if self.load_cache():
            return

        if not self.client_version:
            self.get_client_version()

        if not self.access_token:
            self.get_access_token()

        payload = {
            "client_data": {
                "client_version": self.client_version,
                "client_id": self.client_id,
                "js_sdk_data": {
                    "device_brand": "unknown",
                    "device_model": "unknown",
                    "os": "windows",
                    "os_version": "NT 10.0",
                    "device_id": self.device_id or "",
                    "device_type": "computer"
                }
            }
        }

        headers = {
            'Authority': 'clienttoken.spotify.com',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        response = self.session.post(SPOTIFY_CLIENT_TOKEN_URL, json=payload, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Failed to get client token: HTTP {response.status_code}\nResponse: {response.text[:200]}")

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse client token response as JSON: {e}\nResponse content: {response.text[:500]}")

        if data.get('response_type') != 'RESPONSE_GRANTED_TOKEN_RESPONSE':
            raise Exception(f"Invalid client token response. Response: {json.dumps(data, indent=2)}")

        granted_token = data.get('granted_token', {})
        self.client_token = granted_token.get('token')

        if not self.client_token:
            raise Exception(f"No client token in response. Response: {json.dumps(data, indent=2)}")

        print(f" Client token acquired")
        self.save_cache()

    def get_track_metadata(self, track_id):
        """Fetch track metadata using GraphQL API"""
        if not self.client_token:
            self.get_client_token()

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Client-Token': self.client_token,
            'Spotify-App-Version': self.client_version,
            'Content-Type': 'application/json'
        }

        query = {
            "variables": {
                "uri": f"spotify:track:{track_id}"
            },
            "operationName": "getTrack",
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "612585ae06ba435ad26369870deaae23b5c8800a256cd8a57e08eddc25a37294"
                }
            }
        }

        response = self.session.post(SPOTIFY_GRAPHQL_URL, json=query, headers=headers)

        if response.status_code != 200:
            raise Exception(f"GraphQL query failed: HTTP {response.status_code}\nResponse: {response.text[:200]}")

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse GraphQL response as JSON: {e}\nResponse content: {response.text[:500]}")

        return self.parse_track_data(data)

    def parse_track_data(self, data):
        """Parse GraphQL response to extract metadata"""
        try:
            track = data['data']['trackUnion']

            artists = []

            if 'artists' in track and track['artists'] and 'items' in track['artists']:
                artists = [a['profile']['name'] for a in track['artists']['items'] if 'profile' in a and 'name' in a['profile']]

            if not artists:
                if 'firstArtist' in track and track['firstArtist'] and 'items' in track['firstArtist']:
                    artists.extend([a['profile']['name'] for a in track['firstArtist']['items'] if 'profile' in a and 'name' in a['profile']])

                if 'otherArtists' in track and track['otherArtists'] and 'items' in track['otherArtists']:
                    artists.extend([a['profile']['name'] for a in track['otherArtists']['items'] if 'profile' in a and 'name' in a['profile']])

            if not artists and 'albumOfTrack' in track and 'artists' in track['albumOfTrack'] and 'items' in track['albumOfTrack']['artists']:
                artists = [a['profile']['name'] for a in track['albumOfTrack']['artists']['items'] if 'profile' in a and 'name' in a['profile']]

            artist_string = ', '.join(artists) if artists else 'Unknown Artist'

            album_data = track.get('albumOfTrack', {})
            album_name = album_data.get('name', 'Unknown Album')

            album_artist = artist_string
            if album_data.get('artists', {}).get('items'):
                album_artist = album_data['artists']['items'][0]['profile']['name']

            release_date = ''
            if 'date' in album_data and album_data['date']:
                release_date = album_data['date'].get('isoString', '')

            duration_ms = 0
            if 'duration' in track and track['duration']:
                duration_ms = track['duration'].get('totalMilliseconds', 0)

            metadata = {
                'id': track.get('id', ''),
                'title': track.get('name', 'Unknown Title'),
                'artist': artist_string,
                'album': album_name,
                'album_artist': album_artist,
                'release_date': release_date,
                'track_number': track.get('trackNumber', 1),
                'disc_number': track.get('discNumber', 1),
                'duration_ms': duration_ms,
                'isrc': track.get('isrc', ''),
                'cover_url': None,
                'copyright': '',
                'publisher': ''
            }

            if track['albumOfTrack'].get('coverArt'):
                sources = track['albumOfTrack']['coverArt']['sources']
                if sources:

                    metadata['cover_url'] = max(sources, key=lambda x: x.get('width', 0))['url']

            print(f" Metadata: {metadata['artist']} - {metadata['title']}")
            return metadata

        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to parse track data: {e}\nData structure: {json.dumps(data, indent=2)[:500]}")

    def get_search_results(self, data):
        """get search results to extract track metadata"""

        if isinstance(data, str):
            search_term = data
        elif isinstance(data, dict):
            search_term = data.get("searchTerm") or data.get("query") or ""
        else:
            raise ValueError("data must be a search string or dict with 'searchTerm'")

        if not search_term:
            raise ValueError("Empty search term")

        if not self.client_token:
            self.get_client_token()

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Client-Token': self.client_token,
            'Spotify-App-Version': self.client_version,
            'Content-Type': 'application/json'
        }
        print(f"headers: {headers} ")

        payload = {
            "variables": {
                "searchTerm": search_term,
                "offset": 0,
                "limit": 20,
                "numberOfTopResults": 20,
                "includeAudiobooks": True,
                "includeArtistHasConcertsField": True,
                "includePreReleases": False,
                "includeAuthors": False
            },
            "operationName": "searchDesktop",
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "3c9d3f60dac5dea3876b6db3f534192b1c1d90032c4233c1bbaba526db41eb31"
                }
            }
        }

        print(f" [Search] Sending query: {search_term}")
        response = self.session.post(SPOTIFY_GRAPHQL_URL, json=payload, headers=headers)

        print(f" [Search] Response status: {response.status_code}")
        try:
            resp_json = response.json()
        except Exception:
            print(" [Search] Response text:")
            print(response.text[:3000])
            resp_json = None

        if response.status_code != 200:
            raise Exception(f"Search query failed: HTTP {response.status_code}\nResponse: {response.text[:500]}")

        return resp_json

    def parse_search_results(self, resp_json):
        """
        Parse raw searchV2 GraphQL response into a clean list of track dicts.

        Returns list of:
        {
            id, name, uri, spotify_url,
            duration_ms,
            artists,
            album,
            album_uri,
            cover_url,
            playable,
        }
        """
        if not resp_json:
            return [], 0, 0

        s = resp_json.get("data", {}).get("searchV2", {}) or {}
        raw_items = s.get("tracksV2", {}).get("items", [])
        total = s.get("tracksV2", {}).get("totalCount", 0)

        results = []
        for item in raw_items:
            t = item.get("item", {}).get("data", {}) or {}
            if not t:
                continue

            artists = []
            for a in t.get("artists", {}).get("items", []):
                name = (a.get("profile") or {}).get("name")
                if name:
                    artists.append(name)

            album = t.get("albumOfTrack") or {}
            cover_sources = album.get("coverArt", {}).get("sources", []) if album else []
            cover_url = None
            if cover_sources:
                cover_url = max(cover_sources, key=lambda x: x.get("width", 0)).get("url")

            playability = t.get("playability") or {}
            playable = playability.get("playable", True) if isinstance(playability, dict) else bool(playability)

            track_id = t.get("id")
            results.append({
                "id":           track_id,
                "name":         t.get("name"),
                "uri":          t.get("uri"),
                "spotify_url":  f"https://open.spotify.com/track/{track_id}" if track_id else None,
                "duration_ms":  (t.get("duration") or {}).get("totalMilliseconds"),
                "artists":      ", ".join(artists) if artists else None,
                "album":        album.get("name"),
                "album_uri":    album.get("uri"),
                "cover_url":    cover_url,
                "playable":     playable,
            })

        returned_count = len(results)
        return results, total, returned_count

if __name__ == '__main__':

    client = SpotifyClient()

