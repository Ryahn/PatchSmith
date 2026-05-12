from pathlib import Path

from patcher.core.hasher import sha256_file


def test_sha256_file_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "a.bin"
    p.write_bytes(b"hello patchsmith")
    h, sz = sha256_file(p)
    assert sz == len(b"hello patchsmith")
    assert len(h) == 64


def test_sha256_empty_file(tmp_path: Path) -> None:
    p = tmp_path / "empty"
    p.write_bytes(b"")
    h, sz = sha256_file(p)
    assert sz == 0
    assert h == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
