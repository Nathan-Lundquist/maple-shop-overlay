"""
Always-on-top tkinter overlay window showing shop price analysis.

Layout:
  ┌─────────────────────────────────────────────────────┐
  │ Maple Shop Checker          [⚙] [×]                 │
  ├─────────────────────────────────────────────────────┤
  │ Item Name           │ Shop   │ NPC    │ Rating       │
  ├─────────────────────────────────────────────────────┤
  │ White Potion        │ 100    │ 160    │ GREAT  -60   │
  │ Blue Potion         │ 170    │ 150    │ NOPE   +20   │
  │ ...                 │        │        │              │
  └─────────────────────────────────────────────────────┘
  DB: 12,450 items  |  last scan: 0.3s ago
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, font as tkfont
import time
import threading
from dataclasses import dataclass
from typing import Optional, Callable
from .deal import DealResult, DealRating, RATING_COLORS


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

BG       = "#1a1a2e"
BG_ROW   = "#16213e"
BG_ROW2  = "#0f3460"
FG       = "#e0e0e0"
FG_DIM   = "#888899"
ACCENT   = "#e94560"
TITLE_BG = "#0f3460"

FONT_FAMILY = "Courier New"
FONT_SIZE   = 10
FONT_BOLD   = (FONT_FAMILY, FONT_SIZE, "bold")
FONT_NORM   = (FONT_FAMILY, FONT_SIZE)
FONT_SMALL  = (FONT_FAMILY, 8)


def _fmt(n: int) -> str:
    """Format mesos with commas."""
    return f"{n:,}"


# ---------------------------------------------------------------------------
# Row data
# ---------------------------------------------------------------------------

@dataclass
class OverlayRow:
    ocr_name: str
    matched_name: str
    match_score: float
    deal: DealResult


# ---------------------------------------------------------------------------
# Overlay window
# ---------------------------------------------------------------------------

class ShopOverlay:
    def __init__(self, on_close: Optional[Callable] = None) -> None:
        self._on_close = on_close
        self._rows: list[OverlayRow] = []
        self._status = "Waiting for shop..."
        self._lock = threading.Lock()
        self._running = True

        self._root = tk.Tk()
        self._root.title("Maple Shop Checker")
        self._root.configure(bg=BG)
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.92)
        self._root.resizable(True, True)
        self._root.protocol("WM_DELETE_WINDOW", self._close)

        self._build_ui()
        self._root.geometry("580x300+40+40")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Title bar
        title_bar = tk.Frame(self._root, bg=TITLE_BG, pady=4)
        title_bar.pack(fill="x")
        title_bar.bind("<ButtonPress-1>", self._drag_start)
        title_bar.bind("<B1-Motion>", self._drag_motion)

        tk.Label(
            title_bar, text="🍁 Maple Shop Checker",
            bg=TITLE_BG, fg=FG, font=FONT_BOLD, padx=8,
        ).pack(side="left")

        close_btn = tk.Label(title_bar, text="✕", bg=TITLE_BG, fg=ACCENT, font=FONT_BOLD, padx=8, cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda _: self._close())

        # Header row
        header = tk.Frame(self._root, bg=BG_ROW2)
        header.pack(fill="x")
        for text, width in [
            ("Item Name", 24),
            ("Shop Price", 10),
            ("NPC Price", 10),
            ("Rating", 12),
        ]:
            tk.Label(
                header, text=text, bg=BG_ROW2, fg=FG_DIM,
                font=FONT_BOLD, width=width, anchor="w", padx=4,
            ).pack(side="left")

        # Scrollable item list
        container = tk.Frame(self._root, bg=BG)
        container.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=self._canvas.yview)
        self._item_frame = tk.Frame(self._canvas, bg=BG)

        self._item_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        )
        self._canvas.create_window((0, 0), window=self._item_frame, anchor="nw")
        self._canvas.configure(yscrollcommand=scrollbar.set)

        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Status bar
        self._status_var = tk.StringVar(value=self._status)
        status_bar = tk.Label(
            self._root, textvariable=self._status_var,
            bg=BG_ROW2, fg=FG_DIM, font=FONT_SMALL,
            anchor="w", padx=6, pady=2,
        )
        status_bar.pack(fill="x", side="bottom")

    # ------------------------------------------------------------------
    # Drag to move (borderless feel)
    # ------------------------------------------------------------------

    def _drag_start(self, event: tk.Event) -> None:
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag_motion(self, event: tk.Event) -> None:
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self._root.winfo_x() + dx
        y = self._root.winfo_y() + dy
        self._root.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    # Public API (thread-safe)
    # ------------------------------------------------------------------

    def update_rows(self, rows: list[OverlayRow], status: str = "") -> None:
        with self._lock:
            self._rows = rows
            if status:
                self._status = status
        self._root.after(0, self._redraw)

    def set_status(self, status: str) -> None:
        with self._lock:
            self._status = status
        self._root.after(0, lambda: self._status_var.set(status))

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _redraw(self) -> None:
        # Clear existing item widgets
        for child in self._item_frame.winfo_children():
            child.destroy()

        with self._lock:
            rows = list(self._rows)
            status = self._status

        if not rows:
            tk.Label(
                self._item_frame,
                text="No shop detected — open an NPC or player shop.",
                bg=BG, fg=FG_DIM, font=FONT_NORM, pady=20,
            ).pack()
        else:
            for i, row in enumerate(rows):
                bg = BG_ROW if i % 2 == 0 else BG
                self._render_row(row, bg)

        self._status_var.set(status)

    def _render_row(self, row: OverlayRow, bg: str) -> None:
        deal = row.deal
        frame = tk.Frame(self._item_frame, bg=bg, pady=1)
        frame.pack(fill="x")

        # Item name (show matched name if confidence is high, else OCR name in dim)
        if row.match_score >= 80:
            name_text = row.matched_name
            name_fg   = FG
        else:
            name_text = f"{row.ocr_name} (?)"
            name_fg   = FG_DIM

        tk.Label(frame, text=_truncate(name_text, 22), bg=bg, fg=name_fg,
                 font=FONT_NORM, width=24, anchor="w", padx=4).pack(side="left")

        # Shop price
        shop_txt = _fmt(deal.shop_price) if deal.shop_price else "—"
        tk.Label(frame, text=shop_txt, bg=bg, fg=FG,
                 font=FONT_NORM, width=10, anchor="e", padx=4).pack(side="left")

        # NPC buy price
        npc_txt = _fmt(deal.npc_buy_price) if deal.npc_buy_price else "—"
        tk.Label(frame, text=npc_txt, bg=bg, fg=FG_DIM,
                 font=FONT_NORM, width=10, anchor="e", padx=4).pack(side="left")

        # Rating badge + savings
        rating_frame = tk.Frame(frame, bg=bg)
        rating_frame.pack(side="left", padx=4)

        tk.Label(
            rating_frame,
            text=deal.label,
            bg=deal.color,
            fg="#111111",
            font=FONT_BOLD,
            padx=4, pady=0,
        ).pack(side="left")

        # Savings / extra cost
        if deal.npc_buy_price > 0 and deal.shop_price > 0:
            diff = deal.npc_buy_price - deal.shop_price
            diff_txt = f"  {'+' if diff >= 0 else ''}{_fmt(diff)}"
            diff_fg = "#55dd55" if diff > 0 else "#ff6666"
            tk.Label(rating_frame, text=diff_txt, bg=bg, fg=diff_fg,
                     font=FONT_NORM).pack(side="left")

        # Flip profit indicator
        if deal.rating == DealRating.FLIP and deal.flip_profit > 0:
            flip_txt = f"  flip+{_fmt(deal.flip_profit)}"
            tk.Label(rating_frame, text=flip_txt, bg=bg, fg=RATING_COLORS[DealRating.FLIP],
                     font=FONT_BOLD).pack(side="left")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _close(self) -> None:
        self._running = False
        if self._on_close:
            self._on_close()
        self._root.destroy()

    def run(self) -> None:
        """Start the tkinter main loop (blocks until window is closed)."""
        self._root.mainloop()

    @property
    def running(self) -> bool:
        return self._running


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n - 1] + "…"
