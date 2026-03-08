"""
spoflac_core/config.py — thin shim.

All constants live in backend/config.py (single source of truth).
When running under Flask (backend/ is on sys.path), modules that do
`from config import ...` pick up backend/config.py directly and this
file is never loaded.  This shim only kicks in when running scripts
standalone (e.g. `python main.py`) from inside the spoflac_core/ dir.
"""
import os as _os, sys as _sys

_backend_dir = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _backend_dir not in _sys.path:
    _sys.path.insert(0, _backend_dir)

from config import *   # noqa: F401, F403, E402
