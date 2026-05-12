# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: PatchSmith main GUI (Windows, windowed)."""

from pathlib import Path

REPO = Path(SPECPATH).resolve().parent

block_cipher = None

a = Analysis(
    [str(REPO / "patcher" / "app.py")],
    pathex=[str(REPO)],
    binaries=[],
    datas=[
        (str(REPO / "bin" / "xdelta-3.1.0-x86_64.exe"), "bin"),
        (str(REPO / "bin" / "7za.exe"), "bin"),
    ],
    hiddenimports=[
        "patcher.gui.main_window",
        "patcher.gui.portable_apply_window",
        "patcher.core.apply_patch",
        "patcher.core.archiver",
        "patcher.core.create_patch",
        "patcher.core.hasher",
        "patcher.core.manifest",
        "patcher.core.paths",
        "patcher.core.xdelta",
        "patcher.core.scanner",
        "patcher.core.differ",
        "patcher.engines.detect",
        "patcher.engines.generic",
        "patcher.platform_check",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PatchSmith",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
