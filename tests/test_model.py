import numpy as np
import pandas as pd
import pytest

from mypropicks.config import DEFAULTS
from mypropicks.eligibility import check_eligibility
from mypropicks.fairvalue import fair_value, sector_medians
from mypropicks.scoring import momentum_metrics, score_universe

FV = DEFAULTS["fair_value"]


def _px(n=300, start=100.0, end=200.0, vol=1e6):
    idx = pd.bdate_range("2025-01-01", periods=n)
    return pd.Series(np.linspace(start, end, n), index=idx), pd.Series(vol, index=idx)


# ---------- eligibility ----------

def test_eligibility_reasons():
    c_ok, v_ok = _px()
    c_short, v_short = _px(n=100)
    c_gap, v_gap = _px()
    v_gap = v_gap.copy()
    v_gap.iloc[-10] = 0
    c_thin, v_thin = _px(vol=10)
    closes = pd.DataFrame({"OK": c_ok, "SHORT": c_short, "GAP": c_gap, "THIN": c_thin})
    vols = pd.DataFrame({"OK": v_ok, "SHORT": v_short, "GAP": v_gap, "THIN": v_thin})
    shares = {"OK": 1e6, "SHORT": 1e6, "GAP": 1e6, "THIN": 1e6}
    e = check_eligibility(closes, vols, shares, liquidity_cr=2)
    assert bool(e.at["OK", "eligible"]) and e.at["OK", "reason"] == ""
    assert e.at["SHORT", "reason"] == "short history"
    assert e.at["GAP", "reason"] == "not traded every day"
    assert e.at["THIN", "reason"] == "low liquidity"
    assert e.at["OK", "avg_mcap_6m"] > 0


# ---------- fair value ----------

def test_label_bands():
    m = {"target_mean": 100.0}
    assert fair_value(m, {}, 85, FV)["label"] == "Undervalued"
    assert fair_value(m, {}, 105, FV)["label"] == "Fair"
    assert fair_value(m, {}, 115, FV)["label"] == "Overvalued"


def test_outlier_dropped():
    # sector P/E 10 x EPS 10 = 100; P/B 2 x 55 = 110; target 90; EV/EBITDA way off (1000)
    m = {"eps": 10, "bvps": 55, "target_mean": 90, "ebitda": 100, "net_debt": 0, "shares": 1}
    med = {"pe": 10, "pb": 2, "ev_ebitda": 10}
    r = fair_value(m, med, 100, FV)
    assert "sector_ev_ebitda" not in r["methods"]
    # weighted geometric mean: P/E x1, P/B x1, analyst target x1 (fewer than 5 analysts)
    assert r["fair_value"] == pytest.approx((100 * 110 * 90) ** (1 / 3))
    assert r["n_methods"] == 3


def test_own_history_methods_and_weights():
    """A stock's own past P/E and P/B count double; so does a target backed by 5+ analysts."""
    m = {"eps": 10, "bvps": 50, "own_pe_hist": 12, "own_pb_hist": 2.2,
         "target_mean": 125, "n_analysts": 8}
    r = fair_value(m, {"pe": 10}, 100, FV)
    assert r["methods"] == {"own_pe": 120.0, "own_pb": 110.0, "sector_pe": 100.0,
                            "analyst_target": 125.0}
    expected = (120 ** 2 * 110 ** 2 * 100 * 125 ** 2) ** (1 / 7)
    assert r["fair_value"] == pytest.approx(expected)


def test_dcf_left_out_by_default():
    """DCF on free data was far off (median ~2.9x below analyst targets), so its weight is 0."""
    m = {"fcf": 100.0, "fcf_cagr3": 0.10, "shares": 10.0, "net_debt": 0.0, "target_mean": 100}
    r = fair_value(m, {}, 100, FV)
    assert "dcf" not in r["methods"]


def test_confidence_from_agreement():
    close = {"eps": 10, "bvps": 50, "own_pe_hist": 10.5, "own_pb_hist": 2.1, "target_mean": 102}
    assert fair_value(close, {"pe": 10, "pb": 2}, 100, FV)["confidence"] == "High"
    assert fair_value({"eps": 10, "target_mean": 200}, {"pe": 10}, 100, FV)["confidence"] == "Medium"
    assert fair_value({"eps": 10, "target_mean": 290}, {"pe": 10}, 100, FV)["confidence"] == "Low"
    assert fair_value({"target_mean": 100}, {}, 100, FV)["confidence"] == "Low"
    assert fair_value({}, {}, 100, FV)["confidence"] == "None"


