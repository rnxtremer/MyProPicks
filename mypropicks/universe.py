"""NSE index constituent lists (the universe each portfolio picks from)."""
from __future__ import annotations

import io
import urllib.request

import pandas as pd

from .config import PORTFOLIOS, data_dir

HOSTS = [
    "https://www.niftyindices.com/IndexConstituent/{f}.csv",
    "https://nsearchives.nseindia.com/content/indices/{f}.csv",
]


def _download(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8-sig")


def _parse(text: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(text))
    df = df.rename(columns={"Symbol": "symbol", "Company Name": "name", "Industry": "industry"})
    df = df[["symbol", "name", "industry"]].copy()
    df["symbol"] = df["symbol"].astype(str).str.strip()
    return df.reset_index(drop=True)


def fetch_universe(portfolio: str, refresh: bool = True) -> pd.DataFrame:
    """Return columns symbol, name, industry. Falls back to the last good copy."""
    f = PORTFOLIOS[portfolio]["index_file"]
    cache = data_dir() / "universe" / f"{f}.csv"
    errors = []
    if refresh or not cache.exists():
        for host in HOSTS:
            url = host.format(f=f)
            try:
                text = _download(url)
                df = _parse(text)
                if len(df) == 0:
                    raise ValueError("empty list")
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(text, encoding="utf-8")
                return df
            except Exception as e:  # noqa: BLE001 - any failure falls back
                errors.append(f"{url}: {e}")
    if cache.exists():
        return _parse(cache.read_text(encoding="utf-8"))
    raise RuntimeError("Could not get constituent list. Tried: " + "; ".join(errors or [HOSTS[0].format(f=f)]))
