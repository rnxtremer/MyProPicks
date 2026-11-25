# MyProPicks: design

Date: 2026-11-24 · Status: draft, awaiting approval

## 1. Intent

A free, personal replacement for InvestingPro's ProPicks, for Indian stocks. It keeps three
model portfolios. On the 1st of every month it reviews each one and says exactly which stocks
to sell and which to buy, so each portfolio always holds its top-ranked stocks. The owner
places trades by hand with their own broker and logs what they actually did. The tool then
tracks real profit and loss.

**Why:** to avoid paying for a ProPicks subscription.

## 2. The three portfolios

| Portfolio        | Holds exactly | Picked from (universe)                  |
| ---------------- | ------------- | --------------------------------------- |
| Nifty 20         | 20 stocks     | Nifty 100 constituents                  |
| Nifty Midcap 30  | 30 stocks     | Nifty Midcap 150 constituents           |
| Nifty Smallcap 50| 50 stocks     | Nifty Smallcap 250 constituents         |

"Nifty 20" and "Nifty Midcap 30" are not official NSE indices. These are the owner's portfolio
names. The universes are the official NSE lists that match each size band. There are only
these three portfolios.

## 3. Goals, non-goals, anti-goals

**Goals**
- Rank every stock in each universe monthly with a clear, rules-based score.
- Give a recommended list for each portfolio: the top N stocks by score.
- Monthly review: compare the recommended list with what the owner actually holds, then list
  the SELLs (held, no longer in top N) and the BUYs (in top N, not held). There is no cap on
  swaps. The portfolio is always restored to exactly N.
- Suggest quantities for buys: equal weight, based on the owner's capital or sale proceeds.
- Record the owner's real trades and show P&L per portfolio and overall: realised, unrealised,
  and return against the matching index.
- Two ways to work: the dashboard and a command line. Both use the same files.

**Non-goals**
- No automatic trading and no broker connection. The owner places every order.
- No intraday signals, alerts or stop-losses.
- No tax calculation (STCG/LTCG). It may be added later.
- No mobile app or hosting. It runs on this Windows PC only.

**Anti-goals** (failure even if it technically works)
- A recommended list that is short of N, or a review that leaves a portfolio short.
- Silent failures. If prices for a stock can't be fetched, the review says so by name.
- A black box. The owner must be able to see why each stock ranked where it did.
- Claiming certainty. Every review carries a short note: rules-based ranking, not advice, no
  guaranteed returns.

## 4. Constraints
- Free data only.
- Windows 11, Python 3.13 (already installed), single user, local files.
- Data files must be plain enough to open and fix in Excel.

## 5. Approaches considered

| Approach | Trade-off | Decision |
| --- | --- | --- |
| **Python engine + Streamlit dashboard + CSV/JSON files + Windows scheduled task** | Needs Python packages installed once. Runs offline and on schedule. Files are easy to edit by hand. | **Chosen** |
| Excel / Google Sheets workbook | Familiar, but can't realistically pull and rank about 500 stocks' price history monthly | Dropped |
| Full web app with a database | Prettier and works on a phone, but far more to build and maintain for one user. A database is harder to fix by hand | Dropped |

## 6. How it works

### 6.1 Data (free sources)
- **Constituent lists:** NSE/niftyindices.com publish free CSVs (Nifty 100, Midcap 150,
  Smallcap 250). They are refreshed at each review, with the last good copy kept as a
  fallback. The builder must confirm the current URLs.
- **Prices:** daily closes and volume for the past ~14 months from Yahoo Finance
  (`yfinance`, tickers like `TCS.NS`). Cached locally so re-runs are fast.
- **Fundamentals (required for scoring):** annual and quarterly income statement, balance
  sheet and cash flow, plus market cap, shares, EPS, book value, dividends and analyst
  targets, all from `yfinance`. Coverage is good for large caps and patchier for small caps
  (see the missing-data rule in 6.2).

The method has two stages, as the owner asked: **NSE's rules decide who is eligible, and a
ProPicks-style score decides who is best.**

### 6.2a Stage 1: eligibility, using NSE's own index rules
NSE's index methodology builds its size indices like this:
- Stocks are ranked by **average full market cap over the last 6 months**. Ranks 1–100 form
  the Nifty 100, ranks 101–250 the Midcap 150, and ranks 251–500 the Smallcap 250.
- Nifty 50 / Nifty 100 stocks must also trade in the F&O segment, trade on 100% of days in
  the last 6 months, have impact cost ≤ 0.50% on 90% of observations (a liquidity test),
  and have at least 1 month of listing history (3 months for IPOs).
- Index weights use **free-float market cap**, reviewed every six months (March/September).

How we apply it:
- We use NSE's **published constituent lists** as each universe. NSE has already applied its
  full formula, including the free-float and impact-cost data that isn't freely available to
  us. This is the most faithful option.
