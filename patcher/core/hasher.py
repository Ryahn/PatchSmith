"""Streaming SHA256 hashing."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> tuple[str, int]:
    """Return (hex digest, file size in bytes)."""
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size
