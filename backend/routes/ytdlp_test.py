"""
yt-dlp Download Test Endpoint with Proxy Support

Tests downloading YouTube videos/songs with optional proxy configuration.
Works with single terminal (app.py only).

Uses yt-dlp Python library directly for proper proxy support.

Environment Variables:
    YTDLP_PROXY: Proxy URL (http://, https://, socks5://)
                Example: export YTDLP_PROXY="http://proxy.example.com:8080"
    
Usage:
    # Direct (no proxy)
    python app.py
    
    # With proxy via environment variable
    export YTDLP_PROXY="http://proxy.example.com:8080"
    python app.py
    
    # Or on Windows
    set YTDLP_PROXY=http://proxy.example.com:8080
    python app.py
"""

import logging
from flask import Blueprint, jsonify, request
from pathlib import Path
import os
import sys
import time
from typing import Optional

# Initialize logger first (before any other code tries to use it)
logger = logging.getLogger(__name__)

# Import yt-dlp library
try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False
    yt_dlp = None

# Import free-proxy library
try:
    from fp.fp import FreeProxy
    HAS_FREE_PROXY = True
    logger.info("✅ free-proxy library imported successfully")
except ImportError as e:
    HAS_FREE_PROXY = False
    FreeProxy = None
    logger.error(f"❌ Could not import free-proxy: {e}")
except Exception as e:
    HAS_FREE_PROXY = False
    FreeProxy = None
    logger.error(f"❌ Error with free-proxy: {e}")

ytdlp_bp = Blueprint('ytdlp_test', __name__, url_prefix='/api/ytdlp-test')

# Hardcoded test URL (single video, not playlist)
TEST_YOUTUBE_URL = "https://www.youtube.com/watch?v=YiYm01qX2u4"

# Cache for fetched proxy
CACHED_PROXY = None
CACHED_PROXY_TIME = None
PROXY_CACHE_TTL = 3600  # 1 hour


def get_working_proxy() -> Optional[str]:
    """
    Get a working proxy using free-proxy library.
    Uses cache if available, otherwise fetches new one.
    
    Returns:
        str: Working proxy URL or None
    """
    global CACHED_PROXY, CACHED_PROXY_TIME
    
    if not HAS_FREE_PROXY:
        logger.warning("⚠️  free-proxy library not installed")
        return None
    
    # Check cache
    if CACHED_PROXY and CACHED_PROXY_TIME:
        if time.time() - CACHED_PROXY_TIME < PROXY_CACHE_TTL:
            logger.info(f"🔄 Using cached proxy: {CACHED_PROXY}")
            return CACHED_PROXY
    
    try:
        logger.info("🔍 Fetching free proxy...")
        proxy = FreeProxy().get()
        
        if proxy:
            logger.info(f"✅ Got free proxy: {proxy}")
            CACHED_PROXY = proxy
            CACHED_PROXY_TIME = time.time()
            return proxy
        else:
            logger.warning("⚠️  Could not get proxy")
            return None
    
    except Exception as e:
        logger.warning(f"⚠️  Error fetching proxy: {e}")
        return None


logger.info("✅ yt-dlp endpoint ready - using free-proxy library")


def get_yt_dlp_info(url: str, proxy: str = None) -> dict:
    """
    Get video info from YouTube using yt-dlp Python library.
    
    Args:
        url: YouTube URL
        proxy: Optional proxy URL. If None, auto-fetches a working proxy
    
    Returns:
        dict with video info or error details
    """
    if not HAS_YTDLP:
        return {
            'success': False,
            'error': 'yt-dlp not installed - install with: pip install yt-dlp'
        }
    
    # Auto-fetch proxy if not provided
    if not proxy:
        logger.info("🔄 Auto-fetching proxy...")
        proxy = get_working_proxy()
        if proxy:
            logger.info(f"🌐 Using auto-fetched proxy: {proxy}")
        else:
            logger.warning("⚠️  Could not fetch proxy, trying direct connection")
    
    try:
        # Configure yt-dlp options
        ydl_opts = {
            'skip_download': True,
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 30,
            'noplaylist': True,  # Only extract single video, NOT playlist
            'no_check_certificates': True,  # Skip SSL verification (avoid certificate errors)
            'extractor_args': {
                'youtube': {
                    'skip': ['js']  # Skip JS extraction requirement (use fallback)
                }
            }
        }
        
        # Add proxy if available
        if proxy:
            ydl_opts['proxy'] = proxy
        
        logger.info(f"🔍 Fetching info from: {url}")
        
        # Use yt-dlp Python library directly
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        return {
            'success': True,
            'title': info.get('title', 'Unknown'),
            'duration': info.get('duration', 0),
            'uploader': info.get('uploader', 'Unknown'),
            'video_id': info.get('id', ''),
            'formats': len(info.get('formats', [])),
            'best_audio_format': info.get('format', ''),
            'filesize': info.get('filesize'),
            'ext': info.get('ext'),
            'proxy_used': proxy or 'none (direct)',
        }
    
    except yt_dlp.utils.DownloadError as e:
        return {
            'success': False,
            'error': f'Download error: {str(e)}',
            'proxy_used': proxy or 'none'
        }
    except yt_dlp.utils.ExtractorError as e:
        return {
            'success': False,
            'error': f'Extractor error: {str(e)}',
            'proxy_used': proxy or 'none'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'proxy_used': proxy or 'none'
        }


