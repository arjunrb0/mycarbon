"""
Emission factors with sources, units, and confidence levels.

Every factor here carries its provenance. The point is not decoration: a
carbon calculator whose numbers cannot be traced is a random number generator
with a nice UI. Where a value is derived rather than quoted, the derivation
chain is written out so it can be checked and argued with.

Confidence levels used below:
    HIGH     quoted directly from a primary or official source
    MEDIUM   quoted from a reputable source, but transferred from another
             country or context to India
    LOW      derived by the author from cited inputs plus stated assumptions;
             treat as order-of-magnitude only

── THE UNIT BUGS THIS MODULE FIXES ──────────────────────────────────────────

The original factors had three dimensional errors that no amount of citation
would have repaired:

1. TRANSPORT was the big one. 2.31 and 2.68 are the standard combustion
   factors for petrol and diesel in kg CO2 PER LITRE. The calculator
   multiplied them by KILOMETRES. Since an Indian car covers roughly 15 km on
   a litre, this overstated driving emissions by about 15x — a 40 km/day
   commute came out at 34 tonnes CO2/yr, which is more than the average
   American emits in total, from everything.

2. HOUSING treated embodied carbon as recurring. Bricks are fired once, when
   the house is built; they do not re-emit every year. Charging the full
   embodied carbon annually is a category error. It is now amortised over an
   assumed building life.

3. APPLIANCES double-counted electricity. A fridge's running emissions are
   already inside the metered kWh figure, so counting appliances separately
   charged the same energy twice. The category now represents only the
   MANUFACTURING carbon of the appliance, amortised over its life, which is
   genuinely additional to the electricity reading.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Factor:
    value: float
    unit: str
    source: str
    url: str
    confidence: str
    note: str = ""


# ── Electricity ──────────────────────────────────────────────────────────────
# India's grid is coal-heavy, which makes this the single most consequential
# number in the calculator. The CEA publishes it annually.
#
# Three different factors get quoted and they are not interchangeable:
#   Weighted Average  — all generation including renewables. Right for
#                       consumption accounting, which is what we do here.
#   Operating Margin  — excludes must-run renewables. Used for CDM/offset
#                       baselines, NOT for a personal footprint.
#   Build Margin      — the most recently built capacity.
# Picking the wrong one is a common and invisible error.

ELECTRICITY = Factor(
    value=0.710,
    unit="kg CO2 / kWh",
    source="Central Electricity Authority, CO2 Baseline Database for the Indian "
           "Power Sector, Version 21.0 — Weighted Average Emission Factor, FY 2024-25",
    url="https://cea.nic.in/cdm-co2-baseline-database/",
    confidence="HIGH",
    note="Was 0.82 — that was roughly India's grid around 2015-18. The grid has "
         "decarbonised since as renewables scaled, so the old value overstated "
         "electricity emissions by about 15%. Transmission and distribution "
         "losses are not added on top here; including them would raise the "
         "consumption-side figure by roughly 15-20%.",
)


# ── Transportation ───────────────────────────────────────────────────────────
# Expressed PER KILOMETRE, which is what the calculator actually asks the user
# for. Getting here needs two numbers: how much CO2 a litre of fuel releases,
# and how far the vehicle goes on that litre.
#
#   petrol:  2.31 kg CO2/litre ÷ 15 km/litre = 0.154 kg/km
#   diesel:  2.68 kg CO2/litre ÷ 18 km/litre = 0.149 kg/km
#
# Fuel economy is real-world Indian city/highway mix, which runs 15-25% below
# the ARAI lab ratings printed in brochures. Using ARAI figures would flatter
# every petrol and diesel result.

PETROL_PER_LITRE = Factor(
    value=2.31, unit="kg CO2 / litre",
    source="Standard stoichiometric combustion factor for petrol, as used in "
           "UK DEFRA / IPCC national inventory guidance",
    url="https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting",
    confidence="HIGH",
    note="Tailpipe (tank-to-wheel) only. Excludes extraction and refining, "
         "which add roughly 20% on a well-to-wheel basis.",
)

DIESEL_PER_LITRE = Factor(
    value=2.68, unit="kg CO2 / litre",
    source="Standard stoichiometric combustion factor for diesel, as used in "
           "UK DEFRA / IPCC national inventory guidance",
    url="https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting",
    confidence="HIGH",
)

FUEL_ECONOMY_KMPL = Factor(
    value=15.0, unit="km / litre",
    source="Real-world Indian petrol car economy; ARAI-rated figures for common "
           "hatchbacks exceed 24 km/l but deliver 18-20 km/l in practice, and "
           "larger or older vehicles do worse",
    url="https://gomechanic.in/blog/arai-fuel-efficiency-vs-actual-fuel-efficiency/",
    confidence="MEDIUM",
    note="A single fleet-average number standing in for everything from a "
         "two-wheeler at 45 km/l to an SUV at 8 km/l. This is the largest "
         "source of error in the transport estimate.",
)

TRANSPORT_PER_KM = {
    "Petrol": Factor(
        value=2.31 / 15.0,          # 0.154
        unit="kg CO2 / km",
        source="Derived: petrol combustion factor / real-world fuel economy",
        url="https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting",
        confidence="MEDIUM",
    ),
    "Diesel": Factor(
        value=2.68 / 18.0,          # 0.149
        unit="kg CO2 / km",
        source="Derived: diesel combustion factor / real-world fuel economy "
               "(diesel engines are more efficient per litre)",
        url="https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting",
        confidence="MEDIUM",
    ),
    "Hybrid": Factor(
        value=2.31 / 22.0,          # 0.105
        unit="kg CO2 / km",
        source="Derived: petrol combustion factor / hybrid economy, taken as "
               "~45% better than a comparable petrol car",
        url="https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting",
        confidence="LOW",
    ),
    "Electric": Factor(
        value=0.15 * 0.710,         # 0.107
        unit="kg CO2 / km",
        source="Derived: ~0.15 kWh/km typical compact EV consumption x CEA grid "
               "factor 0.710 kg CO2/kWh",
        url="https://cea.nic.in/cdm-co2-baseline-database/",
        confidence="MEDIUM",
        note="IMPORTANT AND COUNTERINTUITIVE: on India's coal-heavy grid an EV "
             "is about 30% cleaner than petrol per km — NOT the 95% the old "
             "0.12 kg/km figure implied. An EV is only as clean as the "
             "electricity charging it. The old value was closer to a European "
             "grid than an Indian one, and it made 'buy an EV' look far more "
             "attractive than it is here. This factor falls every year as the "
             "grid decarbonises.",
    ),
}


# ── Diet ─────────────────────────────────────────────────────────────────────
# Scarborough et al. (2014) is the standard reference: 2,041 vegans, 15,751
# vegetarians and 29,589 meat-eaters, normalised to a 2,000 kcal/day diet.

DIET_PER_DAY = {
    "Non-Vegetarian": Factor(
        value=5.63, unit="kg CO2e / day",
        source="Scarborough et al. (2014), Climatic Change 125:179-192 — "
               "medium meat-eaters (50-99 g meat/day)",
        url="https://link.springer.com/article/10.1007/s10584-014-1169-1",
        confidence="MEDIUM",
    ),
    "Vegetarian": Factor(
        value=3.81, unit="kg CO2e / day",
        source="Scarborough et al. (2014), Climatic Change 125:179-192",
        url="https://link.springer.com/article/10.1007/s10584-014-1169-1",
        confidence="MEDIUM",
    ),
    "Vegan": Factor(
        value=2.89, unit="kg CO2e / day",
        source="Scarborough et al. (2014), Climatic Change 125:179-192",
        url="https://link.springer.com/article/10.1007/s10584-014-1169-1",
        confidence="MEDIUM",
    ),
}

DIET_LIMITATION = (
    "These are UK diets, and transferring them to India is the weakest "
    "assumption in this module. Two errors push in opposite directions: Indian "
    "non-vegetarian diets contain far less red meat than UK ones, so 5.63 is "
    "probably too high; but Indian vegetarian diets are heavy in dairy, which "
    "is emissions-intensive, so 3.81 is probably too low. The gap between "
    "vegetarian and non-vegetarian is therefore likely NARROWER in India than "
    "this model shows. No equivalent India-specific cohort study was found."
)

DIET_REFERENCE_MEALS = 3   # Scarborough normalises to 2,000 kcal ~ 3 meals/day


# ── Waste ────────────────────────────────────────────────────────────────────
WASTE = Factor(
    value=0.446,
    unit="kg CO2e / kg waste",
    source="UK DEFRA GHG conversion factors 2025 — general/residual waste to "
           "landfill, 446.242 kg CO2e per tonne",
    url="https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting",
    confidence="MEDIUM",
    note="Was 0.232, which understated it by roughly half. Landfill emissions "
         "are mostly methane from decomposing organic matter, and Indian "
         "municipal waste has a HIGHER wet organic fraction than UK waste, so "
         "if anything this is still conservative for India. Applying a UK "
         "landfill factor also assumes UK landfill management — many Indian "
         "sites are open dumps with different decomposition behaviour.",
)


# ── Water ────────────────────────────────────────────────────────────────────
WATER = Factor(
    value=0.66 * 0.710 / 1000,      # 0.00047
    unit="kg CO2 / litre",
    source="Derived: ~0.66 kWh per m3 for municipal abstraction, treatment and "
           "distribution x CEA grid factor 0.710 kg CO2/kWh",
    url="https://cea.nic.in/cdm-co2-baseline-database/",
    confidence="LOW",
    note="The energy intensity of water supply varies enormously with how far "
         "and how high the water must be pumped — a gravity-fed hill town and "
         "a city drawing from a distant reservoir differ by an order of "
         "magnitude. Excludes energy used to HEAT water in the home, which is "
         "usually much larger than supply energy and is already counted under "
         "electricity.",
)


# ── Housing ──────────────────────────────────────────────────────────────────
# Embodied carbon is a ONE-TIME emission at construction. To sit in an annual
# footprint it must be amortised over the building's service life.
#
#   brick masonry:  ~250 kg of brick per m2 of floor area
#                   x 0.24 kg CO2/kg fired clay brick   = ~60 kg CO2/m2
#                   / 50 year building life             = 1.2 kg CO2/m2/yr
#                   / 10.764 sq ft per m2               = 0.111 kg CO2/sqft/yr

BUILDING_LIFE_YEARS = 50

HOUSING_PER_SQFT_YEAR = {
    "Brick": Factor(
        value=0.111,
        unit="kg CO2 / sq ft / year",
        source="Derived from fired clay brick embodied carbon of ~0.24 kg CO2/kg "
               "(Indian brick LCA literature), assuming ~250 kg masonry per m2 "
               "of floor area, amortised over a 50-year building life",
        url="https://www.sciencedirect.com/science/article/abs/pii/S0959652616308381",
        confidence="LOW",
        note="The masonry-mass-per-floor-area assumption is the author's, not a "
             "cited figure, and it is the weak link in this chain. Indian "
             "brick emissions also vary widely by kiln type — traditional "
             "clamp kilns are dirtier than zigzag kilns.",
    ),
    "Wood": Factor(
        value=0.045,
        unit="kg CO2 / sq ft / year",
        source="Derived: timber construction taken at ~40% of brick embodied "
               "carbon on an equivalent-structure basis",
        url="https://www.sciencedirect.com/science/article/abs/pii/S0959652616308381",
        confidence="LOW",
        note="Ignores biogenic carbon storage in timber, which some accounting "
             "standards treat as a negative emission. Timber construction is "
             "also rare in most of India.",
    ),
}


# ── Appliances ───────────────────────────────────────────────────────────────
APPLIANCE_EMBODIED = Factor(
    value=30.0,
    unit="kg CO2 / appliance / year",
    source="Derived: ~300 kg CO2 manufacturing footprint for a typical major "
           "household appliance, amortised over a 10-year service life",
    url="https://www.sciencedirect.com/science/article/pii/S2949750723000056",
    confidence="LOW",
    note="MANUFACTURING carbon only. The electricity an appliance consumes is "
         "already captured by the metered kWh input, so counting operational "
         "energy here as well would double-count it. The old factor of 1.0 kg "
         "per appliance per year had no defensible interpretation at all — it "
         "was neither embodied nor operational.",
)


# ── Registry, for the UI ─────────────────────────────────────────────────────
ALL_FACTORS = {
    "Electricity": ELECTRICITY,
    "Transport — Petrol": TRANSPORT_PER_KM["Petrol"],
    "Transport — Diesel": TRANSPORT_PER_KM["Diesel"],
    "Transport — Hybrid": TRANSPORT_PER_KM["Hybrid"],
    "Transport — Electric": TRANSPORT_PER_KM["Electric"],
    "Diet — Non-Vegetarian": DIET_PER_DAY["Non-Vegetarian"],
    "Diet — Vegetarian": DIET_PER_DAY["Vegetarian"],
    "Diet — Vegan": DIET_PER_DAY["Vegan"],
    "Waste": WASTE,
    "Water": WATER,
    "Housing — Brick": HOUSING_PER_SQFT_YEAR["Brick"],
    "Housing — Wood": HOUSING_PER_SQFT_YEAR["Wood"],
    "Appliances": APPLIANCE_EMBODIED,
}

GENERAL_LIMITATIONS = [
    "These are AVERAGE factors applied to an individual. Averages describe "
    "populations, not people — your actual grid mix, car, and diet all differ "
    "from the mean.",
    "Consumption emissions from goods and services — clothing, electronics, "
    "healthcare, education — are not modelled at all. For many households "
    "these are comparable to the categories that ARE modelled, so the total "
    "should be read as a lower bound.",
    "Air travel is not modelled, and a single long-haul return flight can "
    "exceed everything else in this calculator combined.",
    "Factors are point-in-time. The grid factor in particular falls every "
    "year, so a result computed today is not comparable to one from 2018.",
    "Several factors are transferred from UK or global datasets because no "
    "India-specific equivalent was found. Each is marked MEDIUM or LOW "
    "confidence above.",
]
