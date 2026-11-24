from datetime import date

import streamlit as st

from common import PF_KEYS, PF_LABELS, current_review, footer, load_review_file, trades
from mypropicks import ledger

st.title("Log a trade")
st.caption("Record each trade you actually placed with your broker. Holdings and P&L come from these.")

rev = current_review()
suggest = {}
if rev:
    for pf in PF_KEYS:
        ch = load_review_file(str(rev), f"changes_{pf}.csv")
        if ch is not None:
            suggest[pf] = ch

with st.form("trade", clear_on_submit=True):
    c1, c2 = st.columns(2)
    pf = c1.selectbox("Portfolio", PF_KEYS, format_func=lambda k: PF_LABELS[k])
    action = c2.segmented_control("Action", ["BUY", "SELL"], default="BUY", required=True)
    c3, c4, c5 = st.columns(3)
    symbol = c3.text_input("NSE symbol", placeholder="e.g. TCS")
    qty = c4.number_input("Quantity", min_value=0.0, step=1.0, format="%g")
    price = c5.number_input("Price per share (₹)", min_value=0.0, step=0.05, format="%.2f")
    c6, c7 = st.columns(2)
    when = c6.date_input("Trade date", value=date.today(), max_value=date.today())
    charges = c7.number_input("Charges (brokerage, STT, etc.) ₹", min_value=0.0, step=1.0)
    note = st.text_input("Note (optional)")
    ok = st.form_submit_button("Save trade", type="primary", icon=":material/save:")

if ok:
    try:
        row = ledger.append_trade(when, pf, symbol, action, qty, price, charges, note)
    except ValueError as e:
        st.error(str(e), title="Not saved")
    else:
        st.success(f"{row['action']} {row['qty']:g} {row['symbol']} @ ₹{row['price']:,.2f} in "
                   f"{PF_LABELS[row['portfolio']]} on {row['date']}.", title="Saved")

if suggest:
    with st.expander("This month's suggested trades (for reference)"):
        for k, ch in suggest.items():
            if not ch.empty:
                st.markdown(f"**{PF_LABELS[k]}**")
                st.dataframe(ch, hide_index=True, alt=f"{PF_LABELS[k]} suggested trades")

st.subheader("Recent trades")
t = trades()
if t.empty:
    st.caption("No trades yet.")
else:
    st.dataframe(t.tail(20).iloc[::-1], hide_index=True, alt="The 20 most recent trades")
    st.caption("To fix a mistake, remove the wrong line from data/trades.csv (in your GitHub repo when using the cloud app).")

footer()
