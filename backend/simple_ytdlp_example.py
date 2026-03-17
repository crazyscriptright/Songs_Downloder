#!/usr/bin/env python3
"""
Simple yt-dlp Download Example with HTTPS Proxy Support

Direct Python library usage (no Flask API).
Shows how to bypass IP blocking with proxies.

Install:
    pip install yt-dlp

Usage:
    python simple_ytdlp_example.py                      # Direct download
    python simple_ytdlp_example.py socks5://proxy:1080  # With proxy
    python simple_ytdlp_example.py http://proxy:8080    # HTTP proxy
"""

import sys
import yt_dlp
from pathlib import Path

# Test URL
YOUTUBE_URL = "https://www.youtube.com/watch?v=YiYm01qX2u4&list=RDYiYm01qX2u4&start_radio=1&pp=oAcB"

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
    print("\n" + "="*70)
    print("  yt-dlp Download Example with Proxy Support")
    print("="*70)
    
    # Get proxy from command line
    proxy = None
    if len(sys.argv) > 1:
        proxy = sys.argv[1]
    
    print(f"\n📌 Test URL: {YOUTUBE_URL}")
    
    # Test 1: Get info
    info = get_video_info(YOUTUBE_URL, proxy=proxy)
    
    if not info:
        print("\n⚠️  Failed to get video info")
        if not proxy:
            print("💡 Try with a proxy:")
            print("   python simple_ytdlp_example.py socks5://127.0.0.1:9050")
        return
    
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
