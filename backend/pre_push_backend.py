#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PY = sys.executable


def run_step(label: str, cmd: list[str], cwd: Path) -> None:
    print(f"\n==> {label}")
    print("$", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    print("Running backend pre-push checks...")

    compile_targets = [
        "app.py",
        "api_metadata_enricher.py",
        "tools/enrich_metadata.py",
        "tools/picard_fallback_enricher.py",
        "config.py",
        "state.py",
        "routes",
        "services",
        "integrations",
        "spoflac_core",
        "utils",
    ]

    run_step(
        "Python syntax/bytecode compile",
        [PY, "-m", "compileall", "-q", *compile_targets],
        ROOT,
    )

    run_step(
        "Critical file syntax check",
        [
            PY,
            "-m",
            "py_compile",
            "app.py",
            "services/downloader.py",
            "routes/flac_download.py",
            "tools/enrich_metadata.py",
            "tools/picard_fallback_enricher.py",
        ],
        ROOT,
    )

    print("\n✅ Backend pre-push checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
