# PyInstaller spec for Maple Shop Checker
# Run: pyinstaller build.spec

import sys
import os
from pathlib import Path

block_cipher = None

# Path to Tesseract installation on the build machine (Windows default)
TESSERACT_DIR = Path(os.environ.get(
    "TESSERACT_DIR",
    r"C:\Program Files\Tesseract-OCR"
))

# Files to bundle from Tesseract
tess_binaries = []
tess_datas = []

if TESSERACT_DIR.exists():
    tess_exe = TESSERACT_DIR / "tesseract.exe"
    if tess_exe.exists():
        tess_binaries.append((str(tess_exe), "tesseract"))

    # Only bundle English + OSD (keeps size down)
    tessdata_dir = TESSERACT_DIR / "tessdata"
    for lang_file in ["eng.traineddata", "osd.traineddata"]:
        p = tessdata_dir / lang_file
        if p.exists():
            tess_datas.append((str(p), "tesseract/tessdata"))
else:
    print(f"WARNING: Tesseract not found at {TESSERACT_DIR}")
    print("Set TESSERACT_DIR env var or install Tesseract first.")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=tess_binaries,
    datas=tess_datas + [
        ("assets", "assets"),       # include DB if pre-built
    ],
    hiddenimports=[
        "PIL._tkinter_finder",
        "rapidfuzz",
        "mss.windows",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "pandas", "IPython"],
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
    name="MapleShopChecker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no console window — overlay only
    icon=None,              # add an .ico file path here if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MapleShopChecker",
)
