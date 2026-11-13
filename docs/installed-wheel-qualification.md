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

The retained SIF can run the normal fresh-install sequence with the leaf-owned
wrapper from the reviewed checkout:

```bash
bash .github/ci/exec-in-sif.sh probe-wheel-in-sif.sh 3.12 \
    --dist /absolute/path/to/reviewed-dist \
    --expected-version "$CANDIDATE_VERSION"
```

The dist directory must contain exactly one wheel whose package and version
match the requested candidate. The wrapper creates a temporary environment,
installs the wheel with its normal dependencies, runs `uv pip check`, and invokes
the unchanged owning probe with `-I` outside the checkout. It uses private HOME,
config and cache directories and excludes inherited credentials, Python paths
and coverage hooks. Normal dependency installation needs package-index access;
this is not a network sandbox. Creation, installation, dependency checking and
probe execution have 30-, 180-, 30- and 60-second limits respectively. Failure
stops the sequence; it never falls back to another installer. Temporary files
are removed afterwards, so retain stdout/stderr in the calling job.

The caller still owns image/runtime and source/archive identity verification.
The wrapper does not register a release profile or authorize publication.
Runner refusal controls live in `tests/integration/test_wheel_probe_runner.py`;
real fresh-wheel execution remains a separate required qualification.

This probe is a release prerequisite building block. It does not register a
release runtime, publish artifacts or modify the existing release workflow.
It does not replace the full retained-SIF suite with its original extras,
worker count, coverage and deadlines. Archive/source identity, installed-file
integrity, image/runtime qualification, publisher settings and public delivery
remain separate checks. Hosted GUI, authentication and physical Safari are
outside this probe's scope.

## Source and archive identity

The release-image adapter `.github/ci/release-identity.py` uses the shared
artifact verifier from a fixed commit. It fetches the bounded public core files
and verifies their SHA-256 hashes before executing them with isolated Python.
This step requires POSIX, Python3.11 or newer, Git, and access to the public
source host. It does not request credentials.

From the reviewed checkout, select the exact commit, the version declared in
its `pyproject.toml` (without a leading `v`), and an owned archive directory:

```bash
REVIEWED_COMMIT="$(git rev-parse HEAD)"
REVIEWED_DIST=/absolute/path/to/reviewed-dist

python3.12 -I .github/ci/release-identity.py write-proof \
    --commit "$REVIEWED_COMMIT" --version "$CANDIDATE_VERSION" \
    --dist "$REVIEWED_DIST"
python3.12 -I .github/ci/release-identity.py verify-proof \
    --commit "$REVIEWED_COMMIT" --version "$CANDIDATE_VERSION" \
    --dist "$REVIEWED_DIST"
```

The directory must contain exactly the versioned Stats wheel and source
archive. `write-proof` creates `release-proof.json` exclusively; it refuses an
existing proof. `verify-proof` recomputes the source/archive checks and compares
the saved proof. Wrong commits or versions, changed or missing package payloads,
extra archives, symlinked inputs and changed verifier bytes fail.

The shared core checks archive membership and source bytes against Git,
including the required skills, built documentation and application files.
The proof is verification evidence; it grants no runtime, tag or publishing
admission. The build application now requires three arguments: the baked Python
minor, the independently resolved expected commit, and the expected version.
It checks source identity before dependency installation or deleting `dist/`,
then builds normally, writes the archive proof, runs the fresh installed-wheel
probe, and verifies the archive proof again. A failure stops the application.
`verify-source` is also available as a local, archive-free identity check; it
does not fetch the shared core or authorize a build.

This helper integration does not enable the shared Stats build profile. Its
registration still admits tests only. The legacy release caller does not supply
the required independent identity arguments and must not be dispatched as a
shortcut. Shared source-closure updates, actual complete SIF build qualification
at an unused version, protected promotion and publisher admission remain release
prerequisites. Every existing private 1.0.0 archive remains ineligible for upload.
Archive identity and the fresh installed-wheel behavioral probe are separate
requirements, and neither replaces the full retained-image suite.

## Retained runtime and image bytes

The outer `.github/ci/exec-in-sif.sh` requires the configured runtime and image
paths plus their reviewed SHA-256 digests:

