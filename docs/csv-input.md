# CSV input and separators

The data pane keeps the manual group boxes inline. **Project data…** (project
mode) or **Import CSV…** (Quick analysis) opens the import dialog. Choose an
authorized project file or a local CSV/TSV file, review its preview, choose
numeric columns, and press **Import selected**. A one-column file also waits
for confirmation. Opening a preview does not replace the group boxes.

Cancel, Close and Escape preserve both existing group data and the pending
preview/column choices. Reopening continues that preview. The native dialog
keeps background controls inert and returns focus when closed.

The selector supports Auto, Comma, Tab, Semicolon, Pipe and Space. Auto compares
column-count consistency across records, ignoring quoted punctuation. The
indicator shows the separator actually used. An explicit choice reparses the
current preview and says **your choice**. A `.tsv` filename retains its tab
contract and is labeled **.tsv default**.

Equally plausible punctuation delimiters require an explicit choice before
import. The documented tab preference is preserved when structured tabs and
punctuation both fit; the UI reports that alternatives also fit. A single
record is labeled as limited evidence. A separator-free numeric column is
shown as a single column rather than claiming a comma was detected. Unequal
record widths remain visible in the preview and are flagged for review.

Quoting supports delimiters inside quoted cells and doubled quotes. Space mode
collapses whitespace runs outside quotes, so `"control group"  1` has two
fields. A UTF-8 BOM does not become part of the first quoted header. Browser
import still expects one record per line; multiline quoted cells are not
supported. Malformed quoting must not turn `1"2"3` into `123`. Source-row
integrity checks continue to prevent paired analyses after missing/invalid
observations lose row correspondence.

Python file-backed resolution uses the same record-consistency rule.
`resolve_columns(..., sep=...)` and `resolve_groups(..., sep=...)` provide
explicit overrides. Ambiguous punctuation in Auto raises `ValueError` asking
for `sep`, and quoted whitespace fields load through pandas' quote-aware
whitespace reader.

Regression evidence:

- `tests/scitex_stats/_utils/test__csv_support.py` reads real files and checks
  named columns, separators, ambiguity, quoting and BOM handling.
- `tests/scitex_stats/_django/static/stats/js/test_csv_import.cjs` exercises
  the shipped client, including cancellation and preservation of group data.
- `tests/scitex_stats/_django/check_import_dialog_browser.py` drives the real
  standalone Django app in Chromium at desktop and phone sizes. Invoke it
  with `--chromium /path/to/chrome --output-dir /tmp/stats-dialog-proof` in an
  environment with the server stack and Playwright installed. It uses a
  disposable project root and synthetic files, and writes screenshots and
  a JSON receipt; it does not access a live project or database.
