"""SpotDL downloader (YouTube fallback)"""
import os
import subprocess
import sys

class SpotDLDownloader:
    """Download music using SpotDL (YouTube source)"""

    def __init__(self):
        self.check_installation()

    def check_installation(self):
        """Check if SpotDL is installed"""
        try:
            result = subprocess.run(
                ['spotdl', '--version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.decode().strip()
                print(f"✓ SpotDL installed: {version}")
            else:
                raise Exception("SpotDL not responding")
        except FileNotFoundError:
            print("\n⚠ SpotDL not found!")
            print("Install with: pip install spotdl")
            raise Exception("SpotDL not installed")
        except subprocess.TimeoutExpired:
            raise Exception("SpotDL timeout")

    def download(self, spotify_url, output_dir='.', format='flac'):
        """Download track using SpotDL

        Args:
            spotify_url: Spotify track URL or URI
            output_dir: Output directory
            format: Audio format (flac, mp3, m4a, opus, ogg)

        Returns:
            Path to downloaded file
        """
        print(f"Downloading with SpotDL (YouTube source)...")
        print(f"Format: {format.upper()}")

        os.makedirs(output_dir, exist_ok=True)

        cmd = [
            'spotdl',
            spotify_url,
            '--output', output_dir,
            '--format', format,
            '--bitrate', '320k' if format == 'mp3' else 'auto',
            '--threads', '4',
        ]

        try:

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                raise Exception(f"SpotDL failed: {error_msg}")

            output = result.stdout

            for line in output.split('\n'):
                if 'Downloaded' in line or '.flac' in line or '.mp3' in line:

                    parts = line.split(':')
                    if len(parts) > 1:
                        filename = parts[-1].strip()
                        filepath = os.path.join(output_dir, filename)
                        if os.path.exists(filepath):
                            print(f"✓ Downloaded: {filepath}")
                            return filepath

            files = [
                os.path.join(output_dir, f)
                for f in os.listdir(output_dir)
                if f.endswith(f'.{format}')
            ]

            if files:
                newest_file = max(files, key=os.path.getctime)
                print(f"✓ Downloaded: {newest_file}")
                return newest_file

            raise Exception("Could not find downloaded file")

        except subprocess.TimeoutExpired:
            raise Exception("SpotDL download timeout (5 minutes)")
        except Exception as e:
            raise Exception(f"SpotDL error: {e}")

    def download_with_metadata(self, spotify_url, output_path, metadata=None):
        """Download and optionally update metadata

        Args:
            spotify_url: Spotify URL
            output_path: Desired output path
            metadata: Optional metadata dict to embed

        Returns:
            Path to downloaded file
        """
        output_dir = os.path.dirname(output_path) or '.'
        filename = os.path.basename(output_path)
        format = os.path.splitext(filename)[1].lstrip('.')

        if format not in ['flac', 'mp3', 'm4a', 'opus', 'ogg']:
            format = 'flac'

        downloaded_file = self.download(spotify_url, output_dir, format)

        if downloaded_file != output_path:
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(downloaded_file, output_path)
                downloaded_file = output_path
            except Exception as e:
                print(f"⚠ Could not rename file: {e}")

        if metadata:
            try:
                from . import metadata as meta_module
                meta_module.embed_metadata(downloaded_file, metadata)
                print("✓ Metadata updated")
            except Exception as e:
                print(f"⚠ Failed to update metadata: {e}")

        return downloaded_file

if __name__ == '__main__':

    downloader = SpotDLDownloader()
    downloader.download('https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp', './test')
