import streamlit as st

# Header section
st.title("MyCarbon")
st.write("""
    In today's world, understanding and reducing our carbon footprint is essential to fight climate change. This tool helps you calculate your carbon emissions, enabling you to track and reduce your environmental impact.
""")

# Section 1: The Importance of Carbon Calculation
st.header("Why Calculate Your Carbon Footprint?")
st.write("""
    Carbon footprint refers to the total amount of greenhouse gases, particularly carbon dioxide (CO2), that are emitted by human activities. This includes energy usage, travel, waste, and more. 
    By understanding the impact of your actions, you can make informed decisions to reduce your emissions and contribute to a more sustainable future.
    
    **Why it's important:**
    - **Environmental impact:** Carbon emissions contribute to global warming, which leads to rising sea levels, more frequent storms, and habitat loss.
    - **Personal responsibility:** Understanding how your lifestyle choices affect the environment helps you take control of your carbon footprint.
    - **Informed decisions:** From reducing energy consumption to optimizing transportation methods, knowing your carbon footprint can guide your decisions toward a more sustainable lifestyle.
""")

# Section 2: How the Carbon Calculator Works
st.header("How Does This Calculator Work?")
st.write("""
    Our carbon calculator is designed to be simple yet effective. You’ll be guided through a series of questions about your daily activities and lifestyle. Based on your responses, the app will estimate your carbon emissions and provide actionable insights on how to reduce them.

    The app provides a more detailed calculation, covering various categories such as energy, travel, food, and waste.

    The more detailed the information you provide, the more accurate your carbon footprint estimate will be.
""")

# Section 3: Getting Started with the Calculator
st.header("Ready to Get Started?")
st.write("""
        It's easy to begin your journey toward a more sustainable lifestyle. Simply click the "Carbon Calculation" on the sidebar.
    """)


# Section 3: Tips for Reducing Your Carbon Footprint
st.header("Tips to Reduce Your Carbon Footprint")
st.write("""
    After calculating your carbon footprint, you can take steps to reduce it. Here are some tips:
    - **Use energy efficiently:** Switch to LED bulbs, unplug devices when not in use, and consider renewable energy sources.
    - **Choose sustainable transport options:** Walk, cycle, use public transport, or carpool when possible.
    - **Eat sustainably:** Opt for plant-based foods, reduce food waste, and support local farmers.
    - **Reduce, reuse, recycle:** Minimize your waste by reusing items and recycling where possible.
    - **Invest in green technologies:** If possible, switch to eco-friendly appliances and technologies.

    By applying these practices, you can make a significant difference in reducing your carbon footprint.
""")

# Footer with a call to action
st.markdown("---")
st.write("""
    **Take action today to reduce your carbon footprint!** 
    Join the movement towards a greener, more sustainable world.
""")
