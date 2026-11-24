"""The monthly review: rank each universe, decide SELLs and BUYs, write the review folder."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd

from . import fundamentals, ledger, prices, universe
from .config import DISCLAIMER, PORTFOLIOS, data_dir, load_config
from .eligibility import check_eligibility
from .fairvalue import fair_value, sector_medians
from .scoring import momentum_metrics, score_universe
from .sizing import suggest_quantities

Progress = Callable[[str, float], None]


def decide_changes(ranked: pd.DataFrame, held: list[str], n: int) -> dict:
    """No buffer: the new list is the top N. Buys = N - kept, so sells equal buys when you hold N."""
    warnings: list[str] = []
    ranked = ranked.sort_values("rank")
    held = list(dict.fromkeys(held))
    # A held stock whose prices couldn't be fetched this time is kept, not sold on missing data.
    no_price = [s for s in held if s in ranked.index and ranked.at[s, "reason"] == "no price data"]
    for s in no_price:
        warnings.append(f"{s}: price data unavailable this month, so it is kept. Check it by hand.")
    eligible = [s for s in ranked[ranked["eligible"]].index if s not in no_price]
    new_list = no_price[:n] + eligible[: max(n - len(no_price), 0)]
    if len(new_list) < n:
        rest = [s for s in ranked.index if s not in new_list]
        # Prefer fill-ins that at least have a price.
        rest.sort(key=lambda s: ranked.at[s, "reason"] == "no price data")
        extra = rest[: n - len(new_list)]
        warnings.append(f"Warning: only {len(eligible)} eligible stocks; filled {len(extra)} from "
                        f"the next-best ineligible ones: {', '.join(extra)}.")
        new_list += extra

    sell = []
    for s in held:
        if s in new_list:
            continue
        if s not in ranked.index:
            reason = "left universe"
        elif not bool(ranked.at[s, "eligible"]):
            reason = f"ineligible: {ranked.at[s, 'reason']}"
        else:
            reason = f"dropped to rank {int(ranked.at[s, 'rank'])}"
        sell.append((s, reason))
    keep = [s for s in held if s in new_list]
    buy = [s for s in new_list if s not in held]
    if held and len(held) < n:
        warnings.append(f"The portfolio was short: it held {len(held)} of {n}, so the review buys "
                        f"{n - len(held)} extra.")
    if len(held) > n:
        warnings.append(f"The portfolio held {len(held)} stocks, more than {n}.")
    return {"new_list": new_list, "sell": sell, "buy": buy, "keep": keep, "warnings": warnings}


def _review_dir(d: date) -> Path:
    return data_dir() / "reviews" / d.isoformat()


def latest_review(before: date | None = None) -> Path | None:
    root = data_dir() / "reviews"
    if not root.exists():
        return None
    dirs = sorted(p for p in root.iterdir() if p.is_dir() and (p / "summary.md").exists())
    if before:
        dirs = [p for p in dirs if p.name < before.isoformat()]
    return dirs[-1] if dirs else None


def latest_list_dir(portfolio: str, before: date) -> Path | None:
    """The newest earlier review folder that actually contains this portfolio's list."""
    root = data_dir() / "reviews"
    if not root.exists():
        return None
    dirs = sorted(p for p in root.iterdir()
                  if p.is_dir() and p.name < before.isoformat() and (p / f"list_{portfolio}.csv").exists())
    return dirs[-1] if dirs else None


