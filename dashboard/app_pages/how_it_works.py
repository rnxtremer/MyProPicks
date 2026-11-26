import pandas as pd
import streamlit as st

from common import PORTFOLIOS, config, footer
from mypropicks.config import DISCLAIMER
from mypropicks.review import keep_within

cfg = config()
w = cfg["weights"]
liq = cfg["liquidity_cr"]
fv = cfg["fair_value"]
UNIVERSE = {"nifty20": "Nifty 100", "midcap30": "Nifty Midcap 150", "smallcap50": "Nifty Smallcap 250"}

st.title(":material/school: How MyProPicks works")
st.markdown(
    "MyProPicks is your own rules-based stock picker, modelled on ProPicks. Every month it ranks "
    "every stock in three NSE indices, keeps the best ones in three model portfolios, and tells you "
    "exactly which stocks to **sell** and which to **buy** so each portfolio stays complete."
)
st.markdown(":violet-badge[:material/rule: Fixed rules, no guesswork] "
            ":blue-badge[:material/calendar_month: Reviewed on the 1st of every month] "
            ":green-badge[:material/savings: Free data, no subscription] "
            ":orange-badge[:material/person: You place the trades yourself]")

# ---- the three portfolios ----
st.subheader("The three portfolios")
with st.container(horizontal=True):
    for key, p in PORTFOLIOS.items():
        with st.container(border=True):
            st.markdown(f"#### {p['label']}")
            st.markdown(f"**{p['n']} stocks** picked from the **{UNIVERSE.get(key, p['index_name'])}**")
            st.caption(f"Liquidity floor: ₹{liq[key]} cr traded on a typical day")

# ---- the monthly cycle ----
st.subheader("The monthly cycle")
steps = [
    (":material/download:", "1. Fetch", "Downloads NSE's latest index lists, prices (a year daily, 5 years monthly) and each company's financials."),
    (":material/fact_check:", "2. Check", "Drops stocks that fail NSE-style trading checks."),
    (":material/leaderboard:", "3. Score", "Scores every stock in 5 areas and ranks them."),
    (":material/swap_horiz:", "4. Compare", "Compares the new top N with last month's list, and with what you hold on your private page."),
    (":material/receipt_long:", "5. Report", "Writes the SELL and BUY list with reasons, and updates the 3-year AI vs index chart."),
    (":material/edit_note:", "6. You act", "You place the trades with your broker and log them here."),
]
with st.container(horizontal=True):
    for icon, title, text in steps:
        with st.container(border=True, height="stretch"):
            st.markdown(f"**{icon} {title}**")
            st.caption(text)

tabs = st.tabs([":material/fact_check: Eligibility", ":material/leaderboard: Scoring",
                ":material/balance: Fair value", ":material/swap_horiz: Monthly changes",
                ":material/show_chart: How the AI did",
                ":material/account_balance_wallet: Your trades & P&L",
                ":material/dashboard: Dashboard pages", ":material/info: Data & limits"])

# ---- eligibility ----
with tabs[0]:
    st.markdown("Before any scoring, a stock must pass the same kind of checks NSE uses for its "
                "indices. A stock that fails any of them is ranked **below every eligible stock**, "
                "so it can't make the list.")
    st.table({
        ":material/list: In the index": "It's in NSE's current constituent list for that index",
        ":material/history: Enough history": "At least 250 trading days (about a year) of prices",
        ":material/event_available: Trades every day": "Traded on every one of the last 126 sessions (about 6 months)",
        ":material/water_drop: Liquid enough": f"Median daily traded value over the last 63 sessions of at least "
                                               f"₹{liq['nifty20']} cr (Nifty 20), ₹{liq['midcap30']} cr (Midcap 30), "
                                               f"₹{liq['smallcap50']} cr (Smallcap 50)",
    }, border="horizontal")
    st.caption("Each portfolio is compared only with the other stocks in its own index.")

