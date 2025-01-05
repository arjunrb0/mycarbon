import streamlit as st

# Ensure this is the first Streamlit command in the script
st.set_page_config(layout="wide", page_title="MyCarbon")

# Page setup
advanced_page = st.Page(
    page="advanced.py",
    title="Carbon Calculator",
)

info_page = st.Page(
    page="about_me.py",
    title="About",
    default=True,
)

# Navigation without sections
pg = st.navigation(pages=[advanced_page, info_page])

# Navigation Setup with sections
pg = st.navigation(
    {
        "Info": [info_page],
        "Projects": [advanced_page],
    }
)

# Shared on all pages
st.logo("assets/oak_logo2.png")
st.sidebar.markdown(" Designed by Arjun Reddy for Oakridge School Project")

# Run navigation
pg.run()
