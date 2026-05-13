"""Invoke xdelta3 CLI (encode/decode)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

from patcher.core.paths import bin_dir, patch_tools_dir

OnXdeltaSubprocessFn = Callable[[subprocess.Popen | None], None]


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
    *,
    compression_level: int = 6,
    progress_log: Callable[[str], None] | None = None,
    progress_label: str | None = None,
    on_subprocess: OnXdeltaSubprocessFn | None = None,
) -> None:
    patch_out.parent.mkdir(parents=True, exist_ok=True)
    lev = max(1, min(9, int(compression_level)))
    cmd = [
        str(xdelta_exe),
        "-e",
        f"-{lev}",
        "-S",
        "djw",
        "-s",
        str(old_file),
        str(new_file),
        str(patch_out),
    ]
    done = threading.Event()
    start_mono = time.monotonic()

    def _heartbeat() -> None:
        while not done.wait(20.0):
            if patch_out.is_file():
                try:
                    patch_part = patch_out.stat().st_size
                except OSError:
                    patch_part = -1
            else:
                patch_part = 0
            elapsed = round(time.monotonic() - start_mono, 1)
            if progress_log is not None:
                label = progress_label or patch_out.name
                mib = patch_part / (1024 * 1024) if patch_part >= 0 else 0.0
                try:
                    progress_log(
                        f"  xdelta encoding {label}… {elapsed:.0f}s elapsed, "
                        f"~{mib:.0f} MiB patch on disk so far"
                    )
                except Exception:
                    pass

    proc: subprocess.Popen | None = None
    out, err = "", ""
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if on_subprocess is not None:
            on_subprocess(proc)
        hb = threading.Thread(target=_heartbeat, daemon=True)
        hb.start()
        try:
            out, err = proc.communicate()
        finally:
            done.set()
    finally:
        if on_subprocess is not None:
            on_subprocess(None)
    if proc is None:
        raise RuntimeError("xdelta3 encode failed to start subprocess")
    if proc.returncode != 0:
        msg = ((err or "") + (out or "")).strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"xdelta3 encode failed: {msg}")


def decode(
    xdelta_exe: Path,
    old_file: Path,
    patch_file: Path,
    new_out: Path,
    *,
    on_subprocess: OnXdeltaSubprocessFn | None = None,
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
    proc: subprocess.Popen | None = None
    out, err = "", ""
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if on_subprocess is not None:
            on_subprocess(proc)
        out, err = proc.communicate()
    finally:
        if on_subprocess is not None:
            on_subprocess(None)
    if proc is None:
        raise RuntimeError("xdelta3 decode failed to start subprocess")
    if proc.returncode != 0:
        msg = ((err or "") + (out or "")).strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"xdelta3 decode failed: {msg}")
