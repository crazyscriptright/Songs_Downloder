"""
FLAC Download Blueprint
Routes:
    POST /flac/download           — queue a FLAC download (Spotify/Tidal/Qobuz/Amazon)
    GET  /flac/status/<id>        — poll status for a FLAC download
    GET  /flac/file/<id>/<name>   — serve the finished file

Integrates the spoflac_core/main.py SpotiFLAC download logic into the Flask app.
"""

import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

import config
import state
import api_metadata_enricher
from services.post_download_enricher import run_post_download_enrichment

from spoflac_core.modules import amazon
from spoflac_core.modules import metadata
from spoflac_core.modules import qobuz
from spoflac_core.modules import soundcloud
from spoflac_core.modules import tidal
from spoflac_core.modules import url_resolver
from spoflac_core.modules import utils

flac_bp = Blueprint("flac", __name__, url_prefix="/flac")


def _run_cli_music_hardening(file_path: str) -> None:
    """Run CLI metadata hardening for a local music file."""
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

        subprocess.run(
            [python_exec, 'tools/enrich_metadata.py', str(path), '-y'],
            cwd=str(backend_dir),
            env=env,
            check=False,
            capture_output=True,
        )
    except Exception as exc:
        print(f"[flac] CLI hardening skipped: {exc}")

def _update(download_id: str, status: str, progress: int | None = None, message: str = "") -> None:
    """Mutate the shared status entry and persist it."""
    entry = state.download_status[download_id]
    entry["status"] = status
    entry["eta"] = message
    if progress is not None:
        entry["progress"] = progress
    state.save_download_status()

def _run_flac_download(
    download_id: str,
    music_url: str,
    service: str,
    quality: str,
    output: str,
    template: str,
    fallback: bool,
) -> None:
    """
    Background thread: URL → metadata → download → embed tags.
    Uses URLResolver which accepts any platform URL (Spotify/Tidal/Qobuz/Amazon/SoundCloud).
    """
    try:

        _update(download_id, "processing", 10, "Resolving URL…")
        result = url_resolver.URLResolver().resolve(music_url)

        track_metadata    = result['metadata']
        sl_result         = result['sl_result']
        detected_platform = result['source_platform']

        state.download_status[download_id]["track"] = {
            "title":  track_metadata.get("title"),
            "artist": track_metadata.get("artist"),
            "album":  track_metadata.get("album"),
        }

        if service == "auto":
            if detected_platform in ("tidal", "qobuz", "amazon", "soundcloud"):
                service = detected_platform
            else:
                service = "tidal"
            print(f"[flac] Auto-selected: {service}  (platform={detected_platform})")

        ext = ".m4a" if service == "amazon" else ".flac"
        filename = utils.build_filename(track_metadata, template, ext)
        utils.ensure_directory(output)
        output_path = os.path.join(output, filename)

        if os.path.exists(output_path):
            state.download_status[download_id].update(
                status="complete", progress=100,
                file=filename, output_path=output_path,
                download_url=f"/flac/file/{download_id}/{filename}",
                eta="Already exists on disk",
            )
            state.save_download_status()
            return

        _update(download_id, "downloading", 40, f"Downloading via {service.capitalize()}…")

        services_to_try = [service]
        if fallback:
            fallback_chain = ["tidal", "qobuz", "amazon", "soundcloud"]
            services_to_try += [s for s in fallback_chain if s != service]

        download_success = False
        last_error: Exception | None = None

        for idx, current_service in enumerate(services_to_try):
            try:
                prog = 40 + int((idx / max(len(services_to_try), 1)) * 45)
                _update(download_id, "downloading", prog, f"Trying {current_service.capitalize()}…")

                if current_service == "tidal":
                    service_url = sl_result['tidal_url']
                    if not service_url:
                        raise Exception("Tidal URL not available from song.link")
                    tidal.TidalDownloader().download(service_url, output_path, quality)
                    download_success = True
                    break

                elif current_service == "qobuz":
                    isrc = sl_result['isrc']
                    if not isrc:
                        raise Exception("ISRC not found — cannot search Qobuz")
                    qobuz.QobuzDownloader().download(isrc, output_path, quality)
                    download_success = True
                    break

                elif current_service == "amazon":
                    service_url = sl_result['amazon_url']
                    if not service_url:
                        raise Exception("Amazon URL not available from song.link")
                    amazon.AmazonDownloader().download(
                        service_url, output_path, asin=sl_result['amazon_asin']
                    )
                    download_success = True
                    break

                elif current_service == "soundcloud":
                    sc_url = sl_result['soundcloud_url']
                    if not sc_url:
                        raise Exception("SoundCloud URL not available from song.link")
                    out_dir = os.path.dirname(os.path.abspath(output_path))
                    downloaded = soundcloud.SoundCloudDownloader().download(sc_url, out_dir, 'flac')
                    if not downloaded:
                        raise Exception("SoundCloud/yt-dlp returned no file")
                    downloaded = os.path.abspath(downloaded)
                    if downloaded != os.path.abspath(output_path):
                        if os.path.exists(output_path):
                            os.remove(output_path)
                        os.rename(downloaded, output_path)
                    download_success = True
                    break

                else:
                    raise Exception(f"Unknown service: {current_service}")

            except Exception as exc:
                last_error = exc
                print(f"[flac] {current_service} failed: {exc}")
                if not fallback or current_service == services_to_try[-1]:
                    break

        if not download_success:
            raise Exception(f"All services failed. Last error: {last_error}")

        _update(download_id, "processing", 92, "Enriching metadata (language + lyrics)…")
        
        # Enrich metadata with language detection + lyrics
        try:
            enriched_metadata = api_metadata_enricher.enrich_track_metadata(track_metadata)
            print(f"[flac] ✓ Language: {enriched_metadata.get('language', 'Unknown')} ({enriched_metadata.get('language_detected_from', 'api')})")
            if enriched_metadata.get('lyrics-eng'):
                print(f"[flac] ✓ Lyrics: {len(enriched_metadata['lyrics-eng'])} characters")
            track_metadata.update(enriched_metadata)
        except Exception as e:
            print(f"[flac] ⚠ Enrichment failed (will embed with basic metadata): {e}")
        
        metadata.embed_metadata(output_path, track_metadata)

        _update(download_id, "processing", 96, "Enhancing metadata/artwork…")
        try:
            enrichment_result = run_post_download_enrichment(output_path, metadata_context=track_metadata)
            print(
                f"[flac] post-process metadata={enrichment_result.get('metadata_enriched')} "
                f"artwork={enrichment_result.get('artwork_updated')}"
            )
        except Exception as post_exc:
            print(f"[flac] post-process skipped: {post_exc}")

        _run_cli_music_hardening(output_path)

        state.download_status[download_id].update(
            status="complete",
            progress=100,
            file=filename,
            output_path=output_path,
            download_url=f"/flac/file/{download_id}/{filename}",
            eta="Done",
        )
        state.save_download_status()
        print(f"[flac] ✓ {filename}  ({os.path.getsize(output_path) / 1_048_576:.2f} MB)")

    except Exception as exc:
        state.download_status[download_id].update(status="error", progress=0, eta=str(exc))
        state.save_download_status()
        print(f"[flac] ✗ download error: {exc}")

