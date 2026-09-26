---
description: |
  [TOPIC] APA 7 Reporting
  [DETAILS] exact APA 7 output line per test (result["apa"]), the rule behind
  each formatting choice with its Publication Manual section, the table and
  descriptives forms, and validate_apa() for checking manuscript text.
tags: [scitex-stats-apa7-reporting, scitex-stats]
---

# scitex-stats — APA 7 Reporting

Every `run_test(...)` result (and anything passed through `to_json_safe`)
carries `result["apa"]`, built from one rule table
(`scitex_stats._utils._apa._rules.RULES`). `validate_apa()` reads the same
table, so the formatter and the validator cannot drift. The raw values
(`statistic`, `pvalue`, `df`, CI bounds) stay unrounded in the result.

References are to the *Publication Manual of the American Psychological
Association* (7th ed., 2020): §6.36 decimal fractions, §6.43 statistics in
text, §6.44 statistical symbols (Table 6.5), §6.45 spacing and punctuation,
§7.14 table notes (asterisks), §3.6–3.7 (JARS: sample size, effect sizes, CIs).

## What `result["apa"]` contains

| Key | Content |
|-----|---------|
| `plain` / `html` / `latex` / `segments` | The APA line. `segments` are `{text, kind}` with kind `text`, `sym` (italic Latin), `greek` (upright), `sub`, `sup`. |
| `table` | Rows `{key, label, value, label_plain, value_plain}` for a results table: statistic, *df*, *z*, *p*, exact *p*, effect size, interpretation, 95% CI, *n* per group / *N*, power, significance (asterisks allowed here), notes (Welch, Yates, Levene), H0. |
| `descriptives` | `{columns, rows, plain, html, segments}`: group, *n*, *M*, *SD* (or *Mdn*, *IQR* for rank-based tests). Present when `run_test` saw the data. |
| `rule`, `reference` | The rule key and the source the layout follows. |
| `statistic`, `df`, `p_value`, `effect_size`, `ci` | Display strings. |

```python
import scitex_stats as ss
r = ss.run_test("ttest_ind", data=[5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7],
                data2=[6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2])
r["apa"]["plain"]              # 't(14) = −6.35, p < .001, d = −3.18, 95% CI [−4.65, −1.70], n₁ = 8, n₂ = 8'
r["apa"]["descriptives"]["plain"]  # 'x (n = 8, M = 5.46, SD = 0.38); y (n = 8, M = 6.66, SD = 0.38)'
ss.validate_apa("t(14) = -6.354, p = 0.0000, d = 3.2")["violations"]
```

CLI: `scitex-stats validate-apa "t = 2.1, p = 0.04"` (exit 1 on violations,
`--html` to check italics, `--result result.json` to compare with a result).
MCP: tool `validate_apa(text, html, result)`.

## Global rules

