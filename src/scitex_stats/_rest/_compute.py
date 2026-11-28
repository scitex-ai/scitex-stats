#!/usr/bin/env python3
# File: src/scitex_stats/_rest/_compute.py

"""Handlers of the stateless calculations: descriptives, effect sizes, power,
corrections and bootstrap confidence intervals.

Each one is a thin wrapper over the package function of the same job; every
choice the caller makes is a closed enum declared on the operation (no
callable, module or attribute name is ever taken from the request).
"""

from __future__ import annotations

from typing import Dict

try:  # PS-233: scitex-sdk is the [server] extra
    from scitex_sdk.app.api_exec import ApiProblem
except ImportError as exc:
    raise ImportError(
        "scitex_stats._rest needs scitex-sdk, which is not installed. "
        "Install the optional stack: pip install 'scitex-stats[server]'"
    ) from exc

from ._handlers import INPUT_ERRORS, finite, input_error
from ._inputs import Budget, finite_json, in_range, invalid, numbers, value_cap

#: ``descriptive.describe`` statistic names (nan-safe forms), in output order.
DESCRIPTIVE_STATISTICS = (
    "count",
    "mean",
    "std",
    "var",
    "min",
    "q25",
    "median",
    "q75",
    "max",
    "skewness",
    "kurtosis",
)
EFFECT_SIZE_MEASURES = ("cohens_d", "hedges_g", "glass_delta", "cliffs_delta")
POWER_TEST_TYPES = ("ttest", "anova", "correlation", "chi2")
CORRECTION_METHODS = ("bonferroni", "holm", "sidak", "fdr_bh", "fdr_by")
BOOTSTRAP_STATISTICS = ("median", "mean")
BOOTSTRAP_METHODS = ("percentile", "basic", "bca")

#: Bootstrap resamples per call for a member (public: the profile's max_n_boot).
MAX_N_RESAMPLES = 100_000
#: values x resamples per call: scipy resamples in one array of this many floats.
MAX_BOOTSTRAP_WORK = 20_000_000
#: BCa's jackknife builds an n x (n - 1) array, so it is bounded on n itself.
MAX_BCA_VALUES = 5_000
#: The default bootstrap resamples when the call names none.
PUBLIC_N_RESAMPLES = 10_000
RESAMPLING_TOO_LARGE = "stats.resampling_too_large"


def run_descriptives(call) -> Dict:
    from scitex_stats.descriptive import describe

    params = call.params
    data = numbers(params["data"], "data", Budget(value_cap(call)))
    wanted = params.get("statistics") or list(DESCRIPTIVE_STATISTICS)
    if not isinstance(wanted, list) or not all(
        s in DESCRIPTIVE_STATISTICS for s in wanted
    ):
        raise invalid(
            f"statistics must be an array drawn from {', '.join(DESCRIPTIVE_STATISTICS)}",
            "statistics",
        )
    import numpy as np

    wanted = list(dict.fromkeys(wanted))
    values, names = describe(np.asarray(data, dtype=float), funcs=wanted)
    return finite_json(
        {"n": len(data), "statistics": dict(zip(names, np.asarray(values).tolist()))}
    )


def run_effect_size(call) -> Dict:
    from scitex_stats.effect_sizes import effect_size

    params = call.params
    budget = Budget(value_cap(call))
    data = numbers(params["data"], "data", budget, min_len=2)
    data2 = numbers(params["data2"], "data2", budget, min_len=2)
    try:
        out = effect_size(data, data2, measure=params.get("measure", "cohens_d"))
    except INPUT_ERRORS as exc:
        raise input_error(exc) from None
    return finite_json(out)


def run_power_analysis(call) -> Dict:
    from scitex_stats.power import power_analysis

    p = call.params
    effect = finite(p["effect_size"], "effect_size")
    if effect == 0:
        raise invalid("effect_size must be non-zero", "effect_size")
    test_type = p.get("test_type", "ttest")
    if test_type == "correlation":
        in_range(abs(effect), "effect_size", 0, 1, open_low=True, open_high=True)
    n = p.get("n")
    kwargs = dict(
        test_type=test_type,
        effect_size=effect,
        alpha=in_range(
            p.get("alpha", 0.05), "alpha", 0, 1, open_low=True, open_high=True
        ),
        power=in_range(
            p.get("power", 0.8), "power", 0, 1, open_low=True, open_high=True
        ),
        n=int(in_range(n, "n", 4 if test_type == "correlation" else 2, 10_000_000))
        if n is not None
        else None,
        n_groups=int(in_range(p.get("n_groups", 2), "n_groups", 2, 1_000)),
        ratio=in_range(p.get("ratio", 1.0), "ratio", 0, 100, open_low=True),
    )
    try:
        out = power_analysis(**kwargs)
    except INPUT_ERRORS as exc:
        raise input_error(exc) from None
    return finite_json(out)


def run_correction(call) -> Dict:
    from scitex_stats.correct import correct_pvalues

    p = call.params
    pvalues = numbers(p["pvalues"], "pvalues", Budget(value_cap(call)))
    if any(not 0 <= v <= 1 for v in pvalues):
        raise invalid("pvalues must lie in [0, 1]", "pvalues")
    alpha = in_range(p.get("alpha", 0.05), "alpha", 0, 1, open_low=True, open_high=True)
    try:
        out = correct_pvalues(pvalues, method=p.get("method", "fdr_bh"), alpha=alpha)
    except INPUT_ERRORS as exc:
        raise input_error(exc) from None
    return finite_json(out)


def _resampling_limit(call) -> int:
    limits = call.limits
    cap = limits.get("max_n_boot") if limits is not None else None
    return min(MAX_N_RESAMPLES, cap or MAX_N_RESAMPLES)


def _too_large(detail: str, limit: str, value: int) -> ApiProblem:
    return ApiProblem(
        413, RESAMPLING_TOO_LARGE, detail, extra={"limit": limit, limit: value}
    )


def run_bootstrap_ci(call) -> Dict:
    from scitex_stats.descriptive import bootstrap_ci

    p = call.params
    data = numbers(p["data"], "data", Budget(value_cap(call)), min_len=2)
    cap = _resampling_limit(call)
    n_resamples = p.get("n_resamples", min(PUBLIC_N_RESAMPLES, cap))
    if n_resamples < 1:
        raise invalid("n_resamples must be a positive integer", "n_resamples")
    if n_resamples > cap:
        raise _too_large(
            f"n_resamples may be at most {cap} for this call", "max_n_boot", cap
        )
    if len(data) * n_resamples > MAX_BOOTSTRAP_WORK:
        raise _too_large(
            f"len(data) x n_resamples may be at most {MAX_BOOTSTRAP_WORK}",
            "max_bootstrap_work",
            MAX_BOOTSTRAP_WORK,
        )
    method = p.get("method", "percentile")
    if method == "bca" and len(data) > MAX_BCA_VALUES:
        raise _too_large(
            f"method bca takes at most {MAX_BCA_VALUES} values",
            "max_bca_values",
            MAX_BCA_VALUES,
        )
    seed = int(in_range(p.get("seed", 42), "seed", 0, 2**32 - 1))
    try:
        out = bootstrap_ci(
            data,
            p.get("statistic", "median"),
            confidence=in_range(
                p.get("confidence", 0.95),
                "confidence",
                0,
                1,
                open_low=True,
                open_high=True,
            ),
            n_resamples=int(n_resamples),
            method=method,
            seed=seed,
        )
    except INPUT_ERRORS as exc:
        raise input_error(exc) from None
    return finite_json(out)


# EOF
