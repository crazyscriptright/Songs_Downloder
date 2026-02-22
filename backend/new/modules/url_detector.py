"""URL detection and parsing for multiple platforms"""
import re
from typing import Tuple, Optional


class URLDetector:
    """Detect and parse URLs from Spotify, Tidal, Qobuz, Amazon"""
    
    @staticmethod
    def detect_platform(url: str) -> Optional[str]:
        """Detect which platform a URL belongs to"""
        url_lower = url.lower()
        
        if 'spotify.com' in url_lower or url.startswith('spotify:'):
            return 'spotify'
        elif 'tidal.com' in url_lower:
            return 'tidal'
        elif 'qobuz.com' in url_lower:
            return 'qobuz'
        elif 'amazon.com' in url_lower or 'music.amazon' in url_lower:
            return 'amazon'
        
        return None
    
    @staticmethod
    def parse_spotify_url(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse Spotify URL to get content type and ID
        
        Returns:
            (content_type, id) where content_type is 'track', 'album', 'playlist', or 'artist'
        """
        # Handle spotify:track:ID format
        if url.startswith('spotify:'):
            parts = url.split(':')
            if len(parts) >= 3:
                return parts[1], parts[2]
        
        # Handle https://open.spotify.com/track/ID format
        patterns = [
            (r'spotify\.com/track/([a-zA-Z0-9]+)', 'track'),
            (r'spotify\.com/album/([a-zA-Z0-9]+)', 'album'),
            (r'spotify\.com/playlist/([a-zA-Z0-9]+)', 'playlist'),
            (r'spotify\.com/artist/([a-zA-Z0-9]+)', 'artist'),
        ]
        
        for pattern, content_type in patterns:
            match = re.search(pattern, url)
            if match:
                return content_type, match.group(1)
        
        return None, None
    
    @staticmethod
    def parse_tidal_url(url: str) -> Optional[str]:
        """Parse Tidal URL to get track ID"""
        match = re.search(r'tidal\.com/(?:browse/)?track/(\d+)', url)
        if match:
            return match.group(1)
        return None
    
    @staticmethod
    def parse_qobuz_url(url: str) -> Optional[str]:
        """Parse Qobuz URL to get track/album ID"""
        # Qobuz format: https://www.qobuz.com/us-en/album/name/id
        # or https://open.qobuz.com/track/trackid
        patterns = [
            r'qobuz\.com/(?:[^/]+/)?album/[^/]+/([a-zA-Z0-9]+)',
            r'qobuz\.com/(?:[^/]+/)?track/([a-zA-Z0-9]+)',
            r'open\.qobuz\.com/track/(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def parse_amazon_url(url: str) -> Optional[str]:
        """Parse Amazon Music URL to get ASIN"""
        match = re.search(r'(B[0-9A-Z]{9})', url)
        if match:
            return match.group(1)
        return None
    
    @staticmethod
    def get_track_id(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Universal track ID extractor
        
        Returns:
            (platform, track_id)
        """
        platform = URLDetector.detect_platform(url)
        
        if not platform:
            return None, None
        
        if platform == 'spotify':
            content_type, track_id = URLDetector.parse_spotify_url(url)
            if content_type == 'track':
                return platform, track_id
            return platform, None  # Not a track URL
            
        elif platform == 'tidal':
            return platform, URLDetector.parse_tidal_url(url)
            
        elif platform == 'qobuz':
            return platform, URLDetector.parse_qobuz_url(url)
            
        elif platform == 'amazon':
            return platform, URLDetector.parse_amazon_url(url)
        
        return None, None


if __name__ == '__main__':
    # Test
    detector = URLDetector()
    
    test_urls = [
        "https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp",
        "spotify:track:3n3Ppam7vgaVa1iaRUc9Lp",
        "https://tidal.com/browse/track/123456789",
        "https://www.qobuz.com/us-en/album/test/abc123",
        "https://music.amazon.com/albums/B08X123456",
    ]
    
    for url in test_urls:
        platform, track_id = detector.get_track_id(url)
        print(f"URL: {url}")
        print(f"  Platform: {platform}, ID: {track_id}\n")
