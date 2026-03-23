#!/usr/bin/env python3
from __future__ import annotations

import shutil
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
    print("Running monorepo pre-push checks...")

    backend_script = ROOT / "backend" / "scripts" / "pre_push_backend.py"
    run_step(
        "Backend checks",
        [PY, str(backend_script)],
        ROOT,
    )

    frontend_dir = ROOT / "spotiflac-frontend"
    if frontend_dir.exists():
        npm = shutil.which("npm")
        if npm is None:
            print("\n❌ npm not found in PATH. Cannot run frontend build.")
            return 1

        run_step(
            "Frontend build",
            [npm, "run", "build"],
            frontend_dir,
        )

    print("\n✅ Monorepo pre-push checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
