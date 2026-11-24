"""ProPicks-style ranking: five Financial Health categories, each a percentile average."""
from __future__ import annotations

import numpy as np
import pandas as pd

CATEGORIES: dict[str, list[tuple[str, bool]]] = {
    # (metric, higher_is_better)
    "profitability": [("roe", True), ("roce", True), ("op_margin", True), ("net_margin", True)],
    "growth": [("rev_cagr3", True), ("rev_growth", True), ("eps_growth", True), ("op_profit_growth", True)],
    "cash_flow": [("ocf_to_np", True), ("fcf_yield", True), ("debt_equity", False), ("interest_cover", True)],
    "relative_value": [("upside", True), ("pe_rel", False), ("pb_rel", False)],
    "momentum": [("mom_12_1", True), ("mom_6", True), ("vs_200dma", True), ("vol_1y", False)],
}
ALL_METRICS = [m for ms in CATEGORIES.values() for m, _ in ms]


def momentum_metrics(closes: pd.DataFrame) -> pd.DataFrame:
    rows = {}
    for sym in closes.columns:
        c = closes[sym].dropna()
        r = {"mom_12_1": np.nan, "mom_6": np.nan, "vs_200dma": np.nan, "vol_1y": np.nan}
        if len(c) >= 252:
            r["mom_12_1"] = c.iloc[-21] / c.iloc[-252] - 1
            r["vol_1y"] = c.pct_change().tail(252).std() * np.sqrt(252)
        if len(c) >= 126:
            r["mom_6"] = c.iloc[-1] / c.iloc[-126] - 1
        if len(c) >= 200:
            r["vs_200dma"] = c.iloc[-1] / c.tail(200).mean() - 1
        rows[sym] = r
    return pd.DataFrame.from_dict(rows, orient="index")


def _pct(s: pd.Series, higher_better: bool) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    return s.rank(pct=True, ascending=higher_better) * 100


def _relative(metrics: pd.DataFrame, col: str) -> tuple[pd.Series, pd.Series]:
    """Value divided by its sector median (positive values only); also a loss/negative mask."""
    v = pd.to_numeric(metrics[col], errors="coerce")
    neg = v <= 0
    pos = v.where(v > 0)
    med = pos.groupby(metrics["sector"].fillna("Unknown")).transform("median")
    return pos / med, neg


def score_universe(metrics: pd.DataFrame, eligibility: pd.DataFrame, weights: dict,
                   low_data_threshold: float = 0.60) -> pd.DataFrame:
    df = metrics.copy()
    if "sector" not in df:
        df["sector"] = "Unknown"
    df["pe_rel"], pe_neg = _relative(df, "pe")
    df["pb_rel"], pb_neg = _relative(df, "pb")
    # Yahoo usually leaves P/E blank for loss-makers, so also go by EPS and book value.
    if "eps" in df:
        pe_neg = pe_neg | (pd.to_numeric(df["eps"], errors="coerce") <= 0)
    if "bvps" in df:
        pb_neg = pb_neg | (pd.to_numeric(df["bvps"], errors="coerce") <= 0)

    pcts = pd.DataFrame(index=df.index)
    for _, ms in CATEGORIES.items():
        for m, hb in ms:
            col = df[m] if m in df else pd.Series(np.nan, index=df.index)
            pcts[m] = _pct(col, hb)
    # Loss-makers (negative P/E or P/B) count as the worst in the universe on those metrics.
    pcts.loc[pe_neg, "pe_rel"] = 0.0
    pcts.loc[pb_neg, "pb_rel"] = 0.0

    out = pd.DataFrame(index=df.index)
    for cat, ms in CATEGORIES.items():
        out[cat] = pcts[[m for m, _ in ms]].mean(axis=1, skipna=True)

    w = pd.Series(weights, dtype=float).reindex(list(CATEGORIES)).fillna(0)
    cats = out[list(CATEGORIES)]
    avail = cats.notna().astype(float).mul(w, axis=1)
    out["score"] = (cats.fillna(0).mul(w, axis=1).sum(axis=1) / avail.sum(axis=1)).where(avail.sum(axis=1) > 0)
    out["health"] = (out["score"] / 20).round(1)
    out["data_coverage"] = pcts.notna().sum(axis=1) / len(ALL_METRICS)
    out["low_data"] = out["data_coverage"] < low_data_threshold

    el = eligibility.reindex(df.index)
    out["eligible"] = el["eligible"].fillna(False).astype(bool)
    out["reason"] = el["reason"].fillna("no price data")
    out["avg_mcap_6m"] = pd.to_numeric(el["avg_mcap_6m"], errors="coerce")

    order = out.assign(_s=out["score"].fillna(-1), _m=out["momentum"].fillna(-1),
                       _c=out["avg_mcap_6m"].fillna(0))
    order = order.sort_values(["eligible", "_s", "_m", "_c"], ascending=[False, False, False, False])
    out["rank"] = pd.Series(range(1, len(order) + 1), index=order.index)
    return out.sort_values("rank")
