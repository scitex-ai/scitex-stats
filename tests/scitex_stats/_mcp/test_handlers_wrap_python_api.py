"""Each MCP handler returns exactly its Python API's payload plus the envelope.

§6 parity: the tool and the function share one implementation, so the MCP
payload minus ``success`` / ``timestamp`` must equal the sync call's dict.
"""

import asyncio

import pytest

import scitex_stats as ss
from scitex_stats._mcp import handlers as h

G1 = [5.1, 5.5, 6.0, 6.2, 6.8, 7.1]
G2 = [4.0, 4.4, 4.9, 5.0, 5.3, 5.6]
GROUPS = [G1, G2, [7.0, 8.0, 9.0, 8.5, 7.5]]

CASES = [
    (h.correct_pvalues_handler, ss.correct_pvalues, {"pvalues": [0.01, 0.04, 0.03]}),
    (h.effect_size_handler, ss.effect_size, {"group1": G1, "group2": G2}),
    (h.normality_test_handler, ss.normality_test, {"data": G1 + G2}),
    (h.posthoc_test_handler, ss.posthoc_test, {"groups": GROUPS}),
    (h.power_analysis_handler, ss.power_analysis, {"effect_size": 0.5, "n": 30}),
    (
        h.format_results_handler,
        ss.format_results,
        {"test_name": "t-test", "statistic": 2.1, "p_value": 0.04},
    ),
]


@pytest.mark.parametrize(("handler", "api", "kwargs"), CASES, ids=lambda c: getattr(c, "__name__", ""))
def test_handler_payload_equals_python_api(handler, api, kwargs):
    # Arrange
    expected = api(**kwargs)
    # Act
    out = asyncio.run(handler(**kwargs))
    payload = {k: v for k, v in out.items() if k not in ("success", "timestamp")}
    # Assert
    assert (out["success"], payload) == (True, expected)
