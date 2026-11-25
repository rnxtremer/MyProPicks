"""Shared loaders for the dashboard pages."""
from __future__ import annotations

import hmac
import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))



def _secrets(section: str) -> dict:
    try:
        return dict(st.secrets.get(section, {}))
    except Exception:  # no secrets file when running locally
        return {}


# On Streamlit Cloud the GitHub token lives in the app's secrets; hand it to the core library.
_gh = _secrets("github")
for _k, _env in (("token", "MYPROPICKS_GH_TOKEN"), ("repo", "MYPROPICKS_GH_REPO"),
                 ("branch", "MYPROPICKS_GH_BRANCH"), ("data_repo", "MYPROPICKS_GH_DATA_REPO")):
    if _gh.get(_k):
        os.environ[_env] = str(_gh[_k])

from mypropicks import fundamentals, ledger, remote  # noqa: E402
from mypropicks.config import DISCLAIMER, PORTFOLIOS, data_dir, load_config  # noqa: E402
from mypropicks.prices import get_prices, latest_quotes  # noqa: E402
from mypropicks.review import latest_review, personal_changes  # noqa: E402



@st.cache_data(ttl=300, show_spinner=False)
def _sync_private() -> str | None:
    """Fetch your trades and capital from the private data repo (cloud only)."""
    try:
        remote.sync_private()
    except ValueError as e:
        return str(e)
    return None


_sync_error = _sync_private()


def require_unlock() -> None:
    """Stop the page unless the visitor has entered the app password.

    On your PC with no password set, pages stay open. In the cloud a password is required, so
    nobody who finds the link can see your money or change your records.
    """
    password = str(_secrets("app").get("password") or "")
    if not password and not remote.enabled():
        return
    if st.session_state.get("unlocked"):
        if _sync_error:
            st.warning(_sync_error, icon=":material/cloud_off:")
        if st.sidebar.button("Lock", icon=":material/lock:"):
            st.session_state["unlocked"] = False
            st.rerun()
        return
    st.title(":material/lock: Private page")
    if not password:
        st.error("Set a password under [app] in the app's secrets to open this page.",
                 icon=":material/key_off:")
        st.stop()
    st.caption("Your holdings, trades and settings are private. Enter the app password to continue.")
    with st.form("unlock", border=False, width=360):
        entered = st.text_input("Password", type="password")
        if st.form_submit_button("Unlock", type="primary", icon=":material/lock_open:"):
            if hmac.compare_digest(entered.encode(), password.encode()):
                st.session_state["unlocked"] = True
                st.rerun()
            st.error("That password isn't right.")
    st.stop()


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


@st.cache_data(ttl=300)
def load_rankings(folder: str, pf: str) -> pd.DataFrame | None:
    f = Path(folder) / f"rankings_{pf}.csv"
    return pd.read_csv(f, index_col=0) if f.exists() else None


@st.cache_data(ttl=300)
def load_backtest(pf: str) -> pd.DataFrame | None:
    """The 3-year AI vs index replay saved by the monthly review (None if not run yet)."""
    from mypropicks.backtest import result_file
    f = result_file(pf)
    return pd.read_csv(f, index_col=0, parse_dates=True) if f.exists() else None


def snapshot_file(pf: str) -> Path:
    return data_dir() / "snapshots" / f"rankings_{pf}.csv"


def fmt_inr(x) -> str:
    if x is None or x != x:
        return "—"
    return f"₹{x:,.0f}"


def my_moves(rev: Path, pf: str) -> tuple[pd.DataFrame | None, list[str]]:
    """Your own SELL/BUY list for a review, from your trades and capital. Private pages only."""
    table = load_rankings(str(rev), pf)
    if table is None:
        return None, []
    capital = float(config()["capital"].get(pf) or 0)
    rows, warnings = personal_changes(table, trades(), pf, capital)
    df = pd.DataFrame(rows, columns=["action", "symbol", "reason", "qty", "price"])
    for c in ("qty", "price"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df, warnings
