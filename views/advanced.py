import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from io import BytesIO
import os
from tempfile import NamedTemporaryFile
import plotly.graph_objects as go
import sys

# This page lives in views/ but imports modules from the project root.
# `streamlit run app.py` puts the root on sys.path automatically; anything
# else (test harnesses, direct execution) does not. Make it explicit so the
# page is importable and testable regardless of how it is launched.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import optimizer

# ── Emission Factors ────────────────────────────────────────────────────────
# Sourced values, units and confidence levels live in emission_factors.py.
# This dict is now assembled from them rather than hardcoded, so there is a
# single place where every number can be traced to a citation.
import emission_factors as ef

EMISSION_FACTORS = {
    "N/A": 0,
    # kg CO2 per KILOMETRE (previously per litre, applied to km — a ~15x error)
    "Transportation": {k: f.value for k, f in ef.TRANSPORT_PER_KM.items()},
    "Energy": {
        "Electricity": ef.ELECTRICITY.value,        # kg CO2 / kWh
        "Appliances": ef.APPLIANCE_EMBODIED.value,  # kg CO2 / appliance / yr
    },
    # kg CO2e per DAY for a reference ~3-meal diet, not per meal
    "Diet": {k: f.value for k, f in ef.DIET_PER_DAY.items()},
    "Waste": ef.WASTE.value,                        # kg CO2e / kg
    "Water": ef.WATER.value,                        # kg CO2 / litre
    # kg CO2 per sq ft per YEAR, embodied carbon amortised over building life
    "Housing": {k: f.value for k, f in ef.HOUSING_PER_SQFT_YEAR.items()},
}

INDIA_AVERAGES = {
    "Transportation": 0.62,
    "Electricity": 1.97,
    "Diet": 0.82,
    "Waste": 0.06,
    "Water": 0.01,
    "Appliances": 0.01,
    "Housing": 0.15,
    "Total": 3.64,
}

CATEGORY_COLORS = {
    "Transportation": "#4FC3F7",
    "Electricity": "#1565C0",
    "Diet": "#F48FB1",
    "Housing": "#EF5350",
    "Waste": "#66BB6A",
    "Water": "#AB47BC",
    "Appliances": "#FFA726",
}

# ── Page Title ───────────────────────────────────────────────────────────────
st.markdown("""
    <h1 style='color:#2E7D32; margin-bottom:0'>🌿 Personal Carbon Calculator</h1>
    <p style='color:#555; font-size:16px; margin-top:4px'>
        Estimate your annual CO₂ emissions across key lifestyle categories.
    </p>
    <hr style='border:1px solid #c8e6c9; margin-bottom:20px'>
""", unsafe_allow_html=True)

# ── Name Input ───────────────────────────────────────────────────────────────
col_name, _, _, _, _ = st.columns(5)
with col_name:
    name = st.text_input("👤 Your name:", placeholder="e.g. Arjun")

# ── Info Dialogs ─────────────────────────────────────────────────────────────
@st.dialog("Daily Commute Info")
def commute_info():
    st.write("The daily distance you travel, usually to and from work or school.")
    st.write("🇮🇳 India Average: **15 km/day**")

@st.dialog("Fuel Type Info")
def fuel_info():
    st.write("The type of fuel your vehicle uses: Petrol, Diesel, Electric, or Hybrid.")

@st.dialog("Electricity Info")
def electricity_info():
    st.write("Total electricity consumed per month, measured in kilowatt-hours (kWh).")
    st.write("🇮🇳 India Average: **200 kWh/month**")

@st.dialog("Appliances Info")
def appliances_info():
    st.write("Number of major appliances used per year (fans, fridges, washing machines, etc).")
    st.write("🇮🇳 India Average: **10 appliances**")

@st.dialog("Diet Info")
def diet_info():
    st.write("Your dietary preference affects how much CO₂ your food produces.")

@st.dialog("Meals Info")
def meals_info():
    st.write("Average number of meals consumed per day.")
    st.write("🇮🇳 India Average: **3 meals/day**")

@st.dialog("Water Info")
def water_info():
    st.write("Your daily water usage in liters.")
    st.write("🇮🇳 India Average: **135 liters/day**")

@st.dialog("Waste Info")
def waste_info():
    st.write("Amount of waste generated per week in kilograms.")
    st.write("🇮🇳 India Average: **5 kg/week**")

@st.dialog("Housing Material Info")
def housing_info():
    st.write("The primary material your house is built with affects embodied carbon.")

@st.dialog("House Size Info")
def housingsize_info():
    st.write("The total floor area of your home in square feet.")

# ── Inputs ───────────────────────────────────────────────────────────────────
st.markdown("### 📋 Enter Your Details")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown("#### 🚗 Transportation")
    st.caption("Daily commute distance (km)")
    if st.button("ℹ️ Info", key="commute_info_button"):
        commute_info()
    distance = st.number_input("Distance (km)", min_value=0, step=1, key="distance_input", label_visibility="collapsed")

    st.caption("Vehicle fuel type")
    if st.button("ℹ️ Info", key="fuel_info_button"):
        fuel_info()
    fuel_type = st.selectbox("Fuel Type", ["N/A", "Petrol", "Diesel", "Electric", "Hybrid"], key="fuel_type_input", label_visibility="collapsed")

with col2:
    st.markdown("#### ⚡ Energy")
    st.caption("Monthly electricity (kWh)")
    if st.button("ℹ️ Info", key="electricity_info_button"):
        electricity_info()
    electricity = st.number_input("Electricity (kWh)", min_value=0, step=1, key="electricity_input", label_visibility="collapsed")

    st.caption("Appliances used per year")
    if st.button("ℹ️ Info", key="appliances_info_button"):
        appliances_info()
    appliances = st.number_input("Appliances", min_value=0, step=1, key="appliances_input", label_visibility="collapsed")

