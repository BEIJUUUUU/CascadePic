# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Waterfall Media Viewer (one-dir build).

Paths are relative to this spec file's directory (packaging/).
"""

from PyInstaller.utils.hooks import collect_submodules

datas = [
    ("../src/waterfall_viewer/resources", "waterfall_viewer/resources"),
]

a = Analysis(
    ["launcher.py"],
    pathex=["../src"],
    binaries=[],
    datas=datas,
    hiddenimports=collect_submodules("waterfall_viewer"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WaterfallMediaViewer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="WaterfallMediaViewer",
)