# ---- scoring ----
with tabs[1]:
    st.markdown("Each eligible stock gets a **score from 0 to 100 in five areas**. Within an area, every "
                "measure is turned into a percentile: 100 means the best in the index, 0 the worst. "
                "The area score is the average of its measures, and the total is a weighted average "
                "of the five areas.")
    areas = pd.DataFrame([
        ("Momentum", w["momentum"], "12-month return (skipping the last month), 6-month return, price vs its 200-day average, lower volatility"),
        ("Profitability", w["profitability"], "Return on equity (ROE), return on capital (ROCE), operating margin, net margin"),
        ("Growth", w["growth"], "3-year revenue growth, latest revenue growth, EPS growth, operating profit growth"),
        ("Relative value", w["relative_value"], "Upside to fair value, P/E vs sector median, P/B vs sector median (cheaper is better)"),
        ("Cash flow", w["cash_flow"], "Operating cash vs net profit, free-cash-flow yield, lower debt-to-equity, interest cover"),
    ], columns=["Area", "Weight", "What it measures"]).sort_values("Weight", ascending=False)
    areas["Weight"] = areas["Weight"] * 100
    st.dataframe(areas, hide_index=True,
                 column_config={"Weight": st.column_config.ProgressColumn("Weight", format="%.0f%%",
                                                                          min_value=0, max_value=30),
                                "What it measures": st.column_config.TextColumn(width="large")},
                 alt="The five scoring areas and their weights")
    c1, c2 = st.columns(2)
    with c1.container(border=True, height="stretch"):
        st.markdown("**:material/sort: How the rank is decided**")
        st.markdown("- Highest total score is rank 1.\n"
                    "- Ties go to the stronger momentum, then the bigger company.\n"
                    "- Top 20 / 30 / 50 make the list.\n"
                    "- **Health score** = total score ÷ 20, so it runs from 0 to 5.")
    with c2.container(border=True, height="stretch"):
        st.markdown("**:material/shield: Fairness rules**")
        st.markdown("- Loss-makers (negative earnings or book value) score 0 on P/E and P/B.\n"
                    "- If a whole area has no data, its weight is shared among the others.\n"
                    "- Under 60% of measures available → the stock is flagged **low data**.")
    st.caption("You can change the weights in `config.yaml` under `weights`.")

# ---- fair value ----
with tabs[2]:
    fw = fv.get("weights", {})
    st.markdown("Fair value is a **weighted average of up to six valuation methods**. Each one "
                "estimates what a share is worth; methods that proved more reliable count more.")
    st.dataframe(pd.DataFrame([
        ("Its own past P/E", fw.get("own_pe", 1), "Today's earnings per share × the P/E the stock itself traded at, at each of its last few year-ends (the median)"),
        ("Its own past P/B", fw.get("own_pb", 1), "Today's book value per share × the P/B the stock itself traded at in past years"),
        ("Analyst target", fw.get("analyst_target", 1), f"The average analyst price target; counts once if fewer than {fv.get('analyst_min', 5)} analysts cover the stock"),
        ("Sector P/E", fw.get("sector_pe", 1), "Earnings per share × the median P/E of its sector"),
        ("Sector P/B", fw.get("sector_pb", 1), "Book value per share × the median P/B of its sector"),
        ("Sector EV/EBITDA", fw.get("sector_ev_ebitda", 1), "EBITDA × the sector's median EV/EBITDA, minus net debt, per share"),
    ], columns=["Method", "Counts", "How it works"]), hide_index=True,
        column_config={"Counts": st.column_config.NumberColumn("Counts", format="×%g"),
                       "How it works": st.column_config.TextColumn(width="large")},
        alt="Fair value methods and how much each counts")
    st.markdown("- **Why these weights:** checked against analysts' targets on about 500 NSE stocks, a "
                "stock's own past P/E and P/B were the most reliable guides, sector multiples less so. "
                "A discounted-cash-flow model on free data was far off (typically about 3× too low), "
                "so it's left out.\n"
                "- **Geometric average:** one very high estimate can't drag the result as far as an "
                "ordinary average would.\n"
                "- **Confidence:** **High** when 3 or more methods agree within 1.6×, **Medium** within "
                "2.5×, otherwise **Low**. A Low-confidence fair value is a rough guess.")
    c1, c2, c3 = st.columns(3)
    with c1.container(border=True, height="stretch"):
        st.markdown(":green-badge[:material/trending_up: Undervalued]")
        st.caption(f"Price is more than {fv['band']:.0%} below fair value.")
    with c2.container(border=True, height="stretch"):
        st.markdown(":blue-badge[:material/balance: Fair]")
        st.caption(f"Price is within ±{fv['band']:.0%} of fair value.")
    with c3.container(border=True, height="stretch"):
        st.markdown(":red-badge[:material/trending_down: Overvalued]")
        st.caption(f"Price is more than {fv['band']:.0%} above fair value.")
    st.markdown("- **Odd results are dropped:** with 3 or more methods, any method more than 3× or under ⅓ "
                "of their median is ignored.\n"
                "- **Banks and lenders** skip EV/EBITDA, because borrowing is their raw material and it "
                "gives nonsense for them.\n"
                "- **It's an estimate, not a true price.** Nobody knows a stock's real fair value; treat "
                "this as one guide among many.")

