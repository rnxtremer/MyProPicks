"""Shared loaders for the dashboard pages."""
from __future__ import annotations

import hmac
import json
import os
import sys
from datetime import date
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

from mypropicks import explain, fundamentals, ledger, remote  # noqa: E402
from mypropicks.config import DISCLAIMER, PORTFOLIOS, data_dir, load_config  # noqa: E402
from mypropicks import prices as _prices  # noqa: E402
from mypropicks.prices import get_prices, index_history, latest_quotes  # noqa: E402
from mypropicks.review import latest_list_dir, latest_review, personal_changes  # noqa: E402



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


REPO_URL = "https://github.com/rnxtremer/MyProPicks"
CREATOR = "Rudra Narayan Das"
CREATOR_GITHUB = "https://github.com/rnxtremer"


def _next_review(today: date) -> date:
    """The monthly review runs on the 1st (08:00 IST)."""
    return date(today.year + (today.month == 12), today.month % 12 + 1, 1)


def footer() -> None:
    """Site footer: what MyProPicks is, quick links, data sources and the disclaimer."""
    st.space("large")
    st.divider()
    about, explore, learn, data = st.columns([1.6, 1, 1, 1.2], gap="large")
    with about:
        st.markdown("**:material/insights: MyProPicks**")
        st.caption("Rules-based stock picks for three Indian portfolios: Nifty 20, Midcap 30 and "
                   "Smallcap 50, reviewed on the 1st of every month.")
        rev = latest_review()
        today = date.today()
        nice = lambda d: f"{d.day} {d:%b %Y}"  # noqa: E731
        badges = ([f":gray-badge[:material/event_available: Last review {nice(date.fromisoformat(rev.name))}]"]
                  if rev else [])
        badges.append(f":gray-badge[:material/update: Next review {nice(_next_review(today))}]")
        st.markdown(" ".join(badges))
        st.caption(f"Created by **{CREATOR}** · [:material/person: GitHub]({CREATOR_GITHUB})")
    with explore:
        st.markdown("**Explore**")
        st.page_link("app_pages/analysis.py", label="Portfolio analysis")
        st.page_link("app_pages/this_month.py", label="This month")
        st.page_link("app_pages/rankings.py", label="Full rankings")
    with learn:
        st.markdown("**Learn**")
        st.page_link("app_pages/how_it_works.py", label="How it works")
        st.page_link("app_pages/info.py", label="Info: terms explained")
        st.page_link(REPO_URL, label="Source code", icon=":material/code:")
    with data:
        st.markdown("**Data**")
        st.caption("Prices and financials: Yahoo Finance, delayed by about 15 minutes.")
        st.caption("Index members: NSE (niftyindices.com).")
        st.caption("Benchmarks: Nifty 50, Nifty Midcap 150, Nifty Smallcap 250.")
    st.divider()
    with st.container(horizontal=True, vertical_alignment="top", gap="large"):
        st.caption(f"© {date.today().year} MyProPicks · {CREATOR}", width="content")
        st.caption(f":material/info: {DISCLAIMER}", width="stretch")


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


@st.cache_data(ttl=300, show_spinner="Fetching live prices…")
def quotes(symbols: tuple[str, ...]) -> dict[str, dict]:
    return latest_quotes(list(symbols))


# Market strip on Portfolio analysis: (name, Yahoo ticker). GIFT Nifty isn't on Yahoo.
MARKETS = [("Nifty 50", "^NSEI"), ("Sensex", "^BSESN"), ("Bank Nifty", "^NSEBANK"),
           ("India VIX", "^INDIAVIX"), ("Nasdaq", "^IXIC"), ("S&P 500", "^GSPC")]


@st.cache_data(ttl=300, show_spinner=False)
def market_quotes() -> dict[str, dict]:
    out = {}
    for name, tk in MARKETS:
        try:
            q = _prices.live_ticker(tk)
        except Exception:  # noqa: BLE001
            q = None
        if q:
            out[name] = q
    return out


