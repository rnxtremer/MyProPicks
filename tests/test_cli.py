from mypropicks import cli, ledger


def test_cli_log_appends_row(tmp_data, capsys):
    rc = cli.main(["log", "--portfolio", "nifty20", "--action", "BUY", "--symbol", "TCS",
                   "--qty", "10", "--price", "3450", "--date", "2026-12-02"])
    assert rc == 0
    t = ledger.load_trades()
    assert t[["symbol", "qty", "price"]].values.tolist() == [["TCS", 10.0, 3450.0]]
    assert "Logged" in capsys.readouterr().out


def test_cli_log_rejects_bad_trade(tmp_data, capsys):
    rc = cli.main(["log", "--portfolio", "nifty20", "--action", "SELL", "--symbol", "TCS",
                   "--qty", "1", "--price", "10"])
    assert rc == 2
    assert "can't sell" in capsys.readouterr().err


def test_cli_status_runs_without_trades(tmp_data, capsys):
    assert cli.main(["status", "--offline"]) == 0
    assert "Nifty 20" in capsys.readouterr().out
