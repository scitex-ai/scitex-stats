#!/usr/bin/env python3
# File: src/scitex_stats/_rest/__init__.py

"""The stats REST API and MCP tools, declared once (scitex-sdk ``ApiPlugin``).

Published under the ``scitex.apis`` entry point as ``stats``; any SciTeX host
serves it at ``/api/v1/stats/`` through ``scitex_sdk.app.api_serve`` with no
stats-specific host code, and :func:`register_mcp` turns the same operations
into MCP tools named ``stats_<resource>_<verb>``.

==========================  =================================================  ========
operation                   REST                                               cost
==========================  =================================================  ========
stats.tests.list            GET  /api/v1/stats/tests                (public)   light
stats.tests.get             GET  /api/v1/stats/tests/{test_id}      (public)   light
stats.tests.run             POST /api/v1/stats/tests/{test_id}/run             standard
stats.tests.recommend       POST /api/v1/stats/tests/recommend                 light
stats.descriptives.run      POST /api/v1/stats/descriptives/run                standard
stats.effect-sizes.run      POST /api/v1/stats/effect-sizes/run                standard
stats.power-analyses.run    POST /api/v1/stats/power-analyses/run              light
stats.corrections.run       POST /api/v1/stats/corrections/run                 light
stats.bootstrap-cis.run     POST /api/v1/stats/bootstrap-cis/run               standard
==========================  =================================================  ========

Every POST is a read-only calculation (scope ``stats:<resource>:read``, no
idempotency key) with ``exposure="public_eligible"``: a host may open it to
anonymous callers through its public-tier configuration. A public-class call
is held to that profile (``max_values``, ``max_n_boot``); every caller is held
to the hard caps in :mod:`._inputs` and :mod:`._compute`.

This module needs scitex-sdk (the ``server`` extra); nothing in
``scitex_stats`` imports it, so the plain package never does. A host loads it
through the entry point.
"""

from __future__ import annotations

try:
    from scitex_sdk.app.api_ops import ApiOperation, build_plugin
    from scitex_sdk.app.api_plugin import ApiError, ApiField
except ImportError as exc:  # PS-233: fail loudly with the extra to install
    raise ImportError(
        "scitex_stats._rest needs scitex-sdk, which is not installed. "
        "Install the optional stack: pip install 'scitex-stats[server]'"
    ) from exc

from ._compute import (
    BOOTSTRAP_METHODS,
    BOOTSTRAP_STATISTICS,
    CORRECTION_METHODS,
    EFFECT_SIZE_MEASURES,
    POWER_TEST_TYPES,
    RESAMPLING_TOO_LARGE,
)
from ._handlers import TEST_NOT_FOUND
from ._inputs import INVALID, TOO_MANY

P = "stats"
H = "scitex_stats._rest."
NOT_FOUND = ApiError(TEST_NOT_FOUND, 404, "No test with this name")
BAD_INPUT = ApiError(INVALID, 400, "The inputs do not fit the calculation")
TOO_MANY_VALUES = ApiError(TOO_MANY, 413, "More numeric values than this call may send")
TOO_MUCH_RESAMPLING = ApiError(
    RESAMPLING_TOO_LARGE, 413, "More bootstrap work than this call may ask for"
)
DATA_ERRORS = (BAD_INPUT, TOO_MANY_VALUES)
CALC = dict(item=False, read_only=True, exposure="public_eligible")

DATA = ApiField("data", "array", False, "Numbers: the (first) sample")
DATA2 = ApiField("data2", "array", False, "Numbers: the second sample")
GROUPS = ApiField(
    "groups", "array", False, "Array of number arrays: one per group (or table row)"
)
GROUP_NAMES = ApiField("group_names", "array", False, "Labels, one per group")
ALPHA = ApiField("alpha", "number", False, "Significance level in (0, 1); default 0.05")

