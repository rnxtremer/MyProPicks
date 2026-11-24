from datetime import date

import numpy as np
import pandas as pd

from mypropicks import fundamentals, ledger, prices, review, universe
from mypropicks.review import decide_changes
from mypropicks.sizing import suggest_quantities


def _ranked(n_elig: int, n_inelig: int = 0) -> pd.DataFrame:
    syms = [f"S{i:02d}" for i in range(n_elig + n_inelig)]
    return pd.DataFrame({
        "rank": range(1, len(syms) + 1),
        "eligible": [i < n_elig for i in range(len(syms))],
        "reason": ["" if i < n_elig else "low liquidity" for i in range(len(syms))],
    }, index=syms)


def test_first_run_buys_n():
    r = decide_changes(_ranked(40), [], 20)
    assert len(r["buy"]) == 20 and r["sell"] == [] and r["new_list"] == r["buy"]


def test_sells_equal_buys():
    ranked = _ranked(40)
    held = [f"S{i:02d}" for i in range(16)] + ["S30", "S31", "S32", "S33"]
    r = decide_changes(ranked, held, 20)
    assert len(r["sell"]) == 4 and len(r["buy"]) == 4
    assert {s for s, _ in r["sell"]} == {"S30", "S31", "S32", "S33"}
    assert r["buy"] == ["S16", "S17", "S18", "S19"]
    assert dict(r["sell"])["S30"] == "dropped to rank 31"
    assert len(r["keep"]) + len(r["buy"]) == 20


def test_held_stock_outside_universe_is_sold():
    held = [f"S{i:02d}" for i in range(19)] + ["GONE"]
    r = decide_changes(_ranked(40), held, 20)
    assert ("GONE", "left universe") in r["sell"]
    assert r["buy"] == ["S19"]


def test_ineligible_held_reason():
    ranked = _ranked(25, 5)
    held = [f"S{i:02d}" for i in range(19)] + ["S27"]
    r = decide_changes(ranked, held, 20)
    assert ("S27", "ineligible: low liquidity") in r["sell"]


def test_fill_when_eligible_below_n():
    r = decide_changes(_ranked(15, 10), [], 20)
    assert len(r["new_list"]) == 20
    assert any("only 15 eligible" in w for w in r["warnings"])


def test_short_portfolio_gets_extra_buys():
    held = [f"S{i:02d}" for i in range(18)]
    r = decide_changes(_ranked(40), held, 20)
    assert r["sell"] == [] and len(r["buy"]) == 2
    assert any("short" in w for w in r["warnings"])


def test_equal_split():
    assert suggest_quantities(["A", "B"], {"A": 100, "B": 300}, 10_000) == {"A": 50, "B": 16}
    assert suggest_quantities(["A"], {"A": 100}, 0) == {"A": 0}
    assert suggest_quantities([], {}, 1000) == {}


# ---------- full pipeline with fake data ----------

def _install_fakes(monkeypatch, n=30, failing=("S05", "S11", "S23")):
    syms = [f"S{i:02d}" for i in range(n)]
    csv_text = "Company Name,Industry,Symbol,Series,ISIN Code\n" + "".join(
        f"Co {s},{'IT' if i % 2 else 'Bank'},{s},EQ,X{i}\n" for i, s in enumerate(syms))
    monkeypatch.setattr(universe, "_download", lambda url: csv_text)
    rng = np.random.default_rng(1)

    def fake_px(sym, months):
        if sym in failing:
            return pd.DataFrame()
        i = int(sym[1:])
        idx = pd.bdate_range(end="2026-11-30", periods=290)
        close = 100 * np.cumprod(1 + rng.normal(0.0005 * (i % 7), 0.01, len(idx)))
        return pd.DataFrame({"Close": close, "Volume": 1e6}, index=idx)

    monkeypatch.setattr(prices, "_download_one", fake_px)

    def fake_fund(sym, max_age_days=30):
        i = int(sym[1:])
        return {"info": {"trailingPE": 10 + i, "priceToBook": 1 + i / 10, "trailingEps": 10,
                         "bookValue": 50, "sharesOutstanding": 1e7, "marketCap": 1e10,
                         "returnOnEquity": 0.1 + i / 100, "sector": "X"},
                "financials": {}, "cashflow": {}, "balance_sheet": {}, "quarterly": {}}

    monkeypatch.setattr(fundamentals, "get_fundamentals", fake_fund)
    return syms


def test_review_lists_fetch_failures_and_still_fills_n(tmp_data, monkeypatch):
    _install_fakes(monkeypatch)
    out = review.run_review(as_of=date(2026, 12, 1), portfolios=["nifty20"])
    summary = (out / "summary.md").read_text(encoding="utf-8")
    for s in ("S05", "S11", "S23"):
        assert s in summary
    lst = pd.read_csv(out / "list_nifty20.csv")
    assert len(lst) == 20
    assert "Not investment advice" in summary
    assert review.latest_review() == out


def test_second_review_carries_added_on(tmp_data, monkeypatch):
    _install_fakes(monkeypatch)
    first = review.run_review(as_of=date(2026, 12, 1), portfolios=["nifty20"])
    second = review.run_review(as_of=date(2027, 1, 1), portfolios=["nifty20"])
    a = pd.read_csv(first / "list_nifty20.csv").set_index("symbol")
    b = pd.read_csv(second / "list_nifty20.csv").set_index("symbol")
    common = a.index.intersection(b.index)
    assert len(common) > 0
    assert (b.loc[common, "added_on"] == "2026-12-01").all()


def test_review_uses_holdings_when_logged(tmp_data, monkeypatch):
    _install_fakes(monkeypatch)
    ledger.append_trade("2026-11-01", "nifty20", "OLDCO", "BUY", 5, 100)
    out = review.run_review(as_of=date(2026, 12, 1), portfolios=["nifty20"])
    ch = pd.read_csv(out / "changes_nifty20.csv")
    sells = ch[ch["action"] == "SELL"]
    assert sells["symbol"].tolist() == ["OLDCO"]
    assert sells["reason"].tolist() == ["left universe"]
