"""
The calculator page: inputs, live results, the reduction planner, and the report.

Everything renders from the current inputs on every run, so nothing hides
behind a button. The old page gated its results on `if st.button(...)`, which is
only True for the single rerun after a click — moving any slider or opening an
info box afterwards wiped the results. State that must survive reruns and page
changes lives in st.session_state instead.
"""

import os
import sys
from urllib.parse import urlencode

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pandas as pd
import streamlit as st

import charts
import emission_factors as ef
import inputs as I
import insights
import optimizer as opt
import report
import ui

ui.inject_css()

# ── State ────────────────────────────────────────────────────────────────────
# Widget values are copied into `saved` after every run and restored before
# the widgets are drawn. Streamlit discards a widget's state whenever its page
# isn't displayed, so without this a visit to another page would wipe the form.
PLAN_DEFAULTS = {"plan_mode": "budget", "plan_budget": 20_000, "plan_target": 30}
MODES = {"budget": "Spend a set budget", "target": "Reach a target"}


def _wkey(k):
    return f"in_{k}"


if "saved" not in st.session_state:
    saved = {**I.DEFAULTS, **PLAN_DEFAULTS, "name": ""}
    shared = I.from_query_params(st.query_params.to_dict())
    saved.update(shared)
    st.session_state.saved = saved
    st.session_state.from_link = bool(shared)

for k, v in st.session_state.saved.items():
    if _wkey(k) not in st.session_state:
        st.session_state[_wkey(k)] = v


def _apply(values: dict):
    for k, v in values.items():
        st.session_state[_wkey(k)] = v
        st.session_state.saved[k] = v
    st.session_state.pop("pdf", None)


def load_example():
    _apply(I.EXAMPLE_PROFILE)


def reset_all():
    _apply({**I.DEFAULTS, **PLAN_DEFAULTS, "name": ""})
    st.query_params.clear()


# ── Header ───────────────────────────────────────────────────────────────────
ui.hero(
    "Measure your carbon footprint — then find the cheapest way to cut it",
    "Enter a few details about how you live. Results update as you type, and the "
    "planner works out which changes save the most CO₂ for your money.",
    eyebrow="MyCarbon · built for India",
)

b1, b2, _ = st.columns([1.2, 1, 4])
b1.button("✨ Try an example", on_click=load_example, width="stretch", type="primary",
          help="Fills in a typical urban family so you can see every feature at once.")
b2.button("↺ Reset", on_click=reset_all, width="stretch")
if st.session_state.get("from_link"):
    st.info("Loaded the details from a shared link. Edit anything to make it yours.",
            icon="🔗")

left, right = st.columns([5, 7], gap="large")

# ── Inputs ───────────────────────────────────────────────────────────────────
AVG = ef.AVERAGE_INDIAN_PROFILE
with left:
    with st.container(border=True):
        st.markdown("#### Your details")
        c1, c2 = st.columns([3, 2])
        c1.text_input("Name (optional)", key=_wkey("name"), placeholder="For your report",
                      help="Only used to title your PDF. Never included in share links.")
        c2.number_input(
            "People at home", key=_wkey("household_size"), min_value=1, max_value=20, step=1,
            help="Your home's electricity, appliances and floor space are shared, so they're "
                 f"split between everyone living there. Indian average: {AVG['household_size']}.",
        )

        t_travel, t_energy, t_food, t_home, t_water = st.tabs(
            ["🚗 Travel", "⚡ Energy", "🍽️ Food", "🏠 Home", "💧 Water & waste"])
        with t_travel:
            st.selectbox(
                "How do you usually get around?", key=_wkey("fuel_type"),
                options=list(ef.VEHICLE_LABELS), format_func=ef.VEHICLE_LABELS.get,
                help="Two-wheelers emit roughly a third of what a petrol car does per km.",
            )
            st.number_input(
                "Distance per day (km)", key=_wkey("distance"),
                min_value=0.0, max_value=500.0, step=1.0, format="%.0f",
                help=f"Round trip. A typical urban commute is ~{AVG['distance']} km a day.",
                disabled=st.session_state[_wkey("fuel_type")] == "N/A",
            )
            if st.session_state[_wkey("fuel_type")] == "N/A":
                st.caption("Walking, cycling or public transport only — no vehicle emissions "
                           "are counted.")
        with t_energy:
            st.number_input(
                "Home electricity use (kWh per month)", key=_wkey("electricity"),
                min_value=0.0, max_value=5000.0, step=10.0, format="%.0f",
                help="The 'units consumed' on your electricity bill, for the whole home. "
                     f"Average Indian home: {AVG['electricity']} kWh.",
            )
            st.number_input(
                "Major appliances at home", key=_wkey("appliances"),
                min_value=0, max_value=100, step=1,
                help="Fridge, washing machine, AC, TV and so on. This counts the carbon from "
                     "making them — running them is already in your electricity figure.",
            )
        with t_food:
            st.selectbox(
                "Diet", key=_wkey("diet"),
                options=["N/A", "Vegan", "Vegetarian", "Non-Vegetarian"],
                format_func=lambda d: "Choose…" if d == "N/A" else d,
                help="Based on a large study of UK diets — see sources below for why this "
                     "probably overstates the gap for Indian diets.",
            )
            st.number_input(
                "Meals per day", key=_wkey("meals"), min_value=0, max_value=8, step=1,
                help="3 meals is a normal full day of eating.",
            )
        with t_home:
            st.selectbox(
                "Main building material", key=_wkey("house_material"),
                options=["N/A", "Brick", "Wood"],
                format_func=lambda m: "Choose…" if m == "N/A" else m,
                help="The carbon from making the building, spread over a 50-year life.",
            )
            st.number_input(
                "Home size (sq ft)", key=_wkey("house_size"),
                min_value=0.0, max_value=20000.0, step=50.0, format="%.0f",
            )
        with t_water:
            st.number_input(
                "Water use (litres per day, just you)", key=_wkey("water"),
                min_value=0.0, max_value=2000.0, step=5.0, format="%.0f",
                help=f"The Indian urban planning norm is {AVG['water']} litres per person.",
            )
            st.number_input(
                "Waste (kg per week, your share)", key=_wkey("waste"),
                min_value=0.0, max_value=100.0, step=0.5, format="%.1f",
                help=f"About {AVG['waste']} kg a week per person is typical in Indian cities.",
            )