# ---- monthly changes ----
with tabs[3]:
    st.markdown("On the 1st of each month the review builds the new top N and compares it with your "
                "portfolio. The rules are strict and simple:")
    c1, c2 = st.columns(2)
    with c1.container(border=True, height="stretch"):
        st.markdown("**:red[:material/remove_circle: A stock is sold when…]**")
        st.markdown(f"- it has **fallen below rank {keep_within(cfg, 'nifty20')} / "
                    f"{keep_within(cfg, 'midcap30')} / {keep_within(cfg, 'smallcap50')}** "
                    "(the holding buffer, see below),\n"
                    "- it **failed an eligibility check**, or\n"
                    "- it **left the index** altogether.")
    with c2.container(border=True, height="stretch"):
        st.markdown("**:green[:material/add_circle: A stock is bought when…]**")
        st.markdown("- it's in the new top N and you don't hold it yet.\n"
                    "- Buys are taken from the highest ranks first.")
    st.markdown(f"**:material/shield: The holding buffer.** A stock that's already in the list isn't "
                f"sold the moment it slips to rank 21. It stays until it falls below rank "
                f"**{keep_within(cfg, 'nifty20')}** (Nifty 20), **{keep_within(cfg, 'midcap30')}** "
                f"(Midcap 30) or **{keep_within(cfg, 'smallcap50')}** (Smallcap 50). New stocks still "
                "come from the very top. Tested over 3 years with Indian trading costs and tax, this "
                "roughly halved the number of swaps, kept stocks about a year instead of six months "
                "(so more gains are taxed as long-term, at 12.5% instead of 20%), and improved the "
                "after-tax result on average.")
    st.info("The number of buys always equals the number of sells, plus any gap if the portfolio was "
            "short. So the Nifty 20 always ends with 20 stocks, Midcap 30 with 30, Smallcap 50 with 50.",
            title="The portfolio always stays complete", icon=":material/check_circle:")
    st.markdown(f"**Example:** last month's Nifty 20 held stock A at rank 8. This month A ranks 24: "
                f"still within the buffer, so it's **kept**. If it had fallen to rank 35, the review "
                f"would say **SELL A — dropped to rank 35 (below {keep_within(cfg, 'nifty20')})** and "
                "**BUY** the highest-ranked stock you don't own.")
    st.markdown("**What it compares against:** the review itself always compares with last month's "
                "list, so the published lists are the model portfolio. **Your moves** on the "
                "*My holdings & P&L* page compare the new list with the stocks you actually hold.")
    st.markdown("**Safety nets:**\n"
                "- If a held stock's price can't be downloaded, it's **kept** (not sold) and you get a warning.\n"
                "- If fewer than N stocks are eligible, the list is filled with the next best and you're warned.\n"
                "- On *My holdings & P&L*, each of your buys gets a **suggested quantity**: your sale "
                "proceeds and spare cash (or your capital, if you hold nothing yet) are split equally "
                "and rounded down to whole shares.")

