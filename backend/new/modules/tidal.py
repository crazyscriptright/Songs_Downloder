"""Tidal downloader using public APIs"""
import requests
import json
import base64
import random
import os
from tqdm import tqdm
from config import TIDAL_APIS, TIDAL_QUALITY, USER_AGENT


class TidalDownloader:
    def __init__(self):
        self.apis = TIDAL_APIS.copy()
        random.shuffle(self.apis)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        
    def extract_track_id(self, tidal_url):
        """Extract track ID from Tidal URL"""
        # Format: https://tidal.com/browse/track/123456789
        parts = tidal_url.split('/track/')
        if len(parts) < 2:
            raise Exception("Invalid Tidal URL format")
            
        track_id = parts[1].split('?')[0].strip()
        return track_id
        
    def get_download_url(self, track_id, quality='HI_RES'):
        """Fetch stream URL or manifest from Tidal API"""
        quality_param = TIDAL_QUALITY.get(quality, 'HI_RES')
        
        for api_url in self.apis:
            try:
                url = f"{api_url}/track/?id={track_id}&quality={quality_param}"
                print(f"  Trying Tidal API: {api_url}")
                
                response = self.session.get(url, timeout=30)
                
                if response.status_code != 200:
                    print(f"  ✗ HTTP {response.status_code}")
                    continue
                    
                data = response.json()
                
                # V2 API with manifest
                if isinstance(data, dict) and 'data' in data:
                    manifest_b64 = data['data'].get('manifest')
                    if manifest_b64:
                        print(f"  ✓ Manifest received")
                        return self.parse_manifest(manifest_b64)
                        
                # V1 API with direct URL
                if isinstance(data, list) and len(data) > 0:
                    original_url = data[0].get('OriginalTrackURL')
                    if original_url:
                        print(f"  ✓ Direct URL received")
                        return original_url
                        
                print(f"  ✗ Invalid response format")
                
            except Exception as e:
                print(f"  ✗ {api_url}: {e}")
                continue
                
        raise Exception("All Tidal APIs failed")
        
    def parse_manifest(self, manifest_b64):
        """Parse BTS JSON or DASH XML manifest"""
        try:
            manifest = base64.b64decode(manifest_b64).decode('utf-8')
            
            # Try JSON (BTS format)
            try:
                data = json.loads(manifest)
                if 'urls' in data and len(data['urls']) > 0:
                    return data['urls'][0]
            except json.JSONDecodeError:
                pass
                
            # DASH XML format not implemented yet
            # Would need to parse XML, extract segments, download and concatenate
            raise Exception("DASH manifest parsing not yet implemented")
            
        except Exception as e:
            raise Exception(f"Failed to parse manifest: {e}")
            
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
                        
        print(f"✓ Download complete: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
        
    def download(self, tidal_url, output_path, quality='HI_RES'):
        """Main download method"""
        track_id = self.extract_track_id(tidal_url)
        print(f"Tidal Track ID: {track_id}")
        
        download_url = self.get_download_url(track_id, quality)
        self.download_file(download_url, output_path)
        
        return output_path


if __name__ == '__main__':
    # Test
    downloader = TidalDownloader()
    # Example: downloader.download('https://tidal.com/browse/track/123456789', 'test.flac')
