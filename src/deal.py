"""
Deal rating logic — compares shop prices against NPC reference prices.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from .matcher import MatchResult


class DealRating(Enum):
    FLIP      = "FLIP"      # Below NPC sell price → buy here, sell to NPC for profit
    GREAT     = "GREAT"     # Below 60% of NPC buy price
    GOOD      = "GOOD"      # 60–90% of NPC buy price
    FAIR      = "FAIR"      # 90–110% of NPC buy price (roughly NPC price)
    OVERPRICED = "OVERPRICED"  # Above NPC buy price
    UNKNOWN   = "UNKNOWN"   # No NPC price data


# Color codes for the overlay UI (tkinter color strings)
RATING_COLORS = {
    DealRating.FLIP:       "#00ff88",   # bright green
    DealRating.GREAT:      "#55dd55",   # green
    DealRating.GOOD:       "#aaddaa",   # light green
    DealRating.FAIR:       "#dddddd",   # grey
    DealRating.OVERPRICED: "#ff6666",   # red
    DealRating.UNKNOWN:    "#888888",   # dark grey
}

RATING_LABELS = {
    DealRating.FLIP:       "FLIP $$",
    DealRating.GREAT:      "GREAT",
    DealRating.GOOD:       "GOOD",
    DealRating.FAIR:       "FAIR",
    DealRating.OVERPRICED: "NOPE",
    DealRating.UNKNOWN:    "?",
}


@dataclass
class DealResult:
    rating: DealRating
    shop_price: int
    npc_buy_price: int
    npc_sell_price: int
    savings: int            # how much cheaper than NPC buy price (can be negative)
    flip_profit: int        # profit if you buy here + sell to NPC (can be negative)
    color: str
    label: str


def rate_deal(shop_price: int, match: Optional[MatchResult]) -> DealResult:
    """
    Given a shop price and the best DB match for the item, return a DealResult.
    """
    if match is None or match.npc_buy_price == 0:
        return DealResult(
            rating=DealRating.UNKNOWN,
            shop_price=shop_price,
            npc_buy_price=0,
            npc_sell_price=0,
            savings=0,
            flip_profit=0,
            color=RATING_COLORS[DealRating.UNKNOWN],
            label=RATING_LABELS[DealRating.UNKNOWN],
        )

    npc_buy  = match.npc_buy_price
    npc_sell = match.npc_sell_price
    savings  = npc_buy - shop_price
    flip_profit = npc_sell - shop_price

    ratio = shop_price / npc_buy  # 0 = free, 1.0 = exactly NPC price, >1 = overpriced

    if shop_price <= npc_sell:
        rating = DealRating.FLIP
    elif ratio < 0.6:
        rating = DealRating.GREAT
    elif ratio < 0.90:
        rating = DealRating.GOOD
    elif ratio <= 1.10:
        rating = DealRating.FAIR
    else:
        rating = DealRating.OVERPRICED

    return DealResult(
        rating=rating,
        shop_price=shop_price,
        npc_buy_price=npc_buy,
        npc_sell_price=npc_sell,
        savings=savings,
        flip_profit=flip_profit,
        color=RATING_COLORS[rating],
        label=RATING_LABELS[rating],
    )
