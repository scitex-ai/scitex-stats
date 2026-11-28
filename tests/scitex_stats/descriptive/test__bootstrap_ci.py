"""Tests for `scitex_stats.descriptive._bootstrap_ci.bootstrap_ci`.

Every test runs the real resampler (no mocks). The coverage checks draw many
datasets from distributions with a known population parameter under fixed
seeds, so they are deterministic.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

import scitex_stats
from scitex_stats.descriptive import bootstrap_ci as bootstrap_ci_descriptive
from scitex_stats.descriptive._bootstrap_ci import bootstrap_ci


def _skewed() -> np.ndarray:
    return np.random.default_rng(0).lognormal(mean=0.0, sigma=1.0, size=60)


@pytest.fixture(scope="module")
def skewed() -> np.ndarray:
    return _skewed()


@pytest.fixture(scope="module")
def median_res() -> dict:
    return bootstrap_ci(_skewed(), "median", n_resamples=2000, seed=7)


def _mean_diff(x, y):
    return float(np.mean(y) - np.mean(x))


def _corr(a, b):
    return float(np.corrcoef(a, b)[0, 1])


def _paired_diff(a, b):
    return float(np.mean(a - b))


@pytest.fixture(scope="module")
def two_sample_res() -> dict:
    rng = np.random.default_rng(5)
    a, b = rng.normal(0, 1, 40), rng.normal(1, 1, 30)
    return bootstrap_ci(a, _mean_diff, data2=b, n_resamples=1500)


@pytest.fixture(scope="module")
def paired_nan_res() -> dict:
    x = np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0])
    y = np.array([1.5, np.nan, 3.0, 4.5, 4.0, 7.0])
    return bootstrap_ci(
        x, _paired_diff, data2=y, paired=True, nan_policy="omit", n_resamples=300
    )


@pytest.fixture(scope="module")
def omit_res() -> dict:
    x = np.array([1.0, 2.0, np.nan, 4.0, 5.0, np.nan, 7.0])
    return bootstrap_ci(x, nan_policy="omit", n_resamples=500)


# --- public surface ---------------------------------------------------------


def test_bootstrap_ci_is_exported_at_top_level():
    # Arrange
    public = scitex_stats
    # Act
    fn = public.bootstrap_ci
    # Assert
    assert fn is bootstrap_ci


def test_bootstrap_ci_is_exported_from_descriptive():
    # Arrange
    expected = bootstrap_ci
    # Act
    fn = bootstrap_ci_descriptive
    # Assert
    assert fn is expected


def test_bootstrap_ci_is_listed_in_all():
    # Arrange
    names = scitex_stats.__all__
    # Act
    listed = "bootstrap_ci" in names
    # Assert
    assert listed


def test_median_estimate_is_sample_median(skewed, median_res):
    # Arrange
    expected = float(np.median(skewed))
    # Act
    estimate = median_res["estimate"]
    # Assert
    assert estimate == pytest.approx(expected)


def test_median_interval_brackets_estimate(median_res):
    # Arrange
    res = median_res
    # Act
    bracketed = res["ci_lower"] < res["estimate"] < res["ci_upper"]
    # Assert
    assert bracketed


def test_result_records_provenance_fields(median_res):
    # Arrange
    keys = (
        "statistic",
        "ci_level",
        "method",
        "n",
        "n_resamples",
        "seed",
        "nan_policy",
        "n_nan_omitted",
    )
    # Act
    recorded = tuple(median_res[k] for k in keys)
    # Assert
    assert recorded == ("median", 0.95, "percentile", 60, 2000, 7, "raise", 0)


def test_result_describes_ci_method(median_res):
    # Arrange
    res = median_res
    # Act
    label = res["ci_method"]
    # Assert
    assert label == "percentile bootstrap (2000 resamples, seed 7)"


def test_result_renders_apa_ci(median_res):
    # Arrange
    from scitex_stats._utils._apa import format_ci

    expected = format_ci(median_res["ci_lower"], median_res["ci_upper"], 0.95)
    # Act
    rendered = median_res["ci_apa"]
    # Assert
    assert rendered == expected


def test_result_round_trips_through_json(median_res):
    # Arrange
    res = median_res
    # Act
    loaded = json.loads(json.dumps(res))
    # Assert
    assert loaded == res


def test_result_values_are_python_natives(median_res):
    # Arrange
    allowed = (str, int, float, bool)
    # Act
    types = {type(v) for v in median_res.values()}
    # Assert
    assert types <= set(allowed)


def test_result_saves_via_scitex_io(tmp_path, median_res):
    # Arrange
    sio = pytest.importorskip("scitex_io")
    path = tmp_path / "median_ci.json"
    # Act
    sio.save(median_res, str(path), verbose=False)
    # Assert
    assert json.loads(path.read_text()) == median_res


def test_percentile_bounds_match_hand_resampled_quantiles(skewed):
    # Arrange: an independent bootstrap distribution of the median
    idx = np.random.default_rng(99).integers(0, skewed.size, size=(20_000, skewed.size))
    lo, hi = np.percentile(np.median(skewed[idx], axis=-1), [2.5, 97.5])
    # Act
    res = bootstrap_ci(skewed, "median", n_resamples=20_000, seed=11)
    # Assert: independent draws agree up to Monte-Carlo error
    assert np.allclose(
        [res["ci_lower"], res["ci_upper"]], [lo, hi], atol=0.1 * (hi - lo)
    )


# --- determinism -------------------------------------------------------------


def test_same_seed_gives_identical_result(skewed):
    # Arrange
    kwargs = {"seed": 3, "n_resamples": 1000}
    # Act
    first, second = bootstrap_ci(skewed, **kwargs), bootstrap_ci(skewed, **kwargs)
    # Assert
    assert first == second


def test_different_seed_changes_bounds(skewed):
    # Arrange
    a = bootstrap_ci(skewed, seed=3, n_resamples=1000)
    # Act
    b = bootstrap_ci(skewed, seed=4, n_resamples=1000)
    # Assert
    assert (a["ci_lower"], a["ci_upper"]) != (b["ci_lower"], b["ci_upper"])


def test_does_not_touch_global_numpy_state(skewed):
    # Arrange
    np.random.seed(123)
    expected = np.random.random()
    np.random.seed(123)
    # Act
    bootstrap_ci(skewed, n_resamples=200)
    # Assert
    assert np.random.random() == expected


# --- statistics / methods ----------------------------------------------------


def test_mean_interval_matches_t_interval_for_normal_sample():
    # Arrange
    x = np.random.default_rng(1).normal(10.0, 2.0, size=80)
    se = x.std(ddof=1) / np.sqrt(x.size)
    expected = [x.mean() - 1.99 * se, x.mean() + 1.99 * se]
    # Act
    res = bootstrap_ci(x, "mean", n_resamples=4000, seed=1)
    # Assert
    assert np.allclose([res["ci_lower"], res["ci_upper"]], expected, atol=0.25 * se)


@pytest.mark.parametrize("method", ["percentile", "basic", "bca"])
def test_all_methods_return_ordered_finite_interval(skewed, method):
    # Arrange
    kwargs = {"method": method, "n_resamples": 2000}
    # Act
    res = bootstrap_ci(skewed, "median", **kwargs)
    # Assert
    assert (
        np.isfinite(res["ci_lower"])
        and res["ci_lower"] < res["ci_upper"]
        and np.isfinite(res["ci_upper"])
    )


def test_higher_confidence_gives_wider_interval(skewed):
    # Arrange
    narrow = bootstrap_ci(skewed, confidence=0.80, n_resamples=3000)
    # Act
    wide = bootstrap_ci(skewed, confidence=0.99, n_resamples=3000)
    # Assert
    assert wide["ci_upper"] - wide["ci_lower"] > narrow["ci_upper"] - narrow["ci_lower"]


def test_callable_statistic_is_named_after_function(two_sample_res):
    # Arrange
    res = two_sample_res
    # Act
    name = res["statistic"]
    # Assert
    assert name == "_mean_diff"


def test_two_sample_result_reports_both_sizes(two_sample_res):
    # Arrange
    res = two_sample_res
    # Act
    sizes = (res["n"], res["n2"], res["paired"])
    # Assert
    assert sizes == (40, 30, False)


def test_two_sample_interval_excludes_zero_for_clear_shift(two_sample_res):
    # Arrange: a 1-SD shift at n = 40 / 30
    res = two_sample_res
    # Act
    lower = res["ci_lower"]
    # Assert
    assert lower > 0


def test_paired_resampling_preserves_correlation():
    # Arrange: y is a noisy copy of x; independent resampling would centre on 0
    rng = np.random.default_rng(6)
    x = rng.normal(size=50)
    y = x + rng.normal(scale=0.3, size=50)
    # Act
    res = bootstrap_ci(x, _corr, data2=y, paired=True, n_resamples=1500)
    # Assert
    assert res["ci_lower"] > 0.8


# --- coverage on known distributions ----------------------------------------


def _coverage(sampler, truth, statistic, n, reps, seed):
    rng = np.random.default_rng(seed)
    hits = 0
    for i in range(reps):
        res = bootstrap_ci(sampler(rng, n), statistic, n_resamples=1000, seed=i)
        hits += res["ci_lower"] <= truth <= res["ci_upper"]
    return hits / reps


def test_median_ci_coverage_on_exponential():
    # Arrange: Exponential(1) has population median ln 2
    def sampler(r, n):
        return r.exponential(1.0, n)

    # Act
    cov = _coverage(sampler, np.log(2), "median", n=60, reps=300, seed=2024)
    # Assert: nominal 0.95; Monte-Carlo SE ~0.013 at 300 reps
    assert 0.90 <= cov <= 0.99, cov


def test_mean_ci_coverage_on_normal():
    # Arrange
    def sampler(r, n):
        return r.normal(3.0, 1.5, n)

    # Act
    cov = _coverage(sampler, 3.0, "mean", n=40, reps=300, seed=2025)
    # Assert
    assert 0.90 <= cov <= 0.99, cov


# --- NaN policy ---------------------------------------------------------------


def test_nan_omit_reports_remaining_n(omit_res):
    # Arrange
    res = omit_res
    # Act
    n = res["n"]
    # Assert
    assert n == 5


def test_nan_omit_reports_dropped_count(omit_res):
    # Arrange
    res = omit_res
    # Act
    dropped = res["n_nan_omitted"]
    # Assert
    assert dropped == 2


def test_nan_omit_equals_running_on_clean_data(omit_res):
    # Arrange
    clean = np.array([1.0, 2.0, 4.0, 5.0, 7.0])
    # Act
    res = bootstrap_ci(clean, nan_policy="omit", n_resamples=500)
    # Assert
    assert res | {"n_nan_omitted": 2} == omit_res


def test_nan_omit_paired_keeps_complete_pairs(paired_nan_res):
    # Arrange
    res = paired_nan_res
    # Act
    sizes = (res["n"], res["n2"])
    # Assert
    assert sizes == (4, 4)


def test_nan_omit_paired_counts_dropped_pairs(paired_nan_res):
    # Arrange
    res = paired_nan_res
    # Act
    dropped = res["n_nan_omitted"]
    # Assert
    assert dropped == 2


# --- explicit errors ----------------------------------------------------------


@pytest.mark.parametrize(
    "data, kwargs, error, match",
    [
        ([], {}, ValueError, "at least 2"),
        ([1.0], {}, ValueError, "at least 2"),
        ([1.0, 2.0, np.nan, 4.0], {}, ValueError, "NaN"),
        ([np.nan, 1.0, np.nan], {"nan_policy": "omit"}, ValueError, "at least 2"),
        ([3.0] * 20, {}, ValueError, "constant"),
        ([1.0, 2.0, np.inf], {}, ValueError, "infinite"),
        (np.ones((3, 3)), {}, ValueError, "one-dimensional"),
        (["a", "b", "c"], {}, TypeError, "numeric"),
        (
            [1.0, 2.0, 3.0, 4.0],
            {"statistic": "mode"},
            ValueError,
            "statistic must be one of",
        ),
        ([1.0, 2.0, 3.0, 4.0], {"statistic": 3}, TypeError, "statistic must be"),
        (
            [1.0, 2.0, 3.0, 4.0],
            {"method": "studentized"},
            ValueError,
            "method must be one of",
        ),
        (
            [1.0, 2.0, 3.0, 4.0],
            {"nan_policy": "propagate"},
            ValueError,
            "nan_policy must be one of",
        ),
        ([1.0, 2.0, 3.0, 4.0], {"confidence": 1.0}, ValueError, "confidence"),
        ([1.0, 2.0, 3.0, 4.0], {"confidence": 95}, ValueError, "confidence"),
        ([1.0, 2.0, 3.0, 4.0], {"n_resamples": 0}, ValueError, "n_resamples"),
        ([1.0, 2.0, 3.0, 4.0], {"seed": 1.5}, TypeError, "seed"),
        ([1.0, 2.0, 3.0, 4.0], {"paired": True}, ValueError, "requires data2"),
        ([1.0, 2.0, 3.0, 4.0], {"data2": [1.0, 2.0, 3.0]}, ValueError, "one-sample"),
        (
            [1.0, 2.0, 3.0],
            {"statistic": _paired_diff, "data2": [1.0, 2.0], "paired": True},
            ValueError,
            "equal lengths",
        ),
    ],
)
def test_invalid_input_raises_explicitly(data, kwargs, error, match):
    # Arrange
    call_kwargs = dict(kwargs)
    # Act
    call = lambda: bootstrap_ci(data, **call_kwargs)  # noqa: E731
    # Assert
    with pytest.raises(error, match=match):
        call()
