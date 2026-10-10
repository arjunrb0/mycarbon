import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

import emission_factors as ef
import site_content
import ui

ui.inject_css()

ui.hero(
    "What does your lifestyle cost the climate — and what's the cheapest way to cut it?",
    "MyCarbon estimates your yearly carbon footprint from how you travel, eat and live, "
    "using Indian data wherever it exists. Then it finds the combination of changes "
    "that saves the most CO₂ for the money you're willing to spend.",
    eyebrow="MyCarbon",
)


def overview():
    st.markdown("#### MyCarbon in three steps")
    ui.steps([
        ("Tell it how you live",
         "Commute, electricity bill, diet, home, water and waste. Takes about two minutes, "
         "or press “Try an example” to skip straight to results."),
        ("See where your emissions come from",
         "Your footprint as a likely range, compared with a typical urban Indian and with "
         "the level needed for the 1.5°C goal."),
        ("Get the best plan for your money",
         "Set a yearly budget or a target, and the planner picks the combination of changes "
         "that cuts the most CO₂."),
    ])
    c1, c2 = st.columns(2)
    if c1.button("Start the calculator", type="primary", icon=":material/arrow_forward:",
                 width="stretch"):
        st.switch_page("views/calculator.py")
    if c2.button("How it works", icon=":material/insights:", width="stretch"):
        st.switch_page("views/how_it_works.py")


video = site_content.video_url()
if video:
    # Video first, beside the steps: someone landing here can watch the 3-minute
    # tour, or skip it and start straight away.
    v, o = st.columns([7, 5], gap="large")
    with v:
        st.video(video)
    with o:
        overview()
else:
    overview()

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

about = site_content.about_markdown()
if about:
    ui.section("About this project")
    a, g = st.columns([7, 4], gap="large")
    with a:
        st.markdown(about)
    with g:
        with st.container(border=True):
            st.markdown("**At a glance**")
            st.markdown(
                "- **Built by** Arjun Reddy Bathula\n"
                "- **Started** January 2025, as my MYP 5 Personal Project\n"
                "- **Built with** Python, Streamlit, Plotly\n"
                "- **Algorithm** dynamic programming (multiple-choice knapsack)\n"
                "- **Data** Central Electricity Authority, DEFRA, peer-reviewed studies\n"
                "- **Tested** 120+ automated tests, checked against brute force"
            )
            st.link_button("View the code on GitHub", "https://github.com/arjunrb0/mycarbon",
                           icon=":material/code:", width="stretch")

ui.footer()
