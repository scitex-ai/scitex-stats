"""Normalization keeps adjusted probabilities paired with family alpha."""

from copy import deepcopy

import pytest

from scitex_stats._utils._normalizers import (
    force_dataframe,
    normalize_result,
    to_dataframe,
)


@pytest.mark.parametrize(
    "record, expected",
    [
        ({"pvalue": .02, "pvalue_adjusted": .04, "alpha": .05,
          "alpha_adjusted": .025}, True),
        ({"pvalue": .02, "pvalue_adjusted": .06, "alpha": .05,
          "alpha_adjusted": .025}, False),
        ({"pvalue": .03, "pvalue_adjusted": .09, "alpha": .1,
          "alpha_adjusted": .1 / 3}, True),
        ({"pvalue_adjusted": .04, "alpha_adjusted": .025}, True),
        ({"pvalue_adjusted": .06, "alpha_adjusted": .025}, False),
        ({"pvalue": .02, "alpha": .05, "alpha_adjusted": .025}, True),
        ({"pvalue": .03, "alpha": .05, "alpha_adjusted": .025}, False),
        ({"pvalue": .04, "alpha": .05}, True),
        ({"pvalue_adjusted": .05, "alpha": .05, "alpha_adjusted": .025}, False),
    ],
)
def test_inferred_decision_uses_matching_probability_threshold(record, expected):
    # Arrange
    source = deepcopy(record)
    # Act
    normalized = normalize_result(source)
    # Assert
    assert normalized["rejected"] is expected


@pytest.mark.parametrize("fill_missing", [True, False])
def test_existing_decision_and_stars_are_preserved_without_input_mutation(fill_missing):
    # Arrange
    source = {"pvalue": .02, "pvalue_adjusted": .04, "alpha": .05,
              "alpha_adjusted": .025, "rejected": False, "pstars": "custom"}
    before = deepcopy(source)
    # Act
    result = normalize_result(source, fill_missing=fill_missing)
    # Assert
    assert {"decision": result["rejected"], "stars": result["pstars"],
            "source": source} == {"decision": False, "stars": "custom", "source": before}


@pytest.mark.parametrize("convert", [to_dataframe, force_dataframe])
def test_dataframe_conversion_preserves_adjusted_probability_decisions(convert):
    # Arrange
    records = [{"pvalue": .02, "pvalue_adjusted": .04, "alpha": .05,
                "alpha_adjusted": .025},
               {"pvalue": .4, "pvalue_adjusted": .8, "alpha": .05,
                "alpha_adjusted": .025}]
    # Act
    result = convert(records)
    # Assert
    assert result["rejected"].tolist() == [True, False]


def test_missing_result_does_not_invent_a_decision_without_defaults():
    # Arrange
    source = {"label": "no probability"}
    # Act
    result = normalize_result(source, fill_missing=False)
    # Assert
    assert result == source
