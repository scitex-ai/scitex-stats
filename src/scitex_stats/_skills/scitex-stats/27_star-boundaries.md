---
description: |
  [TOPIC] Significance symbol boundaries
  [DETAILS] Current default public/MCP strict comparisons, legacy inclusive
  formatter thresholds, source/tests and the unresolved compatibility gap.
tags: [scitex-stats-star-boundaries, scitex-stats]
---

# Significance symbol boundaries

The public `scitex_stats.p_to_stars` uses strict comparisons with the selected
style's thresholds. Its default APA style and the standalone MCP `p_to_stars`
use the following symbols. The legacy `_utils._formatters.p2stars` helper,
also used by result normalization, includes exact threshold values.

| Default p-value | Public Python / MCP | Legacy `p2stars` |
|---|---|---|
| 0.001 | `**` | `***` |
| 0.01 | `*` | `**` |
| 0.05 | `ns` | `*` |

These rows describe current default behavior, not an interface-consistency
pass. Harmonizing the legacy and public policies remains a compatibility task.
This documentation correction changes no runtime comparison or symbol.

```python
from scitex_stats.auto._formatting import p_to_stars
from scitex_stats._utils._formatters import p2stars

p_to_stars(0.001)  # "**", default APA style
p2stars(0.001)     # "***", inclusive legacy formatter
```

Normalization preserves explicit caller stars/decisions. Its strict rejection
comparison and legacy symbol conversion can differ at an exact threshold;
interpret the explicit decision field and the analysis plan when reporting.
This page qualifies default scalar symbol boundaries, not all custom styles,
custom threshold shapes, missing-value decisions or invalid-input handling.

Owners: `auto/_formatting.py::p_to_stars`,
`auto/_stat_style.py::StatStyle.p_to_stars`,
`_utils/_formatters.py::p2stars` / `_p2stars_scalar`, and
`_mcp/_handlers/_stars.py::p_to_stars_handler`.
Existing behavior controls: `tests/scitex_stats/_utils/test__formatters.py`,
`tests/scitex_stats/auto/test__formatting.py` and MCP handler tests.

## MCP probability admission

Standalone MCP `p_to_stars` requires a finite scalar `p_value` in [0, 1].
The authoritative tool schema declares both bounds and rejects invalid wire
requests. The leaf handler also returns `success: false` with an error and
no stars for out-of-range or nonfinite direct inputs. Schema rejection and
handler error envelopes are separate layers; nonfinite values are not standard
JSON numbers. Endpoints 0 and 1, strict threshold boundaries, optional-threshold
defaults and valid custom-threshold results retain their existing behavior.
This admission change does not qualify all custom-threshold shapes or change
native/legacy formatter validation or missing-value policies.

Owners: `_server.py::p_to_stars` (schema) and
`_mcp/_handlers/_stars.py::p_to_stars_handler` (handler admission).
Behavior and authoritative-schema controls:
`tests/integration/test_star_probability_input.py`.
