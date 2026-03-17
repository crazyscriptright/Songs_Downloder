#!/usr/bin/env python3
"""
yt-dlp Test Script with HTTPS Proxy Support

Test yt-dlp directly with Python library (not via API).
Supports HTTPS proxies to bypass IP blocking.

Features:
  ✅ Direct Python library usage
  ✅ HTTPS proxy support (HTTP, SOCKS5)
  ✅ Default proxy for testing
  ✅ IP bypass capabilities
  ✅ Multiple retry strategies

Usage:
  python test_ytdlp_endpoint.py                    # Without proxy
  python test_ytdlp_endpoint.py --proxy http://proxy:8080
  python test_ytdlp_endpoint.py --proxy socks5://127.0.0.1:9050
  python test_ytdlp_endpoint.py --skip-api        # Direct library only (no Flask API)
"""

import sys
import json
import os
from pathlib import Path
import time

# Try importing yt-dlp
try:
    import yt_dlp
    print("✅ yt-dlp library found")
except ImportError:
    print("❌ yt-dlp not installed. Install with: pip install yt-dlp")
    sys.exit(1)

# Hardcoded test URL
TEST_YOUTUBE_URL = "https://www.youtube.com/watch?v=YiYm01qX2u4&list=RDYiYm01qX2u4&start_radio=1&pp=oAcB"

# Default HTTPS proxies to test
DEFAULT_PROXIES = {
    "none": None,
    "http_example": "http://proxy.example.com:8080",
    "socks5_tor": "socks5://127.0.0.1:9050",  # Tor default
    "socks5_localhost": "socks5h://127.0.0.1:1080",  # Local SOCKS5
}

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def test_yt_dlp_direct(url: str, proxy: str = None, extract_audio: bool = False):
    """
    Test yt-dlp directly using Python library (not API).
    
    Args:
        url: YouTube URL
        proxy: Proxy URL (http://, https://, socks5://, socks5h://)
        extract_audio: Whether to extract audio only
    
    Returns:
        dict with results
    """
    print(f"🎯 Testing with URL: {url}")
    if proxy:
        print(f"🌐 Using proxy: {proxy}")
    else:
        print(f"🌐 No proxy (direct connection)")
    
    try:
        # Configure yt-dlp options
        ydl_opts = {
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 30,
        }
        
        # Add proxy if provided
        if proxy:
            ydl_opts['proxy'] = proxy
            # Force IPv4 due to proxy (some proxies don't support IPv6)
            ydl_opts['socket_timeout'] = 30
        
        # For info extraction only (no download)
        ydl_opts['skip_download'] = True
        
        print(f"\n📊 Fetching video info...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        result = {
            'success': True,
            'title': info.get('title'),
            'duration': info.get('duration'),
            'uploader': info.get('uploader'),
            'video_id': info.get('id'),
            'ext': info.get('ext'),
            'filesize': info.get('filesize'),
            'formats': len(info.get('formats', [])),
        }
        
        print(f"✅ Success!")
        print(f"   Title: {result['title']}")
        print(f"   Duration: {result['duration']}s")
        print(f"   Uploader: {result['uploader']}")
        
        return result
        
    except yt_dlp.utils.DownloadError as e:
        return {
            'success': False,
            'error': f'Download error: {str(e)}',
            'error_type': 'DownloadError'
        }
    except yt_dlp.utils.ExtractorError as e:
        return {
            'success': False,
            'error': f'Extractor error: {str(e)}',
            'error_type': 'ExtractorError'
        }
    except yt_dlp.utils.FormatSortError as e:
        return {
            'success': False,
            'error': f'Format error: {str(e)}',
            'error_type': 'FormatSortError'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }

def download_yt_dlp_direct(url: str, output_path: str = "./downloads/ytdlp-test", proxy: str = None):
    """
    Download audio from YouTube directly using yt-dlp library.
    
    Args:
        url: YouTube URL
        output_path: Output directory
        proxy: Proxy URL
    
    Returns:
        dict with download status
    """
    print(f"🎯 Downloading from: {url}")
    if proxy:
        print(f"🌐 Using proxy: {proxy}")
    
    try:
        # Create output directory
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        # Configure yt-dlp options for audio extraction
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 60,
        }
        
        # Add proxy if provided
        if proxy:
            ydl_opts['proxy'] = proxy
        
        print(f"\n📥 Downloading audio...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        
        # Get downloaded files
        files = list(Path(output_path).glob('*'))
        
        result = {
            'success': True,
            'title': info.get('title'),
            'output_path': str(output_path),
            'files_count': len(files),
            'files': [f.name for f in files],
        }
        
        print(f"✅ Download complete!")
        for f in files:
            size_mb = f.stat().st_size / (1024*1024)
            print(f"   📁 {f.name} ({size_mb:.2f} MB)")
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'output_path': str(output_path)
        }

def test_all_proxies():
    """Test with all default proxies."""
    print_section("TESTING ALL PROXIES")
    
    results = {}
    for proxy_name, proxy_url in DEFAULT_PROXIES.items():
        print(f"\n🔹 Testing proxy: {proxy_name}")
        print(f"   URL: {proxy_url or 'None (direct)'}")
        print("-" * 70)
        
        result = test_yt_dlp_direct(TEST_YOUTUBE_URL, proxy=proxy_url)
        results[proxy_name] = result
        
        if result['success']:
            print(f"✅ {proxy_name}: OK")
        else:
            print(f"❌ {proxy_name}: {result['error']}")
        
        # Small delay between requests
        time.sleep(1)
    
    return results

