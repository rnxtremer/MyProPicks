import json

import altair as alt
import pandas as pd
import streamlit as st

from common import (PF_KEYS, PF_LABELS, PORTFOLIOS, config, current_review, footer, fundamentals_raw,
                    load_backtest, load_review_file, price_histories, prices_note, quotes, snapshot_file,
                    market_quotes, market_strip, with_live)
from mypropicks.backtest import cagr
from mypropicks.config import BENCHMARK_NAMES
from mypropicks.fundamentals import quarterly_summary
from mypropicks.review import keep_within

VALUATIONS = ["Undervalued", "Fair", "Overvalued", "No data"]
VAL_COLORS = ["green", "blue", "red", "gray"]
VAL_BADGE = {"Undervalued": ":green-badge[:material/trending_up: Undervalued]",
             "Fair": ":blue-badge[:material/balance: Fair]",
             "Overvalued": ":red-badge[:material/trending_down: Overvalued]",
             "No data": ":gray-badge[No data]"}

with st.container(horizontal=True, vertical_alignment="bottom"):
    st.title(":material/analytics: Portfolio analysis", width="stretch")
    refresh = st.button("Refresh prices", icon=":material/refresh:")
if refresh:
    quotes.clear()
    market_quotes.clear()
market_strip()

rev = current_review()
if rev is None:
    st.info("Run the first review from **Settings & review**.", title="No list yet")
    footer()
    st.stop()

pf = st.segmented_control("Portfolio", PF_KEYS, format_func=lambda k: PF_LABELS[k],
                          default=PF_KEYS[0], required=True, key="analysis_pf",
                          label_visibility="collapsed")
n = PORTFOLIOS[pf]["n"]
band = config()["fair_value"]["band"]
st.caption(f":material/event: Current recommended list from the **{rev.name}** review "
           f"· whether or not you hold these stocks")

lst = load_review_file(str(rev), f"list_{pf}.csv")
rk = load_review_file(str(rev), f"rankings_{pf}.csv")
if lst is None or rk is None:
    st.warning(f"The {rev.name} review didn't include {PF_LABELS[pf]}.")
    footer()
    st.stop()
rk = rk.set_index("symbol")

# Newer re-ranking (Settings → Refresh live ranks), used only for the at-risk warning.
snap_f = snapshot_file(pf)
rev_f = rev / f"rankings_{pf}.csv"
use_snap = snap_f.exists() and snap_f.stat().st_mtime > rev_f.stat().st_mtime
live = pd.read_csv(snap_f).set_index("symbol") if use_snap else rk

syms = lst["symbol"].tolist()
q = quotes(tuple(syms))
st.caption(f":material/schedule: {prices_note(q)}")
hist = with_live(price_histories(tuple(syms)), q)


def trend(s: str) -> list[float]:
    if s not in hist:
        return []
    return hist[s].dropna().tail(252).iloc[::5].round(2).tolist()


rows = []
for r in lst.itertuples():
    s = r.symbol
    k = rk.loc[s] if s in rk.index else pd.Series(dtype=object)
    ltp = q.get(s, {}).get("ltp")
    if not (pd.notna(ltp) and ltp > 0):           # no live price: use the review's
        ltp = k.get("ltp")
    fv = k.get("fair_value")
    has = pd.notna(fv) and pd.notna(ltp) and ltp > 0
    if not has:
        label = "No data"
    elif ltp < fv * (1 - band):
        label = "Undervalued"
    elif ltp > fv * (1 + band):
        label = "Overvalued"
    else:
        label = "Fair"
    hi, lo = k.get("high_52w"), k.get("low_52w")
    rows.append({
        "rank": r.rank,
        "symbol": s,
        "name": r.name,
        "sector": r.industry,
        "trend": trend(s),
        "ltp": ltp,
        "day_chg": q.get(s, {}).get("change_pct"),
        "since_added": (ltp / r.added_price - 1) if ltp and r.added_price == r.added_price else None,
        "added_on": r.added_on,
        "fair_value": fv,
        "upside": (fv / ltp - 1) if has else None,
        "valuation": label,
        "fv_methods": int(k.get("fv_n_methods") or 0),
        "fv_conf": [k.get("fv_confidence")] if isinstance(k.get("fv_confidence"), str) else [],
        "health": k.get("health"),
        "live_rank": live.at[s, "rank"] if s in live.index else None,
        "pe": k.get("pe"),
        "pb": k.get("pb"),
        "roe": k.get("roe"),
        "debt_equity": k.get("debt_equity"),
        "div_yield": k.get("dividend_yield"),
        "mcap_cr": (k.get("market_cap") or 0) / 1e7 or None,
        "from_52w_high": (ltp / hi - 1) if hi and ltp else None,
        "from_52w_low": (ltp / lo - 1) if lo and ltp else None,
    })
