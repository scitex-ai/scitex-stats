# Installed-wheel qualification

The Stats-owned `.github/ci/probe-statistics.py` checks a fresh normal wheel
installation using its own interpreter with `-I`. Pass the source candidate's
version with `--expected-version`; a missing distribution, wrong version or
source import fails. Use the helper from the reviewed checkout or source archive.
Run from an owned working directory outside that checkout. Choose a new
environment path and set the candidate version from the reviewed
`pyproject.toml`.

This example uses Python 3.12 and explicitly selects the same fresh interpreter
for dependency checks and probe execution. Replace the absolute example paths
and version before running:

```bash
FRESH_ENV=/absolute/path/to/new-env
REVIEWED_WHEEL=/absolute/path/to/reviewed.whl
REVIEWED_SOURCE=/absolute/path/to/reviewed-source
CANDIDATE_VERSION="<version-from-reviewed-source>"

uv venv --python 3.12 "$FRESH_ENV"
uv pip install --python "$FRESH_ENV/bin/python" "$REVIEWED_WHEEL"
uv pip check --python "$FRESH_ENV/bin/python"
"$FRESH_ENV/bin/python" -I \
    "$REVIEWED_SOURCE/.github/ci/probe-statistics.py" \
    --expected-version "$CANDIDATE_VERSION"
```

The probe checks the public Python descriptive mean, an independent t-test
against a closed-form reference, paired CSV input without changing its bytes,
and Benjamini–Hochberg correction. It also checks the actual CLI version,
a real local MCP stdio catalog, valid and empty-input responses, p-value
correction, and on-demand skill content against the installed owning file.
Synthetic inputs and isolated subprocess state keep it independent of user
projects. The owned MCP subprocess disables FastMCP’s automatic PyPI update
check; this is not a network-isolation guarantee. MCP and CLI actions retain
30-second bounds.

Source controls live in `tests/integration/test_installed_wheel_probe.py`.
They exercise the public numerical/file checks and deliberately inject the
source tree to prove that it cannot pass as an installed-wheel result. Fresh-wheel
execution remains a separate required qualification.

This probe is a release prerequisite building block. It does not register a
release runtime, publish artifacts or modify the existing release workflow.
It does not replace the full retained-SIF suite with its original extras,
worker count, coverage and deadlines. Archive/source identity, installed-file
integrity, image/runtime qualification, publisher settings and public delivery
remain separate checks. Hosted GUI, authentication and physical Safari are
outside this probe's scope.
