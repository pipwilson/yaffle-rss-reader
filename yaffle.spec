# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['yaffle.py'],
    pathex=[],
    binaries=[('.venv\Lib\site-packages\wx\WebView2Loader.dll', '.')],
    datas=[('rss-32.png', '.'), ('yaffle.png', '.')],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='yaffle',
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
    icon=['yaffle.ico'],
    hide_console='hide-early',
)
