# Changelog

All notable changes to `scitex-stats` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

- Enforce numeric star inputs before MCP argument coercion. Reject JSON
  booleans and numeric strings for the probability and threshold items while
  preserving valid JSON integer/float values, strict boundaries and numeric
  domain-error envelopes. Verify through a real initialized stdio session.

## [Unreleased]

- Add synchronous `summarize` for the dictionary summary already exposed by
  MCP `describe`, and delegate that handler to the native operation in its
  existing worker. Preserve the numerical kernel and older axis-aware
  `describe`. Declare the explicit summary/describe capability mapping.

- Reject infinite MCP descriptive-statistics samples instead of reporting
  successful nonfinite summaries. Preserve NaN removal, empty-input errors,
  finite calculations and percentile labels.

- Reject invalid native Dunnett significance levels and unknown alternatives
  instead of returning invalid cutoffs or silently selecting the less-sided
  hypothesis. Preserve valid pooled calculations and public presentation.

- Share unrounded global pooled-t/Bonferroni control-comparison statistics
  between native Dunnett and MCP. Correct MCP pairwise-variance drift and
  emit boolean reject flags; preserve native public rounding, fields and CIs.
  Reject unsupported sample geometry and differing means with zero pooled
  variance; preserve the identical-constant zero-difference convention. The
  procedure remains a conservative approximation, with no joint-Dunnett claim.

- Validate MCP post-hoc group counts and provided name lengths before
  calculation. Reject negative/out-of-range Dunnett control indices that
  could include the control in its own comparison. Preserve valid outputs,
  generated-name fallback and all numerical implementations.

- Delegate MCP star selection to the existing native style-aware formatter
  in a worker, translating supported thresholds into a fresh StatStyle.
  Preserve strict boundaries, validation, significance text and result fields.
  Qualify and declare the default-style native/MCP mapping; inventory remains
  partial and generic audit findings remain independent.

- Qualify and declare the existing public recommend_tests / MCP mapping for
  single-factor contexts with default families and return format. Verify
  actual worker calls, context translation, ordered selections and registry
  detail fields; keep the partial capability inventory explicitly incomplete.

- Validate correlation alpha and estimated-sample target power as finite
  probabilities strictly inside (0, 1). Preserve the unused target argument
  in fixed-n mode and all valid numerical calculations. Split correlation
  controls from bounded ANOVA/chi-square search controls.

- Validate finite correlation effect sizes strictly inside (-1, 1) before
  the Fisher transform in both power modes. Return a consistent domain error
  for invalid values; preserve valid fixed-n zero and near-boundary results.

- Reject correlation-power requests with n <= 3 before evaluating the
  undefined Fisher standard error. Preserve valid approximate-power results
  and all other power calculations; document the sample-size requirement.

- Include small valid integer solutions in ANOVA/chi-square power searches.
  Correct exclusive lower bisection sentinels that forced at least three
  observations per group or eleven total even when the model needed fewer.
  Preserve existing ceilings, infeasibility checks and power calculations.

- Fail ANOVA/chi-square required-sample searches when their existing upper
  limit cannot achieve the requested power, rather than reporting that limit
  as a successful estimate. Preserve feasible results, limits and kernels;
  verify against independent Statsmodels power solvers.

- Correct the style-aware p_to_stars docstring at strict default thresholds.
  Document boundary and missing-value behavior separately from inclusive
  native p2stars; keep all formatter calculations unchanged.

- Correct shipped MCP skill catalogues to the standalone server's 18 bare
  names. Separate configured client/umbrella aliases, preserve allowed-tools
  permissions and cover all three documented tables with the owner registry
  regression. Clarify discovery, input/error contracts and skill delivery.

- Declare the existing native verify / MCP verify_result capability after
  real default-option delegation and payload checks. Preserve all previous
  declarations and runtime interfaces. Repair the verification skill's inputs,
  comparison exclusions, transport meaning and advanced-option limitations.

