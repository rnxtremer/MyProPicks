from datetime import date

import streamlit as st

from common import PF_KEYS, PF_LABELS, config, footer, load_review_file, require_unlock, snapshot_file
from mypropicks import remote
from mypropicks.config import save_capital
from mypropicks.review import build_rankings, run_review

require_unlock()
st.title("Settings & review")

cfg = config()

with st.container(border=True):
    st.subheader("Capital per portfolio")
    st.caption("The money you're putting into each portfolio. It's used for suggested quantities and cash.")
    with st.form("capital"):
        cols = st.columns(3)
        vals = {pf: c.number_input(PF_LABELS[pf], min_value=0.0, step=10_000.0,
                                   value=float(cfg["capital"].get(pf) or 0), format="%.0f")
                for c, pf in zip(cols, PF_KEYS)}
        if st.form_submit_button("Save capital", icon=":material/save:"):
            try:
                save_capital(vals)
                st.success("Saved." + (" It's also saved to your private data repo." if remote.enabled() else ""))
            except ValueError as e:
                st.error(str(e))

with st.container(border=True):
    st.subheader("Run the review now")
    if remote.enabled():
        st.caption("In the cloud, the review runs as a GitHub Action: automatically at 08:00 IST on the "
                   "1st of each month, or now with this button. It takes about 40 minutes; the new "
                   "lists appear here once it has finished and the app has reloaded.")
        if st.button("Start the review on GitHub", type="primary", icon=":material/play_arrow:"):
            try:
                remote.trigger_review()
                st.success("Started. Check back in about 40 minutes.", icon=":material/schedule:")
            except ValueError as e:
                st.error(str(e))
    else:
        st.caption("This normally runs by itself on the 1st of each month. The first run takes about 35–40 "
                   "minutes, because it downloads data for about 500 stocks. Later runs reuse cached data.")
        c1, c2 = st.columns([1, 2], vertical_alignment="bottom")
        which = c2.pills("Portfolios", PF_KEYS, selection_mode="multi", default=PF_KEYS,
                         format_func=lambda k: PF_LABELS[k])
        if c1.button("Run review now", type="primary", icon=":material/play_arrow:"):
            bar = st.progress(0.0, text="Starting…")
            order = list(which or PF_KEYS)

            def prog(stage, frac):
                bar.progress(min(frac, 1.0), text=stage)

            out = run_review(as_of=date.today(), portfolios=order, progress=prog)
            load_review_file.clear()
            bar.progress(1.0, text="Done")
            st.success(f"Review written to {out}.")

with st.container(border=True):
    st.subheader("Refresh live ranks")
    st.caption("Re-scores the universes with today's prices, so **Portfolio analysis** can warn about "
               "stocks at risk of removal before the 1st. It doesn't change the lists.")
    if st.button("Refresh live ranks", icon=":material/sync:"):
        bar = st.progress(0.0, text="Starting…")
        for pf in PF_KEYS:
            table, _, _ = build_rankings(pf, cfg, lambda s, f: bar.progress(min(f, 1.0), text=s))
            f = snapshot_file(pf)
            f.parent.mkdir(parents=True, exist_ok=True)
            table.to_csv(f)
            if remote.enabled():
                try:
                    remote.push(f, f"snapshot: live ranks {pf}")
                except ValueError as e:
                    st.warning(str(e))
        bar.progress(1.0, text="Done")
        st.success("Live ranks updated.")

with st.expander("Current settings (config.yaml, plus your capital)"):
    st.json(cfg)

footer()