df = pd.DataFrame(rows)
for c in ("ltp", "day_chg", "since_added", "fair_value", "upside", "health", "live_rank", "pe", "pb",
          "roe", "debt_equity", "div_yield", "mcap_cr", "from_52w_high", "from_52w_low"):
    df[c] = pd.to_numeric(df[c], errors="coerce")  # all-blank columns would otherwise break sorting

# ---- summary strip ----
counts = df["valuation"].value_counts()
avg_h, avg_up, avg_day = df["health"].mean(), df["upside"].mean(), df["day_chg"].mean()
with st.container(horizontal=True):
    st.metric(":material/format_list_numbered: Stocks", f"{len(df)} / {n}", border=True)
    st.metric(":material/trending_up: Undervalued", int(counts.get("Undervalued", 0)), border=True)
    st.metric(":material/balance: Fair", int(counts.get("Fair", 0)), border=True)
    st.metric(":material/trending_down: Overvalued", int(counts.get("Overvalued", 0)), border=True)
    st.metric(":material/favorite: Avg health", f"{avg_h:.1f} / 5" if pd.notna(avg_h) else "—", border=True)
    st.metric(":material/target: Avg upside", f"{avg_up:+.1%}" if pd.notna(avg_up) else "—",
              border=True, help="Average gap between price and fair value")
    st.metric(":material/today: Avg day move", f"{avg_day:+.2%}" if pd.notna(avg_day) else "—",
              border=True)

cutoff = keep_within(config(), pf)
at_risk = df[df["live_rank"].notna() & (df["live_rank"] > cutoff)]["symbol"].tolist()
if at_risk:
    st.warning(f"{', '.join(at_risk)} would drop out if the review ran today "
               f"(ranked below {cutoff}).",
               title="At risk of removal", icon=":material/warning:")

# ---- how the AI did ----
PERIODS = {"1D": None, "1W": pd.DateOffset(weeks=1), "1M": pd.DateOffset(months=1),
           "3M": pd.DateOffset(months=3), "6M": pd.DateOffset(months=6), "1Y": pd.DateOffset(years=1),
           "2Y": pd.DateOffset(years=2), "Max": None}
