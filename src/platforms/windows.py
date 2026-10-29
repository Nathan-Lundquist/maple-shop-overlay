"""
Win32 helpers for finding the MapleStory game window.
"""

from __future__ import annotations
import ctypes
import ctypes.wintypes as wt
import sys
from typing import Optional

if sys.platform != "win32":
    def find_game_window() -> Optional[tuple[int, int, int, int]]:
        return None
else:
    user32 = ctypes.windll.user32
    psapi  = ctypes.windll.psapi

    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    class _RECT(ctypes.Structure):
        _fields_ = [("left", wt.LONG), ("top", wt.LONG),
                    ("right", wt.LONG), ("bottom", wt.LONG)]

    def _get_exe(hwnd: int) -> str:
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h = ctypes.windll.kernel32.OpenProcess(
            _PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if not h:
            return ""
        buf = ctypes.create_unicode_buffer(512)
        size = wt.DWORD(512)
        ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        ctypes.windll.kernel32.CloseHandle(h)
        return buf.value.lower()

    def find_game_window() -> Optional[tuple[int, int, int, int]]:
        """
        Find the MapleStory window and return its client rect in screen coords.
        Returns (left, top, right, bottom) or None.
        """
        result: list[Optional[tuple[int, int, int, int]]] = [None]

        @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        def callback(hwnd: int, _: int) -> bool:
            exe = _get_exe(hwnd)
            if "maplestory" not in exe:
                return True

            # Get the client area (excludes window chrome)
            r = _RECT()
            user32.GetClientRect(hwnd, ctypes.byref(r))
            pt = wt.POINT()
            user32.ClientToScreen(hwnd, ctypes.byref(pt))
            result[0] = (
                pt.x, pt.y,
                pt.x + r.right - r.left,
                pt.y + r.bottom - r.top,
            )
            return False   # stop enumeration

        user32.EnumWindows(callback, 0)
        return result[0]
