#!/usr/bin/env python3
"""Tests for `scitex_stats._provenance`: receipts, determinism, input integrity."""

from __future__ import annotations

import copy
import hashlib
import re
from pathlib import Path

import numpy as np
import pytest

from scitex_stats import _provenance as prov
from scitex_stats._dispatch import run_test
from scitex_stats.reporting import full_report

X = [5.1, 4.9, 6.2, 5.8, 6.0, 5.5, 5.3, 6.1]
Y = [6.3, 6.9, 7.1, 6.5, 7.4, 6.8, 7.0, 6.6]
SRC = Path(__file__).resolve().parents[2] / "src" / "scitex_stats"


def _without_wall_clock(result):
    out = copy.deepcopy(result)
    out["provenance"].pop("timestamp_utc")
    out["provenance"].pop("receipt_sha256")
    return out


@pytest.fixture(scope="module")
def ttest_result():
    return run_test("ttest_ind", data=X, data2=Y)


@pytest.fixture(scope="module")
def mwu_result():
    return run_test("mannwhitneyu", data=X, data2=Y)


# ----- canonical hashing --------------------------------------------------- #


def test_hash_array_is_independent_of_container_and_int_dtype():
    # Arrange
    containers = [[1, 2, 3], np.array([1, 2, 3], dtype=np.int64), np.array([1.0, 2.0, 3.0])]
    # Act
    hashes = {prov.hash_array(c) for c in containers}
    # Assert
    assert len(hashes) == 1


def test_hash_array_folds_negative_zero_and_nan_payloads():
    # Arrange
    odd_nan = np.frombuffer(np.array([0x7FF8000000000001], dtype="<u8").tobytes(), dtype="<f8")[0]
    # Act
    folded = prov.hash_array([-0.0, odd_nan])
    # Assert
    assert folded == prov.hash_array([0.0, np.nan])


def test_hash_array_distinguishes_shape():
    # Arrange
    flat = [1.0, 2.0, 3.0, 4.0]
    # Act
    square = prov.hash_array(np.reshape(flat, (2, 2)))
    # Assert
    assert prov.hash_array(flat) != square


def test_hash_array_matches_documented_digest_input():
    # Arrange
    arr = np.array([1.5, 2.5], dtype="<f8")
    expected = hashlib.sha256(b"scitex-stats:ndarray:v1:<f8:[2]\0" + arr.tobytes()).hexdigest()
    # Act
    actual = prov.hash_array([1.5, 2.5])
    # Assert
    assert actual == expected


def test_combine_hashes_matches_clew_when_installed():
    # Arrange
    clew_hash = pytest.importorskip("scitex_clew._hash")
    hashes = {"data": "ab" * 32, "data2": "cd" * 32}
    # Act
    combined = prov.combine_hashes(hashes)
    # Assert
    assert combined == clew_hash.combine_hashes(hashes)


# ----- receipt schema ------------------------------------------------------ #


@pytest.mark.parametrize(
    "path,expected",
    [
        (("schema",), prov.SCHEMA),
        (("api",), "run_test"),
        (("test", "name"), "ttest_ind"),
        (("test", "function"), "test_ttest_ind"),
        (("test", "parameters", "alternative"), "two-sided"),
        (("test", "parameters", "nan_policy"), "omit"),
        (("inputs", "data", "sha256"), prov.hash_array(X)),
        (("inputs", "data2", "n"), 8),
        (("randomness", "seed"), None),
        (("randomness", "stochastic"), False),
        (("hash_algorithm",), "sha256"),
    ],
)
def test_run_test_receipt_field(ttest_result, path, expected):
    # Arrange
    node = ttest_result["provenance"]
    # Act
    for key in path:
        node = node[key]
    # Assert
    assert node == expected


def test_receipt_result_hash_covers_result(ttest_result):
    # Arrange
    recorded = ttest_result["provenance"]["result_sha256"]
    # Act
    actual = prov.hash_result(ttest_result)
    # Assert
    assert actual == recorded


def test_receipt_hash_covers_receipt(ttest_result):
    # Arrange
    recorded = ttest_result["provenance"]["receipt_sha256"]
    # Act
    actual = prov.receipt_hash(ttest_result["provenance"])
    # Assert
    assert actual == recorded


def test_receipt_records_library_versions(ttest_result):
    # Arrange
    required = {"scitex-stats", "numpy", "scipy", "pandas", "statsmodels", "python"}
    # Act
    recorded = set(ttest_result["provenance"]["versions"])
    # Assert
    assert required <= recorded


def test_receipt_timestamp_is_utc_iso8601(ttest_result):
    # Arrange
    pattern = r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z"
    # Act
    stamp = ttest_result["provenance"]["timestamp_utc"]
    # Assert
    assert re.fullmatch(pattern, stamp)


# ----- determinism --------------------------------------------------------- #


@pytest.mark.parametrize(
    "name,kwargs",
    [
        ("ttest_ind", {"data": X, "data2": Y}),
        ("mannwhitneyu", {"data": X, "data2": Y}),
        ("pearson", {"data": X, "data2": Y}),
        ("wilcoxon", {"data": X, "data2": Y}),
        ("anova", {"groups": [X, Y, [5.9, 6.4, 6.1, 5.7]]}),
        ("chi2", {"groups": [[12, 5], [7, 9]]}),
    ],
)
def test_run_test_is_bit_identical_across_repeated_runs(name, kwargs):
    # Arrange
    first = _without_wall_clock(run_test(name, **kwargs))
    # Act
    repeats = [_without_wall_clock(run_test(name, **kwargs)) for _ in range(2)]
    # Assert
    assert repeats == [first, first]


