"""
Shared mutable application state.

All route handlers and service functions that need to read or mutate
download_status / search_results / etc. should import from here rather
than keeping module-level dicts scattered across api.py.
"""

import json
import os
import shutil
from datetime import datetime
from typing import Any

import config

# ── In-memory stores ───────────────────────────────────────────────────────────
download_status: dict[str, Any] = {}
search_results: dict[str, Any] = {}
active_processes: dict[str, Any] = {}
bulk_heartbeats: dict[str, Any] = {}

# Preview stream URL cache: url -> (stream_url, expires_at_unix)
preview_cache: dict[str, tuple[str, float]] = {}


# ── Persistence helpers ────────────────────────────────────────────────────────

def save_download_status() -> None:
    """Persist download_status to disk (no-op on read-only filesystems)."""
    try:
        with open(config.DOWNLOAD_STATUS_FILE, "w") as f:
            json.dump(download_status, f, indent=2)
    except (IOError, OSError, PermissionError) as exc:
        print(f"Warning: Could not save download status: {exc}")


def load_persistent_data() -> None:
    """Load download_status from disk on startup."""
    global download_status
    try:
        if os.path.exists(config.DOWNLOAD_STATUS_FILE):
            with open(config.DOWNLOAD_STATUS_FILE, "r") as f:
                download_status = json.load(f)
            print(f" Loaded {len(download_status)} download records")
    except (IOError, OSError, json.JSONDecodeError) as exc:
        print(f" Could not load download status: {exc}")
        download_status = {}


def cleanup_old_downloads() -> None:
    """Remove completed/errored downloads older than 24 hours."""
    try:
        current_time = datetime.now()
        to_remove = [
            did
            for did, st in download_status.items()
            if st.get("status") in ("complete", "error", "cancelled")
            and "timestamp" in st
            and (
                current_time - datetime.fromisoformat(st["timestamp"])
            ).total_seconds()
            > 86400
        ]
        for did in to_remove:
            del download_status[did]
        if to_remove:
            save_download_status()
    except Exception as exc:
        print(f"Warning: Could not cleanup old downloads: {exc}")


def cleanup_tmp_directory() -> None:
    """
    Evict old non-JSON files from /tmp when usage exceeds 80 %.
    Runs only on Heroku (IS_HEROKU=True).
    """
    if not config.IS_HEROKU:
        return
    try:
        tmp_dir = "/tmp"
        total, used, _ = shutil.disk_usage(tmp_dir)
        usage_pct = (used / total) * 100

        if usage_pct <= 80:
            return

        print(f" /tmp is {usage_pct:.1f}% full, cleaning up…")
        candidates: list[str] = []
        for root, _dirs, files in os.walk(tmp_dir):
            for name in files:
                path = os.path.join(root, name)
                if not name.endswith(".json"):
                    candidates.append(path)

        candidates.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0)

        deleted = 0
        for path in candidates:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    deleted += 1
            except Exception:
                pass

        total, used, _ = shutil.disk_usage(tmp_dir)
        new_pct = (used / total) * 100
        print(f" Cleaned {deleted} files from /tmp — now {new_pct:.1f}% full")
    except Exception as exc:
        print(f" Error cleaning /tmp: {exc}")
