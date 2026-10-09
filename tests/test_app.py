"""End-to-end tests of the real app, driven through Streamlit's test harness.

These run through app.py so page links and navigation behave as in production.
The first test is the regression guard for the bug that motivated the redesign:
results used to vanish the moment you touched any other control, because they
were only drawn on the single rerun right after a button click.
"""

import os

import pytest

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.py")
CALC = "views/calculator.py"


def open_calculator(query=None):
    at = AppTest.from_file(APP, default_timeout=180)
    if query:
        at.query_params.update(query)
    at.run()
    at.switch_page(CALC)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def click(at, label):
    [b for b in at.button if label in b.label][0].click()
    at.run()
    assert not at.exception, [e.message for e in at.exception]


def tile_text(at):
    return " ".join(h.proto.body for h in at.get("html"))


def test_every_page_loads_without_errors():
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert not at.exception
    for page in ("views/how_it_works.py", CALC):
        at.switch_page(page)
        at.run()
        assert not at.exception, (page, [e.message for e in at.exception])


def test_empty_calculator_shows_the_empty_state():
    at = open_calculator()
    assert "Your results will appear here" in tile_text(at)


def test_example_fills_in_and_shows_results():
    at = open_calculator()
    click(at, "Try an example")
    assert "Your footprint" in tile_text(at)
    assert at.number_input(key="in_distance").value == 24.0


def test_results_survive_touching_other_controls():
    """Regression: results used to disappear on the next interaction."""
    at = open_calculator()
    click(at, "Try an example")
    at.select_slider(key="in_plan_budget").set_value(60_000)
    at.run()
    assert "Your footprint" in tile_text(at)
    assert "Cuts" in tile_text(at)
    at.number_input(key="in_electricity").set_value(300.0)
    at.run()
    assert "Your footprint" in tile_text(at)


def test_target_mode_produces_a_plan():
    at = open_calculator()
    click(at, "Try an example")
    at.segmented_control(key="in_plan_mode").set_value("target")
    at.run()
    assert not at.exception
    assert "Cuts" in tile_text(at)


def test_unreachable_target_warns_instead_of_failing():
    at = open_calculator()
    click(at, "Try an example")
    at.segmented_control(key="in_plan_mode").set_value("target")
    at.run()
    at.slider(key="in_plan_target").set_value(90)
    at.run()
    assert not at.exception
    assert any("isn't reachable" in w.value for w in at.warning)


def test_inputs_survive_leaving_the_page():
    at = open_calculator()
    click(at, "Try an example")
    at.switch_page("views/how_it_works.py")
    at.run()
    at.switch_page(CALC)
    at.run()
    assert at.number_input(key="in_distance").value == 24.0
    assert "Your footprint" in tile_text(at)


def test_share_link_round_trip():
    at = open_calculator({"fuel_type": "Two-wheeler (petrol)", "distance": "18",
                          "electricity": "120", "diet": "Vegetarian"})
    assert at.selectbox(key="in_fuel_type").value == "Two-wheeler (petrol)"
    assert at.number_input(key="in_distance").value == 18.0
    assert "Your footprint" in tile_text(at)


def test_hostile_share_link_is_clamped_not_crashed():
    at = open_calculator({"distance": "999999", "fuel_type": "Rocket",
                          "meals": "abc", "household_size": "-4"})
    assert at.number_input(key="in_distance").value == 500.0   # clamped to the maximum
    assert at.selectbox(key="in_fuel_type").value == "N/A"      # unknown vehicle dropped
    assert at.number_input(key="in_meals").value == 3           # malformed → default
    assert at.number_input(key="in_household_size").value == 1  # clamped to the minimum
    # A distance without a vehicle emits nothing: this used to divide by zero.
    assert "Your results will appear here" in tile_text(at)


def test_reset_clears_everything():
    at = open_calculator()
    click(at, "Try an example")
    click(at, "Reset")
    assert at.number_input(key="in_distance").value == 0.0
    assert "Your results will appear here" in tile_text(at)


def test_pdf_report_is_created_and_offered():
    at = open_calculator()
    click(at, "Try an example")
    click(at, "Create my report")
    assert len(at.get("download_button")) == 1


# ── Home page: optional video and write-up ──────────────────────────────────
import sys as _sys
_sys.path.insert(0, ROOT)
import site_content


def _home(monkeypatch, url):
    monkeypatch.setattr(site_content, "VIDEO_URL", url)
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def test_home_without_a_video_shows_no_player(monkeypatch):
    at = _home(monkeypatch, "")
    assert len(at.get("video")) == 0
    assert any("Start the calculator" in b.label for b in at.button)


def test_home_with_a_video_embeds_it(monkeypatch):
    at = _home(monkeypatch, "https://youtu.be/EXAMPLE0001")
    assert len(at.get("video")) == 1


def test_home_shows_the_write_up_but_never_the_editing_note(monkeypatch):
    at = _home(monkeypatch, "")
    text = " ".join(m.value for m in at.markdown)
    assert "knapsack problem" in text
    assert "DRAFT" not in text and "rewrite this" not in text
