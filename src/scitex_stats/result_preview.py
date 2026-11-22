"""Read SciTeX Stats evidence without rerunning tests or loading data files.

The caller owns access and hash checks. The provider owns interpretation of
native SciTeX Stats results, including the GUI's run-all response.
"""

from __future__ import annotations

import json
import math

from ._provenance import SCHEMA as RECEIPT_SCHEMA

COMPARISON_SCHEMA = "scitex-stats/comparison/v1"


def _missing_effect_sizes(comparisons):
    missing = []
    for group in comparisons.values():
        rows = _mapping(group).get("results")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or row.get("error"):
                continue
            value = row.get("effect_size")
            name = row.get("effect_size_metric")
            finite = type(value) is int or (type(value) is float and math.isfinite(value))
            if not finite or not isinstance(name, str) or not name.strip():
                missing.append(str(row.get("method") or row.get("test_method") or row.get("test") or "Test"))
    return missing


def comparison_artifact(comparisons: dict) -> dict:
    """Package analyses and require a named effect size for every result."""
    if not comparisons or any(
        not isinstance(rows := _mapping(group).get("results"), list)
        or not rows or any(not isinstance(row, dict) for row in rows)
        for group in comparisons.values()
    ):
        raise ValueError("Each comparison requires a nonempty results list")
    if missing := _missing_effect_sizes(comparisons):
        from .reporting import IncompleteReportError

        raise IncompleteReportError("Effect size required for " + ", ".join(missing))
    return {"schema": COMPARISON_SCHEMA, "comparisons": comparisons}


def _preview(comparisons):
    return {"comparisons": comparisons, "missing_effect_sizes": _missing_effect_sizes(comparisons)}


def _invalid_constant(value):
    raise ValueError(value)


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(value)
    return number


def _has_receipt(data):
    receipt = data.get("provenance") if isinstance(data, dict) else None
    return isinstance(receipt, dict) and receipt.get("schema") == RECEIPT_SCHEMA


def _canonical_result(analysis):
    if not isinstance(analysis, dict):
        return None
    method, result = analysis.get("method"), analysis.get("results")
    if not isinstance(method, dict) or not isinstance(result, dict):
        return None
    if not isinstance(method.get("name"), str) or "statistic" not in result or "p_value" not in result:
        return None
    row = {**result, "test_method": method["name"], "alpha": result.get("alpha", .05)}
    effect = result.get("effect_size")
    if isinstance(effect, dict):
        row.update(effect_size=effect.get("value"), effect_size_metric=effect.get("name"))
        if effect.get("ci_lower") is not None and effect.get("ci_upper") is not None:
            row["effect_ci"] = [effect["ci_lower"], effect["ci_upper"]]
    return row


def _mapping(value):
    return value if isinstance(value, dict) else {}


def preview_result(text: str) -> dict | None:
    """Decode a Stats artifact into comparison sections for a consumer UI.

    Supported inputs are a native receipt-bearing `run_test` result, a
    `run_all_applicable` result, a canonical Stats bundle's `stats.json`
    member, or a `comparison_artifact` result. Unknown JSON returns None.
    The returned structure carries reported quantities and never substitutes
    estimates for missing measurements.
    """
    try:
        data = json.loads(text, parse_constant=_invalid_constant, parse_float=_finite_float)
    except (ValueError, RecursionError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema") == COMPARISON_SCHEMA and isinstance(data.get("comparisons"), dict):
        return _preview(data["comparisons"])
    if _has_receipt(data):
        return _preview({"result": {"alpha": data.get("alpha"), "results": [data]}})
    results = data.get("results")
    if (data.get("primary_source") in ("pre-registered", "recommend_test")
        and isinstance(results, list) and any(_has_receipt(row) for row in results)
        and isinstance(recommendation := data.get("recommendation"), dict)):
        thresholds = _mapping(recommendation.get("thresholds"))
        checks = _mapping(recommendation.get("checks"))
        agreement = _mapping(data.get("agreement"))
        return _preview({"analysis": {
            "alpha": thresholds.get("alpha"),
            "primary_test": data.get("primary_test"),
            "primary_source": data["primary_source"],
            "recommendation": recommendation.get("primary"),
            "results": results,
            "assumptions": checks.get("expected_counts"),
            "checks": checks,
            "agreement": agreement.get("summary"),
        }})
    analyses = data.get("analyses")
    if isinstance(analyses, list) and analyses:
        rows = [_canonical_result(analysis) for analysis in analyses]
        if all(row is not None for row in rows):
            return _preview({"analysis": {"results": rows}})
    return None
