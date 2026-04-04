#!/usr/bin/env python3
"""
Simple yt-dlp Download Example with HTTPS Proxy Support

Direct Python library usage (no Flask API).
Shows how to bypass IP blocking with proxies.

Install:
    pip install yt-dlp free-proxy

Usage:
    python simple_ytdlp_example.py                      # Direct download
    python simple_ytdlp_example.py socks5://proxy:1080  # With proxy
    python simple_ytdlp_example.py http://proxy:8080    # HTTP proxy
    python simple_ytdlp_example.py --free-proxy         # Auto-fetch free proxy
"""

import sys
import json
import yt_dlp
from pathlib import Path
from datetime import datetime
import subprocess
import time

try:
    from fp.fp import FreeProxy
except ImportError:
    FreeProxy = None

# Test URL
YOUTUBE_URL = "https://www.youtube.com/watch?v=YiYm01qX2u4&list=RDYiYm01qX2u4&start_radio=1&pp=oAcB"
CACHE_FILE = Path(__file__).resolve().parent / "music_api_cache.json"


def load_music_cache():
    if not CACHE_FILE.exists():
        return {}

    try:
        with CACHE_FILE.open("r", encoding="utf-8") as cache_file:
            return json.load(cache_file)
    except Exception as error:
        print(f"⚠️  Could not read cache file: {error}")
        return {}


def save_music_cache(cache_data: dict):
    with CACHE_FILE.open("w", encoding="utf-8") as cache_file:
        json.dump(cache_data, cache_file, indent=2)


def save_working_proxy(proxy_url: str, source: str, test_url: str):
    cache_data = load_music_cache()
    cache_data["proxy"] = {
        "timestamp": datetime.utcnow().isoformat(),
        "last_working_proxy": proxy_url,
        "source": source,
        "test_url": test_url,
    }
    save_music_cache(cache_data)
    print(f"💾 Saved working proxy to cache: {CACHE_FILE}")


def fetch_free_proxy():
    if FreeProxy is None:
        print("❌ free-proxy library not installed. Install with: pip install free-proxy")
        return None

    def _fetch_with_timeout(https_only: bool, wait_seconds: int = 15):
        mode = "HTTPS-only" if https_only else "any"
        print(f"🔎 Fetching free proxy ({mode})... this may take a few seconds")

        fetch_code = (
            "from fp.fp import FreeProxy; "
            f"p = FreeProxy(rand=True, timeout=1.0, anonym=True, elite=True, https={https_only}).get(); "
            "print(p if p else '')"
        )

        try:
            process = subprocess.Popen(
                [sys.executable, "-c", fetch_code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            deadline = time.time() + wait_seconds
            while process.poll() is None and time.time() < deadline:
                time.sleep(0.2)

            if process.poll() is None:
                process.kill()
                print(f"⚠️  Free proxy fetch timed out after {wait_seconds}s ({mode})")
                return None

            stdout, _ = process.communicate(timeout=2)
            proxy_url = stdout.strip().splitlines()[-1] if stdout.strip() else None
            return proxy_url or None
        except Exception as error:
            raise error

    try:
        proxy_url = _fetch_with_timeout(https_only=True)
        if proxy_url:
            return proxy_url
    except Exception as error:
        print(f"⚠️  Failed to fetch HTTPS proxy: {error}")

    try:
        proxy_url = _fetch_with_timeout(https_only=False)
        if proxy_url:
            return proxy_url
    except Exception as error:
        print(f"⚠️  Failed to fetch proxy: {error}")

    return None

def get_video_info(url: str, proxy: str = None):
    """
    Get video info without downloading.
    
    Args:
        url: YouTube URL
        proxy: Optional proxy (http://, https://, socks5://, socks5h://)
    """
    print(f"\n📊 Getting video info...")
    print(f"   URL: {url}")
    if proxy:
        print(f"   Proxy: {proxy}")
    
    # Configure yt-dlp
    ydl_opts = {
        'skip_download': True,  # Don't download, just get info
        'quiet': False,
        'no_warnings': False,
        'noplaylist': True,
        'socket_timeout': 20,
    }
    
    # Add proxy if provided
    if proxy:
        ydl_opts['proxy'] = proxy
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        print(f"\n✅ Success!")
        print(f"   Title: {info.get('title')}")
        print(f"   Duration: {info.get('duration')}s")
        print(f"   Uploader: {info.get('uploader')}")
        print(f"   Formats: {len(info.get('formats', []))}")
        
        return info
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None

def download_audio(url: str, output_dir: str = "./downloads", proxy: str = None):
    """
    Download audio from YouTube as MP3.
    
    Args:
        url: YouTube URL
        output_dir: Output directory
        proxy: Optional proxy
    """
    print(f"\n📥 Downloading audio...")
    print(f"   URL: {url}")
    print(f"   Output: {output_dir}")
    if proxy:
        print(f"   Proxy: {proxy}")
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Configure yt-dlp for audio extraction
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'quiet': False,
        'no_warnings': False,
        'noplaylist': True,
        'socket_timeout': 30,
    }
    
    # Add proxy if provided
    if proxy:
        ydl_opts['proxy'] = proxy
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        
        print(f"\n✅ Download complete!")
        print(f"   Title: {info.get('title')}")
        
        # Show file info
        files = list(Path(output_dir).glob('*'))
        if files:
            for f in files:
                size_mb = f.stat().st_size / (1024*1024)
                print(f"   Saved: {f.name} ({size_mb:.2f} MB)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def main():
    """Main function."""
    import argparse

    print("\n" + "="*70)
    print("  yt-dlp Download Example with Proxy Support")
    print("="*70)

    parser = argparse.ArgumentParser(description="Simple yt-dlp test with optional free proxy")
    parser.add_argument("proxy", nargs="?", default=None, help="Proxy URL (http, https, socks5, socks5h)")
    parser.add_argument("--free-proxy", action="store_true", help="Auto-fetch a proxy using free-proxy")
    args = parser.parse_args()

    proxy = args.proxy
    proxy_source = "cli-proxy"

    if args.free_proxy and proxy:
        print("⚠️  Both proxy argument and --free-proxy provided. Using explicit proxy argument.")

    if args.free_proxy and not proxy:
        print("\n⏳ Free-proxy mode enabled")
        proxy = fetch_free_proxy()
        if proxy:
            proxy_source = "free-proxy"
            print(f"✅ Free proxy found: {proxy}")
        else:
            print("⚠️  Could not fetch free proxy; continuing without proxy.")
    
    print(f"\n📌 Test URL: {YOUTUBE_URL}")
    
    # Test 1: Get info
    info = get_video_info(YOUTUBE_URL, proxy=proxy)
    
    if not info:
        print("\n⚠️  Failed to get video info")
        if not proxy:
            print("💡 Try with a proxy:")
            print("   python simple_ytdlp_example.py socks5://127.0.0.1:9050")
        return

    if proxy:
        save_working_proxy(proxy, source=proxy_source, test_url=YOUTUBE_URL)
    
    # Test 2: Download
    print("\n" + "-"*70)
    response = input("\n❓ Download audio? [y/n]: ").lower()
    
    if response == 'y':
        download_audio(YOUTUBE_URL, output_dir="./downloads", proxy=proxy)
    
    print("\n" + "="*70)
    print("  Done!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
