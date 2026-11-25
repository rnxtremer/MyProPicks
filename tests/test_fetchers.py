import json
import numpy as np
import pandas as pd
import pytest

from mypropicks import fundamentals, prices, universe

HEADER = "Company Name,Industry,Symbol,Series,ISIN Code\n"
ROWS = "ABB India Ltd.,Capital Goods,ABB,EQ,INE117A01022\nTata Consultancy Services Ltd.,Information Technology,TCS,EQ,INE467B01029\n"


def test_universe_parses_columns(tmp_data, monkeypatch):
    monkeypatch.setattr(universe, "_download", lambda url: HEADER + ROWS)
    df = universe.fetch_universe("nifty20")
    assert list(df.columns) == ["symbol", "name", "industry"]
    assert df["symbol"].tolist() == ["ABB", "TCS"]
    assert (tmp_data / "universe" / "ind_nifty100list.csv").exists()


def test_universe_falls_back_to_cache(tmp_data, monkeypatch):
    monkeypatch.setattr(universe, "_download", lambda url: HEADER + ROWS)
    universe.fetch_universe("nifty20")

    def boom(url):
        raise OSError("offline")

    monkeypatch.setattr(universe, "_download", boom)
    df = universe.fetch_universe("nifty20")
    assert df["symbol"].tolist() == ["ABB", "TCS"]


def test_universe_no_cache_raises(tmp_data, monkeypatch):
    def boom(url):
        raise OSError("offline")

    monkeypatch.setattr(universe, "_download", boom)
    with pytest.raises(RuntimeError, match="niftyindices"):
        universe.fetch_universe("midcap30")


def _fake_history(n=300):
    idx = pd.bdate_range("2025-01-01", periods=n)
    return pd.DataFrame({"Close": np.linspace(100, 200, n), "Volume": 1000.0}, index=idx)


def test_prices_reports_failed_symbols(tmp_data, monkeypatch):
    def fake(sym, months):
        return pd.DataFrame() if sym == "BAD" else _fake_history()

    monkeypatch.setattr(prices, "_download_one", fake)
    closes, vols, failed = prices.get_prices(["TCS", "BAD"])
    assert failed == ["BAD"]
    assert list(closes.columns) == ["TCS"]
    assert len(closes) == 300


def test_prices_use_cache(tmp_data, monkeypatch):
    calls = []

    def fake(sym, months):
        calls.append(sym)
        return _fake_history()

    monkeypatch.setattr(prices, "_download_one", fake)
    prices.get_prices(["TCS"])
    prices.get_prices(["TCS"])
    assert calls == ["TCS"]


def _raw(**info):
    years = ["2026-03-31", "2025-03-31", "2024-03-31", "2023-03-31"]
    fin = {
        "Total Revenue": dict(zip(years, [133.1, 121.0, 110.0, 100.0])),
        "Operating Income": dict(zip(years, [30.0, 27.0, 25.0, 22.0])),
        "Net Income": dict(zip(years, [20.0, 18.0, 16.0, 15.0])),
        "Diluted EPS": dict(zip(years, [10.0, 9.0, 8.0, 7.5])),
        "EBIT": dict(zip(years, [32.0, 29.0, 26.0, 23.0])),
        "EBITDA": dict(zip(years, [40.0, 36.0, 33.0, 30.0])),
        "Interest Expense": dict(zip(years, [-4.0, -4.0, -4.0, -4.0])),
    }
    cf = {
        "Operating Cash Flow": dict(zip(years, [24.0, 20.0, 18.0, 16.0])),
        "Free Cash Flow": dict(zip(years, [12.1, 11.0, 10.0, 9.09])),
    }
    bs = {
        "Stockholders Equity": dict(zip(years, [100.0, 90.0, 80.0, 70.0])),
        "Total Debt": dict(zip(years, [60.0, 60.0, 60.0, 60.0])),
        "Cash And Cash Equivalents": dict(zip(years, [10.0, 8.0, 6.0, 5.0])),
    }
    base = {
        "debtToEquity": 9.83,
        "dividendYield": 1.95,
        "trailingPE": 17.2,
        "priceToBook": 7.5,
        "marketCap": 1000.0,
        "sharesOutstanding": 10.0,
        "trailingEps": 10.0,
        "bookValue": 10.0,
        "sector": "Technology",
    }
    base.update(info)
    return {"info": base, "financials": fin, "cashflow": cf, "balance_sheet": bs}