# ---- how the AI did ----
with tabs[4]:
    st.markdown("Each portfolio's tab on **Portfolio analysis** has a **How the AI did** chart: what "
                "₹100 would have grown to if you had followed the AI, tracked every trading day over the "
                "last 3 years.")
    c1, c2, c3 = st.columns(3)
    with c1.container(border=True, height="stretch"):
        st.markdown("**:violet[:material/smart_toy: The AI line]**")
        st.caption("At each month-end it ranks the stocks using only the prices and annual results "
                   "available on that date. It sells stocks that fell below the holding buffer, buys the "
                   "best new ones with that money, and leaves the rest untouched, as you would.")
    with c2.container(border=True, height="stretch"):
        st.markdown("**:orange[:material/groups: All members (dashed)]**")
        st.caption("Buys every one of today's index members equally, with no choosing at all, and "
                   "rebalances back to equal amounts each month, like an index fund. It's the fair "
                   "yardstick for the AI.")
    with c3.container(border=True, height="stretch"):
        st.markdown("**:gray[:material/account_balance: The index]**")
        st.caption("Nifty 50 for the Nifty 20, Nifty Midcap 150 for the Midcap 30, Nifty Smallcap 250 "
                   "for the Smallcap 50.")
    st.markdown("**:material/touch_app: Reading the chart**")
    r1, r2 = st.columns(2)
    with r1.container(border=True, height="stretch"):
        st.markdown("**:material/date_range: Pick a period**")
        st.caption("Use the buttons next to the title: **1D, 1W, 1M, 3M, 6M, 1Y, 2Y** or **Max** "
                   "(the full 3 years). Every period restarts all three lines at ₹100, so you compare "
                   "them from the same starting point.")
    with r2.container(border=True, height="stretch"):
        st.markdown("**:material/ads_click: Hover for values**")
        st.caption("Move the mouse over the chart (or press and hold on a phone). A guide line follows "
                   "it and shows that day's date and the value of all three lines.")
    st.markdown("**The numbers above the chart** change with the period:\n"
                "- **Longer than a year:** **CAGR**, the average yearly growth, and **AI's real edge** "
                "in points *a year* (AI CAGR − all-members CAGR).\n"
                "- **A year or less:** plain **return** for that period, and the edge in points "
                "(AI return − all-members return). Yearly rates over a few days or weeks would be "
                "misleading, so they aren't shown.")
    st.info("The simulation uses today's index members, so companies that dropped out are missing; it "
            "holds equal amounts; and stock prices include dividends while the index doesn't. All of "
            "that helps both the AI and the all-members line beat the index. That's why the fair "
            "comparison is the AI against the dashed line, not against the index.",
            title="Why the index is easy to beat here", icon=":material/lightbulb:")
    st.markdown("- **No look-ahead:** annual results count only 90 days after the year ends; analyst "
                "targets aren't used, because their history isn't available.\n"
                "- **Not included:** brokerage, taxes and the gap between the price you see and the price "
                "you get.\n"
                "- **Updated:** every month, by the review. Values are recorded for every trading day; "
                "the AI only changes its holdings at month-ends.\n"
                "- **Past results don't promise future returns.**")

# ---- trades & P&L ----
with tabs[5]:
    st.markdown("MyProPicks never trades for you. You buy and sell with your own broker, then tell it "
                "what you did, in either of two ways:")
    c1, c2 = st.columns(2)
    with c1.container(border=True, height="stretch"):
        st.markdown("**:material/edit_note: On the dashboard**")
        st.caption("Use the **Log a trade** page: portfolio, buy or sell, stock, quantity, price, charges.")
    with c2.container(border=True, height="stretch"):
        st.markdown("**:material/terminal: From the command line**")
        st.caption("On your PC: `python -m mypropicks log --portfolio nifty20 --action BUY "
                   "--symbol PNB --qty 100 --price 149.75`")
    st.markdown("- **Average-cost method:** each buy updates your average price; sells book realised profit or loss.\n"
                "- **Charges** (brokerage, taxes) reduce realised profit.\n"
                "- **Cash** = starting capital − buys + sells − charges.\n"
                "- **Checks:** you can't sell more than you held on that date, and bad input is refused "
                "before anything is saved.")

# ---- dashboard pages ----
with tabs[6]:
    st.table({
        ":material/event: This month": "The latest review: what to sell, what to buy, and why",
        ":material/analytics: Portfolio analysis": "Each current list with live price, fair value, valuation label, health, a detail card per stock, and the 3-year AI vs index chart",
        ":material/account_balance_wallet: My holdings & P&L": "Private. Your own moves this month, what you own, its value, profit or loss, and the value over time vs the index",
        ":material/edit_note: Log a trade": "Private. Record a buy or sell",
        ":material/leaderboard: Full rankings": "Every stock in each index with every score",
        ":material/settings: Settings & review": "Private. Set your capital, run a review now, refresh the at-risk check",
        ":material/school: How it works": "This page",
        ":material/menu_book: Info": "Every term used in the app, explained simply: what it is, how it's worked out and how much it matters",
    }, border="horizontal")
    st.caption(":material/lock: Private pages ask for the app password, so your holdings, trades "
               "and capital stay yours even when the app link is public.")

# ---- data & limits ----
with tabs[7]:
    st.markdown("- **Index lists** come from NSE (niftyindices.com).\n"
                "- **Prices and financials** come from Yahoo Finance, free and delayed by about 15 minutes. "
                "Live prices refresh every 5 minutes, and the time of the price is shown on the page.\n"
                "- **Benchmarks:** Nifty 50 (for the Nifty 20), Nifty Midcap 150 and Nifty Smallcap 250.\n"
                "- **How the AI did (3-year chart):** see the *How the AI did* tab.\n"
                "- **Speed:** the first review downloads data for about 500 stocks and takes around 35–40 "
                "minutes; later runs reuse cached data and take a few minutes.\n"
                "- **Gaps:** free data sometimes misses a figure; such stocks are scored on what's "
                "available and may be flagged low data.")
    st.warning(DISCLAIMER, icon=":material/gavel:")

footer()