def build_rankings(portfolio: str, cfg: dict, progress: Progress | None = None) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
    """Return (rankings table, failed symbols, closes) for one portfolio's universe."""
    uni = universe.fetch_universe(portfolio).drop_duplicates("symbol").set_index("symbol")
    syms = uni.index.tolist()

    def p(stage, frac):
        if progress:
            progress(f"{PORTFOLIOS[portfolio]['label']}: {stage}", frac)

    closes, vols, failed = prices.get_prices(
        syms, progress=lambda i, t, s: p(f"prices {i + 1}/{t} ({s})", 0.5 * i / max(t, 1)))

    rows = {}
    fund_failed = []
    for i, s in enumerate(syms):
        p(f"fundamentals {i + 1}/{len(syms)} ({s})", 0.5 + 0.5 * i / max(len(syms), 1))
        raw = fundamentals.get_fundamentals(s)
        if raw is None:
            fund_failed.append(s)
            rows[s] = {}
        else:
            rows[s] = fundamentals.extract_metrics(raw)
    metrics = pd.DataFrame.from_dict(rows, orient="index").reindex(syms)
    # Keep every expected column even if every fetch failed.
    expected = list(fundamentals.extract_metrics({}).keys())
    metrics = metrics.reindex(columns=list(dict.fromkeys(list(metrics.columns) + expected)))
    metrics["yahoo_sector"] = metrics["sector"]
    metrics["sector"] = uni["industry"]  # NSE's own industry classification
    metrics["name"] = uni["name"]

    mom = momentum_metrics(closes) if not closes.empty else pd.DataFrame()
    metrics = metrics.join(mom, how="left")
    ltp = closes.ffill().iloc[-1] if not closes.empty else pd.Series(dtype=float)
    metrics["ltp"] = ltp.reindex(syms)

    shares = pd.to_numeric(metrics["shares"], errors="coerce").to_dict()
    elig = check_eligibility(closes, vols, shares, cfg["liquidity_cr"][portfolio],
                             min_history=cfg["eligibility"]["min_history_days"],
                             traded_window=cfg["eligibility"]["traded_days_window"])

    med = sector_medians(metrics)
    fv_rows = {}
    for s in syms:
        m = metrics.loc[s].to_dict()
        md = med.loc[m["sector"]].to_dict() if m.get("sector") in med.index else {}
        fv_rows[s] = fair_value(m, md, m.get("ltp"), cfg["fair_value"])
    metrics["fair_value"] = [fv_rows[s]["fair_value"] for s in syms]
    metrics["upside"] = [fv_rows[s]["upside"] for s in syms]
    metrics["fv_label"] = [fv_rows[s]["label"] for s in syms]
    metrics["fv_methods"] = [json.dumps(fv_rows[s]["methods"]) for s in syms]
    metrics["fv_n_methods"] = [fv_rows[s]["n_methods"] for s in syms]

    scored = score_universe(metrics, elig, cfg["weights"], cfg["low_data_threshold"])
    table = scored.join(metrics.drop(columns=[c for c in scored.columns if c in metrics.columns]))
    table.index.name = "symbol"
    all_failed = sorted(set(failed) | set(fund_failed))
    table["fetch_note"] = ""
    for s in failed:
        table.loc[s, "fetch_note"] = "no price data"
    for s in fund_failed:
        table.loc[s, "fetch_note"] = (table.loc[s, "fetch_note"] + "; no fundamentals").strip("; ")
    return table.sort_values("rank"), all_failed, closes


def _fmt_money(x) -> str:
    return f"₹{x:,.0f}"


