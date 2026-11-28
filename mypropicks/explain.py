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


# ---- what changed between two reviews ----
# (column, name, threshold, kind, higher_is_good). kind "rel" compares ratios, "abs" differences.
DRIVERS = [
    ("pe", "P/E", 0.05, "rel", False),
    ("pb", "P/B", 0.05, "rel", False),
    ("roe", "ROE", 0.02, "abs", True),
    ("op_margin", "operating margin", 0.02, "abs", True),
    ("rev_growth", "sales growth", 0.05, "abs", True),
    ("eps_growth", "EPS growth", 0.10, "abs", True),
    ("fcf_yield", "free cash flow yield", 0.01, "abs", True),
    ("debt_equity", "debt/equity", 0.15, "rel", False),
    ("mom_6", "6-month return", 0.05, "abs", True),
]
PCT = {"roe", "op_margin", "rev_growth", "eps_growth", "fcf_yield", "mom_6"}
CAT_OF = {"pe": "relative_value", "pb": "relative_value", "roe": "profitability", "op_margin": "profitability",
          "rev_growth": "growth", "eps_growth": "growth", "fcf_yield": "cash_flow", "debt_equity": "cash_flow",
          "mom_6": "momentum"}


def _fmt(col: str, v: float) -> str:
    if col in ("rev_growth", "eps_growth", "mom_6"):
        return _pct(v)
    if col in PCT:
        return f"{v:.0%}" if col != "fcf_yield" else f"{v:.1%}"
    return f"{v:.1f}"


def _drivers(row: pd.Series, prev: pd.Series | None) -> list[dict]:
    """Every meaningful change since the previous review, with its size (1 = just over the
    threshold) and whether it is good for the stock (None = depends: a price move)."""
    if prev is None:
        return []
    out = []
    for col, name, thr, kind, up_good in DRIVERS:
        a, b = _num(prev, col), _num(row, col)
        if a is None or b is None:
            continue
        if kind == "rel":
            if a <= 0 or b <= 0:
                continue
            ch = b / a - 1
        else:
            ch = b - a
        if abs(ch) < thr:
            continue
        verb = "up" if ch > 0 else "down"
        if col in ("rev_growth", "eps_growth"):
            verb = "picked up" if ch > 0 else "slowed"
        out.append({"size": abs(ch) / thr, "good": (ch > 0) == up_good, "cat": CAT_OF[col],
                    "text": f"{name} {verb} {_fmt(col, a)} → {_fmt(col, b)}"})
    fv, pfv, up, pup = _num(row, "fair_value"), _num(prev, "fair_value"), _num(row, "upside"), _num(prev, "upside")
    if fv and pfv and abs(fv / pfv - 1) >= 0.10:
        cut = fv < pfv
        where = ("" if up is None else f" (upside now {up:.0%})" if up >= 0.05
                 else " (price now at it)" if up > -0.05 else f" (price now {-up:.0%} above it)")
        out.append({"size": abs(fv / pfv - 1) / 0.10, "good": not cut, "cat": "relative_value",
                    "text": f"fair value {'cut' if cut else 'raised'} ₹{pfv:,.0f} → ₹{fv:,.0f}{where}"})
    px, ppx = _num(row, "ltp"), _num(prev, "ltp")
    if px and ppx and abs(px / ppx - 1) >= 0.05:
        ch = px / ppx - 1
        out.append({"size": abs(ch) / 0.05, "good": None, "move": ch, "cat": "momentum",
                    "text": f"price {'up' if ch > 0 else 'down'} {abs(ch):.0%} to ₹{px:,.0f}"})
    v, pv = _num(row, "vs_200dma"), _num(prev, "vs_200dma")
    if v is not None and pv is not None and (v > 0) != (pv > 0):
        out.append({"size": 1.5, "good": v > 0, "cat": "momentum",
                    "text": "price rose above its 200-day average" if v > 0
                    else "price dropped below its 200-day average"})
    return sorted(out, key=lambda d: -d["size"])


def buy_reason(row: pd.Series, prev: pd.Series | None = None) -> str:
    """The biggest improvement since last month (if any), the stock's strongest fact, and its
    gap to fair value."""
    parts = []
    cheap = (_num(row, "upside") or 0) >= 0.05
    good = [d for d in _drivers(row, prev) if (d["good"] or (d["good"] is None and d["move"] < 0))
            and (cheap or "fair value" not in d["text"])]   # a raised fair value only helps if below it
    used = set()
    if good:
        d = good[0]
        parts.append(d["text"] + (", now cheaper" if d["good"] is None else ""))
        used.add(d["cat"])
    scores = {c: _num(row, c) for c in CATS}
    ranked = sorted((c for c in CATS if scores[c] is not None), key=lambda c: -scores[c])
    fv_said = any("fair value" in p for p in parts)
    room = 2 - len(parts) - (1 if cheap and not fv_said else 0)
    for c in ranked:
        if room <= 0 or scores[c] < 55:
            break
        if (c == "relative_value" and cheap) or c in used:
            continue                      # already said by the fair-value gap or the change above
        st = _strength(c, row)
        if st:
            parts.append(st)
            room -= 1
    if cheap and len(parts) < 2 and not any("fair value" in p for p in parts):
        parts.append(_fair_value_now(row))
    return _cap("; ".join(parts[:2])) or "Strong all-round scores"


def sell_reason(row: pd.Series | None, prev: pd.Series | None = None, old: str = "") -> str:
    """The biggest changes for the worse since last month (P/E, ROE, margins, growth, fair value,
    price...), then how the overall score moved. With no earlier review: the weakest numbers."""
    old = str(old or "")
    if old.startswith("left universe"):
        return "Left the index"
    if old.startswith("ineligible"):
        why = old.split(":", 1)[-1].strip()
        return f"No longer qualifies: {INELIGIBLE.get(why, why)}"
    if row is None:
        return "Other stocks now score higher"
    parts = []
    for d in _drivers(row, prev):
        if d["good"] is False:
            parts.append(d["text"])
        elif d["good"] is None:
            parts.append(d["text"] + (", now pricier" if d["move"] > 0 else ""))
        if len(parts) == 2:
            break
    up = _num(row, "upside")
    if len(parts) < 2 and up is not None and up < 0.05 and not any("fair value" in p for p in parts):
        parts.append(_fair_value_now(row))
    if not parts:                          # nothing changed much: name the weakest numbers
        scores = {c: _num(row, c) for c in CATS}
        for c in sorted((c for c in CATS if scores[c] is not None), key=lambda c: scores[c])[:2]:
            w = _weakness(c, row)
            if w and scores[c] < 45:
                parts.append(w)
    parts = [p for p in parts if p][:2]
    sc, psc = _num(row, "score"), _num(prev, "score")
    if sc is not None and psc is not None and psc - sc >= 0.5:
        parts.append(f"score {psc:.0f} → {sc:.0f}")
    elif len(parts) < 2:
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