- Between NSE's six-monthly reviews, we re-check each month with the parts we can compute
  from free data: 6-month average market cap rank, trading on 100% of days in the last 6
  months, and a traded-value floor as a stand-in for impact cost (defaults: ₹50 cr large,
  ₹10 cr mid, ₹2 cr small per day, median of 3 months). A stock that fails is ineligible
  that month and marked with the reason.
- At least 250 trading days of price history, so momentum can be measured.

### 6.2b Stage 2: ranking, the ProPicks-style method
ProPicks' exact model is secret. What InvestingPro publishes about it: picks come from its
**Financial Health score** (five categories: profitability, growth, cash flow, relative
value and price momentum), its **Fair Value** estimate (an average of several valuation
models), and machine-learning models trained on long histories. Strategies are reviewed
monthly. We rebuild the published parts transparently. The ML part is replaced by fixed,
visible weights you can change. Being able to see why a stock ranks where it does matters
more here than imitating a black box.

Each metric is converted to a percentile rank (0–100) **within its universe and, where
meaningful, within its sector**. Each category is the average of its metrics:

| Category (weight) | Metrics |
| --- | --- |
| Profitability (20%) | ROE, ROCE, operating margin, net margin |
| Growth (20%) | Revenue growth (3-yr CAGR and latest year), EPS growth, operating profit growth |
| Cash flow (15%) | Operating cash flow ÷ net profit, free-cash-flow yield, low debt/equity, interest cover |
| Relative value (20%) | Fair-value upside (see 6.2c), P/E and P/B vs sector median |
| Price momentum (25%) | 12-1 month return, 6-month return, price vs 200-day average, lower 1-yr volatility |

- **Financial Health score** = the weighted total, shown on a 0–5 scale as InvestingPro
  does. Ranking uses the 0–100 score.
- **Missing data:** a missing metric is dropped and its category averages the rest. A
  missing category has its weight shared out across the others. Any stock scored with less
  than 60% of its data is flagged "low data" in the review.
- **Exclusions:** loss-making stocks (negative trailing EPS) can still rank, but their P/E
  metrics count as worst-in-universe.
- Ties are broken by price momentum, then by market cap.

### 6.2c Fair value (also used in the analysis page, 6.9)
Fair value is a weighted geometric mean of the methods that have data (weights in
`fair_value.weights` in config):
1. **Own past P/E (×2):** trailing EPS × the median P/E the stock traded at on its last
   few financial year-ends (5 years of monthly closes; per-share figures use today's share
   count because prices are split-adjusted). Needs at least two years.
2. **Own past P/B (×2):** book value per share × its own median past P/B.
3. **Analyst target (×2):** mean analyst target; counts ×1 with fewer than 5 analysts.
4. **Sector P/E (×1):** trailing EPS × sector median P/E.
5. **Sector P/B (×1):** book value per share × sector median P/B.
6. **Sector EV/EBITDA (×1):** implied price from the sector median EV/EBITDA (not for lenders).
7. **Simple DCF (×0, off):** 5-year free-cash-flow projection. Checked on the November 2026
   data it came out a median ~2.9× below analyst targets, so its weight is 0.

The weights come from a check against analysts' targets on ~500 stocks: leaving the analyst
target out, the old equal-weight five-method average was a median 37% from the target; the
new mix is ~20%. **Confidence:** High when 3+ methods agree within 1.6×, Medium within 2.5×,
else Low.

Outliers are dropped first: any method more than 3× or less than ⅓ of the median of the
others. **Label:** undervalued if LTP is more than 10% below fair value, overvalued if more
than 10% above it, fair otherwise (band in config). Each label shows how many methods it was
based on.

### 6.3 Monthly review rule (as the owner decided)
- Holding buffer (`buffer: 0.5` in config): a held stock stays while it ranks within
  N × 1.5 (rank 30 / 45 / 75). Originally there was no buffer; a 3-year test with Indian
  costs and tax (Nov 2026) showed the buffer roughly halved swaps, about doubled the average
  holding period and improved the after-tax edge on average, so the owner adopted it.
- SELL = held stocks ranked below the buffer cut-off, ineligible, or no longer in the universe.
- BUY = the highest-ranked stocks not held. **The number of BUYs always equals the number of
  SELLs**, so the portfolio stays at exactly N (for example, 4 out means 4 in). The one
  exception: if a portfolio is already short (say a stock was delisted or merged), the
  review adds enough extra BUYs to bring it back to N and says so.
- **First run:** with no holdings yet, the review is simply "BUY these N".
- Run date: the 1st of the month, using the latest available closing prices. If the 1st is a
  weekend or holiday, it uses the previous trading day's closes. The owner trades on the next
  trading day.

