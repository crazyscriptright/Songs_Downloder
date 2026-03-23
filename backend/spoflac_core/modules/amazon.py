"""Amazon Music downloader"""
import requests
import re
import os
import subprocess
from urllib.parse import urlparse, parse_qs
from tqdm import tqdm
from core.config import AMAZON_APIS, USER_AGENT


class AmazonDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        
    def extract_asin(self, amazon_url: str) -> str:
        """
        Extract TRACK ASIN from an Amazon Music URL.

        Tries the `trackAsin` query parameter first (most reliable),
        then falls back to a regex scan of the full URL.

        Amazon Music URL example:
          https://music.amazon.com/albums/B0DQ1JZ63Y?trackAsin=B0DQ246HMT
          → returns 'B0DQ246HMT'  (track ASIN, not album ASIN)
        """
        # 1. Prefer the trackAsin query param (exact track ASIN)
        try:
            qs = parse_qs(urlparse(amazon_url).query)
            track_asin = qs.get('trackAsin', [None])[0]
            if track_asin and re.match(r'^B[0-9A-Z]{9}$', track_asin):
                return track_asin
        except Exception:
            pass

        # 2. Fallback: first ASIN pattern found in the URL path
        matches = re.findall(r'B[0-9A-Z]{9}', amazon_url)
        if not matches:
            raise Exception("Could not extract ASIN from Amazon URL")
        # If there are multiple, prefer the one in the path (first)
        return matches[0]
        
    def get_stream_info(self, asin: str):
        """Get stream URL and decryption key, trying all AMAZON_APIS in order."""
        last_err = None
        for api_base in AMAZON_APIS:
            url = f"{api_base}/{asin}"
            print(f"  Trying Amazon API: {api_base}")
            try:
                response = self.session.get(url, timeout=20)
                if response.status_code != 200:
                    print(f"  HTTP {response.status_code}")
                    last_err = Exception(f"Amazon API {api_base} returned HTTP {response.status_code}")
                    continue
                data = response.json()
                if 'streamUrl' not in data:
                    last_err = Exception(f"streamUrl missing from {api_base} response")
                    continue
                stream_url = data['streamUrl']
                decryption_key = data.get('decryptionKey')
                print(f"  Stream URL received (key={'yes' if decryption_key else 'no'})")
                return stream_url, decryption_key
            except Exception as e:
                print(f"  {api_base}: {e}")
                last_err = e
                continue
        raise Exception(f"All Amazon APIs failed. Last error: {last_err}")
        
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
        
    def decrypt_file(self, input_path, output_path, decryption_key):
        """Decrypt file using FFmpeg"""
        print("Decrypting file with FFmpeg...")
        
        try:
            cmd = [
                'ffmpeg',
                '-decryption_key', decryption_key,
                '-i', input_path,
                '-c', 'copy',
                '-y',
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            print(" Decryption complete")
            
            # Remove encrypted file
            os.remove(input_path)
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"FFmpeg decryption failed: {e.stderr.decode()}")
        except FileNotFoundError:
            raise Exception("FFmpeg not found. Please install FFmpeg and add it to PATH.")
            
    def download(self, amazon_url: str, output_path: str, asin: str | None = None):
        """
        Main download method.

        If `asin` is provided (e.g. from song.link's entityUniqueId), it is
        used directly — avoids any regex ambiguity from the URL.
        Otherwise the ASIN is extracted from `amazon_url`.
        """
        if not asin:
            asin = self.extract_asin(amazon_url)
        print(f"Amazon ASIN: {asin}")
        stream_url, decryption_key = self.get_stream_info(asin)
        
        if decryption_key:
            # Download encrypted file
            encrypted_path = output_path + '.encrypted'
            self.download_file(stream_url, encrypted_path)
            
            # Decrypt
            self.decrypt_file(encrypted_path, output_path, decryption_key)
        else:
            # Direct download (no encryption)
            self.download_file(stream_url, output_path)
            
        return output_path


if __name__ == '__main__':
    # Test
    downloader = AmazonDownloader()
    # Example: downloader.download('https://music.amazon.com/albums/B08X123456', 'test.m4a')
