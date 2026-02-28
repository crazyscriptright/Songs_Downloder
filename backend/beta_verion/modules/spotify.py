"""Spotify metadata fetcher using TOTP authentication"""
import requests
import pyotp
import base64
import json
import re
from config import (
    SPOTIFY_TOKEN_URL, SPOTIFY_HOME_URL, SPOTIFY_CLIENT_TOKEN_URL,
    SPOTIFY_GRAPHQL_URL, TOTP_SECRET_V61, USER_AGENT
)

class SpotifyClient:
    def __init__(self):
        self.access_token = None
        self.client_token = None
        self.client_id = None
        self.client_version = None
        self.device_id = None
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})

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
            self.client_version = config.get('clientVersion', '1.2.52.442.gf7aaac59')
            print(f" Client version: {self.client_version}")
        else:
            self.client_version = '1.2.52.442.gf7aaac59'
            print(f" Using fallback client version: {self.client_version}")

    def get_client_token(self):
        """Get Spotify client token"""

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

if __name__ == '__main__':

    client = SpotifyClient()

