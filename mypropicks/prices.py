"""Daily price history from Yahoo Finance, cached per symbol."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Callable

import pandas as pd

from .config import data_dir

CACHE_MAX_AGE_S = 20 * 3600


def yahoo(symbol: str) -> str:
    return f"{symbol}.NS"


def _download_one(symbol: str, months: int) -> pd.DataFrame:
    import yfinance as yf

    df = yf.Ticker(yahoo(symbol)).history(period=f"{months}mo", auto_adjust=True)
    if df is None or df.empty:
        return pd.DataFrame()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df[["Close", "Volume"]]


def _cache_file(symbol: str):
    return data_dir() / "cache" / "prices" / f"{symbol.replace('&', '_and_')}.pkl"


def get_prices(
    symbols: list[str],
    months: int = 14,
    progress: Callable[[int, int, str], None] | None = None,
    max_age_s: float = CACHE_MAX_AGE_S,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Return (closes, volumes, failed). Fetched one at a time (parallel fetches lock yfinance's cache)."""
    closes, vols, failed = {}, {}, []
    for i, sym in enumerate(symbols):
        if progress:
            progress(i, len(symbols), sym)
        f = _cache_file(sym)
        df = None
        if f.exists() and time.time() - f.stat().st_mtime < max_age_s:
            df = pd.read_pickle(f)
        else:
            try:
                df = _download_one(sym, months)
            except Exception:  # noqa: BLE001
                df = pd.DataFrame()
            if df is not None and not df.empty:
                f.parent.mkdir(parents=True, exist_ok=True)
                df.to_pickle(f)
        if df is None or df.empty:
            failed.append(sym)
            continue
        df = _drop_partial_today(df)
        closes[sym] = df["Close"]
        vols[sym] = df["Volume"]
    c, v = pd.DataFrame(closes).sort_index(), pd.DataFrame(vols).sort_index()
    # Trim newest dates that most symbols don't have yet (mixed cache ages), so one fresher
    # symbol can't make everyone look "not traded every day".
    while len(c) and c.iloc[-1].notna().mean() < 0.5:
        c, v = c.iloc[:-1], v.iloc[:-1]
    return c, v, failed


def _now_ist() -> datetime:
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).replace(tzinfo=None)


def _drop_partial_today(df: pd.DataFrame) -> pd.DataFrame:
    """Before 15:45 IST, today's bar is still moving: use the previous close instead."""
    now = _now_ist()
    if len(df) and df.index[-1].date() == now.date() and (now.hour, now.minute) < (15, 45):
        return df.iloc[:-1]
    return df


def index_history(ticker: str, start: str) -> pd.Series:
    """Closes of a Yahoo index ticker (e.g. ^CNX100) from a start date. Empty if unavailable."""
    import yfinance as yf

    try:
        df = yf.Ticker(ticker).history(start=start, auto_adjust=True)
    except Exception:  # noqa: BLE001
        return pd.Series(dtype=float)
    if df is None or df.empty:
        return pd.Series(dtype=float)
    s = df["Close"]
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s


def latest_quotes(symbols: list[str]) -> dict[str, dict]:
    """Fresh last price and day change for a few symbols (about 15 minutes delayed)."""
    out = {}
    for sym in symbols:
        try:
            df = _download_one(sym, 1)
            if len(df) >= 2:
                last, prev = float(df["Close"].iloc[-1]), float(df["Close"].iloc[-2])
                out[sym] = {"ltp": last, "change_pct": last / prev - 1, "as_of": str(df.index[-1].date())}
        except Exception:  # noqa: BLE001
            pass
    return out
