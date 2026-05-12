from pathlib import Path

from patcher.core.manifest import ManifestFileEntry, PatchManifest


def test_manifest_roundtrip(tmp_path: Path) -> None:
    m = PatchManifest(
        patch_name="Test",
        from_version="0",
        to_version="1",
        xdelta_threshold_mb=12.5,
        files=[
            ManifestFileEntry(
                path="a/b.txt",
                action="copy",
                new_sha256="abc",
                patch_path="patch_files/new/a/b.txt",
                new_size=3,
            ),
            ManifestFileEntry(
                path="gone.dat",
                action="delete",
                old_sha256="def",
                old_size=9,
            ),
        ],
    )
    path = tmp_path / "patch_manifest.json"
    m.save(path)
    loaded = PatchManifest.load(path)
    assert loaded.patch_name == "Test"
    assert loaded.xdelta_threshold_mb == 12.5
    assert len(loaded.files) == 2
    assert loaded.files[0].path == "a/b.txt"
    assert loaded.files[1].action == "delete"
