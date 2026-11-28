"""Render every dashboard page headlessly on fake data and check for exceptions."""
from datetime import date

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from mypropicks import ledger, review
from tests.test_review import _install_fakes

PAGES = ["app_pages/this_month.py", "app_pages/analysis.py", "app_pages/holdings.py",
         "app_pages/log_trade.py", "app_pages/rankings.py", "app_pages/settings.py", "app_pages/how_it_works.py",
         "app_pages/info.py"]


@pytest.fixture
def fake_world(tmp_data, monkeypatch):
    _install_fakes(monkeypatch)
    from mypropicks import prices
    monkeypatch.setattr(prices, "index_history", lambda t, s: pd.Series(dtype=float))
    review.run_review(as_of=date(2026, 12, 1), portfolios=["nifty20"])
    ledger.append_trade("2026-11-02", "nifty20", "S01", "BUY", 10, 100)
    return tmp_data


def _run(page):
    at = AppTest.from_file("../dashboard/app.py", default_timeout=60)
    at.run()
    at.switch_page(page)
    at.run()
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(fake_world, page):
    at = _run(page)
    assert not at.exception, [e.message for e in at.exception]


def test_analysis_shows_full_list(fake_world):
    at = _run("app_pages/analysis.py")
    assert len(at.dataframe[0].value) == 20


def test_empty_state(tmp_data):
    at = _run("app_pages/analysis.py")
    assert not at.exception
    assert any("No list yet" in (i.title or "") or "first review" in i.value for i in at.info)


def test_analysis_shows_ai_vs_index(fake_world):
    f = fake_world / "backtest" / "nifty20.csv"
    f.parent.mkdir(parents=True)
    pd.DataFrame({"date": ["2023-11-30", "2024-11-29", "2025-11-28"], "ai": [100.0, 121.0, 146.41],
                  "baseline": [100.0, 115.0, 132.25], "index": [100.0, 110.0, 121.0]}).to_csv(f, index=False)
    import streamlit as st
    st.cache_data.clear()  # earlier page tests cached "no backtest yet"
    at = _run("app_pages/analysis.py")
    assert not at.exception, [e.message for e in at.exception]
    labels = [m.label for m in at.metric]
    assert any("AI CAGR" in x for x in labels) and any("Nifty 50 CAGR" in x for x in labels)
    ai = next(m for m in at.metric if "AI CAGR" in m.label)
    assert ai.value == "+21.0%"
    edge = next(m for m in at.metric if "real edge" in m.label)
    assert edge.value == "+6.0 pts a year"  # 21% vs 15% a year


