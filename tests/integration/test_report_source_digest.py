"""Full-report verification must bind the supplied source to its recorded digest."""

from copy import deepcopy

import pytest

import scitex_stats as stats

X = [5.1, 4.9, 6.2, 5.8, 6., 5.5, 5.3, 6.1]
Y = [6.3, 6.9, 7.1, 6.5, 7.4, 6.8, 7., 6.6]


@pytest.fixture(scope="module")
def report_pair():
    source = stats.run_test("mannwhitneyu", data=X, data2=Y)
    report = stats.full_report(source, data=X, data2=Y, n_bootstrap=400)
    return source, report


def test_source_field_unused_by_report_still_must_match_digest(report_pair):
    # Arrange
    source, report = deepcopy(report_pair)
    source["unrecorded_note"] = "changed source result"
    # Act
    actual = stats.verify(report, source_result=source)
    recompute = next(row for row in actual["checks"] if row["name"] == "recompute")
    # Assert
    assert (actual["verified"], recompute["status"],
            "source_result_sha256" in recompute["detail"]) == (False, "fail", True)


def test_source_receipt_reference_must_match_recorded_reference(report_pair):
    # Arrange
    source, report = deepcopy(report_pair)
    source["provenance"]["receipt_sha256"] = "0" * 64
    # Act
    actual = stats.verify(report, source_result=source)
    recompute = next(row for row in actual["checks"] if row["name"] == "recompute")
    # Assert
    assert (actual["verified"], recompute["status"],
            "source_receipt_sha256" in recompute["detail"]) == (False, "fail", True)


def test_unchanged_source_passes_all_existing_checks(report_pair):
    # Arrange
    source, report = deepcopy(report_pair)
    before = deepcopy((source, report))
    # Act
    actual = stats.verify(report, source_result=source)
    # Assert
    assert (actual["verified"], {row["status"] for row in actual["checks"]},
            (source, report)) == (True, {"pass"}, before)


def test_source_timestamp_stays_excluded_by_canonical_hash_policy(report_pair):
    # Arrange
    source, report = deepcopy(report_pair)
    source["timestamp"] = "new serialization time"
    # Act
    actual = stats.verify(report, source_result=source)
    # Assert
    assert actual["verified"] is True


def test_full_report_from_source_without_receipt_still_verifies():
    # Arrange
    source = stats.run_test("mannwhitneyu", data=X, data2=Y)
    del source["provenance"]
    report = stats.full_report(source, data=X, data2=Y, n_bootstrap=400)
    # Act
    actual = stats.verify(report, source_result=source)
    # Assert
    assert actual["verified"] is True
