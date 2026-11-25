"""Fair value: a weighted average of several valuation methods, as InvestingPro describes its own."""
from __future__ import annotations

import math
import statistics

import pandas as pd


# Cash-flow and EV/EBITDA valuation don't fit lenders (debt is their raw material).
FINANCIAL_SECTORS = {"Financial Services"}


def sector_medians(metrics: pd.DataFrame) -> pd.DataFrame:
    """Median P/E, P/B and EV/EBITDA per sector, over positive values only."""
    cols = ["pe", "pb", "ev_ebitda"]
    df = metrics[["sector"] + cols].copy()
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df.loc[df[c] <= 0, c] = None
    return df.groupby("sector")[cols].median()


def _pos(x) -> bool:
    try:
        return x is not None and float(x) > 0 and x == x
    except (TypeError, ValueError):
        return False


def _dcf(m: dict, cfg: dict) -> float | None:
    fcf, shares = m.get("fcf"), m.get("shares")
    if not _pos(fcf) or not _pos(shares):
        return None
    g = m.get("fcf_cagr3")
    if g is None or g != g:
        g = m.get("rev_cagr3")
    if g is None or g != g:
        g = 0.0
    g = min(max(g, cfg["dcf_growth_min"]), cfg["dcf_growth_max"])
    r, tg, years = cfg["dcf_discount"], cfg["dcf_terminal"], cfg["dcf_years"]
    if r <= tg:
        return None
    pv, cash = 0.0, float(fcf)
    for t in range(1, years + 1):
        cash *= 1 + g
        pv += cash / (1 + r) ** t
    terminal = cash * (1 + tg) / (r - tg)
    pv += terminal / (1 + r) ** years
    nd = m.get("net_debt") or 0.0
    equity = pv - nd
    return equity / shares if equity > 0 else None


def _confidence(values: list[float]) -> str:
    """How far the methods agree: High when 3+ agree within 1.6x, Medium within 2.5x."""
    if not values:
        return "None"
    spread = max(values) / min(values)
    if len(values) >= 3 and spread <= 1.6:
        return "High"
    if len(values) >= 2 and spread <= 2.5:
        return "Medium"
    return "Low"


def fair_value(m: dict, med: dict, ltp: float, cfg: dict) -> dict:
    weights = cfg.get("weights") or {}
    methods: dict[str, float] = {}
    if _pos(m.get("eps")) and _pos(m.get("own_pe_hist")):
        methods["own_pe"] = float(m["eps"]) * float(m["own_pe_hist"])
    if _pos(m.get("bvps")) and _pos(m.get("own_pb_hist")):
        methods["own_pb"] = float(m["bvps"]) * float(m["own_pb_hist"])
    if _pos(m.get("eps")) and _pos(med.get("pe")):
        methods["sector_pe"] = float(m["eps"]) * float(med["pe"])
    if _pos(m.get("bvps")) and _pos(med.get("pb")):
        methods["sector_pb"] = float(m["bvps"]) * float(med["pb"])
    lender = m.get("sector") in FINANCIAL_SECTORS
    if not lender and _pos(m.get("ebitda")) and _pos(med.get("ev_ebitda")) and _pos(m.get("shares")):
        eq = float(med["ev_ebitda"]) * float(m["ebitda"]) - float(m.get("net_debt") or 0)
        if eq > 0:
            methods["sector_ev_ebitda"] = eq / float(m["shares"])
    if weights.get("dcf", 1) > 0:
        d = None if lender else _dcf(m, cfg)
        if d:
            methods["dcf"] = d
    if _pos(m.get("target_mean")):
        methods["analyst_target"] = float(m["target_mean"])
    methods = {k: v for k, v in methods.items() if weights.get(k, 1) > 0}

    # Drop outliers: a method more than ratio x (or under 1/ratio of) the median of all methods.
    ratio = cfg["outlier_ratio"]
    if len(methods) >= 3:
        mid = statistics.median(methods.values())
        methods = {k: v for k, v in methods.items() if mid / ratio <= v <= mid * ratio}

    confidence = _confidence(list(methods.values()))
    if not methods or not _pos(ltp):
        return {"methods": methods, "fair_value": None, "upside": None, "label": "No data",
                "n_methods": len(methods), "confidence": confidence}

    def weight(k: str) -> float:
        w = float(weights.get(k, 1))
        if k == "analyst_target" and (m.get("n_analysts") or 0) < cfg.get("analyst_min", 0):
            w = min(w, 1.0)  # a target from only a couple of analysts counts once
        return w

    # Weighted geometric mean: one very high estimate can't drag the result as far as an
    # ordinary average would.
    total = sum(weight(k) for k in methods)
    fv = math.exp(sum(weight(k) * math.log(v) for k, v in methods.items()) / total)
    upside = fv / ltp - 1
    band = cfg["band"]
    if ltp < fv * (1 - band):
        label = "Undervalued"
    elif ltp > fv * (1 + band):
        label = "Overvalued"
    else:
        label = "Fair"
    return {"methods": {k: round(v, 2) for k, v in methods.items()}, "fair_value": fv,
            "upside": upside, "label": label, "n_methods": len(methods), "confidence": confidence}
