#!/usr/bin/env python3
# File: scitex_stats/_utils/_apa/_rules.py
"""Per-test APA 7 reporting rules: the one table the formatter and validator share.

Section numbers refer to the Publication Manual of the APA, 7th ed. (2020):
§6.36 decimal fractions, §6.43 statistics in text, §6.44 symbols and
abbreviations (Table 6.5), §6.45 spacing and punctuation. Where APA gives no
explicit template the rule names the source it follows (``reference``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

# df layouts: "none", "one" -> (14), "two" -> (2, 27), "one_N" -> (2, N = 30)
# sample layouts: "n1n2" -> n₁ = 8, n₂ = 8; "n"; "N"; "none" (df or parentheses carry it)
# center: descriptive statistics that accompany the test ("mean" -> M, SD; "median" -> Mdn, IQR)


@dataclass(frozen=True)
class TestRule:
    key: str
    name: str
    pattern: str
    symbol: Optional[str]
    df: str = "none"
    sample: str = "none"
    center: str = "mean"
    bounded_stat: bool = False
    show_statistic: bool = True
    z: bool = False
    effect_required: bool = True
    reference: str = "APA 7 §6.43"
    example: str = ""


RULES: Tuple[TestRule, ...] = (
    TestRule("ttest_welch", "Welch's t-test", r"welch", "t", "one", "n1n2",
             reference="APA 7 §6.43 (t with df); fractional df to two decimals, §6.36",
             example="t(8.21) = −2.25, p = .054, d = −1.12, 95% CI [−2.18, −0.07], n₁ = 8, n₂ = 8"),
    TestRule("ttest_ind", "Student's t-test", r"student|t-test \(independent\)", "t", "one", "n1n2",
             reference="APA 7 §6.43 (t with df), Table 6.5 (d)",
             example="t(14) = −6.35, p < .001, d = −3.18, 95% CI [−4.65, −1.70], n₁ = 8, n₂ = 8"),
    TestRule("ttest_rel", "Paired t-test", r"paired t", "t", "one", "n",
             reference="APA 7 §6.43; d_z for paired designs (Lakens, 2013)",
             example="t(7) = −7.28, p < .001, d_z = −2.58, 95% CI [−4.01, −1.14], n = 8"),
    TestRule("ttest_1samp", "One-sample t-test", r"one-sample t", "t", "one", "n",
             reference="APA 7 §6.43",
             example="t(7) = 3.46, p = .011, d = 1.22, 95% CI [0.31, 2.14], n = 8"),
    TestRule("mannwhitneyu", "Mann–Whitney U test", r"mann", "U", "none", "n1n2", "median", z=True,
             reference="APA 7 Table 6.5 (U); z and r as in Field (2018, ch. 7)",
             example="U = 17.00, z = −1.58, p = .127, r_rb = −.47, n₁ = 8, n₂ = 8"),
    TestRule("brunner_munzel", "Brunner–Munzel test", r"brunner", "W_BM", "one", "n1n2", "median",
             reference="Brunner & Munzel (2000): W^BM ~ t(df); layout per APA 7 §6.43",
             example="W_BM(8.06) = 1.61, p = .145, P(X > Y) = .25, n₁ = 8, n₂ = 8"),
    TestRule("ks_2samp", "Kolmogorov–Smirnov test (2-sample)", r"kolmogorov.*2-sample", "D", "none", "n1n2",
             "median", bounded_stat=True, effect_required=False,
             reference="APA 7 §6.36 (D ≤ 1: no leading zero), §6.43",
             example="D = .62, p = .087, n₁ = 8, n₂ = 8"),
    TestRule("ks_1samp", "Kolmogorov–Smirnov test (1-sample)", r"kolmogorov.*1-sample", "D", "none", "n",
             "median", bounded_stat=True, effect_required=False,
             reference="APA 7 §6.36, §6.43", example="D = 1.00, p < .001, n = 8"),
    TestRule("wilcoxon", "Wilcoxon signed-rank test", r"wilcoxon", None, "none", "n", "median", z=True,
             reference="APA 7 Table 6.5 (T: Wilcoxon); z and r as in Field (2018, ch. 7)",
             example="T = 6.00, z = −1.68, p = .102, r_rb = −.67, n = 8"),
    TestRule("anova", "One-way ANOVA", r"one-way anova", "F", "two", "N",
             reference="APA 7 §6.43 (F(2, 27)), Table 6.5 (η²)",
             example="F(2, 21) = 23.36, p < .001, η² = .69, N = 24"),
    TestRule("kruskal", "Kruskal–Wallis H test", r"kruskal", "H", "one", "N", "median",
             reference="APA 7 Table 6.5 (H); df = k − 1 as for χ² (§6.43)",
             example="H(2) = 16.72, p < .001, ε² = .70, N = 24"),
    TestRule("friedman", "Friedman test", r"friedman", "χ²_F", "one_N", "none", "median",
             reference="APA 7 §6.43 χ² layout with N = subjects; χ²_F per Field (2018, ch. 7)",
             example="χ²_F(2, N = 8) = 14.25, p < .001, W = .89"),
    TestRule("pearson", "Pearson correlation", r"pearson", "r", "one", "none", bounded_stat=True,
             reference="APA 7 §6.43 (r(28) = .45, df = N − 2), §6.36 (no leading zero)",
             example="r(6) = .24, 95% CI [−.56, .81], p = .569"),
    TestRule("spearman", "Spearman rank correlation", r"spearman", "r_s", "one", "none", "median",
             bounded_stat=True,
             reference="APA 7 Table 6.5 (r_s: Spearman rank-order correlation); df = N − 2",
             example="rₛ(6) = .33, p = .420"),
    TestRule("kendall", "Kendall's tau", r"kendall'?s tau", None, "none", "N", "median", bounded_stat=True,
             reference="APA 7 Table 6.5 (τ: Kendall's tau); Greek upright, §6.44",
             example="τ_b = .21, p = .548, N = 8"),
    TestRule("shapiro", "Shapiro–Wilk test", r"shapiro", "W", "none", "n", bounded_stat=True,
             effect_required=False, reference="APA 7 §6.36 (W ≤ 1), §6.43",
             example="W = .97, p = .921, n = 8"),
    TestRule("chi2", "Chi-square test of independence", r"chi-square", "χ²", "one_N", "none",
             reference="APA 7 §6.43: χ²(4, N = 90) = 0.89, p = .926",
             example="χ²(1, N = 30) = 3.23, p = .072, V = .33"),
    TestRule("fisher", "Fisher's exact test", r"fisher", "OR", "none", "N", show_statistic=False,
             reference="APA 7 §6.43 (exact p), Table 6.5 (OR), CI §6.43",
             example="p = .063, OR = 5.40, 95% CI [1.12, 26.04], N = 30"),
)

GENERIC = TestRule("generic", "Statistical test", r"$^", None, "one", "none")

# Effect-size metric (as the tests name it) -> APA symbol string (parse_symbol syntax).
EFFECT_SYMBOLS: Tuple[Tuple[str, str], ...] = (
    (r"^cohen'?s d \(paired\)$", "d_z"),
    (r"^cohen'?s d", "d"),
    (r"^hedges'? ?g", "g"),
    (r"^rank[- ]biserial", "r_rb"),
    (r"^partial[ _-]eta[ _-]?squared$", "η²_p"),
    (r"^eta[ _-]?squared$", "η²"),
    (r"^epsilon[ _-]?squared$", "ε²"),
    (r"^omega[ _-]?squared$", "ω²"),
    (r"^kendall'?s?[ _]w$", "W"),
    (r"^kendall'?s?[ _]tau-?c$", "τ_c"),
    (r"^(kendall'?s?[ _])?tau(-b)?$", "τ_b"),
    (r"^(spearman'?s? )?rho$", "r_s"),
    (r"^(pearson )?r$", "r"),
    (r"^cram[eé]r'?s v$", "V"),
    (r"^odds ratio$", "OR"),
    (r"^cliff'?s delta$", "δ"),
    (r"^p\(x ?> ?y\)$", "P(X>Y)"),
)

# Symbols whose magnitude cannot exceed 1: no leading zero (APA 7 §6.36).
BOUNDED_BASES = frozenset({"r", "ρ", "τ", "η", "ε", "ω", "V", "W", "D", "δ", "P(X>Y)", "power"})


def effect_symbol(metric: Any) -> Optional[str]:
    text = str(metric or "").strip().lower()
    for pattern, symbol in EFFECT_SYMBOLS:
        if re.match(pattern, text, re.I):
            return symbol
    return None


def is_bounded(symbol: Optional[str]) -> bool:
    if not symbol or symbol.startswith("W_"):  # W_BM, W_+ are unbounded rank statistics
        return False
    return symbol in BOUNDED_BASES or symbol.split("_")[0].rstrip("²") in BOUNDED_BASES


def rule_for(result: Dict[str, Any]) -> TestRule:
    method = str(result.get("test_method") or result.get("test") or "").lower()
    for rule in RULES:
        if re.search(rule.pattern, method):
            return rule
    return GENERIC


def rule_by_key(key: str) -> Optional[TestRule]:
    return next((r for r in RULES if r.key == key), None)


__all__ = ["TestRule", "RULES", "GENERIC", "EFFECT_SYMBOLS", "BOUNDED_BASES",
           "effect_symbol", "is_bounded", "rule_for", "rule_by_key"]

# EOF
