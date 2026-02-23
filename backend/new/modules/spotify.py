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
        # XOR decode the secret
        transformed = bytes([b ^ ((i % 33) + 9) for i, b in enumerate(TOTP_SECRET_V61)])
        
        # Convert to string of integers
        int_string = ''.join(str(b) for b in transformed)
        
        # Hex encode then Base32 encode
        hex_bytes = int_string.encode('utf-8')
        secret = base64.b32encode(hex_bytes).decode('utf-8').rstrip('=')
        
        # Generate TOTP
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
            raise Exception(f"Failed to get access token: HTTP {response.status_code}")
            
        data = response.json()
        self.access_token = data.get('accessToken')
        self.client_id = data.get('clientId')
        
        # Extract device ID from cookies
        if 'sp_t' in self.session.cookies:
            self.device_id = self.session.cookies['sp_t']
            
        print(f"✓ Access token acquired")
        return data
        
    def get_client_version(self):
        """Extract client version from Spotify homepage"""
        response = self.session.get(SPOTIFY_HOME_URL)
        
        # Find appServerConfig script tag
        match = re.search(r'<script id="appServerConfig">([^<]+)</script>', response.text)
        if match:
            encoded_data = match.group(1)
            decoded = base64.b64decode(encoded_data).decode('utf-8')
            config = json.loads(decoded)
            self.client_version = config.get('clientVersion', '1.2.52.442.gf7aaac59')
            print(f"✓ Client version: {self.client_version}")
        else:
            self.client_version = '1.2.52.442.gf7aaac59'  # Fallback version
            
    def get_client_token(self):
        """Get Spotify client token"""
        if not self.access_token:
            self.get_access_token()
            
        if not self.client_version:
            self.get_client_version()
            
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
            'Content-Type': 'application/json'
        }
        
        response = self.session.post(SPOTIFY_CLIENT_TOKEN_URL, json=payload, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get client token: HTTP {response.status_code}")
            
        data = response.json()
        
        if data.get('response_type') != 'RESPONSE_GRANTED_TOKEN_RESPONSE':
            raise Exception("Invalid client token response")
            
        granted_token = data.get('granted_token', {})
        self.client_token = granted_token.get('token')
        print(f"✓ Client token acquired")
        
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
            raise Exception(f"GraphQL query failed: HTTP {response.status_code}")
            
        data = response.json()
        return self.parse_track_data(data)
        
    def parse_track_data(self, data):
        """Parse GraphQL response to extract metadata"""
        try:
            track = data['data']['trackUnion']
            
            metadata = {
                'id': track['id'],
                'title': track['name'],
                'artist': ', '.join([a['profile']['name'] for a in track['artists']['items']]),
                'album': track['albumOfTrack']['name'],
                'album_artist': track['albumOfTrack']['artists']['items'][0]['profile']['name'],
                'release_date': track['albumOfTrack']['date']['isoString'],
                'track_number': track['trackNumber'],
                'disc_number': track['discNumber'],
                'duration_ms': track['duration']['totalMilliseconds'],
                'isrc': track.get('isrc', ''),
                'cover_url': None,
                'copyright': '',
                'publisher': ''
            }
            
            # Extract cover art (highest quality)
            if track['albumOfTrack'].get('coverArt'):
                sources = track['albumOfTrack']['coverArt']['sources']
                if sources:
                    # Get the largest image
                    metadata['cover_url'] = max(sources, key=lambda x: x.get('width', 0))['url']
                    
            print(f"✓ Metadata: {metadata['artist']} - {metadata['title']}")
            return metadata
            
        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to parse track data: {e}")


if __name__ == '__main__':
    # Test
    client = SpotifyClient()
    # Example: test with a track ID
    # metadata = client.get_track_metadata('3n3Ppam7vgaVa1iaRUc9Lp')
    # print(json.dumps(metadata, indent=2))
