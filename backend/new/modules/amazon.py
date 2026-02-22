"""Amazon Music downloader"""
import requests
import re
import os
import subprocess
from tqdm import tqdm
from config import AMAZON_API, USER_AGENT


class AmazonDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        
    def extract_asin(self, amazon_url):
        """Extract ASIN from Amazon Music URL"""
        match = re.search(r'(B[0-9A-Z]{9})', amazon_url)
        if not match:
            raise Exception("Could not extract ASIN from Amazon URL")
        return match.group(1)
        
    def get_stream_info(self, asin):
        """Get stream URL and decryption key from API"""
        url = f"{AMAZON_API}/{asin}"
        
        print(f"Fetching stream info for ASIN: {asin}")
        response = self.session.get(url, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"Amazon API error: HTTP {response.status_code}")
            
        data = response.json()
        
        if 'streamUrl' not in data:
            raise Exception("Stream URL not found in response")
            
        stream_url = data['streamUrl']
        decryption_key = data.get('decryptionKey')
        
        print(f"✓ Stream URL received")
        if decryption_key:
            print(f"✓ Decryption key received")
            
        return stream_url, decryption_key
        
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
            
            print("✓ Decryption complete")
            
            # Remove encrypted file
            os.remove(input_path)
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"FFmpeg decryption failed: {e.stderr.decode()}")
        except FileNotFoundError:
            raise Exception("FFmpeg not found. Please install FFmpeg and add it to PATH.")
            
    def download(self, amazon_url, output_path):
        """Main download method"""
        asin = self.extract_asin(amazon_url)
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
