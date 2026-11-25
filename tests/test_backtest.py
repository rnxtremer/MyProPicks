"""Backtest: point-in-time data and the monthly replay of the model."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from mypropicks import backtest, fundamentals
from mypropicks.config import DEFAULTS


def _raw(ni=(1000.0, 800.0), eq=(5000.0, 4000.0), shares=100.0):
    """Two financial years (FY25, FY24) of a simple company."""
    return {
        "info": {"sharesOutstanding": shares, "sector": "Technology",
                 "targetMeanPrice": 999.0, "trailingEps": 99.0},
        "financials": {
            "Net Income Common Stockholders": {"2025-03-31": ni[0], "2024-03-31": ni[1]},
            "Net Income": {"2025-03-31": ni[0], "2024-03-31": ni[1]},
            "Total Revenue": {"2025-03-31": 10000.0, "2024-03-31": 8000.0},
        },
        "balance_sheet": {"Stockholders Equity": {"2025-03-31": eq[0], "2024-03-31": eq[1]}},
        "cashflow": {},
        "monthly_close": {"2024-03-01": 160.0, "2025-03-01": 250.0, "2025-06-01": 270.0},
    }


# ---------- point-in-time ----------

def test_as_of_hides_unpublished_results():
    """On 1 May 2025 the FY25 results (year to 31 Mar 2025) aren't out yet: only FY24 counts."""
    r = fundamentals.as_of(_raw(), date(2025, 5, 1), price=200.0)
    assert list(r["financials"]["Net Income"]) == ["2024-03-31"]
    assert list(r["balance_sheet"]["Stockholders Equity"]) == ["2024-03-31"]
    assert all(k <= "2025-05-01" for k in r["monthly_close"])
    assert r["info"]["targetMeanPrice"] is None  # no analyst history


def test_as_of_values_from_price():
    r = fundamentals.as_of(_raw(), date(2025, 7, 15), price=200.0)
    info = r["info"]
    assert info["trailingEps"] == pytest.approx(10.0)       # FY25: 1000 / 100 shares
    assert info["trailingPE"] == pytest.approx(20.0)        # 200 / 10
    assert info["bookValue"] == pytest.approx(50.0)
    assert info["priceToBook"] == pytest.approx(4.0)
    assert info["marketCap"] == pytest.approx(20000.0)
    m = fundamentals.extract_metrics(r)
    assert m["pe"] == pytest.approx(20.0) and m["rev_growth"] == pytest.approx(0.25)


# ---------- the replay ----------

def _world(n_stocks=6, months=40):
    """Daily prices: S00 rises steadily, the rest drift; equal fundamentals."""
    days = pd.bdate_range("2022-09-01", periods=months * 21)
    rng = np.random.default_rng(0)
    closes = {}
    for i in range(n_stocks):
        drift = 0.002 if i == 0 else 0.0
        closes[f"S{i:02d}"] = 100 * np.exp(np.cumsum(drift + rng.normal(0, 0.005, len(days))))
    closes = pd.DataFrame(closes, index=days)
    vols = pd.DataFrame(1e7, index=days, columns=closes.columns)
    raws = {s: _raw() for s in closes.columns}
    industries = pd.Series("IT", index=closes.columns)
    index = closes.mean(axis=1)
    return closes, vols, raws, industries, index


CFG = {**DEFAULTS, "liquidity_cr": {"nifty20": 0}}


def test_model_picks_the_strong_stock():
    """Same company results everywhere, so the steady riser wins on momentum at first."""
    closes, vols, raws, ind, index = _world()
    first = backtest.month_ends(closes.index)[-25]
    assert backtest.picks_on("nifty20", CFG, first, closes, vols, raws, ind, 1) == ["S00"]


def test_backtest_chains_monthly_returns(monkeypatch):
    closes, vols, raws, ind, index = _world()
    monkeypatch.setattr(backtest, "picks_on", lambda *a, **k: ["S00"])
    out = backtest.run_backtest("nifty20", CFG, closes, vols, raws, ind, index, months=24, n=1)
    assert list(out.columns) == ["ai", "baseline", "index"]
    assert out.iloc[0].tolist() == [100.0, 100.0, 100.0]
    assert len(out) == 25  # start point plus 24 monthly steps
    d = backtest.month_ends(closes.index)
    assert out["ai"].iloc[-1] == pytest.approx(closes.at[d[-1], "S00"] / closes.at[d[-25], "S00"] * 100, rel=1e-4)
    assert out["index"].iloc[-1] == pytest.approx(index[d[-1]] / index[d[-25]] * 100, rel=1e-4)
    every = 100.0
    for t0, t1 in zip(d[-25:-1], d[-24:]):
        every *= 1 + closes.loc[t1].div(closes.loc[t0]).sub(1).mean()
    assert out["baseline"].iloc[-1] == pytest.approx(every, rel=1e-4)


def test_missing_next_price_counts_as_cash():
    closes, vols, raws, ind, index = _world(n_stocks=2)
    month_ends = backtest.month_ends(closes.index)
    t0, t1 = month_ends[-2], month_ends[-1]
    closes.loc[closes.index > t0, "S00"] = np.nan  # S00 stops trading after t0
    r = backtest.period_return(closes, ["S00", "S01"], t0, t1)
    s01 = closes.at[t1, "S01"] / closes.at[t0, "S01"] - 1
    assert r == pytest.approx(s01 / 2)


def test_cagr():
    s = pd.Series([100.0, 121.0], index=pd.to_datetime(["2023-11-30", "2025-11-30"]))
    assert backtest.cagr(s) == pytest.approx(0.10, abs=1e-3)


def test_backtest_carries_holdings_into_the_next_month(monkeypatch):
    closes, vols, raws, ind, index = _world()
    seen = []

    def fake(*a, held=None, **k):
        seen.append(list(held or []))
        return ["S00"]
    monkeypatch.setattr(backtest, "picks_on", fake)
    backtest.run_backtest("nifty20", CFG, closes, vols, raws, ind, index, months=3, n=1)
    assert seen == [[], ["S00"], ["S00"]]


def test_backtest_lets_kept_stocks_run(monkeypatch):
    """Like you'd actually trade: stocks that stay in the list aren't trimmed back each month."""
    days = pd.bdate_range("2024-01-01", periods=70)
    a = pd.Series([100.0] * 70, index=days)
    a[days >= days[25]] = 200.0                      # A doubles in month 2, then stays flat
    b = pd.Series([100.0] * 70, index=days)
    b[days >= days[50]] = 50.0                       # B halves in month 3
    closes = pd.DataFrame({"A": a, "B": b})
    vols = pd.DataFrame(1e7, index=days, columns=closes.columns)
    index = closes.mean(axis=1)
    monkeypatch.setattr(backtest, "picks_on", lambda *a, **k: ["A", "B"])
    out = backtest.run_backtest("nifty20", CFG, closes, vols, {}, pd.Series(dtype=str), index,
                                months=3, n=2)
    # Held 50/50 and never trimmed: A ends at 100 (50 doubled), B at 25: 125 in total.
    assert out["ai"].iloc[-1] == pytest.approx(125.0)
