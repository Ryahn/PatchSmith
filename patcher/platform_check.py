"""Surface missing external tools (especially macOS + Homebrew)."""

from __future__ import annotations

import sys

from patcher.core.archiver import SevenZipNotFoundError, resolve_7za
from patcher.core.xdelta import XdeltaNotFoundError, resolve_xdelta3


def tool_warning_messages() -> list[str]:
    msgs: list[str] = []
    try:
        resolve_xdelta3(patch_root=None)
    except XdeltaNotFoundError:
        if sys.platform == "darwin":
            msgs.append(
                "xdelta3 was not found. Install with:\n  brew install xdelta\n"
                "Or set the environment variable PATCHSMITH_XDELTA3 to the full path of the xdelta3 binary."
            )
        else:
            msgs.append(
                "xdelta3 was not found. Add it to PATH or set PATCHSMITH_XDELTA3.\n"
                "On Windows, place xdelta-3.1.0-x86_64.exe in the repo bin/ folder."
            )
    try:
        resolve_7za(patch_root=None)
    except SevenZipNotFoundError:
        if sys.platform == "darwin":
            msgs.append(
                "7za was not found. Install with:\n  brew install p7zip\n"
                "Or set PATCHSMITH_7ZA to the full path of the 7za binary."
            )
        else:
            msgs.append(
                "7za was not found. Set PATCHSMITH_7ZA or add 7za.exe to the repo bin/ folder (Windows)."
            )
    return msgs
