"""
Fetches item data from maplestory.io and populates the local database.

Usage:
    python sync_db.py            # sync all Use + Etc + Equip items
    python sync_db.py --region KMS --version 40
"""

import requests
import time
import sys
from typing import Iterator

BASE = "https://maplestory.io/api"
DEFAULT_REGION = "GMS"
DEFAULT_VERSION = "64"

# Categories most relevant for shop comparisons
CATEGORIES = ["Use", "Etc", "Equip"]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "maple-shop-overlay/1.0"})


def _get(path: str, retries: int = 3) -> dict | list | None:
    url = f"{BASE}{path}"
    for attempt in range(retries):
        try:
            r = SESSION.get(url, timeout=10)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 503):
                time.sleep(2 ** attempt)
                continue
            return None
        except requests.RequestException as e:
            if attempt == retries - 1:
                print(f"  [warn] {url} failed: {e}", file=sys.stderr)
            time.sleep(1)
    return None


def iter_items(
    region: str = DEFAULT_REGION,
    version: str = DEFAULT_VERSION,
    categories: list[str] = CATEGORIES,
    delay: float = 0.05,
) -> Iterator[dict]:
    """
    Yields full item dicts (with metaInfo.price) for every item in the given categories.
    Makes one list call per category then one detail call per item.
    """
    for cat in categories:
        print(f"  Fetching category list: {cat}")
        items = _get(f"/{region}/{version}/item/category/{cat}")
        if not items:
            print(f"  [warn] no data for category {cat}")
            continue

        print(f"  {len(items)} items in {cat} — fetching details...")
        for i, stub in enumerate(items, 1):
            item_id = stub.get("id")
            if not item_id:
                continue

            detail = _get(f"/{region}/{version}/item/{item_id}")
            if detail:
                yield detail

            if i % 100 == 0:
                print(f"    {i}/{len(items)}")
            time.sleep(delay)


def extract_price_fields(detail: dict) -> dict:
    """Pull out the fields we care about from a full item detail response."""
    meta = detail.get("metaInfo") or {}
    desc = detail.get("description") or {}
    type_info = detail.get("typeInfo") or {}

    return {
        "id": detail.get("id"),
        "name": desc.get("name") or detail.get("name") or "",
        "category": type_info.get("overallCategory", ""),
        "sub_category": type_info.get("subCategory", ""),
        "npc_buy_price": meta.get("price") or 0,
    }
