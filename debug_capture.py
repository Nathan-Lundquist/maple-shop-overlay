#!/usr/bin/env python3
"""
Debug helper — takes a screenshot, tries to find the shop window,
and shows what the OCR reads. Useful for tuning detection.

Usage:
    python debug_capture.py               # scan all monitors
    python debug_capture.py --save        # save annotated screenshot
    python debug_capture.py --lookup "White Potion"  # look up a specific item
"""

import argparse
import sys
import cv2
import numpy as np
from src.capture import Capturer
from src.shop_reader import ShopReader, _find_shop_rect
from src.matcher import ItemMatcher
from src.deal import rate_deal
from src import database as db


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true", help="Save annotated screenshot")
    parser.add_argument("--lookup", metavar="NAME", help="Look up an item price by name")
    args = parser.parse_args()

    db.init_db()
    stats = db.get_stats()
    print(f"DB: {stats['item_count']:,} items")

    if args.lookup:
        matcher = ItemMatcher()
        results = matcher.match(args.lookup, limit=5)
        if not results:
            print(f"No matches found for '{args.lookup}'")
        else:
            print(f"\nMatches for '{args.lookup}':")
            print(f"{'Name':<30} {'NPC Buy':>10} {'NPC Sell':>10} {'Score':>6}")
            print("-" * 60)
            for r in results:
                print(f"{r.name:<30} {r.npc_buy_price:>10,} {r.npc_sell_price:>10,} {r.score:>6.1f}")
        return

    cap = Capturer()
    reader = ShopReader(cap)

    print("Scanning for shop window...")
    shop = reader.read()

    if shop is None:
        print("No shop detected.")
        print("Tips:")
        print("  - Make sure MapleStory is running and a shop is open")
        print("  - Try adjusting BORDER_HUE_LO/HI in src/shop_reader.py if your")
        print("    client skin has a different color scheme")
        sys.exit(0)

    print(f"Shop found at rect: {shop.rect}")
    print(f"Items detected: {len(shop.items)}\n")

    matcher = ItemMatcher()

    print(f"{'OCR Name':<25} {'Price':>8} {'Matched':<25} {'Score':>6} {'Rating':<10}")
    print("-" * 80)
    for item in shop.items:
        match = matcher.best_match(item.name) if item.name else None
        deal  = rate_deal(item.price or 0, match)
        print(
            f"{item.name or '(blank)':<25} "
            f"{item.price or 0:>8,} "
            f"{match.name if match else '—':<25} "
            f"{match.score if match else 0:>6.1f} "
            f"{deal.label:<10}"
        )

    if args.save:
        # Grab annotated screenshot
        left, top, right, bottom = shop.rect
        img = cap.grab(left, top, right - left, bottom - top)
        if img is not None:
            out = "debug_shop.png"
            cv2.imwrite(out, img)
            print(f"\nSaved shop screenshot to {out}")


if __name__ == "__main__":
    main()