with st.container(border=True):
    bench = BENCHMARK_NAMES[pf]
    bt = load_backtest(pf)
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown(f"**:material/show_chart: How the AI did: {PF_LABELS[pf]} vs {bench}**", width="stretch")
        period = st.segmented_control("Period", list(PERIODS), default="Max", required=True,
                                      key=f"bt_period_{pf}", label_visibility="collapsed")
    if bt is None or len(bt) < 2:
        st.caption("The 3-year comparison appears after the next monthly review.")
    else:
        if period == "1D":
            view = bt.iloc[-2:]
        elif period == "Max":
            view = bt
        else:
            view = bt[bt.index >= bt.index[-1] - PERIODS[period]]
            view = bt.loc[bt.index[max(bt.index.get_indexer([view.index[0]])[0] - 1, 0)]:]  # start the day before
        view = view / view.iloc[0] * 100          # every period starts at ₹100
        years = (view.index[-1] - view.index[0]).days / 365.25
        yearly = years > 1.05                     # CAGR only makes sense beyond a year

        def growth(col: str) -> float:
            return cagr(view[col]) if yearly else view[col].iloc[-1] / 100 - 1

        word = "CAGR" if yearly else "return"
        span = (f"Average yearly growth over {years:.1f} years" if yearly
                else f"Total change from {view.index[0]:%d %b %Y} to {view.index[-1]:%d %b %Y}")
        has_base = "baseline" in view
        ai_g, ix_g = growth("ai"), growth("index")
        with st.container(horizontal=True):
            st.metric(f":material/smart_toy: AI {word}", f"{ai_g:+.1%}", border=True, help=span)
            st.metric(f":material/account_balance: {bench} {word}", f"{ix_g:+.1%}", border=True, help=span)
            if has_base:
                base_g = growth("baseline")
                st.metric(f":material/groups: All members {word}", f"{base_g:+.1%}", border=True,
                          help=f"{span}, holding every one of today's index members in equal amounts. "
                               "It shares the simulation's advantages, so it's the fair yardstick.")
                st.metric(":material/insights: AI's real edge",
                          f"{(ai_g - base_g) * 100:+.1f} pts" + (" a year" if yearly else ""), border=True,
                          help=f"AI {word} minus the all-members {word}: what the AI's choices added")
            else:
                st.metric(":material/compare_arrows: Difference",
                          f"{(ai_g - ix_g) * 100:+.1f} pts" + (" a year" if yearly else ""), border=True,
                          help=f"AI {word} minus index {word}, in percentage points")

        names = {"ai": f"AI {PF_LABELS[pf]}", "baseline": "All members (equal weight)", "index": bench}
        order = [names[c] for c in ("ai", "baseline", "index") if c in view]
        wide = view.rename(columns=names).reset_index(names="Date")
        long = wide.melt("Date", var_name="Series", value_name="Value")
        date_fmt = "%d %b %Y"
        # Hover (or press and hold on a phone): a guide line follows the pointer and shows all values.
        hover = alt.selection_point(nearest=True, on="pointerover", fields=["Date"], empty=False,
                                    clear="pointerout")
        lines = alt.Chart(long).mark_line(strokeWidth=1.8).encode(
            x=alt.X("Date:T", title=None),
            y=alt.Y("Value:Q", title="Value of ₹100", scale=alt.Scale(zero=False)),
            color=alt.Color("Series:N", title=None, sort=order, legend=alt.Legend(orient="top", labelLimit=300, symbolType="stroke", symbolStrokeWidth=3),
                            scale=alt.Scale(domain=order, range=["#6366F1", "#F59E0B", "#94A3B8"][:len(order)])),
            strokeDash=alt.StrokeDash("Series:N", sort=order, legend=None,
                                      scale=alt.Scale(domain=order, range=[[1, 0], [6, 4], [1, 0]][:len(order)])),
        )
        dots = lines.mark_point(filled=True, size=70).encode(
            opacity=alt.condition(hover, alt.value(1), alt.value(0)))
        guide = alt.Chart(wide).mark_rule(color="#94A3B8", strokeWidth=1).encode(
            x="Date:T",
            opacity=alt.condition(hover, alt.value(0.7), alt.value(0)),
            tooltip=[alt.Tooltip("Date:T", title="Date", format=date_fmt)]
                    + [alt.Tooltip(f"{c}:Q", title=c, format=",.1f") for c in order],
        ).add_params(hover)
        st.altair_chart(alt.layer(lines, dots, guide).properties(height=320),
                        alt=f"Value of 100 rupees in the AI's {PF_LABELS[pf]} picks, in all index members "
                            f"held equally, and in the {bench}, over the chosen period")
        st.caption(f"Simulated from {bt.index[0]:%b %Y} to {bt.index[-1]:%b %Y}; each period starts at ₹100. "
                   "Hover over the chart (or press and hold on a phone) to read the values. At each month-end the AI "
                   f"picks its top {n} using only the prices and published results available then, "
                   "keeps each one until it falls below the holding buffer, and replaces leavers with "
                   "the best new picks, splitting the money equally. Because it uses today's index members, "
                   "holds equal amounts and counts dividends (the index doesn't), even buying every member "
                   "beats the index — so compare the AI with the dashed **all members** line to see what "
                   "its choices added. No costs or taxes. Past results don't promise future returns.")

# ---- main table ----
view = df.copy()
for c in ("day_chg", "since_added", "upside", "roe", "div_yield", "from_52w_high", "from_52w_low"):
    view[c] = view[c] * 100
view["valuation"] = view["valuation"].map(lambda v: [v])

COLUMN_SETS = {
    "Overview": ["rank", "symbol", "name", "sector", "trend", "ltp", "day_chg", "since_added",
                 "valuation", "health"],
    "Valuation": ["rank", "symbol", "ltp", "fair_value", "upside", "valuation", "fv_conf",
                  "fv_methods", "pe", "pb", "div_yield"],
    "Fundamentals": ["rank", "symbol", "sector", "health", "roe", "debt_equity", "mcap_cr",
                     "from_52w_high", "from_52w_low"],
}
with st.container(horizontal=True, vertical_alignment="center"):
    st.subheader("Stocks in the list", width="stretch")
    cols_view = st.segmented_control("View", list(COLUMN_SETS), default="Overview", required=True,
                                     key=f"cols_{pf}", label_visibility="collapsed")


def _sign_color(v):
    if pd.isna(v) or v == 0:
        return ""
    return "color: #16A34A" if v > 0 else "color: #DC2626"


