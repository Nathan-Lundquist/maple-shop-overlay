#!/usr/bin/env python3
"""
Sync item price data from maplestory.io into the local SQLite database.

Run this once before first use, then periodically to keep prices up-to-date.

Examples:
    python sync_db.py
    python sync_db.py --region KMS --version 40
    python sync_db.py --categories Use Etc
"""

import argparse
import sys
from src.database import init_db, upsert_item, record_sync, get_stats
from src.api_client import iter_items, extract_price_fields, CATEGORIES


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync maplestory.io item prices to local DB")
    parser.add_argument("--region", default="GMS", help="Game region (default: GMS)")
    parser.add_argument("--version", default="64", help="Game version (default: 64)")
    parser.add_argument(
        "--categories",
        nargs="+",
        default=CATEGORIES,
        metavar="CAT",
        help=f"Item categories to sync (default: {' '.join(CATEGORIES)})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.05,
        help="Seconds between API requests (default: 0.05)",
    )
    args = parser.parse_args()

    print("Initialising database...")
    init_db()

    print(f"Syncing from maplestory.io [{args.region} v{args.version}]")
    print(f"Categories: {', '.join(args.categories)}\n")

    count = 0
    skipped = 0

    for detail in iter_items(
        region=args.region,
        version=args.version,
        categories=args.categories,
        delay=args.delay,
    ):
        fields = extract_price_fields(detail)
        if not fields["id"] or not fields["name"]:
            skipped += 1
            continue

        upsert_item(
            item_id=fields["id"],
            name=fields["name"],
            category=fields["category"],
            sub_category=fields["sub_category"],
            npc_buy_price=fields["npc_buy_price"],
        )
        count += 1

    record_sync(count)
    stats = get_stats()
    print(f"\nDone. Synced {count} items ({skipped} skipped).")
    print(f"DB total: {stats['item_count']} items.")


if __name__ == "__main__":
    main()
