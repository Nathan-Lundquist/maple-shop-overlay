"""
Detects the MapleStory shop window on screen and parses its contents.

MapleStory Classic shop windows have a distinctive beige/tan border with
a dark title bar. We locate the window by color signature then OCR the
item rows inside.

Layout (approximate, varies by resolution):
  - Title bar:  ~20px tall, dark brown (#2b1a00 area)
  - Item rows:  ~32px tall each, light background
    - Item name: left ~70% of row width
    - Quantity:  middle column
    - Price:     right column, digits + commas
"""

from __future__ import annotations
import numpy as np
import cv2
from dataclasses import dataclass
from typing import Optional
from .capture import Capturer
from .ocr import read_item_name, read_price

# ---------------------------------------------------------------------------
# Shop window detection constants
# ---------------------------------------------------------------------------

# Approximate HSV range for the shop window's tan/beige border color
# (adjust if your client skin differs)
BORDER_HUE_LO  = np.array([15,  60,  100], dtype=np.uint8)
BORDER_HUE_HI  = np.array([35, 200,  220], dtype=np.uint8)

# Minimum shop window dimensions (pixels)
MIN_W, MIN_H = 200, 150

# Row height in the shop item list (Classic client at 800x600 = ~32px)
# The reader tries multiple row heights if detection fails.
CANDIDATE_ROW_H = [32, 28, 36, 24]

# Columns as fractions of the row width [left, right)
COL_NAME   = (0.03, 0.62)
COL_QTY    = (0.62, 0.78)
COL_PRICE  = (0.78, 0.99)


@dataclass
class ShopItem:
    name: str
    quantity: Optional[int]
    price: Optional[int]       # mesos shown in shop
    row_y: int                 # y-coordinate of the row (for debug)


@dataclass
class ShopWindow:
    rect: tuple[int, int, int, int]   # (left, top, right, bottom) screen coords
    items: list[ShopItem]
    title: str = ""


def _find_shop_rect(
    screen: np.ndarray,
    origin: tuple[int, int],
) -> Optional[tuple[int, int, int, int]]:
    """
    Find the shop window rectangle within a screen capture.
    Returns (left, top, right, bottom) in screen coordinates.
    """
    hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, BORDER_HUE_LO, BORDER_HUE_HI)

    # Dilate to connect nearby border pixels
    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(mask, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < MIN_W or h < MIN_H:
            continue
        area = cv2.contourArea(cnt)
        rect_area = w * h
        fill = area / rect_area if rect_area else 0
        # Shop border should fill a reasonable fraction of its bounding box
        if fill < 0.05:
            continue
        if best is None or rect_area > best[4]:
            best = (x, y, w, h, rect_area)

    if best is None:
        return None

    x, y, w, h, _ = best
    ox, oy = origin
    return (ox + x, oy + y, ox + x + w, oy + y + h)


def _extract_rows(
    capturer: Capturer,
    shop_rect: tuple[int, int, int, int],
    row_h: int = 32,
    title_h: int = 22,
    header_h: int = 20,
) -> list[ShopItem]:
    """
    Slice the shop window into rows and OCR each one.
    """
    left, top, right, bottom = shop_rect
    w = right - left
    content_top = top + title_h + header_h
    items: list[ShopItem] = []

    y = content_top
    while y + row_h <= bottom - 4:
        row_img = capturer.grab(left, y, w, row_h)
        if row_img is None:
            break

        # Skip rows that are mostly uniform (empty/separator)
        if _is_blank_row(row_img):
            y += row_h
            continue

        def col(bounds: tuple[float, float]) -> np.ndarray:
            x0 = int(w * bounds[0])
            x1 = int(w * bounds[1])
            return row_img[:, x0:x1]

        name  = read_item_name(col(COL_NAME))
        price = read_price(col(COL_PRICE))
        qty   = read_price(col(COL_QTY))   # same digit-read logic works for quantity

        if name or price is not None:
            items.append(ShopItem(name=name, quantity=qty, price=price, row_y=y))

        y += row_h

    return items


def _is_blank_row(row: np.ndarray, threshold: float = 0.97) -> bool:
    """Return True if the row is nearly a solid color (empty separator)."""
    gray = cv2.cvtColor(row, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    white_frac = np.count_nonzero(binary) / binary.size
    return white_frac > threshold


class ShopReader:
    def __init__(self, capturer: Capturer) -> None:
        self._cap = capturer
        self._last_rect: Optional[tuple[int, int, int, int]] = None

    def read(self) -> Optional[ShopWindow]:
        """
        Scan all monitors for a shop window and return parsed contents.
        Returns None if no shop is open.
        """
        for mon in self._cap.monitors():
            ox, oy = mon["left"], mon["top"]
            screen = self._cap.grab(ox, oy, mon["width"], mon["height"])
            if screen is None:
                continue

            rect = _find_shop_rect(screen, (ox, oy))
            if rect is None:
                continue

            # Try different row heights to find the one that yields the most items
            best_items: list[ShopItem] = []
            for row_h in CANDIDATE_ROW_H:
                items = _extract_rows(self._cap, rect, row_h=row_h)
                if len(items) > len(best_items):
                    best_items = items

            self._last_rect = rect
            return ShopWindow(rect=rect, items=best_items)

        self._last_rect = None
        return None

    @property
    def last_rect(self) -> Optional[tuple[int, int, int, int]]:
        return self._last_rect
