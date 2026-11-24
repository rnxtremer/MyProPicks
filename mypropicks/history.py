"""Daily portfolio value over time, rebuilt from the trade log and closing prices."""
from __future__ import annotations

import pandas as pd


def value_over_time(trades: pd.DataFrame, portfolio: str, closes: pd.DataFrame, capital: float) -> pd.DataFrame:
    """Columns: holdings (market value), cash, total. One row per trading day from the first trade."""
    t = trades[trades["portfolio"] == portfolio].copy()
    if t.empty or closes.empty:
        return pd.DataFrame(columns=["holdings", "cash", "total"])
    t["date"] = pd.to_datetime(t["date"])
    if not capital or capital <= 0:
        # No capital set: treat the money you put in (all buys) as the starting pot.
        buys = t[t["action"] == "BUY"]
        capital = float((buys["qty"] * buys["price"]).sum())
    start = t["date"].min()
    px = closes.loc[closes.index >= start].ffill()
    if px.empty:
        return pd.DataFrame(columns=["holdings", "cash", "total"])
    sign = t["action"].map({"BUY": 1, "SELL": -1})
    t["dq"] = sign * t["qty"]
    t["dcash"] = -sign * t["qty"] * t["price"] - t["charges"]
    qty = t.pivot_table(index="date", columns="symbol", values="dq", aggfunc="sum")
    qty = qty.reindex(px.index.union(qty.index)).fillna(0).cumsum().reindex(px.index).ffill().fillna(0)
    cash = t.groupby("date")["dcash"].sum().reindex(px.index.union(t["date"].unique())).fillna(0).cumsum()
    cash = cash.reindex(px.index).ffill().fillna(0) + capital
    syms = [s for s in qty.columns if s in px.columns]
    holdings = (qty[syms] * px[syms]).sum(axis=1)
    return pd.DataFrame({"holdings": holdings, "cash": cash, "total": holdings + cash})
