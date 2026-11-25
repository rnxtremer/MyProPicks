import streamlit as st

st.set_page_config(page_title="MyProPicks", page_icon=":material/insights:", layout="wide")

pages = [
    st.Page("app_pages/analysis.py", title="Portfolio analysis", icon=":material/analytics:", default=True),
    st.Page("app_pages/this_month.py", title="This month", icon=":material/event:"),
    st.Page("app_pages/holdings.py", title="My holdings & P&L", icon=":material/account_balance_wallet:"),
    st.Page("app_pages/log_trade.py", title="Log a trade", icon=":material/edit_note:"),
    st.Page("app_pages/rankings.py", title="Full rankings", icon=":material/leaderboard:"),
    st.Page("app_pages/settings.py", title="Settings & review", icon=":material/settings:"),
    st.Page("app_pages/how_it_works.py", title="How it works", icon=":material/school:"),
]
st.navigation(pages).run()
