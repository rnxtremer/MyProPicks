import streamlit as st

from common import PF_KEYS, PF_LABELS, PORTFOLIOS, footer, load_review_file, review_dirs

st.title("Full rankings")
st.caption("Every stock in each universe, with every score, from any past review.")

dirs = review_dirs()
if not dirs:
    st.info("No reviews yet.", title="Nothing to show")
    footer()
    st.stop()

c1, c2 = st.columns([1, 2], vertical_alignment="bottom")
rev = c1.selectbox("Review", dirs, format_func=lambda p: p.name)
pf = c2.segmented_control("Portfolio", PF_KEYS, format_func=lambda k: PF_LABELS[k],
                          default=PF_KEYS[0], required=True, key="rank_pf")
df = load_review_file(str(rev), f"rankings_{pf}.csv")
if df is None:
    st.warning("This review didn't include that portfolio.")
    footer()
    st.stop()

n = PORTFOLIOS[pf]["n"]
only_elig = st.toggle("Only eligible stocks", value=False)
if only_elig:
    df = df[df["eligible"]]
df = df.assign(in_list=df["rank"] <= n)
cols = ["rank", "in_list", "symbol", "name", "sector", "score", "health", "profitability", "growth",
        "cash_flow", "relative_value", "momentum", "ltp", "fair_value", "fv_label", "eligible",
        "reason", "low_data", "fetch_note"]
st.dataframe(
    df[[c for c in cols if c in df.columns]], hide_index=True, height=700,
    alt=f"Full ranking for {PF_LABELS[pf]}",
    column_config={
        "rank": st.column_config.NumberColumn("#", format="%d"),
        "in_list": st.column_config.CheckboxColumn(f"Top {n}"),
        "symbol": st.column_config.TextColumn("Stock", pinned=True),
        "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
        "health": st.column_config.NumberColumn("Health /5", format="%.1f"),
        "profitability": st.column_config.NumberColumn("Profit.", format="%.0f"),
        "growth": st.column_config.NumberColumn("Growth", format="%.0f"),
        "cash_flow": st.column_config.NumberColumn("Cash flow", format="%.0f"),
        "relative_value": st.column_config.NumberColumn("Value", format="%.0f"),
        "momentum": st.column_config.NumberColumn("Momentum", format="%.0f"),
        "ltp": st.column_config.NumberColumn("Close", format="₹%.2f"),
        "fair_value": st.column_config.NumberColumn("Fair value", format="₹%.0f"),
        "fv_label": "Valuation",
        "reason": "Why ineligible",
        "low_data": st.column_config.CheckboxColumn("Low data"),
        "fetch_note": "Data issue",
    },
)
st.download_button("Download CSV", df.to_csv(index=False), file_name=f"rankings_{pf}_{rev.name}.csv",
                   icon=":material/download:")
footer()