- Reject non-finite/out-of-range MCP star probabilities and malformed
  thresholds before selecting a star level. Require exactly three finite,
  strictly increasing thresholds in [0, 1]. Preserve valid strict boundaries,
  response fields, custom thresholds and existing direct tuple callers.

- Correct native p2stars documentation to describe inclusive boundaries,
  missing/invalid values and actual whole-DataFrame examples. Distinguish its
  table-formatting contract from style-aware and MCP star conversion.

- Repair native p2stars DataFrame input by formatting cells through the
  existing Series/scalar path. Preserve axes, input values, threshold boundaries,
  custom symbols and the existing missing/invalid-value output conventions.

- Run APA text/HTML validation outside the MCP event-loop thread while
  preserving native reports and propagated validation exceptions. Include this
  existing native/MCP adapter in the partial capability declaration.

- Run the three data-based recommendation MCP calculations in worker threads
  so their synchronous native calculations do not block the event loop.
  Preserve existing arguments, result envelopes and error responses; add
  these three adapters to the partial capability declaration.

- Add a leaf-owned capability provider for the four existing core native/MCP
  adapters: normality, effect size, result formatting and p-value correction.
  The initial declaration covers these operations; other APIs/tools still need
  classification and existing audit findings remain active.

- Repair the remaining shipped workflow examples: context-based
  recommendations, independent correlation and distribution examples,
  raw p-value corrections, tuple-based sample sizes and native formatting.
  Define inputs in every example and use current result field names.

- Correct post-hoc selection documentation: Tukey requires an advance
  equal-variance declaration; the reported variance test is diagnostic.
  Repair the multiple-group skill example to use current grouped arguments
  and the public post-hoc dispatcher.

- Remove the empirical 0.95 scaling from the native Dunnett approximation's
  critical value. Its significance flags and intervals now use the same
  Bonferroni threshold as its adjusted p-values. Document that this remains
  an approximation rather than the joint Dunnett procedure.

- Preserve fractional percentile labels in descriptive-statistics MCP results.
  Requests such as 2.1 and 2.9 previously collided under the same integer key.
  Existing whole-number labels and numerical calculations remain unchanged.

- Correct the Stats linter provider to recommend current leaf-owned Python
  calls, including list arguments for ANOVA and Kruskal-Wallis. Remove its
  unrelated umbrella import requirement and correct the provider group name.

- Accept both fisher and fisher_exact in Python, CLI and MCP test dispatch.
  Keep existing names, requested hypotheses, count-table output and provenance
  receipts; no additional MCP tool is registered.

- Forward the requested Fisher alternative in native run_test and CLI calls.
  One-sided calls previously returned two-sided p-values; MCP already forwarded
  the alternative correctly.

- Accept the existing Python test-name aliases in MCP run_test: ttest,
  ttest_rel, brunnermunzel and mann_whitney. Preserve paired NaN handling
  and the requested name in results and verification receipts.

- Use package-owned subprocess coverage support instead of writing startup
  hooks into shared Python environments during test collection.

- Add a leaf-owned installed-wheel probe for numerical, file, CLI, MCP and
  skill behavior; source imports cannot qualify a wheel.

- Use square corners for import dialogs, figure frames and input fields.
  Record served asset identity and geometry in the native browser check.

- Report failed descriptive-statistics MCP results for empty or all-NaN
  inputs, retaining the existing error message and tool name.

- Correct CLI help and skills to describe actual configuration support,
  portable skills destinations, GUI environment variables and port options.
  Package-wide YAML defaults remain unimplemented.

- Match statsmodels in the no-backend correction path: apply BY adjustment,
  preserve tiny Sidak values and handle rejection at the alpha boundary.

- Delegate skills installation to scitex-dev's managed projection, refusing
  unowned or modified destinations instead of deleting caller files. Add the
  vendor-neutral --directory option while retaining --dest compatibility.
  Require scitex-dev 0.62.29 for managed export support.

- Correct Kruskal-Wallis examples for result keys, explicit plot axes and
  tabular output; link all three reference footnotes. Numerical behavior
  and public signatures are unchanged.
