"""Install one Stats wheel normally, then run the owning installed probe."""

from __future__ import annotations

import argparse
import email.parser
import runpy
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def select_wheel(directory, expected_version):
    """Refuse ambiguous inputs and wrong package/version before installation."""
    wheels = sorted(directory.glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("dist must contain exactly one wheel")
    wheel = wheels[0].resolve()
    with zipfile.ZipFile(wheel) as archive:
        names = [name for name in archive.namelist()
                 if name.endswith(".dist-info/METADATA")]
        if len(names) != 1:
            raise ValueError("wheel must contain exactly one distribution metadata file")
        message = email.parser.BytesParser().parsebytes(archive.read(names[0]))
    if message.get_all("Name") != ["scitex-stats"]:
        raise ValueError("wheel distribution must be scitex-stats")
    if message.get_all("Version") != [expected_version]:
        raise ValueError("wheel version differs from expected version")
    return wheel


def run(command, *, root, env, timeout, stdout):
    """Keep installation diagnostics off the probe's JSON stdout."""
    subprocess.run(command, cwd=root, env=env, timeout=timeout, check=True,
                   stdout=stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--expected-version", required=True)
    args = parser.parse_args()
    try:
        wheel = select_wheel(args.dist.resolve(), args.expected_version)
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    helper = Path(__file__).resolve().with_name("probe-statistics.py")
    if not helper.is_file():
        parser.error("owning probe-statistics.py is missing")
    uv = shutil.which("uv")
    if uv is None:
        parser.error("uv is required; no installer fallback is used")
    with tempfile.TemporaryDirectory(prefix="scitex-stats-wheel-runner-") as directory:
        root = Path(directory)
        home = root / "home"
        home.mkdir()
        # Reuse the owning probe's policy for installers, CLI and MCP children.
        policy = runpy.run_path(str(helper))["isolated_environment"]
        env = policy(root, home=home)
        fresh = root / "env"
        python = fresh / "bin/python"
        run([uv, "venv", "--python", sys.executable, str(fresh)],
            root=root, env=env, timeout=30, stdout=sys.stderr)
        run([uv, "pip", "install", "--python", str(python), str(wheel)],
            root=root, env=env, timeout=180, stdout=sys.stderr)
        run([uv, "pip", "check", "--python", str(python)],
            root=root, env=env, timeout=30, stdout=sys.stderr)
        run([str(python), "-I", str(helper),
             "--expected-version", args.expected_version],
            root=root, env=env, timeout=60, stdout=sys.stdout)


if __name__ == "__main__":
    main()
