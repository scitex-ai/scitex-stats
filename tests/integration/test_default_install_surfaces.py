"""Smoke tests: each of the 4 public surfaces must work in a default install.

Default install = `pip install scitex-stats` (no extras). Per the
dep-cleanup audit (feat/pyproject-deps-cleanup), all 4 surfaces
— Python API, CLI, MCP server, Skills entry-points — are required to
import / start without any `[extra]` installed.

These tests guard against regressions where a future change pushes a
required dep back into an extra and silently breaks a surface for
fresh installs. They do **not** exercise feature depth — that's the
job of the per-test suites.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

import pytest


def _scitex_stats_exe():
    """Path to the `scitex-stats` console script co-installed with the
    interpreter running this suite (the build under test), falling back to
    whatever is on PATH. Avoids picking up a stale global/user install
    (e.g. a broken ~/.local/bin script on a shared self-hosted runner)."""
    import os

    local = os.path.join(os.path.dirname(sys.executable), "scitex-stats")
    if os.path.exists(local):
        return local
    # Fall back to PATH (was a self-recursion — infinite loop whenever the
    # console script is not co-located with the running interpreter).
    return shutil.which("scitex-stats")


# ----- Surface 1: Python API -------------------------------------------------


def test_python_api_top_level_import_version_str_scitex_stats():
    """`import scitex_stats` must succeed and expose __version__."""
    # Arrange
    import scitex_stats
    # Act
    # Assert
    assert isinstance(scitex_stats.__version__, str)

def test_python_api_top_level_import_version_scitex_stats():
    """`import scitex_stats` must succeed and expose __version__."""
    # Arrange
    import scitex_stats
    # Act
    # Assert
    assert scitex_stats.__version__  # non-empty


def test_python_api_describe_runs():
    """The headline `describe()` entry should run on a trivial input."""
    # Arrange
    from scitex_stats import describe
    # Act
    out = describe([1.0, 2.0, 3.0])
    # Assert
    assert out is not None


def test_python_api_run_test_ttest_ind_dict():
    """`run_test('ttest_ind', a, b)` should return a dict with a p-value."""
    # Arrange
    import numpy as np
    import scitex_stats as sst
    rng = np.random.default_rng(0)
    a = rng.normal(0.0, 1.0, 30)
    b = rng.normal(0.5, 1.0, 30)
    # Act
    result = sst.run_test("ttest_ind", a, b)
    # Assert
    assert isinstance(result, dict)

def test_python_api_run_test_ttest_ind_pvalue_value():
    """`run_test('ttest_ind', a, b)` should return a dict with a p-value."""
    # Arrange
    import numpy as np
    import scitex_stats as sst
    rng = np.random.default_rng(0)
    a = rng.normal(0.0, 1.0, 30)
    b = rng.normal(0.5, 1.0, 30)
    # Act
    result = sst.run_test("ttest_ind", a, b)
    # Assert
    assert "pvalue" in result or "p_value" in result


# ----- Surface 2: CLI --------------------------------------------------------


def test_cli_help_runs_exe():
    """`scitex-stats --help` exits 0."""
    # Arrange
    # Act
    exe = _scitex_stats_exe()
    # Assert
    assert exe, "scitex-stats CLI not on PATH"
    proc = subprocess.run([exe, "--help"], capture_output=True, timeout=30)

def test_cli_help_runs_returncode_proc():
    """`scitex-stats --help` exits 0."""
    # Arrange
    exe = _scitex_stats_exe()
    # Act
    proc = subprocess.run([exe, "--help"], capture_output=True, timeout=30)
    # Assert
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")

def test_cli_help_runs_stdout_proc():
    """`scitex-stats --help` exits 0."""
    # Arrange
    exe = _scitex_stats_exe()
    # Act
    proc = subprocess.run([exe, "--help"], capture_output=True, timeout=30)
    # Assert
    assert b"scitex-stats" in proc.stdout


def test_cli_version_runs_exe():
    """`scitex-stats --version` prints a version line."""
    # Arrange
    # Act
    exe = _scitex_stats_exe()
    # Assert
    assert exe
    proc = subprocess.run([exe, "--version"], capture_output=True, timeout=30)

def test_cli_version_runs_returncode_proc():
    """`scitex-stats --version` prints a version line."""
    # Arrange
    exe = _scitex_stats_exe()
    # Act
    proc = subprocess.run([exe, "--version"], capture_output=True, timeout=30)
    # Assert
    assert proc.returncode == 0

def test_cli_version_runs_lower_stdout_proc():
    """`scitex-stats --version` prints a version line."""
    # Arrange
    exe = _scitex_stats_exe()
    # Act
    proc = subprocess.run([exe, "--version"], capture_output=True, timeout=30)
    # Assert
    assert b"version" in proc.stdout.lower()


def test_cli_tests_list_runs_exe():
    """`scitex-stats tests list` returns the 23-test catalog."""
    # Arrange
    # Act
    exe = _scitex_stats_exe()
    # Assert
    assert exe
    proc = subprocess.run(
        [exe, "tests", "list"], capture_output=True, timeout=30
    )
    out = proc.stdout.decode()

def test_cli_tests_list_runs_returncode_proc():
    """`scitex-stats tests list` returns the 23-test catalog."""
    # Arrange
    exe = _scitex_stats_exe()
    # Act
    proc = subprocess.run(
        [exe, "tests", "list"], capture_output=True, timeout=30
    )
    # Assert
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    out = proc.stdout.decode()

def test_cli_tests_list_runs_name_ttest_ind_anova():
    """`scitex-stats tests list` returns the 23-test catalog."""
    # Arrange
    exe = _scitex_stats_exe()
    proc = subprocess.run(
        [exe, "tests", "list"], capture_output=True, timeout=30
    )
    # Act
    out = proc.stdout.decode()
    # Assert
    for name in ("ttest_ind", "anova", "pearson", "chi2", "shapiro"):
        assert name in out, f"missing {name} in tests list output"


# ----- Surface 3: MCP server -------------------------------------------------


def test_mcp_server_module_imports_case_1():
    """`from scitex_stats._server import mcp, run_server` must succeed.

    This is the canonical "MCP works out-of-the-box" check — proves the
    fastmcp + mcp deps are in the default install, not gated behind an
    extra.
    """
    # Arrange
    from scitex_stats._server import mcp, run_server  # noqa: F401
    # Act
    # Assert
    assert mcp is not None

def test_mcp_server_module_imports_callable_run_server():
    """`from scitex_stats._server import mcp, run_server` must succeed.

    This is the canonical "MCP works out-of-the-box" check — proves the
    fastmcp + mcp deps are in the default install, not gated behind an
    extra.
    """
    # Arrange
    from scitex_stats._server import mcp, run_server  # noqa: F401
    # Act
    # Assert
    assert callable(run_server)


def test_mcp_doctor_clean_exe():
    """`scitex-stats mcp doctor` reports all checks passing."""
    # Arrange
    # Act
    exe = _scitex_stats_exe()
    # Assert
    assert exe
    proc = subprocess.run(
        [exe, "mcp", "doctor"], capture_output=True, timeout=30
    )

def _doctor_env(exe):
    """`mcp doctor`'s PATH with the console script's directory prepended.

    The doctor's CLI check is about PATH MEMBERSHIP — `shutil.which("scitex-stats")`.
    This harness invokes the script by ABSOLUTE path (the copy co-installed with
    the interpreter under test), so the ambient PATH may legitimately not contain
    it and the check failed for a reason that has nothing to do with the build.
    Establishing the precondition is the harness's job, not the doctor's.
    """
    import os

    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([os.path.dirname(exe), env.get("PATH", "")])
    return env


def test_mcp_doctor_clean_returncode_proc():
    """`scitex-stats mcp doctor` reports all checks passing."""
    # Arrange
    exe = _scitex_stats_exe()
    # Act
    proc = subprocess.run(
        [exe, "mcp", "doctor"], capture_output=True, timeout=30, env=_doctor_env(exe)
    )
    # Assert
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")


def test_mcp_doctor_clean_stdout_proc():
    """`scitex-stats mcp doctor` reports all checks passing."""
    # Arrange
    exe = _scitex_stats_exe()
    # Act
    proc = subprocess.run(
        [exe, "mcp", "doctor"], capture_output=True, timeout=30, env=_doctor_env(exe)
    )
    # Assert
    assert b"All checks passed" in proc.stdout


# ----- Surface 4: Skills + scitex-dev entry-points ---------------------------


@pytest.mark.parametrize(
    "group, expected_name",
    [
        ("scitex_dev.docs", "scitex-stats"),
        ("scitex_dev.skills", "scitex-stats"),
        ("scitex_dev.linter.plugins", "stats"),
    ],
)
def test_scitex_dev_entry_points_registered(group, expected_name):
    """scitex-stats publishes 3 scitex-dev entry-points; all must resolve."""
    # Arrange
    from importlib.metadata import entry_points
    # Act
    eps = entry_points(group=group)
    names = {e.name for e in eps}
    # Assert
    assert expected_name in names, (
        f"entry-point group {group!r} missing {expected_name!r}; "
        f"have: {sorted(names)}"
    )


def test_linter_plugin_loads_dict():
    """The linter plugin must be importable + return a non-empty rule list."""
    # Arrange
    from scitex_stats._linter_plugin import get_plugin
    # Act
    plugin = get_plugin()
    # Assert
    assert isinstance(plugin, dict)

def test_linter_plugin_loads_get_rules():
    """The linter plugin must be importable + return a non-empty rule list."""
    # Arrange
    from scitex_stats._linter_plugin import get_plugin
    # Act
    plugin = get_plugin()
    # Assert
    assert plugin.get("rules"), "linter plugin returned no rules"


def test_skills_cli_list_runs_exe():
    """`scitex-stats skills list` enumerates bundled skill files."""
    # Arrange
    # Act
    exe = _scitex_stats_exe()
    # Assert
    assert exe
    proc = subprocess.run(
        [exe, "skills", "list"], capture_output=True, timeout=30
    )
    out = proc.stdout.decode()

def test_skills_cli_list_runs_returncode_proc():
    """`scitex-stats skills list` enumerates bundled skill files."""
    # Arrange
    exe = _scitex_stats_exe()
    # Act
    proc = subprocess.run(
        [exe, "skills", "list"], capture_output=True, timeout=30
    )
    # Assert
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    out = proc.stdout.decode()

def test_skills_cli_list_runs_skill():
    """`scitex-stats skills list` enumerates bundled skill files."""
    # Arrange
    exe = _scitex_stats_exe()
    proc = subprocess.run(
        [exe, "skills", "list"], capture_output=True, timeout=30
    )
    # Act
    out = proc.stdout.decode()
    # Assert
    assert "SKILL" in out


# ----- Bonus: import-time hygiene -------------------------------------------


def test_top_level_import_does_not_load_heavy_stack_returncode_proc():
    """Cold `import scitex_stats` must NOT eagerly load numpy/scipy/etc.

    PEP 562 lazy-loading in scitex_stats/__init__.py keeps CLI startup
    fast (see audit-cli rule §10). A regression here means a heavy
    submodule was re-exported eagerly.
    """
    # Arrange
    code = (
        "import sys\n"
        "before = set(sys.modules)\n"
        "import scitex_stats\n"
        "after = set(sys.modules) - before\n"
        "heavy = sorted(\n"
        "    m for m in after\n"
        "    if m.split('.')[0] in {\n"
        "        'numpy', 'scipy', 'pandas', 'statsmodels',\n"
        "        'matplotlib', 'figrecipe', 'pingouin', 'torch',\n"
        "    }\n"
        ")\n"
        "print(','.join(heavy))\n"
    )
    # Act
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, timeout=30
    )
    # Assert
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    loaded = proc.stdout.decode().strip()

def test_top_level_import_does_not_load_heavy_stack_loaded():
    """Cold `import scitex_stats` must NOT eagerly load numpy/scipy/etc.

    PEP 562 lazy-loading in scitex_stats/__init__.py keeps CLI startup
    fast (see audit-cli rule §10). A regression here means a heavy
    submodule was re-exported eagerly.
    """
    # Arrange
    code = (
        "import sys\n"
        "before = set(sys.modules)\n"
        "import scitex_stats\n"
        "after = set(sys.modules) - before\n"
        "heavy = sorted(\n"
        "    m for m in after\n"
        "    if m.split('.')[0] in {\n"
        "        'numpy', 'scipy', 'pandas', 'statsmodels',\n"
        "        'matplotlib', 'figrecipe', 'pingouin', 'torch',\n"
        "    }\n"
        ")\n"
        "print(','.join(heavy))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, timeout=30
    )
    # Act
    loaded = proc.stdout.decode().strip()
    # Assert
    assert loaded == "", (
        f"cold `import scitex_stats` eagerly loaded heavy deps: {loaded!r}"
    )
