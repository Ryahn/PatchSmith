# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: one-file ApplyPatch (Linux x86_64, windowed Qt).

Expects repo bin/xdelta3-linux and bin/7za-linux (e.g. copy from p7zip-full in CI).
"""

import runpy
from pathlib import Path

REPO = Path(SPECPATH).resolve().parent
VERSION = runpy.run_path(str(REPO / "patcher" / "version.py"))["__version__"]

block_cipher = None

a = Analysis(
    [str(REPO / "patcher" / "apply_portable.py")],
    pathex=[str(REPO)],
    binaries=[],
    datas=[
        (str(REPO / "bin" / "xdelta3-linux"), "bin"),
        (str(REPO / "bin" / "7za-linux"), "bin"),
    ],
    hiddenimports=[
        "patcher.core.apply_patch",
        "patcher.core.archiver",
        "patcher.core.hasher",
        "patcher.core.manifest",
        "patcher.core.paths",
        "patcher.core.xdelta",
        "patcher.version",
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
    name=f"ApplyPatch-{VERSION}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
