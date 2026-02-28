"""
Download service — yt-dlp subprocess orchestration + proxy API fallback.

All functions here run in background threads started from the download routes.
State mutations go through the shared ``state`` module.
"""

import os
import re
import shlex
import subprocess
import time
import urllib.parse
from datetime import datetime

import requests

import config
import state


# ── Helpers ────────────────────────────────────────────────────────────────────

def _safe_title(title: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", title)


# ── Proxy API fallback ─────────────────────────────────────────────────────────

def download_with_proxy_api(url: str, title: str, download_id: str, advanced_options=None) -> None:
    """Fallback download via p.savenow.to when yt-dlp fails."""
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

        if is_video:
            video_quality = advanced_options.get("videoQuality", "1080")
            format_type = video_quality
            file_extension = "mp4"
        else:
            audio_format = (advanced_options or {}).get("audioFormat", "mp3")
            format_type = audio_format if audio_format in ("mp3", "m4a", "flac", "wav", "opus") else "mp3"
            file_extension = format_type

        params: dict = {
            "copyright": "0",
            "allow_extended_duration": "1",
            "format": format_type,
            "url": url,
            "api": config.VIDEO_DOWNLOAD_API_KEY,
            "add_info": "1",
        }
        if advanced_options:
            aq = advanced_options.get("audioQuality")
            if aq:
                params["audio_quality"] = aq

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

        for _ in range(60):  # 2-minute max
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
                state.download_status[download_id].update(
                    status="complete", progress=100, file=filename,
                    speed="Complete", eta="0:00",
                    completed_at=datetime.now().isoformat(),
                    downloaded_via="proxy_api",
                    download_url=dl_url,
                    alternative_download_urls=prog_data.get("alternative_download_urls", []),
                )
                state.save_download_status()
                print(f" Proxy download complete: {dl_url}")
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


# ── yt-dlp core download ───────────────────────────────────────────────────────

def download_song(url: str, title: str, download_id: str, advanced_options=None) -> None:
    """
    Download *url* to disk using yt-dlp.

    Progress is written into ``state.download_status[download_id]`` in
    real-time.  If yt-dlp fails for YouTube URLs and a proxy API key is
    configured, falls back to ``download_with_proxy_api()``.
    """
    from state import download_status, active_processes, save_download_status

    # ── Proxy-API-only mode (testing flag) ────────────────────────────────────
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

    # ── Normal yt-dlp path ────────────────────────────────────────────────────
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
                import resource  # noqa: F401
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

            # Playlist item counter
            pm = re.search(r"Downloading (?:item|video) (\d+) of (\d+)", line)
            if pm:
                current_idx = int(pm.group(1))
                total_files = int(pm.group(2))
                download_status[download_id]["title"] = f"Downloading {current_idx}/{total_files}"
                save_download_status()

            # Error detection
            if "ERROR:" in line:
                error_messages.append(line.replace("ERROR:", "").strip())
            if any(p.lower() in line.lower() for p in _ERROR_PATTERNS):
                error_messages.append(line)

            # Progress parsing
            if "[download]" in line and "%" in line:
                has_progress = True
                try:
                    pct_m = re.search(r"(\d+\.?\d*)%", line)
                    if not pct_m:
                        continue

                    progress = float(pct_m.group(1))

                    if progress >= 100.0 and total_files > 0:
                        # A playlist item just finished — snapshot it
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
            # YouTube fallback
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


# ── Private helpers ────────────────────────────────────────────────────────────

def _initial_status(title: str, url: str, advanced_options, status: str = "queued") -> dict:
    return {
        "status": status, "progress": 0, "title": title, "url": url,
        "eta": "Calculating…", "speed": "0 KB/s",
        "timestamp": datetime.now().isoformat(),
        "advanced_options": advanced_options,
    }


def _build_cmd(url: str, advanced_options) -> list[str]:
    """Build the yt-dlp command list (without output path or URL)."""
    ALLOWED_AUDIO_FMTS = {"mp3", "m4a", "opus", "vorbis", "wav", "flac"}
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
        cmd.extend(["-x", "--audio-format", audio_fmt, "--audio-quality", aq])

    if add_metadata:
        cmd.append("--embed-metadata")
    if embed_thumbnail and not keep_video:
        cmd.append("--embed-thumbnail")

    # Custom args — strict whitelist
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


def _finalise_success(
    download_id, url, title, safe, download_dir,
    completed_files, total_files, has_progress, advanced_options,
):
    from state import download_status, save_download_status

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
        # Playlist
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
