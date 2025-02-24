# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['lesion_viewer_gui.py'],
             pathex=[],
             binaries=[],
             datas=[
                 ('static', 'static'),
                 ('templates', 'templates'),
                 ('scripts', 'scripts'),
                 ('requirements.yaml', '.'),
                 ('Lesion_viewer.py', '.'),
             ],
             hiddenimports=['nibabel', 'scipy', 'scikit-image', 'pandas', 'matplotlib',
                            'flask', 'werkzeug', 'configparser', 'psutil', 'aiofiles'],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='LesionViewer',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,  # Changed to False for windowed application
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          icon='static/images/icon.ico')

# Add this for a single-file build
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='LesionViewer')