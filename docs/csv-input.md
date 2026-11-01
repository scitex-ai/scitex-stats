# CSV input and separators

The web app supports Auto, Comma, Tab, Semicolon, Pipe and Space. Auto shows the
estimated separator below the selector; an explicit selection shows “your choice”
and reparses the last imported file. TSV filenames keep tab separation in Auto.

CSV quoting is respected within each record: punctuation inside quoted cells
is not a separator, doubled quotes represent a literal quote, and quoted numeric
cells remain numbers. For example, Auto recognizes this file as semicolon-separated:

```csv
"signal, mean";reference
"1";"10"
"2";"20"
```

The column chooser offers the named numeric columns before importing them.
Browser import expects one record per line. Space mode splits whitespace runs.

Python file-backed column resolution uses the same quote-aware separator
estimation before loading through pandas. The functional regression in
`tests/scitex_stats/_utils/test__csv_support.py` reads the example above and
checks both named numeric columns.

Malformed quoting does not turn text into a numeric observation. For example,
`1"2"3` stays invalid rather than becoming `123`. Imports with invalid or
missing observations cannot run analyses that require matching source rows.
