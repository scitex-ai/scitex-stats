#!/usr/bin/env python3
"""End-to-end: project-default mode through a REAL browser.

Why an e2e layer for this: the unit and contract tests above prove the pieces
(routes, refusals, template markers, CSS hooks). What they cannot prove is that
the pieces compose into the journey the Private Beta spec describes — pick an
active project, see ITS authorized files, import one, run a test, and have the
configuration/results/plot/provenance land back INSIDE that project.

Gated like every slow layer: it needs `RUN_E2E=1` (so the default suite stays
fast and hermetic) and playwright's Chromium. It starts the real standalone
server in a subprocess with a temporary projects root, drives the page, and then
checks the FILESYSTEM — the point of the feature is where the bytes land.
"""

from __future__ import annotations

import os
import pathlib
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

pytest.importorskip("playwright.sync_api", reason="e2e layer needs playwright + Chromium")

pytestmark = [pytest.mark.e2e]

CSV = "a,b\n5.1,6.3\n4.9,6.8\n5.6,6.1\n5.8,7.0\n6.0,6.6\n5.4,6.9\n5.2,6.4\n5.7,7.2\n"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _e2e_enabled() -> bool:
    return os.environ.get("RUN_E2E") == "1"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _console_script() -> str:
    """The console script co-installed with the interpreter running the suite."""
    candidate = pathlib.Path(sys.executable).parent / "scitex-stats"
    return str(candidate) if candidate.exists() else "scitex-stats"


def _wait_for_http(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:  # noqa: S310 (localhost)
                if response.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(0.5)
    return False


@pytest.fixture(scope="module")
def stats_server(tmp_path_factory):
    """A real standalone server over a temporary projects root."""
    root = tmp_path_factory.mktemp("projects")
    project = root / "cohort"
    project.mkdir()
    (project / "measurements.csv").write_text(CSV, encoding="utf-8")

    port = _free_port()
    env = dict(os.environ)
    env["SCITEX_STATS_PROJECTS_ROOT"] = str(root)
    proc = subprocess.Popen(  # noqa: S603
        [_console_script(), "gui", "serve", "--port", str(port), "--force"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        if not _wait_for_http(f"{base}/"):
            proc.terminate()
            pytest.fail(f"standalone server never answered on {base}")
        yield base, project
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            proc.kill()


def test_project_default_mode_round_trip(stats_server):
    """Import the project's CSV, run a test, and land every artifact back in it."""
    # Arrange
    from playwright.sync_api import sync_playwright

    base, project = stats_server
    if not _e2e_enabled():
        pytest.skip("set RUN_E2E=1 to run the browser e2e layer")

    artifacts = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.goto(f"{base}/?project=cohort", wait_until="load")
        page.wait_for_timeout(700)

        # the active project's authorized file is listed, and exactly one picker
        artifacts["listed"] = page.locator(".stats-project__import").all_inner_texts()
        artifacts["pickers"] = page.locator("[data-stx-project-picker]").count()

        # import it, run the test, then write everything back into the project
        page.locator(".stats-project__import").first.click()
        page.wait_for_timeout(600)
        page.locator("#statsCalculate").click()
        page.wait_for_timeout(2500)
        for button in ("#statsSaveResults", "#statsSaveProvenance", "#statsSaveConfig", "#statsSavePlot"):
            page.locator(button).click()
            page.wait_for_timeout(700)
        artifacts["status"] = page.locator("#statsSaveStatus").inner_text()
        browser.close()

    written = sorted(str(p.relative_to(project)) for p in project.rglob("*") if p.is_file())
    plot = project / "stats" / "plots" / "plot.png"
    # Assert: one journey, all of it measured on disk and in the DOM
    assert artifacts["listed"] == ["measurements.csv"] and artifacts["pickers"] == 1
    assert "stats/results/result.json" in written
    assert "stats/provenance/provenance.json" in written
    assert "stats/config/config.json" in written
    assert plot.is_file() and plot.read_bytes().startswith(PNG_MAGIC)


# EOF
