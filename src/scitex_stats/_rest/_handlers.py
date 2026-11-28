#!/usr/bin/env python3
# File: src/scitex_stats/_rest/_handlers.py

"""Handlers of the ``tests`` resource: catalogue, run, recommend.

Every handler takes the SDK's :class:`~scitex_sdk.app.api_exec.ApiCall`
(``call.params`` already typed, unknown keys already refused), checks the
content with :mod:`._inputs`, calls the package function, and returns
JSON-native data with NaN/Inf as ``null``. No handler reads or writes a file,
imports a name from the request, or runs code the caller supplies.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable

from scitex_sdk.app.api_exec import ApiPage, ApiProblem

from . import _catalog
from ._inputs import (
    Budget,
    finite_json,
    groups_of,
    in_range,
    invalid,
    names_of,
    numbers,
    value_cap,
    without_keys,
)

TEST_NOT_FOUND = "stats.test_not_found"
#: Package errors that mean "these inputs do not fit this test" (a 400).
INPUT_ERRORS = (
    ValueError,
    TypeError,
    ZeroDivisionError,
    FloatingPointError,
    ArithmeticError,
)
#: Fields of ``tests.run`` that every test kind may take.
_ALWAYS = {"alternative"}


def only(params: Dict[str, Any], allowed: Iterable[str], why: str) -> None:
    """Refuse a field the chosen form does not read (never ignore it silently)."""
    extra = sorted(set(params) - set(allowed))
    if extra:
        raise invalid(f"{', '.join(extra)} not used {why}", extra[0])


def input_error(exc: BaseException) -> ApiProblem:
    detail = (
        str(exc).strip().splitlines()[0][:500]
        if str(exc).strip()
        else type(exc).__name__
    )
    return invalid(detail, "data")


def finite(value: float, field: str) -> float:
    return in_range(value, field, -math.inf, math.inf, open_low=True, open_high=True)


# ------------------------------------------------------------------ catalogue


def list_tests(call) -> ApiPage:
    entries = _catalog.catalogue()
    page = entries[call.offset : call.offset + call.limit]
    return ApiPage(
        page, has_more=call.offset + call.limit < len(entries), total=len(entries)
    )


def _test_id(call) -> str:
    test_id = call.id or ""
    from scitex_stats import available_tests

    if test_id not in available_tests():
        raise ApiProblem(
            404,
            TEST_NOT_FOUND,
            f"no test named {test_id[:80]!r}; GET /api/v1/stats/tests lists them",
        )
    return test_id


def get_test(call) -> Dict:
    return _catalog.describe_test(_test_id(call))


# ------------------------------------------------------------------ run


def _run_kwargs(test_id: str, params: Dict[str, Any], budget: Budget) -> Dict:
    entry = _catalog.describe_test(test_id)
    kind = entry["kind"]
    given = set(params)
    allowed = set(entry["required"]) | set(entry["optional"])
    if kind == "contingency":
        allowed |= {"data", "data2"}
    if kind in ("two_sample", "paired"):
        allowed |= _ALWAYS
    only(params, allowed, f"by {test_id} ({entry['inputs']})")
    if kind == "contingency":
        if "groups" in given and ("data" in given or "data2" in given):
            raise invalid(
                "send the table either as groups or as data and data2", "groups"
            )
        if "groups" not in given and not {"data", "data2"} <= given:
            raise invalid(
                f"{test_id} needs groups (the table) or data and data2", "groups"
            )
    else:
        missing = [f for f in entry["required"] if f not in given]
        if missing:
            raise invalid(
                f"{test_id} needs {', '.join(missing)} ({entry['inputs']})", missing[0]
            )
    kwargs: Dict[str, Any] = {}
    if "data" in given:
        kwargs["data"] = numbers(params["data"], "data", budget)
    if "data2" in given:
        kwargs["data2"] = numbers(params["data2"], "data2", budget)
    if "groups" in given:
        kwargs["groups"] = groups_of(params["groups"], "groups", budget)
    if "popmean" in given:
        kwargs["popmean"] = finite(params["popmean"], "popmean")
    if "alternative" in given:
        kwargs["alternative"] = params["alternative"].replace("_", "-")
    if "group_names" in given:
        n = len(kwargs.get("groups") or []) or 2
        kwargs["group_names"] = names_of(params["group_names"], "group_names", n)
    return kwargs


def run_test(call) -> Dict:
    from scitex_stats import run_test as _run_test

    test_id = _test_id(call)
    kwargs = _run_kwargs(test_id, call.params, Budget(value_cap(call)))
    try:
        result = _run_test(
            test_id, plot=False, json_safe=True, embed_inputs=False, **kwargs
        )
    except INPUT_ERRORS as exc:
        raise input_error(exc) from None
    return finite_json(result)


# ------------------------------------------------------------------ recommend

#: ``design`` values and their meaning for each form.
DATA_DESIGNS = {
    "independent": "independent",
    "between": "independent",
    "paired": "paired",
    "within": "paired",
}
CONTEXT_DESIGNS = {
    "independent": "between",
    "between": "between",
    "paired": "within",
    "within": "within",
    "mixed": "mixed",
}
DATA_FIELDS = {"groups", "design", "scale", "group_names", "assume_equal_variance"}
CONTEXT_FIELDS = {
    "n_groups",
    "sample_sizes",
    "outcome_type",
    "design",
    "paired",
    "has_control_group",
    "n_factors",
    "top_k",
}
#: Per-value plot coordinates; one point per input value, so never in the answer.
_PLOT_KEYS = ("qq",)


def _recommend_from_data(params: Dict[str, Any], budget: Budget) -> Dict:
    from scitex_stats import recommend_test

    only(params, DATA_FIELDS, "with groups (the data form)")
    groups = groups_of(params["groups"], "groups", budget)
    design = params.get("design")
    if design is not None and design not in DATA_DESIGNS:
        raise invalid(
            "design must be independent, between, paired or within with groups",
            "design",
        )
    try:
        out = recommend_test(
            groups,
            DATA_DESIGNS.get(design) if design else None,
            scale=params.get("scale"),
            group_names=names_of(params.get("group_names"), "group_names", len(groups)),
            assume_equal_variance=bool(params.get("assume_equal_variance", False)),
        )
    except INPUT_ERRORS as exc:
        raise input_error(exc) from None
    return {
        "mode": "data",
        "recommendation": finite_json(without_keys(out, _PLOT_KEYS)),
    }


def _count(
    params: Dict[str, Any], field: str, low: int, high: int, default: int
) -> int:
    value = params.get(field, default)
    return int(in_range(value, field, low, high))


def _recommend_from_context(params: Dict[str, Any], budget: Budget) -> Dict:
    from scitex_stats import StatContext, recommend_tests

    only(params, CONTEXT_FIELDS, "with n_groups (the design form)")
    n_groups = _count(params, "n_groups", 1, 1_000, 2)
    sizes = params.get("sample_sizes")
    if sizes is None:
        sizes = [30] * n_groups
    sizes = numbers(sizes, "sample_sizes", budget)
    if len(sizes) != n_groups or any(s != int(s) or not 1 <= s <= 1e9 for s in sizes):
        raise invalid("sample_sizes must be n_groups positive integers", "sample_sizes")
    try:
        ctx = StatContext(
            n_groups=n_groups,
            sample_sizes=[int(s) for s in sizes],
            outcome_type=params.get("outcome_type", "continuous"),
            design=CONTEXT_DESIGNS[params.get("design", "between")],
            paired=params.get("paired"),
            has_control_group=bool(params.get("has_control_group", False)),
            n_factors=_count(params, "n_factors", 1, 10, 1),
        )
        names = recommend_tests(ctx, top_k=_count(params, "top_k", 1, 50, 3))
    except INPUT_ERRORS as exc:
        raise input_error(exc) from None
    return {"mode": "design", "recommendations": list(names)}


def recommend(call) -> Dict:
    params = call.params
    has_data, has_context = "groups" in params, "n_groups" in params
    if has_data == has_context:
        raise invalid(
            "send exactly one of groups (recommend from data) or n_groups "
            "(recommend from a design description)",
            "groups",
        )
    budget = Budget(value_cap(call))
    if has_data:
        return _recommend_from_data(params, budget)
    return _recommend_from_context(params, budget)


# EOF