def test_custom_proxy(proxy_url: str):
    """Test with a custom proxy."""
    print_section(f"TESTING CUSTOM PROXY: {proxy_url}")
    
    print(f"🌐 Proxy: {proxy_url}\n")
    result = test_yt_dlp_direct(TEST_YOUTUBE_URL, proxy=proxy_url)
    
    return result

def api_endpoint_test():
    """Test via Flask API endpoint (requires backend running)."""
    print_section("TEST VIA FLASK API ENDPOINT")
    
    try:
        import requests
        
        base_url = "http://localhost:5000/api/ytdlp-test"
        
        print("Testing Flask API endpoint...\n")
        
        # Check status
        response = requests.get(f"{base_url}/status")
        print(f"Status endpoint: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        
        return response.status_code == 200
        
    except requests.ConnectionError:
        print("❌ Cannot connect to Flask API")
        print("   Make sure backend is running: python app.py")
        return False
    except Exception as e:
        print(f"❌ API test error: {e}")
        return False

def test_info():
    """Get info from hardcoded YouTube URL."""
    print_section("TEST 2: VIDEO INFO (Direct Library)")
    return test_yt_dlp_direct(TEST_YOUTUBE_URL, proxy=None)

def main():
    """Main test runner."""
    print("\n" + "="*70)
    print("  yt-dlp Direct Library Test with HTTPS Proxy Support")
    print("="*70)
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Test yt-dlp with proxy support')
    parser.add_argument('--proxy', type=str, help='Proxy URL (http, https, socks5, socks5h)')
    parser.add_argument('--all-proxies', action='store_true', help='Test all default proxies')
    parser.add_argument('--download', action='store_true', help='Download audio (not just info)')
    parser.add_argument('--url', type=str, default=TEST_YOUTUBE_URL, help='YouTube URL')
    parser.add_argument('--skip-api', action='store_true', help='Skip Flask API tests')
    parser.add_argument('--output', type=str, default='./downloads/ytdlp-test', help='Output directory')
    
    args = parser.parse_args()
    
    print(f"\n🎵 Test URL: {args.url}\n")
    
    # Test 1: Direct library without proxy
    if not args.proxy and not args.all_proxies:
        print_section("TEST 1: DIRECT (No Proxy)")
        result = test_yt_dlp_direct(args.url)
        
        if result['success']:
            print("\n✅ Direct connection works!")
            print(f"   Title: {result['title']}")
            print(f"   Uploader: {result['uploader']}")
        else:
            print(f"\n❌ Error: {result['error']}")
            print("\n💡 Try with a proxy:")
            print("   python test_ytdlp_endpoint.py --proxy socks5://127.0.0.1:9050")
    
    # Test 2: With custom proxy
    if args.proxy:
        print_section("TEST 2: WITH CUSTOM PROXY")
        result = test_yt_dlp_direct(args.url, proxy=args.proxy)
        
        if result['success']:
            print("\n✅ Proxy connection works!")
        else:
            print(f"\n❌ Proxy error: {result['error']}")
            print("\n💡 Make sure proxy is running:")
            print(f"   URL: {args.proxy}")
    
    # Test 3: All proxies
    if args.all_proxies:
        results = test_all_proxies()
        
        print_section("PROXY TEST SUMMARY")
        working = [name for name, res in results.items() if res['success']]
        failed = [name for name, res in results.items() if not res['success']]
        
        if working:
            print(f"✅ Working proxies ({len(working)}):")
            for proxy in working:
                print(f"   • {proxy}")
        
        if failed:
            print(f"\n❌ Failed proxies ({len(failed)}):")
            for proxy in failed:
                error = results[proxy].get('error', 'Unknown error')
                print(f"   • {proxy}: {error[:50]}")
    
    # Test 4: Download
    if args.download:
        print_section("TEST: DOWNLOAD")
        result = download_yt_dlp_direct(args.url, output_path=args.output, proxy=args.proxy)
        
        if result['success']:
            print(f"\n✅ Download complete!")
        else:
            print(f"\n❌ Download error: {result['error']}")
    
    # Test 5: API endpoint (unless skipped)
    if not args.skip_api:
        api_endpoint_test()
    
    # Print summary and proxy info
    print_section("PROXY FORMATS & EXAMPLES")
    print("""
Supported Proxy Formats:
  • HTTP:     http://proxy.example.com:8080
  • HTTPS:    https://proxy.example.com:8080
  • SOCKS5:   socks5://127.0.0.1:1080
  • SOCKS5h:  socks5h://127.0.0.1:1080  (hostname through proxy)

Examples:

1️⃣  Direct connection (no proxy):
    python test_ytdlp_endpoint.py
    
2️⃣  With HTTP proxy:
    python test_ytdlp_endpoint.py --proxy http://proxy.company.com:8080
    
3️⃣  With HTTPS proxy:
    python test_ytdlp_endpoint.py --proxy https://secure-proxy.com:443
    
4️⃣  With Tor (SOCKS5):
    tor --SocksPort 9050  # In another terminal
    python test_ytdlp_endpoint.py --proxy socks5://127.0.0.1:9050
    
5️⃣  Test all default proxies:
    python test_ytdlp_endpoint.py --all-proxies
    
6️⃣  Download audio with proxy:
    python test_ytdlp_endpoint.py --proxy socks5://127.0.0.1:9050 --download
    
7️⃣  Custom output directory:
    python test_ytdlp_endpoint.py --download --output ./my_downloads
    
8️⃣  Skip API tests (direct library only):
    python test_ytdlp_endpoint.py --skip-api --proxy http://proxy:8080

Default Proxies Available:
    """)
    for name, url in DEFAULT_PROXIES.items():
        if url:
            print(f"  • {name}: {url}")
        else:
            print(f"  • {name}: (direct connection)")
    
    print("\n" + "="*70)
    print("  Test Complete!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