@pytest.fixture(scope="module")
def bootstrap_reports(mwu_result):
    kw = {"data": X, "data2": Y, "n_bootstrap": 500}
    return full_report(mwu_result, **kw), full_report(mwu_result, **kw), full_report(mwu_result, seed=7, **kw)


def test_full_report_bootstrap_ci_is_reproducible(bootstrap_reports):
    # Arrange
    a, b, _ = bootstrap_reports
    # Act
    same = a["provenance"]["result_sha256"] == b["provenance"]["result_sha256"]
    # Assert
    assert same


def test_full_report_default_seed_is_42(bootstrap_reports):
    # Arrange
    a, _, _ = bootstrap_reports
    # Act
    seed = a["provenance"]["randomness"]["seed"]
    # Assert
    assert seed == 42


def test_full_report_marks_bootstrap_as_stochastic(bootstrap_reports):
    # Arrange
    a, _, _ = bootstrap_reports
    # Act
    randomness = a["provenance"]["randomness"]
    # Assert
    assert (randomness["stochastic"], a["ci_method"]) == (True, "bootstrap")


def test_full_report_records_overridden_seed(bootstrap_reports):
    # Arrange
    _, _, c = bootstrap_reports
    # Act
    seed = c["provenance"]["randomness"]["seed"]
    # Assert
    assert seed == 7


def test_full_report_random_state_warns_deprecated(mwu_result):
    # Arrange
    kw = {"data": X, "data2": Y, "n_bootstrap": 300}
    # Act
    call = lambda: full_report(mwu_result, random_state=3, **kw)  # noqa: E731
    # Assert
    with pytest.warns(DeprecationWarning):
        call()


def test_full_report_random_state_is_a_seed_alias(mwu_result):
    # Arrange
    kw = {"data": X, "data2": Y, "n_bootstrap": 300}
    # Act
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        old = full_report(mwu_result, random_state=3, **kw)
    # Assert
    assert old["ci"] == full_report(mwu_result, seed=3, **kw)["ci"]


def test_library_source_uses_no_global_numpy_random_state():
    # Arrange
    pattern = re.compile(r"np\.random\.(?!default_rng\b)[a-z_]+\(")
    # Act
    offenders = [
        f"{p.relative_to(SRC)}:{i}"
        for p in SRC.rglob("*.py")
        for i, line in enumerate(p.read_text().splitlines(), 1)
        if pattern.search(line)
    ]
    # Assert
    assert not offenders, offenders


# ----- input integrity ----------------------------------------------------- #


@pytest.fixture(scope="module")
def nan_report():
    x = X[:3] + [np.nan] + X[3:]
    return run_test("ttest_ind", data=x, data2=Y)["input_integrity"]


@pytest.mark.parametrize(
    "field,expected",
    [
        ("n_input", 9),
        ("n_used", 8),
        ("n_excluded", 1),
        ("excluded_indices", [3]),
        ("excluded_reason", {"nan": 1}),
    ],
)
def test_nan_exclusion_is_reported(nan_report, field, expected):
    # Arrange
    rep = nan_report["inputs"]["data"]
    # Act
    value = rep[field]
    # Assert
    assert value == expected


def test_nan_exclusion_total_is_reported(nan_report):
    # Arrange
    rep = nan_report
    # Act
    total = rep["n_excluded_total"]
    # Assert
    assert total == 1


def test_nan_in_paired_design_excludes_the_whole_pair():
    # Arrange
    y = list(Y)
    y[2] = np.nan
    # Act
    ii = run_test("pearson", data=X, data2=y)["input_integrity"]["inputs"]
    # Assert
    assert (ii["data"]["excluded_indices"], ii["data2"]["excluded_reason"]) == ([2], {"nan_pairwise": 1})


@pytest.mark.parametrize(
    "name,kwargs,match",
    [
        ("ttest_ind", {"data": X + [np.nan], "data2": Y, "nan_policy": "raise"}, "nan_policy='raise'"),
        ("ttest_ind", {"data": X + [np.inf], "data2": Y}, "infinite"),
        ("ttest_ind", {"data": [], "data2": Y}, "empty"),
        ("ttest_ind", {"data": [np.nan, np.nan], "data2": Y}, "no values left"),
        ("ttest_ind", {"data": ["1.0", "2.0"], "data2": Y}, "non-numeric"),
        ("ttest_ind", {"data": [1.0, "a"], "data2": Y}, "non-numeric"),
        ("wilcoxon", {"data": X, "data2": Y[:5]}, "equal length"),
        ("chi2", {"groups": [[12, np.nan], [7, 9]]}, "contingency"),
    ],
)
def test_bad_inputs_raise_explicitly(name, kwargs, match):
    # Arrange
    call = lambda: run_test(name, **kwargs)  # noqa: E731
    # Act
    expectation = pytest.raises(prov.InputIntegrityError, match=match)
    # Assert
    with expectation:
        call()


def test_type_coercion_is_reported():
    # Arrange
    r = run_test("ttest_ind", data=[5, 4, 6, 5, 6], data2=np.array(Y))
    # Act
    ii = r["input_integrity"]["inputs"]
    # Assert
    assert (ii["data"]["coercion"], ii["data2"]["coercion"]) == ("list[int64] -> ndarray[float64]", None)


def test_none_values_are_counted_as_nan():
    # Arrange
    r = run_test("ttest_ind", data=[5.0, None, 6.0, 5.5], data2=Y)
    # Act
    rep = r["input_integrity"]["inputs"]["data"]
    # Assert
    assert (rep["none_as_nan"], rep["n_excluded"]) == (1, 1)