def test_fair_value_skips_negative_inputs():
    m = {"eps": -5, "bvps": 50, "target_mean": None}
    med = {"pe": 20, "pb": 2}
    r = fair_value(m, med, 100, FV)
    assert "sector_pe" not in r["methods"]
    assert r["methods"] == {"sector_pb": 100.0}
    assert r["n_methods"] == 1


def test_no_data_label():
    r = fair_value({}, {}, 100, FV)
    assert r["label"] == "No data" and r["fair_value"] is None


def test_dcf_positive_when_weighted():
    m = {"fcf": 100.0, "fcf_cagr3": 0.10, "shares": 10.0, "net_debt": 0.0}
    cfg = {**FV, "weights": {**FV["weights"], "dcf": 1}}
    r = fair_value(m, {}, 100, cfg)
    assert r["methods"]["dcf"] > 0


def test_sector_medians_positive_only():
    df = pd.DataFrame({"sector": ["A", "A", "A"], "pe": [10, 20, -5], "pb": [1, 3, 2], "ev_ebitda": [5, 7, None]})
    med = sector_medians(df)
    assert med.loc["A", "pe"] == 15
    assert med.loc["A", "ev_ebitda"] == 6


# ---------- scoring ----------

def _metrics(rows: dict) -> pd.DataFrame:
    cols = ["roe", "roce", "op_margin", "net_margin", "rev_cagr3", "rev_growth", "eps_growth",
            "op_profit_growth", "ocf_to_np", "fcf_yield", "debt_equity", "interest_cover",
            "upside", "pe", "pb", "mom_12_1", "mom_6", "vs_200dma", "vol_1y"]
    df = pd.DataFrame(rows, index=cols).T
    df["sector"] = "S"
    return df.astype({c: float for c in cols})


GOOD = [0.3, 0.3, 0.3, 0.2, 0.2, 0.2, 0.2, 0.2, 1.2, 0.05, 0.1, 20, 0.3, 10, 2, 0.5, 0.3, 0.2, 0.2]
BAD = [0.05, 0.05, 0.05, 0.02, 0.0, 0.0, 0.0, 0.0, 0.5, 0.01, 2.0, 1.5, -0.3, 40, 8, -0.2, -0.1, -0.1, 0.5]


def _elig(syms, inelig=()):
    return pd.DataFrame({"eligible": [s not in inelig for s in syms], "reason": "",
                         "avg_mcap_6m": 1.0}, index=syms)


def test_better_stock_ranks_first():
    m = _metrics({"A": GOOD, "B": BAD})
    s = score_universe(m, _elig(["A", "B"]), DEFAULTS["weights"])
    assert s.at["A", "rank"] == 1 and s.at["B", "rank"] == 2
    assert 0 <= s.at["A", "health"] <= 5


def test_missing_category_reweights():
    m = _metrics({"A": GOOD, "B": BAD, "C": GOOD})
    for col in ["rev_cagr3", "rev_growth", "eps_growth", "op_profit_growth", "roe", "roce",
                "op_margin", "net_margin", "ocf_to_np", "fcf_yield", "debt_equity", "interest_cover"]:
        m.at["C", col] = np.nan
    s = score_universe(m, _elig(["A", "B", "C"]), DEFAULTS["weights"])
    assert not np.isnan(s.at["C", "score"])
    assert np.isnan(s.at["C", "growth"])
    assert bool(s.at["C", "low_data"]) and not bool(s.at["A", "low_data"])


def test_ineligible_ranked_after_eligible():
    m = _metrics({"A": GOOD, "B": BAD})
    s = score_universe(m, _elig(["A", "B"], inelig=("A",)), DEFAULTS["weights"])
    assert s.at["B", "rank"] == 1 and s.at["A", "rank"] == 2


def test_loss_maker_pe_worst():
    bad_pe = list(GOOD)
    bad_pe[13] = -12  # negative P/E
    m = _metrics({"A": GOOD, "L": bad_pe, "B": BAD})
    s = score_universe(m, _elig(["A", "L", "B"]), DEFAULTS["weights"])
    assert s.at["L", "relative_value"] < s.at["A", "relative_value"]


def test_momentum_metrics():
    c, _ = _px(n=300, start=100, end=200)
    mm = momentum_metrics(pd.DataFrame({"X": c}))
    assert mm.at["X", "mom_12_1"] > 0 and mm.at["X", "mom_6"] > 0 and mm.at["X", "vs_200dma"] > 0
