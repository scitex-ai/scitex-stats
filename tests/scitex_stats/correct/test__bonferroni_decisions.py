"""Bonferroni decisions must apply the family correction exactly once."""

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest
from statsmodels.stats.multitest import multipletests

from scitex_stats.correct import correct_bonferroni


@pytest.mark.parametrize("form", ["records", "dataframe", "forced_dataframe"])
@pytest.mark.parametrize(
    "pvalues, alpha",
    [([0.02, 0.5], 0.05), ([0.01, 0.01, 0.5, 0.9], 0.05),
     ([0.03, 0.7, 1.0], 0.1)],
)
def test_decisions_and_probabilities_match_independent_reference(form, pvalues, alpha):
    # Arrange: no exact threshold ties, so reference <= and leaf < agree.
    records = [{"pvalue": p, "label": str(i)} for i, p in enumerate(pvalues)]
    data = pd.DataFrame(records) if form == "dataframe" else records
    before = deepcopy(data)
    expected_reject, expected_p, _, expected_alpha = multipletests(
        pvalues, alpha=alpha, method="bonferroni"
    )

    # Act
    corrected = correct_bonferroni(
        data, alpha=alpha, verbose=False,
        return_as="dataframe" if form == "forced_dataframe" else None,
    )
    frame = pd.DataFrame(corrected)

    # Assert
    np.testing.assert_allclose(frame["pvalue_adjusted"], expected_p, rtol=1e-12)
    np.testing.assert_array_equal(frame["rejected"], expected_reject)
    np.testing.assert_allclose(frame["alpha_adjusted"], expected_alpha)
    assert frame["label"].tolist() == [str(i) for i in range(len(pvalues))]
    if isinstance(data, pd.DataFrame):
        pd.testing.assert_frame_equal(data, before)
    else:
        assert data == before


def test_per_row_alpha_and_missing_alpha_use_original_family_threshold():
    # Arrange
    data = pd.DataFrame({"pvalue": [0.02, 0.02, 0.02],
                         "alpha": [0.1, np.nan, 0.01]}, index=[7, 3, 9])
    before = data.copy(deep=True)

    # Act
    corrected = correct_bonferroni(data, alpha=0.05, verbose=False)

    # Assert
    np.testing.assert_array_equal(corrected["rejected"], [True, False, False])
    np.testing.assert_allclose(corrected["pvalue_adjusted"], [0.06] * 3)
    np.testing.assert_allclose(corrected["alpha_adjusted"], np.array([0.1, 0.05, 0.01]) / 3)
    assert corrected.index.tolist() == [7, 3, 9]
    pd.testing.assert_frame_equal(data, before)


def test_existing_strict_boundary_is_preserved():
    # Arrange
    records = [{"pvalue": 0.025}, {"pvalue": 0.5}]

    # Act
    corrected = correct_bonferroni(records, alpha=0.05, verbose=False)

    # Assert: the leaf retains p_adjusted < alpha, not the reference's <=.
    assert corrected[0]["pvalue_adjusted"] == 0.05
    assert not corrected[0]["rejected"]
    assert corrected[0]["alpha_adjusted"] == 0.025


def test_single_dict_and_explicit_dict_shape_remain_supported():
    # Arrange
    original = {"pvalue": 0.02, "name": "one"}

    # Act
    single = correct_bonferroni(original, alpha=0.05, verbose=False)
    records = correct_bonferroni([original, {"pvalue": 0.5}],
                                return_as="dict", verbose=False)

    # Assert
    assert isinstance(single, dict) and single["rejected"]
    assert single["pvalue_adjusted"] == 0.02
    assert isinstance(records, list) and records[0]["rejected"]
    assert records[0]["pvalue_adjusted"] == 0.04
    assert original == {"pvalue": 0.02, "name": "one"}


def test_record_alpha_overrides_preserve_missing_and_null_fallbacks():
    # Arrange
    records = [{"pvalue": 0.02, "alpha": 0.1}, {"pvalue": 0.02},
               {"pvalue": 0.02, "alpha": None}]
    original = deepcopy(records)

    # Act
    corrected = correct_bonferroni(records, alpha=0.05, verbose=False)

    # Assert
    assert [bool(row["rejected"]) for row in corrected] == [True, False, False]
    np.testing.assert_allclose([row["pvalue_adjusted"] for row in corrected], [.06] * 3)
    np.testing.assert_allclose([row["alpha_adjusted"] for row in corrected],
                               np.array([.1, .05, .05]) / 3)
    assert records == original