with col3:
    st.markdown("#### 🍽️ Diet")
    st.caption("Dietary preference")
    if st.button("ℹ️ Info", key="diet_info_button"):
        diet_info()
    diet = st.selectbox("Diet", ["N/A", "Vegetarian", "Non-Vegetarian", "Vegan"], key="diet_input", label_visibility="collapsed")

    st.caption("Meals per day")
    if st.button("ℹ️ Info", key="meals_info_button"):
        meals_info()
    meals = st.number_input("Meals", min_value=0, step=1, key="meals_input", label_visibility="collapsed")

with col4:
    st.markdown("#### 🏠 Housing")
    st.caption("House material")
    if st.button("ℹ️ Info", key="housing_info_button"):
        housing_info()
    house_material = st.selectbox("Material", ["N/A", "Brick", "Wood"], key="house_material_input", label_visibility="collapsed")

    st.caption("House size (sq ft)")
    if st.button("ℹ️ Info", key="housingsize_info_button"):
        housingsize_info()
    house_size = st.number_input("House Size", min_value=0, step=100, key="house_size_input", label_visibility="collapsed")

with col5:
    st.markdown("#### 💧 Utility")
    st.caption("Daily water usage (liters)")
    if st.button("ℹ️ Info", key="water_info_button"):
        water_info()
    water = st.number_input("Water (liters)", min_value=0, step=10, key="water_input", label_visibility="collapsed")

    st.caption("Waste per week (kg)")
    if st.button("ℹ️ Info", key="waste_info_button"):
        waste_info()
    waste = st.number_input("Waste (kg)", min_value=0, step=1, key="waste_input", label_visibility="collapsed")

# ── Calculations ─────────────────────────────────────────────────────────────
distance_yr  = distance * 365
electricity_yr = electricity * 12
waste_yr     = waste * 52
water_yr     = water * 365

transportation_emissions = 0 if fuel_type == "N/A" else EMISSION_FACTORS["Transportation"][fuel_type] * distance_yr
electricity_emissions    = EMISSION_FACTORS["Energy"]["Electricity"] * electricity_yr
# The diet factor is per DAY for a reference ~3-meal (2,000 kcal) diet, so
# meals scales it rather than multiplying it. The old code multiplied a
# per-meal-shaped number by meals AND by 365, which inflated diet emissions
# roughly threefold.
diet_emissions           = (
    0 if diet == "N/A"
    else EMISSION_FACTORS["Diet"][diet] * (meals / ef.DIET_REFERENCE_MEALS) * 365
)
waste_emissions          = EMISSION_FACTORS["Waste"] * waste_yr
water_emissions          = EMISSION_FACTORS["Water"] * water_yr
appliances_emissions     = EMISSION_FACTORS["Energy"]["Appliances"] * appliances
housing_emissions        = 0 if house_material == "N/A" else EMISSION_FACTORS["Housing"][house_material] * house_size

# Keep the unrounded kg/yr values — the optimizer works in kg and rounding
# to tonnes here would throw away the precision it needs.
BASELINE_KG = {
    "Transportation": transportation_emissions,
    "Electricity":    electricity_emissions,
    "Diet":           diet_emissions,
    "Waste":          waste_emissions,
    "Water":          water_emissions,
    "Appliances":     appliances_emissions,
    "Housing":        housing_emissions,
}

USER_INPUTS = {
    "distance": distance,
    "fuel_type": fuel_type,
    "electricity": electricity,
    "appliances": appliances,
    "diet": diet,
    "meals": meals,
    "house_material": house_material,
    "house_size": house_size,
    "water": water,
    "waste": waste,
}

def to_tonnes(e):
    return round(e / 1000, 2)

transportation_emissions = to_tonnes(transportation_emissions)
electricity_emissions    = to_tonnes(electricity_emissions)
diet_emissions           = to_tonnes(diet_emissions)
waste_emissions          = to_tonnes(waste_emissions)
water_emissions          = to_tonnes(water_emissions)
appliances_emissions     = to_tonnes(appliances_emissions)
housing_emissions        = to_tonnes(housing_emissions)

total_emissions = round(
    transportation_emissions + electricity_emissions + diet_emissions +
    waste_emissions + water_emissions + appliances_emissions + housing_emissions, 2
)

df = pd.DataFrame({
    "Category": ["Transportation", "Electricity", "Diet", "Waste", "Water", "Appliances", "Housing", "Total"],
    "Your Emissions (t CO₂/yr)": [
        transportation_emissions, electricity_emissions, diet_emissions,
        waste_emissions, water_emissions, appliances_emissions, housing_emissions, total_emissions
    ],
    "India Average (t CO₂/yr)": [
        INDIA_AVERAGES["Transportation"], INDIA_AVERAGES["Electricity"], INDIA_AVERAGES["Diet"],
        INDIA_AVERAGES["Waste"], INDIA_AVERAGES["Water"], INDIA_AVERAGES["Appliances"],
        INDIA_AVERAGES["Housing"], INDIA_AVERAGES["Total"]
    ]
})

# ── Chart helpers (matplotlib only — no kaleido) ──────────────────────────────
def make_pie_image(df):
    df_c = df[df["Category"] != "Total"]  # ✅ FIX HERE

    values = df_c["Your Emissions (t CO₂/yr)"].fillna(0)
    colors = [CATEGORY_COLORS.get(c, "#999") for c in df_c["Category"]]

    fig, ax = plt.subplots(figsize=(6, 5))

    if values.sum() == 0:
        ax.text(0.5, 0.5, "No data to display", ha='center', va='center')
        texts = []
    else:
        wedges, texts, autotexts = ax.pie(
            values,
            labels=df_c["Category"],
            autopct=lambda p: f'{p:.1f}%' if p > 2 else '',
            colors=colors,
            startangle=140,
            wedgeprops={"edgecolor": "white", "linewidth": 1.5}
        )

    for t in texts:
        t.set_fontsize(9)

    ax.set_title("Carbon Emissions by Category", fontsize=13, fontweight="bold", pad=15)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf

