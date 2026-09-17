# Changelog

All notable changes to `scitex-stats` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [0.2.27] — 2026-09-17

### Changed
- The Statistics app's data and test panes follow the operator UI review:
  - The file drop zone answers the pointer and the keyboard — hover /
    focus-within tint, the dragover accent ring, and a native "choose a file"
    button inside it. The zone itself stays a click target (a click that misses
    an interactive child opens the picker), so mouse, touch and keyboard all
    reach the file dialog.
  - `Load sample dataset` is a titled secondary action directly below the drop
    zone, with a one-line description of what it loads and a confirmation
    before it replaces anything already typed; the ambiguous inline "or" label
    is gone.
  - Selected test rows are flat: a 4px vertical accent line on the left edge, a
    subtle full-row tint and semibold text — no rounded card, no shadow.
  - Phones (390px): single-column options, a wrapping pane header, and >=44px
    touch targets for every control.

## [0.2.26] — 2026-09-17

### Added
- `scitex_stats.run_posthoc` / `select_posthoc`: post-hoc after a 3+ group
  omnibus test, chosen deterministically (ANOVA: Tukey HSD or Games–Howell by
  Brown–Forsythe; Welch's ANOVA: Games–Howell; Kruskal–Wallis: Dunn–Holm;
  Friedman: Nemenyi or Wilcoxon–Holm; RM ANOVA: paired t–Holm). Exact
  studentized-range p values, adjusted p (APA), pairwise effect sizes with CIs;
  a non-significant omnibus skips comparisons unless `when="always"`, which flags it.
- `scitex_stats.report(data, design=..., output="report.pdf")`, `scitex-stats
  report data.csv --out report.pdf` and the `generate_report` MCP tool: one PDF
  (plus HTML and Markdown) with metadata, data summary and exclusions,
  assumption checks, applicability and primary test, APA result, sensitivity
  analyses, post-hoc table, figure with brackets, methods paragraph and
  references. WeasyPrint renders offline; new `[report]` extra.
- Stats app: "Download report (PDF)" and "Save to Files" in Results (EN/JA).
- Provenance receipt on every `run_test`, `full_report` and MCP `run_test`
  result (`result["provenance"]`, schema `scitex-stats/provenance@1`): test
  and parameters, per-input SHA-256 with n, seed, library versions, UTC
  timestamp, result and receipt hashes. See skill `17_provenance-verify.md`.
- `scitex_stats.verify(result, data=...)`, `scitex-stats verify` CLI and the
  `verify_result` MCP tool: receipt/result/input hash checks plus a
  bit-for-bit recompute.
- `result["input_integrity"]`: NaN exclusions (with indices and reason),
  type coercions; `run_test(nan_policy="omit"|"raise")`.
- APA 7 output fixed at the source: every result carries an `apa` block
  (plain / html / latex / rule / table / descriptives), with
  `scitex_stats.validate_apa()` and `scitex-stats validate-apa` as the
  checked contract.
- Data-driven test selection: `check_applicability()`, `recommend_test()`,
  `run_all_applicable()` — with `scitex-stats tests check-applicability` /
  `recommend-test` / `execute-all` and their MCP tools — plus explicit
  assumption checks, thresholds and Q-Q data.
- Neutral, versioned plot spec per result; the Statistics app gains a Plot
  view (FigRecipe or plain matplotlib) with `Open in FigRecipe`.
- Statistics Django app: a three-pane workflow shell (`1. Data Input` /
  `2. Test Selection` / `3. Results`) served by `scitex-stats gui serve`
  standalone or mounted by the hub under its own prefix.

### Changed
- `full_report` bootstrap CIs are seeded by default: `seed=42`, a fresh
  `numpy.random.default_rng(seed)` per interval (previously unseeded).
  `random_state=` is a deprecated alias. New `ci_method` field.
- `run_test` / MCP `run_test` raise `InputIntegrityError` on infinite,
  non-numeric or empty inputs, and on NaN in contingency tables; NaN in
  paired designs is excluded pairwise (MCP `data_file` columns were
  previously `dropna()`-ed independently, which misaligned pairs).
