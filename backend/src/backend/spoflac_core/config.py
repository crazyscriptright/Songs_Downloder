"""
spoflac_core/config.py — thin shim.

All constants live in backend/core/config.py (single source of truth).
When running under Flask (backend/ is on sys.path), modules that do
`from core.config import ...` pick up backend/core/config.py directly and this
file is never loaded.  This shim only kicks in when running scripts
standalone (e.g. `python main.py`) from inside the spoflac_core/ dir.
"""
import os as _os
import sys as _sys

# When running standalone scripts, add backend/src/ to sys.path so the
# `backend` package (at ../../) can be found.
_src_dir = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _src_dir not in _sys.path:
    _sys.path.insert(0, _src_dir)

from backend.core.config import *  # noqa: F401, F403, E402
