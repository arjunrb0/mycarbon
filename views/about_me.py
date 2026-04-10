import streamlit as st

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
    <div style='background:linear-gradient(135deg,#1B5E20,#43A047);
                padding:36px 28px; border-radius:14px; margin-bottom:24px'>
        <h1 style='color:white; margin:0; font-size:2.4rem'>🌿 MyCarbon</h1>
        <p style='color:#C8E6C9; font-size:1.1rem; margin-top:8px'>
            Understand your environmental impact — one category at a time.
        </p>
    </div>
""", unsafe_allow_html=True)

st.write("""
In today's world, understanding and reducing our carbon footprint is more important than ever.
**MyCarbon** helps you estimate your annual CO₂ emissions based on your daily lifestyle — 
and compare yourself against the India national average.
""")

# ── Why it matters ────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🌍 Why Calculate Your Carbon Footprint?")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    <div style='background:#E8F5E9; padding:16px; border-radius:10px; height:160px'>
        <h4 style='color:#2E7D32'>🌡️ Environmental Impact</h4>
        <p style='font-size:14px'>Carbon emissions drive global warming — leading to rising sea levels, 
        extreme weather, and habitat loss across the planet.</p>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div style='background:#E8F5E9; padding:16px; border-radius:10px; height:160px'>
        <h4 style='color:#2E7D32'>👤 Personal Responsibility</h4>
        <p style='font-size:14px'>Your daily choices — how you travel, eat, and consume energy — 
        directly affect the planet. Awareness is the first step.</p>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown("""
    <div style='background:#E8F5E9; padding:16px; border-radius:10px; height:160px'>
        <h4 style='color:#2E7D32'>📊 Informed Decisions</h4>
        <p style='font-size:14px'>By knowing which habits produce the most CO₂, 
        you can focus your efforts where they matter most for maximum impact.</p>
    </div>
    """, unsafe_allow_html=True)

# ── How it works ──────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### ⚙️ How Does the Calculator Work?")

st.markdown("""
The calculator collects information across **5 key lifestyle categories** and multiplies 
your inputs by established CO₂ emission factors to estimate your annual footprint in **tonnes of CO₂**.
""")

categories = [
    ("🚗", "Transportation", "Daily commute distance and vehicle fuel type"),
    ("⚡", "Energy",         "Monthly electricity consumption and number of appliances"),
    ("🍽️", "Diet",           "Dietary preference (Vegan / Vegetarian / Non-Veg) and meals per day"),
    ("🏠", "Housing",        "House construction material and total floor area"),
    ("💧", "Utility",        "Daily water usage and weekly waste generated"),
]

for icon, cat, desc in categories:
    st.markdown(f"""
    <div style='display:flex; align-items:center; gap:14px; padding:10px 0;
                border-bottom:1px solid #E0E0E0'>
        <span style='font-size:1.8rem'>{icon}</span>
        <div>
            <b style='color:#2E7D32'>{cat}</b><br>
            <span style='font-size:14px; color:#555'>{desc}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── India benchmark ───────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🇮🇳 India Average Benchmark")
st.markdown("""
Your results are always compared against the **India national average of ~3.64 tonnes CO₂/year** 
(and the world average of ~4.7 tonnes). This gives your numbers real context.
""")

b1, b2, b3 = st.columns(3)
b1.metric("🇮🇳 India Average", "3.64 t CO₂/yr")
b2.metric("🌍 World Average",  "4.7 t CO₂/yr")
b3.metric("🎯 Paris Target",   "< 2.0 t CO₂/yr")

# ── Get started ───────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🚀 Ready to Get Started?")
st.markdown("""
Head to the **Carbon Calculator** page in the sidebar. Fill in your details across each category, 
hit **Calculate Emissions**, and get your personalised results — including a full PDF report 
you can save and share.
""")

st.markdown("""
<div style='background:#F1F8E9; border-left:5px solid #66BB6A; padding:14px 18px; border-radius:8px'>
    <b>💡 Tip:</b> The more accurate your inputs, the more useful your results will be. 
    Check your electricity bill for kWh usage and your odometer for daily distance.
</div>
""", unsafe_allow_html=True)

# ── Tips ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### ♻️ General Tips to Reduce Your Footprint")

t1, t2 = st.columns(2)
with t1:
    st.markdown("""
- 💡 Switch to LED bulbs and unplug devices when not in use
- 🚌 Use public transport, carpool, or cycle for daily commutes
- 🌱 Reduce meat consumption — try plant-based meals a few days a week
- ♻️ Separate waste and compost organic material
""")
with t2:
    st.markdown("""
- 🚿 Take shorter showers and fix leaky taps
- 🌞 Consider rooftop solar panels (subsidised in India)
- 🛍️ Avoid single-use plastics — carry a reusable bag and bottle
- 🏷️ Buy energy-efficient (5-star rated) appliances
""")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<p style='text-align:center; color:#888; font-size:13px'>
    Built by <b>Arjun Reddy Bathula</b> for Oakridge International School · 
    <a href='https://mycarbon.streamlit.app' style='color:#43A047'>mycarbon.streamlit.app</a>
</p>
""", unsafe_allow_html=True)
