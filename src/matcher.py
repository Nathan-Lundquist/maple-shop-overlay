"""
Fuzzy item name matcher between OCR output and the database.

Builds an in-memory index of all item names on first use, then uses
rapidfuzz for fast approximate string matching.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import sqlite3

try:
    from rapidfuzz import process, fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False

from . import database as db

MIN_SCORE = 70   # 0-100; below this we don't trust the match


@dataclass
class MatchResult:
    item_id: int
    name: str
    score: float            # 0-100 match confidence
    npc_buy_price: int
    npc_sell_price: int
    category: str
    sub_category: str


class ItemMatcher:
    def __init__(self) -> None:
        self._names: list[tuple[int, str]] = []   # (id, name)
        self._name_list: list[str] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._names = db.all_names()
            self._name_list = [n for _, n in self._names]
            self._loaded = True

    def invalidate(self) -> None:
        """Call after a DB sync to refresh the index."""
        self._loaded = False

    def match(self, ocr_text: str, limit: int = 3) -> list[MatchResult]:
        """
        Find the best DB items matching the OCR'd text.
        Returns up to `limit` results sorted by match score.
        """
        if not ocr_text or len(ocr_text) < 2:
            return []

        self._ensure_loaded()
        if not self._name_list:
            return []

        if _HAS_RAPIDFUZZ:
            hits = process.extract(
                ocr_text,
                self._name_list,
                scorer=fuzz.WRatio,
                limit=limit,
                score_cutoff=MIN_SCORE,
            )
        else:
            # Naive fallback: case-insensitive substring match
            query_lo = ocr_text.lower()
            hits = [
                (name, 85, i)
                for i, name in enumerate(self._name_list)
                if query_lo in name.lower()
            ][:limit]

        results: list[MatchResult] = []
        for name, score, idx in hits:
            item_id, _ = self._names[idx]
            row = db.get_by_id(item_id)
            if row is None:
                continue
            results.append(MatchResult(
                item_id=row["id"],
                name=row["name"],
                score=score,
                npc_buy_price=row["npc_buy_price"] or 0,
                npc_sell_price=row["npc_sell_price"] or 0,
                category=row["category"] or "",
                sub_category=row["sub_category"] or "",
            ))
        return results

    def best_match(self, ocr_text: str) -> Optional[MatchResult]:
        results = self.match(ocr_text, limit=1)
        return results[0] if results else None
