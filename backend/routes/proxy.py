"""
Proxy Blueprint
Routes: /proxy/download, /proxy/progress, /proxy/file, /api/proxy-image
"""

import os

import requests
from flask import Blueprint, Response, jsonify, request

from core import config
from utils.image import get_responsive_image_url

proxy_bp = Blueprint("proxy", __name__)


@proxy_bp.route("/proxy/download", methods=["GET"])
def proxy_download():
    """Proxy savenow.to download initiation to avoid CORS."""
    if not config.VIDEO_DOWNLOAD_API_KEY:
        return jsonify({"error": "API key not configured on server"}), 500

    params = {
        "copyright": "0",
        "allow_extended_duration": "1",
        "format": request.args.get("format", "mp3"),
        "url": request.args.get("url"),
        "api": config.VIDEO_DOWNLOAD_API_KEY,
        "add_info": "1",
    }
    for opt_key in ("audio_quality", "allow_extended_duration", "no_merge", "audio_language", "start_time", "end_time"):
        val = request.args.get(opt_key)
        if val:
            params[opt_key] = val

    try:
        resp = requests.get("https://p.savenow.to/ajax/download.php", params=params)
        data = resp.json()
        data.pop("message", None)
        return jsonify(data), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@proxy_bp.route("/proxy/progress", methods=["GET"])
def proxy_progress():
    """Proxy savenow.to progress polling to avoid CORS."""
    job_id = request.args.get("progress_id") or request.args.get("id")
    if not job_id:
        return jsonify({"success": False, "error": "No job ID provided"}), 400
    try:
        resp = requests.get(f"https://p.savenow.to/api/progress?id={job_id}", timeout=10)
        data = resp.json()
        data.pop("message", None)
        return jsonify(data), resp.status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@proxy_bp.route("/proxy/file", methods=["GET"])
def proxy_file():
    """Proxy file download to hide source headers from client."""
    download_url = request.args.get("file_url") or request.args.get("url")
    if not download_url:
        return jsonify({"error": "No download URL provided"}), 400
    try:
        resp = requests.get(
            download_url, stream=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=30,
        )
        filename = "download.mp3"
        cd = resp.headers.get("Content-Disposition", "")
        if "filename=" in cd:
            filename = cd.split("filename=")[1].strip('"')

        content_type = resp.headers.get("Content-Type", "application/octet-stream")
        return Response(
            resp.iter_content(chunk_size=8192),
            mimetype=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": resp.headers.get("Content-Length", ""),
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@proxy_bp.route("/api/proxy-image", methods=["GET"])
def proxy_image():
    """Proxy CDN images through the backend with responsive quality selection."""
    image_url = request.args.get("url")
    size = request.args.get("size", "medium")
    if not image_url:
        return jsonify({"error": "URL parameter required"}), 400

    try:
        responsive_url = get_responsive_image_url(image_url, size)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Accept": "image/avif,image/webp,*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",
            "Referer": (
                "https://www.youtube.com/"
                if ("ytimg.com" in responsive_url or "youtube.com" in responsive_url)
                else "https://www.google.com/"
            ),
        }

        proxies = None
        purl = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
        if purl:
            proxies = {"http": purl, "https": purl}

        resp = requests.get(responsive_url, headers=headers, proxies=proxies, timeout=10)

        # YouTube maxresdefault 404 → fall back to hqdefault
        if resp.status_code == 404 and "ytimg.com" in responsive_url and "maxresdefault" in responsive_url:
            fallback = responsive_url.replace("maxresdefault.jpg", "hqdefault.jpg")
            resp = requests.get(fallback, headers=headers, proxies=proxies, timeout=10)

        if resp.status_code == 200:
            return Response(
                resp.content,
                mimetype=resp.headers.get("Content-Type", "image/jpeg"),
                headers={"Cache-Control": "public, max-age=86400", "Access-Control-Allow-Origin": "*"},
            )
        return jsonify({"error": "Failed to fetch image"}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500