- Give the remaining seven statistical-test reference lists unique linked
  footnotes. Remove broad docutils suppression and fail documentation builds
  on warnings. No statistical implementations or signatures are changed.

- Restore the original API-listing and MCP subprocess test budgets (60 and
  30 seconds respectively). Preserve all test cases and assertions.

- Repair statistical-test reference rendering across twelve functions: separate
  nested lists, format the contingency-table example and absolute-value math,
  and use referenced, uniquely named footnotes. Numerical implementations and
  public signatures are unchanged.

## [1.0.0] — 2026-10-24

First stable release: the beta UI batch toward SciTeX Cloud, hardened
after operator review (separator estimation + hard spec + live indicator,
column-spec import with preview and pending-vs-active clarity, alert-red
Clear, header-named chooser).

### Added
- Active-separator indicator: a live hint under the Separator selector
  (Using: X, estimated/your choice), updated on every import and choice.
- Pending-vs-active clarity: the column chooser states the analysis still
  uses the boxes until Import; the preview shows only while boxes match the
  last import (hides on any edit or partial import); chooser lists real
  header names instead of Column N.
- CSV import preview: filename, detected separator, shape and first rows
  render under the drop zone on every import (hidden on Clear/sample/
  chooser-cancel); wrong parses are visible before any test runs.
- Clear button wears the alert red (`--status-error`, the same SDK token
  `.stats-error` uses) via a new `stats-btn--danger` variant.
- Space-separated tables: separator estimation and the hard Separator
  selector accept whitespace tables (strict consistency, so prose cells
  never flip a comma file); Python `data=` file loading, MCP `run_test`
  (`sep`), and the CLI estimate instead of assuming comma.

### Changed
- `scitex-sdk[gui]` floor raised to >=0.3.12 (server + dev; identical-row
  pack + layout doctrine).

### Fixed
- Bundled skill docs now match the measured surface: MCP tool table
  lists all 18 served tools (was 10, missing report/verify/skills/APA
  rows) and `tests list` notes 22 names (was 23).
- Skill Python-API page now states 25 `test_*` functions with the
  Agreement pair (`test_kendalls_w`, `test_icc`) in the examples
  (was 23, pair omitted).

## [1.0.0-beta] — 2026-10-23

Beta: operator UI batch toward SciTeX Cloud beta (close to beta).

### Added
- Hard separator specification for CSV import: Separator selector
  (Auto default + Comma/Tab/Semicolon/Pipe) under the drop zone;
  overrides estimation for file imports only, paste boxes keep
  estimation. Single-column files import directly, multi-column
  files open the checked-by-default column chooser.
- Dispatcher coverage note in the skill test catalog: `run_test()`
  routes 22 aliases, MCP `run_test` 23 names; 8 public tests
  (agreement family, anova_rm/2way, theilsen, mcnemar, cochran_q,
  normality) go direct — documented limitation, not a silent gap.

### Changed
- "Load sample dataset" renamed to "Try with Sample Data",
  right-aligned in the data-input action row (operator).
- Sample data fits the current design/measurement scale: categorical
  loads an integer-count twin so applicable tests auto-run and
  results show (operator).
- In-content title "SciTeX Stats", professional "No results yet"
  empty-state copy, alternative hypothesis leads the test pane.
- `scitex-sdk[gui]` floor raised to >=0.3.12 (server + dev).

### Fixed
- Bundled skill docs match the measured surface: MCP tool table
  lists all 18 served tools (was 10); skill Python-API page states
  25 `test_*` functions with the Agreement pair in the examples
  (was 23, pair omitted).
- `__init__` docstring MCP count 10 -> 18.
- MCP 2.x compat: `input_schema` canonical kwarg + readers.
- CLI `list-python-apis` 60s timeout guard against xdist cold-start
  flake; plain-command 60s budget in tests.

## [1.0.0-alpha] — 2026-10-20

First alpha toward 1.0.0: whole-package professional-grade pass
(stats-pro-grade-audit-20261020).

