---
description: |
  [TOPIC] CSV input
  [DETAILS] Auto/manual delimiters, quoted numeric cells, column import and source-row integrity.
tags: [scitex-stats-csv-import, scitex-stats]
---

# CSV input in the Stats app

Use the manual input area, or open the Stats app with `?quick=1` when a project
is selected. Upload a CSV/TSV file, review the preview and detected separator,
then choose **Import selected** when multiple numeric columns are offered.
The analysis uses the group boxes; the preview alone does not import columns.

**Auto** estimates Tab, Comma, Semicolon, Pipe, or consistent whitespace.
The indicator says **estimated**. Choosing a separator manually reparses the
current file and changes the indicator to **your choice**. A `.tsv` file keeps
its tab default unless overridden explicitly.

Quoted cells can contain delimiters, and doubled quotes escape a literal quote.
The browser expects one CSV record per line. It does not support multiline
quoted cells. Malformed quoting must remain nonnumeric: never remove quotes to
turn `1"2"3` into `123`. Missing/invalid observations prevent tests that require
matching source rows; keep the original row correspondence when correcting data.

For Python file inputs, `resolve_columns(..., sep=...)` accepts an explicit
separator, and its default estimates the separator.

Source: `_django/static/stats/js/app.js` owns the browser parser, chooser and
row-integrity checks; `_utils/_csv_support.py` owns Python file parsing.
Regression evidence: `_django/static/stats/js/test_csv_import.cjs` under the
tests tree exercises the shipped client script; `_utils/test__csv_support.py`
checks real file-backed column resolution. Confirm deployed behavior with an
actual file upload as well as these tests.