values = {k: st.session_state[_wkey(k)] for k in I.DEFAULTS}
st.session_state.saved.update(values)
st.session_state.saved["name"] = st.session_state[_wkey("name")]
st.query_params.from_dict(I.to_query_params(values))

baseline = ef.compute_baseline_kg(values)
ranges = ef.baseline_range_kg(values)
total = sum(baseline.values())
# "Empty" means nothing produces emissions yet — not "nothing was typed". A
# distance with no vehicle, or a floor area with no material, changes inputs
# but still totals zero, and every percentage below divides by the total.
empty = total <= 0

# ── Results ──────────────────────────────────────────────────────────────────
with right:
    if empty:
        ui.empty_state(
            "Your results will appear here",
            "Fill in the tabs on the left — start with Travel and Energy, they matter "
            "most — or press “Try an example” to see a full result straight away.",
        )
    else:
        lo, _, hi = ranges["Total"]
        typical = ef.INDIA_AVERAGES["Total"]
        biggest = max(baseline, key=baseline.get)
        head, story = insights.verdict(total)
        ui.tiles([
            ("Your footprint", f"{total / 1000:.2f} t",
             f"CO₂e per year · likely {lo / 1000:.1f}–{hi / 1000:.1f} t", True),
            ("vs typical urban Indian", f"{total / 1000 / typical:.0%}",
             f"typical is {typical:.2f} t", False),
            ("1.5°C level for 2030", f"{ef.LIFESTYLE_TARGET_2030.value:g} t",
             "per person, per year", False),
            ("Biggest source", f"{insights.CATEGORY_ICONS[biggest]} {biggest}",
             f"{baseline[biggest] / total:.0%} of your total", False),
        ], columns=2)
        st.markdown(f"**{head}.** {story.split('. ', 1)[1]}")
        st.plotly_chart(charts.breakdown_chart(baseline, ef.INDIA_AVERAGES, ranges),
                        width="stretch", config={"displayModeBar": False})
        st.caption("Whiskers show the likely range, which widens where the underlying "
                   "data is less certain.")

        factors = ef.category_factors(values)
        with st.expander("Table view and data quality"):
            st.dataframe(
                pd.DataFrame([
                    {
                        "Category": f"{insights.CATEGORY_ICONS[c]} {c}",
                        "You (t/yr)": round(baseline[c] / 1000, 2),
                        "Likely range": f"{ranges[c][0] / 1000:.2f} – {ranges[c][2] / 1000:.2f}",
                        "Typical (t/yr)": ef.INDIA_AVERAGES.get(c, 0),
                        "Data quality": (ui.badge_text(factors[c].confidence)
                                         if factors.get(c) and baseline[c] > 0 else "—"),
                        "Source": factors[c].source if factors.get(c) else "",
                    }
                    for c in sorted(baseline, key=lambda c: -baseline[c])
                ]),
                hide_index=True, width="stretch",
                column_config={"Source": st.column_config.TextColumn(width="large")},
            )

        tip_list = insights.tips(baseline)
        if tip_list:
            with st.container(border=True):
                st.markdown("**Where to focus first**")
                for cat, tip in tip_list:
                    st.markdown(f"{insights.CATEGORY_ICONS[cat]} **{cat}** — {tip}")

