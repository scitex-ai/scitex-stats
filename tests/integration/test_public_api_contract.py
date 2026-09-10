#!/usr/bin/env python3
"""Public-API contract for the hub Statistics app (compass §12 L450-454).

This is the thin, stable surface the hub's `Statistics` app is allowed to
call. It is a *contract*, not a re-test of feature depth (that is the
job of the per-capability suites under tests/scitex_stats/<module>/). It
pins, per named capability, the top-level namespace and the headline
public symbols, and proves each is importable AND callable — so a future
refactor that buries a capability behind internals, renames a public
symbol, or drops it from a namespace fails loudly here instead of
silently breaking the hub.

Coverage per compass line:
- L452 (keep the UI thin): every capability is reached through the
  top-level `scitex_stats` namespace — the hub imports ONE package.
- L453 (descriptive, tests, effect size, power, post-hoc, corrections):
  each named capability is pinned to its public symbols here.

The six capability namespaces and their headline symbols are asserted as
importable + callable; one representative live call per capability proves
the surface actually works (returns a sane object), not merely that the
name exists.
"""

from __future__ import annotations

import types

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Contract data: capability -> (top-level namespace, headline callable
# symbols). The hub must be able to reach every symbol here via
# `scitex_stats.<namespace>.<symbol>`. `describe`/`run_test`/
# `recommend_tests` are top-level dispatchers covered separately below.
# ---------------------------------------------------------------------------
_CAPABILITIES: dict[str, tuple[str, list[str]]] = {
    "descriptive": (
        "descriptive",
        [
            "describe",
            "mean",
            "std",
            "var",
            "quantile",
            "ci",
            "skewness",
            "kurtosis",
            "zscore",
            "q25",
            "q50",
            "q75",
        ],
    ),
    "tests": (
        "tests",
        [
            "test_ttest_ind",
            "test_ttest_rel",
            "test_ttest_1samp",
            "test_anova",
            "test_anova_rm",
            "test_anova_2way",
            "test_wilcoxon",
            "test_mannwhitneyu",
            "test_kruskal",
            "test_friedman",
            "test_brunner_munzel",
            "test_pearson",
            "test_spearman",
            "test_kendall",
            "test_theilsen",
            "test_chi2",
            "test_fisher",
            "test_mcnemar",
            "test_cochran_q",
            "test_shapiro",
            "test_kendalls_w",
            "test_icc",
        ],
    ),
    "effect_sizes": (
        "effect_sizes",
        [
            "cohens_d",
            "interpret_cohens_d",
            "eta_squared",
            "interpret_eta_squared",
            "cliffs_delta",
            "interpret_cliffs_delta",
            "prob_superiority",
            "interpret_prob_superiority",
            "epsilon_squared",
            "interpret_epsilon_squared",
        ],
    ),
    "power": (
        "power",
        ["power_ttest", "sample_size_ttest"],
    ),
    "posthoc": (
        "posthoc",
        ["posthoc_tukey", "posthoc_games_howell", "posthoc_dunnett"],
    ),
    "correct": (
        "correct",
        [
            "correct_bonferroni",
            "correct_fdr",
            "correct_holm",
            "correct_sidak",
        ],
    ),
}

# Top-level dispatchers the hub is expected to call directly (L452).
_TOP_LEVEL_DISPATCHERS = [
    "run_test",
    "describe",
    "recommend_tests",
    "available_tests",
]


@pytest.fixture
def rng():
    # Arrange
    return np.random.default_rng(42)


@pytest.fixture
def two_groups(rng):
    # Arrange
    x = rng.normal(0.0, 1.0, 30)
    y = rng.normal(0.5, 1.0, 30)
    # Act
    return x, y


@pytest.fixture
def three_groups(rng):
    # Arrange
    a = rng.normal(0.0, 1.0, 25)
    b = rng.normal(0.3, 1.0, 25)
    c = rng.normal(0.8, 1.0, 25)
    # Act
    return [a, b, c]


# ===================================================================
# 1. L452 — one thin top-level surface for the hub
# ===================================================================
class TestTopLevelSurface:
    """The hub imports `scitex_stats` once and reaches every capability
    through the top-level namespace (L452: keep the UI thin)."""

    @pytest.mark.parametrize("name", _TOP_LEVEL_DISPATCHERS)
    def test_top_level_dispatcher_present(self, name):
        # Arrange
        import scitex_stats
        # Act
        obj = getattr(scitex_stats, name)
        # Assert
        assert obj is not None
        assert callable(obj)

    @pytest.mark.parametrize("capability", list(_CAPABILITIES))
    def test_capability_namespace_is_top_level_module(self, capability):
        # Arrange
        import scitex_stats
        # Act
        namespace, _ = _CAPABILITIES[capability]
        obj = getattr(scitex_stats, namespace)
        # Assert
        assert isinstance(obj, types.ModuleType), (
            f"{namespace!r} must be a module on the top-level surface"
        )

    @pytest.mark.parametrize("capability", list(_CAPABILITIES))
    def test_capability_namespace_declares_public_names(self, capability):
        # Arrange
        import scitex_stats
        # Act
        namespace, _ = _CAPABILITIES[capability]
        all_names = list(getattr(getattr(scitex_stats, namespace), "__all__", []))
        # Assert
        assert all_names, f"{namespace} must declare a non-empty __all__"

    def test_version_string(self):
        # Arrange
        import scitex_stats
        # Act
        # Assert
        assert isinstance(scitex_stats.__version__, str)
        assert scitex_stats.__version__


# ===================================================================
# 2. L453 — named capability symbols are public AND callable
# ===================================================================
@pytest.mark.parametrize(
    "capability, namespace, symbols",
    [(cap, ns, syms) for cap, (ns, syms) in _CAPABILITIES.items()],
)
class TestCapabilitySymbols:
    """Every headline symbol the hub consumes is reachable via the
    top-level namespace and is callable (a live function, not a stub)."""

    def test_symbol_in_namespace_public_names(self, capability, namespace, symbols):
        # Arrange
        import scitex_stats
        pub = set(getattr(getattr(scitex_stats, namespace), "__all__", []))
        # Act
        missing = [s for s in symbols if s not in pub]
        # Assert
        assert not missing, f"{namespace}: not in __all__: {missing}"

    def test_symbols_are_callable(self, capability, namespace, symbols):
        # Arrange
        import scitex_stats
        mod = getattr(scitex_stats, namespace)
        # Act
        not_callable = [s for s in symbols if not callable(getattr(mod, s, None))]
        # Assert
        assert not not_callable, (
            f"{namespace}: symbols not callable: {not_callable}"
        )


# ===================================================================
# 3. L453 — one representative live call per capability (the surface works)
# ===================================================================
class TestCapabilityLive:
    """Prove the pinned surface actually executes, not just imports."""

    def test_descriptive_mean_runs(self, rng):
        # Arrange
        from scitex_stats import descriptive
        x = rng.normal(10.0, 2.0, 40)
        # Act
        m = descriptive.mean(x)
        # Assert
        assert np.isfinite(float(m))
        assert 8.0 < float(m) < 12.0

    def test_describe_tuple_runs(self, rng):
        # Arrange
        import scitex_stats as ss
        x = rng.normal(0.0, 1.0, 100)
        # Act
        values, names = ss.describe(x)
        # Assert
        assert isinstance(names, list)
        assert "mean" in names

    def test_tests_dispatcher_run(self, two_groups):
        # Arrange
        import scitex_stats as ss
        x, y = two_groups
        # Act
        result = ss.run_test("ttest_ind", data=x, data2=y)
        # Assert
        assert isinstance(result, dict)
        assert "statistic" in result
        assert "pvalue" in result or "p_value" in result

    def test_tests_anova_direct(self, three_groups):
        # Arrange
        from scitex_stats import tests
        # Act — groups keyword is the documented entry (see README Figure 1)
        result = tests.test_anova(groups=three_groups)
        # Assert
        assert isinstance(result, dict)
        assert "statistic" in result

    def test_effect_sizes_cohens_d_runs(self, two_groups):
        # Arrange
        from scitex_stats import effect_sizes
        x, y = two_groups
        # Act
        d = effect_sizes.cohens_d(x, y)
        # Assert
        assert np.isfinite(float(d))

    def test_power_sample_size_runs(self):
        # Arrange
        from scitex_stats import power
        # Act
        n = power.sample_size_ttest(effect_size=0.5, alpha=0.05, power=0.8)
        # Assert
        # sample_size_ttest returns (n1, n2) for a two-sample design
        assert isinstance(n, (int, tuple))
        if isinstance(n, tuple):
            assert all(k >= 1 for k in n)

    def test_posthoc_tukey_runs(self, three_groups):
        # Arrange
        from scitex_stats import posthoc
        # Act
        out = posthoc.posthoc_tukey(three_groups)
        # Assert
        assert out is not None

    def test_correct_fdr_runs(self, three_groups):
        # Arrange
        import scitex_stats as ss
        from scitex_stats import correct
        import pandas as pd
        # Build a small results frame of p-values from three pairwise t-tests
        a, b, c = three_groups
        pvals = [
            float(ss.run_test("ttest_ind", data=a, data2=b)["pvalue"]),
            float(ss.run_test("ttest_ind", data=a, data2=c)["pvalue"]),
            float(ss.run_test("ttest_ind", data=b, data2=c)["pvalue"]),
        ]
        df = pd.DataFrame({"test": ["ab", "ac", "bc"], "pvalue": pvals})
        # Act
        out = correct.correct_fdr(df)
        # Assert
        assert out is not None


# ===================================================================
# 4. Umbrella — the six capabilities are ALL present together (L453 "etc.")
# ===================================================================
class TestAllSixCapabilitiesPresent:
    """The compass names six tools; all six must be simultaneously
    reachable on the thin surface. A missing capability is a contract
    break, not a soft miss."""

    def test_six_namespaces_all_importable(self):
        # Arrange
        import scitex_stats
        expected = {
            "descriptive",
            "tests",
            "effect_sizes",
            "power",
            "posthoc",
            "correct",
        }
        # Act
        present = {
            ns
            for ns in expected
            if isinstance(getattr(scitex_stats, ns, None), types.ModuleType)
        }
        # Assert
        assert present == expected, f"missing capabilities: {expected - present}"

    def test_contract_covers_six_capabilities(self):
        # Arrange
        expected = {
            "descriptive",
            "tests",
            "effect_sizes",
            "power",
            "posthoc",
            "correct",
        }
        # Act
        # Assert
        assert set(_CAPABILITIES) == expected
