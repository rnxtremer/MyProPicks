"""Shared loaders for the dashboard pages."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# On Streamlit Cloud the GitHub token lives in the app's secrets; hand it to the core library.
try:
    _gh = st.secrets.get("github", {})
except Exception:  # no secrets file when running locally
    _gh = {}
for _k, _env in (("token", "MYPROPICKS_GH_TOKEN"), ("repo", "MYPROPICKS_GH_REPO"),
                 ("branch", "MYPROPICKS_GH_BRANCH")):
    if _gh.get(_k):
        os.environ[_env] = str(_gh[_k])

from mypropicks import fundamentals, ledger  # noqa: E402
from mypropicks.config import DISCLAIMER, PORTFOLIOS, data_dir, load_config  # noqa: E402
from mypropicks.prices import get_prices, latest_quotes  # noqa: E402
from mypropicks.review import latest_review  # noqa: E402

PF_KEYS = list(PORTFOLIOS)
PF_LABELS = {k: v["label"] for k, v in PORTFOLIOS.items()}


def footer() -> None:
    st.divider()
    st.caption(DISCLAIMER + " Prices from Yahoo Finance are delayed by about 15 minutes.")


def review_dirs() -> list[Path]:
    root = data_dir() / "reviews"
    if not root.exists():
        return []
    return sorted((p for p in root.iterdir() if (p / "summary.md").exists()), reverse=True)


@st.cache_data(ttl=300)
def load_review_file(folder: str, name: str) -> pd.DataFrame | None:
    f = Path(folder) / name
    return pd.read_csv(f) if f.exists() else None


def current_review() -> Path | None:
    return latest_review()


@st.cache_data(ttl=900, show_spinner="Fetching latest prices…")
def quotes(symbols: tuple[str, ...]) -> dict[str, dict]:
    return latest_quotes(list(symbols))


@st.cache_data(ttl=3600)
def price_history(symbol: str) -> pd.DataFrame:
    closes, _, _ = get_prices([symbol])
    return closes


@st.cache_data(ttl=3600, show_spinner="Loading price history…")
def price_histories(symbols: tuple[str, ...]) -> pd.DataFrame:
    # Trend lines don't need today's close: reuse cached history up to 3 days old.
    closes, _, _ = get_prices(list(symbols), max_age_s=3 * 86400)
    return closes


@st.cache_data(ttl=3600)
def fundamentals_raw(symbol: str) -> dict | None:
    f = data_dir() / "cache" / "fundamentals" / f"{symbol.replace('&', '_and_')}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return fundamentals.get_fundamentals(symbol)


def trades() -> pd.DataFrame:
    return ledger.load_trades()


def config() -> dict:
    return load_config()


def snapshot_file(pf: str) -> Path:
    return data_dir() / "snapshots" / f"rankings_{pf}.csv"


def fmt_inr(x) -> str:
    if x is None or x != x:
        return "—"
    return f"₹{x:,.0f}"
