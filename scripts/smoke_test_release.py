"""Launch the freshly built standalone binary and check it runs.

Runs the bundled ``envy-skywatch --version`` (no display needed) and confirms the
version prints. This proves the standalone bundle starts on a clean machine.
"""

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
APP = "envy-skywatch"
VERSION = "0.1.0"


def main():
    binary = ROOT / "dist" / "standalone" / APP / (APP + (".exe" if os.name == "nt" else ""))
    if not binary.exists():
        raise SystemExit(f"standalone binary not found: {binary}")
    result = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=120)
    output = (result.stdout + result.stderr).strip()
    print(output)
    if APP not in output or VERSION not in output:
        raise SystemExit(f"unexpected --version output: {output!r}")
    print("standalone smoke test passed")


if __name__ == "__main__":
    main()