def test_info_shares_add_up_and_search_works(fake_world):
    """Every scoring measure is explained, and their score shares add up to 100%."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))
    from glossary import TERMS
    from mypropicks.scoring import ALL_METRICS
    explained = {t["metric"] for t in TERMS if t.get("metric")}
    assert explained == set(ALL_METRICS)
    assert all(t.get("ranges") for t in TERMS if t.get("metric"))  # every measure has a range guide
    colours = {c for t in TERMS for _, _, c in t.get("ranges", [])}
    assert colours <= {"red", "orange", "blue", "green"}
    at = _run("app_pages/info.py")
    at.text_input[0].input("roe").run()
    assert not at.exception
    labels = [e.label for e in at.expander]
    assert any(x.startswith("ROE") for x in labels)
    assert len(labels) < 10  # filtered, not the whole glossary


def test_theme_file_is_valid():
    """A broken config.toml silently drops the whole theme, so check it parses."""
    import tomllib
    from pathlib import Path
    cfg = tomllib.loads((Path(__file__).resolve().parents[1] / "dashboard/.streamlit/config.toml")
                        .read_text(encoding="utf-8"))
    assert cfg["theme"]["metricValueFontSize"] == "1.6rem"


def test_analysis_survives_missing_prices(fake_world, monkeypatch):
    """Yahoo sometimes sends no usable price at all: the page must still render."""
    import glob
    import streamlit as st
    import sys
    from mypropicks import prices
    blank = lambda syms: {s: {"ltp": float("nan"), "change_pct": float("nan")} for s in syms}  # noqa: E731
    monkeypatch.setattr(prices, "latest_quotes", blank)
    if "common" in sys.modules:                    # the page's own copy, if already imported
        monkeypatch.setattr(sys.modules["common"], "latest_quotes", blank)
    for f in glob.glob(str(fake_world / "reviews" / "*" / "rankings_nifty20.csv")):
        rk = pd.read_csv(f)
        rk["ltp"] = None
        rk.to_csv(f, index=False)
    st.cache_data.clear()
    at = _run("app_pages/analysis.py")
    assert not at.exception, [e.message for e in at.exception]


def test_prices_note():
    import sys
    sys.path.insert(0, "dashboard")
    from common import prices_note
    assert "3:28 pm IST" in prices_note({"A": {"as_of": "2026-11-26 15:28", "live": True}})
    assert "26 Nov 2026" in prices_note({"A": {"as_of": "2026-11-26", "live": False}})
    assert "unavailable" in prices_note({})


def test_with_live_adds_todays_price():
    import sys
    sys.path.insert(0, "dashboard")
    from common import with_live
    hist = pd.DataFrame({"PNB": [150.0, 148.61], "HAL": [4900.0, 4930.0]},
                        index=pd.to_datetime(["2026-11-24", "2026-11-25"]))
    out = with_live(hist, {"PNB": {"ltp": 147.5, "as_of": "2026-11-26 15:28"},
                           "XYZ": {"ltp": 1.0, "as_of": "2026-11-26 15:28"}})
    assert out.index[-1] == pd.Timestamp("2026-11-26")
    assert out.at[pd.Timestamp("2026-11-26"), "PNB"] == 147.5
    assert "XYZ" not in out and len(hist) == 2            # unknown symbols ignored, input untouched
    again = with_live(out, {"PNB": {"ltp": 147.0, "as_of": "2026-11-26 15:30"}})
    assert len(again) == 3 and again.at[pd.Timestamp("2026-11-26"), "PNB"] == 147.0


def test_footer_next_review_and_links(fake_world):
    import sys
    sys.path.insert(0, "dashboard")
    from common import _next_review
    assert _next_review(date(2026, 11, 26)) == date(2026, 12, 1)
    assert _next_review(date(2026, 12, 1)) == date(2027, 1, 1)
    at = _run("app_pages/info.py")
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "Next review" in text and "Explore" in text
    assert any("Rudra Narayan Das" in c.value and "github.com/rnxtremer" in c.value for c in at.caption)


def test_market_strip_shows_indices(fake_world):
    import streamlit as st
    st.cache_data.clear()
    at = _run("app_pages/analysis.py")
    assert not at.exception
    labels = [m.label for m in at.metric]
    for name in ("Nifty 50", "Sensex", "Bank Nifty", "India VIX", "Nasdaq", "S&P 500"):
        assert name in labels
    assert any(m.value == "25,000.00" for m in at.metric)


def test_leavers_and_journey_chart(fake_world):
    import sys
    sys.path.insert(0, "dashboard")
    from common import journey_chart, leavers
    from pathlib import Path
    rev = sorted((fake_world / "reviews").iterdir())[-1]
    later = rev.parent / "2027-01-01"
    later.mkdir()
    for f in rev.iterdir():
        (later / f.name).write_bytes(f.read_bytes())
    lst = pd.read_csv(rev / "list_nifty20.csv")
    s = lst["symbol"].iloc[0]
    # an old-style changes file (no added_* columns): looked up in the previous list
    pd.DataFrame({"action": ["SELL"], "symbol": [s], "reason": ["dropped"], "qty": [None],
                  "price": [123.0]}).to_csv(later / "changes_nifty20.csv", index=False)
    out = leavers(Path(later), "nifty20")
    assert out.at[0, "added_on"] == lst["added_on"].iloc[0]
    assert out.at[0, "added_price"] == pytest.approx(lst["added_price"].iloc[0])
    px = pd.Series([100.0, 105, 110, 108], index=pd.date_range("2026-11-02", periods=4))
    chart = journey_chart(px, "2026-11-03", 105.0, "2026-11-05", 108.0)
    assert len(chart.layer) >= 6
    import streamlit as st
    st.cache_data.clear()
    at = _run("app_pages/this_month.py")
    assert not at.exception, [e.message for e in at.exception]
    assert any("How the leaving stocks did" in m.value for m in at.markdown)


def test_journey_chart_formats_are_valid():
    """A '₹' inside a number format breaks the chart (no date axis); it belongs in titles only."""
    import json
    import sys
    sys.path.insert(0, "dashboard")
    from common import journey_chart
    px = pd.Series([100.0, 105, 110, 108], index=pd.date_range("2026-11-02", periods=4))
    spec = json.dumps(journey_chart(px, "2026-11-03", 105.0, "2026-11-05", 108.0,
                                    avg=px.rolling(2).mean()).to_dict())
    import re
    formats = re.findall(r'"format": "([^"]*)"', spec)
    assert formats and all("₹" not in f and "\u20b9" not in f for f in formats)
    assert '"padding"' not in spec       # custom padding cut off the date axis in Streamlit


def test_this_month_says_replaced(fake_world):
    at = _run("app_pages/this_month.py")
    assert not at.exception
    values = [m.value for m in at.metric]
    assert not any(" in · " in v for v in values)
    assert any(v.endswith("replaced") or v.endswith("added") or v == "No changes" for v in values)


def test_this_month_has_no_qty_column(fake_world):
    at = _run("app_pages/this_month.py")
    assert not at.exception
    assert all("qty" not in df.value.columns for df in at.dataframe)


def test_this_month_reasons_are_plain_english(fake_world):
    import streamlit as st
    st.cache_data.clear()
    at = _run("app_pages/this_month.py")
    assert not at.exception
    for df in at.dataframe:
        if "reason" in df.value.columns:
            assert not df.value["reason"].astype(str).str.match(r"^(dropped to )?rank \d").any()
