---
description: |
  [TOPIC] CSV input
  [DETAILS] Auto/manual delimiters, quoted numeric cells, column import and source-row integrity.
tags: [scitex-stats-csv-import, scitex-stats]
---

# CSV input in the Stats app

Keep manual numeric groups in their boxes, or open **Project data…** / **Import
CSV…** for a compact import dialog. Choose a project/local file, review the
separator and preview, select numeric columns, then **Import selected**. Even
a single numeric column waits for this confirmation. Previewing does not
replace existing groups; Cancel/Close/Escape retain the preview and selected
columns for reopening. Native dialog modality keeps background controls inert.

**Auto** estimates Tab, Comma, Semicolon, Pipe, or consistent whitespace using
record widths. The indicator says **estimated**, **your choice**, **.tsv
default**, or **single column**, as appropriate. Equally plausible punctuation
separators require an explicit choice; structured tabs keep their documented
priority, with an alternatives notice. One-record estimates and inconsistent
widths are reported rather than presented as certain. A hard choice reparses
the pending preview without changing group boxes until Import.

Quoted cells can contain delimiters, and doubled quotes escape a literal quote.
The browser expects one CSV record per line. It does not support multiline
quoted cells. Malformed quoting must remain nonnumeric: never remove quotes to
turn `1"2"3` into `123`. Missing/invalid observations prevent tests that require
matching source rows; keep the original row correspondence when correcting data.

For Python file inputs, `resolve_columns(..., sep=...)` accepts an explicit
separator. Auto ambiguity raises `ValueError` asking for an explicit `sep`.
Whitespace parsing respects quoted labels, and UTF-8 BOMs are removed.

Source: `_django/static/stats/js/app.js` owns the browser parser, chooser and
row-integrity checks; `_utils/_csv_support.py` owns Python file parsing.
Regression evidence: `_django/static/stats/js/test_csv_import.cjs` under the
tests tree exercises the shipped client script; `_utils/test__csv_support.py`
checks real file-backed column resolution. Confirm deployed behavior with an
actual file upload as well as these tests.

Native-browser regression: `_django/check_import_dialog_browser.py` under the
tests tree runs a disposable standalone app at desktop/phone sizes and checks
modal focus, Escape/return focus, cancellation, selected-column import and
theme colors. See `docs/csv-input.md` for the invocation.


## MCP file input

The registered `run_test` tool accepts `data_file`, `columns` and optional
`sep`, using the same leaf file parser as its handler. For an ambiguous
semicolon/comma file, explicitly choose semicolon:

```json
{"test_name": "ttest_paired", "data_file": "ambiguous.csv", "columns": ["x", "y"], "sep": ";"}
```

Omit `sep` or pass null for existing Auto behavior. Ambiguous Auto input
fails explicitly; choosing a wrong delimiter still fails when selected
columns are absent. Explicit overrides are recorded as
`provenance.source.sep`, alongside the existing file digest and columns,
without changing the source file. Every successful file result also includes
`provenance.source.sep_used`, the token chosen by the leaf parser for that read,
including Auto and the `.tsv` tab contract. A space token (`" "`) means
whitespace runs; an explicit regex token is preserved. `source.sep` still
records only an explicit request. Both fields are covered by the receipt.
Actual schema,
ambiguous-file calculation/error and input-preservation checks live in
`tests/scitex_stats/_mcp/_handlers/test__run_test.py`,
`tests/integration/test_mcp_describe_stdio.py` and
`tests/scitex_stats/_mcp/_handlers/test__run_test.py`.
