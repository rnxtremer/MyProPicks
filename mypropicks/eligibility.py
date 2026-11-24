"""NSE index-style eligibility checks that free data allows.

NSE's own lists already apply its full formula (free-float market cap, impact cost,
F&O membership). Between NSE's six-monthly reviews, these monthly re-checks catch stocks
that have since become thin or irregularly traded.
"""
from __future__ import annotations

import pandas as pd


def check_eligibility(
    closes: pd.DataFrame,
    volumes: pd.DataFrame,
    shares: dict[str, float],
    liquidity_cr: float,
    min_history: int = 250,
    traded_window: int = 126,
    liquidity_window: int = 63,
) -> pd.DataFrame:
    rows = {}
    for sym in closes.columns:
        c = closes[sym]
        v = volumes[sym] if sym in volumes else pd.Series(dtype=float)
        avg_mcap = None
        sh = shares.get(sym)
        last_c = c.tail(traded_window)
        if sh and last_c.notna().any():
            avg_mcap = float(sh * last_c.mean())
        if c.notna().sum() < min_history:
            reason = "short history"
        else:
            tail_v = v.reindex(last_c.index)
            if last_c.isna().any() or tail_v.isna().any() or (tail_v <= 0).any():
                reason = "not traded every day"
            else:
                tv = (c * v).tail(liquidity_window).median()
                reason = "low liquidity" if tv < liquidity_cr * 1e7 else ""
        rows[sym] = {"eligible": reason == "", "reason": reason, "avg_mcap_6m": avg_mcap}
    return pd.DataFrame.from_dict(rows, orient="index",
                                  columns=["eligible", "reason", "avg_mcap_6m"])
