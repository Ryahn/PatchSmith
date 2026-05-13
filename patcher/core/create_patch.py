"""Build a patch folder from old and new game roots."""

from __future__ import annotations

import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from patcher.core import archiver, hasher, xdelta
from patcher.core.differ import diff_trees
from patcher.core.manifest import ManifestFileEntry, PatchManifest
from patcher.core.paths import bin_dir, patch_tools_dir, portable_apply_bundle_name, repo_root
from patcher.core.scanner import iter_files


LogFn = Callable[[str], None]
ConfirmLargeXdeltaFn = Callable[[str], bool]


class UserCancelledError(Exception):
    """Raised when the user aborts patch creation (e.g. large-xdelta confirmation)."""


def _noop_log(_: str) -> None:
    return None


def _is_windows() -> bool:
    return sys.platform == "win32"


def _is_linux() -> bool:
    return sys.platform.startswith("linux")


def _game_path(root: Path, rel_posix: str) -> Path:
    parts = rel_posix.split("/")
    return root.joinpath(*parts)


@dataclass
class CreatePatchOptions:
    old_root: Path
    new_root: Path
    out_patch_dir: Path
    patch_name: str
    from_version: str
    to_version: str
    xdelta_threshold_mb: float
    """xdelta3 secondary compression 1–9 (higher = smaller deltas, slower)."""
    xdelta_compression_level: int = 6
    """If > 0, prompt before xdelta when any planned job is ≥ this many MiB (GUI only passes a confirm fn)."""
    large_xdelta_warn_mb: float = 500.0
    confirm_large_xdelta: ConfirmLargeXdeltaFn | None = None
    track_deletes: bool = True
    bundle_archive: bool = False
    archive_format: str = "7z"
    archive_compression_level: int = 6
    bundle_tools: bool = False
    bundle_portable_apply: bool = False
    overwrite: bool = False
    extra_ignore_names: list[str] | None = None
    extra_ignore_path_prefixes: list[str] | None = None


def _threshold_bytes(mb: float) -> int:
    return int(mb * 1024 * 1024)


