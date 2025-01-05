import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import matplotlib.pyplot as plt
from io import BytesIO
import os
from tempfile import NamedTemporaryFile
import kaleido
import plotly.graph_objects as go



# Define emission factors (example values, replace with accurate data)
EMISSION_FACTORS = {
        "N/A": 0,
        "Transportation": {
            "Petrol": 2.31,  # kgCO2/liter
            "Diesel": 2.68,  # kgCO2/liter
            "Electric": 0.12,  # kgCO2/km (assumes grid power)
            "Hybrid": 1.5  # kgCO2/liter (average hybrid efficiency)
        },
        "Energy": {
            "Electricity": 0.82,  # kgCO2/kWh
            "Appliances": 1.0,  # kgCO2/unit per year
        },
        "Diet": {
            "Vegetarian": 0.9,  # kgCO2/meal
            "Non-Vegetarian": 2.5,  # kgCO2/meal
            "Vegan": 0.7  # kgCO2/meal
        },
        "Waste": 0.232,  # kgCO2/kg
        "Water": 0.0003,  # kgCO2/liter
        "Housing": {
            "Brick": 0.3,  # kgCO2/sq ft/year
            "Wood": 0.2  # kgCO2/sq ft/year
        },
    }

# Streamlit app title
st.title("Personal Carbon Calculator")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    name = st.text_input("Enter your name:")

# Information Dialogs
@st.dialog("Daily Commute Info")
def commute_info():
    st.write("The daily distance you travel, usually to and from work or school.")
    st.write("The India Average is 15 kilometers per day.")

@st.dialog("Fuel Info")
def fuel_info():
    st.write("The type of fuel your vehicle uses: Petrol, Diesel, Electric, or Hybrid.")
  

@st.dialog("Electricity Info")
def electricity_info():
    st.write("The total electricity used in a month, measured in kilowatt-hours (kWh).")
    st.write("The India Average is 200 kWh per month.")

@st.dialog("Appliances Info")
def appliances_info():
    st.write("The number of appliances used per year and their average energy consumption.")
    st.write("The India Average is 10 Appliances per year, that include fans, washing machines, refrigerators, etc.")

@st.dialog("Diet Info")
def diet_info():
    st.write("Your dietary preference: Vegetarian, Non-Vegetarian, or Vegan.")

@st.dialog("Meals Info")
def meals_info():
    st.write("The average number of meals consumed daily.")
    st.write("The India Average is 3 meals per day.")

@st.dialog("Water Info")
def water_info():
    st.write("Your daily water usage, measured in liters.")
    st.write("The India Average is 135 liters per day.")

@st.dialog("Waste Info")
def waste_info():
    st.write("The amount of waste you generate weekly, measured in kilograms.")
    st.write("The India Average is 5 kilograms per week.")

@st.dialog("Housing Info")
def housing_info():
    st.write("Your house material type (Brick/Wood) and size in square feet.")

@st.dialog("Housing Size Info")
def housingsize_info():
    st.write("The size of your house in square feet.")

# Input sections
col1, col2, col3, col4, col5 = st.columns(5)

# Transportation inputs
with col1:
    st.header("Transportation")
    st.subheader("🚗 Daily commute distance (in km)")
    if st.button("Info", key="commute_info_button"):
        commute_info()
    distance = st.number_input("Distance", min_value=0, step=1, key="distance_input")
    
    st.subheader("🚙 Type of Vehicle Fuel Used")
    if st.button("Info", key="fuel_info_button"):
        fuel_info()
    fuel_type = st.selectbox("Fuel Type", ["N/A", "Petrol", "Diesel", "Electric", "Hybrid"], key="fuel_type_input")

# Energy inputs
with col2:
    st.header("Energy")
    st.subheader("🔦 Monthly electricity consumption")
    if st.button("Info", key="electricity_info_button"):
        electricity_info()
    electricity = st.number_input("Electricity", min_value=0, step=1, key="electricity_input")
    
    st.subheader("🔌 No. appliances used per year")
    if st.button("Info", key="appliances_info_button"):
        appliances_info()
    appliances = st.number_input("Appliances", min_value=0, step=1, key="appliances_input")

# Diet inputs
with col3:
    st.header("Dietary Habits")
    st.subheader("🍽️Dietary Preferences and Quantities")
    if st.button("Info", key="diet_info_button"):
        diet_info()
    diet = st.selectbox("Diet", ["N/A", "Vegetarian", "Non-Vegetarian", "Vegan"], key="diet_input")
    
    st.subheader("🍽️ Number of meals per day")
    if st.button("Info", key="meals_info_button"):
        meals_info()
    meals = st.number_input("Meals", min_value=0, step=1, key="meals_input")
    

