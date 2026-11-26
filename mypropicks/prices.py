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


def _cache_file(symbol: str, cache: str = "prices"):
    return data_dir() / "cache" / cache / f"{symbol.replace('&', '_and_')}.pkl"


def get_prices(
    symbols: list[str],
    months: int = 14,
    progress: Callable[[int, int, str], None] | None = None,
    max_age_s: float = CACHE_MAX_AGE_S,
    cache: str = "prices",
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Return (closes, volumes, failed). Fetched one at a time (parallel fetches lock yfinance's cache)."""
    closes, vols, failed = {}, {}, []
    for i, sym in enumerate(symbols):
        if progress:
            progress(i, len(symbols), sym)
        f = _cache_file(sym, cache)
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


def _live_one(symbol: str) -> dict | None:
    """Yahoo's live price (about 15 minutes delayed) with its time and the previous close,
    from one intraday request. None if Yahoo has nothing usable."""
    import yfinance as yf

    t = yf.Ticker(yahoo(symbol))
    bars = t.history(period="1d", interval="5m")
    m = t.history_metadata or {}
    last, prev, when = m.get("regularMarketPrice"), m.get("chartPreviousClose") or m.get("previousClose"),         m.get("regularMarketTime")
    if not (last and last > 0):                    # no live price: the last good 5-minute bar
        bars = _clean(bars)
        if bars.empty:
            return None
        last, when = float(bars["Close"].iloc[-1]), bars.index[-1]
    when = pd.Timestamp(when) if when is not None else None
    if when is not None and when.tz is not None:
        when = when.tz_convert("Asia/Kolkata").tz_localize(None)
    return {"ltp": float(last), "change_pct": (last / prev - 1) if prev and prev > 0 else None,
            "as_of": when.strftime("%Y-%m-%d %H:%M") if when is not None else None, "live": True}


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Drop the blank or zero rows Yahoo sometimes sends."""
    if df is None or df.empty:
        return pd.DataFrame()
    return df[df["Close"].notna() & (df["Close"] > 0)]


def latest_quotes(symbols: list[str]) -> dict[str, dict]:
    """Live last price (about 15 minutes delayed), its time, and the change from the previous
    day's close. Falls back to the last daily close if live data isn't available."""
    out = {}
    for sym in symbols:
        try:
            q = _live_one(sym)
        except Exception:  # noqa: BLE001
            q = None
        if q is None:
            try:
                daily = _clean(_download_one(sym, 1))
            except Exception:  # noqa: BLE001
                daily = pd.DataFrame()
            if len(daily) >= 2:
                last, prev = float(daily["Close"].iloc[-1]), float(daily["Close"].iloc[-2])
                q = {"ltp": last, "change_pct": last / prev - 1,
                     "as_of": str(daily.index[-1].date()), "live": False}
        if q:
            out[sym] = q
    return out