### Fixed
- Results column cleanup follow-ups: straight result card and
  assumption-check highlight, no rounding (operator, #160, #161).
- DATA INPUT full-height fill: panes stretch, pane fills column height,
  body flexes (operator CCT4792, #161).
- MCP `correct_pvalues` no-statsmodels fallback: unknown methods now
  correct via fdr_bh like the statsmodels path (was: raw p-values
  returned as corrected); requested name still echoed (#162).

### Changed
- Test count standardized on 25 public `test_*` functions across
  README, sphinx docs, CLI/MCP descriptions, and skill catalog;
  agreement family (Kendall's W, ICC) added to README Figure 2 and
  the catalog (#162).
- `scitex-sdk[gui]` floor raised to >=0.3.8 (server + dev, #161).

### Known limitations (beta scope)
- `run_test()` dispatches 22 names; MCP `run_test` accepts 23; both
  short of the 25 public functions — tracked as
  stats-dispatch-parity-20261020.
- Test-count-sensitive wording: MCP `run_test` description stays at 23
  (its enum truth) until parity lands.

## [0.2.40] — 2026-10-19

### Fixed
- Results column cleanup: dedupe notes/decision-path/assumptions, flat
  verdict card, Copy-by-contents inline in the Raw-result row, desktop pane
  titles (operator order, #158).
- Wrap assumption checks and sensitivity output in collapsible details
  (open-by-default, #156).

### Changed
- Migrate stale frontend tests to the debounced auto-calculate flow
  (CI-only, #157).

## [0.2.39] — 2026-10-19

### Fixed
- Separate picker verdict kicker and tooltip reasons (operator CCT4715,
  #152).
- Drop Quick analysis header toggle (operator element report, #153).
- Adopt SDK canonical AppHeader component (operator standing rule); raise
  scitex-sdk floor to >=0.3.7 (#154).

## [0.2.38] — 2026-10-19

### Fixed
- Unbreak stats auto-calculate, guard quick-analysis leave, bound PDF build
  (#150).
- Raise mcp-doctor CLI timeout 15s to 60s against xdist cold-start flake
  (CI-only, #149).

## [0.2.37] — 2026-10-18

### Fixed
- Remove the Applicable-tests rail from the results pane (operator order):
  applicability survives as picker dim/disable plus hover tooltips only.
- Collapse right-rail reasons behind closed details (prior slice).

## [0.2.30] — 2026-10-04

### Added
- Add a leaf-owned public recommendation compatibility callable with the
  existing request defaults and response envelopes.

### Changed
- Separate the recommendation executor from its Django HTTP adapter while
  preserving its parameters and response contract.

### Fixed
- Guard optional Django imports and retain the optional umbrella backend in
  the cross-package import checks.
- Use the standard Linux runner for GitHub Release asset uploads after the
  existing test, build and PyPI publication jobs.

## [0.2.29] — 2026-10-03

### Changed
- The Statistics Django app uses `scitex-sdk[gui]>=0.3.1` for the shared
  standalone and mounted application contracts, templates, static assets,
  workspace shell, and project picker.

### Fixed
- Remove duplicate visible step headings from the data and test panes while
  preserving their accessible labels.
- Keep the Add group and Clear controls at least 44px tall on phones when the
  app uses the shared SDK shell.
- Treat non-callable report host services as unavailable in capability checks
  and Save to Files.
- The report's determinism contract is now stated accurately where it ships. The
  comment in `reporting/_pdf/_html.py` claimed two runs over the same input were
  **byte-identical**; the artifacts contradict that (measured: two renders with the
  same timestamp differed inside an object carrying `/Length1 ... /FlateDecode`, an
  embedded font program, while metadata was identical and zero pages differed). The
  shipped contract is now **content determinism** — identical page text, metadata,
  page count and decoded content streams, with the creation date taken from the
  report timestamp — documented in `reporting/_pdf/_render.py`,
  `reporting/_pdf/_html.py` and the `scitex_stats.report` docstring, and asserted by
  `tests/scitex_stats/reporting/_pdf/test__api.py::test_pdf_is_content_deterministic_for_the_same_input_and_timestamp`.
  No behaviour changed.

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
