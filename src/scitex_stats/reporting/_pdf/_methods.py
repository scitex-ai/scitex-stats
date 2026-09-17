#!/usr/bin/env python3
# File: src/scitex_stats/reporting/_pdf/_methods.py
"""Paste-ready methods paragraph and the reference list for the methods used."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from scitex_stats._utils._apa._segments import S, Segment, T, seg
from scitex_stats.posthoc._auto import POSTHOC_REFERENCES

REFERENCES = {
    "apa": "American Psychological Association. (2020). Publication manual of the American Psychological Association (7th ed.). https://doi.org/10.1037/0000165-000",
    "student": "Student. (1908). The probable error of a mean. Biometrika, 6(1), 1–25. https://doi.org/10.2307/2331554",
    "welch": "Welch, B. L. (1947). The generalization of “Student's” problem when several different population variances are involved. Biometrika, 34(1–2), 28–35. https://doi.org/10.1093/biomet/34.1-2.28",
    "delacre": "Delacre, M., Lakens, D., & Leys, C. (2017). Why psychologists should by default use Welch's t-test instead of Student's t-test. International Review of Social Psychology, 30(1), 92–101. https://doi.org/10.5334/irsp.82",
    "mann_whitney": "Mann, H. B., & Whitney, D. R. (1947). On a test of whether one of two random variables is stochastically larger than the other. The Annals of Mathematical Statistics, 18(1), 50–60. https://doi.org/10.1214/aoms/1177730491",
    "brunner_munzel": "Brunner, E., & Munzel, U. (2000). The nonparametric Behrens–Fisher problem: Asymptotic theory and a small-sample approximation. Biometrical Journal, 42(1), 17–25. https://doi.org/10.1002/(SICI)1521-4036(200001)42:1<17::AID-BIMJ17>3.0.CO;2-U",
    "wilcoxon": POSTHOC_REFERENCES["wilcoxon"],
    "fisher": "Fisher, R. A. (1925). Statistical methods for research workers. Oliver and Boyd.",
    "kruskal": "Kruskal, W. H., & Wallis, W. A. (1952). Use of ranks in one-criterion variance analysis. Journal of the American Statistical Association, 47(260), 583–621. https://doi.org/10.1080/01621459.1952.10483441",
    "friedman": "Friedman, M. (1937). The use of ranks to avoid the assumption of normality implicit in the analysis of variance. Journal of the American Statistical Association, 32(200), 675–701. https://doi.org/10.1080/01621459.1937.10503522",
    "shapiro": "Shapiro, S. S., & Wilk, M. B. (1965). An analysis of variance test for normality (complete samples). Biometrika, 52(3–4), 591–611. https://doi.org/10.1093/biomet/52.3-4.591",
    "brown_forsythe": POSTHOC_REFERENCES["brown_forsythe"],
    "cohen": "Cohen, J. (1988). Statistical power analysis for the behavioral sciences (2nd ed.). Lawrence Erlbaum Associates.",
    "simmons": "Simmons, J. P., Nelson, L. D., & Simonsohn, U. (2011). False-positive psychology: Undisclosed flexibility in data collection and analysis allows presenting anything as significant. Psychological Science, 22(11), 1359–1366. https://doi.org/10.1177/0956797611417632",
    "scipy": "Virtanen, P., Gommers, R., Oliphant, T. E., et al. (2020). SciPy 1.0: Fundamental algorithms for scientific computing in Python. Nature Methods, 17, 261–272. https://doi.org/10.1038/s41592-019-0686-2",
}

TEST_REFS = {
    "ttest_ind": ["student"], "ttest_welch": ["welch", "delacre"], "ttest_rel": ["student"],
    "mannwhitneyu": ["mann_whitney"], "brunner_munzel": ["brunner_munzel"], "wilcoxon": ["wilcoxon"],
    "anova": ["fisher"], "kruskal": ["kruskal"], "friedman": ["friedman"],
    "welch_anova": ["welch_anova"], "anova_rm": ["fisher", "greenhouse"],
}
REFERENCES["welch_anova"] = "Welch, B. L. (1951). On the comparison of several mean values: An alternative approach. Biometrika, 38(3–4), 330–336. https://doi.org/10.1093/biomet/38.3-4.330"
REFERENCES["greenhouse"] = "Greenhouse, S. W., & Geisser, S. (1959). On methods in the analysis of profile data. Psychometrika, 24(2), 95–112. https://doi.org/10.1007/BF02289823"

_PROSE = {
    "welch_anova": "Welch's one-way analysis of variance",
    "anova_rm": "a repeated-measures analysis of variance",
    "ttest_ind": "Student's independent-samples t-test",
    "ttest_welch": "Welch's t-test",
    "brunner_munzel": "the Brunner–Munzel test",
    "mannwhitneyu": "the Mann–Whitney U test",
    "ttest_rel": "a paired-samples t-test",
    "wilcoxon": "the Wilcoxon signed-rank test",
    "anova": "a one-way analysis of variance (ANOVA)",
    "kruskal": "the Kruskal–Wallis test",
    "friedman": "the Friedman test",
}
_EFFECT = {
    "ttest_ind": "Cohen's *d*", "ttest_welch": "Cohen's *d*", "ttest_rel": "Cohen's *d*~z~",
    "brunner_munzel": "the probability of superiority, *P*(*X* > *Y*)", "mannwhitneyu": "the rank-biserial correlation *r*~rb~",
    "wilcoxon": "the matched-pairs rank-biserial correlation", "anova": "η^2^", "kruskal": "ε^2^", "friedman": "Kendall's *W*",
    "welch_anova": "pairwise Hedges' *g*", "anova_rm": "partial η^2^",
}
_RANK = {"brunner_munzel", "mannwhitneyu", "wilcoxon", "kruskal", "friedman"}
_MARK = re.compile(r"(\*[^*]+\*|~[^~]+~|\^[^^]+\^)")


def marked(text: str) -> List[Segment]:
    """``*M*`` italic symbol, ``~z~`` subscript, ``^2^`` superscript; rest plain text."""
    out: List[Segment] = []
    for part in _MARK.split(text):
        if not part:
            continue
        if part.startswith("*"):
            out.append(S(part[1:-1]))
        elif part.startswith("~"):
            out.append(seg(part[1:-1], "sub"))
        elif part.startswith("^"):
            out.append(seg(part[1:-1], "sup"))
        else:
            out.append(T(part))
    return out


def methods_segments(ctx: Dict[str, Any]) -> List[Segment]:
    primary = ctx["primary"]
    within = ctx["design"] == "within"
    alpha = f"{ctx['alpha']:g}".lstrip("0")
    k = ctx["k"]
    center = "medians (*Mdn*) and interquartile ranges (*IQR*)" if primary in _RANK else "means (*M*) and standard deviations (*SD*)"
    parts = [f"Descriptive statistics are reported as {center} per {'condition' if within else 'group'}."]
    if within and k == 2:
        parts.append("Normality of the paired differences was assessed with the Shapiro–Wilk test (Shapiro & Wilk, 1965).")
    elif within:
        parts.append("Normality of the residuals after removing subject and condition effects was assessed with the "
                     "Shapiro–Wilk test (Shapiro & Wilk, 1965).")
    else:
        parts.append("Normality within each group was assessed with the Shapiro–Wilk test (Shapiro & Wilk, 1965) and "
                     "homogeneity of variance with the Brown–Forsythe test (Brown & Forsythe, 1974), each at α = .05.")
    verb = "Differences between conditions" if within else "Group differences"
    parts.append(f"{verb} were assessed with {_PROSE[primary]}, chosen by a rule fixed before inspecting test results "
                 f"({ctx['rationale_short']}). Effect sizes are reported as {_EFFECT[primary]} with 95% confidence intervals where computable.")
    ph = ctx.get("posthoc")
    if ph and ph.get("method"):
        what = {"tukey": "Tukey's honestly significant difference test", "games_howell": "the Games–Howell procedure",
                "dunn": "Dunn's test with Holm correction", "nemenyi": "the Nemenyi test",
                "wilcoxon": "pairwise Wilcoxon signed-rank tests with Holm correction",
                "paired_t": "pairwise paired t-tests with Holm correction"}[ph["method"]]
        cond = "following a significant omnibus test" if not ph.get("forced") else "regardless of the omnibus result (exploratory)"
        parts.append(f"Pairwise comparisons used {what}, {cond}; adjusted *p* values are reported.")
    others = ctx.get("sensitivity") or []
    if others:
        names = ", ".join(_PROSE[t] for t in others)
        parts.append(f"As sensitivity analyses, {names} {'was' if len(others) == 1 else 'were'} also run; these do not replace the primary test.")
    parts.append(f"All tests were two-sided with α = {alpha}. Analyses were run in scitex-stats {ctx['version']} "
                 f"(Python {ctx['python']}, SciPy {ctx['scipy']}; Virtanen et al., 2020) with random seed {ctx['seed']}.")
    return marked(" ".join(parts))


def references(primary: str, sensitivity: List[str], posthoc_refs: List[str], design: str = "between") -> List[str]:
    keys = ["apa", "shapiro", "scipy", *TEST_REFS[primary]]
    if design == "between":
        keys.append("brown_forsythe")
    for t in sensitivity:
        keys += TEST_REFS[t]
    if sensitivity:
        keys.append("simmons")
    refs = {REFERENCES[k] for k in keys} | set(posthoc_refs)
    return sorted(refs, key=lambda r: r.lower())


__all__ = ["REFERENCES", "marked", "methods_segments", "references"]

# EOF
