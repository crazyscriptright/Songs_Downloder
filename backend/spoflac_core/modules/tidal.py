"""Tidal downloader using public APIs"""
import requests
import json
import base64
import random
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from tqdm import tqdm
from core.config import TIDAL_APIS, TIDAL_QUALITY, USER_AGENT


class TidalDownloader:
    def __init__(self):
        self.apis = TIDAL_APIS.copy()
        random.shuffle(self.apis)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        
    def extract_track_id(self, tidal_url):
        """Extract track ID from Tidal URL"""
        # Format: https://tidal.com/browse/track/123456789
        parts = tidal_url.split('/track/')
        if len(parts) < 2:
            raise Exception("Invalid Tidal URL format")
            
        track_id = parts[1].split('?')[0].strip()
        return track_id
        
    def get_download_url(self, track_id, quality='HI_RES'):
        """Fetch stream URL or manifest from Tidal API"""
        quality_param = TIDAL_QUALITY.get(quality, 'HI_RES')
        
        for api_url in self.apis:
            try:
                url = f"{api_url}/track/?id={track_id}&quality={quality_param}"
                print(f"  Trying Tidal API: {api_url}")
                
                response = self.session.get(url, timeout=30)
                
                if response.status_code != 200:
                    print(f"  HTTP {response.status_code}")
                    continue
                    
                data = response.json()
                
                # V2 API with manifest
                if isinstance(data, dict) and 'data' in data:
                    manifest_b64 = data['data'].get('manifest')
                    if manifest_b64:
                        print(f"  Manifest received")
                        return self.parse_manifest(manifest_b64)
                        
                # V1 API with direct URL
                if isinstance(data, list) and len(data) > 0:
                    original_url = data[0].get('OriginalTrackURL')
                    if original_url:
                        print(f"  Direct URL received")
                        return original_url
                        
                print(f"  Invalid response format")
                
            except Exception as e:
                print(f"  {api_url}: {e}")
                continue
                
        raise Exception("All Tidal APIs failed")
        
    def parse_manifest(self, manifest_b64):
        """Parse BTS JSON or DASH XML manifest and return a download-ready result.

        Returns either:
          - A plain HTTPS URL (single file, direct download)
          - A dict {'type': 'dash', 'init_url': str, 'segment_urls': [str],
                    'mime_type': str}   → caller must concatenate and convert
        """
        try:
            manifest_bytes = base64.b64decode(manifest_b64)
            manifest_str = manifest_bytes.decode('utf-8')
        except Exception as e:
            raise Exception(f"Failed to decode manifest base64: {e}")

        # ── BTS JSON format ──────────────────────────────────────────────────
        stripped = manifest_str.strip()
        if stripped.startswith('{'):
            try:
                data = json.loads(manifest_str)
                urls = data.get('urls', [])
                if urls:
                    print(f"  BTS manifest → direct URL")
                    return urls[0]
            except json.JSONDecodeError:
                pass

        # ── DASH XML format ──────────────────────────────────────────────────
        if not (stripped.startswith('<') or stripped.startswith('<?')):
            raise Exception("Unknown manifest format (not JSON or XML)")

        try:
            root = ET.fromstring(manifest_str)
        except ET.ParseError as e:
            raise Exception(f"Failed to parse DASH XML: {e}")

        # Strip namespace for simpler XPath
        ns_match = re.match(r'\{(.+?)\}', root.tag)
        ns = f"{{{ns_match.group(1)}}}" if ns_match else ''

        # -------------------------------------------------------------------
        # Walk AdaptationSets to find the best audio track
        # -------------------------------------------------------------------
        best_bandwidth = -1
        best_rep = None
        best_seg_tmpl = None
        best_base_url = ''
        mime_type = 'audio/flac'

        for adaptation_set in root.iter(f'{ns}AdaptationSet'):
            at_mime = adaptation_set.get('mimeType', '')
            if 'audio' not in at_mime and at_mime:
                continue  # skip non-audio tracks

            # SegmentTemplate can sit on AdaptationSet OR on Representation
            as_seg_tmpl = adaptation_set.find(f'{ns}SegmentTemplate')

            for rep in adaptation_set.findall(f'{ns}Representation'):
                bw = int(rep.get('bandwidth', 0))
                if bw > best_bandwidth:
                    rep_seg_tmpl = rep.find(f'{ns}SegmentTemplate') or as_seg_tmpl
                    if rep_seg_tmpl is None:
                        continue

                    # BaseURL: prefer on Representation, then AdaptationSet, then MPD root
                    base_url = ''
                    for el in [rep, adaptation_set, root]:
                        bu = el.find(f'{ns}BaseURL')
                        if bu is not None and bu.text:
                            base_url = bu.text.strip()
                            break

                    best_bandwidth = bw
                    best_rep = rep
                    best_seg_tmpl = rep_seg_tmpl
                    best_base_url = base_url
                    mime_type = at_mime or adaptation_set.get('mimeType', 'audio/flac')

        if best_seg_tmpl is None:
            raise Exception("No usable audio SegmentTemplate found in DASH manifest")

        init_tmpl  = best_seg_tmpl.get('initialization', 'init.mp4')
        media_tmpl = best_seg_tmpl.get('media', 'seg-$Number$.m4s')
        start_num  = int(best_seg_tmpl.get('startNumber', 1))

        def _full_url(tmpl: str) -> str:
            """Resolve a segment template relative to BaseURL."""
            if tmpl.startswith('http'):
                return tmpl
            return best_base_url.rstrip('/') + '/' + tmpl.lstrip('/')

        init_url = _full_url(init_tmpl)

        # Count segments from SegmentTimeline
        segment_urls = []
        seg_num = start_num
        timeline = best_seg_tmpl.find(f'{ns}SegmentTimeline')
        if timeline is not None:
            for s_el in timeline.findall(f'{ns}S'):
                repeat = int(s_el.get('r', 0))
                # r < 0 means “repeated indefinitely”  — Tidal never uses this but guard anyway
                if repeat < 0:
                    repeat = 0
                for _ in range(repeat + 1):
                    seg_url = _full_url(media_tmpl.replace('$Number$', str(seg_num)))
                    segment_urls.append(seg_url)
                    seg_num += 1
        else:
            # No timeline: fall back to a reasonable segment count
            duration_str = root.get('mediaPresentationDuration', 'PT0S')
            # parse PT{hours}H{minutes}M{seconds}S
            m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?', duration_str)
            total_seconds = 0.0
            if m:
                total_seconds = float(m.group(1) or 0) * 3600 + float(m.group(2) or 0) * 60 + float(m.group(3) or 0)
            timescale = int(best_seg_tmpl.get('timescale', 44100))
            seg_duration = int(best_seg_tmpl.get('duration', timescale))
            count = max(1, int(total_seconds * timescale / seg_duration) + 2)
            for i in range(count):
                seg_url = _full_url(media_tmpl.replace('$Number$', str(seg_num)))
                segment_urls.append(seg_url)
                seg_num += 1

        print(f"  DASH manifest → {len(segment_urls)} segments  mime={mime_type}")
        return {
            'type':         'dash',
            'init_url':     init_url,
            'segment_urls': segment_urls,
            'mime_type':    mime_type,
        }
            
    def download_file(self, url_or_manifest, output_path):
        """Download a single-URL file or a DASH multi-segment stream."""
        if isinstance(url_or_manifest, dict) and url_or_manifest.get('type') == 'dash':
            self._download_dash(url_or_manifest, output_path)
        else:
            self._download_single(url_or_manifest, output_path)

    def _download_single(self, url, output_path):
        """Stream a single HTTP URL to a file."""
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
        print(f" Download complete: {os.path.getsize(output_path) / (1024*1024):.2f} MB")

    def _download_dash(self, manifest: dict, output_path: str):
        """Download and concatenate DASH segments, then convert to FLAC if needed."""
        init_url      = manifest['init_url']
        segment_urls  = manifest['segment_urls']
        mime_type     = manifest.get('mime_type', '')

        # Determine raw extension from mime / URL
        if 'flac' in mime_type or init_url.endswith('.flac'):
            raw_ext = '.flac'
        else:
            raw_ext = '.mp4'

        with tempfile.NamedTemporaryFile(delete=False, suffix=raw_ext) as tmp:
            tmp_path = tmp.name

        try:
            print(f"Downloading DASH: init + {len(segment_urls)} segments → {output_path}")
            all_urls = [init_url] + segment_urls
            with open(tmp_path, 'wb') as f:
                with tqdm(total=len(all_urls), unit='seg', desc='Segments') as pbar:
                    for seg_url in all_urls:
                        resp = self.session.get(seg_url, timeout=60)
                        if resp.status_code == 200:
                            f.write(resp.content)
                        else:
                            print(f"  Warning: segment {seg_url[-40:]} returned HTTP {resp.status_code}")
                        pbar.update(1)

            # Convert / remux if needed
            if raw_ext == '.mp4' and output_path.endswith('.flac'):
                print(" Converting MP4 segments → FLAC via ffmpeg...")
                try:
                    subprocess.run(
                        ['ffmpeg', '-y', '-i', tmp_path, '-c:a', 'flac', output_path],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                    )
                    print(f" Conversion complete: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
                except subprocess.CalledProcessError as e:
                    # ffmpeg not available or failed — save the raw mp4 instead
                    raw_path = output_path.replace('.flac', '.m4a')
                    os.replace(tmp_path, raw_path)
                    print(f" ffmpeg failed; saved as {raw_path} (install ffmpeg to auto-convert)")
                    return
            elif raw_ext == '.flac' or mime_type == 'audio/flac':
                os.replace(tmp_path, output_path)
                print(f" FLAC segments written: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
                return
            else:
                # mp4 output — just rename
                os.replace(tmp_path, output_path.replace('.flac', '.m4a'))
                return

        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
        
    def download(self, tidal_url, output_path, quality='HI_RES'):
        """Main download method"""
        track_id = self.extract_track_id(tidal_url)
        print(f"Tidal Track ID: {track_id}")
        
        download_url = self.get_download_url(track_id, quality)
        self.download_file(download_url, output_path)
        
        return output_path


if __name__ == '__main__':
    # Test
    downloader = TidalDownloader()
    # Example: downloader.download('https://tidal.com/browse/track/123456789', 'test.flac')
