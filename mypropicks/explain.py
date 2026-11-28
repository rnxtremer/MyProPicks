"""Short, concrete reasons for the review's buys and sells, quoting the numbers behind them.

Category scores are 0-100 percentiles within the index (higher is better). A buy is explained by
the hard numbers behind its strongest categories plus its gap to fair value. A sell is explained
by what changed since last month (fair value, price trend, overall score), or, with no earlier
review, by its weakest numbers.
"""
from __future__ import annotations

import pandas as pd

CATS = ["profitability", "growth", "cash_flow", "relative_value", "momentum"]
INELIGIBLE = {"low liquidity": "too little trading volume", "no price data": "no recent price data"}


def _num(row: pd.Series | None, col: str) -> float | None:
    if row is None:
        return None
    v = row.get(col)
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if v != v else v


def _pct(x: float) -> str:
    return f"{x:+.0%}"


def _cap(text: str) -> str:
    return text[0].upper() + text[1:] if text else text


# ---- the numbers behind each category ----
def _strength(cat: str, r: pd.Series) -> str | None:
    g = lambda c: _num(r, c)  # noqa: E731
    if cat == "profitability":
        roe, om = g("roe"), g("op_margin")
        bits = []
        if roe is not None:
            bits.append(f"ROE {roe:.0%}")
        if om is not None:
            bits.append(f"{om:.0%} operating margin")
        return ", ".join(bits) or None
    if cat == "growth":
        rv, eps = g("rev_growth"), g("eps_growth")
        bits = []
        if rv is not None:
            bits.append(f"sales {_pct(rv)}")
        if eps is not None:
            bits.append(f"EPS {_pct(eps)}")
        return (", ".join(bits) + " last year") if bits else None
    if cat == "cash_flow":
        fy, ocf = g("fcf_yield"), g("ocf_to_np")
        if fy is not None and fy >= 0.03:
            return f"free cash flow yield {fy:.1%}"
        if ocf is not None and ocf >= 1:
            return f"cash earnings {ocf:.1f}× profit"
        return None
    if cat == "relative_value":
        pe, pb = g("pe"), g("pb")
        if pe is not None and pe > 0:
            return f"cheap at P/E {pe:.1f}"
        return f"cheap at P/B {pb:.1f}" if pb is not None else None
    if cat == "momentum":
        m6, v200 = g("mom_6"), g("vs_200dma")
        if m6 is not None and m6 >= 0.05:
            return f"price up {m6:.0%} in 6 months"
        if v200 is not None and v200 > 0 and (m6 or 0) > 0:
            return "price rising, above its 200-day average"
        return None
    return None


def _weakness(cat: str, r: pd.Series) -> str | None:
    g = lambda c: _num(r, c)  # noqa: E731
    if cat == "profitability" and g("roe") is not None:
        return f"low ROE ({g('roe'):.0%})"
    if cat == "growth" and g("eps_growth") is not None:
        return f"EPS {_pct(g('eps_growth'))} last year"
    if cat == "cash_flow" and g("ocf_to_np") is not None:
        return f"cash earnings only {g('ocf_to_np'):.1f}× profit"
    if cat == "relative_value" and g("pe") is not None and g("pe") > 0:
        return f"expensive at P/E {g('pe'):.0f}"
    if cat == "momentum" and g("mom_6") is not None:
        return f"price {_pct(g('mom_6'))} in 6 months"
    return None


def _fair_value_now(r: pd.Series) -> str | None:
    up, fv = _num(r, "upside"), _num(r, "fair_value")
    if up is None or fv is None:
        return None
    if up >= 0.05:
        return f"{up:.0%} below fair value (₹{fv:,.0f})"
    if up > -0.05:
        return f"price now at fair value (₹{fv:,.0f})"
    return f"price now {-up:.0%} above fair value (₹{fv:,.0f})"


def buy_reason(row: pd.Series, prev: pd.Series | None = None) -> str:
    scores = {c: _num(row, c) for c in CATS}
    ranked = sorted((c for c in CATS if scores[c] is not None), key=lambda c: -scores[c])
    cheap = (_num(row, "upside") or 0) >= 0.05
    parts = []
    for c in ranked:
        if len(parts) == (1 if cheap else 2) or scores[c] < 55:
            break
        if c == "relative_value" and cheap:
            continue                      # the fair-value gap says it better
        s = _strength(c, row)
        if s:
            parts.append(s)
    if cheap:
        parts.append(_fair_value_now(row))
    return _cap("; ".join(parts)) or "Strong all-round scores"


def sell_reason(row: pd.Series | None, prev: pd.Series | None = None, old: str = "") -> str:
    old = str(old or "")
    if old.startswith("left universe"):
        return "Left the index"
    if old.startswith("ineligible"):
        why = old.split(":", 1)[-1].strip()
        return f"No longer qualifies: {INELIGIBLE.get(why, why)}"
    if row is None:
        return "Other stocks now score higher"
    parts = []
    up, pup = _num(row, "upside"), _num(prev, "upside")
    fv, pfv = _num(row, "fair_value"), _num(prev, "fair_value")
    if up is not None and pup is not None and pup - up >= 0.10 and fv and pfv:
        where = (f"upside {up:.0%}, was {pup:.0%}" if up >= 0.05
                 else "price now at it" if up > -0.05 else f"price now {-up:.0%} above it")
        parts.append(f"fair value cut to ₹{fv:,.0f} from ₹{pfv:,.0f} ({where})")
    elif up is not None and up < 0.05:
        parts.append(_fair_value_now(row))
    m6, pm6 = _num(row, "mom_6"), _num(prev, "mom_6")
    if m6 is not None and pm6 is not None and pm6 - m6 >= 0.05:
        parts.append(f"6-month return slipped to {_pct(m6)}")
    if not parts:                          # no change to point at: name the weakest numbers
        scores = {c: _num(row, c) for c in CATS}
        for c in sorted((c for c in CATS if scores[c] is not None), key=lambda c: scores[c])[:2]:
            w = _weakness(c, row)
            if w and scores[c] < 45:
                parts.append(w)
    if not parts:
        parts.append("other stocks now score higher")
    parts = [p for p in parts if p][:2]
    sc, psc = _num(row, "score"), _num(prev, "score")
    if sc is not None and psc is not None and psc - sc >= 0.5:
        parts.append(f"score {psc:.0f} → {sc:.0f}")
    elif len(parts) < 2 and "other stocks now score higher" not in parts:
        parts.append("other stocks now score higher")
    return _cap("; ".join(parts))


def reason(action: str, symbol: str, table: pd.DataFrame, prev: pd.DataFrame | None = None,
           old: str = "") -> str:
    """Reason for one change. `table` and `prev` are rankings indexed by symbol."""
    row = table.loc[symbol] if symbol in table.index else None
    p = prev.loc[symbol] if prev is not None and symbol in prev.index else None
    if action == "BUY":
        return buy_reason(row, p) if row is not None else "New pick"
    return sell_reason(row, p, old)
