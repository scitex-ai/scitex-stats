"""Check installed Stats numerical, CLI, MCP and skill behavior on owned data."""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata as metadata
import json
import math
import os
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify_installation(expected_version):
    try:
        distribution = metadata.distribution("scitex-stats")
        version = distribution.version
    except metadata.PackageNotFoundError as exc:
        raise RuntimeError("a fresh wheel installation is required") from exc
    require(version == expected_version, "installed candidate version mismatch")
    import scitex_stats

    module = Path(scitex_stats.__file__).resolve()
    require(
        module == (Path(sysconfig.get_path("purelib")) / "scitex_stats/__init__.py").resolve(),
        "a fresh wheel installation is required; source imports are refused",
    )
    direct_url = distribution.read_text("direct_url.json")
    require(
        not direct_url or not json.loads(direct_url).get("dir_info", {}).get("editable"),
        "a fresh wheel installation is required; editable installs are refused",
    )
    return {"version": version, "module": str(module)}


def verify_python(root):
    import numpy as np
    import scitex_stats
    from scitex_stats.correct import correct_fdr

    values, names = scitex_stats.describe([1.0, 2.0, 3.0], funcs=["mean"])
    require(names == ["mean"], "descriptive API returned unexpected labels")
    np.testing.assert_allclose(values, [2.0], rtol=1e-12)

    independent = scitex_stats.test_ttest_ind([1, 2, 3], [4, 5, 6])
    # Closed-form Student t reference: t=-sqrt(27/2), df=4.
    s = math.sqrt(27.0 / 35.0)
    np.testing.assert_allclose(
        [independent["statistic"], independent["pvalue"]],
        [-math.sqrt(13.5), 1.0 - 1.5 * s + 0.5 * s**3],
        rtol=1e-10,
    )

    csv_path = root / "paired.csv"
    original = b"before,after\n1,2\n2,4\n3,6\n4,8\n"
    csv_path.write_bytes(original)
    paired = scitex_stats.test_ttest_rel("before", "after", data=str(csv_path))
    np.testing.assert_allclose(paired["statistic"], -math.sqrt(15.0), rtol=1e-12)
    require(csv_path.read_bytes() == original, "file-backed analysis changed input")

    corrected = correct_fdr(
        [{"pvalue": p} for p in [0.01, 0.04, 0.03]], verbose=False
    )
    np.testing.assert_allclose(
        [row["pvalue_adjusted"] for row in corrected], [0.03, 0.04, 0.04],
        rtol=1e-12,
    )
    return {"mean": 2.0, "independent_t": independent["statistic"],
            "paired_t": paired["statistic"], "fdr_bh": [0.03, 0.04, 0.04],
            "input_unchanged": True}


def isolated_environment(root):
    return {
        "PATH": os.defpath,
        "HOME": str(root),
        "SCITEX_DIR": str(root / "state"),
        "MPLBACKEND": "Agg",
    }


async def verify_mcp(root):
    from importlib.resources import files

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-I", "-m", "scitex_stats", "mcp", "start"],
        env=isolated_environment(root),
        cwd=root,
    )
    log = root / "mcp-stderr.log"
    try:
        with log.open("w") as errors:
            async with (
                stdio_client(parameters, errlog=errors) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                catalog = await session.list_tools()
                names = {tool.name for tool in catalog.tools}
                require(
                    {"describe", "correct_pvalues", "skills_list", "skills_get"} <= names,
                    "required public MCP tools are missing",
                )

                async def call(name, arguments):
                    result = await session.call_tool(name, arguments)
                    return json.loads(result.content[0].text)

                empty = await call("describe", {"data": []})
                require(empty == {"success": False, "error": "No valid data points"},
                        "MCP empty input was not reported as a failure")
                valid = await call("describe", {"data": [1, 2, 3]})
                require((valid["success"], valid["n"], valid["mean"]) == (True, 3, 2.0),
                        "MCP descriptive result is incorrect")
                corrected = await call(
                    "correct_pvalues", {"pvalues": [0.01, 0.04, 0.03], "method": "fdr_bh"}
                )
                import numpy as np

                require(corrected["success"], "MCP correction failed")
                np.testing.assert_allclose(
                    corrected["corrected_pvalues"], [0.03, 0.04, 0.04], rtol=1e-12
                )
                listed = await call("skills_list", {})
                require(listed["success"] and listed["skills"], "MCP skills are absent")
                skill = await call("skills_get", {})
                expected = files("scitex_stats").joinpath(
                    "_skills/scitex-stats/SKILL.md"
                ).read_text()
                require(skill["success"] and skill["content"] == expected,
                        "MCP skill body differs from the installed owning package")
                return {"tools": sorted(names), "empty_input_failure": True,
                        "valid_describe": True, "fdr_bh": True, "exact_skill_body": True}
    finally:
        if log.exists():
            sys.stderr.write(log.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-version", required=True)
    args = parser.parse_args()
    installation = verify_installation(args.expected_version)
    with tempfile.TemporaryDirectory(prefix="scitex-stats-wheel-") as directory:
        root = Path(directory)
        cli = subprocess.run(
            [sys.executable, "-I", "-m", "scitex_stats", "--version"],
            cwd=root, env=isolated_environment(root), capture_output=True,
            text=True, check=True, timeout=30,
        )
        require(cli.stdout.strip() == f"scitex-stats, version {args.expected_version}",
                "CLI reports an unexpected package or version")
        python = verify_python(root)
        mcp = asyncio.run(asyncio.wait_for(verify_mcp(root), timeout=30))
    json.dump({"installation": installation, "python": python, "mcp": mcp,
               "cli_version": True}, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