styled = view.style.map(_sign_color, subset=["day_chg", "since_added", "upside",
                                             "from_52w_high"])
st.dataframe(
    styled, hide_index=True, height=min(35 * (len(view) + 1) + 3, 760),
    column_order=COLUMN_SETS[cols_view],
    column_config={
        "rank": st.column_config.NumberColumn("#", width="small"),
        "symbol": st.column_config.TextColumn("Stock", pinned=True),
        "name": st.column_config.TextColumn("Company"),
        "sector": st.column_config.TextColumn("Sector"),
        "trend": st.column_config.AreaChartColumn("1-year trend", width="medium",
                                                  help="Weekly closes over the last year"),
        "ltp": st.column_config.NumberColumn("LTP", format="₹%.2f"),
        "day_chg": st.column_config.NumberColumn("Day %", format="%+.2f%%"),
        "since_added": st.column_config.NumberColumn("Since added %", format="%+.1f%%",
                                                     help="Change since the stock entered the list"),
        "fair_value": st.column_config.NumberColumn("Fair value", format="₹%.0f"),
        "upside": st.column_config.NumberColumn("Upside %", format="%+.1f%%"),
        "valuation": st.column_config.MultiselectColumn("Valuation", options=VALUATIONS,
                                                        color=VAL_COLORS),
        "fv_methods": st.column_config.NumberColumn("Methods", format="%d",
                                                    help="How many valuation methods were averaged"),
        "fv_conf": st.column_config.MultiselectColumn(
            "Confidence", options=["High", "Medium", "Low", "None"],
            color=["#16A34A", "#2563EB", "#DC2626", "#6B7280"],
            help="How closely the valuation methods agree. Low means treat the fair value with care."),
        "health": st.column_config.ProgressColumn("Health", min_value=0, max_value=5, format="%.1f"),
        "pe": st.column_config.NumberColumn("P/E", format="%.1f"),
        "pb": st.column_config.NumberColumn("P/B", format="%.1f"),
        "roe": st.column_config.NumberColumn("ROE %", format="%.1f%%"),
        "debt_equity": st.column_config.NumberColumn("Debt/Eq", format="%.2f"),
        "div_yield": st.column_config.NumberColumn("Div yield %", format="%.2f%%"),
        "mcap_cr": st.column_config.NumberColumn("Mcap (₹ cr)", format="%,.0f"),
        "from_52w_high": st.column_config.NumberColumn("vs 52w high", format="%+.1f%%"),
        "from_52w_low": st.column_config.NumberColumn("vs 52w low", format="%+.1f%%"),
    },
    alt=f"{PF_LABELS[pf]} current list with valuation and health",
)

# ---- mix and best value ----
with st.container(border=True):
    st.markdown("**:material/pie_chart: Sector mix**")
    mix = df["sector"].value_counts().rename_axis("Sector").reset_index(name="Stocks")
    bars = alt.Chart(mix).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X("Stocks:Q", title=None, axis=alt.Axis(tickMinStep=1, format="d")),
        y=alt.Y("Sector:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
        tooltip=["Sector", "Stocks"],
    )
    labels = bars.mark_text(align="left", dx=6, color="#94A3B8", fontWeight=600).encode(text="Stocks:Q")
    st.altair_chart((bars + labels).properties(height=max(200, 32 * len(mix))),
                    alt="Number of stocks per sector")

with st.container(border=True):
    st.markdown("**:material/sell: Biggest gap to fair value**")
    best = df[df["valuation"] == "Undervalued"].nlargest(5, "upside")
    if best.empty:
        st.caption("No undervalued stocks in this list right now.")
    else:
        top = best[["symbol", "name", "sector", "ltp", "fair_value", "upside"]].assign(
            upside=best["upside"] * 100)
        st.dataframe(top, hide_index=True, height=35 * (len(top) + 1) + 3,
                     column_config={"symbol": st.column_config.TextColumn("Stock", pinned=True),
                                    "name": st.column_config.TextColumn("Company", width="medium"),
                                    "sector": "Sector",
                                    "ltp": st.column_config.NumberColumn("LTP", format="₹%.2f"),
                                    "fair_value": st.column_config.NumberColumn("Fair value", format="₹%.0f"),
                                    "upside": st.column_config.ProgressColumn(
                                        "Upside", format="%+.0f%%", min_value=0,
                                        max_value=max(100.0, float(top["upside"].max())))},
                     alt="Five most undervalued stocks in the list")
    st.caption(f"Undervalued means the price is more than {band:.0%} below fair value; "
               f"Fair is within ±{band:.0%}.")

