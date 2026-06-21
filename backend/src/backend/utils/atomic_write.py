"""
Atomic JSON file I/O helpers with advisory locking.

Prevents race conditions when multiple processes / threads write to the
same JSON cache file concurrently (e.g. multiple Flask worker processes).

Usage
-----
Simple overwrite::

    from utils.atomic_write import atomic_json_write
    atomic_json_write("cache.json", {"key": "value"})

Safe read-modify-write (preserves other keys in a shared cache file)::

    from utils.atomic_write import atomic_json_read_modify_write

    def _updater(data: dict) -> dict:
        data["my_section"] = {"token": "xyz", "ts": "2026-01-01T00:00:00"}
        return data

    atomic_json_read_modify_write("cache.json", _updater)
"""

import json
import os
import tempfile
import time
from typing import Any, Callable

_LOCK_TIMEOUT      = 5.0
_LOCK_POLL         = 0.05

def _lock_path(filepath: str) -> str:
    return filepath + ".lock"

def _acquire_lock(lock_path: str, timeout: float = _LOCK_TIMEOUT) -> bool:
    """
    Create an exclusive advisory lock file.
    Returns True if the lock was acquired, False on timeout.
    Uses O_EXCL so the create+check is atomic on all supported platforms.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            try:
                os.write(fd, str(os.getpid()).encode())
            finally:
                os.close(fd)
            return True
        except FileExistsError:
            if time.monotonic() >= deadline:
                return False
            time.sleep(_LOCK_POLL)

def _release_lock(lock_path: str) -> None:
    try:
        os.remove(lock_path)
    except FileNotFoundError:
        pass

def atomic_json_write(
    filepath: str,
    data: Any,
    indent: int = 2,
    **json_kwargs: Any,
) -> None:
    """
    Write *data* to *filepath* as JSON atomically.

    Strategy:
    1. Acquire advisory lock (.lock sidecar file).
    2. Write to a sibling temp file.
    3. fsync the temp file.
    4. ``os.replace`` temp → filepath  (atomic on all POSIX and Win32).
    5. Release lock.

    Falls back to a best-effort write without locking if the lock cannot
    be acquired within *_LOCK_TIMEOUT* seconds.
    """
    lock_path = _lock_path(filepath)
    locked = _acquire_lock(lock_path)
    _write_temp_replace(filepath, data, indent, **json_kwargs)
    if locked:
        _release_lock(lock_path)

def atomic_json_read_modify_write(
    filepath: str,
    updater: Callable[[dict], dict],
    indent: int = 2,
    **json_kwargs: Any,
) -> dict:
    """
    Thread/process-safe read-modify-write for a shared JSON file.

    1. Acquire advisory lock.
    2. Read the current contents (empty dict if missing/corrupt).
    3. Call ``updater(data)`` → new_data.
    4. Atomically write new_data back.
    5. Release lock.

    Returns the new data dict.
    """
    lock_path = _lock_path(filepath)

    if not _acquire_lock(lock_path):

        data = _safe_read(filepath)
        new_data = updater(data)
        _write_temp_replace(filepath, new_data, indent, **json_kwargs)
        return new_data

    try:
        data = _safe_read(filepath)
        new_data = updater(data)
        _write_temp_replace(filepath, new_data, indent, **json_kwargs)
        return new_data
    finally:
        _release_lock(lock_path)

def _safe_read(filepath: str) -> dict:
    """Return parsed JSON from *filepath*, or {} on any error."""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_temp_replace(
    filepath: str,
    data: Any,
    indent: int = 2,
    **json_kwargs: Any,
) -> None:
    """Write data to a temp file then atomically replace *filepath*."""
    dir_ = os.path.dirname(os.path.abspath(filepath))
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            mode="w",
            encoding="utf-8",
            dir=dir_,
            suffix=".tmp",
        ) as tmp:
            tmp_path = tmp.name
            json.dump(data, tmp, indent=indent, **json_kwargs)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_path, filepath)
        tmp_path = None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