def run_review(as_of: date | None = None, portfolios: list[str] | None = None,
               progress: Progress | None = None) -> Path:
    as_of = as_of or date.today()
    cfg = load_config()
    out = _review_dir(as_of)
    out.mkdir(parents=True, exist_ok=True)
    trades = ledger.load_trades()

    lines = [f"# MyProPicks review — {as_of.isoformat()}", "",
             "Prices are the latest available closes. Place trades on the next trading day.", ""]
    for pf in portfolios or list(PORTFOLIOS):
        meta = PORTFOLIOS[pf]
        n = meta["n"]
        table, failed, _ = build_rankings(pf, cfg, progress)
        table.to_csv(out / f"rankings_{pf}.csv")

        holdings_held = ledger.held_symbols(trades, pf)
        prev_list = []
        prev_entries = {}
        prev_dir = latest_list_dir(pf, as_of)
        if prev_dir:
            pl = pd.read_csv(prev_dir / f"list_{pf}.csv")
            prev_list = pl["symbol"].tolist()
            prev_entries = pl.set_index("symbol")[["added_on", "added_price"]].to_dict("index")
        if holdings_held:
            basis, held = "your logged holdings", holdings_held
        else:
            basis, held = ("last month's list" if prev_list else "nothing (first run)"), prev_list
        ch = decide_changes(table, held, n)

        ltp = table["ltp"].to_dict()
        lst = pd.DataFrame({"symbol": ch["new_list"]})
        lst.insert(0, "rank", range(1, len(lst) + 1))
        lst["name"] = lst["symbol"].map(table["name"])
        lst["industry"] = lst["symbol"].map(table["sector"])
        lst["added_on"] = [prev_entries.get(s, {}).get("added_on", as_of.isoformat()) for s in lst["symbol"]]
        lst["added_price"] = [prev_entries.get(s, {}).get("added_price", ltp.get(s)) for s in lst["symbol"]]
        lst.to_csv(out / f"list_{pf}.csv", index=False)

        # Quantities: first run uses capital; swaps use sale proceeds plus spare cash.
        capital = float(cfg["capital"].get(pf) or 0)
        if holdings_held:
            h = ledger.holdings(trades, pf).set_index("symbol")
            proceeds = sum(h.at[s, "qty"] * (ltp.get(s) if pd.notna(ltp.get(s)) else h.at[s, "avg_cost"]) for s, _ in ch["sell"] if s in h.index)
            budget = proceeds + max(ledger.cash(trades, pf, capital), 0)
        else:
            budget = capital if not prev_list else 0
        qty = suggest_quantities(ch["buy"], {k: v for k, v in ltp.items() if v == v}, budget)
        sell_qty = {}
        if holdings_held:
            h = ledger.holdings(trades, pf).set_index("symbol")
            sell_qty = {s: h.at[s, "qty"] for s, _ in ch["sell"] if s in h.index}

        rows = [{"action": "SELL", "symbol": s, "reason": r, "qty": sell_qty.get(s, ""),
                 "price": ltp.get(s, "")} for s, r in ch["sell"]]
        rows += [{"action": "BUY", "symbol": s, "reason": f"rank {int(table.at[s, 'rank'])}",
                  "qty": qty.get(s, "") if budget else "", "price": ltp.get(s)} for s in ch["buy"]]
        pd.DataFrame(rows, columns=["action", "symbol", "reason", "qty", "price"]).to_csv(
            out / f"changes_{pf}.csv", index=False)

        lines += [f"## {meta['label']} ({n} stocks from {meta['index_name']})", "",
                  f"Compared against: {basis}. {len(ch['sell'])} out, {len(ch['buy'])} in, "
                  f"{len(ch['keep'])} kept.", ""]
        if rows:
            lines += ["| Action | Stock | Why | Qty | Last close |", "|---|---|---|---|---|"]
            for r in rows:
                price = f"{r['price']:,.2f}" if isinstance(r["price"], (int, float)) and r["price"] == r["price"] else "—"
                lines.append(f"| {r['action']} | {r['symbol']} | {r['reason']} | {r['qty'] if r['qty'] != '' else '—'} | {price} |")
            lines.append("")
            if not budget and ch["buy"]:
                lines += [f"_Set capital for {pf} in config.yaml (or log your trades) to get suggested quantities._", ""]
            else:
                lines += [f"_Budget for buys: {_fmt_money(budget)}, split equally._", ""]
        else:
            lines += ["No changes this month.", ""]
        for w in ch["warnings"]:
            lines += [f"- ⚠ {w}"]
        if failed:
            lines += [f"- ⚠ Data could not be fetched for {len(failed)} stock(s): {', '.join(failed)}. "
                      "They were ranked with what was available, or as ineligible if prices were missing."]
        low = table[table["low_data"] & table.index.isin(ch["new_list"])].index.tolist()
        if low:
            lines += [f"- Low data (scored on under 60% of metrics): {', '.join(low)}."]
        lines.append("")
    lines += ["---", f"_{DISCLAIMER}_", ""]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return out
