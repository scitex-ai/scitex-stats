"""File separator overrides must be bound into the analysis receipt."""

import asyncio
import copy
import hashlib
import math

import pytest

from scitex_stats import verify
from scitex_stats._mcp._handlers._run_test import run_test_handler


def test_explicit_separator_preserves_data_and_records_source(tmp_path):
    # Arrange
    content = b"x;y;note,tag\n1;2;a,b\n2;4;c,d\n3;6;e,f\n4;8;g,h\n"
    path = tmp_path / "ambiguous.csv"
    path.write_bytes(content)
    # Act
    result = asyncio.run(
        run_test_handler(
            "ttest_paired",
            data_file=str(path),
            columns=["x", "y"],
            sep=";",
        )
    )
    # Assert
    assert (
        result["success"],
        result["statistic"],
        result["provenance"]["source"],
        path.read_bytes(),
    ) == (
        True,
        pytest.approx(-math.sqrt(15), rel=1e-12),
        {
            "data_file": str(path),
            "columns": ["x", "y"],
            "sep": ";",
            "sep_used": ";",
            "file_sha256": hashlib.sha256(content).hexdigest(),
        },
        content,
    )


@pytest.mark.parametrize("separator", [",", "\t", ";", "|", " "])
def test_auto_file_separator_is_reported_with_exact_statistic(tmp_path, separator):
    # Arrange
    path = tmp_path / "automatic.csv"
    content = "\n".join(separator.join(row) for row in [
        ["x", "y"], ["1", "2"], ["2", "4"], ["3", "6"], ["4", "8"],
    ]) + "\n"
    path.write_text(content)
    before = path.read_bytes()
    # Act
    result = asyncio.run(run_test_handler(
        "ttest_paired", data_file=str(path), columns=["x", "y"],
    ))
    source = result.get("provenance", {}).get("source", {})
    # Assert
    assert (result["success"], source.get("sep_used"), "sep" in source,
            result["statistic"], path.read_bytes()) == (
        True, separator, False, pytest.approx(-math.sqrt(15), rel=1e-12), before,
    )


def test_tsv_tab_contract_is_reported_with_omitted_override(tmp_path):
    # Arrange
    path = tmp_path / "automatic.TSV"
    path.write_text("x\ty\n1\t2\n2\t4\n3\t6\n4\t8\n")
    # Act
    result = asyncio.run(run_test_handler(
        "ttest_paired", data_file=str(path), columns=["x", "y"], sep=None,
    ))
    # Assert
    assert (result["success"], result["provenance"]["source"].get("sep_used"),
            "sep" in result["provenance"]["source"]) == (True, "\t", False)


def test_effective_separator_is_covered_by_receipt_verification(tmp_path):
    # Arrange
    path = tmp_path / "receipt.csv"
    path.write_text("x;y\n1;2\n2;4\n3;6\n4;8\n")
    result = asyncio.run(run_test_handler(
        "ttest_paired", data_file=str(path), columns=["x", "y"],
    ))
    modified = copy.deepcopy(result)
    modified["provenance"]["source"]["sep_used"] = ","
    # Act
    good, bad = verify(result), verify(modified)
    # Assert
    assert (result["provenance"]["source"].get("sep_used"), good["verified"],
            bad["verified"], any(c["name"] == "receipt" and c["status"] == "fail"
            for c in bad["checks"])) == (";", True, False, True)