def make_gauge_image(value):
    fig, ax = plt.subplots(figsize=(6, 3.5), subplot_kw={"projection": "polar"})
    ax.set_theta_offset(np.pi)
    ax.set_theta_direction(-1)
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    ax.set_ylim(0, 1)

    # Colored arcs
    for start, end, color in [(0, 60, "#66BB6A"), (60, 120, "#FFA726"), (120, 180, "#EF5350")]:
        theta = np.linspace(np.radians(start), np.radians(end), 100)
        ax.fill_between(theta, 0.6, 0.9, color=color, alpha=0.85)

    # Needle
    max_val = 30
    angle = np.radians(min(value / max_val * 180, 180))
    ax.annotate("", xy=(angle, 0.85), xytext=(angle, 0),
                arrowprops=dict(arrowstyle="->", color="#1A237E", lw=2.5))

    ax.set_yticklabels([])
    ax.set_xticklabels([])
    ax.spines["polar"].set_visible(False)
    ax.grid(False)

    label = "Low" if value <= 5 else "Moderate" if value <= 15 else "High"
    ax.set_title(f"Total: {value} t CO₂/yr  —  {label}", fontsize=12, fontweight="bold", pad=20)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf

def make_bar_comparison_image(df):
    df_c = df[df["Category"] != "Total"]
    categories = df_c["Category"].tolist()
    your_vals  = df_c["Your Emissions (t CO₂/yr)"].tolist()
    avg_vals   = df_c["India Average (t CO₂/yr)"].tolist()
    x = np.arange(len(categories))
    width = 0.35

    fig, ax = plt.subplots(figsize=(9, 4))
    bars1 = ax.bar(x - width/2, your_vals, width, label="Your Emissions", color="#2E7D32", alpha=0.85)
    bars2 = ax.bar(x + width/2, avg_vals,  width, label="India Average",  color="#A5D6A7", alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("tonnes CO₂/year", fontsize=10)
    ax.set_title("Your Emissions vs India Average", fontsize=13, fontweight="bold")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)

    for bar in bars1:
        if bar.get_height() > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f'{bar.get_height():.2f}', ha='center', va='bottom', fontsize=7)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf

def make_before_after_image(baseline_kg, plan):
    """Grouped bar: current emissions vs emissions after the plan, per category.

    Only categories the plan actually touches are drawn — showing seven bars
    where four are identical wastes the reader's attention on the ones that
    did not move.
    """
    after_kg = optimizer.projected_baseline(baseline_kg, plan)
    saved = optimizer.category_savings(plan)

    cats = [c for c in baseline_kg if saved.get(c, 0) > 0]
    cats.sort(key=lambda c: -baseline_kg[c])

    fig, ax = plt.subplots(figsize=(9, 4))

    if not cats:
        ax.text(0.5, 0.5, "No reduction actions selected", ha="center", va="center")
        ax.axis("off")
    else:
        before_vals = [baseline_kg[c] / 1000 for c in cats]
        after_vals  = [after_kg[c] / 1000 for c in cats]
        x = np.arange(len(cats))
        width = 0.35

        b1 = ax.bar(x - width/2, before_vals, width, label="Before", color="#EF5350", alpha=0.85)
        b2 = ax.bar(x + width/2, after_vals,  width, label="After plan", color="#2E7D32", alpha=0.85)

        ax.set_xticks(x)
        ax.set_xticklabels(cats, rotation=20, ha="right", fontsize=9)
        ax.set_ylabel("tonnes CO2/year", fontsize=10)
        ax.set_title("Emissions Before vs After Your Reduction Plan",
                     fontsize=13, fontweight="bold")
        ax.legend()
        ax.spines[["top", "right"]].set_visible(False)

        for bars in (b1, b2):
            for bar in bars:
                if bar.get_height() > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                            f"{bar.get_height():.2f}", ha="center", va="bottom", fontsize=7)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf


def make_table_image(df):
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.axis("tight")
    ax.axis("off")
    table_data = []
    for _, row in df.iterrows():
        your_val = row["Your Emissions (t CO₂/yr)"]
        avg_val  = row["India Average (t CO₂/yr)"]
        diff     = round(your_val - avg_val, 2)
        flag     = "OK" if diff <= 0 else "UP"
        table_data.append([row["Category"], f"{your_val:.2f}", f"{avg_val:.2f}", f"{diff:+.2f} {flag}"])

    t = ax.table(
        cellText=table_data,
        colLabels=["Category", "Yours (t CO₂)", "India Avg", "Difference"],
        cellLoc="center", loc="center"
    )
    t.auto_set_font_size(False)
    t.set_fontsize(9)
    t.auto_set_column_width([0, 1, 2, 3])

    # Colour header row
    for j in range(4):
        t[0, j].set_facecolor("#2E7D32")
        t[0, j].set_text_props(color="white", fontweight="bold")

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)

    return buf

# ── Dynamic text & tips ───────────────────────────────────────────────────────
def get_summary(total):
    if total <= 5:
        return "Low Impact", "Your carbon footprint is well below the India average. Keep up your eco-friendly habits!"
    elif total <= 15:
        return "Moderate Impact", "Your footprint is around the India average. There is room for improvement in a few areas."
    else:
        return "High Impact", "Your footprint is significantly above average. Targeted changes can make a big difference."

