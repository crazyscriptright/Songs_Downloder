"""
Download service — yt-dlp subprocess orchestration + proxy API fallback.

All functions here run in background threads started from the download routes.
State mutations go through the shared ``state`` module.
"""

import os
import re
import shlex
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests

from core import config
from core import state
from services import api_metadata_enricher
from services.post_download_enricher import run_post_download_enrichment

def _safe_title(title: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", title)

def _run_cli_music_hardening(file_path: str) -> None:
    """
    Run CLI metadata hardening command on a completed local music file:
        python tools/music_metadata_enhancer/enrich_metadata.py "<file>" -y
    """
    try:
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            return

        if path.suffix.lower() not in {'.mp3', '.flac', '.m4a', '.mp4', '.aac', '.wav'}:
            return

        backend_dir = Path(__file__).resolve().parents[1]
        python_exec = sys.executable
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        print(f" Running CLI metadata hardening for: {path.name}")

        hardening = subprocess.run(
            [python_exec, 'tools/music_metadata_enhancer/enrich_metadata.py', str(path), '-y'],
            cwd=str(backend_dir),
            env=env,
            check=False,
            capture_output=True,
            timeout=180,
        )

        if hardening.returncode == 0:
            print(f" CLI metadata hardening completed: {path.name}")
        else:
            stderr_text = (hardening.stderr or b"").decode("utf-8", errors="replace")
            stdout_text = (hardening.stdout or b"").decode("utf-8", errors="replace")
            stderr_line = stderr_text.strip().splitlines()
            stdout_line = stdout_text.strip().splitlines()
            err_preview = stderr_line[-1] if stderr_line else (stdout_line[-1] if stdout_line else 'unknown error')
            print(f" CLI metadata hardening failed ({hardening.returncode}): {path.name} | {err_preview}")

    except Exception as cli_exc:
        print(f" CLI hardening skipped: {cli_exc}")

_MP3_VBR    = {"0": 0, "2": 2, "5": 5, "9": 9}
_AAC_VBR    = {"0": 5, "2": 4, "5": 3, "9": 1}
_OGG_VBR    = {"0": 10, "2": 8, "5": 6, "9": 3}
_OPUS_KBPS  = {"0": "320k", "2": "256k", "5": "192k", "9": "128k"}
_WAV_KBPS   = {}

def _converter_quality_kwargs(audio_format: str, audio_quality: str) -> dict:
    """
    Map yt-dlp audioQuality string → AudioConverter keyword arguments.
    Falls back gracefully for unknown quality values.
    """
    q = str(audio_quality) if audio_quality in {"0", "2", "5", "9"} else "0"
    fmt = audio_format.lower()

    if fmt == "mp3":
        return {"vbr_quality": _MP3_VBR.get(q, 0)}
    if fmt in ("aac", "m4a"):
        return {"vbr_quality": _AAC_VBR.get(q, 5)}
    if fmt == "ogg":
        return {"vbr_quality": _OGG_VBR.get(q, 10)}
    if fmt == "opus":
        return {"bitrate": _OPUS_KBPS.get(q, "320k")}
    if fmt in ("flac", "wav"):
        return {}
    return {"bitrate": "320k"}

def download_with_spoflac(url: str, title: str, download_id: str, advanced_options=None) -> None:
    """
    Download via spoflac_core (Tidal/Qobuz/Amazon/SoundCloud fallback chain).
    Resolves URL, fetches metadata + lyrics, downloads FLAC, embeds tags,
    and optionally converts to the requested format.
    """
    try:
        from spoflac_core.modules import url_resolver, utils
        from spoflac_core.modules import tidal, qobuz, amazon, soundcloud, metadata

        state.download_status[download_id].update(
            status="downloading",
            progress=5,
            eta="Resolving URL and fetching metadata...",
            speed="Initializing",
        )
        state.save_download_status()

        quality = advanced_options.get("audioQuality", "HI_RES") if advanced_options else "HI_RES"
        if quality == "0":
            quality = "HI_RES"

        resolver = url_resolver.URLResolver()
        resolved = resolver.resolve(url)
        track_metadata = resolved['metadata']
        sl_result = resolved['sl_result']

        print(f" SpotiFLAC: {track_metadata['artist']} - {track_metadata['title']} | lyrics={'yes' if track_metadata.get('lyrics') else 'no'}")

        state.download_status[download_id].update(
            progress=15,
            eta="Preparing download...",
            title=f"{track_metadata['artist']} - {track_metadata['title']}",
        )
        state.save_download_status()

        download_dir = os.path.join(config.DOWNLOAD_FOLDER, download_id)
        os.makedirs(download_dir, exist_ok=True)

        ext = '.flac'
        filename = utils.build_filename(track_metadata, '{artist} - {title}', ext)
        output_path = os.path.join(download_dir, filename)

        state.download_status[download_id].update(
            progress=25,
            eta="Attempting download...",
            speed="Connecting",
        )
        state.save_download_status()

        services_to_try = [
            ('tidal', sl_result.get('tidal_url')),
            ('qobuz', sl_result.get('isrc')),
            ('amazon', sl_result.get('amazon_url')),
            ('soundcloud', sl_result.get('soundcloud_url')),
        ]

        download_success = False
        last_error = None

        for service_name, service_data in services_to_try:
            if not service_data:
                print(f"  Skipping {service_name.capitalize()} - no data available")
                continue

            try:
                print(f" Downloading from {service_name}...")

                state.download_status[download_id].update(
                    progress=40,
                    eta=f"Downloading from {service_name.capitalize()}...",
                    speed=f"{service_name.capitalize()}",
                )
                state.save_download_status()

                if service_name == 'tidal':
                    downloader = tidal.TidalDownloader()
                    downloader.download(service_data, output_path, quality)
                    download_success = True
                    break

                elif service_name == 'qobuz':
                    downloader = qobuz.QobuzDownloader()
                    downloader.download(service_data, output_path, quality)
                    download_success = True
                    break

                elif service_name == 'amazon':

                    ext = '.m4a'
                    filename = utils.build_filename(track_metadata, '{artist} - {title}', ext)
                    output_path = os.path.join(download_dir, filename)

                    downloader = amazon.AmazonDownloader()
                    downloader.download(service_data, output_path, asin=sl_result.get('amazon_asin'))
                    download_success = True
                    break

                elif service_name == 'soundcloud':
                    downloader = soundcloud.SoundCloudDownloader()
                    downloaded = downloader.download(service_data, download_dir, 'flac')
                    if downloaded:
                        downloaded = os.path.abspath(downloaded)
                        if downloaded != os.path.abspath(output_path):
                            if os.path.exists(output_path):
                                os.remove(output_path)
                            os.rename(downloaded, output_path)
                        download_success = True
                        break

            except Exception as e:
                last_error = e
                print(f"  {service_name.capitalize()} failed: {e}")
                continue

        if not download_success:
            raise Exception(f"All services failed. Last error: {last_error}")

        state.download_status[download_id].update(
            progress=85,
            eta="Enriching metadata (language detection + lyrics)...",
            speed="Processing",
        )
        state.save_download_status()

        try:
            enriched_metadata = api_metadata_enricher.enrich_track_metadata(track_metadata)
            print(f"   ✅ Language detected: {enriched_metadata.get('language', 'Unknown')} ({enriched_metadata.get('language_detected_from', 'api')})")
            if enriched_metadata.get('lyrics-eng'):
                print(f"   ✅ Lyrics added: {len(enriched_metadata['lyrics-eng'])} characters")
            track_metadata.update(enriched_metadata)
        except Exception as e:
            print(f"   ⚠️  Enrichment failed (will embed with basic metadata): {e}")

        metadata.embed_metadata(output_path, track_metadata)

        req_format   = ((advanced_options or {}).get("audioFormat") or "flac").lower()
        if req_format == "best":
            req_format = "opus"
        req_quality  = str((advanced_options or {}).get("audioQuality", "0"))
        embed_thumb  = (advanced_options or {}).get("embedThumbnail", True)
        downloaded_ext = os.path.splitext(output_path)[1].lstrip(".").lower()

        _SUPPORTED_CONVERT_FMTS = {"mp3", "aac", "m4a", "ogg", "opus", "flac", "wav"}
        needs_conversion = (
            req_format in _SUPPORTED_CONVERT_FMTS
            and req_format != downloaded_ext

            and not (downloaded_ext in ("m4a",) and req_format == "flac")
        )

        if needs_conversion:
            try:
                from spoflac_core.modules.audio_converter import AudioConverter

                converted_filename = os.path.splitext(os.path.basename(output_path))[0] + f".{req_format}"
                converted_path = os.path.join(os.path.dirname(output_path), converted_filename)

                print(f" Converting {downloaded_ext.upper()} → {req_format.upper()} (quality={req_quality})")

                state.download_status[download_id].update(
                    progress=90,
                    eta=f"Converting to {req_format.upper()}...",
                    speed="Converting",
                )
                state.save_download_status()

                quality_kwargs = _converter_quality_kwargs(req_format, req_quality)
                converter = AudioConverter()
                converter.convert(
                    output_path,
                    converted_path,
                    req_format,
                    preserve_metadata=True,
                    overwrite=True,
                    **quality_kwargs,
                )

                try:
                    os.remove(output_path)
                except OSError:
                    pass

                output_path = converted_path
                print(f" Converted → {os.path.basename(output_path)}")

                if req_format == 'mp3' and track_metadata.get('lyrics-eng'):
                    try:
                        print(f" Re-embedding lyrics-eng into MP3...")
                        from spoflac_core.modules import metadata as meta_module
                        meta_module.embed_mp3_metadata(output_path, track_metadata, cover_path=None)
                        print(f" ✓ Lyrics-eng re-embedded into MP3")
                    except Exception as re_embed_exc:
                        print(f"  (Lyrics re-embed failed: {re_embed_exc})")

            except Exception as conv_exc:
                print(f" Conversion to {req_format.upper()} failed: {conv_exc} — keeping {downloaded_ext.upper()}")
        else:
            pass

        state.download_status[download_id].update(
            progress=95,
            eta="Enhancing metadata/artwork...",
            speed="Post-processing",
        )
        state.save_download_status()

        try:
            enrichment_result = run_post_download_enrichment(output_path, metadata_context=track_metadata)
            print(
                f" Post-process: metadata={enrichment_result.get('metadata_enriched')} "
                f"artwork={enrichment_result.get('artwork_updated')}"
            )
        except Exception as post_exc:
            print(f" Post-process skipped (SpotiFLAC): {post_exc}")

        _run_cli_music_hardening(output_path)

        file_size = os.path.getsize(output_path) / (1024 * 1024)
        print(f" SpotiFLAC done: {os.path.basename(output_path)} ({file_size:.1f} MB)")

        state.download_status[download_id].update(
            status="complete",
            progress=100,
            file=os.path.basename(output_path),
            speed="Complete",
            eta="0:00",
            completed_at=datetime.now().isoformat(),
        )
        state.save_download_status()

    except Exception as exc:
        print(f"\n❌ SpotiFLAC download failed: {exc}")
        state.download_status[download_id].update(
            status="error",
            progress=0,
            error=f"SpotiFLAC download failed: {exc}",
            speed="0 KB/s",
            eta="N/A",
            failed_at=datetime.now().isoformat(),
        )
        state.save_download_status()
        raise

def download_with_proxy_api(url: str, title: str, download_id: str, advanced_options=None) -> None:
    """
    Fallback download via p.savenow.to when yt-dlp fails.
    Audio: Always downloads FLAC (lossless source), then converts to requested format/quality.
    Video: Downloads video directly in requested format.
    """
    try:
        print(f" Proxy API fallback for: {title}")
        if not config.VIDEO_DOWNLOAD_API_KEY:
            raise Exception("Proxy API key not configured")

        state.download_status[download_id].update(
            status="downloading", progress=0,
            eta="Initiating proxy download…", speed="0 KB/s",
        )
        state.save_download_status()

        is_video = advanced_options and advanced_options.get("keepVideo", False)
        download_dir = os.path.join(config.DOWNLOAD_FOLDER, download_id)
        os.makedirs(download_dir, exist_ok=True)

        if is_video:
            video_quality = advanced_options.get("videoQuality", "1080")
            format_type = video_quality
            file_extension = "mp4"
        else:
            format_type = "flac"
            file_extension = "flac"

        params: dict = {
            "copyright": "0",
            "allow_extended_duration": "1",
            "format": format_type,
            "url": url,
            "api": config.VIDEO_DOWNLOAD_API_KEY,
            "add_info": "1",
        }

        api_url = "https://p.savenow.to/ajax/download.php"
        print(" Calling proxy API:", api_url + "?" + urllib.parse.urlencode(params))

        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            raise Exception(data.get("message", "Failed to initiate download"))

        job_id = data.get("id")
        if not job_id:
            raise Exception("No job ID returned from API")

        print(f" Proxy job ID: {job_id}")

        for _ in range(60):
            prog_resp = requests.get(f"https://p.savenow.to/api/progress?id={job_id}", timeout=10)
            prog_data = prog_resp.json()
            pct = round((prog_data.get("progress", 0) / 1000) * 100)
            text = prog_data.get("text", "Processing")

            state.download_status[download_id].update(
                status="downloading", progress=pct, eta=f"{text}…", speed="Proxy API",
            )
            state.save_download_status()

            if prog_data.get("success") == 1 and prog_data.get("progress") == 1000:
                dl_url = prog_data.get("download_url")
                if not dl_url:
                    raise Exception("No download URL in completed response")

                filename = f"{_safe_title(title)}.{file_extension}"
                local_path = os.path.join(download_dir, filename)

                print(f" Proxy download completed remotely, saving local file: {filename}")
                with requests.get(dl_url, stream=True, timeout=120) as file_resp:
                    file_resp.raise_for_status()
                    with open(local_path, 'wb') as out_file:
                        for chunk in file_resp.iter_content(chunk_size=1024 * 128):
                            if chunk:
                                out_file.write(chunk)

                if not is_video:
                    audio_format = ((advanced_options or {}).get("audioFormat") or "flac").lower()
                    req_quality = str((advanced_options or {}).get("audioQuality", "0"))

                    # If user selected "best" quality, prefer opus codec
                    if audio_format == "best":
                        req_format = "opus"
                    else:
                        req_format = audio_format

                    state.download_status[download_id].update(
                        progress=85,
                        eta=f"Converting to {req_format.upper()}...",
                        speed="Converting",
                    )
                    state.save_download_status()

                    _SUPPORTED_CONVERT_FMTS = {"mp3", "aac", "m4a", "ogg", "opus", "flac", "wav"}
                    needs_conversion = req_format in _SUPPORTED_CONVERT_FMTS and req_format != "flac"

                    if needs_conversion:
                        try:
                            from spoflac_core.modules.audio_converter import AudioConverter

                            converted_filename = os.path.splitext(os.path.basename(local_path))[0] + f".{req_format}"
                            converted_path = os.path.join(download_dir, converted_filename)

                            quality_kwargs = _converter_quality_kwargs(req_format, req_quality)

                            print(f" Converting {file_extension.upper()} → {req_format.upper()} (quality={req_quality})")

                            converter = AudioConverter()
                            converter.convert(
                                local_path,
                                converted_path,
                                req_format,
                                preserve_metadata=True,
                                overwrite=True,
                                **quality_kwargs,
                            )

                            try:
                                os.remove(local_path)
                            except OSError:
                                pass

                            local_path = converted_path
                            filename = converted_filename
                            print(f" Converted → {os.path.basename(local_path)}")

                        except Exception as conv_exc:
                            print(f" Conversion to {req_format.upper()} failed: {conv_exc} — keeping FLAC")

                    _run_cli_music_hardening(local_path)

                state.download_status[download_id].update(
                    status="complete", progress=100, file=filename,
                    speed="Complete", eta="0:00",
                    completed_at=datetime.now().isoformat(),
                    downloaded_via="proxy_api",
                    download_url=f"/get_file/{download_id}/{filename}",
                    source_download_url=dl_url,
                    alternative_download_urls=prog_data.get("alternative_download_urls", []),
                )
                state.save_download_status()
                print(f" Proxy download complete (local): {local_path}")
                return

            time.sleep(2)

        raise Exception("Download timeout — took too long to process")

    except Exception as exc:
        print(f" Proxy API failed: {exc}")
        state.download_status[download_id].update(
            status="error", progress=0,
            error=f"Both yt-dlp and proxy API failed. Last error: {exc}",
            speed="0 KB/s", eta="N/A",
            failed_at=datetime.now().isoformat(),
        )
        state.save_download_status()
        raise

def _detect_spoflac_platform(url: str) -> str | None:
    """
    Return the platform name if the URL should be routed to SpotiFLAC,
    or None if yt-dlp should handle it directly.

    yt-dlp handles natively (returns None — no SpotiFLAC involvement):
        youtube.com, youtu.be, music.youtube.com, soundcloud.com,
        jiosaavn.com, saavn.com

    SpotiFLAC only — no yt-dlp fallback (SpotiFLAC has its own
    internal Tidal → Qobuz → Amazon → SoundCloud fallback chain):
        spotify, tidal, qobuz, amazon music, deezer, apple music,
        and any other URL not covered by yt-dlp above.
    """
    url_lower = url.lower()

    if 'music.youtube.com' in url_lower:
        return None
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return None
    if 'soundcloud.com' in url_lower:
        return None
    if 'jiosaavn.com' in url_lower or 'saavn.com' in url_lower:
        return None

    if 'spotify.com' in url_lower or url.startswith('spotify:'):
        return 'spotify'
    if 'tidal.com' in url_lower:
        return 'tidal'
    if 'qobuz.com' in url_lower:
        return 'qobuz'
    if 'music.amazon' in url_lower or ('amazon.com' in url_lower and 'music' in url_lower):
        return 'amazon'
    if 'deezer.com' in url_lower:
        return 'deezer'
    if 'music.apple.com' in url_lower or 'itunes.apple.com' in url_lower:
        return 'appleMusic'

    return 'unknown'

def download_song(url: str, title: str, download_id: str, advanced_options=None) -> None:
    """
    Download *url* to disk.

    Routing logic:
      - Spotify / Tidal / Qobuz / Amazon / Deezer / Apple Music / unknown
            → SpotiFLAC only (internal fallback: Tidal→Qobuz→Amazon→SoundCloud)
            → NO yt-dlp fallback
      - YouTube / YouTube Music / SoundCloud / JioSaavn
            → yt-dlp directly (unchanged original behaviour)

    Progress is written into ``state.download_status[download_id]`` in
    real-time.
    """
    from core.state import download_status, active_processes, save_download_status

    platform = _detect_spoflac_platform(url)

    if platform is not None:
        audio_format = (advanced_options or {}).get("audioFormat", "flac")
        if audio_format == "best":
            audio_format = "opus"

        _PLATFORM_LABELS = {
            'spotify':    'Spotify',
            'tidal':      'Tidal',
            'qobuz':      'Qobuz',
            'amazon':     'Amazon Music',
            'deezer':     'Deezer',
            'appleMusic': 'Apple Music',
            'unknown':    'Unknown (catch-all)',
        }
        label = _PLATFORM_LABELS.get(platform, platform)
        print(f" SpotiFLAC route: {label} | format={audio_format}")

        download_status[download_id] = _initial_status(title, url, advanced_options, "downloading")
        save_download_status()

        try:
            download_with_spoflac(url, title, download_id, advanced_options)
        except Exception as exc:
            print(f"⚠️  SpotiFLAC failed for {label}: {exc}")
            download_status[download_id].update(
                status="error",
                progress=0,
                error=f"SpotiFLAC failed: {exc}",
                speed="0 KB/s",
                eta="N/A",
                failed_at=datetime.now().isoformat(),
            )
            save_download_status()
        return

    if config.FORCE_PROXY_API and ("youtube.com" in url or "youtu.be" in url):
        download_status[download_id] = _initial_status(title, url, advanced_options, "downloading")
        download_status[download_id]["eta"] = "Initiating proxy download…"
        save_download_status()
        try:
            download_with_proxy_api(url, title, download_id, advanced_options)
            return
        except Exception as exc:
            download_status[download_id].update(
                status="error", progress=0,
                error=f"Proxy API failed: {exc}",
                speed="0 KB/s", eta="N/A",
                failed_at=datetime.now().isoformat(),
            )
            save_download_status()
            return

    state.cleanup_tmp_directory()

    download_status[download_id] = _initial_status(title, url, advanced_options, "downloading")
    save_download_status()

    try:
        if not url or not isinstance(url, str):
            raise ValueError("Invalid URL")
        if not url.startswith(("http://", "https://")):
            raise ValueError("Only HTTP/HTTPS URLs are allowed")

        safe = _safe_title(title)
        cmd = _build_cmd(url, advanced_options)

        download_dir = os.path.join(config.DOWNLOAD_FOLDER, download_id)
        os.makedirs(download_dir, exist_ok=True)

        cmd.extend(["-P", download_dir, "-o", "%(title)s.%(ext)s", "--newline", url])

        creation_flags = 0
        if os.name == "nt":
            creation_flags = subprocess.BELOW_NORMAL_PRIORITY_CLASS

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            shell=False,
            creationflags=creation_flags,
        )
        active_processes[download_id] = process

        if os.name != "nt":
            try:
                import resource
                os.setpriority(os.PRIO_PROCESS, process.pid, 10)
            except Exception:
                pass

        error_messages: list[str] = []
        has_progress = False
        current_idx = 0
        total_files = 0
        completed_files: list[dict] = []

        _ERROR_PATTERNS = (
            "Video unavailable", "Private video", "This video is not available",
            "Unable to download", "HTTP Error", "is not a valid URL",
            "Unsupported URL", "no suitable formats",
            "Requested format is not available", "Sign in to confirm",
            "members-only content", "not supported", "Unsupported site",
            "No video formats found",
        )

        for raw_line in process.stdout:
            if download_status.get(download_id, {}).get("status") == "cancelled":
                process.terminate()
                break

            line = raw_line.strip()

            pm = re.search(r"Downloading (?:item|video) (\d+) of (\d+)", line)
            if pm:
                current_idx = int(pm.group(1))
                total_files = int(pm.group(2))
                download_status[download_id]["title"] = f"Downloading {current_idx}/{total_files}"
                save_download_status()

            if "ERROR:" in line:
                error_messages.append(line.replace("ERROR:", "").strip())
            if any(p.lower() in line.lower() for p in _ERROR_PATTERNS):
                error_messages.append(line)

            if "[download]" in line and "%" in line:
                has_progress = True
                try:
                    pct_m = re.search(r"(\d+\.?\d*)%", line)
                    if not pct_m:
                        continue

                    progress = float(pct_m.group(1))

                    if progress >= 100.0 and total_files > 0:

                        try:
                            existing = os.listdir(download_dir)
                            if existing:
                                newest = max(
                                    (os.path.join(download_dir, f) for f in existing),
                                    key=os.path.getctime,
                                )
                                fname = os.path.basename(newest)
                                if fname not in {f["file"] for f in completed_files}:
                                    fid = f"{download_id}_file_{len(completed_files)}"
                                    ftitle = os.path.splitext(fname)[0]
                                    download_status[fid] = {
                                        "status": "complete", "progress": 100,
                                        "title": ftitle, "url": url, "file": fname,
                                        "speed": "Complete", "eta": "0:00",
                                        "timestamp": download_status[download_id]["timestamp"],
                                        "completed_at": datetime.now().isoformat(),
                                        "advanced_options": advanced_options,
                                        "parent_download_id": download_id,
                                        "file_index": len(completed_files) + 1,
                                        "total_files": total_files,
                                    }
                                    completed_files.append({"download_id": fid, "title": ftitle, "file": fname})
                                    download_status[download_id]["file_downloads"] = completed_files.copy()
                                    save_download_status()
                        except Exception:
                            pass

                    if total_files > 0:
                        progress = ((len(completed_files) + progress / 100) / total_files) * 100

                    speed_m = re.search(r"at\s+([\d\.]+\s*[KMG]iB/s)", line)
                    eta_m = re.search(r"ETA\s+([\d:]+)", line)

                    display_title = title
                    if total_files > 0:
                        display_title = f"Downloading {current_idx}/{total_files}: {title}"

                    download_status[download_id] = {
                        "status": "downloading",
                        "progress": min(progress, 99),
                        "title": display_title,
                        "url": url,
                        "speed": speed_m.group(1) if speed_m else "Unknown",
                        "eta": eta_m.group(1) if eta_m else "Unknown",
                        "current_file": current_idx if total_files > 0 else None,
                        "total_files": total_files if total_files > 0 else None,
                        "file_downloads": completed_files.copy() if completed_files else None,
                        "timestamp": download_status[download_id]["timestamp"],
                        "advanced_options": advanced_options,
                    }
                    save_download_status()
                except Exception:
                    pass

        if download_id in active_processes:
            del active_processes[download_id]

        process.wait()

        if download_status.get(download_id, {}).get("status") == "cancelled":
            return

        if error_messages:
            download_status[download_id].update(
                status="error", progress=0,
                error=" | ".join(error_messages[:3]),
                speed="0 KB/s", eta="N/A",
                failed_at=datetime.now().isoformat(),
            )
            save_download_status()
            return

        if process.returncode == 0:
            _finalise_success(
                download_id, url, title, safe, download_dir,
                completed_files, total_files, has_progress, advanced_options,
            )
        else:
            error_text = " | ".join(error_messages[:3]) if error_messages else "Download failed"
            download_status[download_id].update(
                status="error", progress=0, error=error_text,
                speed="0 KB/s", eta="N/A",
                failed_at=datetime.now().isoformat(),
            )
            save_download_status()

            if "youtube.com" in url or "youtu.be" in url:
                try:
                    download_with_proxy_api(url, title, download_id, advanced_options)
                    return
                except Exception:
                    pass

    except Exception as exc:
        state.download_status[download_id].update(
            status="error", progress=0, error=str(exc),
            speed="0 KB/s", eta="N/A",
            failed_at=datetime.now().isoformat(),
        )
    finally:
        state.save_download_status()
        if download_id in state.active_processes:
            del state.active_processes[download_id]

