"""Qobuz downloader using public APIs"""
import requests
import json
import random
import os
from tqdm import tqdm
from core.config import (
    QOBUZ_STANDARD_APIS, QOBUZ_JUMO_API, QOBUZ_SEARCH_API,
    QOBUZ_APP_ID, QOBUZ_QUALITY, USER_AGENT
)


class QobuzDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        
    def search_by_isrc(self, isrc):
        """Search Qobuz catalog by ISRC"""
        url = f"{QOBUZ_SEARCH_API}?query={isrc}&limit=1&app_id={QOBUZ_APP_ID}"
        
        print(f"Searching Qobuz for ISRC: {isrc}")
        response = self.session.get(url, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"Qobuz search failed: HTTP {response.status_code}")
            
        data = response.json()
        
        if 'tracks' not in data or 'items' not in data['tracks']:
            raise Exception("Invalid Qobuz search response")
            
        items = data['tracks']['items']
        if len(items) == 0:
            raise Exception(f"Track not found on Qobuz for ISRC: {isrc}")
            
        track_id = items[0]['id']
        print(f" Qobuz Track ID: {track_id}")
        return track_id
        
    def download_from_jumo(self, track_id, quality='6'):
        """Download URL from Jumo-DL API with XOR decryption"""
        quality_map = {'27': 27, '7': 7, '6': 6}
        format_id = quality_map.get(quality, 6)
        
        url = f"{QOBUZ_JUMO_API}?track_id={track_id}&format_id={format_id}&region=US"
        headers = {
            'User-Agent': USER_AGENT,
            'Referer': 'https://jumo-dl.pages.dev/'
        }
        
        print(f"  Trying Jumo-DL API")
        response = self.session.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
            
        # Try plain JSON first
        try:
            data = response.json()
            if 'url' in data:
                return data['url']
        except json.JSONDecodeError:
            pass
            
        # XOR decode
        decoded = ''.join(
            chr(ord(c) ^ 253 ^ ((i * 17) % 128))
            for i, c in enumerate(response.text)
        )
        
        data = json.loads(decoded)
        if 'url' not in data:
            raise Exception("URL not found in response")
            
        return data['url']
        
    def download_from_standard(self, api_base, track_id, quality='6'):
        """Download URL from standard Qobuz APIs"""
        if 'download-music' in api_base:
            url = f"{api_base}?track_id={track_id}&quality={quality}"
        else:
            url = f"{api_base}?trackId={track_id}&quality={quality}"
            
        response = self.session.get(url, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
            
        data = response.json()
        
        # Try direct 'url' field
        if 'url' in data:
            return data['url']
            
        # Try nested 'data.url' field
        if 'data' in data and 'url' in data['data']:
            return data['data']['url']
            
        raise Exception("URL not found in response")
        
    def get_download_url(self, track_id, quality='6', allow_fallback=True):
        """Get download URL with provider rotation and quality fallback"""
        quality_code = QOBUZ_QUALITY.get(quality, quality)
        
        # Build provider list
        providers = []
        
        # Standard APIs
        for api in QOBUZ_STANDARD_APIS:
            providers.append(('standard', api))
            
        # Jumo-DL API
        providers.append(('jumo', None))
        
        # Randomize order
        random.shuffle(providers)
        
        def try_download(qual):
            for provider_type, api_base in providers:
                try:
                    if provider_type == 'jumo':
                        print(f"  Trying Jumo-DL (Quality: {qual})")
                        return self.download_from_jumo(track_id, qual)
                    else:
                        print(f"  Trying {api_base} (Quality: {qual})")
                        return self.download_from_standard(api_base, track_id, qual)
                except Exception as e:
                    print(f"  Failed: {e}")
                    continue
            return None
            
        # Try requested quality
        url = try_download(quality_code)
        if url:
            return url
            
        # Quality fallback
        if allow_fallback:
            if quality_code == '27':
                print(" Quality 27 failed, trying 7 (24-bit Standard)...")
                url = try_download('7')
                if url:
                    return url
                    
            if quality_code in ['27', '7']:
                print(" Falling back to quality 6 (16-bit)...")
                url = try_download('6')
                if url:
                    return url
                    
        raise Exception("All Qobuz providers failed")
        
    def download_file(self, url, output_path):
        """Download file with progress bar"""
        print(f"Downloading to: {output_path}")
        
        response = self.session.get(url, stream=True, timeout=120)
        
        if response.status_code != 200:
            raise Exception(f"Download failed: HTTP {response.status_code}")
            
        total_size = int(response.headers.get('content-length', 0))
        
        with open(output_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc='Downloading') as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
                        
        print(f" Download complete: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
        
    def download(self, isrc, output_path, quality='6'):
        """Main download method"""
        track_id = self.search_by_isrc(isrc)
        download_url = self.get_download_url(track_id, quality)
        self.download_file(download_url, output_path)
        
        return output_path


if __name__ == '__main__':
    # Test
    downloader = QobuzDownloader()
    # Example: downloader.download('USRC17607839', 'test.flac')
