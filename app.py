import streamlit as st

# Must be the first Streamlit command.
st.set_page_config(
    page_title="MyCarbon — carbon footprint calculator & reduction planner",
    page_icon="assets/icon.svg",
    layout="wide",
)

home = st.Page("views/home.py", title="Home", icon=":material/eco:", default=True)
calculator = st.Page("views/calculator.py", title="Calculator",
                     icon=":material/calculate:", url_path="calculator")
how = st.Page("views/how_it_works.py", title="How it works",
              icon=":material/insights:", url_path="how-it-works")

pg = st.navigation([home, calculator, how], position="top")
st.logo("assets/logo.svg", size="large")
pg.run()
