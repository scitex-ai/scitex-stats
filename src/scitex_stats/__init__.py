#!/usr/bin/env python3
# File: src/scitex_stats/__init__.py

"""scitex-stats — Publication-ready statistical testing framework.

Functionalities
---------------
- `run_test(name, ...)` — single dispatcher across 23 tests (parametric,
  nonparametric, correlation, categorical, normality) returning a unified
  result dict (statistic, pvalue, effect_size, power, formatted, ...).
- `recommend_tests(StatContext(...))` — design-driven test selection from
  number of groups, sample sizes, outcome type, paired vs between.
- `effect_sizes`, `power`, `correct`, `posthoc`, `descriptive`,
  `auto` — submodules exposing the primitives behind `run_test`
  (Cohen's d / Cliff's delta / eta-sq / sample-size-ttest /
  Bonferroni / FDR / Tukey HSD / Dunn / ...).
- APA / Nature / LaTeX formatting via `result["formatted"]`.
- `full_report(result, ...)` — six-stat reporting doctrine bundler:
  packages n, 95% CI, method, p-value, effect size, and test statistic
  into one dict + human-readable string, deriving the CI analytically
  (scipy closed-form) or via bootstrap when raw data is supplied.
  Raises when any of the six fields can't be determined — partial
  reports are treated as incomplete, not silently accepted.

IO
--
- Reads: numeric arrays (`numpy.ndarray`, `pandas.DataFrame`,
  `pandas.Series`, sequences); optional `.env` walk-up via
  scitex-config; runtime cache under `$SCITEX_DIR/stats/runtime/`.
- Writes: nothing by default — pure functions returning result dicts.
  Caller persists via `scitex_io.save(...)` if desired.

Dependencies
------------
- Hard: `numpy`, `scipy`, `pandas`, `scitex-dev`, `scitex-config`,
  `scitex-logging`.
- Optional (`[plot]`): `matplotlib`. (`[mcp]`): `fastmcp`.
  (`[figrecipe]`): `figrecipe`.

Standalone import::

    import scitex_stats as ss
    result = ss.run_test("ttest_ind", data=g1, data2=g2)
    print(result["formatted"])  # APA-style summary

CLI: ``scitex-stats <command>``. MCP: 10 tools for AI agents.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _version
from pathlib import Path as _Path

# ---------------------------------------------------------------------------
# .env-respect: walk parent dirs from cwd up to $HOME, load any .env files.
# Closer-to-cwd .env wins; process env always wins. Helper landed on
# scitex-config develop at eb9507e1 (load_dotenv walk_up + stop_at).
# Wrapped in try/except so the import never breaks if scitex-config is
# missing or older than 0.3.0.
# ---------------------------------------------------------------------------
try:
    from scitex_config import PriorityConfig as _PC

    _PC.load_dotenv(walk_up=True, stop_at=str(_Path.home()))
except Exception:
    pass

# ---------------------------------------------------------------------------
# Runtime path resolver: anything writable (cache, db, generated outputs)
# lives under ~/.scitex/stats/runtime/<sub>/ rather than ~/.scitex/stats/<sub>/.
# Config files (e.g. ~/.scitex/stats/config.yaml) stay at the top level.
# Implementation + one-shot migration live in _runtime_paths to keep
# __init__.py thin and let the audit-mirror test (PS-204) find a real
# src file to pair the test against.
# ---------------------------------------------------------------------------
from ._runtime_paths import migrate_runtime_dirs as _migrate_runtime_dirs
from ._runtime_paths import runtime_path as _runtime_path  # re-export

_migrate_runtime_dirs()

try:
    __version__ = _version("scitex-stats")
except _PackageNotFoundError:
    _pyproject = _Path(__file__).parent.parent.parent / "pyproject.toml"
    __version__ = "0.0.0+local"
    if _pyproject.exists():
        with open(_pyproject) as _f:
            for _line in _f:
                if _line.startswith("version"):
                    __version__ = _line.split("=")[1].strip().strip('"')
                    break

# ---------------------------------------------------------------------------
# PEP 562 lazy public API. Was eager-importing tests/auto/correct/...
# transitively pulling scipy + 22 test modules at every CLI call (9.3s).
# Lazy attribute access keeps `import scitex_stats` < 500ms; heavy machinery
# only loads when its function is actually called.
# See _skills/general/03_interface_01_python-api/04 §"PEP 562 module __getattr__"
# and audit-cli rule §10 (CLI startup speed).
# ---------------------------------------------------------------------------

# `run_test`, `describe`, `recommend_tests` are wrapped in @supports_return_as
# (when scitex-dev is installed) at first attribute access.
_DECORATED_FNS = {"run_test", "describe", "recommend_tests"}

# Public-name → source-submodule (relative to scitex_stats).
_LAZY_ATTRS: dict[str, str] = {
    # Submodules (also re-exported as attributes)
    "auto": "auto",
    "correct": "correct",
    "descriptive": "descriptive",
    "effect_sizes": "effect_sizes",
    "posthoc": "posthoc",
    "power": "power",
    "reporting": "reporting",
    "tests": "tests",
    # Dispatcher
    "available_tests": "_dispatch",
    "run_test": "_dispatch",
    # Six-stat reporting doctrine (n, 95% CI, method, p-value, effect size,
    # test statistic — see scitex_stats.reporting.full_report)
    "full_report": "reporting",
    # JSON
    "to_json_safe": "_utils._serialize",
    # Stats ↔ SciTeX bundle I/O (optional scitex-io; extra [bundle])
    "Stats": "_integration",
    "BUNDLE_AVAILABLE": "_integration",
    "test_result_to_stats": "_bundle_io",
    "save_stats": "_bundle_io",
    "load_stats": "_bundle_io",
    # Stats ↔ figrecipe annotations (optional figrecipe; extra [figrecipe])
    "to_figrecipe": "_figrecipe_integration",
    "annotate": "_figrecipe_integration",
    "load_and_annotate": "_figrecipe_integration",
    # Auto convenience
    "StatContext": "auto",
    "StatStyle": "auto",
    "TestRule": "auto",
    "check_applicable": "auto",
    "get_stat_style": "auto",
    "p_to_stars": "auto",
    "recommend_tests": "auto",
    # Descriptive
    "describe": "descriptive",
    # Parametric (6)
    "test_ttest_ind": "tests",
    "test_ttest_rel": "tests",
    "test_ttest_1samp": "tests",
    "test_anova": "tests",
    "test_anova_rm": "tests",
    "test_anova_2way": "tests",
    # Nonparametric (5)
    "test_brunner_munzel": "tests",
    "test_wilcoxon": "tests",
    "test_kruskal": "tests",
    "test_mannwhitneyu": "tests",
    "test_friedman": "tests",
    # Correlation (4)
    "test_pearson": "tests",
    "test_spearman": "tests",
    "test_kendall": "tests",
    "test_theilsen": "tests",
    # Categorical (4)
    "test_chi2": "tests",
    "test_fisher": "tests",
    "test_mcnemar": "tests",
    "test_cochran_q": "tests",
    # Normality (4)
    "test_shapiro": "tests",
    "test_normality": "tests",
    "test_ks_1samp": "tests",
    "test_ks_2samp": "tests",
    # Agreement (2)
    "test_kendalls_w": "tests",
    "test_icc": "tests",
}


def _supports_return_as_lazy(fn):
    """Apply scitex-dev's @supports_return_as if available; identity otherwise."""
    try:
        from scitex_dev.decorators import supports_return_as
    except ImportError:
        return fn
    return supports_return_as(fn)