@flac_bp.route("/download", methods=["POST"])
def flac_download():
    """
    POST /flac/download

    JSON body (all fields except `url` are optional):
    {
        "url":      "https://open.spotify.com/track/...",
        "service":  "auto" | "tidal" | "qobuz" | "amazon" | "soundcloud",
        "quality":  "HI_RES" | "LOSSLESS" | "6" | "7" | "27",
        "output":   "/path/to/output/dir",
        "template": "{artist} - {title}",
        "fallback": true
    }

    Returns: { "download_id": "flac_...", "status": "started" }
    """
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url:
        return jsonify({"error": "Missing required field: 'url'"}), 400
    if not url.startswith(("http://", "https://", "spotify:")):
        return jsonify({"error": "Invalid URL — must be http/https or a spotify: URI"}), 400

    service  = data.get("service",  config.DEFAULT_SERVICE)
    quality  = data.get("quality",  config.DEFAULT_QUALITY)
    output   = data.get("output",   config.DEFAULT_OUTPUT_DIR)
    template = data.get("template", "{artist} - {title}")
    fallback = bool(data.get("fallback", True))

    valid_services = {"auto", "tidal", "qobuz", "amazon", "soundcloud"}
    if service not in valid_services:
        return jsonify({"error": f"Invalid service. Choose from: {', '.join(sorted(valid_services))}"}), 400

    download_id = f"flac_{datetime.now().timestamp()}"
    state.download_status[download_id] = {
        "status":    "queued",
        "progress":  0,
        "title":     url,
        "url":       url,
        "service":   service,
        "quality":   quality,
        "eta":       "Queued…",
        "speed":     "—",
        "timestamp": datetime.now().isoformat(),
        "type":      "flac",
    }
    state.save_download_status()

    threading.Thread(
        target=_run_flac_download,
        args=(download_id, url, service, quality, output, template, fallback),
        daemon=True,
    ).start()

    return jsonify({"download_id": download_id, "status": "started"})

@flac_bp.route("/status/<download_id>", methods=["GET"])
def flac_status(download_id: str):
    """
    GET /flac/status/<download_id>

    Returns the current status entry for the given download ID.
    Possible status values: queued, processing, downloading, complete, error
    """
    entry = state.download_status.get(download_id)
    if not entry:
        return jsonify({"status": "not_found"}), 404
    return jsonify(entry)

@flac_bp.route("/file/<download_id>/<filename>", methods=["GET"])
def flac_serve_file(download_id: str, filename: str):
    """
    GET /flac/file/<download_id>/<filename>

    Serves the finished FLAC/M4A file as an attachment.
    Only works once the download status is 'complete'.
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "Invalid filename"}), 400

    entry = state.download_status.get(download_id)
    if not entry:
        return jsonify({"error": "Download ID not found"}), 404
    if entry.get("status") != "complete":
        return jsonify({"error": f"Download not complete yet (status: {entry.get('status')})"}), 425

    output_path = entry.get("output_path")
    if not output_path or not os.path.isfile(output_path):
        return jsonify({"error": "File not found on disk"}), 404

    return send_file(output_path, as_attachment=True, download_name=filename)
