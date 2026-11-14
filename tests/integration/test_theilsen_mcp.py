"""Qualify Theil–Sen as slope estimation, without fabricated p-value fields."""

import asyncio
import json
import os
from pathlib import Path
import sys

import numpy as np
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from scipy import stats
import scitex_stats as ss

from scitex_stats import _server
from scitex_stats._dispatch import _TEST_NAME_ALIASES
from scitex_stats._mcp._handlers._run_test import _TEST_DISPATCH, run_test_handler

CASES = [
    ([0.,1.,2.,3.,4.,5.], [1.,3.,5.,7.,9.,60.]),
    ([0.,1.,2.,4.,7.,9.,11.], [2.,3.,8.,9.,11.,20.,21.]),
    ([0.,1.,2.,3.,4.,5.], [10.,8.,6.,4.,2.,-15.]),
    ([0.,float("nan"),2.,3.,4.,5.,6.,7.], [1.,3.,float("nan"),7.,9.,11.,13.,15.]),
]
FIELDS = ["slope", "intercept", "low_slope", "high_slope"]
ABSENT = {"statistic", "statistic_name", "p_value", "pvalue", "stars", "significant", "alpha"}
ERROR = "Theil-Sen returns a fixed two-sided 95% slope interval; one-sided alternatives are unsupported"


def reference(x,y):
    x,y = np.asarray(x),np.asarray(y)
    keep = np.isfinite(x) & np.isfinite(y)
    return stats.theilslopes(y[keep],x[keep],alpha=.95)


async def registered_call(**kwargs):
    return json.loads(await getattr(_server.run_test,"fn",_server.run_test)(**kwargs))


@pytest.mark.parametrize("x,y", CASES)
def test_native_estimator_matches_scipy_slope_intercept_and_slope_interval(x,y):
    # Arrange
    expected = reference(x,y)
    # Act
    result = ss.test_theilsen(x,y,verbose=False)
    # Assert
    assert [result[key] for key in FIELDS] == pytest.approx(tuple(expected))


@pytest.mark.parametrize("call", [run_test_handler, registered_call])
@pytest.mark.parametrize("x,y", CASES)
def test_mcp_theilsen_preserves_native_estimate_and_independent_reference(call,x,y):
    # Arrange
    expected = reference(x,y)
    native = ss.test_theilsen(x,y,verbose=False)
    # Act
    result = asyncio.run(call(test_name="theilsen",data=[x,y]))
    observed = [result.get(key) for key in FIELDS]
    payload = {key:result.get(key) for key in native}
    # Assert
    assert (result["success"], observed, payload, ABSENT & set(result), result.get("result_type"), result.get("confidence_level")) == (
        True, pytest.approx(tuple(expected)), native, set(), "regression_estimate", .95,
    )


@pytest.mark.parametrize("index", [0,3])
def test_mcp_theilsen_calls_real_native_estimator_in_worker(index,observe_native):
    # Arrange
    x,y = CASES[index]
    a,b = np.asarray(x),np.asarray(y)
    keep = np.isfinite(a) & np.isfinite(b)
    # Act
    with observe_native(ss.test_theilsen) as calls:
        report = asyncio.run(run_test_handler("theilsen",data=[x,y]))
    observed = [(row["x"].tolist(),row["y"].tolist(),row["verbose"]) for row in calls]
    # Assert
    assert (report["success"],observed) == (True,[(a[keep].tolist(),b[keep].tolist(),False)])


@pytest.mark.parametrize("call", [run_test_handler,registered_call])
@pytest.mark.parametrize("alternative", ["less","greater"])
def test_theilsen_rejects_unimplemented_one_sided_inference(call,alternative):
    # Arrange
    x,y = CASES[0]
    # Act
    result = asyncio.run(call(test_name="theilsen",data=[x,y],alternative=alternative))
    # Assert
    assert result == {"success":False,"error":ERROR}


@pytest.mark.parametrize("index", [0,3])
def test_theilsen_receipt_replays_the_estimate_with_original_paired_inputs(index):
    # Arrange
    x,y = CASES[index]
    result = asyncio.run(run_test_handler("theilsen",data=[x,y]))
    # Act
    checked = ss.verify(result,groups=[x,y])
    # Assert
    assert checked["verified"] is True, checked


