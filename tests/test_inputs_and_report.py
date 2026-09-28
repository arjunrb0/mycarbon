"""Tests for share-link parsing and the PDF report."""

import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import emission_factors as ef
import inputs as I
import optimizer as opt

pypdf = pytest.importorskip("pypdf")
report = pytest.importorskip("report")


# ── Share links ──────────────────────────────────────────────────────────────
def test_example_survives_a_round_trip_through_a_link():
    params = I.to_query_params(I.EXAMPLE_PROFILE)
    assert {**I.DEFAULTS, **I.from_query_params(params)} == {**I.DEFAULTS, **I.EXAMPLE_PROFILE}


def test_links_leave_out_defaults_and_personal_data():
    params = I.to_query_params({**I.DEFAULTS, "distance": 12.0, "name": "Arjun"})
    assert params == {"distance": "12"}


@pytest.mark.parametrize("key,raw,expected", [
    ("distance", "12.5", 12.5),
    ("distance", "-3", 0.0),                 # clamped up
    ("distance", "1e12", 500.0),             # clamped down
    ("household_size", "3.6", 4),            # ints are rounded
    ("fuel_type", "Petrol", "Petrol"),
    ("fuel_type", "petrol", None),           # choices are exact
    ("fuel_type", "<script>", None),
    ("meals", "nan", None),
    ("meals", "inf", None),
    ("meals", "", None),
    ("not_a_field", "1", None),
])
def test_coerce(key, raw, expected):
    assert I.coerce(key, raw) == expected


def test_every_choice_field_default_is_a_valid_choice():
    for f in I.FIELDS:
        if f.kind == "choice":
            assert f.default in f.choices
        else:
            assert f.min <= f.default <= f.max


def test_example_profile_is_valid_input():
    for k, v in I.EXAMPLE_PROFILE.items():
        assert I.coerce(k, v) == v, k


# ── PDF report ───────────────────────────────────────────────────────────────
def _pdf_text(data):
    reader = pypdf.PdfReader(io.BytesIO(data))
    return len(reader.pages), " ".join(p.extract_text() for p in reader.pages)


def _example():
    values = {**I.DEFAULTS, **I.EXAMPLE_PROFILE}
    scored = opt.build_actions(ef.compute_baseline_kg(values), values)
    return values, opt.solve_dp_grouped(scored, 20_000)


def test_report_with_a_plan():
    values, plan = _example()
    pages, text = _pdf_text(report.build_pdf("Asha", values, plan, "With a budget."))
    assert pages == 3
    assert "Asha's Carbon Footprint Report" in text
    assert "Your reduction plan" in text


def test_report_without_a_plan_skips_that_page():
    values, _ = _example()
    pages, text = _pdf_text(report.build_pdf("", values))
    assert pages == 2
    assert "Your Carbon Footprint Report" in text
    assert "Your reduction plan" not in text


def test_report_survives_names_outside_latin1():
    """The PDF's built-in font can't draw Devanagari; it must not crash either."""
    values, plan = _example()
    data = report.build_pdf("अर्जुन ₹ — test", values, plan, "₹20,000 budget — test")
    assert data.startswith(b"%PDF")
