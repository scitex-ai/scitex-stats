"""Reject infinite descriptive inputs while retaining finite/NaN contracts."""

import asyncio
from datetime import datetime
import json
import math
import statistics

import pytest

from scitex_stats import _server
from scitex_stats._mcp.handlers import describe_handler


def call_handler(data):
    return asyncio.run(describe_handler(data=data))


def call_server(data):
    function = getattr(_server.describe, "fn", _server.describe)
    return json.loads(asyncio.run(function(data=data)))


@pytest.mark.parametrize("call", [call_handler, call_server])
@pytest.mark.parametrize("data", [[float("inf")], [-float("inf")],
                                 [1., float("inf")], [1., -float("inf")],
                                 [-float("inf"), float("inf")],
                                 [float("nan"), 1., float("inf")]])
def test_describe_rejects_infinite_samples(call, data):
    # Arrange
    # Act
    report = call(data)
    # Assert
    assert report == {"success": False, "error": "Data must contain only finite values after removing NaN"}


@pytest.mark.parametrize("call", [call_handler, call_server])
@pytest.mark.parametrize("data", [[], [float("nan"), float("nan")]])
def test_describe_preserves_empty_after_nan_removal_error(call, data):
    # Arrange
    # Act
    report = call(data)
    # Assert
    assert report == {"success": False, "error": "No valid data points"}


@pytest.mark.parametrize("call", [call_handler, call_server])
@pytest.mark.parametrize("data, clean, percentiles", [
    ([1., 2., 3.], [1., 2., 3.], {"25": 1.5, "50": 2., "75": 2.5}),
    ([float("nan"), 1., 2., 3., float("nan")], [1., 2., 3.], {"25": 1.5, "50": 2., "75": 2.5}),
    ([-5., -1., 2., 8.], [-5., -1., 2., 8.], {"25": -2., "50": .5, "75": 3.5}),
])
def test_describe_finite_results_match_standard_library(call, data, clean, percentiles):
    # Arrange
    n = len(clean)
    expected = {"mean": statistics.fmean(clean), "median": statistics.median(clean),
                "std": statistics.stdev(clean), "var": statistics.variance(clean),
                "sem": statistics.stdev(clean) / math.sqrt(n), "min": min(clean),
                "max": max(clean), "range": max(clean)-min(clean),
                "iqr": percentiles["75"]-percentiles["25"]}
    # Act
    report = call(data)
    observed = {name: report[name] for name in expected}
    timestamp = datetime.fromisoformat(report["timestamp"])
    # Assert
    assert (report["success"], report["n"], observed, report["percentiles"], isinstance(timestamp, datetime)) == (
        True, n, pytest.approx(expected), percentiles, True,
    )
