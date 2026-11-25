import streamlit as st

from common import config, footer
from glossary import GROUPS, TERMS
from mypropicks.review import keep_within
from mypropicks.scoring import CATEGORIES

cfg = config()
weights = cfg["weights"]
liq = cfg["liquidity_cr"]
AREA_NAMES = {"momentum": "momentum", "profitability": "profitability", "growth": "growth",
              "relative_value": "relative value", "cash_flow": "cash flow"}
FILL = {
    "weights": ", ".join(f"{AREA_NAMES[k]} {v:.0%}" for k, v in
                         sorted(weights.items(), key=lambda kv: -kv[1])),
    "liquidity": f"₹{liq['nifty20']} cr for the Nifty 100, ₹{liq['midcap30']} cr Midcap, "
                 f"₹{liq['smallcap50']} cr Smallcap",
    "cutoffs": " / ".join(str(keep_within(cfg, k)) for k in ("nifty20", "midcap30", "smallcap50")),
}


def pct(x: float) -> str:
    """6.25% stays 6.25%, 5% stays 5%: exact shares, so they visibly add up."""
    return f"{x * 100:.3g}%"


def score_share(metric: str) -> tuple[float, str, bool] | None:
    """(share of the total score, area name, higher is better) for a scoring measure."""
    for area, measures in CATEGORIES.items():
        for m, higher in measures:
            if m == metric:
                return weights.get(area, 0) / len(measures), AREA_NAMES[area], higher
    return None


st.title(":material/menu_book: Info")
st.markdown("Every term used in MyProPicks, explained in plain words: **what it is**, **how it's "
            "worked out**, **what it means when it's high or low**, a **range guide** to what's good and "
            "bad, and **how it can affect the share price**. Search for a word, or pick a topic, then open any term.")

query = st.text_input("Search", placeholder="e.g. ROE, fair value, CAGR", icon=":material/search:",
                      max_chars=40).strip().lower()
group_names = {key: f"{icon} {name}" for key, icon, name in GROUPS}
pick = st.pills("Topic", list(group_names), format_func=lambda k: group_names[k],
                selection_mode="single")


def fill(text: str) -> str:
    return text.format(**FILL) if text else ""


def card(t: dict, share) -> None:
    """One term: what it is, how it's worked out, reading high and low, price effect, use, example."""
    st.markdown(f"##### :material/help: What it is\n{fill(t['what'])}")
    if t.get("how"):
        st.markdown(f"##### :material/calculate: How it's worked out\n{fill(t['how'])}")
    if t.get("high") or t.get("low"):
        # Colour by direction when the score says which way is better; neutral otherwise.
        hi_c, lo_c = ("green", "red") if share and share[2] else ("red", "green") if share else ("blue", "orange")
        c1, c2 = st.columns(2)
        if t.get("high"):
            with c1.container(border=True, height="stretch"):
                st.markdown(f"**:{hi_c}[:material/arrow_upward: When it's high]**")
                st.markdown(fill(t["high"]))
        if t.get("low"):
            with c2.container(border=True, height="stretch"):
                st.markdown(f"**:{lo_c}[:material/arrow_downward: When it's low]**")
                st.markdown(fill(t["low"]))
    if t.get("ranges"):
        st.markdown("##### :material/straighten: Range guide")
        with st.container(horizontal=True):
            for rng, verdict, colour in t["ranges"]:
                with st.container(border=True, width="stretch"):
                    st.markdown(f":{colour}-badge[{verdict}]")
                    st.markdown(f"**{rng}**")
        st.caption("Typical levels for Indian companies. Always compare within the same industry.")
    if t.get("good"):
        st.markdown(f"##### :material/thumb_up: What's good\n{fill(t['good'])}")
    if t.get("price"):
        st.markdown(f"##### :material/candlestick_chart: Effect on the share price\n{fill(t['price'])}")
    if t.get("matters") or share:
        st.markdown("##### :material/tune: In MyProPicks")
        if t.get("matters"):
            st.markdown(fill(t["matters"]))
        if share:
            st.markdown(
                f":violet-badge[:material/pie_chart: {pct(share[0])} of the total score] "
                f":gray-badge[part of {share[1]}] "
                + (":green-badge[:material/arrow_upward: higher is better]" if share[2]
                   else ":orange-badge[:material/arrow_downward: lower is better]"))
    if t.get("example"):
        st.info(fill(t["example"]), title="Example", icon=":material/lightbulb:")


def matches(t: dict) -> bool:
    if pick and t["group"] != pick:
        return False
    if not query:
        return True
    text = " ".join(str(t.get(k, "")) for k in ("term", "what", "how", "high", "low", "good",
                                                   "price", "matters", "example"))
    return query in text.lower()


shown = 0
for key, icon, name in GROUPS:
    terms = [t for t in TERMS if t["group"] == key and matches(t)]
    if not terms:
        continue
    shown += len(terms)
    st.subheader(f"{icon} {name}")
    for t in terms:
        share = score_share(t["metric"]) if t.get("metric") else None
        label = t["term"] + (f"  ·  {pct(share[0])} of the score" if share else "")
        with st.expander(label, expanded=bool(query)):
            card(t, share)

if not shown:
    st.info("No term matches that search. Try a shorter word, or clear the topic.",
            icon=":material/search_off:")
else:
    st.caption(f"{shown} term{'s' if shown != 1 else ''} shown. Score shares come from the current "
               "settings and add up to 100% across all 19 measures.")

footer()
