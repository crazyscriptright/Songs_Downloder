"""SongLink API client for URL conversion and ISRC extraction"""
import time
import requests
from urllib.parse import quote
from config import SONGLINK_API, DEEZER_API, SONGLINK_MIN_DELAY, SONGLINK_RETRY_DELAY, USER_AGENT


class SongLinkClient:
    def __init__(self):
        self.last_call_time = 0
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        
    def _rate_limit(self):
        """Enforce rate limiting (7 seconds between calls)"""
        elapsed = time.time() - self.last_call_time
        if elapsed < SONGLINK_MIN_DELAY:
            sleep_time = SONGLINK_MIN_DELAY - elapsed
            print(f"  Rate limiting: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)
            
    def get_platform_url(self, spotify_id, platform='tidal'):
        """Convert Spotify ID to another platform's URL"""
        self._rate_limit()
        
        spotify_url = f"https://open.spotify.com/track/{spotify_id}"
        url = f"{SONGLINK_API}?url={quote(spotify_url)}"
        
        try:
            response = self.session.get(url, timeout=30)
            self.last_call_time = time.time()
            
            if response.status_code == 429:
                print(f"  Rate limited by API, waiting {SONGLINK_RETRY_DELAY}s...")
                time.sleep(SONGLINK_RETRY_DELAY)
                return self.get_platform_url(spotify_id, platform)
                
            if response.status_code != 200:
                raise Exception(f"SongLink API error: HTTP {response.status_code}")
                
            data = response.json()
            
            if 'linksByPlatform' not in data or platform not in data['linksByPlatform']:
                raise Exception(f"{platform.capitalize()} URL not found for track")
                
            platform_url = data['linksByPlatform'][platform]['url']
            print(f" {platform.capitalize()} URL: {platform_url}")
            return platform_url
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"SongLink API request failed: {e}")
            
    def get_isrc(self, spotify_id):
        """Get ISRC code via Deezer API"""
        try:
            # Get Deezer URL
            deezer_url = self.get_platform_url(spotify_id, 'deezer')
            
            # Extract Deezer track ID
            deezer_id = deezer_url.rstrip('/').split('/')[-1]
            
            # Query Deezer API
            response = self.session.get(f"{DEEZER_API}/{deezer_id}", timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"Deezer API error: HTTP {response.status_code}")
                
            data = response.json()
            
            if 'isrc' not in data:
                raise Exception("ISRC not found in Deezer response")
                
            isrc = data['isrc']
            print(f" ISRC: {isrc}")
            return isrc
            
        except Exception as e:
            print(f" Failed to get ISRC: {e}")
            return None


if __name__ == '__main__':
    # Test
    client = SongLinkClient()
    # Example: test with a track ID
    # tidal_url = client.get_platform_url('3n3Ppam7vgaVa1iaRUc9Lp', 'tidal')
    # isrc = client.get_isrc('3n3Ppam7vgaVa1iaRUc9Lp')