# ── Reduction planner ────────────────────────────────────────────────────────
plan, plan_label = None, ""
if not empty:
    ui.section(
        "Plan your reduction",
        "Choose a yearly budget or a goal. The planner searches every combination of "
        "changes and picks the best one — never two changes that cut the same emissions.",
    )
    scored = opt.build_actions(baseline, values)

    if not scored:
        st.info("No changes in the catalogue would reduce your footprint further — "
                "you're already doing everything it knows about.")
    else:
        with st.container(border=True):
            mc, sc = st.columns([2, 3], gap="large")
            mode = mc.segmented_control(
                "I want to…", options=list(MODES), format_func=MODES.get,
                key=_wkey("plan_mode"),
            ) or "budget"
            st.session_state.saved["plan_mode"] = mode
            if mode == "budget":
                budget = sc.select_slider(
                    "Yearly budget", options=list(range(0, 150_001, 1_000)),
                    format_func=ui.inr, key=_wkey("plan_budget"))
                st.session_state.saved["plan_budget"] = budget
                plan = opt.solve_dp_grouped(scored, budget)
                plan_label = f"With a budget of {ui.inr(budget)} a year."
            else:
                pct = sc.slider("Cut my footprint by", min_value=5, max_value=90, step=5,
                                key=_wkey("plan_target"), format="%d%%")
                st.session_state.saved["plan_target"] = pct
                plan, max_kg = opt.solve_min_cost_for_target(scored, total * pct / 100)
                if plan is None:
                    st.warning(
                        f"Every change in the catalogue together saves "
                        f"{max_kg / 1000:.2f} t a year ({max_kg / total:.0%}), so a {pct}% "
                        f"cut isn't reachable with these actions alone. Showing the "
                        f"cheapest plan that gets as close as possible.", icon="⚠️")
                    plan, _ = opt.solve_min_cost_for_target(scored, max_kg)
                    plan_label = f"Aiming for the largest achievable cut ({max_kg / total:.0%})."
                else:
                    plan_label = f"The cheapest way to cut your footprint by {pct}%."

        if plan is not None and plan.chosen:
            after = opt.projected_baseline(baseline, plan)
            after_total = sum(after.values())
            cut = total - after_total
            ui.tiles([
                ("Cuts", f"{cut / 1000:.2f} t/yr", f"{cut / total:.0%} of your footprint", True),
                ("Your yearly cost", ui.inr(plan.total_cost),
                 "your share, spread over each item's life", False),
                ("Footprint afterwards", f"{after_total / 1000:.2f} t",
                 "vs 2.5 t 1.5°C level" if after_total > 2500 else "within the 1.5°C level",
                 False),
                ("Changes", str(len(plan.chosen)), f"from {len(scored)} that apply to you",
                 False),
            ])
            pc, cc = st.columns([6, 5], gap="large")
            with pc:
                st.dataframe(
                    pd.DataFrame([
                        {
                            "Change": s.name,
                            "Area": f"{insights.CATEGORY_ICONS[s.category]} {s.category}",
                            "Your cost (₹/yr)": round(s.cost),
                            "Saves (kg/yr)": round(s.saving),
                            "Details": s.detail,
                        }
                        for s in sorted(plan.chosen, key=lambda a: -a.saving)
                    ]),
                    hide_index=True, width="stretch",
                    column_config={
                        "Your cost (₹/yr)": st.column_config.NumberColumn(format="₹%d"),
                        "Saves (kg/yr)": st.column_config.ProgressColumn(
                            format="%d kg", min_value=0,
                            max_value=int(max(s.saving for s in plan.chosen))),
                        "Details": st.column_config.TextColumn(width="medium"),
                    },
                )
                st.caption("Costs are indicative. One-off purchases are spread over their "
                           "useful life; household items are split between the people at home.")
            with cc:
                st.plotly_chart(charts.before_after_chart(baseline, after),
                                width="stretch", config={"displayModeBar": False})
        elif plan is not None:
            st.info("That budget is too small for any change on the list — try raising it.")

        with st.expander("🔬 How good is this plan? Compare the algorithms"):
            max_b = 150_000
            optimal = opt.optimal_frontier(scored, max_b, step=1_000)
            greedy = opt.greedy_frontier(scored, max_b, step=1_000)
            marker = plan.total_cost if (plan and mode == "target") else (
                budget if mode == "budget" else None)
            st.plotly_chart(charts.frontier_chart(optimal, greedy, marker),
                            width="stretch", config={"displayModeBar": False})
            gaps = [(b, o - g) for (b, o), (_, g) in zip(optimal, greedy) if o - g > 1e-6]
            st.markdown(
                "The **blue line** is the best possible saving at each budget, found by "
                "dynamic programming. The **orange line** is the obvious shortcut — keep "
                "picking whichever change saves the most CO₂ per rupee. "
                + (f"For your details the shortcut falls short at **{len(gaps)} of "
                   f"{len(optimal)} budgets**, by up to "
                   f"**{max(g for _, g in gaps):,.0f} kg a year**."
                   if gaps else
                   "For your details the shortcut happens to match the best plan at every "
                   "budget — that isn't true in general.")
            )
            st.markdown(
                "Both lines level off: the first few thousand rupees buy the cheap, "
                "high-impact changes, and each extra rupee after that buys less.")
            st.page_link("views/how_it_works.py", label="How the algorithm works",
                         icon=":material/arrow_forward:")
            st.dataframe(
                pd.DataFrame({
                    "Budget (₹/yr)": [b for b, _ in optimal],
                    "Optimal saving (kg/yr)": [round(o) for _, o in optimal],
                    "Shortcut saving (kg/yr)": [round(g) for _, g in greedy],
                }),
                hide_index=True, width="stretch", height=220,
            )

