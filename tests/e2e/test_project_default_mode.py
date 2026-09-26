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


def _save_and_wait(page, button, expected):
    """Click a save control and wait for ITS OWN artifact to be reported.

    One retry, because a dropped click is a browser-test hazard rather than a
    product defect; a deterministic failure still fails on the second attempt,
    and then the message carries the status line so the cause is legible.
    """
    for attempt in (1, 2):
        page.locator(button).click()
        try:
            page.wait_for_function(
                "(want) => document.getElementById('statsSaveStatus').textContent.includes(want)",
                arg=expected,
                timeout=10_000,
            )
            return
        except Exception:
            if attempt == 2:
                status = page.locator("#statsSaveStatus").inner_text()
                raise AssertionError(f"{button} never reported {expected!r}; status line was {status!r}")


def _drive_browser(base: str) -> dict:
    """Walk the journey once and return what the page showed.

    Every step waits for the CONDITION it depends on, not for a fixed sleep: a
    fixed-duration journey was flaky under load (5 of 6 runs of the same code
    path passed, one fixture timed out mid-click), and a flaky e2e teaches
    nothing.
    """
    from playwright.sync_api import sync_playwright

    observed = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.goto(f"{base}/?project=cohort", wait_until="load")
        # the app's own readiness marker: interaction is wired, so a click cannot
        # land in the gap between DOM-ready and the listeners being attached
        page.wait_for_selector('[data-stats-app][data-stats-ready="1"]', timeout=30_000)

        # the active project's authorized file must be listed before we touch it
        page.wait_for_selector(".stats-project__import", timeout=30_000)
        observed["listed"] = page.locator(".stats-project__import").all_inner_texts()
        observed["pickers"] = page.locator("[data-stx-project-picker]").count()

        page.locator(".stats-project__import").first.click()
        page.wait_for_function(
            "() => Array.from(document.querySelectorAll('.stats-group__input'))"
            ".some(area => area.value.trim().length > 0)",
            timeout=30_000,
        )
        page.locator("#statsCalculate").click()
        page.wait_for_selector("#statsResult:not([hidden])", timeout=60_000)

        for button, expected in (
            ("#statsSaveResults", "stats/results/"),
            ("#statsSaveProvenance", "stats/provenance/"),
            ("#statsSaveConfig", "stats/config/"),
            ("#statsSavePlot", "stats/plots/"),
        ):
            _save_and_wait(page, button, expected)
        observed["status"] = page.locator("#statsSaveStatus").inner_text()

        # Quick analysis is the STATELESS alternative: the same page without a
        # project. Its state and its refusals are part of the acceptance, so the
        # journey ends by measuring them.
        page.goto(f"{base}/?quick=1", wait_until="load")
        page.wait_for_selector('[data-stats-app][data-stats-ready="1"]', timeout=30_000)
        observed["quick_panel_visible"] = page.locator("#statsProjectFiles").is_visible()
        observed["quick_manual_visible"] = page.locator("#statsManualData").is_visible()
        observed["quick_save_status"] = page.evaluate(
            """async () => {
            const token = document.querySelector('meta[name=csrf-token]').content;
            // the MODE lives in the URL, so the stateless probe must state it:
            // a bare POST would resolve the last-visited project instead.
            const response = await fetch('/api/project-save?quick=1', {
              method: 'POST',
              headers: {'Content-Type': 'application/json', 'X-CSRFToken': token},
              body: JSON.stringify({project: 'cohort', kind: 'config', name: 'config.json', payload: {}}),
            });
            return response.status;
          }"""
        )
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


def test_quick_analysis_hides_the_project_panel_and_shows_manual_input(project_journey):
    # Arrange
    state = (project_journey["quick_panel_visible"], project_journey["quick_manual_visible"])
    # Act
    measured = tuple(bool(value) for value in state)
    # Assert
    assert measured == (False, True)


def test_quick_analysis_refuses_persistence_server_side(project_journey):
    # Arrange
    reported = project_journey["quick_save_status"]
    # Act
    code = int(reported)
    # Assert
    assert code == 403


# EOF
