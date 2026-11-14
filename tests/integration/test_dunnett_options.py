"""Guard the declared native Dunnett hypothesis and significance-level domains."""

import pytest

from scitex_stats.posthoc._dunnett import (
    _dunnett_statistics,
    dunnett_critical_value,
    posthoc_dunnett,
)

CONTROL = [1., 2., 4., 8., 9.]
TREATMENTS = [[3., 4., 5., 7.], [5., 8., 9., 15., 17., 21.]]


@pytest.mark.parametrize("alpha", [0., 1., -.1, 1.1, float("nan"), float("inf"),
                                   -float("inf"), True, False, "0.05", 1j, [.05]])
@pytest.mark.parametrize("function, kwargs", [
    (dunnett_critical_value, {"k": 2, "df": 12}),
    (posthoc_dunnett, {"control": CONTROL, "treatments": TREATMENTS}),
])
def test_dunnett_rejects_invalid_significance_levels(alpha, function, kwargs):
    # Arrange
    # Act
    with pytest.raises(ValueError, match="alpha must be a finite real number strictly between 0 and 1"):
        # Assert
        function(alpha=alpha, **kwargs)


@pytest.mark.parametrize("alternative", ["invalid", "TWO-SIDED", "", None, "two_sided"])
@pytest.mark.parametrize("function, kwargs", [
    (dunnett_critical_value, {"k": 2, "df": 12}),
    (posthoc_dunnett, {"control": CONTROL, "treatments": TREATMENTS}),
    (_dunnett_statistics, {"control": CONTROL, "treatments": TREATMENTS}),
])
def test_dunnett_rejects_unknown_alternatives(alternative, function, kwargs):
    # Arrange
    # Act
    with pytest.raises(ValueError, match="alternative must be 'two-sided', 'less' or 'greater'"):
        # Assert
        function(alternative=alternative, **kwargs)
