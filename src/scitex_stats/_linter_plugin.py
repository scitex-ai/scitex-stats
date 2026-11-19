"""Linter plugin for scitex-stats: statistics-specific rules.

- ``STX-ST001``-``ST006`` — a raw ``scipy.stats`` test call has a
  ``stx.stats`` equivalent with effect sizes / CI.
- ``STX-I002`` — ``from scipy import stats`` / ``from scipy.stats import ...``
  (use ``stx.stats``). Moved here from the scitex-dev engine, which lists
  scitex-stats as its owner in its handover table: same id, severity,
  message and gates, so findings are unchanged. With this plugin installed
  the engine stops emitting it; with an older scitex-stats the engine's
  compatibility copy still does.

Registered via the ``scitex_dev.linter.plugins`` entry point.
"""

import ast

# STX-I002 — engine metadata, verbatim.
_I002 = dict(
    id="STX-I002",
    severity="warning",
    category="import",
    message="Use `stx.stats` instead of importing scipy.stats directly",
    suggestion="Replace with `stx.stats` which adds effect sizes, CI, and power analysis.",
    requires="scitex",
)


def _bind_import_checker(rule, spi):
    """Checker emitting STX-I002 exactly where the engine did."""

    class ScipyStatsImportChecker(ast.NodeVisitor):
        category = "import"
        # Package-availability map for the ``requires`` gate; None = detect.
        available = None

        def __init__(self, source_lines, config):
            self.source_lines = source_lines
            self.config = config
            self.issues = []

        def visit_ImportFrom(self, node):
            module = node.module or ""
            hit = module == "scipy.stats" or (
                module == "scipy" and any(a.name == "stats" for a in node.names)
            )
            if hit:
                lineno = node.lineno
                source = (
                    self.source_lines[lineno - 1].rstrip()
                    if 1 <= lineno <= len(self.source_lines)
                    else ""
                )
                spi.add_issue(
                    self.issues,
                    rule,
                    lineno,
                    node.col_offset,
                    source,
                    self.config,
                    available=self.available,
                )
            self.generic_visit(node)

    return ScipyStatsImportChecker


def get_plugin():
    """Return scitex-stats linter rules, call mappings and checkers."""
    from scitex_dev.linter import spi
    from scitex_dev.linter.spi import Rule

    I002 = Rule(**_I002)

    ST001 = Rule(
        id="STX-ST001",
        severity="warning",
        category="stats",
        message="`scipy.stats.ttest_ind()` — use `stx.stats.ttest_ind()` for auto effect size + CI",
        suggestion="Replace with `stx.stats.ttest_ind(a, b)` which includes Cohen's d and CI.",
        requires="scitex",
    )

    ST002 = Rule(
        id="STX-ST002",
        severity="warning",
        category="stats",
        message="`scipy.stats.mannwhitneyu()` — use `stx.stats.mannwhitneyu()` for auto effect size",
        suggestion="Replace with `stx.stats.mannwhitneyu(a, b)` which includes Cliff's delta.",
        requires="scitex",
    )

    ST003 = Rule(
        id="STX-ST003",
        severity="warning",
        category="stats",
        message="`scipy.stats.pearsonr()` — use `stx.stats.pearsonr()` for auto CI + power",
        suggestion="Replace with `stx.stats.pearsonr(a, b)` which includes CI and power analysis.",
        requires="scitex",
    )

    ST004 = Rule(
        id="STX-ST004",
        severity="warning",
        category="stats",
        message="`scipy.stats.f_oneway()` — use `stx.stats.anova_oneway()` for post-hoc + effect sizes",
        suggestion="Replace with `stx.stats.anova_oneway(*groups)` which includes eta-squared.",
        requires="scitex",
    )

    ST005 = Rule(
        id="STX-ST005",
        severity="warning",
        category="stats",
        message="`scipy.stats.wilcoxon()` — use `stx.stats.wilcoxon()` for auto effect size",
        suggestion="Replace with `stx.stats.wilcoxon(a, b)` which includes effect size and CI.",
        requires="scitex",
    )

    ST006 = Rule(
        id="STX-ST006",
        severity="warning",
        category="stats",
        message="`scipy.stats.kruskal()` — use `stx.stats.kruskal()` for post-hoc + effect sizes",
        suggestion="Replace with `stx.stats.kruskal(*groups)` which includes epsilon-squared.",
        requires="scitex",
    )

    return {
        "rules": [ST001, ST002, ST003, ST004, ST005, ST006, I002],
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
        "checkers": [_bind_import_checker(I002, spi)],
    }
