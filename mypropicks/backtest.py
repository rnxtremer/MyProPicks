"""Backtest: how the model's picks would have done over the last few years.

At each month-end the model ranks today's index members using only what it could have known
then (prices up to that day, annual results published by then, no analyst targets), buys the
top N in equal amounts. Each month after that it trades as the app tells you to: sells stocks
that fell below the holding buffer, splits that money equally across the new picks, and leaves
the stocks that stay untouched. The result is compared with the
portfolio's index, both starting at 100, and with a fair yardstick: every one of today's index
members held in equal amounts, rebalanced monthly. That yardstick shares the backtest's built-in
advantages (today's members only, equal weights, dividends), so the gap between it and the AI is
what the AI's choices really added.

Known limits, shown on the dashboard: it uses today's index members (stocks that dropped out
are missing, which flatters the result), it ignores costs and taxes, and stock prices include
dividends while the indices don't.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd

from . import fundamentals, prices, universe
from .config import BENCHMARKS, PORTFOLIOS, data_dir
from .review import decide_changes, keep_within, rank_universe

Progress = Callable[[str, float], None]
HISTORY_MONTHS = 50  # 3 years of tests plus a year of history for the first one


def month_ends(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """The last trading day of each month in the index (the newest month may be partial)."""
    s = pd.Series(index, index=index)
    return s.groupby([index.year, index.month]).max().tolist()


def period_return(closes: pd.DataFrame, picks: list[str], start, end) -> float:
    """Equal-weight return from one month-end to the next. A stock with no price at the end
    (stopped trading) counts as 0%, as if it had been sold for cash at the start."""
    if not picks:
        return 0.0
    a, b = closes.loc[start, picks], closes.loc[:end, picks].ffill().iloc[-1]
    stopped = closes.loc[(closes.index > start) & (closes.index <= end), picks].isna().all()
    r = (b / a - 1).where(~stopped & a.notna(), 0.0).fillna(0.0)
    return float(r.mean())


def picks_on(portfolio: str, cfg: dict, when, closes: pd.DataFrame, vols: pd.DataFrame,
             raws: dict[str, dict], industries: pd.Series, n: int,
             held: list[str] | None = None) -> list[str]:
    """The list the model would have held on `when`, from data available then: the top N, with
    stocks already held kept while they stay within the buffer, as the live review does."""
    c, v = closes.loc[:when], vols.loc[:when]
    price = c.ffill().iloc[-1]
    syms = [s for s in c.columns if pd.notna(price.get(s))]  # not listed yet: skip
    rows = {}
    for s in syms:
        raw = raws.get(s)
        rows[s] = fundamentals.extract_metrics(fundamentals.as_of(raw, when, float(price[s]))) if raw else {}
    metrics = pd.DataFrame.from_dict(rows, orient="index").reindex(syms)
    expected = list(fundamentals.extract_metrics({}).keys())
    metrics = metrics.reindex(columns=list(dict.fromkeys(list(metrics.columns) + expected)))
    metrics["yahoo_sector"] = metrics["sector"]
    metrics["sector"] = industries.reindex(syms)
    table = rank_universe(metrics, c[syms], v[syms], cfg, portfolio)
    return decide_changes(table, held or [], n, keep_within(cfg, portfolio))["new_list"]


def run_backtest(portfolio: str, cfg: dict, closes: pd.DataFrame, vols: pd.DataFrame,
                 raws: dict[str, dict], industries: pd.Series, index: pd.Series,
                 months: int = 36, n: int | None = None,
                 progress: Progress | None = None) -> pd.DataFrame:
    """Columns `ai`, `baseline` (all members, equal weight) and `index`, one row per month-end,
    all starting at 100."""
    n = n or PORTFOLIOS[portfolio]["n"]
    dates = month_ends(closes.index)[-(months + 1):]
    idx = index.sort_index().ffill()
    every, rows, held = 100.0, [], []
    pos: dict[str, float] = {}        # rupees in each AI holding
    cash = 100.0
    base = float(idx.asof(dates[0]))
    rows.append({"date": dates[0], "ai": 100.0, "baseline": 100.0, "index": 100.0})
    for i, (t0, t1) in enumerate(zip(dates[:-1], dates[1:])):
        if progress:
            progress(f"{PORTFOLIOS[portfolio]['label']}: backtest {t0.date()}", i / (len(dates) - 1))
        picks = picks_on(portfolio, cfg, t0, closes, vols, raws, industries, n, held=held)
        held = picks
        # Trade as the app tells you to: sell what left the list, split the money equally across
        # the new buys, and leave the stocks that stay untouched (no monthly trimming).
        for s in [s for s in pos if s not in picks]:
            cash += pos.pop(s)
        buys = [s for s in picks if s not in pos and pd.notna(closes.at[t0, s])]
        for s in buys:
            pos[s] = cash / len(buys)
        if buys:
            cash = 0.0
        for s in pos:
            pos[s] *= 1 + period_return(closes, [s], t0, t1)
        listed = [s for s in closes.columns if pd.notna(closes.at[t0, s])]
        every *= 1 + period_return(closes, listed, t0, t1)  # an index fund rebalances
        ai = cash + sum(pos.values())
        rows.append({"date": t1, "ai": round(ai, 4), "baseline": round(every, 4),
                     "index": round(float(idx.asof(t1)) / base * 100, 4)})
    return pd.DataFrame(rows).set_index("date")


def cagr(series: pd.Series) -> float | None:
    """Yearly growth rate between the first and last values of a dated series."""
    s = series.dropna()
    if len(s) < 2 or s.iloc[0] <= 0:
        return None
    years = (s.index[-1] - s.index[0]).days / 365.25
    return (s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1 if years > 0 else None


def result_file(portfolio: str) -> Path:
    return data_dir() / "backtest" / f"{portfolio}.csv"


def build(portfolio: str, cfg: dict, progress: Progress | None = None, months: int = 36) -> Path:
    """Fetch the data, run the backtest and save it to data/backtest/<portfolio>.csv."""
    uni = universe.fetch_universe(portfolio).drop_duplicates("symbol").set_index("symbol")
    syms = uni.index.tolist()
    closes, vols, _ = prices.get_prices(syms, months=HISTORY_MONTHS, cache="prices_long",
                                        max_age_s=20 * 86400)
    raws = {s: fundamentals.get_fundamentals(s) for s in closes.columns}
    start = (closes.index[0] if len(closes) else pd.Timestamp(date.today())).date().isoformat()
    index = prices.index_history(BENCHMARKS[portfolio], start)
    if index.empty:
        raise ValueError(f"No history for the index {BENCHMARKS[portfolio]}.")
    out = run_backtest(portfolio, cfg, closes, vols, {s: r for s, r in raws.items() if r},
                       uni["industry"], index, months=months, progress=progress)
    f = result_file(portfolio)
    f.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(f)
    return f
