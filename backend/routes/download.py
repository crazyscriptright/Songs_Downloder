"""
Download Blueprint
Routes: /download, /download_status/<id>, /downloads, /bulk_download,
        /bulk_status/<id>, /bulk_heartbeat/<id>, /cancel_download/<id>,
        /clear_downloads, /get_file/<id>/<filename>
"""

import os
import re
import threading
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, send_file

import config
import state
from services.downloader import download_song

download_bp = Blueprint("download", __name__)


@download_bp.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get("url")
    title = data.get("title")
    advanced_options = data.get("advancedOptions")

    print(f"\n{'='*70}")
    print(f"📥 Download request received")
    print(f"   URL: {url}")
    print(f"   Title: {title}")
    print(f"   Advanced Options: {advanced_options}")
    print(f"{'='*70}\n")

    if not url or not title:
        return jsonify({"error": "Missing url or title"}), 400
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return jsonify({"error": "Invalid URL format. Only HTTP/HTTPS URLs are allowed."}), 400
    if not isinstance(title, str):
        return jsonify({"error": "Invalid title type"}), 400
    if ".." in title:
        return jsonify({"error": "Invalid title: path traversal detected"}), 400
    if len(title) > 500:
        title = title[:500]
    if len(url) > 2048:
        return jsonify({"error": "URL too long"}), 400

    if advanced_options and isinstance(advanced_options, dict):
        custom_args = advanced_options.get("customArgs", "")
        if custom_args:
            DANGEROUS = ["&&", "||", ";", "|", "`", "$", "\n", "\r"]
            for d in DANGEROUS:
                if d in custom_args:
                    return jsonify({"error": "Security: Dangerous character in custom arguments"}), 400

    download_id = f"download_{datetime.now().timestamp()}"
    state.download_status[download_id] = {
        "status": "queued", "progress": 0,
        "title": title, "url": url,
        "eta": "Initializing…", "speed": "0 KB/s",
        "timestamp": datetime.now().isoformat(),
        "advanced_options": advanced_options,
    }
    state.save_download_status()
    threading.Thread(target=download_song, args=(url, title, download_id, advanced_options)).start()
    return jsonify({"download_id": download_id, "status": "started"})


@download_bp.route("/download_status/<download_id>")
def download_status_check(download_id):
    if download_id not in state.download_status:
        return jsonify({"status": "not_found"}), 404

    status = state.download_status[download_id].copy()
    if status["status"] == "complete" and "file" in status:
        if "download_url" not in status:
            status["download_url"] = f"/get_file/{download_id}/{status['file']}"
        elif status.get("downloaded_via") == "proxy_api":
            if status.get("alternative_download_urls"):
                pass  # already has external URL
    return jsonify(status)


@download_bp.route("/downloads")
def get_all_downloads():
    filtered = {}
    current_time = datetime.now()
    for did, status in state.download_status.items():
        if status.get("status") in ("downloading", "queued", "preparing"):
            filtered[did] = status
        elif status.get("status") in ("complete", "error", "cancelled"):
            if "timestamp" in status:
                try:
                    dt = datetime.fromisoformat(status["timestamp"])
                    if (current_time - dt).total_seconds() < 86400:
                        filtered[did] = status
                except Exception:
                    filtered[did] = status
            else:
                filtered[did] = status

    for did, status in filtered.items():
        if status["status"] == "complete" and "file" in status and "download_url" not in status:
            status["download_url"] = f"/get_file/{did}/{status['file']}"

    return jsonify(filtered)