def get_tips(transportation_emissions, electricity_emissions, diet_emissions,
             waste_emissions, water_emissions, appliances_emissions, housing_emissions):
    tips = []
    vals = {
        "Transportation": transportation_emissions,
        "Electricity":    electricity_emissions,
        "Diet":           diet_emissions,
        "Waste":          waste_emissions,
        "Water":          water_emissions,
        "Appliances":     appliances_emissions,
        "Housing":        housing_emissions,
    }
    tip_map = {
        "Transportation": "Consider switching to public transport, carpooling, cycling, or an EV to cut travel emissions.",
        "Electricity":    "Switch to LED bulbs, use solar panels if possible, and unplug devices when not in use.",
        "Diet":           "Reducing meat intake and choosing local, seasonal produce can significantly cut food emissions.",
        "Waste":          "Composting organic waste, recycling, and reducing single-use plastics lowers landfill emissions.",
        "Water":          "Fix leaking taps, use water-efficient appliances, and take shorter showers.",
        "Appliances":     "Choose 5-star rated appliances and replace old devices with energy-efficient models.",
        "Housing":        "Improve insulation, use energy-efficient windows, and consider green building materials.",
    }
    sorted_cats = sorted(vals, key=vals.get, reverse=True)
    for cat in sorted_cats[:4]:
        if vals[cat] > INDIA_AVERAGES[cat]:
            tips.append(f"**{cat}:** {tip_map[cat]}")
    if not tips:
        tips.append("Great work! Your emissions are below average in all categories. Consider going carbon-neutral next.")
    return tips

# ── Plotly charts for on-screen display ──────────────────────────────────────
pie_fig = px.pie(
    df[df["Category"] != "Total"],
    names="Category",
    values="Your Emissions (t CO₂/yr)",
    title="Emissions Distribution",
    color="Category",
    color_discrete_map=CATEGORY_COLORS,
    hole=0.3,
)
pie_fig.update_traces(textposition="inside", textinfo="percent+label")
pie_fig.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))

dial_fig = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=total_emissions,
    delta={"reference": INDIA_AVERAGES["Total"], "valueformat": ".2f"},
    title={"text": "Total CO₂ (tonnes/yr)<br><span style='font-size:12px'>vs India avg 3.64 t</span>"},
    gauge={
        "axis": {"range": [0, 30]},
        "bar": {"color": "#1B5E20"},
        "steps": [
            {"range": [0, 5],  "color": "#C8E6C9"},
            {"range": [5, 15], "color": "#FFF9C4"},
            {"range": [15, 30],"color": "#FFCDD2"},
        ],
        "threshold": {"line": {"color": "red", "width": 3}, "thickness": 0.75, "value": INDIA_AVERAGES["Total"]},
    },
))
dial_fig.update_layout(margin=dict(t=60, b=0, l=20, r=20))