def market_strip() -> None:
    """One row of index cards: level, day change and the time of the price."""
    q = market_quotes()
    if not q:
        return
    with st.container(horizontal=True, gap="small"):
        for name, _ in MARKETS:
            v = q.get(name)
            if not v:
                continue
            chg = v.get("change_pct")
            when = pd.Timestamp(v["as_of"]) if v.get("as_of") else None
            st.metric(name, f"{v['ltp']:,.2f}", f"{chg:+.2%}" if chg is not None else None, border=True,
                      delta_color="inverse" if name == "India VIX" else "normal",
                      help=(f"As of {when.day} {when:%b}, {when:%H:%M} IST (about 15 minutes delayed). "
                            + ("India VIX measures expected volatility: rising means more fear."
                               if name == "India VIX" else "")) if when is not None else None)


def with_live(hist: pd.DataFrame, q: dict[str, dict]) -> pd.DataFrame:
    """Daily closes with each stock's live price added as today's point (or replacing it), so
    charts reach the latest price instead of stopping at the last cached close."""
    out = hist.copy()
    for s, v in q.items():
        if s in out and v.get("as_of") and pd.notna(v.get("ltp")):
            out.loc[pd.Timestamp(v["as_of"]).normalize(), s] = float(v["ltp"])
    return out.sort_index()


def prices_note(q: dict[str, dict]) -> str:
    """One line saying how fresh the prices are, e.g. 'Live prices as of 26 Nov, 3:25 pm IST'."""
    times = sorted(v["as_of"] for v in q.values() if v.get("as_of"))
    if not times:
        return "Live prices unavailable right now; showing prices from the review."
    t = pd.Timestamp(times[-1])
    if any(v.get("live") for v in q.values()):
        return (f"Live prices as of {t:%d %b}, {t:%I:%M %p}".replace(" 0", " ").replace("AM", "am")
                .replace("PM", "pm") + " IST (about 15 minutes delayed) · refreshed every 5 minutes")
    return f"Prices from the last close ({t:%d %b %Y}); live prices unavailable right now"


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


# ---- a stock's time in the list: from added to removed ----
GAIN, LOSS, OUTSIDE = "#22C55E", "#EF4444", "#94A3B8"


@st.cache_data(ttl=3600, show_spinner=False)
def index_series(ticker: str, start: str) -> pd.Series:
    return index_history(ticker, start)


@st.cache_data(ttl=300)
def explained_changes(folder: str, pf: str) -> pd.DataFrame | None:
    """A review's changes with short plain-English reasons. Reviews saved before reasons were
    written ("rank 17") get them worked out from that review's and the previous one's rankings."""
    ch = load_review_file(folder, f"changes_{pf}.csv")
    if ch is None or ch.empty:
        return ch
    rev = Path(folder)
    rk = load_review_file(folder, f"rankings_{pf}.csv")
    if rk is None:
        return ch
    rk = rk.set_index(rk.columns[0]) if rk.columns[0] in ("symbol", "Unnamed: 0") else rk
    prev = None
    prev_dir = latest_list_dir(pf, date.fromisoformat(rev.name))
    if prev_dir is not None and (prev_dir / f"rankings_{pf}.csv").exists():
        prev = pd.read_csv(prev_dir / f"rankings_{pf}.csv", index_col=0)
    ch = ch.copy()
    ch["reason"] = [explain.reason(r.action, r.symbol, rk, prev, r.reason) for r in ch.itertuples()]
    return ch


def leavers(rev: Path, pf: str) -> pd.DataFrame:
    """This review's SELLs with when each entered the list and at what price. Older reviews
    didn't save that, so it's looked up in the previous review's list."""
    ch = explained_changes(str(rev), pf)
    if ch is None or ch.empty:
        return pd.DataFrame(columns=["symbol", "reason", "price", "added_on", "added_price"])
    out = ch[ch["action"] == "SELL"].copy()
    for c in ("added_on", "added_price"):
        if c not in out:
            out[c] = None
    if out["added_on"].isna().any():
        prev = latest_list_dir(pf, date.fromisoformat(rev.name))
        if prev is not None:
            pl = pd.read_csv(prev / f"list_{pf}.csv").set_index("symbol")
            miss = out["added_on"].isna()
            out.loc[miss, "added_on"] = out.loc[miss, "symbol"].map(pl["added_on"])
            out.loc[miss, "added_price"] = out.loc[miss, "symbol"].map(pl["added_price"])
    out["added_price"] = pd.to_numeric(out["added_price"], errors="coerce")
    out["price"] = pd.to_numeric(out["price"], errors="coerce")
    return out.reset_index(drop=True)


