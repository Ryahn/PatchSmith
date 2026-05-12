"""Classify files as unchanged / changed / new / deleted from hash maps."""

from __future__ import annotations

from dataclasses import dataclass

FileInfo = tuple[str, int]  # sha256 hex, size


@dataclass(frozen=True)
class DiffResult:
    unchanged: frozenset[str]
    changed: frozenset[str]
    new: frozenset[str]
    deleted: frozenset[str]


def diff_trees(
    old_map: dict[str, FileInfo],
    new_map: dict[str, FileInfo],
) -> DiffResult:
    old_keys = frozenset(old_map)
    new_keys = frozenset(new_map)
    common = old_keys & new_keys
    unchanged: set[str] = set()
    changed: set[str] = set()
    for rel in common:
        if old_map[rel][0] == new_map[rel][0]:
            unchanged.add(rel)
        else:
            changed.add(rel)
    new_files = new_keys - old_keys
    deleted_files = old_keys - new_keys
    return DiffResult(
        unchanged=frozenset(unchanged),
        changed=frozenset(changed),
        new=frozenset(new_files),
        deleted=frozenset(deleted_files),
    )
