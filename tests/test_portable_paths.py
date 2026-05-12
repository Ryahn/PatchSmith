from pathlib import Path

from patcher.core.paths import (
    PORTABLE_APPLY_EXE_NAME,
    PORTABLE_APPLY_LINUX_NAME,
    portable_apply_bundle_name,
    portable_apply_patch_root,
)


def test_portable_apply_bundle_name_windows(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "win32", raising=False)
    assert portable_apply_bundle_name() == PORTABLE_APPLY_EXE_NAME


def test_portable_apply_bundle_name_linux(monkeypatch) -> None:
    monkeypatch.setattr("sys.platform", "linux", raising=False)
    assert portable_apply_bundle_name() == PORTABLE_APPLY_LINUX_NAME


def test_portable_apply_patch_root_prefers_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PATCHSMITH_PATCH_ROOT", str(tmp_path))
    assert portable_apply_patch_root() == tmp_path.resolve()
