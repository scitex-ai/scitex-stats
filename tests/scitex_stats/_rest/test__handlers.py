#!/usr/bin/env python3
# File: tests/scitex_stats/_rest/test__handlers.py
"""``tests`` resource through the SDK serving path: catalogue, run, recommend."""

import json

from scitex_stats import available_tests, run_test

from ._host import MEMBER, get, post

A = [5.1, 4.9, 5.6, 5.8, 6.0, 5.4]
B = [6.3, 6.8, 6.1, 7.0, 6.6, 6.9]


# ------------------------------------------------------------------ catalogue


def test_anonymous_callers_list_every_test():
    # Arrange
    # Act
    response = get("tests?limit=100")
    # Assert
    assert response.json()["total"] == len(available_tests())


def test_an_alias_resolves_to_its_function():
    # Arrange
    # Act
    response = get("tests/ttest")
    # Assert
    assert response.json()["data"]["function"] == "test_ttest_ind"


def test_a_catalogue_entry_names_the_fields_it_reads():
    # Arrange
    # Act
    response = get("tests/ttest_1samp")
    # Assert
    assert response.json()["data"]["required"] == ["data"]


def test_an_unknown_test_is_a_404():
    # Arrange
    # Act
    response = get("tests/no_such_test")
    # Assert
    assert (response.status_code, response.json()["code"]) == (
        404,
        "stats.test_not_found",
    )


# ------------------------------------------------------------------ run


def test_an_anonymous_run_matches_the_python_api():
    # Arrange
    expected = run_test("ttest_ind", data=A, data2=B)["pvalue"]
    # Act
    response = post("tests/ttest_ind/run", {"data": A, "data2": B})
    # Assert
    assert response.json()["data"]["pvalue"] == expected


def test_running_an_unknown_test_is_a_404():
    # Arrange
    # Act
    response = post("tests/os.system/run", {"data": A})
    # Assert
    assert response.json()["code"] == "stats.test_not_found"


def test_the_receipt_carries_hashes_not_the_values():
    # Arrange
    # Act
    response = post("tests/ttest_ind/run", {"data": A, "data2": B})
    # Assert
    assert "values" not in response.json()["data"]["provenance"]["inputs"]["data"]


def test_a_nan_literal_is_refused():
    # Arrange
    raw = '{"data": [1, 2, NaN], "data2": [1, 2, 3]}'
    # Act
    response = post("tests/ttest_ind/run", None, raw=raw)
    # Assert
    assert (response.status_code, response.json()["code"]) == (
        400,
        "stats.invalid_input",
    )


def test_an_infinity_literal_is_refused():
    # Arrange
    raw = '{"data": [1, 2, Infinity], "data2": [1, 2, 3]}'
    # Act
    response = post("tests/ttest_ind/run", None, raw=raw)
    # Assert
    assert response.json()["code"] == "stats.invalid_input"


def test_a_string_value_is_refused():
    # Arrange
    body = {"data": [1, "2", 3], "data2": B}
    # Act
    response = post("tests/ttest_ind/run", body)
    # Assert
    assert response.json()["code"] == "stats.invalid_input"


def test_a_boolean_value_is_refused():
    # Arrange
    body = {"data": [1, True, 3], "data2": B}
    # Act
    response = post("tests/ttest_ind/run", body)
    # Assert
    assert response.json()["code"] == "stats.invalid_input"


def test_a_nested_array_in_data_is_refused():
    # Arrange
    body = {"data": [[1, 2], [3, 4]], "data2": B}
    # Act
    response = post("tests/ttest_ind/run", body)
    # Assert
    assert response.json()["code"] == "stats.invalid_input"


def test_an_unknown_key_is_refused():
    # Arrange
    body = {"data": A, "data2": B, "__class__": "x"}
    # Act
    response = post("tests/ttest_ind/run", body)
    # Assert
    assert response.json()["code"] == "api.unknown_parameter"


def test_a_field_the_test_does_not_read_is_refused():
    # Arrange
    body = {"data": A, "data2": B, "popmean": 3}
    # Act
    response = post("tests/ttest_ind/run", body)
    # Assert
    assert response.json()["code"] == "stats.invalid_input"


