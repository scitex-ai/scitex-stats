"""Render supplied effect interval bounds without calculating an interval."""

from __future__ import annotations

from math import isfinite
from typing import Any, Mapping

__all__ = ["format_effect_interval"]


def format_effect_interval(effect: Mapping[str, Any], decimal_places: int = 2) -> str:
    """Return a generic CI label at effect precision, or empty when absent.

    Supplied bounds require a finite point estimate and two finite ordered
    endpoints. The interface carries no confidence level, so the label does
    not invent one. No interval or statistical coverage is calculated.
    """
    lower, upper = effect.get("ci_lower"), effect.get("ci_upper")
    if lower is None and upper is None:
        return ""
    if lower is None or upper is None:
        raise ValueError("Both ci_lower and ci_upper are required")
    value = effect.get("value")
    if value is None:
        raise ValueError("An effect value is required when CI bounds are supplied")
    try:
        lower, upper, value = float(lower), float(upper), float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Effect value and CI bounds must be finite numbers") from error
    if not all(isfinite(number) for number in (lower, upper, value)):
        raise ValueError("Effect value and CI bounds must be finite numbers")
    if lower > upper:
        raise ValueError("ci_lower must not exceed ci_upper")
    return f"CI [{lower:.{decimal_places}f}, {upper:.{decimal_places}f}]"
