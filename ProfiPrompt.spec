# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file fuer ProfiPrompt
# Build: python -m PyInstaller ProfiPrompt.spec --clean --noconfirm

block_cipher = None

a = Analysis(
    ['src/profiprompt.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/icons', 'icons'),
        ('locales', 'locales'),
    ],
    hiddenimports=[
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'PySide6.QtCore',
        'PySide6.QtPrintSupport',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ProfiPrompt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon='src/icons/BCO.0bdc6366-1e3b-4548-ae52-db1ba790b9b1_umgewandelt.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ProfiPrompt',
)
