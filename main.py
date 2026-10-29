#!/usr/bin/env python3
"""
Maple Shop Checker — always-on-top overlay that reads your MapleStory
shop and shows whether prices are a deal vs. NPC prices.

Quick start:
    1. python sync_db.py          # populate item DB (run once)
    2. python main.py             # start overlay
"""

import sys
import threading
import time
import argparse
from src import database as db
from src.capture import Capturer
from src.shop_reader import ShopReader
from src.matcher import ItemMatcher
from src.deal import rate_deal
from src.overlay import ShopOverlay, OverlayRow


SCAN_INTERVAL = 1.0   # seconds between shop scans


def scan_loop(
    reader: ShopReader,
    matcher: ItemMatcher,
    overlay: ShopOverlay,
    interval: float,
) -> None:
    while overlay.running:
        t0 = time.monotonic()

        shop = reader.read()

        if shop is None:
            overlay.set_status("No shop open — open an NPC or player shop in-game")
            time.sleep(interval)
            continue

        rows: list[OverlayRow] = []
        for item in shop.items:
            if not item.name and item.price is None:
                continue

            match = matcher.best_match(item.name) if item.name else None
            deal  = rate_deal(item.price or 0, match)

            rows.append(OverlayRow(
                ocr_name=item.name,
                matched_name=match.name if match else item.name,
                match_score=match.score if match else 0,
                deal=deal,
            ))

        elapsed = time.monotonic() - t0
        n_items = len(rows)
        status_parts = [f"{n_items} item{'s' if n_items != 1 else ''}"]
        if shop.title:
            status_parts.append(shop.title)
        status_parts.append(f"scan: {elapsed*1000:.0f}ms")
        status = "  |  ".join(status_parts)

        overlay.update_rows(rows, status=status)

        # Sleep for remainder of interval
        remaining = interval - (time.monotonic() - t0)
        if remaining > 0:
            time.sleep(remaining)


def main() -> None:
    parser = argparse.ArgumentParser(description="Maple Shop Price Checker Overlay")
    parser.add_argument(
        "--interval", type=float, default=SCAN_INTERVAL,
        help=f"Scan interval in seconds (default: {SCAN_INTERVAL})",
    )
    args = parser.parse_args()

    # --- Preflight checks ---
    db.init_db()
    stats = db.get_stats()
    if stats["item_count"] == 0:
        print("ERROR: Item database is empty.")
        print("Run 'python sync_db.py' first to populate item prices from maplestory.io")
        sys.exit(1)

    print(f"DB: {stats['item_count']:,} items loaded")
    if stats["last_sync"]:
        print(f"Last sync: {stats['last_sync']['synced_at']}")

    # --- Initialise components ---
    capturer = Capturer()
    reader   = ShopReader(capturer)
    matcher  = ItemMatcher()

    # --- Start overlay ---
    overlay = ShopOverlay()
    overlay.set_status(f"Ready — {stats['item_count']:,} items in DB")

    # Run scan loop in background thread; overlay runs its own mainloop
    scan_thread = threading.Thread(
        target=scan_loop,
        args=(reader, matcher, overlay, args.interval),
        daemon=True,
    )
    scan_thread.start()

    print("Overlay started. Open a shop in MapleStory to see price analysis.")
    overlay.run()   # blocks until window closed


if __name__ == "__main__":
    main()
