from pathlib import Path

from patcher.engines.detect import Engine, detect_engine


def test_detect_generic_empty(tmp_path: Path) -> None:
    assert detect_engine(tmp_path) is Engine.GENERIC


def test_detect_rpg_structure(tmp_path: Path) -> None:
    (tmp_path / "www" / "data").mkdir(parents=True)
    (tmp_path / "www" / "js").mkdir(parents=True)
    assert detect_engine(tmp_path) is Engine.RPG_MAKER_MV_MZ
