"""Create and extract archives using 7za CLI."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from patcher.core.paths import bin_dir, patch_tools_dir


class SevenZipNotFoundError(FileNotFoundError):
    pass


def _is_windows() -> bool:
    return sys.platform == "win32"


def _homebrew_7za_candidates() -> list[Path]:
    return [
        Path("/opt/homebrew/bin/7za"),
        Path("/usr/local/bin/7za"),
    ]


def resolve_7za(*, patch_root: Path | None = None) -> Path:
    env = os.environ.get("PATCHSMITH_7ZA")
    if env:
        p = Path(env)
        if p.is_file():
            return p.resolve()

    if _is_windows():
        exe = bin_dir() / "7za.exe"
        if exe.is_file():
            return exe.resolve()

    if sys.platform.startswith("linux"):
        for name in ("7za-linux", "7za"):
            p = bin_dir() / name
            if p.is_file():
                return p.resolve()

    if patch_root is not None:
        tools = patch_tools_dir(patch_root)
        for name in ("7za.exe", "7za"):
            cand = tools / name
            if cand.is_file():
                return cand.resolve()

    for cand in _homebrew_7za_candidates():
        if cand.is_file():
            return cand.resolve()

    w = shutil.which("7za")
    if w:
        return Path(w).resolve()

    msg = (
        "7za not found. Set PATCHSMITH_7ZA or install p7zip / 7-Zip "
        "(Windows: ship bin/7za.exe; macOS: e.g. brew install p7zip)."
    )
    raise SevenZipNotFoundError(msg)


def create_archive(
    sevenza: Path,
    patch_root: Path,
    archive_path: Path,
    *,
    archive_format: str,
    compression_level: int,
) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        archive_path.unlink()
    fmt = archive_format.lower()
    if fmt not in ("7z", "zip"):
        raise ValueError(f"Unsupported archive format: {archive_format}")
    cmd = [
        str(sevenza),
        "a",
        f"-t{fmt}",
        f"-mx={int(compression_level)}",
        "-y",
        str(archive_path.resolve()),
        "*",
    ]
    try:
        subprocess.run(
            cmd,
            cwd=str(patch_root.resolve()),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or str(e)).strip()
        raise RuntimeError(f"7za create failed: {err}") from e


def extract_archive(sevenza: Path, archive_path: Path) -> Path:
    """Extract to a new temp directory; return that directory path."""
    out = Path(tempfile.mkdtemp(prefix="patchsmith_extract_"))
    cmd = [
        str(sevenza),
        "x",
        "-y",
        f"-o{str(out)}",
        str(archive_path.resolve()),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or str(e)).strip()
        raise RuntimeError(f"7za extract failed: {err}") from e
    return out