# ── Report and sharing ───────────────────────────────────────────────────────
if not empty:
    ui.section("Keep and share your results")
    rc, sc = st.columns(2, gap="large")
    name = st.session_state[_wkey("name")]
    signature = (tuple(sorted(values.items())), name, plan_label,
                 tuple(s.name for s in plan.chosen) if plan else ())
    with rc:
        with st.container(border=True):
            st.markdown("**📄 PDF report**")
            st.caption("A 3-page summary with your breakdown, plan and next steps.")
            cached = st.session_state.get("pdf")
            if cached and cached["sig"] == signature:
                st.download_button(
                    "⬇️ Download PDF", data=cached["bytes"], mime="application/pdf",
                    file_name=f"mycarbon_{(name.strip() or 'report').replace(' ', '_')}.pdf",
                    width="stretch", type="primary",
                )
            else:
                if cached:
                    st.caption("Your details changed since the last report.")
                if st.button("Create my report", width="stretch"):
                    with st.spinner("Building your report…"):
                        st.session_state.pdf = {
                            "sig": signature,
                            "bytes": report.build_pdf(name, values, plan, plan_label),
                        }
                    st.rerun()
    with sc:
        with st.container(border=True):
            st.markdown("**🔗 Share link**")
            st.caption("This link reopens the calculator with your details filled in. "
                       "Your name is never included.")
            base = getattr(st.context, "url", None) or "https://mycarbon.streamlit.app/calculator"
            st.code(f"{base.split('?')[0]}?{urlencode(I.to_query_params(values))}",
                    language=None, wrap_lines=True)

# ── Sources ──────────────────────────────────────────────────────────────────
with st.expander("📚 Where these numbers come from"):
    st.caption("Every factor is traceable. **High** means quoted from a primary source, "
               "**Medium** borrowed from another country's data, **Low** worked out by hand "
               "from cited inputs plus a stated assumption.")
    st.dataframe(
        pd.DataFrame([
            {"Factor": label, "Value": f"{f.value:,.4g}", "Unit": f.unit,
             "Data quality": ui.badge_text(f.confidence), "Source": f.source}
            for label, f in ef.ALL_FACTORS.items()
        ]),
        hide_index=True, width="stretch",
        column_config={"Source": st.column_config.TextColumn(width="large")},
    )
    st.markdown("**What “typical urban Indian” means**")
    st.caption(
        f"A documented profile — urban, grid-connected, commuting by two-wheeler — run "
        f"through exactly the same calculation as you. It's deliberately higher than "
        f"India's national per-capita CO₂ of {ef.INDIA_NATIONAL_PER_CAPITA.value} t, "
        f"which includes the many people with no vehicle and little electricity.")
    st.dataframe(
        pd.DataFrame([
            {"Input": k.replace("_", " ").capitalize(), "Typical value": str(v),
             "Basis": ef.AVERAGE_PROFILE_SOURCES.get(k, "Model assumption")}
            for k, v in ef.AVERAGE_INDIAN_PROFILE.items()
        ]),
        hide_index=True, width="stretch",
        column_config={"Basis": st.column_config.TextColumn(width="large")},
    )
    st.markdown("**Limitations**")
    for lim in ef.GENERAL_LIMITATIONS + [ef.DIET_LIMITATION]:
        st.markdown(f"- {lim}")

ui.footer()
