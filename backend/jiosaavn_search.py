"""
JioSaavn Song Search API

This script searches for songs on JioSaavn using their public API
and displays the results with download links.

Usage:
    python jiosaavn_search.py
"""

import requests
import json
import os
from urllib.parse import quote_plus

class JioSaavnAPI:
    def __init__(self):
        # Use the newer API endpoint that's less geo-restricted
        self.base_url = "https://www.jiosaavn.com/api.php"
        # Alternative unofficial APIs that work globally
        self.alt_apis = [
            "https://saavn.dev/api/search/songs",
            "https://jiosaavn-api.vercel.app/search/songs",
            "https://saavn-api.vercel.app/search/songs"
        ]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://www.jiosaavn.com",
            "Referer": "https://www.jiosaavn.com/",
            "X-Requested-With": "XMLHttpRequest",
            "X-Forwarded-For": "103.21.124.0",  # Indian IP range
            "CF-IPCountry": "IN"  # Cloudflare country header
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search_songs(self, query, page=1, limit=20):
        """Search for songs on JioSaavn with fallback to alternative API"""
        
        # Try primary API first
        result = self._search_primary(query, page, limit)
        
        # If primary fails or returns empty, try alternative API
        if not result or (isinstance(result, dict) and not result.get('results')):
            print("⚠️ Primary API failed, trying alternative endpoint...")
            result = self._search_alternative(query, page, limit)
        
        return result
    
    def _search_primary(self, query, page=1, limit=20):
        """Search using official JioSaavn API"""
        # Build query parameters
        params = {
            "p": page,
            "q": query,
            "_format": "json",
            "_marker": "0",
            "api_version": "4",
            "ctx": "wap6dot0",
            "n": limit,
            "__call": "search.getResults"
        }
        
        # Build URL
        url = f"{self.base_url}?p={params['p']}&q={quote_plus(query)}&_format={params['_format']}&_marker={params['_marker']}&api_version={params['api_version']}&ctx={params['ctx']}&n={params['n']}&__call={params['__call']}"
        
        print(f"🔍 Searching JioSaavn (Primary) for: {query}")
        print(f"📡 URL: {url}\n")
        
        try:
            # Send GET request with session
            response = self.session.get(url, timeout=10)
            
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text[:500])
                return None
                
        except Exception as e:
            print(f"❌ Primary API request failed: {e}")
            return None
    
    def _search_alternative(self, query, page=1, limit=20):
        """Search using alternative public JioSaavn APIs"""
        
        # Try each alternative API
        for api_url in self.alt_apis:
            try:
                url = f"{api_url}?query={quote_plus(query)}&page={page}&limit={limit}"
                
                print(f"🔍 Trying alternative API: {api_url}")
                print(f"📡 URL: {url}\n")
                
                # Alternative API might not need all the headers
                alt_headers = {
                    "User-Agent": self.headers["User-Agent"],
                    "Accept": "application/json"
                }
                
                response = requests.get(url, headers=alt_headers, timeout=10)
                
                print(f"📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    # Convert alternative API format to match original format
                    if data.get('success') and data.get('data'):
                        if 'results' in data['data']:
                            return {'results': data['data']['results']}
                        elif 'songs' in data['data']:
                            return {'results': data['data']['songs']}
                    elif data.get('data') and isinstance(data['data'], list):
                        return {'results': data['data']}
                    elif 'results' in data:
                        return data
                    
                    # If we got any data, try to return it
                    return data
                    
            except Exception as e:
                print(f"❌ API {api_url} failed: {e}")
                continue
        
        print("❌ All alternative APIs failed")
        return None
    
    def parse_results(self, data):
        """Parse and display search results"""
        if not data:
            return []
        
        songs = []
        
        try:
            # Check if results exist
            if "results" not in data:
                print("⚠ No results found")
                return []
            
            results = data["results"]
            
            print(f"\n{'='*70}")
            print(f"🎵 Found {len(results)} Songs")
            print(f"{'='*70}\n")
            
            for idx, song in enumerate(results, 1):
                # Extract artist information from nested structure
                more_info = song.get('more_info', {})
                artist_map = more_info.get('artistMap', {})
                
                # Get primary artists
                primary_artists_list = artist_map.get('primary_artists', [])
                primary_artists_str = ', '.join([artist.get('name', '') for artist in primary_artists_list])
                
                # Get singers (alternative location)
                singers_list = [artist.get('name', '') for artist in artist_map.get('artists', []) if artist.get('role') == 'singer']
                singers_str = ', '.join(singers_list)
                
                # Extract song information
                song_info = {
                    'title': song.get('title', 'Unknown'),
                    'subtitle': song.get('subtitle', ''),
                    'id': song.get('id', ''),
                    'url': song.get('url', ''),
                    'image': song.get('image', ''),
                    'language': song.get('language', ''),
                    'year': song.get('year', ''),
                    'play_count': song.get('play_count', ''),
                    'primary_artists': primary_artists_str or singers_str or 'Unknown Artist',
                    'singers': singers_str or primary_artists_str or 'Unknown Artist',
                    'type': song.get('type', ''),
                    'perma_url': song.get('perma_url', ''),
                    'more_info': more_info
                }
                
                songs.append(song_info)
                
                # Display song info
                print(f"{idx}. {song_info['title']}")
                print(f"   👤 Artists: {song_info['primary_artists']}")
                print(f"   📀 Album/Subtitle: {song_info['subtitle']}")
                print(f"   🆔 ID: {song_info['id']}")
                print(f"   🔗 URL: {song_info['perma_url']}")
                print(f"   🖼️  Image: {song_info['image']}")
                print(f"   🗣️  Language: {song_info['language']}")
                print(f"   📅 Year: {song_info['year']}")
                print(f"   ▶️  Plays: {song_info['play_count']}")
                print(f"   🎤 Singers: {song_info['singers']}")
                print("-" * 70)
            
        except Exception as e:
            print(f"❌ Error parsing results: {e}")
        
        return songs
    
    def get_song_details(self, song_id):
        """Get detailed information about a specific song"""
        
        params = {
            "pids": song_id,
            "_format": "json",
            "_marker": "0",
            "api_version": "4",
            "ctx": "wap6dot0",
            "__call": "song.getDetails"
        }
        
        url = f"{self.base_url}?pids={song_id}&_format=json&_marker=0&api_version=4&ctx=wap6dot0&__call=song.getDetails"
        
        print(f"\n📥 Fetching details for song ID: {song_id}")
        
        try:
            # Use session for consistency
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None


def main():
    print("="*70)
    print("JioSaavn Song Search")
    print("="*70)
    
    # Initialize API
    api = JioSaavnAPI()
    
    # Get search query
    search_query = input("\n🔍 Enter song name to search: ").strip()
    
    if not search_query:
        search_query = "love me again"  # Default
        print(f"Using default search: {search_query}")
    
    # Search for songs
    results = api.search_songs(search_query)
    
    if results:
        # Parse and display results
        songs = api.parse_results(results)
        
        if songs:
            print(f"\n{'='*70}")
            print(f"✓ Total songs found: {len(songs)}")
            print(f"{'='*70}")
            
            # Save results to file (use /tmp on Heroku)
            output_file = "/tmp/jiosaavn_search_results.json" if os.getenv('DYNO') else "jiosaavn_search_results.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(songs, f, indent=2, ensure_ascii=False)
            print(f"✓ Results saved to {output_file}")
            
            # Save full response (use /tmp on Heroku)
            full_response_file = "/tmp/jiosaavn_full_response.json" if os.getenv('DYNO') else "jiosaavn_full_response.json"
            with open(full_response_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"✓ Full response saved to {full_response_file}")
            
            # Ask if user wants song details
            print(f"\n{'='*70}")
            get_details = input("Do you want to get details for any song? (Enter song number or 'n' to skip): ").strip()
            
            if get_details.isdigit():
                song_index = int(get_details) - 1
                if 0 <= song_index < len(songs):
                    song_id = songs[song_index]['id']
                    details = api.get_song_details(song_id)
                    
                    if details:
                        print(f"\n{'='*70}")
                        print(f"Song Details:")
                        print(f"{'='*70}")
                        print(json.dumps(details, indent=2))
                        
                        # Save details (use /tmp on Heroku)
                        details_file = f"/tmp/song_details_{song_id}.json" if os.getenv('DYNO') else f"song_details_{song_id}.json"
                        with open(details_file, "w", encoding="utf-8") as f:
                            json.dump(details, f, indent=2, ensure_ascii=False)
                        print(f"\n✓ Details saved to {details_file}")
                else:
                    print("❌ Invalid song number")
        else:
            print("⚠ No songs found")
    else:
        print("❌ Search failed")


if __name__ == "__main__":
    main()
