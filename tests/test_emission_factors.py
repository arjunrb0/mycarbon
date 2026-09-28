"""Tests for the emission factor data.

Most of these are UNIT SANITY checks with explicit plausible ranges. That is
deliberate: the worst bug this project had was dimensional, not logical — a
per-litre factor applied per kilometre, which was off by ~15x and produced a
34 tonne commute without anything crashing. Type checkers and unit tests on
the algorithm cannot catch that class of error. Range assertions can.

Each range below is wide enough not to be brittle when a factor is legitimately
re-sourced, but tight enough to catch an order-of-magnitude slip.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import emission_factors as ef


# ── Metadata integrity ───────────────────────────────────────────────────────
@pytest.mark.parametrize("label,factor", sorted(ef.ALL_FACTORS.items()))
def test_every_factor_is_fully_documented(label, factor):
    assert factor.value > 0
    assert factor.unit.strip()
    assert len(factor.source.strip()) > 20, "source must be specific"
    assert factor.url.startswith("http")
    assert factor.confidence in {"HIGH", "MEDIUM", "LOW"}


def test_low_confidence_factors_explain_themselves():
    """A LOW-confidence number without a caveat is worse than no number."""
    for label, f in ef.ALL_FACTORS.items():
        if f.confidence == "LOW":
            assert f.note.strip(), f"{label} is LOW confidence but has no note"


# ── Unit sanity: the regression guard for the per-litre/per-km bug ───────────
@pytest.mark.parametrize("fuel", sorted(ef.TRANSPORT_PER_KM))
def test_transport_factors_are_per_km_not_per_litre(fuel):
    """Any road vehicle sits well under 1 kg CO2/km.

    The original bug put 2.31 here. This assertion would have caught it.
    """
    value = ef.TRANSPORT_PER_KM[fuel].value
    assert 0.01 < value < 0.5, f"{fuel}={value} is not a plausible kg CO2/km"


def test_petrol_per_km_is_consistent_with_its_derivation():
    expected = ef.PETROL_PER_LITRE.value / ef.FUEL_ECONOMY_KMPL.value
    assert ef.TRANSPORT_PER_KM["Petrol"].value == pytest.approx(expected)


def test_electric_is_cleaner_than_petrol_but_not_dramatically():
    """On India's grid an EV is ~30% better, not ~95%.

    The old 0.12 vs 2.31 pairing implied a 95% cut and made 'buy an EV' the
    headline recommendation. That was an artefact of the unit bug.
    """
    petrol = ef.TRANSPORT_PER_KM["Petrol"].value
    electric = ef.TRANSPORT_PER_KM["Electric"].value
    reduction = 1 - electric / petrol
    assert 0.15 < reduction < 0.6, f"EV reduction of {reduction:.0%} looks wrong"


def test_grid_factor_is_plausible_for_india():
    assert 0.5 < ef.ELECTRICITY.value < 1.0


def test_diet_factors_are_ordered_and_per_day():
    veg = ef.DIET_PER_DAY["Vegetarian"].value
    vegan = ef.DIET_PER_DAY["Vegan"].value
    nonveg = ef.DIET_PER_DAY["Non-Vegetarian"].value
    assert vegan < veg < nonveg
    assert all(1 < f.value < 15 for f in ef.DIET_PER_DAY.values())


def test_housing_is_amortised_not_one_time():
    """Embodied carbon spread over a building life is a small annual number."""
    for material, f in ef.HOUSING_PER_SQFT_YEAR.items():
        assert 0.001 < f.value < 1.0, f"{material} looks like a one-time figure"


def test_waste_and_water_units():
    assert 0.1 < ef.WASTE.value < 2.0            # kg CO2e per kg waste
    assert 0.0001 < ef.WATER.value < 0.01        # kg CO2 per litre


# ── compute_baseline_kg ──────────────────────────────────────────────────────
EMPTY = {"distance": 0, "fuel_type": "N/A", "electricity": 0, "appliances": 0,
         "diet": "N/A", "meals": 0, "house_material": "N/A", "house_size": 0,
         "water": 0, "waste": 0}


def test_empty_profile_emits_nothing():
    assert all(v == 0 for v in ef.compute_baseline_kg(EMPTY).values())


def test_na_selections_do_not_raise():
    profile = dict(EMPTY, distance=20, house_size=800, meals=3)
    result = ef.compute_baseline_kg(profile)
    assert result["Transportation"] == 0     # no fuel type chosen
    assert result["Housing"] == 0            # no material chosen
    assert result["Diet"] == 0               # no diet chosen


def test_baseline_covers_every_reported_category():
    assert set(ef.compute_baseline_kg(EMPTY)) == {
        "Transportation", "Electricity", "Diet",
        "Waste", "Water", "Appliances", "Housing",
    }


def test_emissions_scale_linearly_with_usage():
    single = ef.compute_baseline_kg(dict(EMPTY, electricity=100))["Electricity"]
    double = ef.compute_baseline_kg(dict(EMPTY, electricity=200))["Electricity"]
    assert double == pytest.approx(2 * single)


def test_meals_scale_diet_around_the_reference():
    """3 meals is the reference, so it must reproduce the raw per-day factor."""
    profile = dict(EMPTY, diet="Vegetarian", meals=ef.DIET_REFERENCE_MEALS)
    expected = ef.DIET_PER_DAY["Vegetarian"].value * 365
    assert ef.compute_baseline_kg(profile)["Diet"] == pytest.approx(expected)


# ── India averages ───────────────────────────────────────────────────────────
def test_india_averages_are_computed_from_the_documented_profile():
    """Both sides of every comparison must come from the same code path."""
    recomputed = ef.compute_baseline_kg(ef.AVERAGE_INDIAN_PROFILE)
    for cat, tonnes in ef.INDIA_AVERAGES.items():
        if cat == "Total":
            continue
        assert tonnes == pytest.approx(round(recomputed[cat] / 1000, 2))


def test_india_average_total_is_the_sum_of_its_parts():
    parts = sum(v for k, v in ef.INDIA_AVERAGES.items() if k != "Total")
    assert ef.INDIA_AVERAGES["Total"] == pytest.approx(parts, abs=0.05)


def test_average_profile_inputs_are_all_documented_or_trivial():
    for key in ef.AVERAGE_INDIAN_PROFILE:
        assert key in ef.AVERAGE_PROFILE_SOURCES or key in {
            "fuel_type", "meals", "house_material",
        }, f"{key} needs a stated basis"


def test_average_profile_exceeds_national_per_capita():
    """Documents the scope difference rather than letting it look like a bug.

    The profile is urban and vehicle-owning; the national mean includes people
    with neither. If this ever inverts, one of the two numbers is wrong.
    """
    assert ef.INDIA_AVERAGES["Total"] > ef.INDIA_NATIONAL_PER_CAPITA.value


def test_general_limitations_are_present():
    assert len(ef.GENERAL_LIMITATIONS) >= 4
    assert ef.DIET_LIMITATION.strip()


def test_two_wheelers_emit_less_than_the_equivalent_car():
    t = ef.TRANSPORT_PER_KM
    assert t["Two-wheeler (petrol)"].value < t["Petrol"].value / 2
    assert t["Two-wheeler (electric)"].value < t["Electric"].value / 2


def test_every_vehicle_has_a_label():
    assert set(ef.VEHICLE_LABELS) == set(ef.TRANSPORT_PER_KM) | {"N/A"}


# ── Household size ───────────────────────────────────────────────────────────
def test_shared_categories_are_split_by_household_size():
    profile = dict(EMPTY, electricity=200, appliances=6, house_material="Brick",
                   house_size=900, diet="Vegetarian", meals=3, water=100)
    one = ef.compute_baseline_kg(profile)
    three = ef.compute_baseline_kg(dict(profile, household_size=3))
    for cat in ("Electricity", "Appliances", "Housing"):
        assert three[cat] == pytest.approx(one[cat] / 3), cat
    for cat in ("Diet", "Water"):                      # already per person
        assert three[cat] == pytest.approx(one[cat]), cat


def test_bad_household_size_is_treated_as_one():
    base = ef.compute_baseline_kg(dict(EMPTY, electricity=100))
    for bad in (0, -2, None):
        assert ef.compute_baseline_kg(dict(EMPTY, electricity=100, household_size=bad)) == base


# ── Uncertainty ranges ───────────────────────────────────────────────────────
def test_ranges_bracket_the_central_estimate():
    r = ef.baseline_range_kg(ef.AVERAGE_INDIAN_PROFILE)
    central = ef.compute_baseline_kg(ef.AVERAGE_INDIAN_PROFILE)
    for cat, value in central.items():
        lo, mid, hi = r[cat]
        assert lo <= mid <= hi and mid == pytest.approx(value)


def test_weaker_data_gets_a_wider_range():
    r = ef.baseline_range_kg(dict(EMPTY, electricity=100, appliances=5))
    elec = (r["Electricity"][2] - r["Electricity"][1]) / r["Electricity"][1]    # HIGH
    appl = (r["Appliances"][2] - r["Appliances"][1]) / r["Appliances"][1]       # LOW
    assert appl > elec


def test_total_range_combines_by_root_sum_of_squares():
    """Narrower than simply adding half-widths, wider than the widest single one."""
    r = ef.baseline_range_kg(ef.AVERAGE_INDIAN_PROFILE)
    halves = [r[c][2] - r[c][1] for c in r if c != "Total"]
    total_half = r["Total"][2] - r["Total"][1]
    assert max(halves) <= total_half + 1e-9
    assert total_half <= sum(halves) + 1e-9
    assert total_half == pytest.approx(sum(h * h for h in halves) ** 0.5)


def test_empty_profile_has_a_zero_range():
    assert ef.baseline_range_kg(EMPTY)["Total"] == (0.0, 0.0, 0.0)