@pytest.mark.parametrize("call", [run_test_handler,registered_call])
def test_theilsen_csv_route_preserves_column_selection_and_estimate(call,tmp_path):
    # Arrange
    x,y = CASES[0]
    source = tmp_path/"sample.csv"
    source.write_text("x;y\n"+"".join(f"{a};{b}\n" for a,b in zip(x,y)))
    expected = reference(x,y)
    # Act
    result = asyncio.run(call(test_name="theilsen",data_file=str(source),columns=["x","y"],sep=";"))
    # Assert
    assert (result["success"],[result.get(key) for key in FIELDS]) == (True,pytest.approx(tuple(expected)))


def test_native_generic_dispatch_stays_limited_to_its_advertised_test_names():
    # Arrange
    x,y = CASES[0]
    # Act
    with pytest.raises(ValueError,match="Unknown test: theilsen"):
        # Assert
        ss.run_test("theilsen",data=x,data2=y)


def test_catalogue_discovery_counts_remain_separate_from_behavior_acceptance():
    # Arrange
    native = set(ss.available_tests())
    mcp = set(_TEST_DISPATCH) | set(_TEST_NAME_ALIASES)
    # Act
    observed = (len(native),len(_TEST_DISPATCH),len(mcp),"theilsen" in native,"theilsen" in mcp)
    # Assert
    assert observed == (23,23,28,False,True)


def collect_protocol(directory):
    params = StdioServerParameters(command=sys.executable,args=["-m","scitex_stats","mcp","start"],
        env={**os.environ,"HOME":str(directory),"TMPDIR":str(directory),"SCITEX_DIR":str(directory/"state"),
             "XDG_CACHE_HOME":str(directory/"cache"),"FASTMCP_CHECK_FOR_UPDATES":"off",
             "PYTHONPATH":str(Path(__file__).resolve().parents[2]/"src")},cwd=directory)
    async def collect():
        with (directory/"server.log").open("w") as errors:
            async with (stdio_client(params,errlog=errors) as (read,write),ClientSession(read,write) as session):
                await session.initialize()
                listing = await session.list_tools()
                x,y = CASES[0]
                requests = [{"test_name":"theilsen","data":[x,y]},
                            {"test_name":"theilsen","data":[x,y],"alternative":"greater"},
                            {"test_name":"ttest_ind","data":[x,y]}]
                reports = [json.loads((await session.call_tool("run_test",row)).content[0].text) for row in requests]
                schemas = {t.name:getattr(t,"input_schema",None) or t.inputSchema for t in listing.tools}
                return {"schemas":schemas,"theilsen_reports":reports}
    result = asyncio.run(asyncio.wait_for(collect(),timeout=30))
    snapshot = json.dumps(result,indent=2)
    (directory/"protocol-results.json").write_text(snapshot)
    return snapshot


@pytest.fixture(scope="module")
def protocol_snapshot(tmp_path_factory):
    return collect_protocol(tmp_path_factory.mktemp("theilsen-stdio"))


@pytest.fixture
def protocol(protocol_snapshot):
    return json.loads(protocol_snapshot)


def test_stdio_theilsen_returns_estimation_fields_without_pvalue_placeholders(protocol):
    # Arrange
    expected = reference(*CASES[0])
    # Act
    result = protocol["theilsen_reports"][0]
    # Assert
    assert (len(protocol["schemas"]),result["success"],[result.get(key) for key in FIELDS],ABSENT & set(result),result.get("result_type")) == (
        18,True,pytest.approx(tuple(expected)),set(),"regression_estimate",
    )


def test_stdio_theilsen_returns_clear_one_sided_error(protocol):
    # Arrange
    # Act
    result = protocol["theilsen_reports"][1]
    # Assert
    assert result == {"success":False,"error":ERROR}


def test_stdio_ordinary_ttest_retains_its_statistic_and_pvalue(protocol):
    # Arrange
    expected = stats.ttest_ind(*CASES[0])
    # Act
    result = protocol["theilsen_reports"][2]
    # Assert
    assert (result["success"],result["statistic"],result["p_value"],"result_type" in result) == (
        True,pytest.approx(float(expected.statistic)),pytest.approx(float(expected.pvalue)),False,
    )
