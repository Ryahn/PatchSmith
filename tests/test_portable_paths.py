from pathlib import Path

from patcher.core.paths import PORTABLE_APPLY_EXE_NAME, portable_apply_patch_root


def test_portable_apply_exe_name() -> None:
    assert PORTABLE_APPLY_EXE_NAME == "ApplyPatch.exe"


def test_portable_apply_patch_root_prefers_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PATCHSMITH_PATCH_ROOT", str(tmp_path))
    assert portable_apply_patch_root() == tmp_path.resolve()
