import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

import emission_factors as ef
import ui

ui.inject_css()

ui.hero(
    "What does your lifestyle cost the climate — and what's the cheapest way to cut it?",
    "MyCarbon estimates your yearly carbon footprint from how you travel, eat and live, "
    "using Indian data wherever it exists. Then it finds the combination of changes "
    "that saves the most CO₂ for the money you're willing to spend.",
    eyebrow="MyCarbon",
)

c1, c2, _ = st.columns([1.4, 1.2, 3])
if c1.button("Start the calculator", type="primary", icon=":material/arrow_forward:",
             width="stretch"):
    st.switch_page("views/calculator.py")
if c2.button("How it works", icon=":material/insights:", width="stretch"):
    st.switch_page("views/how_it_works.py")

ui.section("Some numbers for context", "Tonnes of CO₂ per person per year.")
ui.tiles([
    ("Typical urban Indian", f"{ef.INDIA_AVERAGES['Total']:.1f} t",
     "two-wheeler commuter, same method as your result", True),
    ("1.5°C lifestyle level, 2030", f"{ef.LIFESTYLE_TARGET_2030.value:g} t",
     "Hot or Cool Institute", False),
    ("India, national average", f"{ef.INDIA_NATIONAL_PER_CAPITA.value:g} t",
     "energy and industry CO₂", False),
    ("World average", f"{ef.WORLD_AVERAGE_PER_CAPITA:g} t", "", False),
])
st.caption("These aren't all measured the same way — the national figure includes "
           "industry and excludes most food emissions, for example. The calculator "
           "compares you with the first one, because it's measured exactly like your result.")

ui.section("What you get")
f1, f2, f3 = st.columns(3, gap="medium")
with f1:
    with st.container(border=True, height="stretch"):
        st.markdown("#### 📊 An honest footprint")
        st.markdown("Seven categories, with every emission factor traced to a source. "
                    "Results come as a **range**, not a falsely precise single number — "
                    "wider where the data is weaker.")
with f2:
    with st.container(border=True, height="stretch"):
        st.markdown("#### 🎯 A plan that fits your budget")
        st.markdown("Set a yearly budget or a target. The planner checks every combination "
                    "of changes and returns the best one — and never counts two changes "
                    "to the same commute twice.")
with f3:
    with st.container(border=True, height="stretch"):
        st.markdown("#### 📄 A report to keep")
        st.markdown("Download a three-page PDF, or copy a link that reopens the calculator "
                    "with your details (never your name) filled in.")

ui.section("How it works, briefly")
ui.steps([
    ("Tell it how you live",
     "Commute, electricity bill, diet, home, water and waste. Shared things like "
     "electricity are split between the people at home."),
    ("See where your emissions come from",
     "Each input is multiplied by a published emission factor — India's own grid "
     "factor for electricity, for example — and compared with a typical urban Indian."),
    ("Get the best plan for your money",
     "Choosing changes under a budget is a classic optimisation problem (the 'knapsack "
     "problem'). MyCarbon solves it exactly with dynamic programming."),
])

ui.section("Findings that surprised me while building it")
s1, s2 = st.columns(2, gap="medium")
with s1:
    with st.container(border=True, height="stretch"):
        st.markdown("**An electric car isn't the big win here.** On India's coal-heavy "
                    "grid it's only about 30% cleaner per km than a petrol car. An "
                    "electric two-wheeler, carpooling, or rooftop solar usually saves "
                    "far more per rupee.")
with s2:
    with st.container(border=True, height="stretch"):
        st.markdown("**Correct code can still give absurd answers.** An early version "
                    "recommended carpooling, the metro, cycling *and* an EV for the "
                    "same commute, and added up all four savings. The algorithm was "
                    "right; the model was wrong.")

ui.footer()
