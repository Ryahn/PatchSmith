import sys
from pathlib import Path

from patcher.core.paths import portable_apply_bundle_name, portable_apply_patch_root
from patcher.version import __version__


def test_portable_apply_bundle_name_windows(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    assert portable_apply_bundle_name() == f"ApplyPatch-{__version__}.exe"


def test_portable_apply_bundle_name_linux(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert portable_apply_bundle_name() == f"ApplyPatch-{__version__}"


def test_portable_apply_patch_root_prefers_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PATCHSMITH_PATCH_ROOT", str(tmp_path))
    assert portable_apply_patch_root() == tmp_path.resolve()
