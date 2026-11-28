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
    assert reason("SELL", "A", now, before) == "Fair value cut ₹561 → ₹329 (upside now 19%); score 59 → 58"


def test_sell_price_above_fair_value():
    before = _t(score=61, fair_value=248.0, upside=0.01)
    now = _t(score=59, fair_value=193.0, upside=-0.22)
    assert reason("SELL", "A", now, before) == "Fair value cut ₹248 → ₹193 (price now 22% above it); score 61 → 59"


def test_sell_without_history_names_weak_numbers():
    now = _t(relative_value=20, momentum=30, pe=48.0, mom_6=-0.12, upside=0.2)
    assert reason("SELL", "A", now) == "Expensive at P/E 48; price -12% in 6 months"


def test_sell_ineligible_and_left_index():
    t = _t()
    assert reason("SELL", "A", t, old="ineligible: low liquidity") == "No longer qualifies: too little trading volume"
    assert reason("SELL", "ZZ", t, old="left universe") == "Left the index"
    assert "rank" not in reason("BUY", "A", t).lower()


def test_sell_names_the_biggest_changes_for_the_worse():
    before = _t(pe=20.0, roe=0.18, ltp=100.0, vs_200dma=0.05, mom_6=0.10, score=60, eps_growth=0.2)
    now = _t(pe=24.0, roe=0.14, ltp=88.0, vs_200dma=-0.04, mom_6=-0.02, score=56, eps_growth=0.05)
    assert reason("SELL", "A", now, before) == \
        "P/E up 20.0 → 24.0; 6-month return down +10% → -2%; score 60 → 56"


def test_sell_mentions_falling_profits():
    before = _t(roe=0.20, op_margin=0.30, score=60)
    now = _t(roe=0.12, op_margin=0.22, score=57)
    assert reason("SELL", "A", now, before).startswith("ROE down 20% → 12%; operating margin down 30% → 22%")


def test_buy_leads_with_the_improvement_without_repeating_it():
    before = _t(eps_growth=0.10, fair_value=274.0, upside=-0.49)
    now = _t(growth=90, momentum=88, rev_growth=0.16, eps_growth=1.74, mom_6=0.38, fair_value=405.0, upside=-0.24)
    assert reason("BUY", "A", now, before) == "EPS growth picked up +10% → +174%; price up 38% in 6 months"


def test_crossing_the_200_day_average():
    before, now = _t(vs_200dma=0.03, score=59), _t(vs_200dma=-0.02, score=58)
    assert reason("SELL", "A", now, before).startswith("Price dropped below its 200-day average")
    assert reason("BUY", "A", before, now).startswith("Price rose above its 200-day average")
