"""Reject discarded or missing MCP input groups before test computation."""

import asyncio
import json
import os
from pathlib import Path
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from scipy import stats

from scitex_stats import _server
from scitex_stats._mcp.handlers import run_test_handler

X = [-.2, .1, .4, .9, 1.5, 1.8, 2.3, 2.8]
Y = [-.6, -.1, .5, .7, 1.2, 1.7, 2., 2.5]
TWO = ["ttest_ind", "ttest_paired", "brunner_munzel", "mannwhitneyu", "wilcoxon",
       "pearson", "spearman", "kendall", "theilsen", "ks_2samp"]
ONE = ["ttest_1samp", "shapiro", "normality", "ks_1samp"]
BAD = [(name, [X,Y,X][:n], 2) for name in TWO for n in [0,1,3]] + [
    (name, [X,Y][:n], 1) for name in ONE for n in [0,2]]
ALIASES = ["ttest", "ttest_rel", "brunnermunzel", "mann_whitney"]
VALID = [(name, [X,Y]) for name in TWO] + [(name, [X]) for name in ONE]


async def registered_call(**kwargs):
    function = getattr(_server.run_test, "fn", _server.run_test)
    return json.loads(await function(**kwargs))


def count_error(name, expected, actual):
    noun = "data group" if expected == 1 else "data groups"
    return {"success": False, "error": f"{name} requires exactly {expected} {noun}; got {actual}"}


@pytest.mark.parametrize("call", [run_test_handler, registered_call])
@pytest.mark.parametrize("name, groups, expected", BAD)
def test_bad_group_counts_fail_before_execution(call, name, groups, expected):
    # Arrange
    wanted = count_error(name, expected, len(groups))
    # Act
    report = asyncio.run(call(test_name=name, data=groups))
    # Assert
    assert report == wanted


@pytest.mark.parametrize("call", [run_test_handler, registered_call])
@pytest.mark.parametrize("name", ALIASES)
def test_alias_count_errors_preserve_the_requested_name(call, name):
    # Arrange
    groups = [X,Y,X]
    # Act
    report = asyncio.run(call(test_name=name, data=groups))
    # Assert
    assert report == count_error(name, 2, 3)


@pytest.mark.parametrize("call", [run_test_handler, registered_call])
@pytest.mark.parametrize("name, groups", VALID)
def test_valid_group_counts_preserve_success_and_complete_input_receipts(call, name, groups):
    # Arrange
    expected = {f"data[{i}]" for i in range(len(groups))}
    # Act
    report = asyncio.run(call(test_name=name, data=groups))
    # Assert
    assert (report["success"], report["test_name"], set(report["provenance"]["inputs"])) == (True, name, expected)


@pytest.mark.parametrize("call", [run_test_handler, registered_call])
@pytest.mark.parametrize("name, columns, expected", [
    ("ttest_1samp", ["a", "b"], 1), ("ttest_ind", ["a", "b", "c"], 2),
])
def test_extra_csv_columns_are_not_silently_discarded(call, name, columns, expected, tmp_path):
    # Arrange
    source = tmp_path/"samples.csv"
    source.write_text("a;b;c\n" + "".join(f"{x};{y};{x}\n" for x,y in zip(X,Y)))
    # Act
    report = asyncio.run(call(test_name=name, data_file=str(source), columns=columns, sep=";"))
    # Assert
    assert report == count_error(name, expected, len(columns))


def collect_protocol(directory):
    params = StdioServerParameters(command=sys.executable, args=["-m", "scitex_stats", "mcp", "start"],
        env={**os.environ, "HOME": str(directory), "TMPDIR": str(directory),
             "SCITEX_DIR": str(directory/"state"), "XDG_CACHE_HOME": str(directory/"cache"),
             "FASTMCP_CHECK_FOR_UPDATES": "off",
             "PYTHONPATH": str(Path(__file__).resolve().parents[2]/"src")}, cwd=directory)
    async def collect():
        with (directory/"server.log").open("w") as errors:
            async with (stdio_client(params, errlog=errors) as (read,write), ClientSession(read,write) as session):
                await session.initialize()
                listing = await session.list_tools()
                cases = [("ttest_ind", [X,Y,X]), ("ttest_1samp", [X,Y]), ("ttest_ind", [X,Y])]
                reports = [json.loads((await session.call_tool("run_test", {"test_name": name, "data": groups})).content[0].text)
                           for name,groups in cases]
                return {"tools": [tool.name for tool in listing.tools], "reports": reports}
    result = asyncio.run(asyncio.wait_for(collect(), timeout=30))
    snapshot = json.dumps(result,indent=2)
    (directory/"protocol-results.json").write_text(snapshot)
    return snapshot


@pytest.fixture(scope="module")
def protocol_snapshot(tmp_path_factory):
    return collect_protocol(tmp_path_factory.mktemp("arity-stdio"))


@pytest.fixture
def protocol(protocol_snapshot):
    return json.loads(protocol_snapshot)


@pytest.mark.parametrize("index, name, expected, actual", [(0,"ttest_ind",2,3),(1,"ttest_1samp",1,2)])
def test_stdio_extra_groups_return_the_count_failure(protocol, index, name, expected, actual):
    # Arrange
    wanted = count_error(name,expected,actual)
    # Act
    report = protocol["reports"][index]
    # Assert
    assert report == wanted


def test_stdio_valid_two_group_request_still_matches_scipy(protocol):
    # Arrange
    expected = stats.ttest_ind(X,Y)
    # Act
    report = protocol["reports"][2]
    # Assert
    assert (len(protocol["tools"]), report["success"], report["statistic"], report["p_value"]) == (
        18, True, pytest.approx(float(expected.statistic)), pytest.approx(float(expected.pvalue)),
    )