| Rule | Choice | APA 7 |
|------|--------|-------|
| Symbols | Latin statistical symbols italic (*t*, *F*, *U*, *T*, *H*, *D*, *W*, *z*, *r*, *p*, *d*, *g*, *V*, *OR*, *n*, *N*, *M*, *SD*, *Mdn*, *IQR*, *df*); Greek upright (χ², τ, η², ε², ω², δ, α); sub/superscripts upright (*n*₁, *r*ₛ). "CI" is an abbreviation, not italic. In the app, table labels and descriptives headers use the same segments. | §6.44, Table 6.5 |
| Minus | U+2212 (−), never a hyphen, in text, CIs and tables. | §6.45 |
| Spacing | Spaces around =, <, >. | §6.45 |
| Decimals | Statistics, effect sizes, CIs, *M*, *SD* to two decimals. | §6.36 |
| *p* | Three decimals (`p = .032`); `p < .001` below .001; never `p = .000`; `p > .999` at the top. The unrounded value stays in `pvalue` and the table's "Exact *p*" row. | §6.36, §6.43 |
| Leading zero | Omitted for values that cannot exceed 1 (*p*, *r*, *r*ₛ, τ, η², ε², *V*, Kendall's *W*, Shapiro–Wilk *W*, *D*, *P*(*X* > *Y*), power); kept otherwise (*t*, *d*, *OR*, *M*, *SD*). | §6.36 |
| *df* | In parentheses after the symbol; integers as integers; fractional *df* (Welch, Brunner–Munzel) to two decimals; *F*(*df*₁, *df*₂); χ²(*df*, *N* = total). | §6.43 |
| Effect size | Reported with each test that has one, followed by its CI when the library computes it: `95% CI [lower, upper]`. No CI is invented. | §6.43, §3.7 |
| Sample size | *n*₁, *n*₂ for two independent groups; *n* for paired/one-sample; *N* for k groups and contingency tables (inside the parentheses for χ²). Correlations carry it in *df* = *N* − 2. | §6.44 (N vs n), §3.6 |
| Asterisks | Never in the inline line; the table's Significance row may show them. | §6.43, §7.14 |
| Order | statistic(*df*) = value, [*z*], *p*, effect = value, CI, sample sizes. For correlations the CI follows *r* (the effect is the statistic). | §6.43 examples |

## Exact output per test

Fixture: `A = [5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7]`,
`B = [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2]`,
`B2 = [6.3, 4.8, 7.1, 7.9, 5.6, 6.9, 8.4, 5.2]`,
`C = [5.9, 6.2, 5.5, 6.4, 6.1, 5.8, 6.0, 6.3]`, table `[[12, 5], [4, 9]]`.
Every line below is asserted verbatim in `tests/scitex_stats/_utils/test__apa.py`
and equals `RULES[...].example`.

| `run_test` name | Call | Plain output | Descriptives | Reference |
|-----------------|------|--------------|--------------|-----------|
| `ttest_ind` | A, B | t(14) = −6.35, p < .001, d = −3.18, 95% CI [−4.65, −1.70], n₁ = 8, n₂ = 8 | *M*, *SD* | §6.43; *d* Table 6.5; CI of *d*: Hedges & Olkin (1985) normal approximation |
| `ttest_welch` | A, B2 | t(8.21) = −2.25, p = .054, d = −1.12, 95% CI [−2.18, −0.07], n₁ = 8, n₂ = 8 | *M*, *SD* | §6.43, §6.36 (fractional *df*); table note says Welch's correction was used |
| `ttest_rel` | A, B | t(7) = −7.28, p < .001, d_z = −2.58, 95% CI [−4.01, −1.14], n = 8 | *M*, *SD* | §6.43; *d*_z for paired designs (Lakens, 2013) |
| `ttest_1samp` | A, popmean=5 | t(7) = 3.46, p = .011, d = 1.22, 95% CI [0.31, 2.14], n = 8 | *M*, *SD* | §6.43; *d* = (*M* − μ₀)/*SD* |
| `mannwhitneyu` | A, B2 | U = 17.00, z = −1.58, p = .127, r_rb = −.47, n₁ = 8, n₂ = 8 | *Mdn*, *IQR* | Table 6.5 (*U*); *z* and effect *r* as in Field (2018, *Discovering Statistics*, ch. 7); *r*_rb = 2*U*/(*n*₁*n*₂) − 1 (Kerby, 2014) |
| `brunner_munzel` | A, B2 | W_BM(8.06) = 1.61, p = .145, P(X > Y) = .25, n₁ = 8, n₂ = 8 | *Mdn*, *IQR* | Brunner & Munzel (2000): statistic ~ *t*(*df*); layout §6.43 |
| `ks_2samp` | A, B2 | D = .62, p = .087, n₁ = 8, n₂ = 8 | *Mdn*, *IQR* | §6.36 (*D* ≤ 1), §6.43 |
| `ks_1samp` | A | D = 1.00, p < .001, n = 8 | *Mdn*, *IQR* | §6.36, §6.43 |
| `wilcoxon` | A, B2 | T = 6.00, z = −1.68, p = .102, r_rb = −.67, n = 8 | *Mdn*, *IQR* | Table 6.5 (*T*: Wilcoxon); *z*/*r* as in Field (2018, ch. 7). One-sided tests report *W*₊. |
| `anova` | A, B, C | F(2, 21) = 23.36, p < .001, η² = .69, N = 24 | *M*, *SD* | §6.43 (*F*(2, 27)), Table 6.5 (η²); table note: Levene's *p* |
| `kruskal` | A, B, C | H(2) = 16.72, p < .001, ε² = .70, N = 24 | *Mdn*, *IQR* | Table 6.5 (*H*); *df* = *k* − 1 |
| `friedman` | A, B, C (as columns) | χ²_F(2, N = 8) = 14.25, p < .001, W = .89 | *Mdn*, *IQR* | §6.43 χ² layout with *N* = subjects; χ²_F per Field (2018, ch. 7); Kendall's *W* |
| `pearson` | A, B | r(6) = .24, 95% CI [−.56, .81], p = .569 | *M*, *SD* | §6.43 (*r*(28) = .45, *df* = *N* − 2), §6.36 |
| `spearman` | A, B | rₛ(6) = .33, p = .420 | *Mdn*, *IQR* | Table 6.5 lists *r*ₛ for Spearman; ρ is reserved for the population correlation |
| `kendall` | A, B | τ_b = .21, p = .548, N = 8 | *Mdn*, *IQR* | Table 6.5 (τ); no *df* convention, so *N* is given |
| `shapiro` | A | W = .97, p = .921, n = 8 | *M*, *SD* | §6.36 (*W* ≤ 1), §6.43 |
| `chi2` | table | χ²(1, N = 30) = 3.23, p = .072, V = .33 | — | §6.43: χ²(4, *N* = 90) = 0.89, *p* = .926; table note: Yates' correction on 2×2 |
| `fisher` | table | p = .063, OR = 5.40, 95% CI [1.12, 26.04], N = 30 | — | §6.43 (exact *p*), Table 6.5 (*OR*) |

Plain text uses Unicode sub/superscripts where Unicode has them (₁ ₂ ₛ ²) and
`_x` otherwise (`r_rb`, `d_z`, `τ_b`, `χ²_F`, `W_BM`); HTML and LaTeX use real
subscripts.

## Choices where APA 7 is silent or ambiguous

- **Spearman**: *r*ₛ (Table 6.5), not ρ.
- **Wilcoxon statistic**: *T* (Table 6.5 "Wilcoxon's test"), not scipy's "W".
- **Nonparametric effect size**: rank-biserial *r*_rb (library's measure), with
  *z* from the tie-corrected normal approximation (no continuity correction).
  Sign: positive when the first group tends to be larger, for both
  Mann–Whitney and Wilcoxon.
- **Friedman**: χ²_F with *N* (subjects) inside the parentheses, like χ².
- **Brunner–Munzel**: no APA symbol exists; *W*_BM with its Satterthwaite *df*.
  scipy's sign convention (positive when the second group tends to be larger).
  Complete separation gives NaN statistic and *p* (scipy), shown as "—".
- **Kendall's τ**: *N* after *p* instead of *df*.
- **Decimals**: two for all statistics (§6.36 allows fewer/more "as needed");
  *p* always three.
- ***p* ≥ .9995**: `p > .999`.
- **CI of *d***: normal approximation (Hedges & Olkin, 1985), not the
  noncentral-*t* interval.
- **ANOVA effect size**: η² (the library's measure); ω² is less biased but not
  computed yet.

## Validator codes

`APA-P-ZERO`, `APA-P-SMALL`, `APA-P-DECIMALS`, `APA-LEADING-ZERO`,
`APA-MISSING-ZERO`, `APA-DECIMALS`, `APA-MINUS`, `APA-SPACING`, `APA-ASTERISK`,
`APA-MISSING-DF`, `APA-DF-PAIR`, `APA-CHI2-N`, `APA-MISSING-P`,
`APA-MISSING-EFFECT`, `APA-MISSING-N`, `APA-NOT-ITALIC`, `APA-GREEK-ITALIC`,
`APA-MISMATCH` (text differs from `result["apa"]["plain"]`). Each violation
carries `message`, `fix`, `excerpt` and `reference`.
