"""Keep one-sample hypotheses consistent across dispatch, CLI, MCP and replay."""

import asyncio
from functools import partial
import json

from click.testing import CliRunner
import pytest
from scipy import stats
import scitex_stats as ss

from scitex_stats._cli import main
from scitex_stats._mcp._handlers._run_test import run_test_handler

SAMPLE = [-.2, .1, .4, .9, 1.5, 1.8, 2.3, 2.8]
NATIVE = [
    ("ttest_1samp", {"popmean": 0.}, partial(stats.ttest_1samp, popmean=0.)),
    ("ttest_1samp", {"popmean": .5}, partial(stats.ttest_1samp, popmean=.5)),
    ("ks_1samp", {}, partial(stats.ks_1samp, cdf=stats.norm.cdf)),
]
MCP = [("ttest_1samp", partial(stats.ttest_1samp, popmean=0.)),
       ("ks_1samp", partial(stats.ks_1samp, cdf=stats.norm.cdf))]
ALTERNATIVES = ["two-sided", "less", "greater"]


@pytest.mark.parametrize("name, kwargs, reference", NATIVE)
@pytest.mark.parametrize("alternative", ALTERNATIVES)
def test_native_one_sample_dispatch_matches_requested_scipy_hypothesis(name, kwargs, reference, alternative):
    # Arrange
    expected = reference(SAMPLE, alternative=alternative)
    # Act
    report = ss.run_test(name, data=SAMPLE, alternative=alternative, **kwargs)
    params = report["provenance"]["test"]["parameters"]
    # Assert
    assert (report["statistic"], report["pvalue"], params["alternative"]) == (
        pytest.approx(float(expected.statistic)), pytest.approx(float(expected.pvalue)), alternative,
    )


@pytest.mark.parametrize("name, reference", MCP)
@pytest.mark.parametrize("alternative", ALTERNATIVES)
def test_mcp_one_sample_dispatch_matches_requested_scipy_hypothesis(name, reference, alternative):
    # Arrange
    expected = reference(SAMPLE, alternative=alternative)
    # Act
    report = asyncio.run(run_test_handler(name, data=[SAMPLE], alternative=alternative))
    params = report["provenance"]["test"]["parameters"]
    # Assert
    assert (report["success"], report["alternative"], report["statistic"], report["p_value"], params["alternative"]) == (
        True, alternative, pytest.approx(float(expected.statistic)), pytest.approx(float(expected.pvalue)), alternative,
    )


@pytest.mark.parametrize("name, reference", MCP)
@pytest.mark.parametrize("alternative", ALTERNATIVES)
def test_root_cli_one_sample_dispatch_matches_requested_hypothesis(name, reference, alternative, tmp_path):
    # Arrange
    source = tmp_path / "sample.json"
    source.write_text(json.dumps(SAMPLE))
    expected = reference(SAMPLE, alternative=alternative)
    # Act
    result = CliRunner().invoke(main, ["tests", "execute", name, str(source), "--alternative", alternative])
    report = json.loads(result.output)
    # Assert
    assert (result.exit_code, report["statistic"], report["pvalue"]) == (
        0, pytest.approx(float(expected.statistic)), pytest.approx(float(expected.pvalue)),
    )


@pytest.mark.parametrize("name, kwargs, reference", NATIVE)
@pytest.mark.parametrize("alternative", ALTERNATIVES)
def test_native_one_sample_receipt_replays_the_requested_hypothesis(name, kwargs, reference, alternative):
    # Arrange
    report = ss.run_test(name, data=SAMPLE, alternative=alternative, **kwargs)
    # Act
    checked = ss.verify(report, data=SAMPLE)
    # Assert
    assert checked["verified"] is True, checked


@pytest.mark.parametrize("name, reference", MCP)
@pytest.mark.parametrize("alternative", ALTERNATIVES)
def test_mcp_one_sample_receipt_replays_the_requested_hypothesis(name, reference, alternative):
    # Arrange
    report = asyncio.run(run_test_handler(name, data=[SAMPLE], alternative=alternative))
    # Act
    checked = ss.verify(report, groups=[SAMPLE])
    # Assert
    assert checked["verified"] is True, checked


def test_default_shapiro_remains_a_nondirectional_control():
    # Arrange
    expected = stats.shapiro(SAMPLE)
    # Act
    native = ss.run_test("shapiro", data=SAMPLE)
    mcp = asyncio.run(run_test_handler("shapiro", data=[SAMPLE]))
    # Assert
    assert (native["pvalue"], mcp["success"], mcp["p_value"]) == (
        pytest.approx(float(expected.pvalue)), True, pytest.approx(float(expected.pvalue)),
    )