# ── PDF Generator ─────────────────────────────────────────────────────────────
def generate_pdf(name, df, total_emissions, transportation_emissions, electricity_emissions,
                 diet_emissions, waste_emissions, water_emissions, appliances_emissions,
                 housing_emissions, fuel_type, diet, house_material,
                 plan=None, budget=0):

    label, summary = get_summary(total_emissions)
    tips = get_tips(transportation_emissions, electricity_emissions, diet_emissions,
                    waste_emissions, water_emissions, appliances_emissions, housing_emissions)

    pie_buf  = make_pie_image(df)
    gauge_buf = make_gauge_image(total_emissions)
    bar_buf  = make_bar_comparison_image(df)
    table_buf = make_table_image(df)

    def buf_to_tmp(buf):
        tmp = NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(buf.read())
        tmp.close()
        return tmp.name
    
    def clean(text):
        return (text
            .replace("—", "-")
            .replace("–", "-")
            .replace("\u2019", "'")
            .replace("\u2018", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("•", "-")
            .replace("…", "...")
            .replace("✓", "+")
            .replace("⚠", "!")
    )

    pie_path   = buf_to_tmp(pie_buf)
    gauge_path = buf_to_tmp(gauge_buf)
    bar_path   = buf_to_tmp(bar_buf)
    table_path = buf_to_tmp(table_buf)

    has_plan = plan is not None and len(plan.chosen) > 0
    ba_path = buf_to_tmp(make_before_after_image(BASELINE_KG, plan)) if has_plan else None
    tmp_paths = [pie_path, gauge_path, bar_path, table_path]
    if ba_path:
        tmp_paths.append(ba_path)

    class PDF(FPDF):
        def header(self):
            self.set_fill_color(46, 125, 50)
            self.rect(0, 0, 210, 28, "F")
            self.set_font("Arial", "B", 18)
            self.set_text_color(255, 255, 255)
            self.set_y(6)
            display_name = name.strip()
            title = (f"{display_name}'s Carbon Emission Report" if display_name
                     else "Your Carbon Emission Report")   # not "Your's"
            self.cell(0, 8, title, ln=True, align="C")
            self.set_font("Arial", "I", 10)
            self.cell(0, 6, f"Generated on {datetime.now().strftime('%d %B %Y, %H:%M')}", ln=True, align="C")
            self.set_text_color(0, 0, 0)
            self.ln(4)

        def footer(self):
            self.set_y(-12)
            self.set_font("Arial", "I", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 6, f"MyCarbon  |  mycarbon.streamlit.app  |  Page {self.page_no()}", align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # ── Page 1: Overview ─────────────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(4)

    # Summary box
    pdf.set_fill_color(232, 245, 233)
    pdf.set_draw_color(46, 125, 50)
    pdf.set_line_width(0.5)
    pdf.rect(10, pdf.get_y(), 190, 24, "FD")
    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(27, 94, 32)
    pdf.set_x(12)
    pdf.cell(0, 8, f"Overall Impact: {label}", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(40, 40, 40)
    pdf.set_x(12)
    pdf.multi_cell(186, 6, summary)
    pdf.ln(4)

    # Input summary
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(46, 125, 50)
    pdf.cell(0, 7, "Input Summary", ln=True)
    pdf.set_draw_color(200, 230, 201)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    inputs = [
        ("Fuel Type",       fuel_type if fuel_type != "N/A" else "Not specified"),
        ("Daily Commute",   f"{distance} km/day"),
        ("Electricity",     f"{electricity} kWh/month"),
        ("Appliances",      f"{appliances} units/year"),
        ("Diet",            diet if diet != "N/A" else "Not specified"),
        ("Meals",           f"{meals}/day"),
        ("House Material",  house_material if house_material != "N/A" else "Not specified"),
        ("House Size",      f"{house_size} sq ft"),
        ("Water Usage",     f"{water} liters/day"),
        ("Waste Generated", f"{waste} kg/week"),
    ]
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(40, 40, 40)
    col_w = 93
    for i, (label_t, val) in enumerate(inputs):
        if i % 2 == 0:
            pdf.set_x(10)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(38, 6, label_t + ":", border=0)
        pdf.set_font("Arial", "", 9)
        pdf.cell(col_w - 38, 6, val, border=0, ln=(1 if i % 2 == 1 else 0))
    pdf.ln(4)

    # Charts row
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(46, 125, 50)
    pdf.cell(0, 7, "Visual Overview", ln=True)
    pdf.set_draw_color(200, 230, 201)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    chart_y = pdf.get_y()
    pdf.image(pie_path,   x=10,  y=chart_y, w=90)
    pdf.image(gauge_path, x=108, y=chart_y, w=92)
    pdf.ln(72)

    # ── Page 2: Detailed Breakdown ────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(4)

    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(46, 125, 50)
    pdf.cell(0, 8, "Detailed Emissions Breakdown", ln=True)
    pdf.set_draw_color(200, 230, 201)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.image(table_path, x=10, w=190)
    pdf.ln(4)
    pdf.image(bar_path,   x=10, w=190)
    pdf.ln(4)

    # Per-category detail
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(46, 125, 50)
    pdf.cell(0, 7, "Category Analysis", ln=True)
    pdf.set_draw_color(200, 230, 201)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    cats = [
        ("Transportation", transportation_emissions, "Petrol/Diesel engines emit CO2 per litre burned. EVs emit via grid power."),
        ("Electricity",    electricity_emissions,    f"India's grid is coal-heavy at {ef.ELECTRICITY.value} kg CO2 per kWh (CEA, FY 2024-25)."),
        ("Diet",           diet_emissions,           "Non-veg diets have up to 3.5x the footprint of vegan diets."),
        ("Waste",          waste_emissions,           "Landfill waste produces methane, a potent greenhouse gas."),
        ("Water",          water_emissions,           "Water treatment and heating contribute to household emissions."),
        ("Appliances",     appliances_emissions,      "More appliances mean more standby and active power consumption."),
        ("Housing",        housing_emissions,         "Building materials have embodied carbon from manufacture & transport."),
    ]

    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(40, 40, 40)
    for cat, val, note in cats:
        avg = INDIA_AVERAGES[cat]
        diff = round(val - avg, 2)
        status = "Below average" if diff <= 0 else f"Above average by {diff:.2f} t"
        color = CATEGORY_COLORS.get(cat, "#999999")
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        pdf.set_fill_color(r, g, b)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 6, f"  {cat}", fill=True, ln=True)
        pdf.set_text_color(40, 40, 40)
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 5, f"   Your emissions: {val:.2f} t CO2/yr  |  India avg: {avg:.2f} t  |  {status}", ln=True)
        pdf.set_font("Arial", "I", 8)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 5, f"   {note}")
        pdf.ln(1)

    # ── Page 3: Recommendations ───────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(4)

    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(46, 125, 50)
    pdf.cell(0, 8, "Personalised Recommendations", ln=True)
    pdf.set_draw_color(200, 230, 201)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 6, "Based on your inputs, here are the highest-impact changes you can make to reduce your carbon footprint:")
    pdf.ln(3)

    all_tips = {
        "Transportation": [
            "Switch to public transport or carpooling for daily commutes.",
            "Consider purchasing an electric or hybrid vehicle.",
            "For short trips under 3 km, walk or cycle instead.",
        ],
        "Electricity": [
            "Replace all bulbs with LED lighting (uses 75% less energy).",
            "Install rooftop solar panels — eligible for government subsidies in India.",
            "Use a smart power strip to eliminate standby power drain.",
        ],
        "Diet": [
            "Try at least 2 meat-free days per week to cut food emissions.",
            "Buy local and seasonal produce to reduce transport emissions.",
            "Reduce food waste by planning meals and composting scraps.",
        ],
        "Waste": [
            "Separate wet and dry waste and use a compost bin for organic matter.",
            "Avoid single-use plastics — carry a reusable bag and bottle.",
            "Donate or sell old items instead of discarding them.",
        ],
        "Water": [
            "Fix leaking taps — a dripping tap wastes 15 liters/day.",
            "Install a low-flow showerhead to cut water use by 40%.",
            "Collect rainwater for garden and cleaning use.",
        ],
        "Appliances": [
            "Replace old appliances with 5-star BEE-rated models.",
            "Unplug chargers and devices when not in use.",
            "Use a ceiling fan instead of AC when possible.",
        ],
        "Housing": [
            "Add wall insulation or double-glazed windows to reduce cooling load.",
            "Paint walls white or light colours to reflect heat.",
            "Use sustainable materials for any future renovations.",
        ],
    }

    vals_dict = {
        "Transportation": transportation_emissions,
        "Electricity":    electricity_emissions,
        "Diet":           diet_emissions,
        "Waste":          waste_emissions,
        "Water":          water_emissions,
        "Appliances":     appliances_emissions,
        "Housing":        housing_emissions,
    }
    sorted_cats = sorted(vals_dict, key=vals_dict.get, reverse=True)

    for cat in sorted_cats:
        val = vals_dict[cat]
        avg = INDIA_AVERAGES[cat]
        color = CATEGORY_COLORS.get(cat, "#999999")
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        pdf.set_fill_color(r, g, b)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(255, 255, 255)
        above = val > avg
        tag = "  ! Priority" if above else "  + On Track"
        pdf.cell(0, 6, f"  {cat}{tag}", fill=True, ln=True)
        pdf.set_text_color(40, 40, 40)
        pdf.set_font("Arial", "", 9)
        for tip in all_tips[cat]:
            pdf.set_x(10)
            pdf.multi_cell(190, 5, clean(f"- {tip}"))
    pdf.ln(1)

    # Final note
    pdf.ln(4)
    pdf.set_fill_color(232, 245, 233)
    pdf.set_draw_color(46, 125, 50)
    pdf.rect(10, pdf.get_y(), 190, 20, "FD")
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(27, 94, 32)
    pdf.set_x(12)
    pdf.cell(0, 7, "Your Carbon Snapshot", ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(40, 40, 40)
    pdf.set_x(12)
    world_avg = 4.7
    india_avg = INDIA_AVERAGES["Total"]
    pdf.multi_cell(186, 5,
        f"Total: {total_emissions:.2f} t CO2/yr  |  India avg: {india_avg} t  |  World avg: {world_avg} t  "
        f"|  {'Below' if total_emissions < india_avg else 'Above'} India average by {abs(round(total_emissions - india_avg, 2))} t"
    )

    # ── Page 4: Optimised Reduction Plan ──────────────────────────────────────
    if has_plan:
        after_kg = optimizer.projected_baseline(BASELINE_KG, plan)
        base_total = sum(BASELINE_KG.values())
        after_total = sum(after_kg.values())
        pct = (base_total - after_total) / base_total * 100 if base_total else 0

        pdf.add_page()
        pdf.ln(4)

        pdf.set_font("Arial", "B", 13)
        pdf.set_text_color(46, 125, 50)
        pdf.cell(0, 8, "Your Optimised Reduction Plan", ln=True)
        pdf.set_draw_color(200, 230, 201)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 6, clean(
            f"Given an annual budget of Rs {budget:,.0f}, these actions cut the most CO2. "
            f"The selection is computed by dynamic programming - it evaluates combinations "
            f"of actions rather than ranking them individually, and treats overlapping "
            f"actions (such as different ways of changing the same commute) as "
            f"alternatives so their savings are never counted twice."
        ))
        pdf.ln(3)

        # Headline numbers
        pdf.set_fill_color(232, 245, 233)
        pdf.set_draw_color(46, 125, 50)
        pdf.set_line_width(0.5)
        box_y = pdf.get_y()
        pdf.rect(10, box_y, 190, 20, "FD")
        pdf.set_xy(12, box_y + 3)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(27, 94, 32)
        pdf.cell(0, 6, "Plan Summary", ln=True)
        pdf.set_x(12)
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(186, 5, clean(
            f"Before: {base_total/1000:.2f} t CO2/yr   |   "
            f"After: {after_total/1000:.2f} t CO2/yr   |   "
            f"Saved: {(base_total - after_total)/1000:.2f} t ({pct:.1f}%)   |   "
            f"Cost: Rs {plan.total_cost:,.0f} of Rs {budget:,.0f}"
        ))
        pdf.ln(6)

        # Chosen actions
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(46, 125, 50)
        pdf.cell(0, 7, "Recommended Actions", ln=True)
        pdf.set_draw_color(200, 230, 201)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2)

        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(46, 125, 50)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(88, 7, "  Action", border=0, fill=True)
        pdf.cell(34, 7, "Category", border=0, fill=True, align="C")
        pdf.cell(34, 7, "Cost (Rs/yr)", border=0, fill=True, align="C")
        pdf.cell(34, 7, "Saves (kg/yr)", border=0, fill=True, align="C", ln=True)

        pdf.set_text_color(40, 40, 40)
        for i, s in enumerate(sorted(plan.chosen, key=lambda a: -a.saving)):
            pdf.set_fill_color(*((245, 250, 245) if i % 2 == 0 else (255, 255, 255)))
            pdf.set_font("Arial", "", 9)
            pdf.cell(88, 6, clean(f"  {s.name}"), border=0, fill=True)
            pdf.cell(34, 6, s.category, border=0, fill=True, align="C")
            pdf.cell(34, 6, f"{s.cost:,.0f}", border=0, fill=True, align="C")
            pdf.cell(34, 6, f"{s.saving:,.0f}", border=0, fill=True, align="C", ln=True)

        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(232, 245, 233)
        pdf.cell(88, 7, "  TOTAL", border=0, fill=True)
        pdf.cell(34, 7, "", border=0, fill=True)
        pdf.cell(34, 7, f"{plan.total_cost:,.0f}", border=0, fill=True, align="C")
        pdf.cell(34, 7, f"{plan.total_saving:,.0f}", border=0, fill=True, align="C", ln=True)
        pdf.ln(5)

        pdf.image(ba_path, x=10, w=190)
        pdf.ln(3)

        pdf.set_font("Arial", "I", 8)
        pdf.set_text_color(110, 110, 110)
        pdf.multi_cell(0, 4, clean(
            "How to read this: costs are annualised, so a one-time purchase is spread "
            "over its useful life. Savings are estimated against your current emissions "
            "using published emission factors, and assume each action is carried out in "
            "full. Actions that reduce the same source of emissions are treated as "
            "alternatives, so at most one of each such group is recommended."
        ))

    # Cleanup
    for p in tmp_paths:
        try:
            os.unlink(p)
        except Exception:
            pass

    return bytes(bytearray(pdf.output()))