def download_yt_video(url: str, output_path: str, proxy: str = None) -> dict:
    """
    Download audio from YouTube using yt-dlp Python library.
    
    Args:
        url: YouTube URL
        output_path: Directory to save file
        proxy: Optional proxy URL. If None, auto-fetches a working proxy
    
    Returns:
        dict with download status
    """
    if not HAS_YTDLP:
        return {
            'success': False,
            'error': 'yt-dlp not installed - install with: pip install yt-dlp'
        }
    
    # Auto-fetch proxy if not provided
    if not proxy:
        logger.info("🔄 Auto-fetching proxy for download...")
        proxy = get_working_proxy()
        if proxy:
            logger.info(f"🌐 Using auto-fetched proxy: {proxy}")
        else:
            logger.warning("⚠️  Could not fetch proxy, trying direct connection")
    
    try:
        # Ensure output directory exists
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
            'noplaylist': True,  # Only extract single video, NOT playlist
            'no_check_certificates': True,  # Skip SSL verification (avoid certificate errors)
            'extractor_args': {
                'youtube': {
                    'skip': ['js']  # Skip JS extraction requirement (use fallback)
                }
            }
        }
        
        # Add proxy if available
        if proxy:
            ydl_opts['proxy'] = proxy
        
        logger.info(f"📥 Downloading: {url}")
        logger.info(f"🔍 With proxy: {proxy or 'direct connection'}")
        
        # Use yt-dlp Python library directly
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
        
        # Get list of files downloaded
        files = list(Path(output_path).glob('*'))
        return {
            'success': True,
            'message': 'Download completed',
            'files_count': len(files),
            'output_path': str(output_path),
            'files': [f.name for f in files],
            'proxy_used': proxy or 'direct'
        }
    
    except yt_dlp.utils.DownloadError as e:
        return {
            'success': False,
            'error': f'Download error: {str(e)}',
            'proxy_used': proxy or 'direct'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'proxy_used': proxy or 'direct'
        }


@ytdlp_bp.route('/info', methods=['GET', 'POST'])
def get_video_info():
    """
    Get YouTube video info without downloading.
    Automatically fetches and uses a working proxy.
    
    Query params or JSON body:
        url: YouTube URL (optional, uses hardcoded test URL if not provided)
    
    Examples:
        GET  /api/ytdlp-test/info
        POST /api/ytdlp-test/info
    """
    try:
        # Get URL from query string or JSON body
        url = request.args.get('url') or (request.get_json().get('url') if request.is_json else None)
        url = url or TEST_YOUTUBE_URL
        
        logger.info(f"🔍 Getting info for: {url} (auto-fetching proxy)")
        
        # Auto-fetches proxy internally
        info = get_yt_dlp_info(url, proxy=None)
        
        return jsonify({
            'url': url,
            'result': info
        }), 200 if info['success'] else 400
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({
            'error': str(e),
            'url': TEST_YOUTUBE_URL
        }), 500


@ytdlp_bp.route('/download', methods=['POST'])
def download_video():
    """
    Download YouTube video/audio using yt-dlp Python library.
    Automatically fetches and uses a working proxy.
    
    JSON body:
        url: YouTube URL (optional, uses hardcoded test URL if not provided)
        output_path: Output directory (default: ./downloads/ytdlp-test)
    
    Examples:
        POST /api/ytdlp-test/download
        {
            "url": "https://www.youtube.com/watch?v=..."
        }
        
        POST /api/ytdlp-test/download
        {
            "url": "https://www.youtube.com/watch?v=...",
            "output_path": "./downloads/music"
        }
    """
    try:
        data = request.get_json() or {}
        
        url = data.get('url') or TEST_YOUTUBE_URL
        output_path = data.get('output_path', './downloads/ytdlp-test')
        
        logger.info(f"📥 Download request - URL: {url} (auto-fetching proxy)")
        
        # Auto-fetches proxy internally
        result = download_yt_video(url, output_path, proxy=None)
        
        return jsonify({
            'url': url,
            'output_path': output_path,
            'result': result
        }), 200 if result['success'] else 400
    
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500


@ytdlp_bp.route('/test', methods=['GET', 'POST'])
def test_hardcoded():
    """
    Quick test endpoint - fetches info from hardcoded YouTube URL.
    Automatically fetches and uses a working proxy.
    
    GET /api/ytdlp-test/test
    """
    try:
        logger.info(f"🧪 Testing with hardcoded URL: {TEST_YOUTUBE_URL}")
        logger.info("🔄 Auto-fetching proxy...")
        
        # Auto-fetches proxy internally
        info = get_yt_dlp_info(TEST_YOUTUBE_URL, proxy=None)
        
        return jsonify({
            'test_url': TEST_YOUTUBE_URL,
            'result': info,
        }), 200 if info['success'] else 400
    
    except Exception as e:
        logger.error(f"Test error: {e}")
        return jsonify({'error': str(e)}), 500


@ytdlp_bp.route('/status', methods=['GET'])
def check_status():
    """
    Check if yt-dlp is installed and working.
    Shows auto-proxy fetching status.
    
    GET /api/ytdlp-test/status
    """
    if not HAS_YTDLP:
        return jsonify({
            'status': 'error',
            'installed': False,
            'message': 'yt-dlp Python library not found - install with: pip install yt-dlp'
        }), 500
    
    try:
        # Try to get yt-dlp version
        version = yt_dlp.version.__version__ if hasattr(yt_dlp, 'version') else 'unknown'
        
        return jsonify({
            'status': 'ok',
            'installed': True,
            'version': version,
            'library_imported': True,
            'proxy_fetching': 'auto (fetches free proxy when needed)',
            'cached_proxy': CACHED_PROXY or 'none (not fetched yet)',
            'hardcoded_test_url': TEST_YOUTUBE_URL,
            'endpoints': [
                'GET  /api/ytdlp-test/status (this endpoint)',
                'GET  /api/ytdlp-test/test (get video info with auto-proxy)',
                'GET|POST /api/ytdlp-test/info (get video info with optional URL)',
                'POST /api/ytdlp-test/download (download audio with optional URL & output path)'
            ]
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500
