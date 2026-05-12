"""Resolve repository root and bundled `bin/` for dev and PyInstaller."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PORTABLE_APPLY_EXE_NAME = "ApplyPatch.exe"
PORTABLE_APPLY_LINUX_NAME = "ApplyPatch"


def portable_apply_bundle_name() -> str:
    """Filename of the frozen portable apply binary for this OS (at patch root)."""
    if sys.platform == "win32":
        return PORTABLE_APPLY_EXE_NAME
    return PORTABLE_APPLY_LINUX_NAME


def _meipass_dir() -> Path | None:
    if getattr(sys, "frozen", False):
        mp = getattr(sys, "_MEIPASS", None)
        if mp:
            return Path(mp)
    return None


def repo_root() -> Path:
    """PatchSmith repo root (parent of `patcher/`)."""
    here = Path(__file__).resolve()
    # patcher/core/paths.py -> parents[2] == repo root
    return here.parents[2]


def bin_dir() -> Path:
    me = _meipass_dir()
    if me is not None:
        cand = me / "bin"
        if cand.is_dir():
            return cand
    return repo_root() / "bin"


def patch_tools_dir(patch_root: Path) -> Path:
    return patch_root / "tools"


def portable_apply_patch_root() -> Path:
    """
    Directory containing patch_manifest.json for the frozen ApplyPatch.exe
    (exe parent), or PATCHSMITH_PATCH_ROOT / cwd when running from source.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    env = os.environ.get("PATCHSMITH_PATCH_ROOT")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()