- `SCITEX_CI_APPTAINER` and `SCITEX_CI_APPTAINER_SHA256`
- `SCITEX_CI_SIF` and `SCITEX_CI_SIF_SHA256`

Paths must be absolute or start with `~/`. A missing runtime, missing or malformed
digest, changed runtime/image bytes, or an invalid inner script path stops before
execution. The wrapper uses the configured executable; another executable on
PATH cannot replace a missing configured runtime. Quoted paths and arguments
retain spaces.

Use expected digests from a reviewed runtime/image registration. Computing a
checksum of an unknown live file does not qualify it. These byte checks grant
no runtime or publishing admission and do not replace private state/scratch,
capacity and source/archive verification. The legacy release caller reads the
digests from Actions variables; missing configuration remains a release hold.
No release dispatch or variable change is performed by this source change.

## Private state policy building block

`.github/ci/release-context.sh` provides `stats_release_context SCRATCH VENV`
and `stats_release_run COMMAND ...` for a dedicated strict Bash release driver.
The caller supplies an existing absolute, writable, mode-0700 scratch root owned
by its user, plus an absolute interpreter environment with `bin/python`. The
helper refuses a symlinked or nonprivate root and exclusively creates
`SCRATCH/stats-state`; it never reuses or overwrites an existing state directory.

The child receives private HOME, SciTeX, XDG, installer and Matplotlib paths,
headless Matplotlib, explicit tool paths and database-refusal settings through
`env -i`. Ambient provider credentials, Python paths, coverage startup hooks and
virtual environments are not inherited. The calling shell's HOME is unchanged.
Explicit arguments to `stats_release_run` remain the trusted driver's
responsibility. Normal installers can still use network access; this is not a
network sandbox.

The PostgreSQL host is a nonexistent Unix socket directory beneath private
state, with `port=1` and `connect_timeout=1` settings. URL encoding preserves
spaces and reserved characters in its path. Controls in
`tests/integration/test_release_private_state.py` exercise the actual child
environment, source-store DSN resolution and libpq connection refusal, plus
unsafe-root and occupied-state refusals. They do not connect to a live store.

The outer wrapper requires `SCITEX_CI_OWNED_CONTEXT` to name an absolute,
regular, non-symlink file staged by the caller from the qualified
[Dev lifecycle resource](https://github.com/scitex-ai/scitex-dev/blob/41b907f7f32069fcf42855bf5a7722875e29cbec/src/scitex_dev/ci/owned_context.sh).
It verifies the fixed SHA-256
`a795678455d409e076a1c93a4a810b50c89499fcb83ae4c90a8d31a19e90e5d1`
before sourcing it. The frozen upstream snapshot in the test namespace keeps
unit controls offline; production callers supply the resource explicitly.

The shared lifecycle creates a mode-0700 job root under `RUNNER_TEMP` (or
`/tmp`), with birth-token process-group cancellation and bounded cleanup.
The runtime receives an explicit environment, a private home, private `/tmp`
and `/var/tmp` bindings, and the reviewed checkout binding. Bind paths reject
commas, colons and newlines. Ambient provider/OIDC credentials and
`APPTAINERENV_*` overrides are not forwarded.

`run-owned-in-sif.sh` checks the bound root's device, inode, owner and mode,
then applies the private state policy before launching the retained test,
build or fresh-wheel driver. Those inner scripts also require the owned-root
identity, so direct execution against a host's ordinary `/tmp` fails before
installation or deletion. The owning probe supplies one environment factory
for the installer and its CLI/MCP children. Each phase receives private state and database-refusal
settings when constructing its child environment.
Build installation uses uv and stops on failure, with no pip fallback.

The supported routes are non-publishing applications. The legacy manual OIDC
publisher is refused. Automatic shared-caller staging, full current native-suite
and cancellation/cleanup qualification, source/runtime registration, and the
qualified shared publisher remain prerequisites for release admission.

The probe environment controls in `tests/integration/test_installed_wheel_probe.py`
exercise both HOME modes with real store resolution and a missing owned Unix
socket, including rejection of ambient environment state. Connection parameters
are checked against the fixture's exact private socket before any libpq call.
The numerical, CLI, MCP result and skill-content assertions are separate from
this environment policy and retain their existing bounds.
