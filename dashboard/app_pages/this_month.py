import streamlit as st

from common import PF_KEYS, PF_LABELS, PORTFOLIOS, current_review, footer, load_review_file

st.title("This month's changes")

rev = current_review()
if rev is None:
    st.info("No review yet. Go to **Settings & review** and press **Run review now**.", title="Nothing to show")
    footer()
    st.stop()

st.caption(f"Review date: **{rev.name}**. Prices are the closes before the review. Place trades on the next trading day.")

cols = st.columns(3)
for col, pf in zip(cols, PF_KEYS):
    ch = load_review_file(str(rev), f"changes_{pf}.csv")
    n_sell = int((ch["action"] == "SELL").sum()) if ch is not None else 0
    n_buy = int((ch["action"] == "BUY").sum()) if ch is not None else 0
    col.metric(PF_LABELS[pf], f"{n_buy} in · {n_sell} out", border=True,
               help=f"{PORTFOLIOS[pf]['n']} stocks from {PORTFOLIOS[pf]['index_name']}")

for pf in PF_KEYS:
    ch = load_review_file(str(rev), f"changes_{pf}.csv")
    with st.container(border=True):
        st.subheader(PF_LABELS[pf])
        if ch is None:
            st.caption("This portfolio wasn't part of this review.")
            continue
        if ch.empty:
            st.success("No changes this month. Keep the list as it is.")
            continue
        left, right = st.columns(2)
        cfg = {
            "symbol": st.column_config.TextColumn("Stock"),
            "reason": st.column_config.TextColumn("Why"),
            "qty": st.column_config.NumberColumn("Qty", format="%d"),
            "price": st.column_config.NumberColumn("Last close", format="₹%.2f"),
        }
        with left:
            st.markdown(":red[**Sell**]")
            sells = ch[ch["action"] == "SELL"].drop(columns="action")
            if sells.empty:
                st.caption("Nothing to sell.")
            else:
                st.dataframe(sells, hide_index=True, column_config=cfg, alt=f"{PF_LABELS[pf]} sells")
        with right:
            st.markdown(":green[**Buy**]")
            buys = ch[ch["action"] == "BUY"].drop(columns="action")
            st.dataframe(buys, hide_index=True, column_config=cfg, alt=f"{PF_LABELS[pf]} buys")

with st.expander("Full review summary"):
    st.markdown((rev / "summary.md").read_text(encoding="utf-8"))

footer()
