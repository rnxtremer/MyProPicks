import pandas as pd

from mypropicks.explain import reason


def _t(**cols):
    return pd.DataFrame(cols, index=["A"])


def test_buy_names_strengths_and_improvement():
    now = _t(profitability=93, growth=65, cash_flow=70, relative_value=50, momentum=27, upside=0.0)
    before = _t(profitability=93, growth=65, cash_flow=70, relative_value=41, momentum=30, upside=0.0)
    assert reason("BUY", "A", now, before) == "Highly profitable, strong cash flow; valuation improved"


def test_buy_mentions_gap_to_fair_value():
    now = _t(profitability=80, growth=20, cash_flow=10, relative_value=30, momentum=30, upside=0.44)
    assert reason("BUY", "A", now) == "Highly profitable; 44% below fair value"


def test_sell_says_what_weakened():
    now = _t(profitability=60, growth=25, cash_flow=70, relative_value=89, momentum=49, upside=0.19)
    before = _t(profitability=60, growth=25, cash_flow=70, relative_value=95, momentum=50, upside=0.5)
    assert reason("SELL", "A", now, before) == "Got pricier vs peers; overtaken by stronger stocks"


def test_sell_without_history_names_weak_spots():
    now = _t(profitability=60, growth=50, cash_flow=70, relative_value=20, momentum=30, upside=-0.2)
    assert reason("SELL", "A", now) == "Looks expensive, weak price trend; above fair value"


def test_sell_ineligible_and_left_index():
    t = _t(profitability=60, growth=50, cash_flow=70, relative_value=20, momentum=30, upside=0.0)
    assert reason("SELL", "A", t, old="ineligible: low liquidity") == "No longer qualifies: too little trading volume"
    assert reason("SELL", "ZZ", t, old="left universe") == "Left the index"
    assert "rank" not in reason("BUY", "A", t).lower()
