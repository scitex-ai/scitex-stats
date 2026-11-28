"""Stats artifact transport; the fixed shared core owns archive/source checks.

Requires Python 3.11+, as supplied by the release SIF. This checker grants no
tag, runtime or publishing admission. No credentials are requested.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import tomllib
import urllib.request

REPOSITORY = "scitex-ai/scitex-stats"
CORE_COMMIT = "b1c508d348981a5377037c2f7803cca3eb5e6455"
PROOF = "release-proof.json"
SHA = re.compile(r"[0-9a-f]{40}")
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
CORE_FILES = {
    "release_core/__init__.py": "205c84c8b79b50d7abca4196165d169f07666039c118e79539df71a77e5df85f",
    "release_core/__main__.py": "43575b4e51c1c24948d03cad287dec672e55cb6120b930d8d27448a536a76857",
    "release_core/_metadata.py": "de9ad24888e6f2595d9d87837e4e7bee738011d02c5e847743ebecc7aed3afd8",
    "release_core/artifacts.py": "724f1d3db064de2a2935b8637c3d70445e19c99c922ff00fb16bb347474e8321",
    "release_core/files.py": "29a98f933f717bae5f44660f35729b44e37fa9224bf8ebf5a5e32b444fc5d3fb",
    "release_core/policy.py": "184ed54885c8516777110ec814abd2b9cafdd1bf37a5ba7d64636714091eae51",
    "release_core/registered.py": "5af2dc2ab67de1c094e2beee487b7c74681948743b23978014f5b30d99194c4a",
    "release_core/registry.py": "f79fe92d038d735704fca2169730c8e8f06e8270ca36344503f656b2aca7545d",
    "release_core/source.py": "3e157685f0141a6f4e73350c75d6659bece6e1afed48b9095ba629c8ca7f2839"
}

def regular(path, limit=1048576):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("Release input is not a bounded regular file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(fd)
        if len(raw) > limit or (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("Release input changed while reading")
        return raw
    finally:
        os.close(fd)

def verified_core(directory):
    expected = set(CORE_FILES)
    actual = {str(path.relative_to(directory)) for path in directory.rglob("*")}
    if actual != expected | {"release_core"}:
        raise ValueError("Central core closure has unknown or missing files")
    for name, digest in CORE_FILES.items():
        if hashlib.sha256(regular(directory / name)).hexdigest() != digest:
            raise ValueError("Central core file differs from its fixed commit")

def fetch_core(directory):
    (directory / "release_core").mkdir(mode=0o700)
    for name, digest in CORE_FILES.items():
        url = (
            f"https://raw.githubusercontent.com/scitex-ai/.github/{CORE_COMMIT}/{name}"
        )
        with urllib.request.urlopen(url, timeout=20) as response:
            if response.status != 200 or response.url != url:
                raise ValueError("Unexpected core source authority")
            raw = response.read(1048577)
        if len(raw) > 1048576 or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("Public central core source does not match fixed bytes")
        fd = os.open(
            directory / name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
    verified_core(directory)

def artifact_proof(directory, commit, version, source_root):
    if not SHA.fullmatch(commit) or not VERSION.fullmatch(version):
        raise ValueError("Malformed expected source or version")
    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source_root, text=True,
    ).strip()
    if actual != commit:
        raise ValueError("Checkout and expected source differ")
    project = tomllib.loads(subprocess.check_output(
        ["git", "show", commit + ":pyproject.toml"], cwd=source_root, text=True,
    ))["project"]
    if project["name"] != "scitex-stats" or project["version"] != version:
        raise ValueError("Expected version and Git project metadata differ")
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Unsafe artifact directory")
    files = sorted(path for path in directory.iterdir() if path.name != PROOF)
    if any(path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode) for path in files):
        raise ValueError("Artifact must be a regular file")
    wheels = [path for path in files if path.name.endswith(".whl")]
    sdists = [path for path in files if path.name.endswith(".tar.gz")]
    if (
        len(files) != 2 or len(wheels) != 1 or len(sdists) != 1
        or not wheels[0].name.startswith("scitex_stats-" + version + "-")
        or sdists[0].name != "scitex_stats-" + version + ".tar.gz"
    ):
        raise ValueError("Expected exactly the versioned Stats wheel and sdist")
    with tempfile.TemporaryDirectory(prefix="stats-release-core-") as temporary:
        core = Path(temporary)
        fetch_core(core)
        boot = 'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_module("release_core",run_name="__main__")'
        command = [
            sys.executable, "-I", "-S", "-B", "-c", boot, str(core),
            "verify-files", "--repository", REPOSITORY, "--commit", commit,
            "--source-root", str(source_root), "--wheel", str(wheels[0]),
            "--sdist", str(sdists[0]),
        ]
        environment = {
            "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(core),
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
        }
        result = subprocess.run(
            command, env=environment, check=True, capture_output=True,
            text=True, timeout=120,
        )
        identity = json.loads(result.stdout)
    return {
        "schema": "scitex-stats-artifacts/v1", "repository": REPOSITORY,
        "commit": commit, "version": version, "central_core_commit": CORE_COMMIT,
        "source_membership": identity,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["write-proof", "verify-proof"])
    parser.add_argument("--commit", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    args = parser.parse_args()
    proof = artifact_proof(
        args.dist, args.commit, args.version, Path.cwd().resolve(),
    )
    path = args.dist / PROOF
    if args.mode == "write-proof":
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(proof, stream, indent=2)
            stream.write("\n")
    elif json.loads(regular(path)) != proof:
        raise ValueError("Artifact proof or source bytes differ")
    json.dump(proof, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
