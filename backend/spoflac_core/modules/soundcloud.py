"""YouTube / SoundCloud fallback downloader using yt-dlp.

Searches YouTube Music via ytsearch1: query — no Spotify API calls, no rate
limits.  When a SoundCloud URL hits a geo-restriction, automatically retries
with free proxies sourced from the `free-proxy` library.
"""
import os
import subprocess
import glob

def _get_free_proxies(count: int = 5) -> list[str]:
    """Return up to `count` free HTTPS proxy URLs via the free-proxy library."""
    try:
        from fp.fp import FreeProxy
        proxies = []
        seen = set()
        for _ in range(count * 3):
            try:
                p = FreeProxy(rand=True, timeout=1, https=True).get()
                if p and p not in seen:
                    seen.add(p)
                    proxies.append(p)
                    if len(proxies) >= count:
                        break
            except Exception:
                continue
        return proxies
    except ImportError:
        print("  [proxy] free-proxy not installed — run: pip install free-proxy")
        return []

class SoundCloudDownloader:
    """Generic downloader using yt-dlp (YouTube/SoundCloud).

    Originally written as a SpotDL replacement, the name was kept for
    historical reasons.  It now handles SoundCloud URLs directly and
    falls back to querying YouTube when given a search string.
    """

    def __init__(self):
        self._ytdlp = self._find_ytdlp()

    def _find_ytdlp(self):
        """Locate yt-dlp binary."""
        for cmd in ['yt-dlp', 'yt_dlp']:
            try:
                result = subprocess.run(
                    [cmd, '--version'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                )
                version = (result.stdout or result.stderr).decode(errors='ignore').strip()
                print(f" yt-dlp found: {version.splitlines()[0]}")
                return cmd
            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                continue
        raise Exception("yt-dlp not installed. Run: pip install yt-dlp")

    def download_with_metadata(self, spotify_url, output_path, metadata=None):
        """Download track and save to output_path.

        Uses metadata['artist'] + metadata['title'] to search YouTube.
        Falls back to spotify_url as the search string if metadata is missing.
        """
        output_dir = os.path.dirname(os.path.abspath(output_path))
        ext = os.path.splitext(output_path)[1].lstrip('.') or 'flac'
        if ext not in ('flac', 'mp3', 'm4a', 'opus', 'ogg', 'wav'):
            ext = 'flac'

        if metadata and metadata.get('artist') and metadata.get('title'):
            query = f"{metadata['artist']} - {metadata['title']}"
        else:
            query = spotify_url

        print(f"  [yt-dlp] Searching YouTube: {query}")
        downloaded = self._download(query, output_dir, ext)

        if downloaded and os.path.abspath(downloaded) != os.path.abspath(output_path):
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(downloaded, output_path)
                downloaded = output_path
            except Exception as e:
                print(f"  [yt-dlp] Could not rename to expected path: {e}")

        return downloaded

    def download(self, query, output_dir='.', format='flac'):
        """Download by search query or URL."""
        return self._download(query, output_dir, format)

    def _download(self, query, output_dir, ext):
        os.makedirs(output_dir, exist_ok=True)

        search_input = query if query.startswith('http') else f"ytsearch1:{query}"
        outtmpl = os.path.join(output_dir, '%(title)s.%(ext)s')

        base_cmd = [
            self._ytdlp,
            search_input,
            '--output', outtmpl,
            '--format', 'bestaudio[acodec=opus][abr>=96]/bestaudio',
            '--no-playlist',
            '--no-part',
            '--newline',
            '--extract-audio',
            '--audio-format', ext,
            '--audio-quality', '0',
        ]

        before = set(glob.glob(os.path.join(output_dir, f'*.{ext}')))

        def _run(cmd):
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            output_lines = []
            for line in process.stdout:
                line = line.rstrip()
                if line:
                    print(f"  [yt-dlp] {line}")
                    output_lines.append(line)
            try:
                process.wait(timeout=900)
            except subprocess.TimeoutExpired:
                process.kill()
                raise Exception("yt-dlp download timeout (15 minutes)")
            return process.returncode, output_lines

        def _is_geo_error(lines):
            joined = '\n'.join(lines).lower()
            return 'geo restriction' in joined or 'not available from your location' in joined

        def _collect_result(before_set):
            after = set(glob.glob(os.path.join(output_dir, f'*.{ext}')))
            new_files = after - before_set
            if new_files:
                return max(new_files, key=os.path.getctime)
            all_files = glob.glob(os.path.join(output_dir, f'*.{ext}'))
            if all_files:
                return max(all_files, key=os.path.getctime)
            return None

        print(f"Downloading with yt-dlp...")
        returncode, output_lines = _run(base_cmd)

        if returncode == 0:
            result = _collect_result(before)
            if result:
                print(f" Downloaded: {result}")
                return result
            raise Exception("yt-dlp finished but output file not found")

        if not _is_geo_error(output_lines):
            error_tail = '\n'.join(output_lines[-10:])
            raise Exception(f"yt-dlp failed (exit {returncode}):\n{error_tail}")

        print("  [geo] Geo-restriction detected — trying free proxies…")
        proxies = _get_free_proxies(5)
        if not proxies:
            raise Exception("Geo-restricted and no free proxies available (install free-proxy: pip install free-proxy)")

        last_error = f"yt-dlp failed (exit {returncode})"
        for i, proxy in enumerate(proxies, 1):
            print(f"  [proxy {i}/{len(proxies)}] Trying {proxy}…")
            cmd = base_cmd + ['--proxy', proxy]
            rc, lines = _run(cmd)
            if rc == 0:
                result = _collect_result(before)
                if result:
                    print(f" Downloaded via proxy {proxy}: {result}")
                    return result
            last_error = '\n'.join(lines[-5:])
            print(f"  [proxy {i}] Failed — trying next…")

        raise Exception(f"Geo-restricted: all {len(proxies)} proxies failed. Last error:\n{last_error}")

if __name__ == '__main__':
    downloader = SoundCloudDownloader()
    downloader.download_with_metadata(
        'https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp',
        './test/test.flac',
        {'artist': 'Coldplay', 'title': 'The Scientist'},
    )

    downloader.download('https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp', './test')
