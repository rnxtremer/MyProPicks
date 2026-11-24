"""Equal-weight quantity suggestions."""
from __future__ import annotations

import math


def _ok(x) -> bool:
    return x is not None and isinstance(x, (int, float)) and not math.isnan(x) and x > 0


def suggest_quantities(buys: list[str], prices: dict[str, float], budget: float) -> dict[str, int]:
    if not buys:
        return {}
    if not _ok(budget):
        return {s: 0 for s in buys}
    per = budget / len(buys)
    return {s: int(math.floor(per / prices[s])) if _ok(prices.get(s)) else 0 for s in buys}
