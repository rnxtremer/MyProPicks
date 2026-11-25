"""Regression tests for the final-review findings."""
from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from mypropicks import fundamentals, ledger, prices, review
from mypropicks.config import DEFAULTS
from mypropicks.eligibility import check_eligibility
from mypropicks.fairvalue import fair_value
from mypropicks.history import value_over_time
from mypropicks.review import decide_changes
from mypropicks.scoring import score_universe
from mypropicks.sizing import suggest_quantities
from tests.test_model import BAD, GOOD, _elig, _metrics
from tests.test_review import _install_fakes, _ranked


# Critical 1: a held stock with no price must not crash the review, and is kept, not sold.
def test_held_stock_without_price_is_kept():
    ranked = _ranked(40)
    ranked.loc["S05", ["eligible", "reason"]] = [False, "no price data"]
    held = [f"S{i:02d}" for i in range(20)]
    r = decide_changes(ranked, held, 20)
    assert "S05" in r["keep"] and all(s != "S05" for s, _ in r["sell"])
    assert len(r["new_list"]) == 20
    assert any("S05" in w and "price" in w for w in r["warnings"])


def test_sizing_ignores_nan():
    assert suggest_quantities(["A", "B"], {"A": float("nan"), "B": 100}, 1000) == {"A": 0, "B": 5}
    assert suggest_quantities(["A"], {"A": 100}, float("nan")) == {"A": 0}


def test_review_survives_held_stock_fetch_failure(tmp_data, monkeypatch):
    _install_fakes(monkeypatch, failing=("S05",))
    for s in ["S05"] + [f"S{i:02d}" for i in range(10, 29)]:
        ledger.append_trade("2026-11-02", "nifty20", s, "BUY", 1, 100)
    out = review.run_review(as_of=date(2026, 12, 1), portfolios=["nifty20"])
    assert len(pd.read_csv(out / "list_nifty20.csv")) == 20
    table = pd.read_csv(out / "rankings_nifty20.csv", index_col=0)
    rows, warnings = review.personal_changes(table, ledger.load_trades(), "nifty20", 0)
    assert "S05" not in [r["symbol"] for r in rows if r["action"] == "SELL"]
    assert any("S05" in w and "price" in w for w in warnings)


# Important 2: outlier rule must not wipe out every method.
def test_outlier_rule_keeps_majority():
    r = fair_value({"eps": 10, "bvps": 55, "target_mean": 1000}, {"pe": 10, "pb": 2}, 100,
                   DEFAULTS["fair_value"])
    assert set(r["methods"]) == {"sector_pe", "sector_pb"}
    assert r["fair_value"] == pytest.approx((100 * 110) ** 0.5)


# Important 3: one symbol with an extra newest day must not make everyone ineligible.
def test_ragged_last_day_trimmed(tmp_data, monkeypatch):
    def fake(sym, months):
        n = 301 if sym == "NEW" else 300
        idx = pd.bdate_range("2025-01-01", periods=n)
        return pd.DataFrame({"Close": np.linspace(100, 200, n), "Volume": 1e6}, index=idx)

    monkeypatch.setattr(prices, "_download_one", fake)
    closes, vols, _ = prices.get_prices(["A", "B", "C", "NEW"])
    e = check_eligibility(closes, vols, {}, liquidity_cr=2)
    assert e["eligible"].all()


# Partial-day bar: before 15:45 IST, today's bar is dropped.
def test_partial_today_bar_dropped(tmp_data, monkeypatch):
    today = pd.Timestamp("2026-12-01")

    def fake(sym, months):
        idx = pd.bdate_range(end=today, periods=300)
        return pd.DataFrame({"Close": np.linspace(100, 200, 300), "Volume": 1e6}, index=idx)

    monkeypatch.setattr(prices, "_download_one", fake)
    monkeypatch.setattr(prices, "_now_ist", lambda: datetime(2026, 12, 1, 11, 0))
    closes, _, _ = prices.get_prices(["A"])
    assert closes.index[-1] < today


# Important 4: loss-makers with no P/E from Yahoo still count as worst on P/E.
def test_loss_maker_without_pe_is_worst():
    lm = list(GOOD)
    lm[13] = np.nan
    m = _metrics({"A": GOOD, "L": lm, "B": BAD})
    m["eps"] = [5.0, -3.0, 1.0]
    m["bvps"] = [10.0, 10.0, 10.0]
    s = score_universe(m, _elig(["A", "L", "B"]), DEFAULTS["weights"])
    assert s.at["L", "relative_value"] < s.at["A", "relative_value"]


# Important 5: last month's list is found per portfolio, not only in the newest folder.
def test_previous_list_found_per_portfolio(tmp_data, monkeypatch):
    _install_fakes(monkeypatch)
    review.run_review(as_of=date(2026, 12, 1), portfolios=["nifty20"])
    review.run_review(as_of=date(2026, 12, 15), portfolios=["midcap30"])
    out = review.run_review(as_of=date(2027, 1, 1), portfolios=["nifty20"])
    assert "last month's list" in (out / "summary.md").read_text(encoding="utf-8")


# Important 6: every fundamentals fetch failing must not crash.
def test_review_survives_all_fundamentals_failing(tmp_data, monkeypatch):
    _install_fakes(monkeypatch)
    monkeypatch.setattr(fundamentals, "get_fundamentals", lambda s, max_age_days=30: None)
    out = review.run_review(as_of=date(2026, 12, 1), portfolios=["nifty20"])
    assert len(pd.read_csv(out / "list_nifty20.csv")) == 20


def test_review_survives_all_prices_failing(tmp_data, monkeypatch):
    _install_fakes(monkeypatch, failing=tuple(f"S{i:02d}" for i in range(30)))
    out = review.run_review(as_of=date(2026, 12, 1), portfolios=["nifty20"])
    assert len(pd.read_csv(out / "list_nifty20.csv")) == 20
    assert "only 0 eligible" in (out / "summary.md").read_text(encoding="utf-8")


# Important 7: value chart with no capital set starts at the amount invested.
def test_value_over_time_without_capital():
    idx = pd.to_datetime(["2026-12-01", "2026-12-02"])
    closes = pd.DataFrame({"TCS": [100.0, 110.0]}, index=idx)
    t = pd.DataFrame([{"date": "2026-12-01", "portfolio": "nifty20", "symbol": "TCS", "action": "BUY",
                       "qty": 10, "price": 100, "charges": 0}])
    v = value_over_time(t, "nifty20", closes, 0)
    assert v["total"].tolist() == [1000, 1100]


# Backdated SELL before its BUY is rejected.
def test_backdated_sell_rejected(tmp_data):
    ledger.append_trade("2026-12-05", "nifty20", "TCS", "BUY", 10, 100)
    with pytest.raises(ValueError, match="hold"):
        ledger.append_trade("2026-12-01", "nifty20", "TCS", "SELL", 5, 100)


# Banks/NBFCs: cash-flow and EV/EBITDA methods don't apply to lenders.
def test_financials_skip_dcf_and_ev_ebitda():
    m = {"sector": "Financial Services", "eps": 10, "bvps": 50, "fcf": 1e7, "shares": 1e6,
         "ebitda": 1.1e7, "net_debt": 0, "target_mean": 120}
    r = fair_value(m, {"pe": 12, "pb": 2, "ev_ebitda": 10}, 100, DEFAULTS["fair_value"])
    assert set(r["methods"]) == {"sector_pe", "sector_pb", "analyst_target"}
