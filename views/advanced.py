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

# ── Emission Factors ────────────────────────────────────────────────────────
EMISSION_FACTORS = {
    "N/A": 0,
    "Transportation": {
        "Petrol": 2.31,
        "Diesel": 2.68,
        "Electric": 0.12,
        "Hybrid": 1.5,
    },
    "Energy": {
        "Electricity": 0.82,
        "Appliances": 1.0,
    },
    "Diet": {
        "Vegetarian": 0.9,
        "Non-Vegetarian": 2.5,
        "Vegan": 0.7,
    },
    "Waste": 0.232,
    "Water": 0.0003,
    "Housing": {
        "Brick": 0.3,
        "Wood": 0.2,
    },
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
diet_emissions           = 0 if diet == "N/A" else EMISSION_FACTORS["Diet"][diet] * meals * 365
waste_emissions          = EMISSION_FACTORS["Waste"] * waste_yr
water_emissions          = EMISSION_FACTORS["Water"] * water_yr
appliances_emissions     = EMISSION_FACTORS["Energy"]["Appliances"] * appliances
housing_emissions        = 0 if house_material == "N/A" else EMISSION_FACTORS["Housing"][house_material] * house_size

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
    df_c = df[df["Category"] != "Total"]
    colors = [CATEGORY_COLORS.get(c, "#999") for c in df_c["Category"]]
    fig, ax = plt.subplots(figsize=(6, 5))
    wedges, texts, autotexts = ax.pie(
        df_c["Your Emissions (t CO₂/yr)"],
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

    label = "🟢 Low" if value <= 5 else "🟡 Moderate" if value <= 15 else "🔴 High"
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

def make_table_image(df):
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.axis("tight")
    ax.axis("off")
    table_data = []
    for _, row in df.iterrows():
        your_val = row["Your Emissions (t CO₂/yr)"]
        avg_val  = row["India Average (t CO₂/yr)"]
        diff     = round(your_val - avg_val, 2)
        flag     = "✓" if diff <= 0 else "↑"
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
        return "🟢 Low Impact", "Your carbon footprint is well below the India average. Keep up your eco-friendly habits!"
    elif total <= 15:
        return "🟡 Moderate Impact", "Your footprint is around the India average. There is room for improvement in a few areas."
    else:
        return "🔴 High Impact", "Your footprint is significantly above average. Targeted changes can make a big difference."

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
                 housing_emissions, fuel_type, diet, house_material):

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

    pie_path   = buf_to_tmp(pie_buf)
    gauge_path = buf_to_tmp(gauge_buf)
    bar_path   = buf_to_tmp(bar_buf)
    table_path = buf_to_tmp(table_buf)

    class PDF(FPDF):
        def header(self):
            self.set_fill_color(46, 125, 50)
            self.rect(0, 0, 210, 28, "F")
            self.set_font("Arial", "B", 18)
            self.set_text_color(255, 255, 255)
            self.set_y(6)
            display_name = name.strip() if name.strip() else "Your"
            self.cell(0, 8, f"{display_name}'s Carbon Emission Report", ln=True, align="C")
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
        ("Electricity",    electricity_emissions,    "India's grid is coal-heavy at ~0.82 kg CO2 per kWh consumed."),
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
        status = "Below average ✓" if diff <= 0 else f"Above average by {diff:.2f} t"
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
        tag = "  ⚠ Priority" if above else "  ✓ On Track"
        pdf.cell(0, 6, f"  {cat}{tag}", fill=True, ln=True)
        pdf.set_text_color(40, 40, 40)
        pdf.set_font("Arial", "", 9)
        for tip in all_tips[cat]:
            pdf.cell(6, 5, "", border=0)
            pdf.multi_cell(0, 5, f"• {tip}")
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

    # Cleanup
    for p in [pie_path, gauge_path, bar_path, table_path]:
        try:
            os.unlink(p)
        except Exception:
            pass

    return bytes(pdf.output(dest="S"))


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
        st.plotly_chart(pie_fig, use_container_width=True)
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

# ── PDF Download ──────────────────────────────────────────────────────────────
if generate_report_button:
    with st.spinner("🛠️ Building your personalised PDF report..."):
        pdf_bytes = generate_pdf(
            name, df, total_emissions,
            transportation_emissions, electricity_emissions, diet_emissions,
            waste_emissions, water_emissions, appliances_emissions, housing_emissions,
            fuel_type, diet, house_material
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
