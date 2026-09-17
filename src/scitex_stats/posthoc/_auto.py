#!/usr/bin/env python3
# File: src/scitex_stats/posthoc/_auto.py
"""Deterministic post-hoc selection and pairwise comparisons after an omnibus test.

Selection (3 or more groups only):

- one-way ANOVA  -> Tukey HSD when Brown–Forsythe (median-centred Levene)
  p >= alpha, else Games–Howell;
- Welch's ANOVA  -> Games–Howell;
- Kruskal–Wallis -> Dunn's test, Holm-adjusted;
- Friedman       -> Nemenyi (default) or pairwise Wilcoxon signed-rank, Holm-adjusted;
- repeated-measures ANOVA -> pairwise paired t-tests, Holm-adjusted.

Every comparison carries the unadjusted and adjusted p (APA formatted), a
pairwise effect size, and a 95% CI where one is computable. p values for
Tukey, Games–Howell and Nemenyi come from the exact studentized range
distribution (``scipy.stats.studentized_range``). Bootstrap CIs for rank
effect sizes use ``numpy.random.default_rng(seed)`` so repeated runs match.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from scipy import stats

from scitex_stats._utils._apa import format_ci, format_number, format_p, format_p_exact

__all__ = ["select_posthoc", "run_posthoc", "OMNIBUS_TESTS", "POSTHOC_REFERENCES"]

OMNIBUS_TESTS = ("anova", "welch_anova", "kruskal", "friedman", "anova_rm")
_ALIASES = {"one_way_anova": "anova", "f_oneway": "anova", "kruskal_wallis": "kruskal", "rm_anova": "anova_rm"}
_BLOCKED = ("friedman", "anova_rm")
_N_BOOT = 2000
_Q_DF_INF = 1e7  # studentized_range with an effectively infinite df (Nemenyi)

POSTHOC_REFERENCES = {
    "tukey": "Tukey, J. W. (1949). Comparing individual means in the analysis of variance. Biometrics, 5(2), 99–114. https://doi.org/10.2307/3001913",
    "games_howell": "Games, P. A., & Howell, J. F. (1976). Pairwise multiple comparison procedures with unequal n's and/or variances: A Monte Carlo study. Journal of Educational Statistics, 1(2), 113–125. https://doi.org/10.3102/10769986001002113",
    "dunn": "Dunn, O. J. (1964). Multiple comparisons using rank sums. Technometrics, 6(3), 241–252. https://doi.org/10.1080/00401706.1964.10490181",
    "holm": "Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics, 6(2), 65–70.",
    "nemenyi": "Nemenyi, P. B. (1963). Distribution-free multiple comparisons [Doctoral dissertation, Princeton University].",
    "wilcoxon": "Wilcoxon, F. (1945). Individual comparisons by ranking methods. Biometrics Bulletin, 1(6), 80–83. https://doi.org/10.2307/3001968",
    "brown_forsythe": "Brown, M. B., & Forsythe, A. B. (1974). Robust tests for the equality of variances. Journal of the American Statistical Association, 69(346), 364–367. https://doi.org/10.1080/01621459.1974.10482955",
    "hedges": "Hedges, L. V., & Olkin, I. (1985). Statistical methods for meta-analysis. Academic Press.",
    "cliff": "Cliff, N. (1993). Dominance statistics: Ordinal analyses to answer ordinal questions. Psychological Bulletin, 114(3), 494–509. https://doi.org/10.1037/0033-2909.114.3.494",
    "lakens": "Lakens, D. (2013). Calculating and reporting effect sizes to facilitate cumulative science: A practical primer for t-tests and ANOVAs. Frontiers in Psychology, 4, 863. https://doi.org/10.3389/fpsyg.2013.00863",
}

_LABELS = {
    "tukey": "Tukey HSD",
    "games_howell": "Games–Howell",
    "dunn": "Dunn's test",
    "nemenyi": "Nemenyi test",
    "wilcoxon": "Pairwise Wilcoxon signed-rank tests",
    "paired_t": "Pairwise paired t-tests",
}
_CORRECTIONS = {
    "tukey": "Tukey (studentized range, family-wise)",
    "games_howell": "Games–Howell (studentized range with Welch df, family-wise)",
    "dunn": "Holm",
    "nemenyi": "Nemenyi (studentized range, family-wise)",
    "wilcoxon": "Holm",
    "paired_t": "Holm",
}
RANK_METHODS = ("dunn", "nemenyi", "wilcoxon")
SIMULTANEOUS_CI = ("tukey", "games_howell")


def _canonical(omnibus: str) -> str:
    key = str(omnibus or "").lower().replace("-", "_")
    return _ALIASES.get(key, key)


def select_posthoc(
    omnibus: str,
    n_groups: int,
    *,
    equal_variances: Optional[bool] = None,
    friedman_method: str = "nemenyi",
) -> Dict[str, Any]:
    """Pick the post-hoc for an omnibus test; pure, no data access.

    Returns ``{"method", "label", "correction", "reason", "applicable"}``.
    ``applicable`` is False (with a reason) for fewer than 3 groups or an
    omnibus test that has no pairwise follow-up here.
    """
    test = _canonical(omnibus)
    if n_groups < 3:
        return {"method": None, "label": None, "correction": None, "applicable": False,
                "reason": f"Post-hoc comparisons need 3 or more groups (got {n_groups})."}
    if test == "anova":
        # Tukey requires the equal-variance assumption to have been DECLARED in
        # advance. It is never chosen because the sample happens to look
        # homogeneous: an undeclared design stays on Games–Howell, which assumes
        # nothing. (The Brown–Forsythe result is still reported as a diagnostic;
        # it is not allowed to make this choice.)
        if equal_variances is True:
            method, reason = "tukey", "Equal variances were declared in advance, so Tukey HSD."
        elif equal_variances is False:
            method, reason = "games_howell", "Variances were declared unequal in advance, so Games–Howell, which does not assume equal variances."
        else:
            method, reason = "games_howell", "Equal variances were not declared in advance, so Games–Howell, which does not assume equal variances."
    elif test == "welch_anova":
        method, reason = "games_howell", "Welch's ANOVA was used because variances differ, so Games–Howell, which does not assume equal variances."
    elif test == "anova_rm":
        method, reason = "paired_t", "Repeated-measures ANOVA, so pairwise paired t-tests with Holm adjustment."
    elif test == "kruskal":
        method, reason = "dunn", "Rank-based omnibus test, so Dunn's test on the joint ranks with Holm adjustment."
    elif test == "friedman":
        if friedman_method not in ("nemenyi", "wilcoxon"):
            raise ValueError("friedman_method must be 'nemenyi' or 'wilcoxon'")
        method = friedman_method
        reason = ("Repeated-measures rank test, so the Nemenyi test on within-subject mean ranks."
                  if method == "nemenyi" else
                  "Repeated-measures rank test, so pairwise Wilcoxon signed-rank tests with Holm adjustment.")
    else:
        return {"method": None, "label": None, "correction": None, "applicable": False,
                "reason": f"No post-hoc procedure defined for '{omnibus}'."}
    return {"method": method, "label": _LABELS[method], "correction": _CORRECTIONS[method],
            "applicable": True, "reason": reason}


# ---------------------------------------------------------------------------
# Effect sizes
# ---------------------------------------------------------------------------


def _hedges_g(x: np.ndarray, y: np.ndarray, level: float = 0.95) -> Dict[str, Any]:
    n1, n2 = len(x), len(y)
    df = n1 + n2 - 2
    sp = np.sqrt(((n1 - 1) * np.var(x, ddof=1) + (n2 - 1) * np.var(y, ddof=1)) / df) if df > 0 else np.nan
    if not np.isfinite(sp) or sp == 0:
        return {"effect_size": None, "effect_size_metric": "Hedges' g", "effect_ci": None}
    d = (np.mean(x) - np.mean(y)) / sp
    j = 1 - 3 / (4 * df - 1)
    g = j * d
    se = np.sqrt((n1 + n2) / (n1 * n2) + g ** 2 / (2 * (n1 + n2)))
    z = stats.norm.ppf(0.5 + level / 2)
    return {"effect_size": float(g), "effect_size_metric": "Hedges' g",
            "effect_ci": (float(g - z * se), float(g + z * se))}


def _boot_ci(stat_fn, arrays: Sequence[np.ndarray], seed: int, level: float, paired: bool):
    rng = np.random.default_rng(seed)
    values = np.empty(_N_BOOT)
    if paired:
        n = len(arrays[0])
        for b in range(_N_BOOT):
            idx = rng.integers(0, n, n)
            values[b] = stat_fn(*(a[idx] for a in arrays))
    else:
        for b in range(_N_BOOT):
            values[b] = stat_fn(*(a[rng.integers(0, len(a), len(a))] for a in arrays))
    values = values[np.isfinite(values)]
    if values.size < _N_BOOT // 2:
        return None
    lo, hi = np.percentile(values, [50 * (1 - level), 50 * (1 + level)])
    return float(lo), float(hi)


def _cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean(np.sign(x[:, None] - y[None, :])))


def _matched_rank_biserial(x: np.ndarray, y: np.ndarray) -> float:
    d = x - y
    d = d[d != 0]
    if d.size == 0:
        return 0.0
    ranks = stats.rankdata(np.abs(d))
    return float((ranks[d > 0].sum() - ranks[d < 0].sum()) / ranks.sum())


# ---------------------------------------------------------------------------
# Procedures
# ---------------------------------------------------------------------------


def _holm(pvalues: Sequence[float]) -> List[float]:
    p = np.asarray(pvalues, dtype=float)
    m = p.size
    order = np.argsort(p, kind="mergesort")
    adj = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[idx]))
        adj[idx] = running
    return adj.tolist()


def _pairs(k: int):
    return [(i, j) for i in range(k) for j in range(i + 1, k)]


def _tukey(groups, alpha, level):
    k = len(groups)
    ns = [len(g) for g in groups]
    df = sum(ns) - k
    mse = sum(((g - g.mean()) ** 2).sum() for g in groups) / df
    q_crit = stats.studentized_range.ppf(level, k, df)
    out = []
    for i, j in _pairs(k):
        diff = groups[i].mean() - groups[j].mean()
        se = np.sqrt(mse / 2 * (1 / ns[i] + 1 / ns[j]))
        q = abs(diff) / se if se > 0 else 0.0
        p = float(stats.studentized_range.sf(q, k, df)) if se > 0 else 1.0
        out.append({"i": i, "j": j, "statistic": float(q), "stat_symbol": "q", "df": float(df),
                    "p_unadjusted": None, "p_adjusted": min(1.0, p), "mean_diff": float(diff),
                    "diff_ci": (float(diff - q_crit * se), float(diff + q_crit * se))})
    return out


def _games_howell(groups, alpha, level):
    k = len(groups)
    out = []
    for i, j in _pairs(k):
        x, y = groups[i], groups[j]
        vx, vy = np.var(x, ddof=1) / len(x), np.var(y, ddof=1) / len(y)
        se = np.sqrt(vx + vy)
        df = (vx + vy) ** 2 / (vx ** 2 / (len(x) - 1) + vy ** 2 / (len(y) - 1)) if se > 0 else np.nan
        diff = x.mean() - y.mean()
        if se > 0:
            q = abs(diff) / se * np.sqrt(2)
            p = float(stats.studentized_range.sf(q, k, df))
            margin = stats.studentized_range.ppf(level, k, df) / np.sqrt(2) * se
            ci = (float(diff - margin), float(diff + margin))
        else:
            q, p, ci = 0.0, 1.0, None
        out.append({"i": i, "j": j, "statistic": float(q), "stat_symbol": "q",
                    "df": float(df) if np.isfinite(df) else None, "p_unadjusted": None,
                    "p_adjusted": min(1.0, p), "mean_diff": float(diff), "diff_ci": ci})
    return out


def _dunn(groups, alpha, level):
    k = len(groups)
    pooled = np.concatenate(groups)
    n_total = pooled.size
    ranks = stats.rankdata(pooled)
    _, counts = np.unique(pooled, return_counts=True)
    ties = float(((counts ** 3) - counts).sum())
    sigma2 = n_total * (n_total + 1) / 12 - ties / (12 * (n_total - 1))
    bounds = np.cumsum([0] + [len(g) for g in groups])
    mean_ranks = [ranks[bounds[g]:bounds[g + 1]].mean() for g in range(k)]
    out, raw = [], []
    for i, j in _pairs(k):
        se = np.sqrt(sigma2 * (1 / len(groups[i]) + 1 / len(groups[j])))
        z = (mean_ranks[i] - mean_ranks[j]) / se if se > 0 else 0.0
        p = float(2 * stats.norm.sf(abs(z)))
        raw.append(p)
        out.append({"i": i, "j": j, "statistic": float(z), "stat_symbol": "z", "df": None,
                    "p_unadjusted": p, "mean_rank_diff": float(mean_ranks[i] - mean_ranks[j])})
    for row, adj in zip(out, _holm(raw)):
        row["p_adjusted"] = adj
    return out


def _nemenyi(blocks, alpha, level):
    n, k = blocks.shape
    ranks = np.apply_along_axis(stats.rankdata, 1, blocks)
    mean_ranks = ranks.mean(axis=0)
    se = np.sqrt(k * (k + 1) / (6 * n))
    out = []
    for i, j in _pairs(k):
        diff = mean_ranks[i] - mean_ranks[j]
        q = abs(diff) / se * np.sqrt(2)
        p = float(stats.studentized_range.sf(q, k, _Q_DF_INF))
        out.append({"i": i, "j": j, "statistic": float(q), "stat_symbol": "q", "df": None,
                    "p_unadjusted": None, "p_adjusted": min(1.0, p), "mean_rank_diff": float(diff)})
    return out


def _wilcoxon_holm(blocks, alpha, level):
    k = blocks.shape[1]
    out, raw = [], []
    for i, j in _pairs(k):
        x, y = blocks[:, i], blocks[:, j]
        if np.all(x == y):
            w, p = 0.0, 1.0
        else:
            res = stats.wilcoxon(x, y)
            w, p = float(res.statistic), float(res.pvalue)
        raw.append(p)
        out.append({"i": i, "j": j, "statistic": w, "stat_symbol": "W", "df": None, "p_unadjusted": p})
    for row, adj in zip(out, _holm(raw)):
        row["p_adjusted"] = adj
    return out


def _paired_t_holm(blocks, alpha, level):
    k = blocks.shape[1]
    out, raw = [], []
    for i, j in _pairs(k):
        d = blocks[:, i] - blocks[:, j]
        n = d.size
        sd = np.std(d, ddof=1)
        if sd == 0:
            # A constant difference has no variability to test, so no t and no p
            # exist. The old code reported t=0, p=1, i.e. it called a constant
            # difference of 1 "no effect" - the opposite of what the data say.
            # Undefined is the honest answer, and it is labelled as such instead of
            # being given a number nobody can compute.
            mean_diff = float(d.mean())
            raw.append(None)
            out.append({"i": i, "j": j, "statistic": None, "stat_symbol": "t", "df": float(n - 1),
                        "p_unadjusted": None, "mean_diff": mean_diff, "diff_ci": None,
                        "undefined": ("every paired difference is zero: the paired test is undefined "
                                      "(there is no variability to test)"
                                      if mean_diff == 0 else
                                      "the paired difference is constant and non-zero: the paired test is "
                                      "undefined (zero standard error), so no t and no p exist")})
            continue
        if True:
            se = sd / np.sqrt(n)
            t = float(d.mean() / se)
            p = float(2 * stats.t.sf(abs(t), n - 1))
            half = stats.t.ppf(0.5 + level / 2, n - 1) * se
            ci = (float(d.mean() - half), float(d.mean() + half))
        raw.append(p)
        out.append({"i": i, "j": j, "statistic": t, "stat_symbol": "t", "df": float(n - 1),
                    "p_unadjusted": p, "mean_diff": float(d.mean()), "diff_ci": ci})
    # Holm over the DEFINED p-values only: an undefined pair has no p to adjust, and
    # inventing one would put it in the family-wise budget it never entered.
    defined = [index for index, value in enumerate(raw) if value is not None]
    for index, adj in zip(defined, _holm([raw[index] for index in defined])):
        out[index]["p_adjusted"] = adj
    for row in out:
        row.setdefault("p_adjusted", None)
    return out


def _cohens_dz(x: np.ndarray, y: np.ndarray, level: float) -> Dict[str, Any]:
    d = x - y
    n, sd = d.size, np.std(d, ddof=1)
    if sd == 0:
        return {"effect_size": None, "effect_size_metric": "Cohen's d_z", "effect_ci": None}
    dz = d.mean() / sd
    se = np.sqrt(1 / n + dz ** 2 / (2 * n))
    z = stats.norm.ppf(0.5 + level / 2)
    return {"effect_size": float(dz), "effect_size_metric": "Cohen's d_z", "effect_ci": (float(dz - z * se), float(dz + z * se))}


def _omnibus(test: str, groups: List[np.ndarray]) -> Dict[str, Any]:
    names = {"anova": "One-way ANOVA", "welch_anova": "Welch's ANOVA", "kruskal": "Kruskal–Wallis test",
             "friedman": "Friedman test", "anova_rm": "Repeated-measures ANOVA"}
    if test == "anova":
        res = stats.f_oneway(*groups)
        stat, p = res.statistic, res.pvalue
    elif test == "kruskal":
        res = stats.kruskal(*groups)
        stat, p = res.statistic, res.pvalue
    elif test == "friedman":
        res = stats.friedmanchisquare(*groups)
        stat, p = res.statistic, res.pvalue
    elif test == "welch_anova":
        from scitex_stats._recommend._applicability import welch_anova

        res = welch_anova(groups)
        stat, p = res["statistic"], res["pvalue"]
    else:
        import pandas as pd

        from scitex_stats.tests import test_anova_rm

        res = test_anova_rm(pd.DataFrame(np.column_stack(groups)), decimals=12)
        stat, p = res["statistic"], res["pvalue"]
    return {"test": test, "name": names[test], "statistic": float(stat), "pvalue": float(p)}


def run_posthoc(
    groups: Sequence[Sequence[float]],
    omnibus: str = "anova",
    *,
    group_names: Optional[Sequence[str]] = None,
    alpha: float = 0.05,
    omnibus_pvalue: Optional[float] = None,
    equal_variances: Optional[bool] = None,
    friedman_method: str = "nemenyi",
    when: str = "significant",
    seed: int = 42,
    confidence: float = 0.95,
) -> Dict[str, Any]:
    """Run the post-hoc that :func:`select_posthoc` picks for ``omnibus``.

    Parameters
    ----------
    groups : list of array-like
        One array per group. For ``"friedman"`` and ``"anova_rm"`` every group
        is one condition over the same subjects (equal lengths, row-aligned).
    omnibus : {"anova", "welch_anova", "kruskal", "friedman", "anova_rm"}
    group_names : list of str, optional
    alpha : float
        Significance level for the omnibus decision and the ``significant`` flag.
    omnibus_pvalue : float, optional
        The omnibus p already computed; recomputed with scipy when omitted.
    equal_variances : bool, optional
        ANOVA only, and it is the caller's ADVANCE DECLARATION — never inferred from
        the data. Omitted (or ``None``) means "not declared", which keeps the
        post-hoc on Games–Howell instead of granting Tukey on the strength of a
        sample that merely looks homogeneous.
    friedman_method : {"nemenyi", "wilcoxon"}
    when : {"significant", "always"}
        ``"significant"`` runs comparisons only after a significant omnibus;
        ``"always"`` runs them regardless and flags a non-significant omnibus.
    seed : int
        Seed for the bootstrap CIs of rank effect sizes.

    Returns
    -------
    dict
        ``ran``, ``method``, ``label``, ``correction``, ``reason``,
        ``omnibus`` (name, statistic, pvalue, significant), ``flags``,
        ``variance_check`` (ANOVA), ``comparisons`` and ``references``.
    """
    if when not in ("significant", "always"):
        raise ValueError("when must be 'significant' or 'always'")
    test = _canonical(omnibus)
    arrays = [np.asarray(g, dtype=float).ravel() for g in groups]
    arrays = [a[~np.isnan(a)] for a in arrays] if test not in _BLOCKED else arrays
    k = len(arrays)
    names = [str(n) for n in group_names] if group_names else [f"Group {i + 1}" for i in range(k)]
    if len(names) != k:
        raise ValueError(f"Expected {k} group names, got {len(names)}")

    variance_check = None
    if test == "anova" and k >= 3:
        # REPORTED, never decisive: the equal-variance assumption must come from the
        # caller's advance declaration (`equal_variances`), not from the data this
        # run happens to have drawn. Deciding from it is the data-dependent choice
        # the report doctrine forbids.
        bf = stats.levene(*arrays, center="median")
        variance_check = {"test": "Brown–Forsythe (Levene, median-centred)", "statistic": float(bf.statistic),
                          "pvalue": float(bf.pvalue), "alpha": alpha, "equal_variances": bool(bf.pvalue >= alpha)}
    choice = select_posthoc(test, k, equal_variances=equal_variances, friedman_method=friedman_method)
    base: Dict[str, Any] = {**choice, "ran": False, "alpha": alpha, "group_names": names,
                            "variance_check": variance_check, "flags": [], "comparisons": [],
                            "omnibus": None, "references": []}
    if not choice["applicable"]:
        return base

    blocks = None
    if test in _BLOCKED:
        lengths = {len(a) for a in arrays}
        if len(lengths) != 1:
            raise ValueError("Repeated-measures post-hoc needs equal-length, row-aligned groups")
        blocks = np.column_stack(arrays)
        blocks = blocks[~np.isnan(blocks).any(axis=1)]
        arrays = [blocks[:, i] for i in range(k)]

    omni = _omnibus(test, arrays)
    if omnibus_pvalue is not None:
        omni["pvalue"] = float(omnibus_pvalue)
    omni["significant"] = bool(omni["pvalue"] < alpha)
    omni["p_apa"] = format_p(omni["pvalue"])
    base["omnibus"] = omni

    if not omni["significant"]:
        if when == "significant":
            base["reason"] = (f"{choice['reason']} Not run: the omnibus test was not significant "
                              f"(p {omni['p_apa']}, α = {format_number(alpha, 2, False)}).")
            return base
        base["flags"].append("omnibus_not_significant")
        base["note"] = ("The omnibus test was not significant; these comparisons were requested anyway "
                        "and should be read as exploratory.")

    method = choice["method"]
    runner = {"tukey": _tukey, "games_howell": _games_howell, "dunn": _dunn}.get(method)
    block_runner = {"nemenyi": _nemenyi, "wilcoxon": _wilcoxon_holm, "paired_t": _paired_t_holm}.get(method)
    rows = runner(arrays, alpha, confidence) if runner else block_runner(blocks, alpha, confidence)

    comparisons = []
    for n, row in enumerate(rows):
        i, j = row.pop("i"), row.pop("j")
        x, y = arrays[i], arrays[j]
        if method in ("tukey", "games_howell"):
            eff = _hedges_g(x, y, confidence)
            eff_ci_method = "analytic (Hedges & Olkin)"
        elif method == "paired_t":
            eff = _cohens_dz(x, y, confidence)
            eff_ci_method = "analytic (normal approximation)"
        elif method == "dunn":
            eff = {"effect_size": _cliffs_delta(x, y), "effect_size_metric": "Cliff's delta",
                   "effect_ci": _boot_ci(_cliffs_delta, [x, y], seed + n, confidence, paired=False)}
            eff_ci_method = f"percentile bootstrap ({_N_BOOT} resamples, seed {seed + n})"
        else:
            eff = {"effect_size": _matched_rank_biserial(x, y), "effect_size_metric": "matched-pairs rank-biserial r",
                   "effect_ci": _boot_ci(_matched_rank_biserial, [x, y], seed + n, confidence, paired=True)}
            eff_ci_method = f"percentile bootstrap over subjects ({_N_BOOT} resamples, seed {seed + n})"
        p_adj = None if row.get("p_adjusted") is None else float(row["p_adjusted"])
        diff_ci = row.pop("diff_ci", None)
        eff_ci = eff.pop("effect_ci")
        bounded = method in RANK_METHODS
        comparisons.append({
            "group_i": names[i], "group_j": names[j], "n_i": int(len(x)), "n_j": int(len(y)),
            **row, **eff,
            "p_adjusted": p_adj,
            "p_apa": format_p(p_adj),
            "p_adjusted_exact": None if p_adj is None else format_p_exact(p_adj),
            "p_unadjusted_apa": format_p(row["p_unadjusted"]) if row.get("p_unadjusted") is not None else None,
            "significant": bool(p_adj is not None and p_adj < alpha),
            "effect_ci_lower": eff_ci[0] if eff_ci else None,
            "effect_ci_upper": eff_ci[1] if eff_ci else None,
            "effect_ci_apa": format_ci(*eff_ci, confidence, leading_zero=not bounded) if eff_ci else None,
            "effect_ci_method": eff_ci_method if eff_ci else None,
            "mean_diff_ci_lower": diff_ci[0] if diff_ci else None,
            "mean_diff_ci_upper": diff_ci[1] if diff_ci else None,
            "mean_diff_ci_apa": format_ci(*diff_ci, confidence) if diff_ci else None,
            "mean_diff_ci_kind": ("simultaneous" if method in SIMULTANEOUS_CI else "per-comparison") if diff_ci else None,
            "ci_level": confidence,
        })
    base["comparisons"] = comparisons
    base["ran"] = True
    refs = {"tukey": ["tukey", "brown_forsythe", "hedges"], "games_howell": ["games_howell", "brown_forsythe", "hedges"],
            "dunn": ["dunn", "holm", "cliff"], "nemenyi": ["nemenyi"], "wilcoxon": ["wilcoxon", "holm"],
            "paired_t": ["holm", "lakens"]}[method]
    base["references"] = [POSTHOC_REFERENCES[r] for r in refs]
    return base


# EOF
