import pandas as pd
import pytest

from mypropicks.history import value_over_time


def test_value_over_time():
    idx = pd.to_datetime(["2026-12-01", "2026-12-02", "2026-12-03"])
    closes = pd.DataFrame({"TCS": [100.0, 110.0, 120.0]}, index=idx)
    trades = pd.DataFrame([
        {"date": "2026-12-01", "portfolio": "nifty20", "symbol": "TCS", "action": "BUY", "qty": 10, "price": 100, "charges": 0},
        {"date": "2026-12-03", "portfolio": "nifty20", "symbol": "TCS", "action": "SELL", "qty": 5, "price": 120, "charges": 0},
    ])
    v = value_over_time(trades, "nifty20", closes, 10_000)
    assert v["holdings"].tolist() == [1000, 1100, 600]
    assert v["cash"].tolist() == [9000, 9000, 9600]
    assert v["total"].iloc[-1] == pytest.approx(10_200)


def test_value_over_time_empty():
    v = value_over_time(pd.DataFrame(columns=["date", "portfolio"]), "nifty20", pd.DataFrame(), 0)
    assert v.empty
