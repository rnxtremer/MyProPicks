"""Command line: review, backtest, log, status."""
from __future__ import annotations

import argparse
import sys
from datetime import date

from . import ledger
from .config import DISCLAIMER, PORTFOLIOS, load_config


def _cmd_review(a) -> int:
    from .review import run_review

    def prog(stage, frac):
        print(f"\r{stage:<70}", end="", flush=True)

    out = run_review(as_of=date.fromisoformat(a.date) if a.date else None,
                     portfolios=[a.portfolio] if a.portfolio else None, progress=prog)
    print(f"\nReview written to {out}")
    print((out / "summary.md").read_text(encoding="utf-8"))
    return 0


def _cmd_backtest(a) -> int:
    import pandas as pd

    from .backtest import build, cagr

    def prog(stage, frac):
        print(f"\r{stage:<70}", end="", flush=True)

    cfg = load_config()
    for pf in [a.portfolio] if a.portfolio else list(PORTFOLIOS):
        f = build(pf, cfg, progress=prog)
        df = pd.read_csv(f, index_col=0, parse_dates=True)
        ai, bl, ix = cagr(df["ai"]), cagr(df["baseline"]), cagr(df["index"])
        print(f"\n{PORTFOLIOS[pf]['label']}: AI {ai:+.1%} a year, all members {bl:+.1%}, index {ix:+.1%} -> {f}")
    return 0


def _cmd_log(a) -> int:
    try:
        row = ledger.append_trade(a.date, a.portfolio, a.symbol, a.action, a.qty, a.price,
                                  a.charges, a.note or "")
    except ValueError as e:
        print(f"Not logged: {e}", file=sys.stderr)
        return 2
    print(f"Logged: {row['date']} {row['portfolio']} {row['action']} {row['qty']:g} "
          f"{row['symbol']} @ {row['price']:,.2f} (charges {row['charges']:,.2f})")
    return 0


def _cmd_status(a) -> int:
    cfg = load_config()
    trades = ledger.load_trades()
    for pf, meta in PORTFOLIOS.items():
        held = ledger.held_symbols(trades, pf)
        ltp = {}
        if held and not a.offline:
            from .prices import latest_quotes
            ltp = {s: q["ltp"] for s, q in latest_quotes(held).items()}
        p = ledger.pnl(trades, pf, ltp, float(cfg["capital"].get(pf) or 0))
        print(f"{meta['label']}: {p['positions']}/{meta['n']} stocks | invested ₹{p['invested']:,.0f} | "
              f"value ₹{p['value']:,.0f} | unrealised ₹{p['unrealised']:,.0f} | "
              f"realised ₹{p['realised']:,.0f} | cash ₹{p['cash']:,.0f} | return {p['total_return_pct']:.2f}%")
    print(DISCLAIMER)
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="mypropicks")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("review", help="run the monthly review now")
    r.add_argument("--date", help="review date YYYY-MM-DD (default today)")
    r.add_argument("--portfolio", choices=list(PORTFOLIOS))
    r.set_defaults(fn=_cmd_review)

    b = sub.add_parser("backtest", help="replay the model over the last 3 years vs its index")
    b.add_argument("--portfolio", choices=list(PORTFOLIOS))
    b.set_defaults(fn=_cmd_backtest)

    lg = sub.add_parser("log", help="record a trade you placed")
    lg.add_argument("--portfolio", required=True)
    lg.add_argument("--action", required=True, help="BUY or SELL")
    lg.add_argument("--symbol", required=True, help="NSE symbol, e.g. TCS")
    lg.add_argument("--qty", required=True, type=float)
    lg.add_argument("--price", required=True, type=float)
    lg.add_argument("--charges", type=float, default=0.0)
    lg.add_argument("--date", help="trade date YYYY-MM-DD (default today)")
    lg.add_argument("--note")
    lg.set_defaults(fn=_cmd_log)

    st = sub.add_parser("status", help="show P&L per portfolio")
    st.add_argument("--offline", action="store_true", help="skip fetching live prices")
    st.set_defaults(fn=_cmd_status)

    a = ap.parse_args(argv)
    return a.fn(a)