### 6.4 Quantities (equal weight)
- The owner sets the capital for each portfolio on the Settings page (saved to `data/capital.yaml`).
- First run: qty = floor((capital ÷ N) ÷ price).
- Monthly swaps: sale proceeds (at the latest close) are split equally across the BUYs, plus
  any leftover cash. Existing holdings are **not** rebalanced. Only the swapped slots move.
  (Builder's note: an optional "rebalance all to equal weight" flag can come later.)

### 6.5 Recording trades and P&L
- The owner logs each real trade: date, portfolio, symbol, BUY/SELL, quantity, price, and
  charges (optional).
- Holdings are always derived from the trade log, never typed in separately.
- Cash per portfolio = starting capital (config) − buys + sells − charges. This is also
  derived, and used for "leftover cash" in 6.4.
- Cost basis uses the **average cost** method (the usual Indian broker convention).
- P&L per portfolio and in total: invested amount, current value, realised P&L, unrealised
  P&L, return %, and a comparison with the matching index (Nifty 100, Midcap 150, Smallcap
  250) over the same period.
- Warnings: a portfolio holding more or fewer than N stocks, a selling quantity above what is
  held, or trades in a symbol not in that portfolio's universe.

### 6.6 Files (all under `F:\MyProPicks\data\`)
- `trades.csv`: the trade log. This is the single source of truth for holdings and P&L.
- `config.yaml`: factor weights, liquidity thresholds.
- `capital.yaml`: capital per portfolio. Private, like `trades.csv`: in the cloud both live in a
  separate private data repo, so the code repo can be public.
- The review files are the model portfolio (compared with last month's list, no quantities),
  so they are safe to publish. The owner's own sells, buys and quantities are worked out live
  on the password-locked holdings page.
- `universe/<index>.csv`: cached constituent lists.
- `cache/prices/`: cached price history.
- `reviews/YYYY-MM-DD/`: each review's full rankings (CSV, with every factor score), the
  SELL/BUY list per portfolio, and a readable `summary.md`.

The command line (`python -m mypropicks log …`) logs trades with the same checks as the
dashboard.

### 6.7 Dashboard (Streamlit, local, opens in the browser)
- **This month:** the latest review per portfolio, with SELL and BUY lists, suggested
  quantities, and why each stock moved (its rank and factor scores).
- **Log trade:** a form that appends to `trades.csv`.
- **Holdings and P&L:** per portfolio plus a total, with a chart of value over time against
  the index.
- **Rankings:** the full ranked universe for any past review.
- **Settings:** a "Run review now" button and a view of the config.

- **Portfolio analysis:** see 6.9.

### 6.9 Portfolio analysis page (the current recommended lists)
This covers the stocks in the **latest review's lists**: the current Nifty 20, Midcap 30 and
Smallcap 50 picks, whether or not you hold them. Your own holdings and P&L stay on the
Holdings page (6.7).

There are **three separate sections, one per portfolio** (tabs: Nifty 20 | Midcap 30 |
Smallcap 50). Each has a summary strip and a table with a click-through detail card per stock.

**Summary strip:** how many stocks are undervalued, fair or overvalued; the average
Financial Health score; the average fair-value upside; the sector mix; and the date of the
list and of the data.

| Column | Notes |
| --- | --- |
| Rank in list, stock, sector | |
| LTP and day change % | Free Yahoo quotes run about 15 minutes behind; there's a "Refresh" button |
| Change since added % | From the close on the review day the stock entered the list |
| Fair value, upside/downside %, label | **Undervalued / Fair / Overvalued**, colour-coded, with the method count |
| Financial Health score (0–5) | With the five category scores on the detail card |
| Live rank in universe | Warns **"At risk"** if the stock would currently fall below the buffer cut-off, so you see removals coming before the 1st |
| P/E, P/B, ROE, debt/equity, dividend yield | vs sector median on the detail card |
| Market cap | |
| 52-week high/low and distance from each | |

The detail card adds a 1-year price chart with the 200-day average, the fair-value
breakdown by method, and the last 4 quarters' revenue and profit.

Snapshot data (fundamentals and fair value) is refreshed daily on first open. LTP is
refreshed on demand.

### 6.8 Monthly schedule
A Windows Task Scheduler job runs the review at 08:00 on the 1st of each month. It writes
`reviews/YYYY-MM-DD/` and a Windows notification. If the PC is off, it runs at next start-up
(Task Scheduler's "run as soon as possible after a missed start").

## 7. Left to the builder
- Exact NSE/niftyindices URLs and the Yahoo index tickers for benchmarks.
- Project layout, package versions, tests (scoring, review rule, average-cost P&L).
- Handling Yahoo symbol quirks (e.g. `M&M.NS`, renamed or merged stocks).
- Dashboard look and feel.
- Sector classification source (NSE constituent CSVs include an industry column, so use that).
- Rate-limiting and caching for about 500 fundamentals fetches (cache them for a month; the
  fundamentals only change quarterly).