def test_a_missing_second_sample_is_refused():
    # Arrange
    body = {"data": A}
    # Act
    response = post("tests/mannwhitneyu/run", body)
    # Assert
    assert response.json()["errors"][0]["field"] == "data2"


def test_an_unknown_alternative_is_refused():
    # Arrange
    body = {"data": A, "data2": B, "alternative": "sideways"}
    # Act
    response = post("tests/ttest_ind/run", body)
    # Assert
    assert response.json()["code"] == "api.invalid_parameter"


def test_the_alternative_reaches_the_test():
    # Arrange
    expected = run_test("ttest_ind", data=A, data2=B, alternative="less")["pvalue"]
    # Act
    response = post(
        "tests/ttest_ind/run", {"data": A, "data2": B, "alternative": "less"}
    )
    # Assert
    assert response.json()["data"]["pvalue"] == expected


def test_a_contingency_table_runs_from_groups():
    # Arrange
    table = [[10, 20], [30, 5]]
    # Act
    response = post("tests/chi2/run", {"groups": table})
    # Assert
    assert response.json()["data"]["pvalue"] == run_test("chi2", groups=table)["pvalue"]


def test_values_are_counted_across_every_field():
    # Arrange
    body = {"data": [0.0] * 50_001, "data2": [1.0] * 50_000}
    # Act
    response = post("tests/ttest_ind/run", body)
    # Assert
    assert (response.status_code, response.json()["code"]) == (
        413,
        "stats.too_many_values",
    )


def test_a_member_key_lifts_the_public_value_cap():
    # Arrange
    body = {"data": [float(i % 7) for i in range(50_001)], "data2": [1.5] * 50_000}
    # Act
    response = post("tests/ttest_ind/run", body, token=MEMBER)
    # Assert
    assert response.status_code == 200


def test_members_are_held_to_the_hard_cap():
    # Arrange
    body = {"data": [0] * 1_000_001, "data2": [1, 2]}
    # Act
    response = post("tests/ttest_ind/run", body, token=MEMBER)
    # Assert
    assert response.json()["code"] == "stats.too_many_values"


def test_inputs_that_do_not_fit_the_test_are_a_400():
    # Arrange
    body = {"groups": [[1, 2, 3], [4, 5]]}
    # Act
    response = post("tests/friedman/run", body)
    # Assert
    assert response.status_code == 400


# ------------------------------------------------------------------ recommend


def test_recommend_from_data_picks_welch():
    # Arrange
    body = {"groups": [A, B], "design": "independent"}
    # Act
    response = post("tests/recommend", body)
    # Assert
    assert response.json()["data"]["recommendation"]["primary"]["test_id"] == (
        "ttest_welch"
    )


def test_recommend_from_data_omits_per_value_plot_coordinates():
    # Arrange
    body = {"groups": [A, B]}
    # Act
    response = post("tests/recommend", body)
    # Assert
    assert '"qq"' not in json.dumps(response.json())


def test_recommend_from_a_design_lists_test_names():
    # Arrange
    body = {"n_groups": 2, "sample_sizes": [30, 32], "design": "between"}
    # Act
    response = post("tests/recommend", body)
    # Assert
    assert "brunner_munzel" in response.json()["data"]["recommendations"]


def test_recommend_refuses_both_forms_at_once():
    # Arrange
    body = {"groups": [A, B], "n_groups": 2}
    # Act
    response = post("tests/recommend", body)
    # Assert
    assert response.json()["code"] == "stats.invalid_input"


def test_recommend_refuses_a_mixed_design_for_data():
    # Arrange
    body = {"groups": [A, B], "design": "mixed"}
    # Act
    response = post("tests/recommend", body)
    # Assert
    assert response.json()["errors"][0]["field"] == "design"


def test_recommend_refuses_sizes_that_disagree_with_n_groups():
    # Arrange
    body = {"n_groups": 3, "sample_sizes": [10, 10]}
    # Act
    response = post("tests/recommend", body)
    # Assert
    assert response.json()["errors"][0]["field"] == "sample_sizes"


# EOF
