import pandas as pd

from mypropicks.explain import reason

BASE = dict(profitability=50, growth=50, cash_flow=50, relative_value=50, momentum=50, score=58,
            roe=0.12, op_margin=0.2, rev_growth=0.1, eps_growth=0.1, fcf_yield=0.01, ocf_to_np=0.8,
            pe=20.0, pb=3.0, mom_6=0.0, vs_200dma=0.0, ltp=100.0, fair_value=100.0, upside=0.0)


def _t(**cols):
    return pd.DataFrame({**BASE, **cols}, index=["A"])


def test_buy_quotes_profit_numbers_and_fair_value_gap():
    now = _t(profitability=93, cash_flow=65, roe=0.95, op_margin=0.47, fair_value=564.0, upside=0.09)
    assert reason("BUY", "A", now) == "ROE 95%, 47% operating margin; 9% below fair value (₹564)"


def test_buy_growth_and_momentum():
    now = _t(growth=95, momentum=87, rev_growth=0.16, eps_growth=1.74, mom_6=0.38)
    assert reason("BUY", "A", now) == "Sales +16%, EPS +174% last year; price up 38% in 6 months"


def test_buy_never_calls_a_falling_price_a_strength():
    now = _t(momentum=90, mom_6=-0.05, vs_200dma=-0.05, profitability=60)
    assert "price" not in reason("BUY", "A", now).lower()


def test_sell_explains_a_fair_value_cut():
    before = _t(score=59.4, fair_value=561.0, upside=1.04)
    now = _t(score=57.8, fair_value=329.0, upside=0.19)
    assert reason("SELL", "A", now, before) == "Fair value cut to ₹329 from ₹561 (upside 19%, was 104%); score 59 → 58"


def test_sell_price_above_fair_value():
    before = _t(score=61, fair_value=248.0, upside=0.01)
    now = _t(score=59, fair_value=193.0, upside=-0.22)
    assert reason("SELL", "A", now, before) == "Fair value cut to ₹193 from ₹248 (price now 22% above it); score 61 → 59"


def test_sell_without_history_names_weak_numbers():
    now = _t(relative_value=20, momentum=30, pe=48.0, mom_6=-0.12, upside=0.2)
    assert reason("SELL", "A", now) == "Expensive at P/E 48; price -12% in 6 months"


def test_sell_ineligible_and_left_index():
    t = _t()
    assert reason("SELL", "A", t, old="ineligible: low liquidity") == "No longer qualifies: too little trading volume"
    assert reason("SELL", "ZZ", t, old="left universe") == "Left the index"
    assert "rank" not in reason("BUY", "A", t).lower()