- Demo and docstring code uses `numpy.random.default_rng` instead of global
  `np.random.seed` state.
- The app's dependency floors now name the releases that actually ship the
  shared shell: `scitex-app>=0.24.0` (ships `scitex_app/app_shell.html`) and
  `scitex-ui>=0.22.0` (ships the `scitex_static` tag library behind
  `{% app_static %}` and the canonical project selector). The previous
  `scitex-ui>=0.19.0` floor could resolve a scitex-ui whose shell cannot
  render the app template at all, and `scitex-app` was not declared.
- `scitex-stats tests`: the leaf nouns `applicability` and `run-all` are now
  the verb-first `check-applicability` and `execute-all`. The old spellings
  stay available as hidden deprecation aliases that forward to the new
  commands, so existing scripts keep working.

### Fixed
- Standalone app: `scitex_stats._django.settings` never installed
  `scitex_app`, so every page of `scitex-stats gui serve` answered 500 with
  `TemplateDoesNotExist: scitex_app/app_shell.html` while the test suite
  (which configures its own `INSTALLED_APPS`) stayed green. Fixed, and
  pinned by a test that boots the real settings module in a child
  interpreter.
- Assumption-check statistics and thresholds now render in APA form
  (`W = .97, p ≥ .05, α = .05`), routed through the library formatter
  rather than app-side string building.
- `×` renders on phones, `p` is italic inside "p-value", and Sample /
  Recommend preselect the primary test.
- Development gates: the APA test modules mirror their source packages
  (PS-202/PS-204), the cross-package import gate is regenerated (PS-140),
  and the `.po` reader the i18n test needs is a declared `[dev]` dependency.

## [0.2.24] — 2026-06-03

### Added
- `tests/agreement` category (new) with two inter-rater agreement scalars:
  - `test_kendalls_w(matrix, use_abs=False)` — Kendall's coefficient of
    concordance W ∈ [0, 1] (Kendall & Babington Smith 1939). Accepts a
    2-D `(n_subjects, k_raters)` matrix or a long-format DataFrame with
    `(subj, rater, score)` triples. Returns `W`, `S`, `n`, `k`, χ² and
    p-value via the Friedman χ² approximation, plus effect-size
    interpretation and a publication-ready `formatted` string.
  - `test_icc(matrix, form="3,k")` — ICC (Shrout & Fleiss 1979).
    Computes all six classical forms from one variance decomposition
    (McGraw & Wong 1996) and surfaces the selected form at the top level;
    F / p / df / CI / effect size / Koo & Li 2016 interpretation in the
    result dict.
- Top-level aliases `sts.test_kendalls_w` and `sts.test_icc` via the
  PEP-562 lazy attribute loader.
- 27 pytest tests in `tests/scitex_stats/tests/agreement/`.

## [0.2.22]

