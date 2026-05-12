"""Recursive directory scan with optional ignore rules."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path, PurePosixPath


DEFAULT_IGNORE_NAMES = frozenset(
    {
        ".git",
        ".svn",
        ".hg",
        "__MACOSX",
        "Thumbs.db",
        ".DS_Store",
    }
)


def posix_relpath(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    return PurePosixPath(rel.as_posix()).as_posix()


def iter_files(
    root: Path,
    *,
    extra_ignore_names: Iterable[str] | None = None,
    extra_ignore_path_prefixes: Iterable[str] | None = None,
) -> list[str]:
    """
    Return sorted list of file paths relative to root, using forward slashes.
    Directories only; symlinks to files are followed; broken symlinks skipped.
    """
    root = root.resolve()
    ignore_names = set(DEFAULT_IGNORE_NAMES)
    if extra_ignore_names:
        ignore_names.update(extra_ignore_names)
    prefixes: tuple[str, ...] = tuple(
        p.strip("/").replace("\\", "/")
        for p in (extra_ignore_path_prefixes or ())
        if p.strip()
    )

    out: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dpath = Path(dirpath)

        dirnames[:] = [d for d in dirnames if d not in ignore_names]

        for name in filenames:
            if name in ignore_names:
                continue
            fp = dpath / name
            if not fp.is_file():
                continue
            rel = posix_relpath(root, fp)
            if prefixes and any(
                rel == p or rel.startswith(p + "/") for p in prefixes
            ):
                continue
            out.append(rel)

    out.sort()
    return out
