import requests
import json
import time
import re
import os
from datetime import datetime, timedelta

class YouTubeMusicAPI:
    def __init__(self, cache_file="music_api_cache.json", cache_duration_hours=24):
        self.api_key = None
        self.context = None
        self.base_url = "https://music.youtube.com"
        # Use /tmp on Heroku for writable storage
        if os.getenv('DYNO'):
            self.cache_file = f"/tmp/{os.path.basename(cache_file)}"
        else:
            self.cache_file = cache_file
        self.cache_duration_hours = cache_duration_hours
        self.cached_tokens = None
    
    def load_cache(self):
        """Load tokens from cache file if valid"""
        try:
            if not os.path.exists(self.cache_file):
                print(" No cache file found")
                return None
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Get YouTube Music song tokens from unified cache
            if 'ytmusic_songs' not in cache_data:
                return None
            
            tokens_data = cache_data['ytmusic_songs']
            
            # Check if cache is still valid
            cached_time = datetime.fromisoformat(tokens_data['timestamp'])
            expiry_time = cached_time + timedelta(hours=self.cache_duration_hours)
            
            if datetime.now() < expiry_time:
                time_left = expiry_time - datetime.now()
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                print(f" Using cached YT Music song tokens (expires in {hours}h {minutes}m)")
                return tokens_data['tokens']
            else:
                print(f" Cache expired (was {self.cache_duration_hours} hours old)")
                return None
                
        except Exception as e:
            print(f" Error loading cache: {e}")
            return None
    
    def save_cache(self, tokens):
        """Save tokens to unified cache file (atomic, race-condition-safe)."""
        try:
            from utils.atomic_write import atomic_json_read_modify_write

            def _updater(cache_data: dict) -> dict:
                cache_data['ytmusic_songs'] = {
                    'timestamp': datetime.now().isoformat(),
                    'tokens': tokens,
                }
                return cache_data

            atomic_json_read_modify_write(self.cache_file, _updater, ensure_ascii=False)
            print(f" YT Music song tokens cached successfully (valid for {self.cache_duration_hours} hours)")

        except Exception as e:
            print(f" Error saving cache: {e}")
    
    def get_tokens(self, search_query="", force_refresh=False):
        """Get tokens from cache or fetch fresh ones"""
        
        # Try to use cached tokens first
        if not force_refresh:
            cached_tokens = self.load_cache()
            if cached_tokens:
                self.cached_tokens = cached_tokens
                return cached_tokens
        
        # If no valid cache or force refresh, try fast HTTP method first
        print(" Fetching fresh tokens...")
        fresh_tokens = self.get_tokens_fast()
        
        if not fresh_tokens or not fresh_tokens.get('api_key'):
            print(" Fast token extraction failed — using empty tokens")
            fresh_tokens = {}

        # Save to cache
        self.save_cache(fresh_tokens)
        self.cached_tokens = fresh_tokens
        
        return fresh_tokens
    
    def get_tokens_fast(self):
        """Get YT Music tokens without Selenium - 10x faster"""
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }
        
        try:
            print(" Trying fast HTTP method...")
            
            # Direct request to YT Music
            response = requests.get('https://music.youtube.com/', headers=headers, timeout=10)
            html = response.text
            
            # Extract tokens with regex (much faster than Selenium)
            api_key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html)
            visitor_data = re.search(r'"VISITOR_DATA":"([^"]+)"', html)
            client_version = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', html)
            
            # Alternative patterns if first ones don't work
            if not api_key:
                api_key = re.search(r'innertubeApiKey":"([^"]+)"', html)
            if not visitor_data:
                visitor_data = re.search(r'visitorData":"([^"]+)"', html)
            if not client_version:
                client_version = re.search(r'clientVersion":"([^"]+)"', html)
            
            if api_key and visitor_data and client_version:
                tokens = {
                    'api_key': api_key.group(1),
                    'visitor_data': visitor_data.group(1),
                    'client_version': client_version.group(1)
                }
                
                print(f" Fast extraction successful!")
                print(f" API Key: {tokens['api_key']}")
                print(f" Visitor Data: {tokens['visitor_data']}")
                print(f" Client Version: {tokens['client_version']}")
                
                return tokens
            else:
                print(f" Fast extraction incomplete - API Key: {bool(api_key)}, Visitor: {bool(visitor_data)}, Version: {bool(client_version)}")
                return None
                
        except Exception as e:
            print(f" Fast token extraction failed: {e}")
            return None
        
    def build_context(self, visitor_data=None, client_version=None):
        """Build the context object with fresh or default tokens"""
        import time
        
        current_timestamp = str(int(time.time() * 1000))
        
        return {
            "client": {
                "hl": "en",
                "gl": "IN",
                "clientName": "WEB_REMIX",
                "clientVersion": client_version or "1.20251022.00.01",
                "visitorData": visitor_data or "",
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "osName": "Windows",
                "osVersion": "10.0",
                "platform": "DESKTOP",
                "clientFormFactor": "UNKNOWN_FORM_FACTOR",
                "userInterfaceTheme": "USER_INTERFACE_THEME_DARK",
                "timeZone": "Asia/Calcutta",
                "browserName": "Chrome",
                "browserVersion": "131.0.0.0",
                "screenWidthPoints": 1920,
                "screenHeightPoints": 1080,
                "screenPixelDensity": 1,
                "screenDensityFloat": 1,
                "utcOffsetMinutes": 330
            },
            "user": {
                "lockedSafetyMode": False
            },
            "request": {
                "useSsl": True,
                "internalExperimentFlags": [],
                "consistencyTokenJars": []
            },
            "adSignalsInfo": {
                "params": [
                    {"key": "dt", "value": current_timestamp},
                    {"key": "flash", "value": "0"},
                    {"key": "frm", "value": "0"},
                    {"key": "u_tz", "value": "330"},
                    {"key": "u_his", "value": "2"},
                    {"key": "u_h", "value": "1080"},
                    {"key": "u_w", "value": "1920"},
                    {"key": "u_ah", "value": "1040"},
                    {"key": "u_aw", "value": "1920"},
                    {"key": "u_cd", "value": "24"},
                    {"key": "bc", "value": "31"},
                    {"key": "bih", "value": "937"},
                    {"key": "biw", "value": "1903"},
                    {"key": "brdim", "value": "0,0,0,0,1920,0,1920,1040,1920,937"},
                    {"key": "vis", "value": "1"},
                    {"key": "wgl", "value": "true"},
                    {"key": "ca_type", "value": "image"}
                ]
            }
        }
    
    def search(self, query, use_fresh_tokens=True, retry_on_error=True):
        """Search for songs on YouTube Music with caching and auto-retry"""
        
        # Get tokens (from cache or fresh)
        tokens = self.get_tokens(query, force_refresh=not use_fresh_tokens)
        
        # Build URL with API key if available
        if tokens.get('api_key'):
            url = f"https://music.youtube.com/youtubei/v1/search?key={tokens['api_key']}&prettyPrint=false"
        else:
            url = "https://music.youtube.com/youtubei/v1/search?prettyPrint=false"
        
        # Build headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Origin": "https://music.youtube.com",
            "Referer": f"https://music.youtube.com/search?q={query.replace(' ', '+')}"
        }
        
        # Build payload
        payload = {
            "context": self.build_context(
                visitor_data=tokens.get('visitor_data'),
                client_version=tokens.get('client_version')
            ),
            "query": query,
            "params": "EgWKAQIIAWoQEAQQAxAJEAUQChAVEBAQEQ%3D%3D"
        }
        
        print(f"\n Searching for: {query}")
        print(f" URL: {url}")
        
        # Send request
        response = requests.post(url, headers=headers, json=payload)
        
        print(f" Status Code: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f" Error: {response.status_code}")
            print(response.text[:500])
            
            # If error occurs and retry is enabled, try with fresh tokens
            if retry_on_error and use_fresh_tokens:
                print("\n Retrying with fresh tokens...")
                fresh_tokens = self.get_tokens(query, force_refresh=True)
                
                # Update URL with fresh API key
                if fresh_tokens.get('api_key'):
                    url = f"https://music.youtube.com/youtubei/v1/search?key={fresh_tokens['api_key']}&prettyPrint=false"
                
                # Update payload with fresh tokens
                payload["context"] = self.build_context(
                    visitor_data=fresh_tokens.get('visitor_data'),
                    client_version=fresh_tokens.get('client_version')
                )
                
                # Retry request
                response = requests.post(url, headers=headers, json=payload)
                print(f" Retry Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f" Retry failed: {response.status_code}")
                    print(response.text[:500])
            
            return None
    
    def parse_search_results(self, data):
        """Parse and display search results"""
        if not data:
            return []
        
        songs = []
        
        try:
            contents = data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"]
            
            for section in contents:
                if "musicShelfRenderer" in section:
                    shelf = section["musicShelfRenderer"]
                    
                    # Get section title
                    title = shelf["title"]["runs"][0]["text"]
                    
                    if title.lower() == "songs":
                        print(f"\n{'='*60}")
                        print(f" {title}")
                        print(f"{'='*60}\n")
                        
                        # Get songs
                        for item in shelf.get("contents", []):
                            if "musicResponsiveListItemRenderer" in item:
                                renderer = item["musicResponsiveListItemRenderer"]
                                
                                # Extract song info
                                song_title = renderer["flexColumns"][0]["musicResponsiveListItemFlexColumnRenderer"]["text"]["runs"][0]["text"]
                                video_id = renderer["playlistItemData"]["videoId"]
                                thumbnail = renderer["thumbnail"]["musicThumbnailRenderer"]["thumbnail"]["thumbnails"][-1]["url"]
                                
                                # Metadata
                                metadata_runs = renderer["flexColumns"][1]["musicResponsiveListItemFlexColumnRenderer"]["text"]["runs"]
                                metadata = "".join([run["text"] for run in metadata_runs])
                                
                                song_info = {
                                    'title': song_title,
                                    'video_id': video_id,
                                    'url': f"https://music.youtube.com/watch?v={video_id}",
                                    'thumbnail': thumbnail,
                                    'metadata': metadata
                                }
                                
                                songs.append(song_info)
                                
                                print(f" {song_title}")
                                print(f"   Video ID: {video_id}")
                                print(f"   URL: https://music.youtube.com/watch?v={video_id}")
                                print(f"   {metadata}")
                                print(f"   Thumbnail: {thumbnail}")
                                print("-" * 60)
                        
                        break
        except Exception as e:
            print(f" Error parsing results: {e}")
        
        return songs


# Example usage
if __name__ == "__main__":
    # Initialize API with 2-hour cache duration
    api = YouTubeMusicAPI(cache_duration_hours=2)
    
    # Search - will use cache if available, or fetch fresh tokens
    search_query = "follow follow song"
    results = api.search(search_query, use_fresh_tokens=True)
    
    if results:
        songs = api.parse_search_results(results)
        print(f"\n Found {len(songs)} songs")
        
        # Save results (use /tmp on Heroku)
        output_file = "/tmp/search_results.json" if os.getenv('DYNO') else "search_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(songs, f, indent=2, ensure_ascii=False)
        print(f" Results saved to {output_file}")
    
    # Example: Search again - will use cached tokens
    print("\n" + "="*60)
    print(" Searching again (should use cache)...")
    print("="*60)
    
    results2 = api.search("another song", use_fresh_tokens=True)
    if results2:
        songs2 = api.parse_search_results(results2)
        print(f"\n Found {len(songs2)} songs")
