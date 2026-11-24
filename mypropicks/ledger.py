"""Your real trades (trades.csv) and everything derived from them: holdings, cash, P&L."""
from __future__ import annotations

import csv
from datetime import date as _date

import pandas as pd

from . import remote
from .config import PORTFOLIOS, data_dir

COLUMNS = ["date", "portfolio", "symbol", "action", "qty", "price", "charges", "note"]


def trades_file():
    return data_dir() / "trades.csv"


def load_trades() -> pd.DataFrame:
    f = trades_file()
    if not f.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(f, dtype={"symbol": str, "note": str})
    for c in ("qty", "price", "charges"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    df["note"] = df["note"].fillna("")
    return df


def holdings(trades: pd.DataFrame, portfolio: str) -> pd.DataFrame:
    """Average-cost holdings: symbol, qty, avg_cost, invested, realised (incl. closed positions)."""
    t = trades[trades["portfolio"] == portfolio].copy()
    t["_order"] = range(len(t))
    t = t.sort_values(["date", "_order"])
    book: dict[str, dict] = {}
    for r in t.itertuples():
        b = book.setdefault(r.symbol, {"qty": 0.0, "avg_cost": 0.0, "realised": 0.0})
        if r.action == "BUY":
            new_qty = b["qty"] + r.qty
            b["avg_cost"] = (b["qty"] * b["avg_cost"] + r.qty * r.price) / new_qty
            b["qty"] = new_qty
        else:
            b["realised"] += (r.price - b["avg_cost"]) * r.qty
            b["qty"] -= r.qty
            if b["qty"] <= 1e-9:
                b["qty"], b["avg_cost"] = 0.0, 0.0
        b["realised"] -= r.charges
    rows = [{"symbol": s, "qty": b["qty"], "avg_cost": b["avg_cost"],
             "invested": b["qty"] * b["avg_cost"], "realised": b["realised"]} for s, b in book.items()]
    return pd.DataFrame(rows, columns=["symbol", "qty", "avg_cost", "invested", "realised"])


def held_symbols(trades: pd.DataFrame, portfolio: str) -> list[str]:
    h = holdings(trades, portfolio)
    return h.loc[h["qty"] > 0, "symbol"].tolist()


def cash(trades: pd.DataFrame, portfolio: str, capital: float) -> float:
    t = trades[trades["portfolio"] == portfolio]
    buys = (t.loc[t["action"] == "BUY", "qty"] * t.loc[t["action"] == "BUY", "price"]).sum()
    sells = (t.loc[t["action"] == "SELL", "qty"] * t.loc[t["action"] == "SELL", "price"]).sum()
    return float(capital - buys + sells - t["charges"].sum())


def pnl(trades: pd.DataFrame, portfolio: str, ltp: dict[str, float], capital: float) -> dict:
    h = holdings(trades, portfolio)
    open_ = h[h["qty"] > 0]
    value = sum(r.qty * ltp.get(r.symbol, r.avg_cost) for r in open_.itertuples())
    invested = float(open_["invested"].sum())
    realised = float(h["realised"].sum())
    unrealised = value - invested
    base = capital if capital and capital > 0 else invested
    total = (realised + unrealised) / base * 100 if base else 0.0
    return {"invested": invested, "value": float(value), "unrealised": float(unrealised),
            "realised": realised, "cash": cash(trades, portfolio, capital),
            "total_return_pct": float(total), "positions": int(len(open_))}


def append_trade(date, portfolio: str, symbol: str, action: str, qty: float, price: float,
                 charges: float = 0.0, note: str = "") -> dict:
    """Validate and append one trade. Writes nothing if anything is wrong."""
    if portfolio not in PORTFOLIOS:
        raise ValueError(f"Unknown portfolio '{portfolio}'. Use one of: {', '.join(PORTFOLIOS)}")
    action = str(action).strip().upper()
    if action not in ("BUY", "SELL"):
        raise ValueError(f"Unknown action '{action}'. Use BUY or SELL.")
    symbol = str(symbol).strip().upper().removesuffix(".NS")
    if not symbol:
        raise ValueError("Symbol is empty.")
    try:
        qty, price, charges = float(qty), float(price), float(charges or 0)
    except (TypeError, ValueError) as e:
        raise ValueError("Quantity, price and charges must be numbers.") from e
    if qty <= 0:
        raise ValueError("The quantity must be more than 0.")
    if price <= 0:
        raise ValueError("The price must be more than 0.")
    if charges < 0:
        raise ValueError("Charges can't be negative.")
    d = _date.fromisoformat(str(date)) if date else _date.today()

    f = trades_file()
    sha = None
    if remote.enabled():
        # Start from the repo's copy, so a trade logged on another device isn't lost.
        sha = remote.pull(f)
    trades = load_trades()
    if action == "SELL":
        # Check against what you held on the trade date, so a back-dated sell can't go negative.
        as_of = trades[trades["date"].astype(str) <= d.isoformat()]
        h = holdings(as_of, portfolio).set_index("symbol")
        held = float(h.at[symbol, "qty"]) if symbol in h.index else 0.0
        if qty > held + 1e-9:
            raise ValueError(f"You hold {held:g} {symbol} in {portfolio}, so you can't sell {qty:g}.")

    row = {"date": d.isoformat(), "portfolio": portfolio, "symbol": symbol, "action": action,
           "qty": qty, "price": price, "charges": charges, "note": note}
    f.parent.mkdir(parents=True, exist_ok=True)
    before = f.read_bytes() if f.exists() else None
    with open(f, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        if before is None:
            w.writeheader()
        w.writerow(row)
    if remote.enabled():
        try:
            remote.push(f, f"trade: {action} {qty:g} {symbol} ({portfolio})", sha=sha)
        except ValueError:
            # Not saved to GitHub, so undo the local write too.
            if before is None:
                f.unlink()
            else:
                f.write_bytes(before)
            raise
    return row
