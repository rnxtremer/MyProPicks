import pandas as pd
import streamlit as st

from common import (PF_KEYS, PF_LABELS, PORTFOLIOS, current_review, explained_changes, footer, growth_line,
                    index_series, journey_chart, leavers, price_histories)
from mypropicks.config import BENCHMARK_NAMES, BENCHMARKS


def _day(d) -> str:
    d = pd.Timestamp(d)
    return f"{d.day} {d:%b %Y}"


def leavers_report(pf: str) -> None:
    """How each stock leaving the list did, from the day it was added to the day it left."""
    out = leavers(rev, pf)
    out = out[out["added_price"].notna() & out["price"].notna() & out["added_on"].notna()]
    if out.empty:
        return
    st.markdown("**:material/receipt_long: How the leaving stocks did while in the list**")
    removed_on = pd.Timestamp(rev.name)
    hist = price_histories(tuple(out["symbol"]))
    first = min(pd.Timestamp(a) for a in out["added_on"])
    bench = index_series(BENCHMARKS[pf], str((first - pd.Timedelta(days=7)).date()))
    for r in out.itertuples():
        a0 = pd.Timestamp(r.added_on)
        ret = r.price / r.added_price - 1
        days = (removed_on - a0).days
        with st.container(border=True):
            badge = (f":green-badge[:material/trending_up: {ret:+.1%}]" if ret >= 0
                     else f":red-badge[:material/trending_down: {ret:+.1%}]")
            st.markdown(f"**{r.symbol}** {badge}")
            left, right = st.columns([1, 2])
            with left:
                st.metric("Return in the list", f"{ret:+.1%}", border=True,
                          help=f"Added {_day(a0)} at ₹{r.added_price:,.2f}, left {_day(removed_on)} "
                               f"at ₹{r.price:,.2f} (last close before the review)")
                st.caption(f"{growth_line(ret)} over {days} day{'s' if days != 1 else ''}.")
                b = bench.dropna()
                if len(b) and b.index[0] <= a0:
                    b_ret = float(b.asof(removed_on)) / float(b.asof(a0)) - 1
                    st.metric(f"{BENCHMARK_NAMES[pf]} over the same days", f"{b_ret:+.1%}",
                              f"{(ret - b_ret) * 100:+.1f} pts vs index", border=True)
                st.caption(f"Why it left: {r.reason}")
            with right:
                if r.symbol in hist:
                    h = hist[r.symbol].dropna()
                    h = h[(h.index >= a0 - pd.Timedelta(days=90)) & (h.index <= removed_on + pd.Timedelta(days=30))]
                    if len(h) > 1:
                        st.altair_chart(journey_chart(h, a0, float(r.added_price), removed_on, float(r.price),
                                                      height=220),
                                        alt=f"{r.symbol} price with the day it was added and the day it left")
                else:
                    st.caption("No price history.")

st.title("This month's changes")

rev = current_review()
if rev is None:
    st.info("No review yet. Go to **Settings & review** and press **Run review now**.", title="Nothing to show")
    footer()
    st.stop()

st.caption(f"Review date: **{rev.name}**. Prices are the closes before the review. Place trades on the next trading day.")

cols = st.columns(3)
for col, pf in zip(cols, PF_KEYS):
    ch = explained_changes(str(rev), pf)
    n_sell = int((ch["action"] == "SELL").sum()) if ch is not None else 0
    n_buy = int((ch["action"] == "BUY").sum()) if ch is not None else 0
    extra = n_buy - n_sell                    # only when the list was short of stocks
    if ch is None:
        value = "Not reviewed"
    elif n_buy == 0:
        value = "No changes"
    elif n_sell == 0:
        value = f"{n_buy} added"
    else:
        value = f"{n_sell} replaced" + (f" · {extra} added" if extra > 0 else "")
    col.metric(PF_LABELS[pf], value, border=True,
               help=f"{n_sell} stock(s) left the list and {n_buy} new one(s) took their place. "
                    f"{PORTFOLIOS[pf]['n']} stocks from {PORTFOLIOS[pf]['index_name']}.")

for pf in PF_KEYS:
    ch = explained_changes(str(rev), pf)
    with st.container(border=True):
        st.subheader(PF_LABELS[pf])
        if ch is None:
            st.caption("This portfolio wasn't part of this review.")
            continue
        if ch.empty:
            st.success("No changes this month. Keep the list as it is.")
            continue
        left, right = st.container(), st.container()   # stacked: the reasons need the full width
        cfg = {
            "symbol": st.column_config.TextColumn("Stock"),
            "reason": st.column_config.TextColumn("Why", width="large"),
            "price": st.column_config.NumberColumn("Last close", format="₹%.2f"),
        }
        with left:
            st.markdown(":red[**Sell**]")
            sells = ch[ch["action"] == "SELL"].drop(columns=["action", "qty", "added_on", "added_price"], errors="ignore")
            if sells.empty:
                st.caption("Nothing to sell.")
            else:
                st.dataframe(sells, hide_index=True, column_config=cfg, alt=f"{PF_LABELS[pf]} sells")
        with right:
            st.markdown(":green[**Buy**]")
            buys = ch[ch["action"] == "BUY"].drop(columns=["action", "qty", "added_on", "added_price"], errors="ignore")
            st.dataframe(buys, hide_index=True, column_config=cfg, alt=f"{PF_LABELS[pf]} buys")
        leavers_report(pf)

with st.expander("Full review summary"):
    st.markdown((rev / "summary.md").read_text(encoding="utf-8"))

footer()