def journey_chart(price: pd.Series, added_on, added_price: float, removed_on=None,
                  removed_price: float | None = None, avg: pd.Series | None = None,
                  height: int = 280):
    """Price line with the stretch the stock spent in the list shaded (green if it gained, red
    if it lost), and Added / Removed markers with their prices, like a trade journal."""
    import altair as alt

    price = price.dropna()

    def trading_day(d):  # a review on a holiday used the last close before it
        d = pd.Timestamp(d)
        before = price.index[price.index <= d]
        return before[-1] if len(before) else d

    a0 = trading_day(added_on)
    r0 = trading_day(removed_on) if removed_on is not None else price.index[-1]
    end_price = removed_price if removed_price is not None else float(price.iloc[-1])
    colour = GAIN if end_price >= added_price else LOSS
    df = price.rename("Price").rename_axis("Date").reset_index()
    held = df[(df["Date"] >= a0) & (df["Date"] <= r0)]
    lo = min(float(price.min()), added_price, removed_price or added_price)
    hi = max(float(price.max()), added_price, removed_price or added_price)
    pad = (hi - lo) * 0.08 or hi * 0.02
    scale = alt.Scale(domain=[lo - pad, hi + pad], zero=False, nice=False)
    y = alt.Y("Price:Q", title=None, scale=scale)
    x = alt.X("Date:T", title=None)
    layers = [alt.Chart(df).mark_line(color=OUTSIDE, strokeWidth=1.3, opacity=0.7).encode(x=x, y=y)]
    if len(held):
        layers += [alt.Chart(held).mark_area(color=colour, opacity=0.15, clip=True).encode(
                       x=x, y=y, y2=alt.datum(lo - pad)),     # shade down to the chart floor, not 0
                   alt.Chart(held).mark_line(color=colour, strokeWidth=2).encode(x=x, y=y)]
    if avg is not None:
        a = avg.dropna().rename("Avg").rename_axis("Date").reset_index()
        layers.append(alt.Chart(a).mark_line(color="#818CF8", strokeDash=[5, 4], strokeWidth=1.3)
                      .encode(x=x, y=alt.Y("Avg:Q", title=None, scale=scale)))
    marks = [{"Date": a0, "Price": float(added_price), "label": f"Added ₹{added_price:,.2f}",
              "colour": GAIN, "kind": "added"}]
    if removed_on is not None and removed_price is not None:
        marks.append({"Date": r0, "Price": float(removed_price), "label": f"Removed ₹{removed_price:,.2f}",
                      "colour": LOSS, "kind": "removed"})
    m = pd.DataFrame(marks)
    colours = alt.Color("colour:N", scale=None)
    my = alt.Y("Price:Q", scale=scale)
    top = int(m["Price"].idxmax())                # the higher dot gets its label above
    layers += [
        alt.Chart(m).mark_rule(strokeDash=[3, 3], opacity=0.6).encode(x="Date:T", color=colours),
        alt.Chart(m).mark_point(filled=True, size=80, opacity=1).encode(x="Date:T", y=my, color=colours),
        # Both labels sit to the left (the newest point is at the right edge); the higher price's
        # label goes above its dot and the lower one's below, so they never overlap.
        *[alt.Chart(m.iloc[[i]]).mark_text(align="right", dx=-8, fontWeight=600, fontSize=12,
                                           dy=-14 if i == top else 18).encode(
            x="Date:T", y=my, text="label:N", color=colours) for i in range(len(m))],
    ]
    # Hover: invisible points along the price line show the date and price.
    layers.append(alt.Chart(df).mark_point(opacity=0, size=120).encode(
        x=x, y=y, tooltip=[alt.Tooltip("Date:T", format="%d %b %Y"), alt.Tooltip("Price:Q", title="Price (₹)", format=",.2f")]))
    return alt.layer(*layers).properties(height=height)


def growth_line(ret: float, base: int = 10_000) -> str:
    return f"₹{base:,} would have become about ₹{base * (1 + ret):,.0f}"