def _initial_status(title: str, url: str, advanced_options, status: str = "queued") -> dict:
    return {
        "status": status, "progress": 0, "title": title, "url": url,
        "eta": "Calculating…", "speed": "0 KB/s",
        "timestamp": datetime.now().isoformat(),
        "advanced_options": advanced_options,
    }

def _build_cmd(url: str, advanced_options) -> list[str]:
    """Build the yt-dlp command list (without output path or URL)."""
    ALLOWED_AUDIO_FMTS = {"best", "mp3", "m4a", "opus", "vorbis", "wav", "flac"}
    ALLOWED_QUALITIES = {"0", "2", "5", "9"}
    ALLOWED_VIDEO_FMTS = {"mkv", "mp4", "webm"}
    SAFE_ARGS = {
        "--geo-bypass", "--geo-bypass-country", "--prefer-free-formats",
        "--no-playlist", "--yes-playlist", "--playlist-items",
        "--playlist-start", "--playlist-end", "--max-downloads",
        "--windows-filenames", "--format-sort",
        "--max-filesize", "--min-filesize", "--limit-rate", "--throttled-rate",
        "--retries", "--fragment-retries", "--skip-unavailable-fragments",
        "--abort-on-unavailable-fragment", "--keep-fragments",
        "--write-subs", "--write-auto-subs", "--sub-langs",
        "--sub-format", "--convert-subs",
        "--add-chapters", "--split-chapters", "--no-embed-chapters",
        "--xattrs", "--concat-playlist",
        "--no-overwrites", "--continue", "--no-continue", "--no-part",
        "--no-mtime", "--write-description", "--write-info-json",
        "--write-playlist-metafiles", "--encoding",
        "--legacy-server-connect", "--no-check-certificates",
        "--prefer-insecure", "--add-header",
        "--sleep-requests", "--sleep-interval", "--max-sleep-interval",
        "--sleep-subtitles",
    }

    cmd = ["yt-dlp"]

    if not advanced_options:
        cmd.extend(["-x", "--audio-format", "mp3", "--audio-quality", "0",
                    "--embed-metadata", "--embed-thumbnail"])
        return cmd

    audio_fmt = advanced_options.get("audioFormat", "mp3")
    if audio_fmt not in ALLOWED_AUDIO_FMTS:
        audio_fmt = "mp3"

    aq = advanced_options.get("audioQuality", "0")
    if aq not in ALLOWED_QUALITIES:
        aq = "0"

    video_fmt = advanced_options.get("videoFormat", "mkv")
    if video_fmt not in ALLOWED_VIDEO_FMTS:
        video_fmt = "mkv"

    keep_video = advanced_options.get("keepVideo", False)
    embed_thumbnail = advanced_options.get("embedThumbnail", True)
    add_metadata = advanced_options.get("addMetadata", True)
    embed_subs = advanced_options.get("embedSubtitles", False)
    custom_args = advanced_options.get("customArgs", "")
    geo_bypass = advanced_options.get("geoBypass", False)
    prefer_free_formats = advanced_options.get("preferFreeFormats", False)
    speed_limit = advanced_options.get("speedLimit", "")
    max_file_size = advanced_options.get("maxFileSize", "")

    if keep_video:
        vq = advanced_options.get("videoQuality", "1080")
        fps = advanced_options.get("videoFPS", "30")
        if vq == "best":
            fmt_sel = "bestvideo+bestaudio/best"
        elif fps == "60":
            fmt_sel = f"bestvideo[height<={vq}][fps<=60]+bestaudio/best[height<={vq}]"
        elif fps == "30":
            fmt_sel = f"bestvideo[height<={vq}][fps<=30]+bestaudio/best[height<={vq}]"
        else:
            fmt_sel = f"bestvideo[height<={vq}]+bestaudio/best[height<={vq}]"

        cmd.extend(["-f", fmt_sel, "--recode-video", video_fmt])
        if embed_subs:
            cmd.extend(["--embed-subs", "--write-auto-subs", "--sub-langs", "en.*,hi.*,all"])
    else:
        url_lower = (url or "").lower()
        if any(host in url_lower for host in ("music.youtube.com", "youtube.com", "youtu.be")):
            if audio_fmt == "best":
                cmd.extend(["-f", "bestaudio[acodec=opus][abr>=96]/bestaudio"])
                cmd.extend(["-x", "--audio-format", "opus", "--audio-quality", aq])
            else:
                cmd.extend(["-x", "--audio-format", audio_fmt, "--audio-quality", aq])
        else:
            cmd.extend(["-x", "--audio-format", audio_fmt, "--audio-quality", aq])

        if audio_fmt == "mp3":

            mp3_bitrate = {
                "0": "320k",
                "2": "256k",
                "5": "192k",
                "9": "128k",
            }.get(aq, "320k")
            cmd.extend(["--postprocessor-args", f"ExtractAudio+ffmpeg_o:-b:a {mp3_bitrate}"])

    if add_metadata:
        cmd.append("--embed-metadata")
    if embed_thumbnail and not keep_video:
        cmd.append("--embed-thumbnail")
    if geo_bypass:
        cmd.append("--geo-bypass")
    if prefer_free_formats:
        cmd.append("--prefer-free-formats")
    if speed_limit:
        cmd.extend(["--limit-rate", speed_limit])
    if max_file_size:
        cmd.extend(["--max-filesize", max_file_size])

    DANGEROUS = {"&&", "||", ";", "|", "`", "$", "\n", "\r"}
    if custom_args and not any(d in custom_args for d in DANGEROUS):
        try:
            parsed = shlex.split(custom_args)
            i = 0
            while i < len(parsed):
                arg = parsed[i]
                if any(d in arg for d in DANGEROUS):
                    i += 1
                    continue
                ak = arg.split("=")[0] if "=" in arg else arg
                if ak in SAFE_ARGS:
                    cmd.append(arg)
                    if "=" not in arg and i + 1 < len(parsed) and not parsed[i + 1].startswith("-"):
                        cmd.append(parsed[i + 1])
                        i += 1
                i += 1
        except Exception:
            pass

    return cmd

