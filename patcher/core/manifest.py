"""patch_manifest.json schema load/save."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


ManifestAction = Literal["xdelta", "copy", "delete"]


@dataclass
class ManifestFileEntry:
    path: str
    action: ManifestAction
    old_sha256: str | None = None
    new_sha256: str | None = None
    patch_path: str | None = None
    old_size: int | None = None
    new_size: int | None = None

    def to_json_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"path": self.path, "action": self.action}
        if self.old_sha256 is not None:
            d["old_sha256"] = self.old_sha256
        if self.new_sha256 is not None:
            d["new_sha256"] = self.new_sha256
        if self.patch_path is not None:
            d["patch_path"] = self.patch_path
        if self.old_size is not None:
            d["old_size"] = self.old_size
        if self.new_size is not None:
            d["new_size"] = self.new_size
        return d

    @staticmethod
    def from_json_dict(d: dict[str, Any]) -> ManifestFileEntry:
        return ManifestFileEntry(
            path=str(d["path"]),
            action=d["action"],  # type: ignore[arg-type]
            old_sha256=d.get("old_sha256"),
            new_sha256=d.get("new_sha256"),
            patch_path=d.get("patch_path"),
            old_size=d.get("old_size"),
            new_size=d.get("new_size"),
        )


@dataclass
class PatchManifest:
    manifest_version: int = 1
    patch_name: str = ""
    from_version: str = ""
    to_version: str = ""
    created_by: str = "PatchSmith"
    xdelta_threshold_mb: float = 50.0
    archive_format: str | None = None
    archive_compression_level: int | None = None
    bundle_archive: bool = False
    files: list[ManifestFileEntry] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "manifest_version": self.manifest_version,
            "patch_name": self.patch_name,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "created_by": self.created_by,
            "xdelta_threshold_mb": self.xdelta_threshold_mb,
            "files": [f.to_json_dict() for f in self.files],
        }
        if self.archive_format is not None:
            out["archive_format"] = self.archive_format
        if self.archive_compression_level is not None:
            out["archive_compression_level"] = self.archive_compression_level
        out["bundle_archive"] = self.bundle_archive
        return out

    @staticmethod
    def from_json_dict(d: dict[str, Any]) -> PatchManifest:
        files_raw = d.get("files") or []
        files = [ManifestFileEntry.from_json_dict(x) for x in files_raw]
        return PatchManifest(
            manifest_version=int(d.get("manifest_version", 1)),
            patch_name=str(d.get("patch_name", "")),
            from_version=str(d.get("from_version", "")),
            to_version=str(d.get("to_version", "")),
            created_by=str(d.get("created_by", "PatchSmith")),
            xdelta_threshold_mb=float(d.get("xdelta_threshold_mb", 50)),
            archive_format=d.get("archive_format"),
            archive_compression_level=d.get("archive_compression_level"),
            bundle_archive=bool(d.get("bundle_archive", False)),
            files=files,
        )

    def save(self, path: Path) -> None:
        path.write_text(
            json.dumps(self.to_json_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def load(path: Path) -> PatchManifest:
        data = json.loads(path.read_text(encoding="utf-8"))
        return PatchManifest.from_json_dict(data)
