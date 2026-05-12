"""Heuristic engine detection for presets (optional UI)."""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class Engine(str, Enum):
    GENERIC = "Generic"
    UNITY = "Unity"
    RPG_MAKER_MV_MZ = "RPG Maker MV/MZ"
    RENPY = "Ren'Py"
    UNREAL = "Unreal"


def detect_engine(folder: Path) -> Engine:
    root = folder.resolve()

    if any(root.glob("*_Data")) and (
        (root / "UnityPlayer.dll").is_file() or (root / "UnityPlayer.so").is_file()
    ):
        return Engine.UNITY
    if (root / "www" / "data").is_dir() and (root / "www" / "js").is_dir():
        return Engine.RPG_MAKER_MV_MZ
    if (root / "renpy").is_dir() and (root / "game").is_dir():
        return Engine.RENPY
    if (root / "Engine").is_dir():
        for child in root.iterdir():
            if child.is_dir() and (child / "Content" / "Paks").is_dir():
                return Engine.UNREAL
    return Engine.GENERIC


def ignore_overrides_for_engine(engine: Engine) -> tuple[list[str], list[str]]:
    """Return (extra_ignore_names, extra_ignore_path_prefixes)."""
    if engine is Engine.UNITY:
        return [], []
    if engine is Engine.RPG_MAKER_MV_MZ:
        return [], []
    if engine is Engine.RENPY:
        return [], []
    if engine is Engine.UNREAL:
        return [], []
    return [], []