- feat(schema): publish the `scitex_stats._dataclasses` Stats schema (`_Stats.py`) — previously only on develop, which forced scitex-io's bundle to git-pin scitex-stats. Publishing it lets scitex-io depend on `scitex-stats>=0.2.22` and exercises the `.stats.zip` bundle integration on PyPI.
- (incorporates the figrecipe-optional R4 changes merged in #43)

## [0.2.20] — 2026-05-26

### Changed
- Moved 14 ``_demo_*.py`` scripts from ``src/scitex_stats/**`` to
  ``examples/**`` and stripped the ``scitex`` umbrella import from each;
  demos now run against the leaf package + sci-stack alone.
- Stripped the umbrella import from 24 in-source ``__main__`` demo
  blocks across ``_test_*``, ``effect_sizes``, ``posthoc``, ``power``,
  ``correct``, and ``_utils``. Production code at the top of each file
  is untouched; only the ``run_main()``/demo path was rewritten.
- Rewired ``tests/integration/test_demos.py`` into two parametrized
  buckets (file-path ``examples/**`` + dotted-path ``python -m``) so
  every demo still smoke-runs in CI without ``pytest.skip``.
- Suppressed the pre-existing ``docutils`` warning backlog (~65
  duplicate-target ``[1]``/``[2]`` reference labels across
  ``_test_*.py`` docstrings) at the sphinx config level so ``-W`` on
  PR builds no longer fails on the pre-existing issues.

### Fixed
- Replaced ``monkeypatch.setattr("sys.stdin", io.StringIO(…))`` in
  ``test_stats.py`` with a real temp-file-backed ``sys.stdin``
  reassignment in ``try/finally``. Closes PA-306 / STX-NM002.
- ``test_audit_all_clean`` now masks the 2164-finding PA-307 backlog
  via the framework's own ``skip_rules`` channel (UserWarning surfaces
  exactly what's masked) so the gate stops blocking new work while
  the backlog is being cleared. Not ``pytest.skip`` — the gate still
  catches new non-PA-307 violations.

## [0.2.18] — 2026-05-12

### Fixed
- `_export_report_html` crashed on pandas ≥ 2.2 — `Styler.applymap`
  was removed; now uses `Styler.map` with a fallback.
- Six standalone-demo modules (`effect_sizes/_cliffs_delta`,
  `_cohens_d`, `_epsilon_squared`, `_eta_squared`,
  `_prob_superiority`, `power/_power`) raised `NameError` on `stx`
  because `run_main()` referenced scitex without importing it.
- Seven more in-source demos (anova, anova_2way, anova_rm, shapiro,
  ks_1samp, ks_2samp, kruskal, mannwhitneyu, dunnett, games_howell,
  tukey_hsd) called the unsupported
  `convert_results(return_as="excel" / "csv")` and crashed; replaced
  with pandas `.to_excel` / `.to_csv` direct calls.
- Cleaned up a dead duplicate `_correct_fdr_.py` (and its bound
  demo) — the package always imported from `_correct_fdr` (no
  trailing underscore).
- `_figrecipe_integration.annotate` over-unwrapped `RecordingAxes`
  to raw `matplotlib.Axes`, which broke every direct figrecipe
  caller (`add_stat_annotation` lives on `RecordingAxes`).

### Changed
- Refactored `_utils/_normalizers.py` (927 LOC) into three focused
  modules — `_normalize_core`, `_export_files`, `_export_reports` —
  with the original kept as a thin re-exporting orchestrator (~58
  LOC). Public API unchanged.
- Extracted runnable demos out of `_correct_fdr`,
  `_correct_bonferroni`, `_correct_sidak`, `_correct_holm` into
  sibling `_demo_*.py` files. Each core file now fits the
  512-LOC project budget.
- README mirrors scitex-io's structure (self-contained Quick Start,
  numbered `## How it works` with mermaid, mermaid Available Tests
  + decision flowchart). README badge + `codecov.yml` now pin
  develop as the canonical branch.
- Examples converted from `.py` scripts to executed `.ipynb`
  notebooks; CI runs them end-to-end via `jupyter nbconvert
  --execute`.

### Added
- 23-module demo smoke test (`tests/integration/test_demos.py`)
  drives every `_demo_*.py` and `__main__`-bearing `_test_*.py`
  module end-to-end via `python -m …` in tmp_path.
- Direct unit tests for `_plot_anova_2way`, `_plot_holm`,
  `_plot_bonferroni`, `_plot_sidak`, `_plot_fdr`, `_decision_tree`
  render helpers, `_dispatch` branches, every `_mcp/_handlers/*`
  module, every `_cli/*` click subcommand, the `_server.py` FastMCP
  tools, and numpy-path tests for `_circular`/`_nan`/`_real`.
- Subprocess coverage tracking via `tests/conftest.py`
  (`COVERAGE_PROCESS_START` + `COVERAGE_FILE` pin + idempotent
  `.pth` shim) so demo subprocesses contribute coverage.
- `codecov.yml` with `branch: develop` + auto-target gates.
- `.scitex/dev/config.yaml` whitelisting `codecov.yml` and `logs/`.

### Coverage
- Project Codecov: **~32 % → ~90 %** without `omit` shortcuts.

## [0.2.17]

- Initial CHANGELOG entry — see git log for prior history.
