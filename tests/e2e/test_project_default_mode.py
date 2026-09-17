#!/usr/bin/env python3
"""End-to-end: project-default mode through a REAL browser.

Why an e2e layer for this: the unit and contract tests in this repo prove the
PIECES (routes, refusals, template markers, CSS hooks). What they cannot prove
is that the pieces compose into the journey the Private Beta spec describes —
pick an active project, see ITS authorized files, import one, run a test, and
have configuration / results / plot / provenance land back INSIDE that project.

Gated like every slow layer here: it needs `RUN_E2E=1` (so the default suite
stays fast and hermetic) and playwright's Chromium. It starts the real
standalone server in a subprocess over a temporary projects root, drives the
page once, and then checks the FILESYSTEM — the point of the feature is where
the bytes land, not what the DOM says.

The journey runs ONCE, in a function-scoped fixture, and the assertions are
split one-per-test (STX-TQ007): a fixture that both writes the project and
starts the server may not be session/module scoped (STX-TQ004), and a single
fat assertion would hide which part of the journey broke.
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


def _start_server(root: pathlib.Path) -> tuple[subprocess.Popen, str]:
    port = _free_port()
    env = dict(os.environ)
    env["SCITEX_STATS_PROJECTS_ROOT"] = str(root)
    proc = subprocess.Popen(  # noqa: S603
        [_console_script(), "gui", "serve", "--port", str(port), "--force"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )
    return proc, f"http://127.0.0.1:{port}"


def _drive_browser(base: str) -> dict:
    """Walk the journey once and return what the page showed."""
    from playwright.sync_api import sync_playwright

    observed = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.goto(f"{base}/?project=cohort", wait_until="load")
        page.wait_for_timeout(700)
        observed["listed"] = page.locator(".stats-project__import").all_inner_texts()
        observed["pickers"] = page.locator("[data-stx-project-picker]").count()
        page.locator(".stats-project__import").first.click()
        page.wait_for_timeout(600)
        page.locator("#statsCalculate").click()
        page.wait_for_timeout(2500)
        for button in ("#statsSaveResults", "#statsSaveProvenance", "#statsSaveConfig", "#statsSavePlot"):
            page.locator(button).click()
            page.wait_for_timeout(700)
        observed["status"] = page.locator("#statsSaveStatus").inner_text()
        browser.close()
    return observed


@pytest.fixture
def project_journey(tmp_path):
    """Run the whole journey against a real server and report what happened."""
    if not _e2e_enabled():
        pytest.skip("set RUN_E2E=1 to run the browser e2e layer")
    root = tmp_path / "projects"
    project = root / "cohort"
    project.mkdir(parents=True)
    (project / "measurements.csv").write_text(CSV, encoding="utf-8")

    proc, base = _start_server(root)
    try:
        if not _wait_for_http(f"{base}/"):
            pytest.fail(f"standalone server never answered on {base}")
        observed = _drive_browser(base)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            proc.kill()

    observed["project"] = project
    observed["written"] = sorted(str(p.relative_to(project)) for p in project.rglob("*") if p.is_file())
    return observed


def test_project_default_mode_lists_only_its_own_data(project_journey):
    # Arrange
    listed = project_journey["listed"]
    # Act
    names = list(listed)
    # Assert
    assert names == ["measurements.csv"]


def test_project_default_mode_renders_one_picker(project_journey):
    # Arrange
    count = project_journey["pickers"]
    # Act
    instances = int(count)
    # Assert
    assert instances == 1


def test_project_default_mode_writes_results_into_the_project(project_journey):
    # Arrange
    written = project_journey["written"]
    # Act
    has_results = "stats/results/result.json" in written
    # Assert
    assert has_results


def test_project_default_mode_writes_provenance_into_the_project(project_journey):
    # Arrange
    written = project_journey["written"]
    # Act
    has_provenance = "stats/provenance/provenance.json" in written
    # Assert
    assert has_provenance


def test_project_default_mode_writes_config_into_the_project(project_journey):
    # Arrange
    written = project_journey["written"]
    # Act
    has_config = "stats/config/config.json" in written
    # Assert
    assert has_config


def test_project_default_mode_writes_the_rendered_plot_into_the_project(project_journey):
    # Arrange
    plot = project_journey["project"] / "stats" / "plots" / "plot.png"
    # Act
    magic = plot.read_bytes()[:8] if plot.is_file() else b""
    # Assert
    assert magic == PNG_MAGIC


# EOF