# ---- detail card ----
st.subheader("Stock detail")
pick = st.selectbox("Choose a stock", syms, format_func=lambda s: f"{s} — {df.set_index('symbol').at[s, 'name']}",
                    key=f"detail_{pf}")
if pick:
    k = rk.loc[pick]
    row = df.set_index("symbol").loc[pick]
    with st.container(border=True):
        st.markdown(f"### {row['name']}")
        st.markdown(f":violet-badge[:material/tag: {pick}] :gray-badge[:material/category: {row['sector']}] "
                    f":orange-badge[:material/military_tech: Rank {int(row['rank'])} of {n}] "
                    f"{VAL_BADGE[row['valuation']]}")
        with st.container(horizontal=True):
            st.metric("LTP", f"₹{row['ltp']:,.2f}" if pd.notna(row["ltp"]) else "—",
                      f"{row['day_chg']:+.2%}" if pd.notna(row["day_chg"]) else None, border=True)
            st.metric("Fair value", f"₹{row['fair_value']:,.0f}" if pd.notna(row["fair_value"]) else "—",
                      f"{row['upside']:+.1%}" if pd.notna(row["upside"]) else None, border=True,
                      help=f"{row['valuation']}, based on {row['fv_methods']} method(s). "
                           f"Confidence: {(row['fv_conf'] or ['not rated'])[0]}")
            st.metric("Health score", f"{row['health']:.1f} / 5" if pd.notna(row["health"]) else "—",
                      border=True)
            st.metric("Since added", f"{row['since_added']:+.1%}" if pd.notna(row["since_added"]) else "—",
                      border=True, help=f"Entered the list on {row['added_on']}")

        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("**:material/show_chart: Price vs 200-day average**")
            if pick in hist:
                h = hist[[pick]].dropna().rename(columns={pick: "Price"})
                h["200-day average"] = h["Price"].rolling(200).mean()
                st.line_chart(h.tail(252), height=280,
                              alt=f"{pick} price over the last year with its 200-day average")
            else:
                st.caption("No price history.")
        with c2:
            cats = pd.DataFrame({
                "category": ["Profitability", "Growth", "Cash flow", "Relative value", "Momentum"],
                "score": [k.get(c) for c in ("profitability", "growth", "cash_flow", "relative_value", "momentum")],
            })
            st.markdown("**:material/insights: Category scores (0–100)**")
            st.bar_chart(cats, x="category", y="score", horizontal=True, height=280, x_label="", y_label="",
                         alt="Score per category")

        c3, c4 = st.columns(2)
        with c3:
            st.markdown("**:material/calculate: Fair value by method**")
            methods = json.loads(k.get("fv_methods") or "{}")
            names = {"own_pe": "Its own past P/E", "own_pb": "Its own past P/B",
                     "sector_pe": "Sector P/E", "sector_pb": "Sector P/B", "sector_ev_ebitda": "Sector EV/EBITDA",
                     "dcf": "Discounted cash flow", "analyst_target": "Analyst target"}
            fv_w = config()["fair_value"].get("weights", {})
            if methods:
                st.table({f"{names.get(m, m)} (×{fv_w.get(m, 1):g})": f"₹{v:,.0f}"
                          for m, v in methods.items()}, border="horizontal")
                conf = (row["fv_conf"] or [None])[0]
                if conf:
                    st.caption(f"Confidence **{conf}**: "
                               + {"High": "the methods agree closely.",
                                  "Medium": "the methods roughly agree.",
                                  "Low": "the methods disagree, so treat this fair value with care.",
                                  "None": "no method had data."}.get(conf, ""))
            else:
                st.caption("Not enough data for a fair value.")
        with c4:
            st.markdown("**:material/bar_chart: Last 4 quarters (₹ cr)**")
            raw = fundamentals_raw(pick)
            qs = quarterly_summary(raw) if raw else []
            if qs:
                qd = pd.DataFrame(qs)
                qd["Revenue"] = qd["revenue"] / 1e7
                qd["Net profit"] = qd["net_profit"] / 1e7
                st.bar_chart(qd, x="quarter", y=["Revenue", "Net profit"], stack=False, height=260,
                             x_label="", y_label="",
                             alt=f"{pick} quarterly revenue and net profit")
            else:
                st.caption("No quarterly data.")
        if k.get("low_data"):
            st.caption(":material/warning: Low data: this stock was scored on under 60% of the metrics.")

footer()
