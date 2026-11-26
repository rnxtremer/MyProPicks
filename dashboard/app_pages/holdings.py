import pandas as pd
import streamlit as st

from common import (PF_KEYS, PF_LABELS, PORTFOLIOS, config, current_review, fmt_inr, footer, my_moves,
                    prices_note, quotes, require_unlock, trades, with_live)
from mypropicks import ledger
from mypropicks.config import BENCHMARK_NAMES, BENCHMARKS
from mypropicks.history import value_over_time
from mypropicks.prices import get_prices, index_history

require_unlock()
st.title("My holdings & P&L")
st.caption("Built from the trades you logged. The average-cost method is used, as Indian brokers do.")

t = trades()
cfg = config()


def your_moves() -> None:
    """Your own sells and buys for the latest review, with suggested quantities."""
    rev = current_review()
    if rev is None:
        return
    with st.container(border=True):
        st.subheader(":material/swap_horiz: Your moves this month")
        st.caption(f"From the **{rev.name}** review, compared with what you hold. Quantities use "
                   "your sale proceeds and spare cash, or your capital if you hold nothing yet.")
        tabs = st.tabs([PF_LABELS[pf] for pf in PF_KEYS])
        cols = {"symbol": "Stock", "reason": "Why",
                "qty": st.column_config.NumberColumn("Qty", format="%g"),
                "price": st.column_config.NumberColumn("Last close", format="₹%.2f")}
        for tab, pf in zip(tabs, PF_KEYS):
            with tab:
                ch, warnings = my_moves(rev, pf)
                if ch is None:
                    st.caption("This portfolio wasn't part of the latest review.")
                    continue
                for w in warnings:
                    st.warning(w)
                if ch.empty:
                    st.success("Nothing to change. Your portfolio matches the list.")
                    continue
                left, right = st.columns(2)
                for col, action, colour in ((left, "SELL", "red"), (right, "BUY", "green")):
                    with col:
                        part = ch[ch["action"] == action].drop(columns="action")
                        if part["qty"].isna().all():
                            part = part.drop(columns="qty")
                        st.markdown(f":{colour}[**{action.title()} {len(part)}**]")
                        if part.empty:
                            st.caption("Nothing.")
                        else:
                            st.dataframe(part, hide_index=True, column_config=cols,
                                         alt=f"{PF_LABELS[pf]}: stocks to {action.lower()}")
                if not float(cfg["capital"].get(pf) or 0) and t[t["portfolio"] == pf].empty:
                    st.caption("Set your capital in **Settings & review** to get quantities.")


your_moves()
if t.empty:
    st.info("No trades logged yet. Use the **Log a trade** page to record your first buy.", title="Nothing logged")
    footer()
    st.stop()

if st.button("Refresh prices", icon=":material/refresh:"):
    quotes.clear()

held_all = sorted({s for pf in PF_KEYS for s in ledger.held_symbols(t, pf)})
q = quotes(tuple(held_all))
st.caption(f":material/schedule: {prices_note(q)}")
ltp = {s: v["ltp"] for s, v in q.items()}

# ---- totals ----
summ = {pf: ledger.pnl(t, pf, ltp, float(cfg["capital"].get(pf) or 0)) for pf in PF_KEYS}
tot_inv = sum(s["invested"] for s in summ.values())
tot_val = sum(s["value"] for s in summ.values())
tot_real = sum(s["realised"] for s in summ.values())
with st.container(horizontal=True):
    st.metric("Invested", fmt_inr(tot_inv), border=True)
    st.metric("Current value", fmt_inr(tot_val), border=True)
    st.metric("Unrealised P&L", fmt_inr(tot_val - tot_inv),
              f"{(tot_val / tot_inv - 1):+.2%}" if tot_inv else None, border=True)
    st.metric("Realised P&L", fmt_inr(tot_real), border=True)

for pf in PF_KEYS:
    s = summ[pf]
    n = PORTFOLIOS[pf]["n"]
    with st.container(border=True):
        st.subheader(PF_LABELS[pf])
        if s["positions"] == 0 and s["realised"] == 0:
            st.caption("No trades in this portfolio yet.")
            continue
        if s["positions"] != n:
            st.warning(f"This portfolio holds {s['positions']} stocks; it should hold {n}.")
        with st.container(horizontal=True):
            st.metric("Invested", fmt_inr(s["invested"]), border=True)
            st.metric("Value", fmt_inr(s["value"]), border=True)
            st.metric("Unrealised", fmt_inr(s["unrealised"]), border=True)
            st.metric("Realised", fmt_inr(s["realised"]), border=True)
            st.metric("Cash", fmt_inr(s["cash"]), border=True,
                      help="Capital from Settings, minus buys, plus sells, minus charges.")
            st.metric("Total return", f"{s['total_return_pct']:+.2f}%", border=True)

        h = ledger.holdings(t, pf)
        h = h[h["qty"] > 0].copy()
        h["ltp"] = h["symbol"].map(ltp)
        h["value"] = h["qty"] * h["ltp"].fillna(h["avg_cost"])
        h["pnl"] = h["value"] - h["invested"]
        h["pnl_pct"] = (h["pnl"] / h["invested"]) * 100
        h["weight"] = h["value"] / h["value"].sum() * 100
        st.dataframe(h, hide_index=True, alt=f"{PF_LABELS[pf]} holdings", column_config={
            "symbol": "Stock",
            "qty": st.column_config.NumberColumn("Qty", format="%g"),
            "avg_cost": st.column_config.NumberColumn("Avg cost", format="₹%.2f"),
            "invested": st.column_config.NumberColumn("Invested", format="₹%,.0f"),
            "realised": st.column_config.NumberColumn("Realised", format="₹%,.0f"),
            "ltp": st.column_config.NumberColumn("LTP", format="₹%.2f"),
            "value": st.column_config.NumberColumn("Value", format="₹%,.0f"),
            "pnl": st.column_config.NumberColumn("P&L", format="₹%,.0f"),
            "pnl_pct": st.column_config.NumberColumn("P&L %", format="%+.2f%%"),
            "weight": st.column_config.NumberColumn("Weight %", format="%.1f%%"),
        })

        with st.expander(f"Value over time vs {BENCHMARK_NAMES[pf]}", on_change="rerun") as exp:
            if exp.open:
                syms = sorted(t.loc[t["portfolio"] == pf, "symbol"].unique())
                closes = with_live(get_prices(syms)[0], q)   # reach today's live price
                v = value_over_time(t, pf, closes, float(cfg["capital"].get(pf) or 0))
                if v.empty:
                    st.caption("Not enough price history yet.")
                else:
                    chart = pd.DataFrame({"Portfolio": v["total"] / v["total"].iloc[0] * 100})
                    bench = index_history(BENCHMARKS[pf], str(v.index[0].date()))
                    if not bench.empty:
                        b = bench.reindex(v.index).ffill()
                        chart[BENCHMARK_NAMES[pf]] = b / b.dropna().iloc[0] * 100
                    else:
                        st.caption("The comparison index isn't available from Yahoo right now.")
                    st.line_chart(chart, alt=f"{PF_LABELS[pf]} value against its index, both starting at 100")
                    st.caption("Both lines start at 100 on your first trade date.")

with st.expander("All logged trades"):
    st.dataframe(t, hide_index=True, alt="Every logged trade")

footer()
