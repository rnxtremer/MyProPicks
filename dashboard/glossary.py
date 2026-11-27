"""Every term used in the app, in plain words, for the Info page.

Fields per entry (all text, all optional except term, group and what):
- what:    what it is, in everyday language
- how:     how it's worked out, step by step
- high:    what a high value means
- low:     what a low value means
- good:    rule of thumb for what's good (Indian market)
- price:   how it tends to affect the share price
- matters: what it does inside MyProPicks
- example: a worked example with numbers
- metric:  the scoring measure it explains; the Info page adds its share of the total score

{weights}, {liquidity} and {cutoffs} in any text are filled in from the current settings.
"""

GROUPS = [
    ("basics", ":material/school:", "The basics"),
    ("ranking", ":material/leaderboard:", "Score and rank"),
    ("momentum", ":material/trending_up:", "Momentum"),
    ("profitability", ":material/payments:", "Profitability"),
    ("growth", ":material/rocket_launch:", "Growth"),
    ("cash_flow", ":material/account_balance:", "Cash flow and debt"),
    ("value", ":material/balance:", "Valuation and fair value"),
    ("performance", ":material/show_chart:", "Performance"),
    ("money", ":material/account_balance_wallet:", "Your money"),
]

TERMS: list[dict] = [
    # ======================= THE BASICS =======================
    dict(group="basics", term="Index",
         what="An index is a ready-made list of companies that represents a part of the stock market, "
              "plus a single number that tracks how that whole group is doing. Think of it as the "
              "\"class average\" for a group of stocks. When people say \"the market went up 1% today\", "
              "they usually mean an index such as the Nifty 50 went up 1%.",
         how="NSE (the National Stock Exchange) chooses the companies by size and trading activity and "
             "reviews the list twice a year. Bigger companies count for more in the index number, so a "
             "5% move in a giant like Reliance moves the Nifty 50 far more than a 5% move in a smaller member.",
         price="An index doesn't move prices by itself, but being added to a big index often lifts a "
               "stock, because index funds must buy it; being removed often pushes it down.",
         matters="Each MyProPicks portfolio picks only from its own index, and is judged against an index: "
                 "if it can't beat the index, you'd be better off with a cheap index fund.",
         example="The Nifty 50 rising from 24,000 to 25,200 means its 50 companies together gained about 5%."),
    dict(group="basics", term="Nifty 100 / Midcap 150 / Smallcap 250",
         what="The three pools the AI picks from. The Nifty 100 holds India's 100 largest listed "
              "companies (household names). The Midcap 150 holds the next 150 (medium-sized, often "
              "growing fast). The Smallcap 250 holds the 250 after that (small companies).",
         how="NSE ranks all listed companies by their market value: positions 1–100 form the Nifty 100, "
             "101–250 the Midcap 150, and 251–500 the Smallcap 250. MyProPicks downloads the latest lists "
             "from NSE at every review.",
         high="Bigger companies (Nifty 100) are steadier, better known and easier to buy and sell.",
         low="Smaller companies (Smallcap 250) can grow much faster, but their prices swing more and "
             "some fail.",
         price="Small and mid-size stocks usually rise more in good years and fall harder in bad years.",
         matters="Picking within each pool keeps comparisons fair: small banks are compared with small "
                 "banks, not with HDFC Bank."),
    dict(group="basics", term="Nifty 20 / Midcap 30 / Smallcap 50",
         what="The three model portfolios: the AI's 20 best stocks from the Nifty 100, its 30 best from "
              "the Midcap 150, and its 50 best from the Smallcap 250.",
         how="Every month the AI scores every stock in each pool and keeps the top 20, 30 or 50 by rank. "
             "Each stock is meant to get the same amount of money (equal weight).",
         high="More stocks (the Smallcap 50) spread the risk, because small companies are less predictable.",
         low="Fewer stocks (the Nifty 20) work for big companies, which are more predictable.",
         matters="These are the AI's recommendations, shown on Portfolio analysis and This month."),
    dict(group="basics", term="Review",
         what="The monthly check-up. The AI downloads fresh prices and company results, re-scores every "
              "stock, and updates the three lists: which stocks go out, which come in.",
         how="Runs automatically at 08:00 IST on the 1st of each month. A stock leaves only if it falls "
             "out of the top 20 / 30 / 50, fails a trading check, or leaves its index.",
         matters="It's the only time the lists change. Between reviews they stay fixed, which avoids "
                 "over-trading on daily noise."),
    dict(group="basics", term="LTP (last traded price)",
         what="The most recent price at which one share changed hands on the stock exchange. It's "
              "simply \"the share price right now\".",
         how="Taken from Yahoo Finance, about 15 minutes behind the live market. Outside market hours "
             "(9:15 am – 3:30 pm IST) it's the last closing price. The app fetches it again every 5 minutes "
             "(or when you press Refresh prices) and shows the time of the price above the table.",
         price="This *is* the share price; every other measure is compared with it.",
         matters="Used to work out the gap to fair value, your profit or loss, and the day's move."),
    dict(group="basics", term="Day %",
         what="How much the share price has moved today, as a percentage.",
         how="Today's price ÷ yesterday's closing price − 1.",
         high="A big rise often follows news: good results, a contract, an upgrade.",
         low="A big fall often follows bad news, or the whole market falling.",
         good="Daily moves of 1–2% are normal; 5%+ usually means news. Don't judge a stock by one day.",
         matters="Shown for information only. The AI doesn't use daily moves, on purpose."),
    dict(group="basics", term="Market cap (Mcap)",
         what="What the whole company is worth on the stock market: the price tag for buying every "
              "single share.",
         how="Share price × number of shares. Shown in ₹ crore (1 crore = ₹1,00,00,000).",
         high="Large companies (₹1 lakh crore and up) are usually stable, well-run and widely followed.",
         low="Small companies (under about ₹20,000 crore) can grow faster but carry more risk.",
         price="Market cap rises and falls with the share price; it's the price seen at company level.",
         matters="Decides which index a company is in, and breaks ties in the ranking (bigger wins).",
         example="₹500 a share × 200 crore shares = ₹1,00,000 crore market cap."),
    dict(group="basics", term="52-week high / low",
         what="The highest and lowest prices the share reached in the past year. They show where "
              "today's price sits within its recent range.",
         how="Shown as how far today's price is from each, e.g. \"−8% from the 52-week high\".",
         high="Near its 52-week high: the stock is in demand; often a sign of strength.",
         low="Near its 52-week low: investors are worried; it might be cheap, or in real trouble.",
         price="Stocks near their highs often keep going (momentum), but they can also be overheated.",
         matters="Shown for context only; not part of the score."),
    dict(group="basics", term="Sector",
         what="The kind of business a company is in: banking, IT, pharma, cars and so on.",
         how="Taken from NSE's own classification in its index lists.",
         price="Whole sectors often move together on news, such as interest rates for banks or the "
               "dollar for IT companies.",
         matters="Many measures compare a company with others in its own sector, because a fair P/E "
                 "for a bank is very different from one for a software company."),
    dict(group="basics", term="Dividend yield",
         what="The cash a company pays its shareholders each year, as a percentage of the share price. "
              "It's like the \"interest\" a share pays you.",
         how="Yearly dividend per share ÷ share price.",
         high="Above 3%: a generous payer, often a mature, steady business (or a share whose price has fallen).",
         low="Below 1%: the company keeps its profit to grow, common for fast-growing firms.",
         good="Neither is better: a high yield suits income seekers, a low yield is fine if the company "
              "grows fast.",
         price="When a dividend is paid, the price usually drops by about that amount that day.",
         matters="Shown for information only; not part of the score.",
         example="A ₹10 dividend on a ₹400 share is a 2.5% yield."),

    # ======================= SCORE AND RANK =======================
    dict(group="ranking", term="Percentile",
         what="Where a stock stands compared with the others in its pool, on a scale from 0 (worst) to "
              "100 (best). It's like a class rank turned into a percentage.",
         how="For each measure (say ROE), all stocks in the pool are lined up from worst to best. A stock "
             "beating 80% of the others gets a percentile of 80.",
         high="Near 100: one of the best in its pool on that measure.",
         low="Near 0: one of the worst.",
         matters="Every one of the 19 measures is turned into a percentile, so measures in different "
                 "units (%, times, ₹) can be added together fairly.",
         example="If a stock's ROE beats 90 of the 100 Nifty 100 stocks, its ROE percentile is 90."),
    dict(group="ranking", term="The five areas",
         what="The AI looks at a company from five angles: Momentum (is the price trending up?), "
              "Profitability (does it earn well?), Growth (is it growing?), Relative value (is it "
              "cheap?) and Cash flow (is the cash real and the debt safe?).",
         how="Each area has 3 or 4 measures. The area score is the average of their percentiles (0–100).",
         good="The best picks usually score well in several areas, not just one.",
         matters="Weights in the total score: {weights}."),
    dict(group="ranking", term="Total score",
         what="One number from 0 to 100 that sums up how attractive a stock looks to the AI.",
         how="The weighted average of the five area scores. If an area has no data at all for a stock, "
             "its weight is shared among the other areas.",
         high="Above 70: strong on most measures; likely in the list.",
         low="Below 40: weak on many measures.",
         price="A high score doesn't move the price itself, but stocks with strong fundamentals and "
               "trends have tended to do better over time.",
         matters="Decides the rank, and so whether a stock makes the list."),
    dict(group="ranking", term="Health score",
         what="The total score shown on a 0–5 scale, like a star rating, so it's quicker to read.",
         how="Total score ÷ 20.",
         high="4 or more: excellent all round.",
         low="Under 2: weak on many measures.",
         good="Most stocks in the AI's lists score 3 or more.",
         matters="Same information as the total score.",
         example="A total score of 70 is a health of 3.5."),
    dict(group="ranking", term="Rank",
         what="A stock's position in its pool: 1 is the AI's favourite.",
         how="Eligible stocks come first, ordered by total score. Ties go to the stronger momentum, then "
             "the bigger company.",
         high="A low number (near 1) is good: top of the class.",
         low="Above 20 / 30 / 50: not bought. A stock already held is kept down to rank {cutoffs}.",
         matters="New stocks join from the top 20 / 30 / 50. A stock already in the list stays until it "
                 "falls below the holding buffer ({cutoffs})."),
    dict(group="ranking", term="Holding buffer",
         what="A safety margin that stops the AI selling a stock the moment it slips just outside the "
              "list. A held stock stays until it falls clearly below the cut-off.",
         how="Held stocks are kept while they rank within N × 1.5: rank {cutoffs}. New stocks still "
             "come from the very top.",
         high="A wider buffer: fewer swaps, lower costs, more gains held over a year (taxed less), but "
              "weaker stocks are kept longer.",
         low="No buffer: the list always holds the current top N, but swaps more often, with more "
             "costs and short-term tax.",
         good="1.5 × N worked well in our 3-year test: about half the swaps, average holding about a "
              "year, and a better result after costs and tax on average.",
         price="It doesn't move prices; it changes how often you trade, which changes what you keep.",
         matters="Used by the monthly review, by your own moves and by the 3-year backtest.",
         example="In the Nifty 20, a stock that slips from rank 8 to rank 24 is kept. One that falls to "
                 "rank 35 is sold."),
    dict(group="ranking", term="Eligible",
         what="Whether a stock passes basic trading checks, the same kind NSE uses for its indices. It "
              "keeps out stocks that are hard to buy and sell, or too new to judge.",
         how="It needs about a year of price history, must have traded every day for the last 6 months, "
             "and must trade enough money on a typical day ({liquidity}).",
         low="Not eligible: you might not be able to buy or sell it easily at a fair price.",
         matters="A stock that fails is ranked below every eligible one, so it can't make the list."),
    dict(group="ranking", term="Low data",
         what="A warning that free data was missing many figures for this company, so its score rests "
              "on less information.",
         how="Measures with data ÷ all 19 measures. Below 60% gets the flag.",
         matters="The score is less reliable; check the company yourself before relying on it."),
    dict(group="ranking", term="At risk of removal",
         what="A stock in the current list that would drop out if the review ran today.",
         how="Comes from re-scoring with today's prices (Settings → Refresh live ranks).",
         matters="An early warning only; the list changes only at the monthly review."),
    dict(group="ranking", term="Since added",
         what="How much a stock's price has changed since it joined the AI's list.",
         how="Today's price ÷ the price on the day it was added − 1.",
         high="Positive: the pick has worked so far.",
         low="Negative: it has fallen since it was picked.",
         good="Judge picks over months, not days; a few losers are normal in any portfolio.",
         matters="Shows how each pick has done. On a stock's price chart, the green dot marks the day it "
                 "was added and the shaded stretch is its time in the list."),
    dict(group="ranking", term="Return in the list",
         what="How a stock did from the day it joined the AI's list to the day it left.",
         how="Price when it left ÷ price when it was added − 1. Both are the last closing prices "
             "before the review that added or removed it.",
         high="Positive: the stock made money while the AI held it.",
         low="Negative: it lost money while held.",
         good="Compare it with the index over the same days: beating the index is what counts.",
         matters="Shown for every stock leaving the list on the This month page, with a chart marking "
                 "Added and Removed, and what ₹10,000 would have become.",
         example="Added at ₹2,052, removed at ₹3,478: a return of +69.5%, so ₹10,000 became about ₹16,950."),

    # ======================= MOMENTUM =======================
    dict(group="momentum", term="12-month return (skipping the last month)", metric="mom_12_1",
         what="How much the share price rose over the past year, leaving out the most recent month. It "
              "measures the long-term trend.",
         how="Price one month ago ÷ price twelve months ago − 1. The last month is skipped because very "
             "recent jumps often partly reverse.",
         high="Strongly positive (e.g. +40%): a strong uptrend; investors have been buying for months.",
         low="Negative: a downtrend; investors have been selling.",
         good="Higher is better. Studies across many markets find that last year's winners tend to keep "
              "winning for a while.",
         price="Trends tend to continue for months, because news spreads slowly and investors follow "
               "each other, but every trend ends eventually.",
         example="Price ₹100 a year ago and ₹130 a month ago: +30%."),
    dict(group="momentum", term="6-month return", metric="mom_6",
         what="How much the share price rose over the last 6 months: a shorter view of the trend.",
         how="Today's price ÷ price 6 months ago − 1.",
         high="Positive: a recent uptrend.",
         low="Negative: a recent downtrend.",
         good="Higher is better; best when it agrees with the 12-month trend.",
         price="Recent strength often carries on for a few more months."),
    dict(group="momentum", term="Price vs 200-day average", metric="vs_200dma",
         what="How far today's price is above or below its average price over the last 200 trading days "
              "(about 10 months). Traders use it as a simple test of whether a stock is in an uptrend.",
         how="Today's price ÷ the average of the last 200 closing prices − 1.",
         high="Above the average (positive): an uptrend. Very far above (+40% or more) can mean overheated.",
         low="Below the average (negative): a downtrend.",
         good="Higher is better in the score. Between 0% and +30% is a healthy uptrend.",
         price="Many investors buy above the 200-day average and sell below it, which tends to reinforce "
               "the trend."),
    dict(group="momentum", term="Volatility", metric="vol_1y",
         what="How much the share price jumps around from day to day. A calm stock has low volatility; "
              "a stock that swings wildly has high volatility.",
         how="The spread (standard deviation) of daily price changes over a year, scaled up to a yearly "
             "figure.",
         high="Above 40% a year: big swings; scary drops are common.",
         low="Below 20% a year: a smooth ride, typical of large, steady companies.",
         good="Lower is better in the score. Calmer stocks have often given similar returns with less pain.",
         price="High volatility means the price can fall a lot quickly, even if the long-term trend is good."),

    # ======================= PROFITABILITY =======================
    dict(group="profitability", term="ROE (return on equity)", metric="roe",
         what="How much profit a company makes for every rupee its owners (shareholders) have put into "
              "it. It's the business's \"interest rate\" on the owners' money.",
         how="Net profit for the year ÷ shareholders' equity (the owners' money in the business).",
         high="Above 20%: excellent; the business turns owners' money into profit very efficiently. Very "
              "high ROE can also come from heavy debt, so check Debt/Eq too.",
         low="Below 10%: weak; owners would earn nearly as much in a fixed deposit.",
         good="Higher is better. Above 15% is good in India; above 20% is excellent.",
         price="Companies that keep a high ROE for years usually see their share price rise over time, "
               "because profits compound.",
         example="Profit ₹20 crore on ₹100 crore of equity is an ROE of 20%."),
    dict(group="profitability", term="ROCE (return on capital employed)", metric="roce",
         what="Like ROE, but counts all the money in the business, including borrowed money. It shows "
              "how well the company uses every rupee, whoever provided it.",
         how="Operating profit (EBIT: profit before interest and tax) ÷ (equity + debt).",
         high="Above 20%: excellent use of capital.",
         low="Below 10%: the business barely earns more than its money costs.",
         good="Higher is better. It should be above the company's borrowing cost (roughly 9–10% in India).",
         price="High ROCE businesses can grow without needing much new money, which investors reward."),
    dict(group="profitability", term="Operating margin", metric="op_margin",
         what="How much of each rupee of sales is left after paying for running the business: "
              "materials, salaries, rent and so on, but before interest and tax.",
         how="Operating profit ÷ revenue (sales).",
         high="High (e.g. above 20%): pricing power or low costs, typical of strong brands and software.",
         low="Low (under 10%): a thin cushion, typical of retail, trading or very competitive industries.",
         good="Higher is better, but compare with the same industry: 8% is fine for a supermarket and "
              "poor for a software company.",
         price="Rising margins often push the share price up, because profit grows faster than sales."),
    dict(group="profitability", term="Net margin", metric="net_margin",
         what="How much of each rupee of sales ends up as final profit, after everything: costs, "
              "interest and tax. The \"bottom line\" as a share of sales.",
         how="Net profit ÷ revenue.",
         high="Above 15%: very profitable.",
         low="Below 5%: little profit per sale; small problems can wipe it out.",
         good="Higher is better; compare within the same industry.",
         example="Sales ₹1,000 crore and net profit ₹120 crore: a 12% net margin."),

    # ======================= GROWTH =======================
    dict(group="growth", term="3-year revenue CAGR", metric="rev_cagr3",
         what="How fast the company's sales grew per year, on average, over the last 3 years. It "
              "smooths out one-off good or bad years.",
         how="(Sales now ÷ sales 3 years ago) ^ (1/3) − 1.",
         high="Above 15% a year: a fast-growing business.",
         low="Below 5% a year: barely growing (roughly in line with inflation).",
         good="Higher is better. Steady growth over years is worth more than one good year.",
         price="Over the long run, share prices follow sales and profit growth.",
         example="Sales ₹100 crore → ₹152 crore in 3 years is about 15% a year."),
    dict(group="growth", term="Revenue growth", metric="rev_growth",
         what="How much sales grew in the latest financial year compared with the year before.",
         how="This year's sales ÷ last year's sales − 1.",
         high="Above 15%: strong demand for the company's products.",
         low="Negative: sales are shrinking, a warning sign.",
         good="Higher is better, especially if profits grow too.",
         price="Results that beat expectations on growth often lift the price on the day they come out."),
    dict(group="growth", term="EPS growth", metric="eps_growth",
         what="How much profit per share grew in the latest year. This is the growth shareholders care "
              "about most, because it's their share of the profit.",
         how="This year's EPS ÷ last year's EPS − 1.",
         high="Above 20%: profits growing fast.",
         low="Negative: profits falling.",
         good="Higher is better. Growth that comes with growing sales is more reliable than growth from "
              "cost cuts.",
         price="Over time, share prices tend to follow EPS: if EPS doubles and the P/E stays the same, "
               "the price doubles."),
    dict(group="growth", term="Operating profit growth", metric="op_profit_growth",
         what="How much the profit from the company's main business grew in the latest year, ignoring "
              "one-off gains such as selling land.",
         how="This year's operating profit ÷ last year's − 1.",
         high="Strong: the core business is getting better.",
         low="Negative: the core business is weakening, even if one-offs hide it.",
         good="Higher is better."),

    # ======================= CASH FLOW =======================
    dict(group="cash_flow", term="Operating cash vs net profit", metric="ocf_to_np",
         what="Checks whether the profit the company reports actually arrives as cash in the bank. "
              "Profits can be flattered by accounting; cash is much harder to fake.",
         how="Cash from operations ÷ net profit.",
         high="1 or more: profits are real cash. A healthy sign.",
         low="Below 0.7 for years: profits may be stuck in unpaid customer bills or stock, or be "
             "over-stated. A warning sign.",
         good="Higher is better; around 1 or above is good.",
         price="Companies whose profits don't turn into cash often see their share price collapse when "
               "the truth comes out."),
    dict(group="cash_flow", term="FCF yield (free cash flow yield)", metric="fcf_yield",
         what="Free cash flow is the cash left after the company pays for running and investing in the "
              "business: money it could pay out, use to cut debt, or reinvest. The yield compares it "
              "with what the whole company costs on the market.",
         how="Free cash flow ÷ market cap.",
         high="Above 5%: the company produces a lot of spare cash for its price; often good value.",
         low="Negative: the company is spending more than it brings in, normal while building factories, "
             "worrying if it lasts.",
         good="Higher is better.",
         price="High free cash flow lets a company pay dividends and buy back shares, which supports the price."),
    dict(group="cash_flow", term="Debt to equity (Debt/Eq)", metric="debt_equity",
         what="How much money the company has borrowed compared with its owners' money. It shows how "
              "much the business leans on loans.",
         how="Total debt ÷ shareholders' equity.",
         high="Above 1: more borrowed money than owners' money. Risky if business slows, because interest "
              "must still be paid.",
         low="Below 0.5: little debt; the company can survive bad years. 0 means debt-free.",
         good="Lower is better in the score. Banks and lenders are an exception: borrowing is their business.",
         price="Heavily indebted companies often fall hard when interest rates rise or profits dip.",
         example="A Debt/Eq of 0.5 means ₹50 of debt for every ₹100 of owners' money."),
    dict(group="cash_flow", term="Interest cover", metric="interest_cover",
         what="How many times the company's profit could pay the interest on its loans. It shows how "
              "safely it can carry its debt.",
         how="Operating profit (EBIT) ÷ interest paid in the year.",
         high="Above 5: comfortable; interest is a small cost.",
         low="Below 2: danger zone; a bad year could leave it unable to pay its lenders.",
         good="Higher is better.",
         price="Weak interest cover makes the share very sensitive to bad news and rate rises."),

    # ======================= VALUATION =======================
    dict(group="value", term="EPS (earnings per share)",
         what="The company's yearly profit divided by the number of shares: how much profit \"belongs\" "
              "to each share you own.",
         how="Net profit ÷ number of shares.",
         high="Rising EPS year after year: the business is earning more for each share.",
         low="Negative EPS: the company made a loss.",
         price="Share prices tend to follow EPS over the long run.",
         matters="The base for P/E and for two fair value methods.",
         example="Profit ₹1,000 crore ÷ 50 crore shares = EPS of ₹20."),
    dict(group="value", term="P/E (price to earnings)",
         what="How many rupees investors pay for each rupee of the company's yearly profit. It's the "
              "most common \"is it cheap or expensive?\" measure.",
         how="Share price ÷ EPS.",
         high="High P/E (above 40): investors expect fast growth, or the share is expensive. If growth "
              "disappoints, the price can fall sharply.",
         low="Low P/E (under 15): cheap, or the market expects trouble. Check why.",
         good="Compare with the sector and with the company's own past. The Nifty 50 usually trades at "
              "around 20–24 times earnings.",
         price="If profits stay the same, a falling P/E means a falling price. Prices rise when profits "
               "grow, when the P/E rises, or both.",
         example="Price ₹300 and EPS ₹15: a P/E of 20. You pay 20 years of today's profit."),
    dict(group="value", term="P/B (price to book)",
         what="The share price compared with the company's net worth per share: what would be left for "
              "owners if it sold everything and paid all its debts.",
         how="Share price ÷ book value per share (equity ÷ number of shares).",
         high="High P/B (above 5): investors value the business far above its assets, fine for "
              "high-ROE brands and software.",
         low="Below 1: priced below its net worth. Possibly a bargain, or the market doubts the assets "
             "(common for state-owned banks).",
         good="Most useful for banks and lenders. Judge it together with ROE: a high ROE justifies a high P/B.",
         price="For banks, the price usually moves with book value and ROE."),
    dict(group="value", term="EV/EBITDA",
         what="The value of the whole business, including its debt, compared with its yearly cash "
              "profit. Unlike P/E, it isn't fooled by how much debt a company carries.",
         how="(Market cap + debt − cash) ÷ EBITDA (profit before interest, tax, depreciation and amortisation).",
         high="Above 20: expensive, or very high growth expected.",
         low="Below 10: cheap compared with the cash the business makes.",
         good="Lower is cheaper; compare within the same sector. Not used for banks.",
         matters="Used in the sector EV/EBITDA fair value method."),
    dict(group="value", term="P/E vs sector", metric="pe_rel",
         what="Whether a stock is cheaper or more expensive than other companies in the same sector, "
              "judged by P/E.",
         how="The stock's P/E ÷ the median P/E of its sector. Loss-makers count as the worst.",
         high="Above 1: dearer than its peers.",
         low="Below 1: cheaper than its peers.",
         good="Lower is better in the score, but a better company often deserves a higher P/E.",
         price="Cheap stocks in a good sector can re-rate upwards when investors notice them."),
    dict(group="value", term="P/B vs sector", metric="pb_rel",
         what="The same comparison as P/E vs sector, but using price to book.",
         how="The stock's P/B ÷ the median P/B of its sector.",
         high="Above 1: dearer than its peers.",
         low="Below 1: cheaper than its peers.",
         good="Lower is better in the score."),
    dict(group="value", term="Fair value",
         what="MyProPicks' estimate of what one share is really worth, based on the company's profits, "
              "assets and how the market usually values it. The share price can sit above or below it "
              "for long periods.",
         how="A weighted average of up to six methods: the stock's own past P/E and P/B (each counts "
             "double), the analyst target (double when 5 or more analysts cover it), and sector P/E, P/B "
             "and EV/EBITDA (once each). A geometric average stops one very high estimate taking over.",
         high="Fair value well above the price: possibly undervalued.",
         low="Fair value well below the price: possibly overvalued.",
         good="Treat it as a guide, not a target. Check the confidence rating.",
         price="Over long periods, prices tend to drift toward fair value, but that can take years.",
         matters="Feeds the upside measure and the Undervalued / Fair / Overvalued label."),
    dict(group="value", term="Own past P/E and P/B",
         what="The valuation the stock itself usually traded at in past years. Many companies have a "
              "\"normal\" P/E the market is used to paying for them.",
         how="The median P/E (or P/B) at each of its last few year-ends, × today's EPS (or book value).",
         high="Today's price above this level: dearer than usual for this stock.",
         low="Today's price below it: cheaper than usual.",
         price="Prices often return toward a stock's usual valuation once temporary worries fade.",
         matters="The most reliable fair value methods in our checks, so they count double."),
    dict(group="value", term="Analyst target",
         what="The average price that professional analysts at brokers expect the share to reach, "
              "usually within a year.",
         how="Average of the analysts' published targets, from Yahoo Finance.",
         high="Target well above the price: analysts expect a rise.",
         low="Target below the price: analysts think it's run too far.",
         good="More analysts means a more reliable average.",
         price="Big upgrades or downgrades by analysts can move a price on the day.",
         matters="Counts double in fair value when at least 5 analysts cover the stock, once otherwise."),
    dict(group="value", term="Upside", metric="upside",
         what="How far the share price is below (or above) its fair value: the room the price has to rise.",
         how="Fair value ÷ price − 1.",
         high="Positive (e.g. +25%): the price is below fair value; possibly undervalued.",
         low="Negative (e.g. −20%): the price is above fair value; possibly overvalued.",
         good="Higher is better in the score. Treat very high upside (+80% or more) with suspicion: "
              "often the data is off, or the market knows something.",
         example="Fair value ₹120 and price ₹100: upside of +20%."),
    dict(group="value", term="Undervalued / Fair / Overvalued",
         what="A simple label based on the upside, so you can read valuation at a glance.",
         how="Undervalued: price more than 10% below fair value. Overvalued: more than 10% above. Fair: "
             "within 10% either way.",
         good="Undervalued plus High confidence is the strongest signal; Low confidence labels are rough guesses.",
         matters="Only a label; the exact upside is what's scored."),
    dict(group="value", term="Confidence (High / Medium / Low)",
         what="How much to trust a fair value. When different valuation methods give similar answers, "
              "the estimate is more trustworthy.",
         how="High when 3 or more methods agree within 1.6× of each other; Medium within 2.5×; otherwise Low.",
         high="High: the methods agree; the fair value is a fairly solid estimate.",
         low="Low: the methods disagree a lot; treat the fair value as a rough guess.",
         good="Rely on the upside mainly when confidence is High or Medium."),
    dict(group="value", term="Methods",
         what="How many valuation methods went into a fair value.",
         how="Methods with missing data are skipped. Any method more than 3× or under ⅓ of the middle "
             "one is dropped as an odd result.",
         high="4–6 methods: a well-supported estimate.",
         low="1–2 methods: thin; one bad figure can throw it off.",
         good="More methods usually means a steadier estimate."),

    # ======================= PERFORMANCE =======================
    dict(group="performance", term="CAGR (compound annual growth rate)",
         what="The average yearly growth of an investment over several years, assuming gains are "
              "reinvested. It turns an uneven ride into one simple \"% per year\" figure.",
         how="(End value ÷ start value) ^ (1 ÷ number of years) − 1.",
         high="Above 15% a year: excellent for Indian stocks over several years.",
         low="Below 7% a year: about what a fixed deposit pays, with much more risk.",
         good="Compare it with the index's CAGR over the same years.",
         matters="The How the AI did chart shows CAGR for periods longer than a year (2Y, Max). For a "
                 "year or less it shows plain return instead, because a yearly rate over a few weeks "
                 "would be misleading.",
         example="₹100 growing to ₹133 in 3 years is a CAGR of about 10% a year, not 11% (33 ÷ 3)."),
    dict(group="performance", term="Return (for a period)",
         what="How much an investment went up or down over a chosen stretch of time, in total, not per year.",
         how="Value at the end ÷ value at the start − 1.",
         high="Positive: it gained over the period.",
         low="Negative: it lost over the period.",
         good="Over short periods (a day, a week, a month) returns jump around a lot; judge the AI over "
              "years, not weeks.",
         matters="Shown above the chart for 1D, 1W, 1M, 3M, 6M and 1Y.",
         example="₹100 becoming ₹104 over 1 month is a return of +4%."),
    dict(group="performance", term="How the AI did (backtest)",
         what="A test of the AI on the past 3 years: what ₹100 would have grown to if you had followed "
              "its picks, tracked every trading day.",
         how="At each month-end it ranks stocks using only the prices and results available then, buys "
             "the top N; each month after that, it sells stocks that fell below the holding buffer and "
             "buys the best new ones with that money, leaving the rest untouched.",
         good="A good result beats the dashed all-members line, not just the index.",
         matters="Shows whether the rules have worked. Pick a period with the buttons (1D to Max): every "
                 "period restarts at ₹100. Hover over the chart (or press and hold on a phone) to read "
                 "the date and all three values. Past results don't promise future returns."),
    dict(group="performance", term="All members, equal weight",
         what="The dashed line on the chart: buying every stock in the index in equal amounts, with no "
              "choosing at all.",
         how="Same period as the AI line, holding all of today's members in equal amounts and "
             "rebalancing back to equal each month, like an index fund.",
         high="If it's far above the index, much of the gap comes from how the test works, not skill.",
         matters="The fair yardstick for the AI, because it shares the simulation's advantages."),
    dict(group="performance", term="AI's real edge",
         what="How much the AI's choices added, compared with simply buying everything.",
         how="For periods longer than a year: AI CAGR − all-members CAGR, in points a year. For a year "
             "or less: AI return − all-members return, in points.",
         high="Positive (e.g. +5 pts a year): the AI's choices added value.",
         low="Zero or negative: picking didn't beat buying the whole index.",
         good="Even +2 to +3 points a year adds up to a lot over 10+ years.",
         matters="The most honest single number for how good the AI is."),
    dict(group="performance", term="Survivorship bias",
         what="Looking better than reality because the failures are missing from the data, like "
              "judging a school only by the students who graduated.",
         how="The backtest uses today's index members, so companies that dropped out are left out.",
         matters="It flatters the AI line and the all-members line alike, so the gap between them is still fair."),

    # ======================= YOUR MONEY =======================
    dict(group="money", term="Capital",
         what="The money you've set aside for one portfolio.",
         how="You set it in Settings. It's private: stored only in your private data repo.",
         matters="Used for suggested quantities and for your cash balance."),
    dict(group="money", term="Average cost",
         what="What you paid per share, on average, for the shares you still hold.",
         how="Each buy updates the average (total paid ÷ total shares). Selling doesn't change it, as "
             "Indian brokers do it.",
         good="Your profit or loss is measured against it.",
         example="Buy 10 at ₹100 and 10 at ₹120: average cost ₹110."),
    dict(group="money", term="Invested",
         what="The money tied up in the shares you hold right now.",
         how="Quantity × average cost.",
         matters="The base for your unrealised P&L."),
    dict(group="money", term="Value",
         what="What the shares you hold are worth today if you sold them all.",
         how="Quantity × today's price.",
         high="Value above invested: you're in profit.",
         low="Value below invested: you're at a loss."),
    dict(group="money", term="Unrealised P&L",
         what="Profit or loss on shares you still hold. It's on paper only, and changes with the price.",
         how="Value − invested.",
         good="It becomes real (realised) only when you sell."),
    dict(group="money", term="Realised P&L",
         what="Profit or loss you've locked in by selling shares.",
         how="(Sell price − average cost) × quantity sold, minus charges.",
         good="This is money actually made or lost; it counts for tax."),
    dict(group="money", term="Cash",
         what="Money in the portfolio that isn't in shares, ready for the next buys.",
         how="Capital − buys + sells − charges.",
         high="Lots of cash: money sitting idle and not invested.",
         low="Negative: you've spent more than the capital you set; update it in Settings."),
    dict(group="money", term="Total return",
         what="Your overall result for a portfolio, as a percentage.",
         how="(Realised + unrealised P&L) ÷ capital (or ÷ invested, if no capital is set).",
         good="Compare it with the index over the same period."),
    dict(group="money", term="Charges",
         what="Brokerage, taxes (STT, stamp duty, GST) and exchange fees on a trade.",
         how="You enter them when you log a trade.",
         good="Keep them low; frequent trading eats returns.",
         matters="They reduce your realised P&L."),
    dict(group="money", term="Suggested quantity",
         what="How many shares to buy of each new pick, so the portfolio stays equally weighted.",
         how="Sale proceeds plus spare cash (or your capital, if you hold nothing yet), split equally "
             "across the buys and rounded down to whole shares.",
         example="₹1,00,000 across 20 stocks is ₹5,000 each: at ₹150 a share, that's 33 shares."),
    dict(group="money", term="Weight %",
         what="How big one holding is within your portfolio.",
         how="Its value ÷ the portfolio's total value.",
         high="A big weight (e.g. 15% in a 20-stock portfolio): one stock can move your whole result.",
         low="A small weight: a winner there won't help much.",
         good="The aim is roughly equal weights: about 5% each in the Nifty 20."),
]


