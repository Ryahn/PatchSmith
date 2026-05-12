"""Invoke xdelta3 CLI (encode/decode)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from patcher.core.paths import bin_dir, patch_tools_dir


class XdeltaNotFoundError(FileNotFoundError):
    pass


def _is_windows() -> bool:
    return sys.platform == "win32"


def _is_darwin() -> bool:
    return sys.platform == "darwin"


def _is_linux() -> bool:
    return sys.platform.startswith("linux")


def _homebrew_xdelta_candidates() -> list[Path]:
    return [
        Path("/opt/homebrew/bin/xdelta3"),
        Path("/usr/local/bin/xdelta3"),
    ]


def resolve_xdelta3(*, patch_root: Path | None = None) -> Path:
    env = os.environ.get("PATCHSMITH_XDELTA3")
    if env:
        p = Path(env)
        if p.is_file():
            return p.resolve()

    if _is_windows():
        exe = bin_dir() / "xdelta-3.1.0-x86_64.exe"
        if exe.is_file():
            return exe.resolve()

    if _is_linux():
        p = bin_dir() / "xdelta3-linux"
        if p.is_file():
            return p.resolve()

    if patch_root is not None:
        tools = patch_tools_dir(patch_root)
        for name in ("xdelta3.exe", "xdelta3", "xdelta-3.1.0-x86_64.exe"):
            cand = tools / name
            if cand.is_file():
                return cand.resolve()

    if _is_darwin():
        for cand in _homebrew_xdelta_candidates():
            if cand.is_file():
                return cand.resolve()

    w = shutil.which("xdelta3")
    if w:
        return Path(w).resolve()

    msg = "xdelta3 not found. Set PATCHSMITH_XDELTA3 or install xdelta3 (e.g. on macOS: brew install xdelta)."
    raise XdeltaNotFoundError(msg)


def encode(
    xdelta_exe: Path,
    old_file: Path,
    new_file: Path,
    patch_out: Path,
) -> None:
    patch_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(xdelta_exe),
        "-e",
        "-9",
        "-S",
        "djw",
        "-s",
        str(old_file),
        str(new_file),
        str(patch_out),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or str(e)).strip()
        raise RuntimeError(f"xdelta3 encode failed: {err}") from e


def decode(
    xdelta_exe: Path,
    old_file: Path,
    patch_file: Path,
    new_out: Path,
) -> None:
    new_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(xdelta_exe),
        "-d",
        "-s",
        str(old_file),
        str(patch_file),
        str(new_out),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or str(e)).strip()
        raise RuntimeError(f"xdelta3 decode failed: {err}") from e
