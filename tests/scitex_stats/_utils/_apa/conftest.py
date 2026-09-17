"""Shared fixtures for the scitex_stats._utils._apa tests.

The APA package renders one line per test family, so the same dataset set
drives every module's cases. Kept here (not per-module) so the rule table,
the renderer and the validator are all checked against ONE set of results.
"""

import pytest

from scitex_stats import run_test

A = [5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7]
B = [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2]
B2 = [6.3, 4.8, 7.1, 7.9, 5.6, 6.9, 8.4, 5.2]
C = [5.9, 6.2, 5.5, 6.4, 6.1, 5.8, 6.0, 6.3]
TABLE = [[12, 5], [4, 9]]

CASES = {
    "ttest_ind": dict(data=A, data2=B),
    "ttest_welch": dict(data=A, data2=B2),
    "ttest_rel": dict(data=A, data2=B),
    "ttest_1samp": dict(data=A, popmean=5),
    "mannwhitneyu": dict(data=A, data2=B2),
    "brunner_munzel": dict(data=A, data2=B2),
    "ks_2samp": dict(data=A, data2=B2),
    "ks_1samp": dict(data=A),
    "wilcoxon": dict(data=A, data2=B2),
    "anova": dict(groups=[A, B, C]),
    "kruskal": dict(groups=[A, B, C]),
    "friedman": dict(groups=[A, B, C]),
    "pearson": dict(data=A, data2=B),
    "spearman": dict(data=A, data2=B),
    "kendall": dict(data=A, data2=B),
    "shapiro": dict(data=A),
    "chi2": dict(groups=TABLE),
    "fisher": dict(groups=TABLE),
}

EXPECTED = {
    "ttest_ind": "t(14) = −6.35, p < .001, d = −3.18, 95% CI [−4.65, −1.70], n₁ = 8, n₂ = 8",
    "ttest_welch": "t(8.21) = −2.25, p = .054, d = −1.12, 95% CI [−2.18, −0.07], n₁ = 8, n₂ = 8",
    "ttest_rel": "t(7) = −7.28, p < .001, d_z = −2.58, 95% CI [−4.01, −1.14], n = 8",
    "ttest_1samp": "t(7) = 3.46, p = .011, d = 1.22, 95% CI [0.31, 2.14], n = 8",
    "mannwhitneyu": "U = 17.00, z = −1.58, p = .127, r_rb = −.47, n₁ = 8, n₂ = 8",
    "brunner_munzel": "W_BM(8.06) = 1.61, p = .145, P(X > Y) = .25, n₁ = 8, n₂ = 8",
    "ks_2samp": "D = .62, p = .087, n₁ = 8, n₂ = 8",
    "ks_1samp": "D = 1.00, p < .001, n = 8",
    "wilcoxon": "T = 6.00, z = −1.68, p = .102, r_rb = −.67, n = 8",
    "anova": "F(2, 21) = 23.36, p < .001, η² = .69, N = 24",
    "kruskal": "H(2) = 16.72, p < .001, ε² = .70, N = 24",
    "friedman": "χ²_F(2, N = 8) = 14.25, p < .001, W = .89",
    "pearson": "r(6) = .24, 95% CI [−.56, .81], p = .569",
    "spearman": "rₛ(6) = .33, p = .420",
    "kendall": "τ_b = .21, p = .548, N = 8",
    "shapiro": "W = .97, p = .921, n = 8",
    "chi2": "χ²(1, N = 30) = 3.23, p = .072, V = .33",
    "fisher": "p = .063, OR = 5.40, 95% CI [1.12, 26.04], N = 30",
}


@pytest.fixture(scope="module")
def results():
    return {name: run_test(name, **kwargs) for name, kwargs in CASES.items()}


@pytest.fixture(scope="module")
def expected():
    return EXPECTED