# ── Buttons ───────────────────────────────────────────────────────────────────
st.markdown("<hr style='border:1px solid #c8e6c9'>", unsafe_allow_html=True)
btn1, btn2, btn3 = st.columns([1, 1, 1])

with btn1:
    calculate_button = st.button("🌿 Calculate Emissions", use_container_width=True)
with btn2:
    generate_report_button = st.button("📄 Generate PDF Report", use_container_width=True)

# ── Results Display ───────────────────────────────────────────────────────────
if calculate_button:
    st.markdown("<hr style='border:1px solid #c8e6c9'>", unsafe_allow_html=True)
    st.markdown("### 📊 Your Results")

    # Metric cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🚗 Transport",   f"{transportation_emissions} t", f"{round(transportation_emissions - INDIA_AVERAGES['Transportation'], 2):+.2f} vs avg")
    m2.metric("⚡ Electricity", f"{electricity_emissions} t",    f"{round(electricity_emissions - INDIA_AVERAGES['Electricity'], 2):+.2f} vs avg")
    m3.metric("🍽️ Diet",        f"{diet_emissions} t",           f"{round(diet_emissions - INDIA_AVERAGES['Diet'], 2):+.2f} vs avg")
    m4.metric("🏠 Housing",     f"{housing_emissions} t",        f"{round(housing_emissions - INDIA_AVERAGES['Housing'], 2):+.2f} vs avg")

    st.markdown("")

    c1, c2, c3 = st.columns([1.1, 1.2, 1])
    with c1:
        st.subheader("📋 Breakdown")
        st.dataframe(df, use_container_width=True, hide_index=True)


    with c2:
        st.subheader("🥧 Distribution")
        st.plotly_chart(pie_fig, width='stretch')
    with c3:
        st.subheader("🎯 Total Gauge")
        st.plotly_chart(dial_fig, use_container_width=True)

    label, summary = get_summary(total_emissions)
    color = "#E8F5E9" if total_emissions <= 5 else "#FFFDE7" if total_emissions <= 15 else "#FFEBEE"
    st.markdown(f"""
        <div style='background:{color}; padding:16px; border-radius:10px; margin-top:12px'>
            <b style='font-size:16px'>{label}</b><br>{summary}
        </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 💡 Top Tips for You")
    tips = get_tips(transportation_emissions, electricity_emissions, diet_emissions,
                    waste_emissions, water_emissions, appliances_emissions, housing_emissions)
    for tip in tips:
        st.markdown(f"- {tip}")

# ── Reduction Optimizer ───────────────────────────────────────────────────────
st.markdown("<hr style='border:1px solid #c8e6c9'>", unsafe_allow_html=True)
st.markdown("### 🎯 Reduction Plan Optimizer")
st.caption(
    "Given a yearly budget, which combination of changes cuts the most CO₂? "
    "This is a 0/1 knapsack problem — cost is the weight, CO₂ saved is the value."
)

opt_col1, opt_col2 = st.columns([2, 1])
with opt_col1:
    budget = st.slider(
        "Annual budget (₹)", min_value=1_000, max_value=150_000,
        value=30_000, step=1_000, key="budget_input",
    )
with opt_col2:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    optimize_button = st.button("⚙️ Build my plan", use_container_width=True)

if optimize_button:
    scored = optimizer.build_actions(BASELINE_KG, USER_INPUTS)

    if not scored:
        st.warning(
            "No applicable actions — enter your details above first. "
            "Actions only appear where they would actually reduce your emissions."
        )
    else:
        solutions = {
            "Greedy": optimizer.solve_greedy(scored, budget),
            "DP (exact)": optimizer.solve_dp(scored, budget),
            "DP + groups": optimizer.solve_dp_grouped(scored, budget),
        }

        st.markdown("**How the three solvers compare at this budget**")
        cmp1, cmp2, cmp3 = st.columns(3)
        greedy_saving = solutions["Greedy"].total_saving
        for col, (label, sol) in zip((cmp1, cmp2, cmp3), solutions.items()):
            delta = None
            if label != "Greedy" and greedy_saving > 0:
                pct = (sol.total_saving - greedy_saving) / greedy_saving * 100
                delta = f"{pct:+.1f}% vs greedy"
            col.metric(label, f"{sol.total_saving/1000:.2f} t/yr", delta,
                       delta_color="off" if label == "DP + groups" else "normal")

        st.caption(
            "Greedy and DP (exact) optimise the same objective, so any gap between them "
            "is pure algorithmic loss. **DP + groups optimises a different, more honest "
            "objective** — its lower number is a corrected estimate, not a worse plan."
        )

        choice = st.radio(
            "Show plan from:", list(solutions.keys()),
            index=2, horizontal=True, key="solver_choice",
        )
        result = solutions[choice]

        r1, r2, r3 = st.columns(3)
        r1.metric("CO₂ saved", f"{result.total_saving/1000:.2f} t/yr")
        r2.metric("Spent", f"₹{result.total_cost:,.0f}", f"₹{result.leftover:,.0f} unspent")
        r3.metric("Actions chosen", f"{len(result.chosen)} of {len(scored)}")

        st.markdown(f"**Recommended plan — {result.method}**")
        st.dataframe(
            pd.DataFrame([
                {
                    "Action": s.name,
                    "Category": s.category,
                    "Cost (₹/yr)": round(s.cost),
                    "Saves (kg CO₂/yr)": round(s.saving, 1),
                    "kg per ₹": round(s.density, 4),
                }
                for s in result.chosen
            ]),
            use_container_width=True, hide_index=True,
        )

        # ── Before / after ────────────────────────────────────────────
        after_kg = optimizer.projected_baseline(BASELINE_KG, result)
        saved_by_cat = optimizer.category_savings(result)
        touched = sorted(
            [c for c in BASELINE_KG if saved_by_cat.get(c, 0) > 0],
            key=lambda c: -BASELINE_KG[c],
        )

        if touched:
            st.markdown("**Before vs after, by category**")
            ba_df = pd.DataFrame({
                "Category": touched * 2,
                "Emissions (t CO₂/yr)": (
                    [BASELINE_KG[c] / 1000 for c in touched]
                    + [after_kg[c] / 1000 for c in touched]
                ),
                "Scenario": ["Before"] * len(touched) + ["After plan"] * len(touched),
            })
            ba_fig = px.bar(
                ba_df, x="Category", y="Emissions (t CO₂/yr)",
                color="Scenario", barmode="group",
                color_discrete_map={"Before": "#EF5350", "After plan": "#2E7D32"},
                title="Emissions before vs after your reduction plan",
            )
            ba_fig.update_layout(margin=dict(t=50, b=0, l=0, r=0), height=380)
            st.plotly_chart(ba_fig, use_container_width=True)

            base_total = sum(BASELINE_KG.values())
            after_total = sum(after_kg.values())
            t1, t2, t3 = st.columns(3)
            t1.metric("Total before", f"{base_total/1000:.2f} t/yr")
            t2.metric("Total after", f"{after_total/1000:.2f} t/yr",
                      f"-{(base_total - after_total)/1000:.2f} t")
            t3.metric(
                "Reduction",
                f"{(base_total - after_total)/base_total*100:.1f}%" if base_total else "—",
            )
            st.caption(
                "Only categories the plan changes are shown. Untouched categories are "
                "unaffected and would appear as two identical bars."
            )

        with st.expander("Show the full ranking the greedy algorithm used"):
            st.caption(
                "Every applicable action, sorted by CO₂ saved per rupee. "
                "Greedy walks this list top to bottom and takes anything that still fits."
            )
            ranking = optimizer.greedy_ranking(scored)
            chosen_names = {s.name for s in result.chosen}
            st.dataframe(
                pd.DataFrame([
                    {
                        "": "✅" if s.name in chosen_names else "—",
                        "Action": s.name,
                        "Category": s.category,
                        "Cost (₹/yr)": round(s.cost),
                        "Saves (kg CO₂/yr)": round(s.saving, 1),
                        "kg per ₹": round(s.density, 4),
                    }
                    for s in ranking
                ]),
                use_container_width=True, hide_index=True,
            )

        # Sanity check: does the plan claim to save more than a category emits?
        claimed = {}
        for s in result.chosen:
            claimed[s.category] = claimed.get(s.category, 0) + s.saving
        overshoot = {
            cat: (amt, BASELINE_KG.get(cat, 0))
            for cat, amt in claimed.items()
            if amt > BASELINE_KG.get(cat, 0) + 1e-9
        }
        if overshoot:
            lines = "\n".join(
                f"- **{cat}**: plan claims {amt:,.0f} kg saved, but you only emit "
                f"{base:,.0f} kg there."
                for cat, (amt, base) in overshoot.items()
            )
            st.error(
                "**This plan is double-counting.** The optimizer treats every action as "
                "independent and adds their savings together, but some of these actions "
                "overlap — they attack the same emissions.\n\n"
                f"{lines}\n\nThis is a modelling flaw, not an arithmetic one — the "
                "algorithm maximised the sum correctly, but the sum was the wrong thing "
                "to maximise. Switch to **DP + groups** above to see it corrected."
            )
        elif choice == "DP + groups":
            st.success(
                "**No category over-claims.** Actions that attack the same flow of "
                "emissions are now treated as alternatives, so at most one is chosen "
                "from each. Note this check is a smoke alarm, not a proof: overlap that "
                "stays under a category's baseline would still slip through."
            )

# ── Data provenance ───────────────────────────────────────────────────────────
st.markdown("<hr style='border:1px solid #c8e6c9'>", unsafe_allow_html=True)
with st.expander("📚 Where these numbers come from — sources & limitations"):
    st.caption(
        "Every factor below is traceable. Confidence is **HIGH** where quoted from a "
        "primary source, **MEDIUM** where borrowed from another country's dataset, and "
        "**LOW** where derived by hand from cited inputs plus stated assumptions."
    )

    conf_icon = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}
    st.dataframe(
        pd.DataFrame([
            {
                "": conf_icon.get(f.confidence, ""),
                "Factor": label,
                "Value": f"{f.value:,.5g}",
                "Unit": f.unit,
                "Confidence": f.confidence,
                "Source": f.source,
            }
            for label, f in ef.ALL_FACTORS.items()
        ]),
        use_container_width=True, hide_index=True,
    )

    st.markdown("**Notes on individual factors**")
    for label, f in ef.ALL_FACTORS.items():
        if f.note:
            st.markdown(f"- **{label}** — {f.note}")

    st.markdown("**Diet data — the weakest transfer**")
    st.info(ef.DIET_LIMITATION)

    st.markdown("**What this calculator does not capture**")
    for lim in ef.GENERAL_LIMITATIONS:
        st.markdown(f"- {lim}")

    st.warning(
        "**Note on the India averages** shown throughout this page: those comparison "
        "figures have not yet been re-sourced and predate the corrected factors above. "
        "Treat the 'vs India average' deltas as indicative only until they are updated."
    )

# ── PDF Download ──────────────────────────────────────────────────────────────
if generate_report_button:
    with st.spinner("🛠️ Building your personalised PDF report..."):
        # Recompute the plan here rather than reading it from the optimizer
        # section above, so the report is complete whether or not the user
        # pressed "Build my plan" first. The grouped solver is used because it
        # is the one that does not double-count overlapping actions.
        pdf_scored = optimizer.build_actions(BASELINE_KG, USER_INPUTS)
        pdf_plan = (
            optimizer.solve_dp_grouped(pdf_scored, budget) if pdf_scored else None
        )

        pdf_bytes = generate_pdf(
            name, df, total_emissions,
            transportation_emissions, electricity_emissions, diet_emissions,
            waste_emissions, water_emissions, appliances_emissions, housing_emissions,
            fuel_type, diet, house_material,
            plan=pdf_plan, budget=budget,
        )

    st.success("✅ Report ready! Click below to download.")
    with btn3:
        st.download_button(
            label="⬇️ Download PDF Report",
            data=pdf_bytes,
            file_name=f"carbon_report_{(name.strip() or 'user').replace(' ','_')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )