"""
FLAC Download Blueprint
Routes:
    POST /flac/download           — queue a FLAC download (Spotify/Tidal/Qobuz/Amazon)
    GET  /flac/status/<id>        — poll status for a FLAC download
    GET  /flac/file/<id>/<name>   — serve the finished file

Integrates the beta_verion/main.py SpotiFLAC download logic into the Flask app.
"""

import os
import threading
from datetime import datetime

from flask import Blueprint, jsonify, request, send_file

import config
import state

# ── beta_verion is a proper sub-package of backend/ ───────────────────────────
# beta_verion/__init__.py exists, so these are standard package imports.
# The beta modules do `from config import …` which resolves to backend/config.py
# (the backend root is always on sys.path when the Flask app runs).
from beta_verion.modules import amazon  # noqa: E402
from beta_verion.modules import metadata  # noqa: E402
from beta_verion.modules import qobuz  # noqa: E402
from beta_verion.modules import songlink  # noqa: F401 E402  (future isrc lookups)
from beta_verion.modules import spotify  # noqa: E402
from beta_verion.modules import tidal  # noqa: E402
from beta_verion.modules import url_detector  # noqa: E402
from beta_verion.modules import utils  # noqa: E402

# SpotDL is optional
SPOTDL_AVAILABLE = False
if config.SPOTDL_ENABLED:
    try:
        from beta_verion.modules import spotdl as _spotdl_mod  # noqa: E402

        SPOTDL_AVAILABLE = True
    except ImportError:
        print("[flac_download] SpotDL not installed — spotdl service will be unavailable.")

flac_bp = Blueprint("flac", __name__, url_prefix="/flac")


# ── Background worker ──────────────────────────────────────────────────────────

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
    Background thread — mirrors the logic of main.py::download().

    Steps
    -----
    1. Detect platform from URL.
    2. Auto-select service when service == 'auto'.
    3. If URL is already from its own platform → direct download.
    4. Otherwise fetch Spotify metadata, then try service(s) in order.
    5. Embed metadata and mark complete.
    """
    try:
        _update(download_id, "processing", 5, "Detecting URL platform…")

        detector = url_detector.URLDetector()
        detected_platform, track_id = detector.get_track_id(music_url)

        if not detected_platform:
            raise Exception(
                "Unsupported URL. Supported platforms: Spotify, Tidal, Qobuz, Amazon"
            )

        # ── Auto service selection ────────────────────────────────────────────
        if service == "auto":
            if detected_platform != "spotify":
                service = detected_platform
            elif SPOTDL_AVAILABLE:
                service = "spotdl"   # only working Spotify → audio path right now
            else:
                service = "tidal"    # placeholder; will fail gracefully
            print(f"[flac] Auto-selected service: {service}")

        # ── Direct download: non-Spotify URL on its own platform ─────────────
        if detected_platform != "spotify" and service == detected_platform:
            _update(download_id, "processing", 15, f"Direct {detected_platform.capitalize()} download…")
            _direct_download(download_id, music_url, detected_platform, track_id, output, template, quality)
            return

        # ── Spotify path ─────────────────────────────────────────────────────
        if not track_id:
            raise Exception("Could not extract Spotify track ID from URL")

        _update(download_id, "processing", 20, "Fetching Spotify metadata…")
        sp = spotify.SpotifyClient()
        track_metadata = sp.get_track_metadata(track_id)

        # Expose track info in the status payload
        state.download_status[download_id]["track"] = {
            "title":  track_metadata.get("title"),
            "artist": track_metadata.get("artist"),
            "album":  track_metadata.get("album"),
        }

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

        # ── Build service list (with optional fallback chain) ─────────────────
        _update(download_id, "downloading", 40, f"Downloading via {service.capitalize()}…")

        services_to_try = [service]
        if fallback and service != "spotdl":
            if detected_platform == "spotify" and SPOTDL_AVAILABLE:
                # For Spotify URLs spotdl is the only reliable path — try it first
                fallback_chain = ["spotdl", "tidal", "qobuz", "amazon"]
            else:
                fallback_chain = ["tidal", "qobuz", "amazon"]
                if SPOTDL_AVAILABLE:
                    fallback_chain.append("spotdl")
            services_to_try += [s for s in fallback_chain if s != service]

        download_success = False
        last_error: Exception | None = None

        for idx, current_service in enumerate(services_to_try):
            try:
                prog = 40 + int((idx / max(len(services_to_try), 1)) * 45)
                _update(download_id, "downloading", prog, f"Trying {current_service.capitalize()}…")

                if current_service == "spotdl":
                    if not SPOTDL_AVAILABLE:
                        raise Exception("SpotDL is not installed")
                    _spotdl_mod.SpotDLDownloader().download_with_metadata(
                        music_url, output_path, track_metadata
                    )
                    download_success = True
                    break

                # Note: Tidal / Qobuz / Amazon direct-API downloaders are
                # present in the beta modules but currently commented out in
                # main.py.  Uncomment the relevant blocks below once they are
                # re-enabled in the beta.

                # elif current_service == "tidal":
                #     from modules import songlink as _sl
                #     sl = _sl.SongLinkClient()
                #     service_url = sl.get_platform_url(track_id, "tidal")
                #     tidal.TidalDownloader().download(service_url, output_path, quality)
                #     download_success = True; break

                # elif current_service == "qobuz":
                #     from modules import songlink as _sl
                #     sl = _sl.SongLinkClient()
                #     isrc = sl.get_isrc(track_id)
                #     if not isrc:
                #         raise Exception("ISRC not found")
                #     dl = qobuz.QobuzDownloader()
                #     dl.download(isrc, output_path, quality)
                #     download_success = True; break

                # elif current_service == "amazon":
                #     from modules import songlink as _sl
                #     sl = _sl.SongLinkClient()
                #     service_url = sl.get_platform_url(track_id, "amazonMusic")
                #     amazon.AmazonDownloader().download(service_url, output_path)
                #     download_success = True; break

                raise Exception(
                    f"'{current_service}' direct API not yet re-enabled in beta — "
                    "try service=spotdl or wait for the stable release"
                )

            except Exception as exc:
                last_error = exc
                print(f"[flac] {current_service} failed: {exc}")
                if not fallback or current_service == services_to_try[-1]:
                    break

        if not download_success:
            raise Exception(f"All services failed. Last error: {last_error}")

        # ── Embed metadata ────────────────────────────────────────────────────
        _update(download_id, "processing", 92, "Embedding metadata…")
        metadata.embed_metadata(output_path, track_metadata)

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


def _direct_download(
    download_id: str,
    url: str,
    platform: str,
    track_id: str,
    output_dir: str,
    template: str,
    quality: str,
) -> None:
    """
    Mirrors main.py::download_direct().
    Used when the URL itself is already on the target platform.
    """
    ext = ".m4a" if platform == "amazon" else ".flac"
    filename = f"{platform}_{track_id}{ext}"
    utils.ensure_directory(output_dir)
    output_path = os.path.join(output_dir, filename)

    if os.path.exists(output_path):
        state.download_status[download_id].update(
            status="complete", progress=100,
            file=filename, output_path=output_path,
            download_url=f"/flac/file/{download_id}/{filename}",
            eta="Already exists on disk",
        )
        state.save_download_status()
        return

    _update(download_id, "downloading", 35, f"Directly downloading from {platform.capitalize()}…")

    if platform == "tidal":
        tidal.TidalDownloader().download(url, output_path, quality)
    elif platform == "qobuz":
        dl = qobuz.QobuzDownloader()
        dl_url = dl.get_download_url(track_id, quality)
        dl.download_file(dl_url, output_path)
    elif platform == "amazon":
        amazon.AmazonDownloader().download(url, output_path)
    else:
        raise Exception(f"Direct download not supported for platform: {platform}")

    state.download_status[download_id].update(
        status="complete", progress=100,
        file=filename, output_path=output_path,
        download_url=f"/flac/file/{download_id}/{filename}",
        eta="Done",
    )
    state.save_download_status()


# ── Routes ─────────────────────────────────────────────────────────────────────

@flac_bp.route("/download", methods=["POST"])
def flac_download():
    """
    POST /flac/download

    JSON body (all fields except `url` are optional):
    {
        "url":      "https://open.spotify.com/track/...",
        "service":  "auto" | "tidal" | "qobuz" | "amazon" | "spotdl",
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

    valid_services = {"auto", "tidal", "qobuz", "amazon", "spotdl"}
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