def create_patch(opts: CreatePatchOptions, log: LogFn | None = None) -> Path | None:
    """
    Write patch to `out_patch_dir`. If `bundle_archive`, return path to created archive;
    otherwise return None.
    """
    log = log or _noop_log
    old_root = opts.old_root.resolve()
    new_root = opts.new_root.resolve()
    out_dir = opts.out_patch_dir.resolve()

    if out_dir == old_root or out_dir == new_root:
        raise ValueError("Output patch directory must differ from old/new roots.")

    if out_dir.exists():
        if not opts.overwrite:
            raise FileExistsError(f"Output exists: {out_dir} (set overwrite=True to replace).")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    changed_dir = out_dir / "patch_files" / "changed"
    new_dir = out_dir / "patch_files" / "new"
    changed_dir.mkdir(parents=True, exist_ok=True)
    new_dir.mkdir(parents=True, exist_ok=True)

    log("Scanning old tree…")
    old_rels = iter_files(
        old_root,
        extra_ignore_names=opts.extra_ignore_names,
        extra_ignore_path_prefixes=opts.extra_ignore_path_prefixes,
    )
    log("Scanning new tree…")
    new_rels = iter_files(
        new_root,
        extra_ignore_names=opts.extra_ignore_names,
        extra_ignore_path_prefixes=opts.extra_ignore_path_prefixes,
    )

    log("Hashing old files…")
    old_map: dict[str, tuple[str, int]] = {}
    for i, rel in enumerate(old_rels):
        h, sz = hasher.sha256_file(_game_path(old_root, rel))
        old_map[rel] = (h, sz)
        if (i + 1) % 200 == 0:
            log(f"  old {i + 1}/{len(old_rels)}")

    log("Hashing new files…")
    new_map: dict[str, tuple[str, int]] = {}
    for i, rel in enumerate(new_rels):
        h, sz = hasher.sha256_file(_game_path(new_root, rel))
        new_map[rel] = (h, sz)
        if (i + 1) % 200 == 0:
            log(f"  new {i + 1}/{len(new_rels)}")

    dr = diff_trees(old_map, new_map)
    log(
        f"Diff: {len(dr.unchanged)} unchanged, {len(dr.changed)} changed, "
        f"{len(dr.new)} new, {len(dr.deleted)} deleted."
    )

    xdelta_exe = xdelta.resolve_xdelta3(patch_root=None)
    threshold = _threshold_bytes(opts.xdelta_threshold_mb)
    warn_b = _threshold_bytes(opts.large_xdelta_warn_mb) if opts.large_xdelta_warn_mb > 0 else 0
    manifest_files: list[ManifestFileEntry] = []

    plan_xdelta: list[tuple[str, int, int]] = []
    for rel in dr.changed:
        old_h, old_sz = old_map[rel]
        new_h, new_sz = new_map[rel]
        max_sz = max(old_sz, new_sz)
        if max_sz >= threshold:
            plan_xdelta.append((rel, old_sz, new_sz))

    if warn_b and plan_xdelta and opts.confirm_large_xdelta is not None:
        big_jobs = [(rel, o, n) for rel, o, n in plan_xdelta if max(o, n) >= warn_b]
        if big_jobs:
            big_jobs.sort(key=lambda t: max(t[1], t[2]), reverse=True)
            lines: list[str] = []
            for rel, o, n in big_jobs[:25]:
                mb = max(o, n) / (1024 * 1024)
                lines.append(f"  • {rel}  (~{mb:.0f} MiB)")
            more = ""
            if len(big_jobs) > 25:
                more = f"\n… and {len(big_jobs) - 25} more file(s)"
            msg = (
                f"{len(big_jobs)} changed file(s) are each ≥ {opts.large_xdelta_warn_mb:.0f} MiB and will be "
                "encoded with xdelta3. Large jobs can take a long time and stress CPU and disk.\n\n"
                "Largest files:\n"
                + "\n".join(lines)
                + more
                + "\n\nContinue with patch creation?"
            )
            if not opts.confirm_large_xdelta(msg):
                shutil.rmtree(out_dir)
                raise UserCancelledError("Patch creation cancelled.")

    for rel in sorted(dr.changed):
        old_h, old_sz = old_map[rel]
        new_h, new_sz = new_map[rel]
        max_sz = max(old_sz, new_sz)
        use_xdelta = max_sz >= threshold
        if use_xdelta:
            rel_delta = f"patch_files/changed/{rel}.xdelta"
            out_delta = out_dir.joinpath(*rel_delta.split("/"))
            out_delta.parent.mkdir(parents=True, exist_ok=True)
            log(f"xdelta encode: {rel}")
            xdelta.encode(
                xdelta_exe,
                _game_path(old_root, rel),
                _game_path(new_root, rel),
                out_delta,
                compression_level=opts.xdelta_compression_level,
                progress_log=log,
                progress_label=rel,
            )
            manifest_files.append(
                ManifestFileEntry(
                    path=rel,
                    action="xdelta",
                    old_sha256=old_h,
                    new_sha256=new_h,
                    patch_path=rel_delta,
                    old_size=old_sz,
                    new_size=new_sz,
                )
            )
        else:
            rel_copy = f"patch_files/changed/{rel}"
            dst = out_dir.joinpath(*rel_copy.split("/"))
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_game_path(new_root, rel), dst)
            manifest_files.append(
                ManifestFileEntry(
                    path=rel,
                    action="copy",
                    old_sha256=old_h,
                    new_sha256=new_h,
                    patch_path=rel_copy,
                    old_size=old_sz,
                    new_size=new_sz,
                )
            )

    for rel in sorted(dr.new):
        rel_copy = f"patch_files/new/{rel}"
        dst = out_dir.joinpath(*rel_copy.split("/"))
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_game_path(new_root, rel), dst)
        new_h, new_sz = new_map[rel]
        manifest_files.append(
            ManifestFileEntry(
                path=rel,
                action="copy",
                new_sha256=new_h,
                patch_path=rel_copy,
                new_size=new_sz,
            )
        )

    deleted_list: list[str] = []
    if opts.track_deletes:
        for rel in sorted(dr.deleted):
            old_h, old_sz = old_map[rel]
            manifest_files.append(
                ManifestFileEntry(
                    path=rel,
                    action="delete",
                    old_sha256=old_h,
                    old_size=old_sz,
                )
            )
            deleted_list.append(rel)

    if deleted_list:
        (out_dir / "deleted_files.txt").write_text(
            "\n".join(deleted_list) + "\n",
            encoding="utf-8",
        )

    manifest = PatchManifest(
        manifest_version=1,
        patch_name=opts.patch_name,
        from_version=opts.from_version,
        to_version=opts.to_version,
        created_by="PatchSmith",
        xdelta_threshold_mb=opts.xdelta_threshold_mb,
        archive_format=opts.archive_format if opts.bundle_archive else None,
        archive_compression_level=opts.archive_compression_level if opts.bundle_archive else None,
        bundle_archive=opts.bundle_archive,
        files=manifest_files,
    )
    manifest.save(out_dir / "patch_manifest.json")
    log(f"Wrote manifest ({len(manifest_files)} file entries).")

    if opts.bundle_portable_apply:
        bundle_name = portable_apply_bundle_name()
        src = repo_root() / "bin" / bundle_name
        dst = out_dir / bundle_name
        if src.is_file():
            shutil.copy2(src, dst)
            if _is_linux():
                dst.chmod(dst.stat().st_mode | 0o111)
            log(f"Included portable apply tool: {bundle_name}")
        else:
            log(
                f"Warning: portable apply tool not found at {src}. "
                "Build it with PyInstaller (see README / .github/workflows) "
                f"and copy the output to bin/{bundle_name}."
            )

    if opts.bundle_tools:
        tools = patch_tools_dir(out_dir)
        tools.mkdir(parents=True, exist_ok=True)
        b = bin_dir()
        if _is_windows():
            for src_name, dst_name in (
                ("xdelta-3.1.0-x86_64.exe", "xdelta3.exe"),
                ("7za.exe", "7za.exe"),
            ):
                src = b / src_name
                if src.is_file():
                    shutil.copy2(src, tools / dst_name)
                    log(f"Bundled tool: {dst_name}")
        elif _is_linux():
            src = b / "xdelta3-linux"
            if src.is_file():
                shutil.copy2(src, tools / "xdelta3")
                (tools / "xdelta3").chmod(0o755)
                log("Bundled tool: xdelta3")
            z7 = b / "7za-linux"
            if z7.is_file():
                shutil.copy2(z7, tools / "7za")
                (tools / "7za").chmod(0o755)
                log("Bundled tool: 7za")

    archive_path: Path | None = None
    if opts.bundle_archive:
        sevenza = archiver.resolve_7za(patch_root=None)
        ext = ".7z" if opts.archive_format.lower() == "7z" else ".zip"
        archive_path = out_dir.parent / f"{out_dir.name}{ext}"
        log(f"Creating archive {archive_path.name}…")
        archiver.create_archive(
            sevenza,
            out_dir,
            archive_path,
            archive_format=opts.archive_format,
            compression_level=opts.archive_compression_level,
        )
        log("Archive complete.")

    return archive_path