# Housing inputs
with col4:
    st.header("Land Use")
    st.subheader("🏷️ Types of Materials Used")
    if st.button("Info", key="housing_info_button"):
        housing_info()
    house_material = st.selectbox("Material", ["N/A", "Brick", "Wood"], key="house_material_input")
    
    st.subheader("🏠 Total House Size Measured (in sft)")

    if st.button("Info", key="housingsize_info_button"):
        housingsize_info()
    house_size = st.number_input("House Size", min_value=0, step=100, key="house_size_input")

#Resource Management inputs
with col5:
    st.header ("Utility")
    st.subheader("💧 Daily water usage (in liters)")
    if st.button("Info", key="water_info_button"):
        water_info()
    water = st.number_input("Water", min_value=0, step=10, key="water_input")
    
    st.subheader("💩 Waste generated per week (in kg)")
    if st.button("Info", key="waste_info_button"):
        waste_info()
    waste = st.number_input("Waste", min_value=0, step=1, key="waste_input")


# Normalize inputs for yearly emissions
distance *= 365  # Daily to yearly
electricity *= 12  # Monthly to yearly
waste *= 52  # Weekly to yearly
water *= 365  # Daily to yearly

# Calculate emissions
if fuel_type == "N/A":
    transportation_emissions = 0
else:
    transportation_emissions = EMISSION_FACTORS["Transportation"][fuel_type] * distance

electricity_emissions = EMISSION_FACTORS["Energy"].get("Electricity", 0) * electricity
if diet == "N/A":
    diet_emissions = 0
else:
    diet_emissions = EMISSION_FACTORS["Diet"][diet] * meals * 365

waste_emissions = EMISSION_FACTORS["Waste"] * waste
water_emissions = EMISSION_FACTORS["Water"] * water
appliances_emissions = EMISSION_FACTORS["Energy"].get("Appliances", 0)* appliances
if house_material == "N/A":
    housing_emissions = 0
else:
    housing_emissions = EMISSION_FACTORS["Housing"][house_material] * house_size

# Convert emissions to tonnes
def to_tonnes(emission):
    return round(emission / 1000, 2)

# Emissions in tonnes
transportation_emissions = to_tonnes(transportation_emissions)
electricity_emissions = to_tonnes(electricity_emissions)
diet_emissions = to_tonnes(diet_emissions)
waste_emissions = to_tonnes(waste_emissions)
water_emissions = to_tonnes(water_emissions)
appliances_emissions = to_tonnes(appliances_emissions)
housing_emissions = to_tonnes(housing_emissions)

# Calculate total emissions
total_emissions = round(
    transportation_emissions + electricity_emissions + diet_emissions + waste_emissions +
    water_emissions + appliances_emissions + housing_emissions,
    2
)
# Create a dataframe for tabular display
df = pd.DataFrame({
    "Category": [
        "Transportation",
        "Electricity",
        "Diet",
        "Waste",
        "Water",
        "Appliances",
        "Housing",
        "Total"
    ],
    "Emissions (tonnes CO2/year)": [
        transportation_emissions,
        electricity_emissions,
        diet_emissions,
        waste_emissions,
        water_emissions,
        appliances_emissions,
        housing_emissions,
        total_emissions
    ]
})

def save_table_as_image(df):
    fig, ax = plt.subplots(figsize=(6, 4))  # Adjust size as needed
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc='center',
        loc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(col=list(range(len(df.columns))))
    temp_file = NamedTemporaryFile(delete=False, suffix=".png")  # Create a temporary file
    plt.savefig(temp_file.name, format='png', bbox_inches='tight')
    plt.close(fig)
    return temp_file.name

fig = px.pie(
    df[df["Category"] != "Total"],  # Exclude the "Total" row from the pie chart
    names="Category",  # Use the "Category" column for labels
    values="Emissions (tonnes CO2/year)",  # Use the "Emissions (tonnes CO2/year)" column for values
    title="Carbon Emissions Distribution",
    color="Category",
    color_discrete_map={
    "Transportation": "lightblue",
    "Electricity": "blue",
    "Diet": "pink",
    "Housing": "red",
    "Waste": "green",
    "Water": "purple",
    "Appliances": "orange",
    },
)

# Create the dial chart for total emissions
def create_dial_chart(value):
    dial_chart = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={"text": "Total Emissions (tonnes CO2/year)"},
            gauge={
                "axis": {"range": [0, 30]},  # Adjust max value as needed
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 5], "color": "lightgreen"},
                    {"range": [5, 15], "color": "yellow"},
                    {"range": [15, 30], "color": "red"},
                ],
                "threshold": {
                    "line": {"color": "black", "width": 4},  # Threshold line color and width
                    "thickness": 0.75,  # Thickness of the threshold
                    "value": value  # Position the threshold at the value
                },
            },
        )
    )
    return dial_chart

