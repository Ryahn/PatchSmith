import shutil
import sys
from pathlib import Path

import pytest

from patcher.core.apply_patch import ApplyPatchOptions, apply_patch
from patcher.core.archiver import SevenZipNotFoundError, resolve_7za
from patcher.core.create_patch import CreatePatchOptions, create_patch


def _has_windows_bins() -> bool:
    root = Path(__file__).resolve().parents[1]
    return (root / "bin" / "xdelta-3.1.0-x86_64.exe").is_file() and (root / "bin" / "7za.exe").is_file()


@pytest.mark.skipif(sys.platform != "win32", reason="Bundled xdelta/7za paths are Windows-first in this repo")
@pytest.mark.skipif(not _has_windows_bins(), reason="Missing bin/xdelta and bin/7za")
def test_create_apply_roundtrip_no_archive(tmp_path: Path) -> None:
    old = tmp_path / "old"
    new = tmp_path / "new"
    patch = tmp_path / "patch_out"
    old.mkdir()
    new.mkdir()
    (old / "readme.txt").write_text("v1\n", encoding="utf-8")
    (new / "readme.txt").write_text("v2\n", encoding="utf-8")
    (new / "extra.bin").write_bytes(b"\x00\x01")

    opts = CreatePatchOptions(
        old_root=old,
        new_root=new,
        out_patch_dir=patch,
        patch_name="Test patch",
        from_version="1",
        to_version="2",
        xdelta_threshold_mb=50.0,
        track_deletes=True,
        bundle_archive=False,
        bundle_tools=False,
        overwrite=True,
    )
    create_patch(opts, log=lambda s: None)

    game_apply = tmp_path / "game_copy"
    shutil.copytree(old, game_apply)

    apply_patch(
        ApplyPatchOptions(game_root=game_apply, patch_path=patch, backup=False),
        log=lambda s: None,
    )

    assert (game_apply / "readme.txt").read_text(encoding="utf-8") == "v2\n"
    assert (game_apply / "extra.bin").read_bytes() == b"\x00\x01"


@pytest.mark.skipif(sys.platform != "win32", reason="7za.exe bundled for Windows")
@pytest.mark.skipif(not _has_windows_bins(), reason="Missing bin tools")
def test_create_apply_with_7z_archive(tmp_path: Path) -> None:
    try:
        resolve_7za(patch_root=None)
    except SevenZipNotFoundError:
        pytest.skip("7za not resolvable")

    old = tmp_path / "old2"
    new = tmp_path / "new2"
    patch_dir = tmp_path / "patch_dir2"
    old.mkdir()
    new.mkdir()
    (old / "data.txt").write_bytes(b"same")
    (new / "data.txt").write_bytes(b"same")
    (new / "only_new.txt").write_text("hello", encoding="utf-8")

    create_patch(
        CreatePatchOptions(
            old_root=old,
            new_root=new,
            out_patch_dir=patch_dir,
            patch_name="z",
            from_version="a",
            to_version="b",
            xdelta_threshold_mb=9999.0,
            track_deletes=False,
            bundle_archive=True,
            archive_format="zip",
            archive_compression_level=3,
            bundle_tools=False,
            overwrite=True,
        ),
        log=lambda s: None,
    )

    archive = patch_dir.parent / f"{patch_dir.name}.zip"
    assert archive.is_file()

    game_apply = tmp_path / "game_zip"
    shutil.copytree(old, game_apply)
    apply_patch(
        ApplyPatchOptions(game_root=game_apply, patch_path=archive, backup=True, backup_dir=tmp_path / "backs"),
        log=lambda s: None,
    )
    assert (game_apply / "only_new.txt").read_text(encoding="utf-8") == "hello"
