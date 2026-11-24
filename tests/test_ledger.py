import pytest

from mypropicks import ledger


def _buy_sell(tmp_data):
    ledger.append_trade("2026-12-01", "nifty20", "TCS", "BUY", 10, 100)
    ledger.append_trade("2026-12-02", "nifty20", "TCS", "BUY", 10, 120)
    ledger.append_trade("2026-12-03", "nifty20", "TCS", "SELL", 5, 130)


def test_average_cost(tmp_data):
    _buy_sell(tmp_data)
    h = ledger.holdings(ledger.load_trades(), "nifty20").set_index("symbol")
    assert h.at["TCS", "qty"] == 15
    assert h.at["TCS", "avg_cost"] == pytest.approx(110)
    assert h.at["TCS", "realised"] == pytest.approx(100)


def test_append_trade_rejects_oversell(tmp_data):
    _buy_sell(tmp_data)
    before = (tmp_data / "trades.csv").read_bytes()
    with pytest.raises(ValueError, match="hold"):
        ledger.append_trade("2026-12-04", "nifty20", "TCS", "SELL", 20, 130)
    assert (tmp_data / "trades.csv").read_bytes() == before


@pytest.mark.parametrize("kw,msg", [
    ({"portfolio": "nifty99"}, "portfolio"),
    ({"qty": 0}, "quantity"),
    ({"price": -1}, "price"),
    ({"action": "HOLD"}, "action"),
])
def test_append_trade_validation(tmp_data, kw, msg):
    args = {"date": "2026-12-01", "portfolio": "nifty20", "symbol": "TCS", "action": "BUY", "qty": 1, "price": 10}
    args.update(kw)
    with pytest.raises(ValueError, match=msg):
        ledger.append_trade(**args)
    assert not (tmp_data / "trades.csv").exists() or len(ledger.load_trades()) == 0


def test_pnl_and_cash(tmp_data):
    _buy_sell(tmp_data)
    t = ledger.load_trades()
    assert ledger.cash(t, "nifty20", 10000) == pytest.approx(10000 - 1000 - 1200 + 650)
    p = ledger.pnl(t, "nifty20", {"TCS": 140}, 10000)
    assert p["invested"] == pytest.approx(1650)
    assert p["value"] == pytest.approx(2100)
    assert p["unrealised"] == pytest.approx(450)
    assert p["realised"] == pytest.approx(100)
    assert p["total_return_pct"] == pytest.approx(550 / 10000 * 100)


def test_symbol_normalised(tmp_data):
    ledger.append_trade("2026-12-01", "nifty20", " tcs ", "buy", 1, 10)
    assert ledger.load_trades()["symbol"].tolist() == ["TCS"]
    assert ledger.load_trades()["action"].tolist() == ["BUY"]
