"""Unified URL resolver + metadata fetcher.

Design
------
Pass *any* supported track URL (Spotify, Tidal, Qobuz, Amazon, SoundCloud,
Deezer …) to URLResolver.resolve() and get back a single, consistent dict:

    {
        'metadata':        dict,
        'sl_result':       dict,
        'spotify_id':      str | None,
        'source_platform': str,
        'metadata_source': str,
    }

Metadata priority
-----------------
1. Spotify API  (full: title, artist, album, ISRC, cover, duration, …)
2. song.link entity data  (title, artistName, thumbnailUrl — always present)

Download decisions and fallback chains can then be based purely on
sl_result['tidal_url'], sl_result['qobuz_url'], etc.
"""
from __future__ import annotations

import re
from typing import Optional

from spoflac_core.modules.songlink import SongLinkClient
from spoflac_core.modules.spotify import SpotifyClient
from spoflac_core.modules.url_detector import URLDetector

_SONGLINK_SUPPORTED = {
    'spotify', 'tidal', 'qobuz', 'amazon', 'soundcloud', 'deezer',
    'appleMusic', 'youtube', 'youtubeMusic',
}

def _detect_platform(url: str) -> str:
    """Extend URLDetector to also handle SoundCloud and Deezer."""

    platform, _ = URLDetector().get_track_id(url)
    if platform:
        return platform

    url_lower = url.lower()
    if 'soundcloud.com' in url_lower:
        return 'soundcloud'
    if 'deezer.com' in url_lower:
        return 'deezer'
    if 'music.apple.com' in url_lower or 'itunes.apple.com' in url_lower:
        return 'appleMusic'
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    return 'unknown'

class URLResolver:
    """
    Resolve any track URL to metadata + all platform download URLs.

    Usage
    -----
        resolver = URLResolver()
        result   = resolver.resolve("https://soundcloud.com/artist/track")

        metadata = result['metadata']
        sl       = result['sl_result']
    """

    def __init__(self):
        self._sl  = SongLinkClient()
        self._spy: Optional[SpotifyClient] = None

    def _spotify_client(self) -> SpotifyClient:
        if self._spy is None:
            self._spy = SpotifyClient()
        return self._spy

    def resolve(self, url: str) -> dict:
        """
        Main entry point.

        Parameters
        ----------
        url : str
            Any track URL supported by song.link.

        Returns
        -------
        dict with keys:
            metadata        : dict  — ID3-ready metadata dict (Spotify or fallback)
            sl_result       : dict  — all platform URLs from song.link
            spotify_id      : str | None
            source_platform : str   — detected platform of the input URL
            metadata_source : str   — 'spotify' or 'songlink'
        """
        source_platform = _detect_platform(url)
        print(f" [resolver] Source platform: {source_platform}")

        if source_platform == 'spotify':

            _, spotify_id = URLDetector().get_track_id(url)
            if not spotify_id:
                raise Exception(f"Could not parse Spotify track ID from: {url}")
            sl_result = self._sl.get_all_urls(spotify_id)
        else:

            sl_result = self._sl.resolve_from_url(url)
            spotify_id = sl_result.get('spotify_id')

        metadata: dict | None = None
        metadata_source = 'songlink'

        if spotify_id:
            try:
                spy = self._spotify_client()

                metadata = spy.get_track_metadata(spotify_id)
                metadata_source = 'spotify'
                print(f" [resolver] Spotify metadata: {metadata['artist']} – {metadata['title']}")
            except Exception as e:
                print(f" [resolver] Spotify metadata failed ({e}) — using song.link fallback")

        if metadata is None:
            sl_meta = sl_result.get('sl_metadata')
            if sl_meta:
                metadata = sl_meta
                print(f" [resolver] Fallback metadata: {metadata['artist']} – {metadata['title']}")
            else:
                raise Exception(
                    "Could not obtain metadata: Spotify lookup failed and song.link "
                    "returned no entity data for this URL."
                )

        return {
            'metadata':        metadata,
            'sl_result':       sl_result,
            'spotify_id':      spotify_id,
            'source_platform': source_platform,
            'metadata_source': metadata_source,
        }

    def resolve_metadata_only(self, url: str) -> dict:
        """
        Convenience: just return the metadata dict (no download URLs).
        Useful for search previews or tag-only workflows.
        """
        return self.resolve(url)['metadata']

if __name__ == '__main__':
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else \
        'https://soundcloud.com/jinduniverse/high-on-you'

    resolver = URLResolver()
    result = resolver.resolve(test_url)

    print("\n── Result ──────────────────────────────────────────────")
    print(f"Source platform : {result['source_platform']}")
    print(f"Metadata source : {result['metadata_source']}")
    print(f"Spotify ID      : {result['spotify_id']}")
    m = result['metadata']
    print(f"Title           : {m['title']}")
    print(f"Artist          : {m['artist']}")
    print(f"Album           : {m['album']}")
    print(f"ISRC            : {m.get('isrc')}")
    print(f"Cover           : {m.get('cover_url')}")
    sl = result['sl_result']
    print(f"\nTidal URL       : {sl.get('tidal_url')}")
    print(f"Qobuz URL       : {sl.get('qobuz_url')}")
    print(f"Amazon URL      : {sl.get('amazon_url')}")
    print(f"SoundCloud URL  : {sl.get('soundcloud_url')}")