def test_extract_metrics_from_fixture():
    m = fundamentals.extract_metrics(_raw())
    assert m["rev_cagr3"] == pytest.approx(0.10, abs=1e-3)
    assert m["debt_equity"] == pytest.approx(0.0983)
    assert m["dividend_yield"] == pytest.approx(0.0195)
    assert m["roce"] == pytest.approx(32.0 / 160.0)
    assert m["interest_cover"] == pytest.approx(8.0)
    assert m["ocf_to_np"] == pytest.approx(1.2)
    assert m["fcf_yield"] == pytest.approx(12.1 / 1000.0)
    assert m["net_debt"] == pytest.approx(50.0)


def test_extract_metrics_missing_fields_are_none():
    raw = {"info": {"sector": "X"}, "financials": {}, "cashflow": {}, "balance_sheet": {}}
    m = fundamentals.extract_metrics(raw)
    assert m["roe"] is None and m["rev_cagr3"] is None and m["pe"] is None
    assert m["sector"] == "X"


def _hist_raw():
    """Two financial years; prices adjusted for splits, so per-share values use current shares."""
    return {
        "info": {"sharesOutstanding": 100.0},
        "financials": {"Net Income Common Stockholders": {"2025-03-31": 1000.0, "2024-03-31": 800.0}},
        "balance_sheet": {"Stockholders Equity": {"2025-03-31": 5000.0, "2024-03-31": 4000.0}},
        "monthly_close": {"2024-03-01": 160.0, "2024-04-01": 170.0, "2025-03-01": 250.0,
                          "2025-11-01": 300.0},
    }


def test_own_history_multiples():
    m = fundamentals.extract_metrics(_hist_raw())
    # FY24: price 160 / EPS 8 = 20; FY25: 250 / 10 = 25 -> median 22.5
    assert m["own_pe_hist"] == pytest.approx(22.5)
    # FY24: 160 / BVPS 40 = 4; FY25: 250 / 50 = 5 -> median 4.5
    assert m["own_pb_hist"] == pytest.approx(4.5)


def test_own_history_needs_two_years():
    raw = _hist_raw()
    raw["monthly_close"] = {"2025-03-01": 250.0}
    m = fundamentals.extract_metrics(raw)
    assert m["own_pe_hist"] is None and m["own_pb_hist"] is None


def test_old_cache_without_price_history_is_refetched(tmp_data, monkeypatch):
    f = tmp_data / "cache" / "fundamentals" / "TCS.json"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps({"info": {"marketCap": 1}, "financials": {}}), encoding="utf-8")
    fresh = {**_hist_raw(), "info": {"marketCap": 2}}
    monkeypatch.setattr(fundamentals, "_download", lambda s: fresh)
    assert fundamentals.get_fundamentals("TCS")["info"]["marketCap"] == 2


def test_latest_quotes_skips_blank_last_row(monkeypatch):
    df = pd.DataFrame({"Close": [100.0, 110.0, np.nan], "Volume": [1, 1, 1]},
                      index=pd.to_datetime(["2026-11-20", "2026-11-23", "2026-11-25"]))
    monkeypatch.setattr(prices, "_download_one", lambda sym, months: df)
    q = prices.latest_quotes(["PNB"])["PNB"]
    assert q["ltp"] == 110.0
    assert q["change_pct"] == pytest.approx(0.10)
    assert q["as_of"] == "2026-11-23"
