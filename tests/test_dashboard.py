"""Render every dashboard page headlessly on fake data and check for exceptions."""
from datetime import date

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from mypropicks import ledger, review
from tests.test_review import _install_fakes

PAGES = ["app_pages/this_month.py", "app_pages/analysis.py", "app_pages/holdings.py",
         "app_pages/log_trade.py", "app_pages/rankings.py", "app_pages/settings.py", "app_pages/how_it_works.py"]


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
