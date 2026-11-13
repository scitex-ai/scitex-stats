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