def _embed_lyrics_for_file(filepath: str) -> None:
    """
    Fetch and embed synced/plain lyrics into an audio file produced by yt-dlp.
    Reads existing mutagen tags for title/artist/album, queries lrclib.net,
    romanizes non-Latin scripts, then embeds the result via spoflac_core metadata.
    Non-fatal — all exceptions are silently swallowed.
    """
    try:
        import mutagen
        from spoflac_core.modules.url_resolver import URLResolver
        from spoflac_core.modules import metadata as meta

        audio = mutagen.File(filepath, easy=True)
        if audio is None:
            return

        def _tag(key):
            val = audio.get(key)
            return val[0] if val else ''

        track_title  = _tag('title')
        track_artist = _tag('artist')
        track_album  = _tag('album')

        if not track_title:

            stem = os.path.splitext(os.path.basename(filepath))[0]
            if ' - ' in stem:
                track_artist, track_title = stem.split(' - ', 1)
            else:
                track_title = stem

        try:
            length = audio.info.length * 1000
        except Exception:
            length = None

        resolver = URLResolver()
        lyrics = resolver._fetch_lyrics_lrclib(track_title, track_artist, track_album, length)
        if not lyrics:
            return

        lyrics = resolver._romanize_lrc_lyrics(lyrics)

        ext = os.path.splitext(filepath)[1].lower()
        tag_meta = {'lyrics-eng': lyrics}
        if ext == '.flac':
            meta.embed_flac_metadata(filepath, tag_meta)
        elif ext == '.mp3':
            meta.embed_mp3_metadata(filepath, tag_meta)
        elif ext in ('.m4a', '.aac'):
            meta.embed_m4a_metadata(filepath, tag_meta)

    except Exception:
        pass

