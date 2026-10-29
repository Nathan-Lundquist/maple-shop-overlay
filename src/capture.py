"""
Screen capture via mss. Returns numpy arrays (BGR, for OpenCV).
"""

from __future__ import annotations
import numpy as np
import mss
import mss.tools
from typing import Optional


class Capturer:
    def __init__(self) -> None:
        self._sct = mss.mss()

    def grab(self, left: int, top: int, width: int, height: int) -> Optional[np.ndarray]:
        """Capture a screen region. Returns BGR numpy array or None."""
        if width < 4 or height < 4:
            return None
        region = {"left": left, "top": top, "width": width, "height": height}
        try:
            raw = self._sct.grab(region)
        except mss.exception.ScreenShotError:
            return None
        # mss returns BGRA; drop alpha, keep BGR for OpenCV
        img = np.array(raw)[:, :, :3]
        return img

    def grab_rect(self, rect: tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """rect = (left, top, right, bottom)"""
        left, top, right, bottom = rect
        return self.grab(left, top, right - left, bottom - top)

    def monitors(self) -> list[dict]:
        return self._sct.monitors[1:]  # index 0 is the virtual "all monitors" entry
