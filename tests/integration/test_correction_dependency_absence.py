"""Exercise native correction dispatch with a real NumPy-only import path."""

import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
import scitex_stats as ss
from statsmodels.stats.multitest import multipletests

METHODS = ["bonferroni", "holm", "sidak", "fdr_bh", "fdr_by", "unknown_method"]

CHILD = """
import importlib.util
import json
from pathlib import Path
import sys

source, dependencies, request = sys.argv[1:]
sys.path[:0] = [source, dependencies]
assert importlib.util.find_spec("statsmodels") is None
import scitex_stats as ss
import numpy as np
result = ss.correct_pvalues(**json.loads(request))
print(json.dumps({"result": result, "numpy_file": str(Path(np.__file__).resolve()),
                  "statsmodels_absent": importlib.util.find_spec("statsmodels") is None,
                  "site_disabled": bool(sys.flags.no_site),
                  "isolated": bool(sys.flags.isolated)}))
"""


@pytest.fixture(scope="module")
def numpy_only_path(tmp_path_factory):
    """Expose the actual installed NumPy package without exposing site-packages."""
    target = tmp_path_factory.mktemp("numpy-only")
    package = Path(np.__file__).resolve().parent
    # NumPy wheels keep shared libraries beside the package on Linux/Windows.
    for actual in [package, package.parent / "numpy.libs"]:
        if actual.exists():
            try:
                (target / actual.name).symlink_to(actual, target_is_directory=True)
            except OSError as exc:
                pytest.skip(f"Dependency-isolation test requires directory symlinks: {exc}")
    return target


@pytest.mark.parametrize("method", METHODS)
def test_public_correction_dispatch_without_statsmodels(tmp_path, numpy_only_path, method):
    # Arrange: reference comes from a separate, normally installed backend.
    values = [0.0, 0.001, 0.04, 0.03, 0.20, 0.005, 1.0]
    reference_method = "fdr_bh" if method == "unknown_method" else method
    reject, expected, _, _ = multipletests(values, alpha=0.05, method=reference_method)
    source = str(Path(ss.__file__).resolve().parents[1])
    request = json.dumps(dict(pvalues=values, method=method, alpha=0.05))
    env = {"HOME": str(tmp_path), "SCITEX_DIR": str(tmp_path / "scitex"),
           "TMPDIR": str(tmp_path), "PGHOST": str(tmp_path / "absent-pg-socket"),
           "PGPASSFILE": str(tmp_path / "absent-pgpass")}
    # Act
    process = subprocess.run(
        [sys.executable, "-I", "-S", "-c", CHILD, source, str(numpy_only_path), request],
        cwd=tmp_path, env=env, capture_output=True, text=True, check=True, timeout=30,
    )
    observed = json.loads(process.stdout)
    result = observed["result"]
    # Assert
    assert (observed["statsmodels_absent"], observed["site_disabled"],
            observed["isolated"], observed["numpy_file"], result["method"],
            result["corrected_pvalues"], result["reject_null"], result["n_significant"],
            set(result) & {"success", "timestamp"}) == (
                True, True, True, str(Path(np.__file__).resolve()), method,
                pytest.approx(expected.tolist()), reject.tolist(), int(reject.sum()), set(),
            )
