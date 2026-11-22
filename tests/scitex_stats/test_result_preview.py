import json

import pytest

from scitex_stats import run_all_applicable, run_test
from scitex_stats.result_preview import comparison_artifact, preview_result


def test_preview_result_preserves_native_comparison_results_and_checks():
    # Arrange
    data = {"A": [1, 8, 2, 7, 4, 9, 5, 10], "B": [4, 3, 9, 2, 6, 1, 14, 15]}
    result = run_all_applicable(data, "independent", scale="continuous")

    # Act
    preview = preview_result(json.dumps(result))["comparisons"]["analysis"]

    # Assert
    assert preview["results"] == json.loads(json.dumps(result["results"]))
    assert preview["checks"]["normality"] == result["recommendation"]["checks"]["normality"]
    assert len(preview["results"]) > 1


def test_preview_result_reuses_the_native_publication_line():
    # Arrange
    native = run_test("chi2", groups=[[10, 20], [21, 11]])
    # Act
    preview = preview_result(json.dumps(native))["comparisons"]["result"]
    # Assert
    assert preview["results"][0]["apa"]["plain"] == native["apa"]["plain"]


def test_preview_result_recognizes_canonical_stats_and_comparison_artifacts():
    # Arrange
    canonical = {"analyses": [{
        "result_id": "a", "method": {"name": "t-test"},
        "results": {"statistic": 2.1, "p_value": 0.04, "effect_size": {"name": "d", "value": 0.5}},
    }]}
    bundle = comparison_artifact({"named": {"results": [{"test": "chi2", "effect_size": .3, "effect_size_metric": "V"}]}})
    # Act
    preview = preview_result(json.dumps(canonical))["comparisons"]["analysis"]["results"][0]
    # Assert
    assert preview["effect_size_metric"] == "d" and preview["effect_size"] == 0.5
    assert preview_result(json.dumps(bundle))["comparisons"] == bundle["comparisons"]
    assert preview_result('{"result": 1}') is None


def test_comparison_artifact_rejects_a_result_without_effect_size():
    from scitex_stats.reporting import IncompleteReportError

    # Arrange
    comparisons = {"named": {"results": [{"test": "chi2", "p_value": .003}]}}
    # Act / Assert
    with pytest.raises(IncompleteReportError, match="Effect size required for chi2"):
        comparison_artifact(comparisons)
