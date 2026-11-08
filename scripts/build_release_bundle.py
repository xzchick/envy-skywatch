"""Build a standalone ENVY SkyWatch bundle (no Python needed to run it), a wheel,
an sdist, and SHA256SUMS.txt.

PyInstaller produces a self-contained folder with the app and a bundled Python,
Qt and cryptography. Run it on each OS; PyInstaller does not cross-compile.

    python scripts/build_release_bundle.py
"""

import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
VERSION = "0.1.0"
APP = "envy-skywatch"


def platform_tag():
    if sys.platform == "darwin":
        os_name = "macos"
    elif os.name == "nt":
        os_name = "windows"
    elif sys.platform.startswith("linux"):
        os_name = "linux"
    else:
        os_name = sys.platform
    machine = platform.machine().lower()
    arch = {"amd64": "x86_64", "x64": "x86_64", "x86_64": "x86_64",
            "arm64": "arm64", "aarch64": "arm64"}.get(machine, machine or "unknown")
    return os_name, arch


def run(argv):
    print("+", " ".join(argv), flush=True)
    subprocess.run(argv, check=True)


def build_standalone():
    entry = BUILD / "envy_skywatch_entry.py"
    BUILD.mkdir(parents=True, exist_ok=True)
    entry.write_text("import sys\nfrom envy_skywatch.cli import main\nif __name__ == '__main__':\n    sys.exit(main())\n")
    work = BUILD / "pyi"
    # Name the three Qt modules explicitly: the GUI imports them inside functions,
    # and these flags let PyInstaller's PyQt6 hook bundle exactly the needed Qt
    # (not the QML frameworks that a blanket --collect-all duplicates on macOS).
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
         "--name", APP, "--distpath", str(DIST / "standalone"), "--workpath", str(work),
         "--specpath", str(work), "--paths", str(ROOT),
         "--hidden-import", "PyQt6.QtCore", "--hidden-import", "PyQt6.QtGui",
         "--hidden-import", "PyQt6.QtWidgets", str(entry)])
    built = DIST / "standalone" / APP
    if not (built.exists() and built.is_dir()):
        raise SystemExit(f"PyInstaller did not produce {built}")
    return built


def archive(folder: Path, os_name: str, arch: str) -> Path:
    stem = f"{APP}-v{VERSION}-{os_name}-{arch}"
    if os_name == "windows":
        target = DIST / f"{stem}.zip"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in folder.rglob("*"):
                zf.write(path, Path(stem) / path.relative_to(folder))
    else:
        target = DIST / f"{stem}.tar.gz"
        with tarfile.open(target, "w:gz") as tf:
            tf.add(folder, arcname=stem)
    return target


def build_python_packages():
    try:
        run([sys.executable, "-m", "build", "--outdir", str(DIST)])
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("note: 'build' unavailable; skipping wheel/sdist", flush=True)


def write_checksums():
    lines = []
    for path in sorted(DIST.glob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.name}")
    (DIST / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    os_name, arch = platform_tag()
    folder = build_standalone()
    bundle = archive(folder, os_name, arch)
    print("bundle:", bundle.name)
    build_python_packages()
    write_checksums()


if __name__ == "__main__":
    main()
