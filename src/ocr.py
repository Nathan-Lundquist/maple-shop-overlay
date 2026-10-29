"""
OCR helpers for reading MapleStory shop text.

MapleStory Classic uses a small pixel font. Tesseract works well with
upscaling + sharpening applied first. Prices are comma-separated integers.
"""

from __future__ import annotations
import re
import subprocess
import sys
import tempfile
import os
from pathlib import Path
import numpy as np
import cv2
from PIL import Image
from typing import Optional


def _find_tesseract() -> str:
    """
    Locate the tesseract binary.
    When running as a PyInstaller bundle, use the bundled copy.
    Otherwise fall back to whatever is on PATH.
    """
    if getattr(sys, "frozen", False):
        # Running inside a PyInstaller .exe — use bundled binary
        base = Path(sys._MEIPASS) / "tesseract"
        exe = base / "tesseract.exe"
        if exe.exists():
            os.environ["TESSDATA_PREFIX"] = str(base / "tessdata")
            return str(exe)
    return "tesseract"   # rely on PATH


_TESSERACT_CMD = _find_tesseract()

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD
    _HAS_PYTESSERACT = True
except ImportError:
    _HAS_PYTESSERACT = False


# Tesseract config tuned for MapleStory's pixel font
_PSM_LINE = "--psm 7"        # single text line
_PSM_BLOCK = "--psm 6"       # uniform block of text
_DIGITS_OSD = "digits"       # digit-only OCR engine mode
_LANG = "eng"

PRICE_RE = re.compile(r"[\d,]+")


def _preprocess(img: np.ndarray, upscale: int = 3) -> np.ndarray:
    """
    Upscale + sharpen a BGR image for better Tesseract accuracy on pixel fonts.
    Returns a grayscale image.
    """
    h, w = img.shape[:2]
    big = cv2.resize(img, (w * upscale, h * upscale), interpolation=cv2.INTER_NEAREST)
    gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
    # Threshold to binary — MapleStory text is generally dark on light background
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def _run_tesseract(img: np.ndarray, config: str) -> str:
    """Run Tesseract on a preprocessed grayscale image and return stripped text."""
    pil = Image.fromarray(img)

    if _HAS_PYTESSERACT:
        return pytesseract.image_to_string(pil, lang=_LANG, config=config).strip()

    # Fallback: call tesseract CLI directly
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp = f.name
    pil.save(tmp)
    try:
        result = subprocess.run(
            [_TESSERACT_CMD, tmp, "stdout", "-l", _LANG] + config.split(),
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    finally:
        os.unlink(tmp)


def read_item_name(img: np.ndarray) -> str:
    """OCR a single-line item name region."""
    processed = _preprocess(img, upscale=3)
    text = _run_tesseract(processed, f"{_PSM_LINE} -c tessedit_char_blacklist=|")
    # Clean up common OCR artifacts
    text = re.sub(r"[^a-zA-Z0-9 '\-+()]", "", text).strip()
    return text


def read_price(img: np.ndarray) -> Optional[int]:
    """
    OCR a price field (digits + commas, e.g. '12,500').
    Returns integer mesos value or None if unreadable.
    """
    processed = _preprocess(img, upscale=4)
    text = _run_tesseract(processed, f"{_PSM_LINE} -c tessedit_char_whitelist=0123456789,")
    m = PRICE_RE.search(text)
    if not m:
        return None
    try:
        return int(m.group().replace(",", ""))
    except ValueError:
        return None


def read_block(img: np.ndarray) -> str:
    """OCR a multi-line block (e.g. entire shop panel). Returns raw string."""
    processed = _preprocess(img, upscale=3)
    return _run_tesseract(processed, _PSM_BLOCK)
