# -*- mode: python ; coding: utf-8 -*-
import os

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(SPECPATH))

a = Analysis(
    ['lesion_viewer_gui.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        ('Lesion_viewer.py', '.'),
        ('scripts/Isolate_lesions.py', 'scripts'),
        ('scripts/match_lesions.py', 'scripts'),
        ('scripts/app.py', 'scripts'),
        ('scripts/image_processing.py', 'scripts'),
        ('templates', 'templates'),
        ('static', 'static'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='lesion_viewer_gui',
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