def __getattr__(name: str):
    """PEP 562 lazy-loader: import on first access, cache, return."""
    mod_path = _LAZY_ATTRS.get(name)
    if mod_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    mod = import_module(f".{mod_path}", __name__)
    # Submodule re-exports: when a name maps to itself (e.g. "tests": "tests",
    # "power": "power"), the user wants the submodule itself, not an
    # attribute *named* "tests" inside it.
    if name == mod_path:
        attr = mod
    else:
        attr = getattr(mod, name)
        if name in _DECORATED_FNS:
            attr = _supports_return_as_lazy(attr)
    globals()[name] = attr  # cache; subsequent access skips this branch
    return attr


def __dir__() -> list[str]:
    return sorted(set(_LAZY_ATTRS) | set(globals()))


__all__ = [
    "__version__",
    # Submodules
    "auto",
    "correct",
    "descriptive",
    "effect_sizes",
    "posthoc",
    "power",
    "reporting",
    "tests",
    # Dispatcher
    "run_test",
    "available_tests",
    # Six-stat reporting doctrine
    "full_report",
    # Descriptive
    "describe",
    # JSON serialization
    "to_json_safe",
    # Stats ↔ SciTeX bundle I/O (optional scitex-io; extra [bundle])
    "Stats",
    "BUNDLE_AVAILABLE",
    "test_result_to_stats",
    "save_stats",
    "load_stats",
    # Stats ↔ figrecipe annotations (optional figrecipe; extra [figrecipe])
    "to_figrecipe",
    "annotate",
    "load_and_annotate",
    # Auto convenience
    "StatContext",
    "TestRule",
    "StatStyle",
    "recommend_tests",
    "check_applicable",
    "get_stat_style",
    "p_to_stars",
    # Parametric (6)
    "test_ttest_ind",
    "test_ttest_rel",
    "test_ttest_1samp",
    "test_anova",
    "test_anova_rm",
    "test_anova_2way",
    # Nonparametric (5)
    "test_brunner_munzel",
    "test_wilcoxon",
    "test_kruskal",
    "test_mannwhitneyu",
    "test_friedman",
    # Correlation (4)
    "test_pearson",
    "test_spearman",
    "test_kendall",
    "test_theilsen",
    # Categorical (4)
    "test_chi2",
    "test_fisher",
    "test_mcnemar",
    "test_cochran_q",
    # Normality (4)
    "test_shapiro",
    "test_normality",
    "test_ks_1samp",
    "test_ks_2samp",
    # Agreement (2)
    "test_kendalls_w",
    "test_icc",
]
