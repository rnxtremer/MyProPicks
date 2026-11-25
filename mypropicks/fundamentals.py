"""Company figures from Yahoo Finance, cached for a month, and the metrics built from them."""
from __future__ import annotations

import json
import math
import time

from .config import data_dir
from .prices import yahoo

INFO_KEYS = [
    "currentPrice", "marketCap", "trailingPE", "priceToBook", "returnOnEquity", "debtToEquity",
    "dividendYield", "targetMeanPrice", "numberOfAnalystOpinions", "enterpriseToEbitda",
    "bookValue", "trailingEps", "sector", "industry", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
    "sharesOutstanding", "freeCashflow", "operatingMargins", "profitMargins", "revenueGrowth",
    "earningsGrowth", "totalDebt", "totalCash", "ebitda", "longName",
]


def _frame_to_dict(df) -> dict:
    if df is None or getattr(df, "empty", True):
        return {}
    out = {}
    for row in df.index:
        vals = {}
        for col in df.columns:
            v = df.at[row, col]
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
            if not math.isnan(v):
                vals[str(col.date()) if hasattr(col, "date") else str(col)] = v
        if vals:
            out[str(row)] = vals
    return out


def _cache_file(symbol: str):
    return data_dir() / "cache" / "fundamentals" / f"{symbol.replace('&', '_and_')}.json"


def _monthly_closes(t) -> dict:
    """Five years of month-end closes (split-adjusted), for the stock's own past P/E and P/B."""
    try:
        h = t.history(period="5y", interval="1mo", auto_adjust=True)
    except Exception:  # noqa: BLE001
        return {}
    if h is None or h.empty:
        return {}
    c = h["Close"].dropna()
    return {str(k.date()): float(v) for k, v in c.items()}


def _download(symbol: str) -> dict:
    import yfinance as yf

    t = yf.Ticker(yahoo(symbol))
    info = t.info or {}
    return {
        "monthly_close": _monthly_closes(t),
        "info": {k: info.get(k) for k in INFO_KEYS},
        "financials": _frame_to_dict(t.financials),
        "cashflow": _frame_to_dict(t.cashflow),
        "balance_sheet": _frame_to_dict(t.balance_sheet),
        "quarterly": _frame_to_dict(t.quarterly_financials),
        "fetched": time.time(),
    }


def get_fundamentals(symbol: str, max_age_days: int = 30) -> dict | None:
    f = _cache_file(symbol)
    if f.exists() and time.time() - f.stat().st_mtime < max_age_days * 86400:
        cached = json.loads(f.read_text(encoding="utf-8"))
        if "monthly_close" in cached:  # older caches lack price history: fetch again
            return cached
    try:
        raw = _download(symbol)
    except Exception:  # noqa: BLE001
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    if not raw["info"].get("marketCap") and not raw["financials"]:
        return None
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(raw), encoding="utf-8")
    return raw


# ---------- metric extraction ----------

def _series(section: dict, row: str) -> list[float]:
    """Values for a row, newest year first."""
    vals = section.get(row) or {}
    return [vals[k] for k in sorted(vals, reverse=True)]


def _latest(section: dict, row: str):
    s = _series(section, row)
    return s[0] if s else None


def _growth(section: dict, row: str):
    s = _series(section, row)
    if len(s) >= 2 and s[1] and s[1] > 0:
        return s[0] / s[1] - 1
    return None


def _cagr(section: dict, row: str, years: int = 3):
    s = _series(section, row)[: years + 1]
    if len(s) < 2:
        return None
    new, old, n = s[0], s[-1], len(s) - 1
    if old is None or old <= 0 or new is None or new <= 0:
        return None
    return (new / old) ** (1 / n) - 1


