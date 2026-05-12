"""Apply a patch folder or archive to a game root with hash verification."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from patcher.core import archiver, hasher, xdelta
from patcher.core.manifest import ManifestFileEntry, PatchManifest


LogFn = Callable[[str], None]


def _noop_log(_: str) -> None:
    return None


def _game_path(root: Path, rel_posix: str) -> Path:
    return root.joinpath(*rel_posix.split("/"))


def _is_archive(path: Path) -> bool:
    return path.suffix.lower() in (".7z", ".zip")


@dataclass
class ApplyPatchOptions:
    game_root: Path
    patch_path: Path
    backup: bool = True
    backup_dir: Path | None = None


def apply_patch(opts: ApplyPatchOptions, log: LogFn | None = None) -> None:
    log = log or _noop_log
    game_root = opts.game_root.resolve()
    patch_path = opts.patch_path.resolve()

    temp_extract: Path | None = None
    try:
        if patch_path.is_dir():
            patch_root = patch_path
        elif patch_path.is_file() and _is_archive(patch_path):
            sevenza = archiver.resolve_7za(patch_root=None)
            log(f"Extracting archive {patch_path.name}…")
            temp_extract = archiver.extract_archive(sevenza, patch_path)
            patch_root = temp_extract
        else:
            raise FileNotFoundError(f"Patch not found or unsupported: {patch_path}")

        manifest_path = patch_root / "patch_manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Missing patch_manifest.json under {patch_root}")

        manifest = PatchManifest.load(manifest_path)
        log(f"Loaded manifest: {manifest.patch_name!r} ({manifest.from_version} → {manifest.to_version})")

        xdelta_exe = xdelta.resolve_xdelta3(patch_root=patch_root)

        log("Verifying pre-state (old hashes)…")
        for entry in manifest.files:
            if entry.action == "delete":
                if not entry.old_sha256:
                    raise ValueError(f"delete entry missing old_sha256: {entry.path}")
                gp = _game_path(game_root, entry.path)
                if not gp.is_file():
                    raise RuntimeError(
                        f"Expected file missing for delete verification: {entry.path}"
                    )
                h, _ = hasher.sha256_file(gp)
                if h != entry.old_sha256:
                    raise RuntimeError(
                        f"Pre-hash mismatch for {entry.path}: game has {h[:12]}…, "
                        f"manifest expects {entry.old_sha256[:12]}…"
                    )
            elif entry.action == "xdelta":
                if not entry.old_sha256 or not entry.new_sha256:
                    raise ValueError(f"xdelta entry missing hashes: {entry.path}")
                gp = _game_path(game_root, entry.path)
                if not gp.is_file():
                    raise RuntimeError(f"Missing old file for xdelta: {entry.path}")
                h, _ = hasher.sha256_file(gp)
                if h != entry.old_sha256:
                    raise RuntimeError(
                        f"Pre-hash mismatch for {entry.path}: expected old_sha256 from manifest."
                    )
            elif entry.action == "copy":
                if entry.old_sha256 is not None:
                    gp = _game_path(game_root, entry.path)
                    if not gp.is_file():
                        raise RuntimeError(
                            f"Missing old file for copy replace: {entry.path}"
                        )
                    h, _ = hasher.sha256_file(gp)
                    if h != entry.old_sha256:
                        raise RuntimeError(
                            f"Pre-hash mismatch for changed file {entry.path}."
                        )
                else:
                    if entry.new_sha256 is None or entry.patch_path is None:
                        raise ValueError(f"Invalid new-file copy entry: {entry.path}")

        backup_root: Path | None = None
        if opts.backup:
            base = opts.backup_dir.resolve() if opts.backup_dir else game_root.parent
            base.mkdir(parents=True, exist_ok=True)
            import datetime as _dt

            stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_root = base / f"PatchSmith_backup_{stamp}"
            backup_root.mkdir(parents=True, exist_ok=False)
            log(f"Backing up into {backup_root}")

            for entry in manifest.files:
                if entry.action == "delete" or entry.action in ("xdelta", "copy"):
                    gp = _game_path(game_root, entry.path)
                    if gp.is_file():
                        dst = backup_root / Path(*entry.path.split("/"))
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(gp, dst)

        non_delete = [e for e in manifest.files if e.action in ("xdelta", "copy")]
        delete_entries = [e for e in manifest.files if e.action == "delete"]

        for entry in non_delete:
            if entry.action == "xdelta":
                assert entry.patch_path and entry.old_sha256 and entry.new_sha256
                old_file = _game_path(game_root, entry.path)
                patch_file = patch_root.joinpath(*entry.patch_path.split("/"))
                if not patch_file.is_file():
                    raise FileNotFoundError(f"Missing patch payload: {entry.patch_path}")
                target = _game_path(game_root, entry.path)
                tmp = target.with_name(target.name + ".patchsmith.tmp")
                log(f"xdelta decode: {entry.path}")
                xdelta.decode(xdelta_exe, old_file, patch_file, tmp)
                h, _ = hasher.sha256_file(tmp)
                if h != entry.new_sha256:
                    tmp.unlink(missing_ok=True)
                    raise RuntimeError(
                        f"Post-xdelta hash mismatch for {entry.path}: got {h[:16]}…"
                    )
                tmp.replace(target)
            else:
                assert entry.patch_path and entry.new_sha256
                src = patch_root.joinpath(*entry.patch_path.split("/"))
                if not src.is_file():
                    raise FileNotFoundError(f"Missing patch payload: {entry.patch_path}")
                h_src, _ = hasher.sha256_file(src)
                if h_src != entry.new_sha256:
                    raise RuntimeError(
                        f"Patch payload hash mismatch for {entry.path}"
                    )
                target = _game_path(game_root, entry.path)
                target.parent.mkdir(parents=True, exist_ok=True)
                tmp = target.with_name(target.name + ".patchsmith.tmp")
                shutil.copy2(src, tmp)
                h, _ = hasher.sha256_file(tmp)
                if h != entry.new_sha256:
                    tmp.unlink(missing_ok=True)
                    raise RuntimeError(f"Copied file hash mismatch for {entry.path}")
                if target.exists():
                    target.unlink()
                tmp.replace(target)

        for entry in delete_entries:
            gp = _game_path(game_root, entry.path)
            if gp.is_file():
                log(f"Delete: {entry.path}")
                gp.unlink()

        log("Verifying final tree…")
        for entry in manifest.files:
            if entry.action == "delete":
                gp = _game_path(game_root, entry.path)
                if gp.exists():
                    raise RuntimeError(f"File should be deleted but still exists: {entry.path}")
                continue
            if entry.new_sha256 is None:
                continue
            gp = _game_path(game_root, entry.path)
            if not gp.is_file():
                raise RuntimeError(f"Expected file missing after patch: {entry.path}")
            h, _ = hasher.sha256_file(gp)
            if h != entry.new_sha256:
                raise RuntimeError(
                    f"Final hash mismatch for {entry.path}: got {h[:16]}…"
                )

        log("Patch applied successfully.")
    finally:
        if temp_extract is not None:
            shutil.rmtree(temp_extract, ignore_errors=True)
