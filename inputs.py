"""
The calculator's inputs, defined once.

Every input has a key, a type, bounds and a default here, and everything else
reads from this: the widgets, the "Try an example" button, the reset button,
and the share link. Share links matter most — a URL is text anyone can edit, so
values read back from it are type-checked and clamped rather than trusted.
"""

from dataclasses import dataclass
from typing import Optional

import emission_factors as ef


@dataclass(frozen=True)
class Field:
    key: str
    kind: str                 # "int", "float" or "choice"
    default: object
    min: Optional[float] = None
    max: Optional[float] = None
    choices: tuple = ()


FIELDS = [
    Field("household_size", "int", 1, 1, 20),
    Field("fuel_type", "choice", "N/A", choices=tuple(ef.VEHICLE_LABELS)),
    Field("distance", "float", 0.0, 0, 500),
    Field("electricity", "float", 0.0, 0, 5_000),
    Field("appliances", "int", 0, 0, 100),
    Field("diet", "choice", "N/A", choices=("N/A", "Vegan", "Vegetarian", "Non-Vegetarian")),
    Field("meals", "int", 3, 0, 8),
    Field("house_material", "choice", "N/A", choices=("N/A", "Brick", "Wood")),
    Field("house_size", "float", 0.0, 0, 20_000),
    Field("water", "float", 0.0, 0, 2_000),
    Field("waste", "float", 0.0, 0, 100),
]
BY_KEY = {f.key: f for f in FIELDS}

DEFAULTS = {f.key: f.default for f in FIELDS}

# A realistic urban household, so a first-time visitor sees a full result
# without typing anything. Deliberately not the India-average profile —
# comparing the example against itself would show every delta as zero.
EXAMPLE_PROFILE = {
    "household_size": 4,
    "fuel_type": "Petrol",
    "distance": 24.0,
    "electricity": 250.0,
    "appliances": 8,
    "diet": "Non-Vegetarian",
    "meals": 3,
    "house_material": "Brick",
    "house_size": 1100.0,
    "water": 150.0,
    "waste": 4.0,
}


def coerce(key: str, raw):
    """Convert one raw value to the field's type, or return None if invalid."""
    f = BY_KEY.get(key)
    if f is None:
        return None
    try:
        if f.kind == "choice":
            value = str(raw)
            return value if value in f.choices else None
        number = float(raw)
        if number != number or number in (float("inf"), float("-inf")):   # NaN/inf
            return None
        number = min(max(number, f.min), f.max)
        return int(round(number)) if f.kind == "int" else number
    except (TypeError, ValueError):
        return None


def from_query_params(params) -> dict:
    """Read a shared link back into inputs. Unknown or malformed keys are dropped."""
    out = {}
    for key in BY_KEY:
        if key in params:
            value = coerce(key, params[key])
            if value is not None:
                out[key] = value
    return out


def to_query_params(values: dict) -> dict:
    """Only non-default values, so shared links stay short.

    The user's name is deliberately never part of this — a shareable link
    should not carry personal information.
    """
    out = {}
    for f in FIELDS:
        v = values.get(f.key, f.default)
        if v != f.default:
            out[f.key] = f"{v:g}" if isinstance(v, float) else str(v)
    return out