# ---------- range guides: (range, verdict, colour), listed from low values to high ----------
# Colours: red = bad, orange = weak or caution, blue = normal or okay, green = good.
RANGES: dict[str, list[tuple[str, str, str]]] = {
    "Day %": [("Under ±2%", "Normal day", "blue"), ("±2% to ±5%", "Big move", "orange"),
              ("Over ±5%", "Usually news", "red")],
    "Market cap (Mcap)": [("Under ₹30,000 cr", "Small company", "orange"),
                          ("₹30,000 cr – ₹1 lakh cr", "Mid-sized", "blue"),
                          ("Over ₹1 lakh cr", "Large company", "green")],
    "52-week high / low": [("Over 25% below the high", "Weak", "red"),
                           ("5–25% below the high", "Normal", "blue"),
                           ("Within 5% of the high", "Strong", "green")],
    "Dividend yield": [("Under 1%", "Low: keeps profit to grow", "blue"), ("1% – 3%", "Normal", "green"),
                       ("Over 3%", "High: check why", "orange")],
    "Percentile": [("0 – 25", "Bottom quarter", "red"), ("25 – 50", "Below the middle", "orange"),
                   ("50 – 75", "Above the middle", "blue"), ("75 – 100", "Top quarter", "green")],
    "Total score": [("Under 40", "Weak", "red"), ("40 – 55", "Average", "orange"),
                    ("55 – 70", "Good", "blue"), ("Over 70", "Strong", "green")],
    "Health score": [("Under 2", "Weak", "red"), ("2 – 2.75", "Average", "orange"),
                     ("2.75 – 3.5", "Good", "blue"), ("Over 3.5", "Strong", "green")],
    "Rank": [("Top 20 / 30 / 50", "Joins or stays in the list", "green"),
             ("Down to rank 30 / 45 / 75", "Kept if already held", "orange"),
             ("Below rank 30 / 45 / 75", "Sold", "red")],
    "Low data": [("Under 60% of measures", "Low data: less reliable", "red"),
                 ("60% or more", "Enough data", "green")],
    "Since added": [("Below −15%", "Struggling", "red"), ("−15% to +10%", "Normal swings", "blue"),
                    ("Above +10%", "Working", "green")],
    # momentum
    "12-month return (skipping the last month)": [("Below 0%", "Downtrend", "red"),
                                                  ("0% – 15%", "Mild uptrend", "blue"),
                                                  ("15% – 40%", "Strong", "green"),
                                                  ("Over 40%", "Very strong, can overheat", "green")],
    "6-month return": [("Below 0%", "Falling", "red"), ("0% – 10%", "Mild", "blue"),
                       ("10% – 25%", "Strong", "green"), ("Over 25%", "Very strong", "green")],
    "Price vs 200-day average": [("Below 0%", "Downtrend", "red"), ("0% – 15%", "Healthy uptrend", "green"),
                                 ("15% – 30%", "Strong", "green"), ("Over 30%", "Stretched", "orange")],
    "Volatility": [("Under 20% a year", "Calm", "green"), ("20% – 30%", "Normal", "blue"),
                   ("30% – 45%", "Bumpy", "orange"), ("Over 45%", "Wild", "red")],
    # profitability
    "ROE (return on equity)": [("Under 10%", "Weak", "red"), ("10% – 15%", "OK", "orange"),
                               ("15% – 20%", "Good", "green"), ("Over 20%", "Excellent", "green")],
    "ROCE (return on capital employed)": [("Under 10%", "Weak", "red"), ("10% – 15%", "OK", "orange"),
                                          ("15% – 20%", "Good", "green"), ("Over 20%", "Excellent", "green")],
    "Operating margin": [("Under 8%", "Thin", "red"), ("8% – 15%", "OK", "orange"),
                         ("15% – 25%", "Good", "green"), ("Over 25%", "Excellent", "green")],
    "Net margin": [("Under 5%", "Thin", "red"), ("5% – 10%", "OK", "orange"),
                   ("10% – 20%", "Good", "green"), ("Over 20%", "Excellent", "green")],
    # growth
    "3-year revenue CAGR": [("Under 5% a year", "Slow", "red"), ("5% – 10%", "Moderate", "orange"),
                            ("10% – 20%", "Good", "green"), ("Over 20%", "Fast", "green")],
    "Revenue growth": [("Below 0%", "Shrinking", "red"), ("0% – 10%", "Slow", "orange"),
                       ("10% – 20%", "Good", "green"), ("Over 20%", "Fast", "green")],
    "EPS growth": [("Below 0%", "Profit falling", "red"), ("0% – 10%", "Slow", "orange"),
                   ("10% – 25%", "Good", "green"), ("Over 25%", "Fast", "green")],
    "Operating profit growth": [("Below 0%", "Falling", "red"), ("0% – 10%", "Slow", "orange"),
                                ("10% – 25%", "Good", "green"), ("Over 25%", "Fast", "green")],
    # cash flow
    "Operating cash vs net profit": [("Under 0.7", "Warning", "red"), ("0.7 – 1", "OK", "orange"),
                                     ("1 – 1.5", "Good", "green"), ("Over 1.5", "Very good", "green")],
    "FCF yield (free cash flow yield)": [("Below 0%", "Burning cash", "red"), ("0% – 2%", "Low", "orange"),
                                         ("2% – 5%", "Good", "green"), ("Over 5%", "High value", "green")],
    "Debt to equity (Debt/Eq)": [("Under 0.3", "Very safe", "green"), ("0.3 – 1", "Manageable", "blue"),
                                 ("1 – 2", "High", "orange"), ("Over 2", "Risky", "red")],
    "Interest cover": [("Under 2", "Danger", "red"), ("2 – 5", "OK", "orange"),
                       ("5 – 10", "Comfortable", "green"), ("Over 10", "Very safe", "green")],
    # value
    "P/E (price to earnings)": [("Negative", "Loss-making", "red"), ("Under 15", "Cheap: check why", "green"),
                                ("15 – 30", "Normal", "blue"), ("30 – 50", "Pricey", "orange"),
                                ("Over 50", "Very expensive", "red")],
    "P/B (price to book)": [("Under 1", "Below net worth: check why", "green"), ("1 – 3", "Normal", "blue"),
                            ("3 – 8", "Premium", "orange"), ("Over 8", "Very high", "red")],
    "EV/EBITDA": [("Under 8", "Cheap", "green"), ("8 – 15", "Fair", "blue"),
                  ("15 – 25", "Pricey", "orange"), ("Over 25", "Expensive", "red")],
    "P/E vs sector": [("Under 0.8", "Cheaper than peers", "green"), ("0.8 – 1.2", "In line", "blue"),
                      ("Over 1.2", "Dearer than peers", "orange")],
    "P/B vs sector": [("Under 0.8", "Cheaper than peers", "green"), ("0.8 – 1.2", "In line", "blue"),
                      ("Over 1.2", "Dearer than peers", "orange")],
    "Analyst target": [("Under 5 analysts", "Thin coverage", "orange"), ("5 – 15 analysts", "OK", "blue"),
                       ("Over 15 analysts", "Well covered", "green")],
    "Upside": [("Below −10%", "Overvalued", "red"), ("−10% to +10%", "Fair", "blue"),
               ("+10% to +40%", "Undervalued", "green"), ("Over +40%", "Check the confidence", "orange")],
    "Methods": [("1 – 2", "Thin", "orange"), ("3", "OK", "blue"), ("4 – 6", "Solid", "green")],
    # performance and money
    "CAGR (compound annual growth rate)": [("Under 7% a year", "Below a fixed deposit", "red"),
                                           ("7% – 12%", "Average", "orange"),
                                           ("12% – 15%", "Good", "green"), ("Over 15%", "Excellent", "green")],
    "Return (for a period)": [("Below 0%", "Lost money", "red"),
                              ("Positive, but below the index", "Gained, but lagged", "orange"),
                              ("Above the index", "Beat the market", "green")],
    "AI's real edge": [("Below 0 pts", "No edge", "red"), ("0 – 2 pts", "Small", "orange"),
                       ("2 – 5 pts", "Good", "green"), ("Over 5 pts", "Strong", "green")],
    "Total return": [("Below the index", "Lagging", "red"), ("About the index", "In line", "blue"),
                     ("Above the index", "Beating it", "green")],
    "Weight %": [("4% – 6%", "Balanced", "green"), ("6% – 10%", "Overweight", "orange"),
                 ("Over 10%", "Too concentrated", "red")],
}
for _t in TERMS:
    if _t["term"] in RANGES:
        _t["ranges"] = RANGES[_t["term"]]
