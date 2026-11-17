"""Unset optional adjusted thresholds must not defeat raw-p inference."""

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from scitex_stats._utils._normalizers import (
    force_dataframe,
    normalize_result,
    to_dataframe,
)

MISSING = [None, np.nan, pd.NA]


@pytest.mark.parametrize("missing", MISSING)
@pytest.mark.parametrize("fill_missing", [False, True])
def test_raw_probability_uses_family_alpha_when_adjusted_threshold_is_unset(missing, fill_missing):
    # Arrange
    source = {"pvalue": .03, "alpha": .05, "alpha_adjusted": missing}
    # Act
    result = normalize_result(source, fill_missing=fill_missing)
    # Assert
    assert (bool(result["rejected"]), result["pstars"]) == (True, "*")


@pytest.mark.parametrize("missing", MISSING)
@pytest.mark.parametrize("convert", [to_dataframe, force_dataframe])
def test_conversion_keeps_the_inferred_raw_probability_decision(missing, convert):
    # Arrange
    source = [{"pvalue": .03, "alpha": .05, "alpha_adjusted": missing}]
    # Act
    frame = convert(source)
    # Assert
    assert (frame.rejected.tolist(), frame.pstars.tolist()) == ([True], ["*"])


@pytest.mark.parametrize("missing", MISSING)
def test_explicit_decisions_stars_and_input_metadata_are_preserved(missing):
    # Arrange
    source = {"pvalue": .03, "alpha": .05, "alpha_adjusted": missing,
              "rejected": False, "pstars": "caller"}
    before = deepcopy(source)
    # Act
    result = normalize_result(source, fill_missing=False)
    # Assert
    assert (pd.Series(result).equals(pd.Series(before)),
            pd.Series(source).equals(pd.Series(before))) == (True, True)


def test_defined_adjusted_threshold_remains_the_raw_probability_coordinate():
    # Arrange
    source = {"pvalue": .03, "alpha": .05, "alpha_adjusted": .025}
    # Act
    result = normalize_result(source)
    # Assert
    assert result["rejected"] is False


@pytest.mark.parametrize("missing", MISSING)
def test_adjusted_probability_still_uses_family_alpha(missing):
    # Arrange
    source = {"pvalue": .02, "pvalue_adjusted": .04, "alpha": .05,
              "alpha_adjusted": missing}
    # Act
    result = normalize_result(source)
    # Assert
    assert result["rejected"] is True


def test_undefined_adjusted_probability_does_not_fall_back_to_raw_significance():
    # Arrange
    source = {"pvalue": .001, "pvalue_adjusted": None, "alpha": .05,
              "alpha_adjusted": None}
    # Act
    result = normalize_result(source, fill_missing=False)
    # Assert
    assert result == source
