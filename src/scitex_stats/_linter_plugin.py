"""Linter plugin for scitex-stats: statistics-specific rules (ST001-ST006).

Registered via entry point 'scitex_dev.linter.plugins' so scitex-dev
discovers these rules automatically when scitex-stats is installed.
"""


def get_plugin():
    """Return scitex-stats linter rules and call mappings."""
    from scitex_dev.linter.rules import Rule

    ST001 = Rule(
        id="STX-ST001",
        severity="warning",
        category="stats",
        message="`scipy.stats.ttest_ind()` — use `scitex_stats.test_ttest_ind()` for a SciTeX result dictionary",
        suggestion="Use `scitex_stats.test_ttest_ind(a, b)` after importing scitex_stats; inspect its result dictionary keys.",
    )

    ST002 = Rule(
        id="STX-ST002",
        severity="warning",
        category="stats",
        message="`scipy.stats.mannwhitneyu()` — use `scitex_stats.test_mannwhitneyu()` for a SciTeX result dictionary",
        suggestion="Use `scitex_stats.test_mannwhitneyu(a, b)` after importing scitex_stats; inspect its result dictionary keys.",
    )

    ST003 = Rule(
        id="STX-ST003",
        severity="warning",
        category="stats",
        message="`scipy.stats.pearsonr()` — use `scitex_stats.test_pearson()` for a SciTeX result dictionary",
        suggestion="Use `scitex_stats.test_pearson(x, y)` after importing scitex_stats; inspect its result dictionary keys.",
    )

    ST004 = Rule(
        id="STX-ST004",
        severity="warning",
        category="stats",
        message="`scipy.stats.f_oneway()` — use `scitex_stats.test_anova()` for a SciTeX result dictionary",
        suggestion="Use `scitex_stats.test_anova(groups)` after importing scitex_stats; inspect its result dictionary keys.",
    )

    ST005 = Rule(
        id="STX-ST005",
        severity="warning",
        category="stats",
        message="`scipy.stats.wilcoxon()` — use `scitex_stats.test_wilcoxon()` for a SciTeX result dictionary",
        suggestion="Use `scitex_stats.test_wilcoxon(a, b)` after importing scitex_stats; inspect its result dictionary keys.",
    )

    ST006 = Rule(
        id="STX-ST006",
        severity="warning",
        category="stats",
        message="`scipy.stats.kruskal()` — use `scitex_stats.test_kruskal()` for a SciTeX result dictionary",
        suggestion="Use `scitex_stats.test_kruskal(groups)` after importing scitex_stats; inspect its result dictionary keys.",
    )

    return {
        "rules": [ST001, ST002, ST003, ST004, ST005, ST006],
        "call_rules": {
            ("stats", "ttest_ind"): ST001,
            ("scipy.stats", "ttest_ind"): ST001,
            ("stats", "mannwhitneyu"): ST002,
            ("scipy.stats", "mannwhitneyu"): ST002,
            ("stats", "pearsonr"): ST003,
            ("scipy.stats", "pearsonr"): ST003,
            ("stats", "f_oneway"): ST004,
            ("scipy.stats", "f_oneway"): ST004,
            ("stats", "wilcoxon"): ST005,
            ("scipy.stats", "wilcoxon"): ST005,
            ("stats", "kruskal"): ST006,
            ("scipy.stats", "kruskal"): ST006,
        },
        "axes_hints": {},
        "checkers": [],
    }