# Function to save the pie chart as an image
def save_pie_chart_as_image(fig):
    img_bytes = fig.to_image(format="png")
    return img_bytes

# Function to save the dial chart as an image
def save_dial_chart_as_image(dial_chart):
    img_bytes = dial_chart.to_image(format="png")
    return img_bytes

# Function to generate a PDF report
def generate_pdf_report(df, total_emissions):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Carbon Emissions Report", ln=True, align='C')
    pdf.ln(10)
    
    # Add the table of emissions
    for index, row in df.iterrows():
        pdf.cell(200, 10, txt=f"{row['Category']}: {row['Emissions (tonnes CO2/year)']} tonnes CO2", ln=True)
    
    # Add total emissions
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Total Emissions: {total_emissions} tonnes CO2", ln=True)
    
    return pdf

dial_chart_figure = create_dial_chart(total_emissions)

def get_dynamic_text(total_emissions):
    if total_emissions <= 5:
        return (
            "You as an individual have minimal environmental impact. Lifestyle includes renewable energy, limited travel, and sustainable habits."
        )
    elif 6 <= total_emissions <= 15:
        return (
            "You as an individual have moderate environmental impact. Balanced lifestyle with average consumption, follow some energy-efficient practices"
        )
    else:
        return (
            "You as an individual have signficiant environmental impact. Includes heavy relaince on fossil fules, frequent travelling and energy-intensive living"
        )

# BUTTONS
button_col1, button_col2, button_col3 = st.columns([1, 1, 1])

if "report_generated" not in st.session_state:
    st.session_state["report_generated"] = False

button_col1, button_col2, button_col3 = st.columns([1, 1, 1])

with button_col1:
    calculate_button = st.button("Calculate CO2 Emissions")

with button_col2:
    generate_report_button = st.button("Generate Report")

# Handle button clicks
if calculate_button:

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        st.subheader("Data Representation")
        st.write(df) 

    with col2:
        st.subheader("Carbon Emissions Distribution")
        st.plotly_chart(fig, use_container_width=True)  

    with col3:
        st.subheader("Total Emissions Dial")
        st.plotly_chart(dial_chart_figure, use_container_width=True) 
    
    dynamic_text = get_dynamic_text(total_emissions)
    st.success(dynamic_text)


pdf_output = b""

# Check if Generate Report button is clicked
if generate_report_button:
    class PDF(FPDF):
        def header(self):
            self.set_font('Times', 'B', 16)
            self.cell(0, 10, f'{name}\'s',0, 1, 'C')
            self.cell(0, 10, f'CARBON EMISSION REPORT',0, 1, 'C')
            self.set_font('Times', 'I', 12)
            self.cell(0, 10, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 0, 1, 'C')
            self.cell(0, 10, '', "B", 0, 1)

        def footer(self):
            self.set_y(-15)  # Position the footer 15 mm from the bottom
            self.set_font('Times', 'I', 8)  # Smaller font size
            self.cell(0, 10, 'Arjun Reddy Bathula', 0, 0, 'L')

    pdf = PDF()
    pdf.add_page()

    # Save table, pie chart, and dial chart as images
    table_image_path = save_table_as_image(df)
    pie_chart_image_path = NamedTemporaryFile(delete=False, suffix=".png").name
    fig.write_image(pie_chart_image_path, format="png")

    dial_chart_image_path = NamedTemporaryFile(delete=False, suffix=".png").name
    dial_chart_figure.write_image(dial_chart_image_path, format="png")

    # Embed table, pie chart, and dial chart side by side
    pdf.image(table_image_path, x=10, y=60, w=90)
    pdf.image(pie_chart_image_path, x=110, y=60, w=90)
    # Generate dynamic text based on total emissions
    dynamic_text = get_dynamic_text(total_emissions)
    pdf.set_x(150)
    pdf.set_y(120)  # Adjust Y-position to place text below the chart
    pdf.set_font("Arial", "B", 7.5,)
    pdf.multi_cell(0, 10, dynamic_text, align="C")

    pdf.image(dial_chart_image_path, x=110, y=130, w=90)  # Position dial chart below the others

    # Generate PDF as a binary stream
    pdf_output = pdf.output(dest='S').encode('latin1', errors='replace')
    st.success("Report generated successfully! Your download is ready below.")
    with button_col3:
        st.download_button(
            label="Download report",
            data=pdf_output,
            file_name="carbon_report.pdf",
            mime="application/pdf"
    )
