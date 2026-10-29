"""
SQLite database for caching NPC item prices from maplestory.io.
"""

import sqlite3
import math
import os
import sys
from pathlib import Path
from typing import Optional


def _db_path() -> Path:
    # When running as a PyInstaller bundle, data files are under sys._MEIPASS
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets" / "items.db"
    return Path(__file__).parent.parent / "assets" / "items.db"


DB_PATH = _db_path()


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                id              INTEGER PRIMARY KEY,
                name            TEXT NOT NULL,
                category        TEXT,
                sub_category    TEXT,
                npc_buy_price   INTEGER,
                npc_sell_price  INTEGER,
                last_synced     TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_items_name ON items(name COLLATE NOCASE);

            CREATE TABLE IF NOT EXISTS sync_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                synced_at   TEXT DEFAULT (datetime('now')),
                item_count  INTEGER
            );
        """)


def upsert_item(
    item_id: int,
    name: str,
    category: str,
    sub_category: str,
    npc_buy_price: int,
) -> None:
    # NPC sell price: game sells items to players at `price`, players sell back at ~20%.
    # Some items have no NPC buy price (price=0 or missing) — those can't be sold to NPC.
    npc_sell_price = math.floor(npc_buy_price * 0.2) if npc_buy_price > 0 else 0

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO items (id, name, category, sub_category, npc_buy_price, npc_sell_price, last_synced)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                name           = excluded.name,
                category       = excluded.category,
                sub_category   = excluded.sub_category,
                npc_buy_price  = excluded.npc_buy_price,
                npc_sell_price = excluded.npc_sell_price,
                last_synced    = excluded.last_synced
        """, (item_id, name, category, sub_category, npc_buy_price, npc_sell_price))


def record_sync(item_count: int) -> None:
    with get_conn() as conn:
        conn.execute("INSERT INTO sync_log (item_count) VALUES (?)", (item_count,))


def search_by_name(query: str, limit: int = 10) -> list[sqlite3.Row]:
    """Exact and prefix match — fast path before fuzzy matching."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM items
            WHERE name LIKE ? COLLATE NOCASE
            ORDER BY
                CASE WHEN name = ? COLLATE NOCASE THEN 0 ELSE 1 END,
                length(name)
            LIMIT ?
        """, (f"{query}%", query, limit)).fetchall()
    return rows


def get_by_id(item_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()


def get_stats() -> dict:
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        last_sync = conn.execute(
            "SELECT synced_at, item_count FROM sync_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return {
        "item_count": count,
        "last_sync": dict(last_sync) if last_sync else None,
    }


def all_names() -> list[tuple[int, str]]:
    """Return (id, name) for every item — used to build fuzzy index."""
    with get_conn() as conn:
        rows = conn.execute("SELECT id, name FROM items").fetchall()
    return [(r["id"], r["name"]) for r in rows]
