"""File separator overrides must be bound into the analysis receipt."""

import asyncio
import hashlib
import math

import pytest

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
            "file_sha256": hashlib.sha256(content).hexdigest(),
        },
        content,
    )