def _finalise_success(
    download_id, url, title, safe, download_dir,
    completed_files, total_files, has_progress, advanced_options,
):
    from core.state import download_status, save_download_status

    try:
        files = os.listdir(download_dir)
    except FileNotFoundError:
        files = []

    if not has_progress and not files:
        download_status[download_id].update(
            status="error", progress=0,
            error="No download progress detected. URL may be invalid or unavailable.",
            speed="0 KB/s", eta="N/A",
            failed_at=datetime.now().isoformat(),
        )
        save_download_status()
        return

    if len(files) > 1 and total_files > 0:
        for fname in files:
            file_path = os.path.join(download_dir, fname)
            if os.path.isfile(file_path):
                try:
                    run_post_download_enrichment(file_path, metadata_context={"title": os.path.splitext(fname)[0]})
                except Exception as post_exc:
                    print(f" Post-process skipped for {fname}: {post_exc}")
                _run_cli_music_hardening(file_path)

        if completed_files:
            fds = completed_files
        else:
            fds = []
            for idx, fname in enumerate(
                sorted((os.path.join(download_dir, f) for f in files), key=os.path.getctime)
            ):
                bname = os.path.basename(fname)
                ftitle = os.path.splitext(bname)[0]
                fid = f"{download_id}_file_{idx}"
                download_status[fid] = {
                    "status": "complete", "progress": 100,
                    "title": ftitle, "url": url, "file": bname,
                    "speed": "Complete", "eta": "0:00",
                    "timestamp": download_status[download_id]["timestamp"],
                    "completed_at": datetime.now().isoformat(),
                    "advanced_options": advanced_options,
                    "parent_download_id": download_id,
                    "file_index": idx + 1, "total_files": len(files),
                }
                fds.append({"download_id": fid, "title": ftitle, "file": bname})

        first_title = fds[0]["title"] if fds else "Playlist"
        download_status[download_id] = {
            "status": "complete", "progress": 100,
            "title": f"{first_title} (+{len(files)-1} more)",
            "url": url, "file_count": len(files), "file_downloads": fds,
            "speed": "Complete", "eta": "0:00",
            "timestamp": download_status[download_id]["timestamp"],
            "completed_at": datetime.now().isoformat(),
            "advanced_options": advanced_options,
        }
    else:
        fname = None
        if files:
            fname = os.path.basename(
                max((os.path.join(download_dir, f) for f in files), key=os.path.getctime)
            )

        opts = advanced_options or {}
        if fname and not opts.get('keepVideo', False):
            target_path = os.path.join(download_dir, fname)
            try:
                post_result = run_post_download_enrichment(target_path, metadata_context={"title": title})
                if not post_result.get("metadata_enriched"):
                    _embed_lyrics_for_file(target_path)
            except Exception as post_exc:
                print(f" Post-process skipped for {fname}: {post_exc}")
            _run_cli_music_hardening(target_path)

        download_status[download_id] = {
            "status": "complete", "progress": 100,
            "title": os.path.splitext(fname)[0] if fname else title,
            "url": url,
            "file": fname or f"{safe}.mp3",
            "speed": "Complete", "eta": "0:00",
            "timestamp": download_status[download_id]["timestamp"],
            "completed_at": datetime.now().isoformat(),
            "advanced_options": advanced_options,
        }

    save_download_status()
