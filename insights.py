"""Plain-language interpretation of a result, shared by the page and the PDF."""

import emission_factors as ef

CATEGORY_ICONS = {
    "Transportation": "🚗", "Electricity": "⚡", "Diet": "🍽️", "Housing": "🏠",
    "Waste": "🗑️", "Water": "💧", "Appliances": "🔌",
}

TIPS = {
    "Transportation": "Your commute is your biggest lever here. Carpooling, public transport, "
                      "or an electric two-wheeler cut it far more than an electric car does "
                      "on India's current grid.",
    "Electricity": "Rooftop solar and LED lighting give the largest cuts per rupee. "
                   "Check your bill's kWh figure — it is the single input that matters most.",
    "Diet": "A few meat-free days a week is the easiest diet change to sustain, and it "
            "still makes a measurable difference.",
    "Waste": "Separating wet waste for composting keeps it out of landfill, where it "
             "rots into methane.",
    "Water": "Low-flow fittings and fixing leaks cut the energy used to pump and treat "
             "your water.",
    "Appliances": "Keep appliances longer and choose 5-star BEE models when replacing — "
                  "most of an appliance's footprint here is from making it.",
    "Housing": "Building material is fixed once the home exists; for future renovations, "
               "lower-carbon materials such as fly-ash bricks help.",
}


def verdict(total_kg: float) -> tuple:
    """(headline, explanation) comparing a total against the reference points."""
    total_t = total_kg / 1000
    typical = ef.INDIA_AVERAGES["Total"]
    target = ef.LIFESTYLE_TARGET_2030.value
    ratio = total_t / typical if typical else 0

    if ratio < 0.85:
        head = "Below a typical urban Indian"
    elif ratio <= 1.15:
        head = "Close to a typical urban Indian"
    else:
        head = "Above a typical urban Indian"

    if total_t <= target:
        tail = (f"You're already within the {target:g} t per-person level that keeps "
                f"lifestyles on track for the 1.5°C goal by 2030.")
    else:
        tail = (f"Reaching the {target:g} t per-person level for the 1.5°C goal by 2030 "
                f"would mean cutting about {total_t - target:.1f} t a year — the reduction "
                f"planner shows the cheapest ways to get there.")
    return head, f"{head} ({ratio:.0%} of the typical profile). {tail}"


def tips(baseline_kg: dict, limit: int = 3) -> list:
    """(category, tip) for the categories furthest above the typical profile."""
    over = [
        (cat, kg / 1000 - ef.INDIA_AVERAGES.get(cat, 0))
        for cat, kg in baseline_kg.items()
        if kg / 1000 > ef.INDIA_AVERAGES.get(cat, 0) + 0.005
    ]
    over.sort(key=lambda t: -t[1])
    return [(cat, TIPS[cat]) for cat, _ in over[:limit]]
