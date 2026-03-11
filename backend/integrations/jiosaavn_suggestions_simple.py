"""
Simplified JioSaavn Suggestions Scraper
"""

import requests
import json
import time

class JioSaavnSuggestions:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://www.jiosaavn.com",
            "Referer": "https://www.jiosaavn.com/",
            "X-Requested-With": "XMLHttpRequest",
            "X-Forwarded-For": "103.21.124.0",
            "CF-IPCountry": "IN"
        }

    def get_suggestions(self, pid, language='hindi', max_results=16):
        """Get song suggestions using artistOtherTopSongs API."""
        suggestions = self._try_artist_songs(pid, language, max_results)
        if not suggestions:
            print(" No suggestions found")
        return suggestions

    def _get_song_details(self, pid):
        """Fetch song details — accepts both URL tokens (FgQbCDpWWkk) and internal IDs (flp9Nfmz)."""

        try:
            url = (f"https://www.jiosaavn.com/api.php"
                   f"?__call=webapi.get&token={pid}&type=song"
                   f"&includeMetaTags=0&ctx=web6dot0&api_version=4"
                   f"&_format=json&_marker=0")
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                songs = data.get("songs", []) if isinstance(data, dict) else []
                if songs:
                    return songs[0]
        except Exception as e:
            print(f"   Song-detail (webapi.get) error: {e}")

        try:
            url = (f"https://www.jiosaavn.com/api.php"
                   f"?__call=song.getDetails&api_version=4"
                   f"&_format=json&_marker=0&ctx=web6dot0&pids={pid}")
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and data.get("status") != "failure":

                    songs = data.get("songs", [])
                    if songs:
                        return songs[0]

                    for v in data.values():
                        if isinstance(v, dict) and v.get("id"):
                            return v
        except Exception as e:
            print(f"   Song-detail (song.getDetails) error: {e}")

        return None

    def _try_artist_songs(self, pid, language, max_results):
        """Method 2: search.artistOtherTopSongs — artist-based recommendations."""
        suggestions = []
        try:

            print(f"   Fetching song details for {pid} to get artist_id…")
            song = self._get_song_details(pid)
            if not song:
                print("   Could not fetch song details")
                return suggestions

            more_info = song.get("more_info", {})
            artist_map = more_info.get("artistMap", {})
            primary = artist_map.get("primary_artists", [])
            if not primary:
                primary = artist_map.get("artists", [])

            artist_ids_str = song.get("primary_artists_id", "") or ",".join(
                str(a["id"]) for a in primary if a.get("id")
            )
            if not artist_ids_str:
                print("   No artist_id found in song details")
                return suggestions

            internal_song_id = song.get("id", pid)
            print(f"   artist_ids={artist_ids_str}  song_id={internal_song_id}")

            api_url = (
                f"https://www.jiosaavn.com/api.php"
                f"?__call=search.artistOtherTopSongs"
                f"&api_version=4&_format=json&_marker=0&ctx=web6dot0"
                f"&artist_ids={artist_ids_str}&song_id={internal_song_id}&language={language}"
            )
            print(f"   URL: {api_url}")
            resp = requests.get(api_url, headers=self.headers, timeout=10)
            print(f"   Status: {resp.status_code}  Size: {len(resp.content)} bytes")

            if resp.status_code != 200 or len(resp.content) < 10:
                return suggestions

            data = resp.json()
            items = data if isinstance(data, list) else data.get("songs", [])
            print(f"   Got {len(items)} items from artistOtherTopSongs")

            for item in items[:max_results]:
                song_data = self._parse_song_item(item)
                if song_data:
                    suggestions.append(song_data)

        except Exception as e:
            print(f"   artistOtherTopSongs error: {e}")

        return suggestions

    def _parse_song_item(self, item):
        """Parse a song item from either reco.getreco or artistOtherTopSongs."""
        try:
            if not isinstance(item, dict):
                return None

            song_id = item.get('id', '') or item.get('perma_url', '').split('/')[-1]
            title = item.get('title', '') or item.get('song', '')

            if not song_id or not title:
                return None

            more_info = item.get('more_info', {})

            artist = 'Unknown Artist'
            artist_map = more_info.get('artistMap', {})
            primary = artist_map.get('primary_artists', []) or artist_map.get('artists', [])
            if primary:
                artist = ', '.join(a['name'] for a in primary if a.get('name'))
            if not artist or artist == 'Unknown Artist':
                artist = (
                    item.get('primary_artists', '')
                    or more_info.get('music', '')
                    or item.get('music', '')
                    or 'Unknown Artist'
                )

            subtitle = item.get('subtitle', '')
            if not subtitle:
                album = more_info.get('album', '') or item.get('album', '')
                subtitle = f"{artist} - {album}" if album else artist

            thumbnail = (item.get('image', '') or '').replace('150x150', '500x500')

            raw_dur = more_info.get('duration', '') or item.get('duration', '') or '0'
            try:
                secs = int(raw_dur)
                duration = f"{secs // 60}:{secs % 60:02d}"
            except ValueError:
                duration = str(raw_dur)

            return {
                'id':         str(song_id),
                'title':      title,
                'artist':     artist,
                'subtitle':   subtitle,
                'thumbnail':  thumbnail,
                'url':        item.get('perma_url', ''),
                'duration':   duration,
                'language':   item.get('language', ''),
                'type':       'song',
                'year':       str(item.get('year', '')),
                'play_count': int(item.get('play_count', 0) or 0),
            }

        except Exception as e:
            print(f"   Parse error: {e}")
            return None

def test_suggestions(pid, language='hindi'):
    """Test suggestions locally"""
    scraper = JioSaavnSuggestions()
    results = scraper.get_suggestions(pid, language, max_results=10)

    print(f"\n{'='*60}")
    print(f" FINAL RESULTS")
    print(f"{'='*60}")
    print(f"Total suggestions: {len(results)}\n")

    if results:
        for i, song in enumerate(results, 1):
            print(f"{i}. {song['title']}")
            print(f"   Artist: {song['artist']}")
            print(f"   ID: {song['id']}")
            print(f"   URL: {song.get('url', 'N/A')}")
            print()
    else:
        print(" No results found")

    return results

def extract_pid_from_url(url: str) -> str | None:
    """Return the JioSaavn song PID from a full track URL.

    Examples:
        https://www.jiosaavn.com/song/hi/FgQbCDpWWkk       -> FgQbCDpWWkk
        https://www.jiosaavn.com/song/_/9JnbejLw             -> 9JnbejLw
    """
    import re
    m = re.search(r"/song/(?:[^/]+/)?([^/?#]+)", url)
    if m:
        return m.group(1)
    return None

if __name__ == '__main__':
    import sys

    print("Testing JioSaavn Suggestions Locally")
    print("=" * 60)

    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()

        if arg.startswith("http"):
            pid = extract_pid_from_url(arg)
            if not pid:
                print(f"Could not extract PID from URL: {arg}")
                sys.exit(1)
        else:
            pid = arg
    else:

        pid = '9JnbejLw'

    language = 'hindi'
    if len(sys.argv) > 2:
        language = sys.argv[2]

    print(f"Using PID: {pid}  language: {language}\n")
    test_suggestions(pid, language)
