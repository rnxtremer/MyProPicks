"""Short, plain-English reasons for the review's buys and sells, from the category scores.

Scores are 0-100 percentiles within the index (higher is better). A buy is explained by its
strongest categories and its gap to fair value; a sell by what weakened since last month (or,
with no earlier review, by its weakest categories).
"""
from __future__ import annotations

import pandas as pd

CATS = ["profitability", "growth", "cash_flow", "relative_value", "momentum"]
STRONG = {"profitability": "highly profitable", "growth": "growing fast", "cash_flow": "strong cash flow",
          "relative_value": "attractively priced", "momentum": "strong price trend"}
IMPROVED = {"profitability": "profits improved", "growth": "growth picked up",
            "cash_flow": "cash flow improved", "relative_value": "valuation improved",
            "momentum": "price trend picked up"}
WEAKENED = {"profitability": "profits weakened", "growth": "growth slowed", "cash_flow": "cash flow weakened",
            "relative_value": "got pricier vs peers", "momentum": "price trend weakened"}
WEAK = {"profitability": "low profitability", "growth": "weak growth", "cash_flow": "weak cash flow",
        "relative_value": "looks expensive", "momentum": "weak price trend"}
INELIGIBLE = {"low liquidity": "too little trading volume", "no price data": "no recent price data"}


def _num(row: pd.Series, col: str) -> float | None:
    v = row.get(col)
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if v != v else v


def _join(parts: list[str]) -> str:
    parts = [p for p in parts if p]
    if not parts:
        return ""
    text = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + "; " + parts[-1]
    return text[0].upper() + text[1:]


def _changes(row: pd.Series, prev: pd.Series | None) -> dict[str, float]:
    if prev is None:
        return {}
    out = {}
    for c in CATS:
        a, b = _num(prev, c), _num(row, c)
        if a is not None and b is not None:
            out[c] = b - a
    return out


def buy_reason(row: pd.Series, prev: pd.Series | None = None) -> str:
    scores = {c: _num(row, c) for c in CATS}
    best = sorted((c for c in CATS if scores[c] is not None and scores[c] >= 60),
                  key=lambda c: -scores[c])[:2]
    parts = [STRONG[c] for c in best]
    up = _num(row, "upside")
    if up is not None and up >= 0.10 and "relative_value" not in best:
        parts.append(f"{up:.0%} below fair value")
    rises = [c for c, d in sorted(_changes(row, prev).items(), key=lambda kv: -kv[1]) if d >= 5 and c not in best]
    if rises and len(parts) < 3:
        parts.append(IMPROVED[rises[0]])
    return _join(parts[:3]) or "Strong all-round scores"


def sell_reason(row: pd.Series | None, prev: pd.Series | None = None, old: str = "") -> str:
    old = str(old or "")
    if old.startswith("left universe"):
        return "Left the index"
    if old.startswith("ineligible"):
        why = old.split(":", 1)[-1].strip()
        return f"No longer qualifies: {INELIGIBLE.get(why, why)}"
    if row is None:
        return "Overtaken by stronger stocks"
    falls = [c for c, d in sorted(_changes(row, prev).items(), key=lambda kv: kv[1]) if d <= -3]
    parts = [WEAKENED[c] for c in falls[:2]]
    if not parts:
        scores = {c: _num(row, c) for c in CATS}
        parts = [WEAK[c] for c in sorted((c for c in CATS if scores[c] is not None and scores[c] < 40),
                                         key=lambda c: scores[c])[:2]]
    up = _num(row, "upside")
    if up is not None and up <= 0.05:
        parts.append("near fair value" if up > -0.05 else "above fair value")
    if len(parts) < 2:
        parts.append("overtaken by stronger stocks")
    return _join(parts[:3])


def reason(action: str, symbol: str, table: pd.DataFrame, prev: pd.DataFrame | None = None,
           old: str = "") -> str:
    """Reason for one change. `table` and `prev` are rankings indexed by symbol."""
    row = table.loc[symbol] if symbol in table.index else None
    p = prev.loc[symbol] if prev is not None and symbol in prev.index else None
    if action == "BUY":
        return buy_reason(row, p) if row is not None else "New pick"
    return sell_reason(row, p, old)
