# -*- mode: python ; coding: utf-8 -*-
import json
import os
from pathlib import Path

root = Path.cwd()
a = Analysis(
    [str(root / "src" / "profiprompt.py")],
    pathex=[str(root / "src"), str(root)],
    binaries=[],
    datas=[
        (str(root / "pyproject.toml"), "."),
        (str(root / "DesktopIcon.ico"), "."),
        (str(root / "DesktopIcon.png"), "."),
        (str(root / "locales"), "locales"),
        *[(str(root / "src" / "icons" / filename), "icons")
          for filename in ("clipboard-dark.png", "clipboard-light.png", "paperclip-dark.png", "paperclip-light.png")],
        *[(str(root / filename), ".")
          for filename in ("LICENSE", "NOTICE", "THIRD_PARTY_LICENSES.txt", "PRIVACY_POLICY.md")],
    ],
    hiddenimports=["PySide6.QtPrintSupport"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=json.loads(os.environ["PYINSTALLER_EXCLUDES"]),
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="ProfiPrompt",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False,
    icon=[str(root / "DesktopIcon.ico")],
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="ProfiPrompt")
