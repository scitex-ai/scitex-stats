#!/usr/bin/env python3
# File: src/scitex_stats/_rest/_inputs.py

"""Input checks shared by every stats REST handler.

The SDK has already refused unknown keys and checked each field's JSON type
(array, number, ...). What is left is the content: every numeric value is a
finite JSON number (``NaN`` / ``Infinity`` literals, booleans, strings and
nested lists are refused), every array has the declared depth, and the total
count of values stays under the caller's cap — the public profile's
``max_values`` for an anonymous call, :data:`MAX_VALUES` for anyone.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, List, Optional

try:  # PS-233: scitex-sdk is the [server] extra
    from scitex_sdk.app.api_exec import ApiProblem
except ImportError as exc:
    raise ImportError(
        "scitex_stats._rest needs scitex-sdk, which is not installed. "
        "Install the optional stack: pip install 'scitex-stats[server]'"
    ) from exc

#: The hard cap on numeric values per call, for every caller.
MAX_VALUES = 1_000_000
#: The cap for a public-class call whose profile names no ``max_values``.
PUBLIC_MAX_VALUES = 100_000
#: At most this many groups (or contingency-table rows).
MAX_GROUPS = 1_000
#: At most this many characters in one group name.
MAX_NAME_CHARS = 200

INVALID = "stats.invalid_input"
TOO_MANY = "stats.too_many_values"


def invalid(detail: str, field: str) -> ApiProblem:
    return ApiProblem(
        400,
        INVALID,
        detail,
        errors=[{"field": field, "code": "invalid", "message": detail}],
    )


def value_cap(call) -> int:
    """The number of numeric values this call may send."""
    limits = call.limits
    if limits is None:
        return MAX_VALUES
    return min(MAX_VALUES, limits.get("max_values") or PUBLIC_MAX_VALUES)


class Budget:
    """Counts numeric values across every field of one call."""

    def __init__(self, cap: int):
        self.cap = cap
        self.used = 0

    def take(self, n: int, field: str) -> None:
        self.used += n
        if self.used > self.cap:
            raise ApiProblem(
                413,
                TOO_MANY,
                f"this call may send at most {self.cap} numeric values "
                f"(counted across data, data2 and groups); {field} exceeds it",
                extra={"limit": "max_values", "max_values": self.cap},
            )


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise invalid(f"{field} must contain only numbers", field)
    try:
        out = float(value)
    except OverflowError:
        raise invalid(
            f"{field} contains a number too large to represent", field
        ) from None
    if not math.isfinite(out):
        raise invalid(
            f"{field} must contain only finite numbers (no NaN or Infinity)", field
        )
    return out


def numbers(value: Any, field: str, budget: Budget, *, min_len: int = 1) -> List[float]:
    """A flat list of finite numbers, counted against ``budget``."""
    if not isinstance(value, list):
        raise invalid(f"{field} must be an array of numbers", field)
    budget.take(len(value), field)
    if len(value) < min_len:
        raise invalid(f"{field} needs at least {min_len} value(s)", field)
    return [_number(v, field) for v in value]


def groups_of(
    value: Any, field: str, budget: Budget, *, min_groups: int = 1
) -> List[List[float]]:
    """An array of arrays of finite numbers, counted against ``budget``."""
    if not isinstance(value, list):
        raise invalid(f"{field} must be an array of arrays of numbers", field)
    if not min_groups <= len(value) <= MAX_GROUPS:
        raise invalid(
            f"{field} must hold between {min_groups} and {MAX_GROUPS} arrays", field
        )
    return [numbers(g, f"{field}[{i}]", budget) for i, g in enumerate(value)]


def names_of(value: Any, field: str, n_max: int) -> Optional[List[str]]:
    """Optional display labels: strings, at most ``n_max`` of them."""
    if value is None:
        return None
    if not isinstance(value, list) or len(value) > n_max:
        raise invalid(f"{field} must be an array of at most {n_max} strings", field)
    for name in value:
        if not isinstance(name, str) or not 0 < len(name) <= MAX_NAME_CHARS:
            raise invalid(
                f"{field} entries must be strings of 1-{MAX_NAME_CHARS} characters",
                field,
            )
    return list(value)


def in_range(
    value: Any,
    field: str,
    low: float,
    high: float,
    *,
    open_low: bool = False,
    open_high: bool = False,
) -> Any:
    """``value`` unchanged when it lies in the interval, else a 400."""
    above = value > low if open_low else value >= low
    below = value < high if open_high else value <= high
    if not (math.isfinite(value) and above and below):
        left, right = "(" if open_low else "[", ")" if open_high else "]"
        raise invalid(f"{field} must lie in {left}{low}, {high}{right}", field)
    return value


def finite_json(value: Any) -> Any:
    """NumPy -> native, NaN/Inf -> ``None``, recursively (JSON has no NaN)."""
    if isinstance(value, dict):
        return {str(k): finite_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite_json(v) for v in value]
    if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
        return finite_json(value.tolist())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def without_keys(value: Any, keys: Iterable[str]) -> Any:
    """``value`` with every mapping entry named in ``keys`` removed, recursively."""
    drop = set(keys)
    if isinstance(value, dict):
        return {k: without_keys(v, drop) for k, v in value.items() if k not in drop}
    if isinstance(value, list):
        return [without_keys(v, drop) for v in value]
    return value


# EOF