OPERATIONS = (
    ApiOperation(
        P,
        "tests",
        "list",
        H + "_handlers:list_tests",
        summary=(
            "Statistical tests this host runs: id, aliases, description, and the "
            "fields each one reads"
        ),
        paginated=True,
        default_limit=50,
        max_limit=100,
        public=True,
    ),
    # Declared before tests.get on purpose: the SDK mounts routes in
    # declaration order, so the literal tests/recommend must precede the
    # tests/{test_id} pattern or POST tests/recommend answers 405.
    ApiOperation(
        P,
        "tests",
        "recommend",
        H + "_handlers:recommend",
        summary=(
            "Recommend a test: from data (groups) with the decision path, or from "
            "a design description (n_groups, sample_sizes, outcome_type)"
        ),
        params=(
            ApiField("groups", "array", False, "Data form: one number array per group"),
            ApiField(
                "design",
                "string",
                False,
                "independent|between or paired|within; design form also mixed",
                enum=("independent", "between", "paired", "within", "mixed"),
            ),
            ApiField(
                "scale",
                "string",
                False,
                "Data form: measurement scale",
                enum=("continuous", "ordinal", "categorical"),
            ),
            GROUP_NAMES,
            ApiField(
                "assume_equal_variance",
                "boolean",
                False,
                "Data form: Student's instead of Welch's t when variances agree",
            ),
            ApiField("n_groups", "integer", False, "Design form: number of groups"),
            ApiField("sample_sizes", "array", False, "Design form: size of each group"),
            ApiField(
                "outcome_type",
                "string",
                False,
                "Design form: outcome variable type",
                enum=("continuous", "ordinal", "binary", "categorical"),
            ),
            ApiField("paired", "boolean", False, "Design form: explicitly paired"),
            ApiField(
                "has_control_group",
                "boolean",
                False,
                "Design form: a control group exists",
            ),
            ApiField("n_factors", "integer", False, "Design form: number of factors"),
            ApiField("top_k", "integer", False, "Design form: how many tests (1-50)"),
        ),
        errors=DATA_ERRORS,
        **CALC,
    ),
    ApiOperation(
        P,
        "tests",
        "get",
        H + "_handlers:get_test",
        summary="One statistical test (id or alias): description and the fields it reads",
        errors=(NOT_FOUND,),
        public=True,
    ),
    ApiOperation(
        P,
        "tests",
        "run",
        H + "_handlers:run_test",
        summary=(
            "Run one test on inline data; returns statistic, p-value, effect size, "
            "descriptives and a provenance receipt (input hashes)"
        ),
        params=(
            DATA,
            DATA2,
            GROUPS,
            ApiField(
                "alternative",
                "string",
                False,
                "Alternative hypothesis (two-sample and paired tests); default two_sided",
                enum=("two_sided", "greater", "less"),
            ),
            ApiField("popmean", "number", False, "Hypothesised mean (ttest_1samp)"),
            GROUP_NAMES,
        ),
        errors=(NOT_FOUND, *DATA_ERRORS),
        item=True,
        read_only=True,
        exposure="public_eligible",
        compute_cost="standard",
    ),
    ApiOperation(
        P,
        "descriptives",
        "run",
        H + "_compute:run_descriptives",
        summary="Descriptive statistics of one sample (mean, SD, quartiles, ...)",
        params=(
            ApiField("data", "array", True, "Numbers: the sample"),
            ApiField(
                "statistics",
                "array",
                False,
                "Subset of count, mean, std, var, min, q25, median, q75, max, "
                "skewness, kurtosis (default all)",
            ),
        ),
        errors=DATA_ERRORS,
        compute_cost="standard",
        **CALC,
    ),
    ApiOperation(
        P,
        "effect-sizes",
        "run",
        H + "_compute:run_effect_size",
        summary="Effect size of data versus data2, with interpretation (and 95% CI)",
        params=(
            ApiField("data", "array", True, "Numbers: the first group"),
            ApiField("data2", "array", True, "Numbers: the second group"),
            ApiField(
                "measure",
                "string",
                False,
                "Effect size measure",
                enum=EFFECT_SIZE_MEASURES,
            ),
        ),
        errors=DATA_ERRORS,
        compute_cost="standard",
        **CALC,
    ),
    ApiOperation(
        P,
        "power-analyses",
        "run",
        H + "_compute:run_power_analysis",
        summary="Statistical power (given n) or the required sample size (given power)",
        params=(
            ApiField("test_type", "string", False, "Design", enum=POWER_TEST_TYPES),
            ApiField(
                "effect_size",
                "number",
                True,
                "Cohen's d (ttest), f (anova), r (correlation) or w (chi2)",
            ),
            ALPHA,
            ApiField("power", "number", False, "Target power in (0, 1); default 0.8"),
            ApiField(
                "n", "integer", False, "Sample size per group; omit to solve for it"
            ),
            ApiField("n_groups", "integer", False, "Groups (anova) or cells (chi2)"),
            ApiField("ratio", "number", False, "n2 / n1 (ttest); default 1"),
        ),
        errors=(BAD_INPUT,),
        **CALC,
    ),
    ApiOperation(
        P,
        "corrections",
        "run",
        H + "_compute:run_correction",
        summary="Correct p-values for multiple comparisons",
        params=(
            ApiField("pvalues", "array", True, "Raw p-values in [0, 1]"),
            ApiField("method", "string", False, "Correction", enum=CORRECTION_METHODS),
            ALPHA,
        ),
        errors=DATA_ERRORS,
        **CALC,
    ),
    ApiOperation(
        P,
        "bootstrap-cis",
        "run",
        H + "_compute:run_bootstrap_ci",
        summary="Seeded bootstrap confidence interval of the median or mean",
        params=(
            ApiField("data", "array", True, "Numbers: the sample (at least 2)"),
            ApiField(
                "statistic", "string", False, "Statistic", enum=BOOTSTRAP_STATISTICS
            ),
            ApiField("confidence", "number", False, "Level in (0, 1); default 0.95"),
            ApiField(
                "n_resamples",
                "integer",
                False,
                "Resamples (default 10000; public calls at most 10000)",
            ),
            ApiField("method", "string", False, "Interval", enum=BOOTSTRAP_METHODS),
            ApiField("seed", "integer", False, "Seed in [0, 2^32 - 1]; default 42"),
        ),
        errors=(*DATA_ERRORS, TOO_MUCH_RESAMPLING),
        compute_cost="standard",
        **CALC,
    ),
)

PLUGIN = build_plugin(P, "SciTeX Stats API", "1", OPERATIONS)


def register_mcp(mcp) -> list:
    """Register every operation as an MCP tool (``stats_<resource>_<verb>``)."""
    from scitex_sdk.app.api_mcp import register_fastmcp

    return register_fastmcp(mcp, PLUGIN)


__all__ = ["OPERATIONS", "PLUGIN", "register_mcp"]

# EOF
