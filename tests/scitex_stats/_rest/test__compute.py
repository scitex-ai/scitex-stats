#!/usr/bin/env python3
# File: tests/scitex_stats/_rest/test__compute.py
"""Descriptives, effect sizes, power, corrections, bootstrap CIs over HTTP."""

from scitex_stats.correct import correct_pvalues
from scitex_stats.descriptive import bootstrap_ci
from scitex_stats.effect_sizes import effect_size
from scitex_stats.power import power_analysis

from ._host import MEMBER, post

A = [5.1, 4.9, 5.6, 5.8, 6.0, 5.4]
B = [6.3, 6.8, 6.1, 7.0, 6.6, 6.9]


def test_descriptives_report_the_mean():
    # Arrange
    body = {"data": [1, 2, 3, 4]}
    # Act
    response = post("descriptives/run", body)
    # Assert
    assert response.json()["data"]["statistics"]["mean"] == 2.5


def test_descriptives_return_only_the_asked_statistics():
    # Arrange
    body = {"data": [1, 2, 3, 4], "statistics": ["median", "max"]}
    # Act
    response = post("descriptives/run", body)
    # Assert
    assert sorted(response.json()["data"]["statistics"]) == ["max", "median"]


def test_descriptives_refuse_an_unknown_statistic():
    # Arrange
    body = {"data": [1, 2, 3], "statistics": ["__import__"]}
    # Act
    response = post("descriptives/run", body)
    # Assert
    assert response.json()["code"] == "stats.invalid_input"


def test_an_effect_size_matches_the_python_api():
    # Arrange
    expected = effect_size(A, B, measure="hedges_g")["value"]
    # Act
    response = post("effect-sizes/run", {"data": A, "data2": B, "measure": "hedges_g"})
    # Assert
    assert response.json()["data"]["value"] == expected


def test_cliffs_delta_runs_on_large_public_samples():
    # Arrange
    body = {"data": [float(i % 97) for i in range(50_000)], "data2": [3.0] * 50_000}
    # Act
    response = post("effect-sizes/run", {**body, "measure": "cliffs_delta"})
    # Assert
    assert response.status_code == 200


def test_an_unknown_effect_size_measure_is_refused():
    # Arrange
    body = {"data": A, "data2": B, "measure": "os.system"}
    # Act
    response = post("effect-sizes/run", body)
    # Assert
    assert response.json()["code"] == "api.invalid_parameter"


def test_power_matches_the_python_api():
    # Arrange
    expected = power_analysis(effect_size=0.5, n=20)["power"]
    # Act
    response = post("power-analyses/run", {"effect_size": 0.5, "n": 20})
    # Assert
    assert response.json()["data"]["power"] == expected


def test_power_solves_for_the_sample_size():
    # Arrange
    body = {"effect_size": 0.5, "power": 0.8}
    # Act
    response = post("power-analyses/run", body)
    # Assert
    assert response.json()["data"]["mode"] == "sample_size_calculation"


def test_power_refuses_a_correlation_outside_minus_one_one():
    # Arrange
    body = {"test_type": "correlation", "effect_size": 1.5, "n": 30}
    # Act
    response = post("power-analyses/run", body)
    # Assert
    assert response.json()["errors"][0]["field"] == "effect_size"


def test_power_refuses_an_alpha_outside_zero_one():
    # Arrange
    body = {"effect_size": 0.5, "alpha": 1.5}
    # Act
    response = post("power-analyses/run", body)
    # Assert
    assert response.json()["errors"][0]["field"] == "alpha"


def test_a_correction_matches_the_python_api():
    # Arrange
    pvalues = [0.01, 0.02, 0.04, 0.3]
    expected = correct_pvalues(pvalues, method="holm")["corrected_pvalues"]
    # Act
    response = post("corrections/run", {"pvalues": pvalues, "method": "holm"})
    # Assert
    assert response.json()["data"]["corrected_pvalues"] == expected


def test_a_correction_refuses_a_pvalue_above_one():
    # Arrange
    body = {"pvalues": [0.01, 1.5]}
    # Act
    response = post("corrections/run", body)
    # Assert
    assert response.json()["code"] == "stats.invalid_input"


def test_a_bootstrap_ci_matches_the_python_api():
    # Arrange
    expected = bootstrap_ci(A + B, "median", n_resamples=2_000, seed=7)["ci_lower"]
    # Act
    response = post(
        "bootstrap-cis/run", {"data": A + B, "n_resamples": 2_000, "seed": 7}
    )
    # Assert
    assert response.json()["data"]["ci_lower"] == expected


def test_public_resamples_are_capped_by_the_profile():
    # Arrange
    body = {"data": A, "n_resamples": 10_001}
    # Act
    response = post("bootstrap-cis/run", body)
    # Assert
    assert (response.status_code, response.json()["code"]) == (
        413,
        "stats.resampling_too_large",
    )


def test_a_member_may_ask_for_more_resamples():
    # Arrange
    body = {"data": A, "n_resamples": 20_000}
    # Act
    response = post("bootstrap-cis/run", body, token=MEMBER)
    # Assert
    assert response.status_code == 200


def test_bootstrap_work_is_capped_for_members_too():
    # Arrange
    body = {"data": [float(i) for i in range(3_000)], "n_resamples": 10_000}
    # Act
    response = post("bootstrap-cis/run", body, token=MEMBER)
    # Assert
    assert response.json()["limit"] == "max_bootstrap_work"


def test_bca_is_capped_on_the_sample_size():
    # Arrange
    body = {
        "data": [float(i) for i in range(6_000)],
        "n_resamples": 100,
        "method": "bca",
    }
    # Act
    response = post("bootstrap-cis/run", body, token=MEMBER)
    # Assert
    assert response.json()["limit"] == "max_bca_values"


def test_a_statistic_is_a_name_never_code():
    # Arrange
    body = {"data": A, "statistic": "lambda x: __import__('os')"}
    # Act
    response = post("bootstrap-cis/run", body)
    # Assert
    assert response.json()["code"] == "api.invalid_parameter"


# EOF