def _div(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def _median(xs: list[float]) -> float | None:
    xs = sorted(xs)
    if not xs:
        return None
    mid = len(xs) // 2
    return xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2


def _own_history(raw: dict) -> tuple[float | None, float | None]:
    """Median P/E and P/B the stock itself traded at, at each past financial year end.

    Per-share figures use today's share count, because the prices are split-adjusted; reported
    EPS isn't always restated after a split or bonus. Needs at least two years, else None.
    """
    closes = raw.get("monthly_close") or {}
    shares = _num((raw.get("info") or {}).get("sharesOutstanding"))
    if not closes or not shares:
        return None, None
    months = sorted(closes)

    def price_at(fy: str) -> float | None:
        before = [m for m in months if m <= fy[:10]]  # the bar for the year-end month itself
        return closes[before[-1]] if before else None

    fin = raw.get("financials") or {}
    ni = fin.get("Net Income Common Stockholders") or fin.get("Net Income") or {}
    eq = (raw.get("balance_sheet") or {}).get("Stockholders Equity") or {}
    pes, pbs = [], []
    for fy, v in ni.items():
        p, v = price_at(fy), _num(v)
        if p and v and v > 0:
            pes.append(p / (v / shares))
    for fy, v in eq.items():
        p, v = price_at(fy), _num(v)
        if p and v and v > 0:
            pbs.append(p / (v / shares))
    return (_median(pes) if len(pes) >= 2 else None, _median(pbs) if len(pbs) >= 2 else None)


def extract_metrics(raw: dict) -> dict:
    info = raw.get("info", {}) or {}
    fin = raw.get("financials", {}) or {}
    cf = raw.get("cashflow", {}) or {}
    bs = raw.get("balance_sheet", {}) or {}

    revenue = _latest(fin, "Total Revenue")
    op_inc = _latest(fin, "Operating Income")
    net_inc = _latest(fin, "Net Income")
    ebit = _latest(fin, "EBIT")
    ebitda = _latest(fin, "EBITDA") or _num(info.get("ebitda"))
    interest = _latest(fin, "Interest Expense")
    equity = _latest(bs, "Stockholders Equity")
    debt = _latest(bs, "Total Debt")
    if debt is None:
        debt = _num(info.get("totalDebt"))
    cash_bs = _latest(bs, "Cash And Cash Equivalents")
    if cash_bs is None:
        cash_bs = _num(info.get("totalCash"))
    ocf = _latest(cf, "Operating Cash Flow")
    fcf = _latest(cf, "Free Cash Flow")
    if fcf is None:
        fcf = _num(info.get("freeCashflow"))
    mcap = _num(info.get("marketCap"))
    de = _num(info.get("debtToEquity"))
    dy = _num(info.get("dividendYield"))

    own_pe, own_pb = _own_history(raw)

    roe = _num(info.get("returnOnEquity"))
    if roe is None:
        roe = _div(net_inc, equity) if equity and equity > 0 else None

    return {
        "roe": roe,
        "roce": _div(ebit, (equity or 0) + (debt or 0)) if equity else None,
        "op_margin": _div(op_inc, revenue) if op_inc is not None else _num(info.get("operatingMargins")),
        "net_margin": _div(net_inc, revenue) if net_inc is not None else _num(info.get("profitMargins")),
        "rev_cagr3": _cagr(fin, "Total Revenue"),
        "rev_growth": _growth(fin, "Total Revenue") if fin.get("Total Revenue") else _num(info.get("revenueGrowth")),
        "eps_growth": _growth(fin, "Diluted EPS") if fin.get("Diluted EPS") else _num(info.get("earningsGrowth")),
        "op_profit_growth": _growth(fin, "Operating Income"),
        "ocf_to_np": _div(ocf, net_inc) if net_inc and net_inc > 0 else None,
        "fcf_yield": _div(fcf, mcap),
        "debt_equity": de / 100 if de is not None else (_div(debt, equity) if equity and equity > 0 else None),
        "interest_cover": _div(ebit, abs(interest)) if interest else None,
        "pe": _num(info.get("trailingPE")),
        "pb": _num(info.get("priceToBook")),
        "ev_ebitda": _num(info.get("enterpriseToEbitda")),
        "eps": _num(info.get("trailingEps")),
        "bvps": _num(info.get("bookValue")),
        "ebitda": ebitda,
        "net_debt": (debt or 0) - (cash_bs or 0) if (debt is not None or cash_bs is not None) else None,
        "shares": _num(info.get("sharesOutstanding")),
        "fcf": fcf,
        "fcf_cagr3": _cagr(cf, "Free Cash Flow"),
        "target_mean": _num(info.get("targetMeanPrice")),
        "n_analysts": _num(info.get("numberOfAnalystOpinions")),
        "own_pe_hist": own_pe,
        "own_pb_hist": own_pb,
        "market_cap": mcap,
        "dividend_yield": dy / 100 if dy is not None else None,
        "high_52w": _num(info.get("fiftyTwoWeekHigh")),
        "low_52w": _num(info.get("fiftyTwoWeekLow")),
        "sector": info.get("sector"),
    }


def quarterly_summary(raw: dict, n: int = 4) -> list[dict]:
    """Last n quarters of revenue and net profit, oldest first."""
    q = raw.get("quarterly", {}) or {}
    rev = q.get("Total Revenue") or {}
    ni = q.get("Net Income") or {}
    keys = sorted(set(rev) | set(ni))[-n:]
    return [{"quarter": k, "revenue": rev.get(k), "net_profit": ni.get(k)} for k in keys]


# ---------- point in time (for the backtest) ----------

def as_of(raw: dict, when, price: float, lag_days: int = 90) -> dict:
    """The company as the model could have seen it on `when`, at share price `price`.

    Annual results count only once `lag_days` have passed since the financial year ended (Indian
    companies publish within about 60 days). Valuation ratios are rebuilt from those results and
    the price, using today's share count (prices are split-adjusted). There's no history of
    analyst targets, so none is used.
    """
    import datetime as _dt

    when = _dt.date.fromisoformat(str(when)[:10])  # accepts date, datetime, Timestamp or text

    def visible(section: dict) -> dict:
        out = {}
        for row, vals in (section or {}).items():
            kept = {k: v for k, v in (vals or {}).items()
                    if _dt.date.fromisoformat(k[:10]) + _dt.timedelta(days=lag_days) <= when}
            if kept:
                out[row] = kept
        return out

    fin, bs, cf = visible(raw.get("financials")), visible(raw.get("balance_sheet")), visible(raw.get("cashflow"))
    info0 = raw.get("info") or {}
    shares = _num(info0.get("sharesOutstanding"))
    ni = _latest(fin, "Net Income Common Stockholders")
    if ni is None:
        ni = _latest(fin, "Net Income")
    equity = _latest(bs, "Stockholders Equity")
    ebitda = _latest(fin, "EBITDA")
    debt = _latest(bs, "Total Debt") or 0.0
    cash = _latest(bs, "Cash And Cash Equivalents") or 0.0
    eps = ni / shares if ni is not None and shares else None
    bvps = equity / shares if equity is not None and shares else None
    mcap = price * shares if price and shares else None
    info = {
        "sharesOutstanding": shares,
        "sector": info0.get("sector"),
        "trailingEps": eps,
        "bookValue": bvps,
        "trailingPE": price / eps if eps and eps > 0 and price else None,
        "priceToBook": price / bvps if bvps and bvps > 0 and price else None,
        "marketCap": mcap,
        "enterpriseToEbitda": (mcap + debt - cash) / ebitda if mcap and ebitda and ebitda > 0 else None,
        "targetMeanPrice": None,
        "numberOfAnalystOpinions": None,
    }
    closes = {k: v for k, v in (raw.get("monthly_close") or {}).items() if k <= when.isoformat()}
    return {"info": info, "financials": fin, "balance_sheet": bs, "cashflow": cf,
            "monthly_close": closes}