@download_bp.route("/bulk_download", methods=["POST"])
def bulk_download():
    data = request.get_json()
    urls = data.get("urls", [])
    advanced_options = data.get("advancedOptions")

    if not urls or not isinstance(urls, list):
        return jsonify({"error": "URLs list is required"}), 400

    valid_urls = [u.strip() for u in urls if isinstance(u, str) and u.startswith(("http://", "https://"))]
    if not valid_urls:
        return jsonify({"error": "No valid URLs provided"}), 400

    bulk_id = f"bulk_{datetime.now().timestamp()}"
    bulk_downloads = []

    for i, url in enumerate(valid_urls):
        did = f"{bulk_id}_item_{i}"
        bulk_downloads.append({"url": url, "title": f"Item {i+1}", "status": "queued", "progress": 0, "download_id": did, "error": None, "speed": "Queued", "eta": "N/A"})
        state.download_status[did] = {
            "status": "queued", "progress": 0,
            "title": f"Item {i+1}", "url": url,
            "speed": "Queued", "eta": "N/A",
            "timestamp": datetime.now().isoformat(),
            "bulk_id": bulk_id,
            "advanced_options": advanced_options,
        }

    state.download_status[bulk_id] = {
        "type": "bulk", "status": "processing",
        "downloads": bulk_downloads, "total": len(valid_urls),
        "completed": 0, "failed": 0,
        "timestamp": datetime.now().isoformat(),
    }
    state.bulk_heartbeats[bulk_id] = {"last_heartbeat": datetime.now(), "timeout_seconds": 30}
    state.save_download_status()

    def process_bulk():
        for i, info in enumerate(bulk_downloads):
            # Heartbeat check
            if bulk_id in state.bulk_heartbeats:
                hb = state.bulk_heartbeats[bulk_id]
                if (datetime.now() - hb["last_heartbeat"]).total_seconds() > hb["timeout_seconds"]:
                    print(f"⏱️ Heartbeat timeout for {bulk_id}")
                    state.download_status[bulk_id]["status"] = "timeout"
                    state.download_status[bulk_id]["error"] = "Client disconnected"
                    state.save_download_status()
                    state.bulk_heartbeats.pop(bulk_id, None)
                    return

            did = info["download_id"]
            state.download_status[did]["status"] = "downloading"
            state.download_status[bulk_id]["downloads"][i]["status"] = "downloading"
            state.save_download_status()

            download_song(info["url"], info["title"], did, advanced_options)

            s = state.download_status[did]
            if s["status"] == "complete":
                state.download_status[bulk_id]["completed"] += 1
            elif s["status"] == "error":
                state.download_status[bulk_id]["failed"] += 1

            state.download_status[bulk_id]["downloads"][i] = {
                "url": info["url"],
                "title": s.get("title", info["title"]),
                "status": s["status"],
                "progress": s["progress"],
                "download_id": did,
                "error": s.get("error"),
                "speed": s.get("speed", "N/A"),
                "eta": s.get("eta", "N/A"),
                "download_url": s.get("download_url"),
            }
            state.save_download_status()

        state.download_status[bulk_id]["status"] = "complete"
        state.save_download_status()
        state.bulk_heartbeats.pop(bulk_id, None)
        print(f"✅ Bulk complete: {state.download_status[bulk_id]['completed']}/{len(valid_urls)}")

    threading.Thread(target=process_bulk).start()
    return jsonify({"bulk_id": bulk_id, "status": "started", "total": len(valid_urls)})


@download_bp.route("/bulk_status/<bulk_id>")
def bulk_status_check(bulk_id):
    if bulk_id not in state.download_status:
        return jsonify({"error": "Bulk download not found"}), 404

    bulk_data = state.download_status[bulk_id].copy()
    if "downloads" in bulk_data:
        for i, dl in enumerate(bulk_data["downloads"]):
            did = dl.get("download_id")
            if did and did in state.download_status:
                ind = state.download_status[did]
                if ind.get("status") == "complete" and "file" in ind:
                    if "download_url" in ind:
                        bulk_data["downloads"][i]["download_url"] = ind["download_url"]
                    else:
                        bulk_data["downloads"][i]["download_url"] = f"/get_file/{did}/{ind['file']}"
                    bulk_data["downloads"][i]["file"] = ind["file"]
                    if not bulk_data["downloads"][i].get("title") or bulk_data["downloads"][i]["title"].startswith("Item "):
                        bulk_data["downloads"][i]["title"] = ind.get("title", bulk_data["downloads"][i]["title"])
    return jsonify(bulk_data)


@download_bp.route("/bulk_heartbeat/<bulk_id>", methods=["POST"])
def bulk_heartbeat(bulk_id):
    if bulk_id in state.bulk_heartbeats:
        state.bulk_heartbeats[bulk_id]["last_heartbeat"] = datetime.now()
        return jsonify({"status": "ok", "message": "Heartbeat received"})
    elif bulk_id in state.download_status:
        bstatus = state.download_status[bulk_id].get("status", "unknown")
        return jsonify({"status": "ended", "bulk_status": bstatus, "message": f"Bulk download already {bstatus}"})
    return jsonify({"status": "not_found", "message": "Bulk download not found"}), 404


@download_bp.route("/cancel_download/<download_id>", methods=["POST"])
def cancel_download(download_id):
    if download_id not in state.download_status:
        return jsonify({"error": "Download not found"}), 404

    current = state.download_status[download_id]["status"]
    if current in ("complete", "error", "cancelled"):
        return jsonify({"error": "Download already finished"}), 400

    state.download_status[download_id].update(
        status="cancelled", cancelled_at=datetime.now().isoformat(),
        progress=0, speed="Cancelled", eta="N/A",
    )

    if download_id in state.active_processes:
        try:
            state.active_processes[download_id].terminate()
        except Exception as e:
            print(f"Warning: Could not terminate process: {e}")

    state.save_download_status()
    return jsonify({"status": "cancelled", "message": f"Download cancelled: {state.download_status[download_id]['title']}"})


@download_bp.route("/clear_downloads", methods=["POST"])
def clear_downloads():
    to_remove = [did for did, s in state.download_status.items() if s.get("status") in ("complete", "error", "cancelled")]
    for did in to_remove:
        del state.download_status[did]
    state.save_download_status()
    return jsonify({"message": f"Cleared {len(to_remove)} finished downloads", "cleared_count": len(to_remove)})


@download_bp.route("/get_file/<download_id>/<filename>")
def get_file(download_id, filename):
    try:
        if not re.match(r"^[a-zA-Z0-9_.\-]+$", download_id):
            return jsonify({"error": "Invalid download ID"}), 400
        file_path = os.path.join(config.DOWNLOAD_FOLDER, download_id, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
