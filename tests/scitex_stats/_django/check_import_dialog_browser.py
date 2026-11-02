"""Exercise the actual standalone Django page in native Chromium, no live data."""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from wsgiref.simple_server import WSGIRequestHandler, make_server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chromium", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="stats-dialog-projects-") as project_root:
        project = Path(project_root) / "fixture"
        project.mkdir()
        (project / "measurements.tsv").write_text("x\ty\n1\t10\n2\t20\n")
        os.environ["SCITEX_STATS_PROJECTS_ROOT"] = project_root
        os.environ["SCITEX_STATS_APP_MODE"] = "standalone"
        os.environ["DJANGO_SETTINGS_MODULE"] = "scitex_stats._django.settings"
        from django.core.wsgi import get_wsgi_application
        from playwright.sync_api import sync_playwright

        class QuietHandler(WSGIRequestHandler):
            def log_message(self, *args):
                pass

        server = make_server(
            "127.0.0.1", 0, get_wsgi_application(), handler_class=QuietHandler
        )
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        receipts = []
        try:
            with sync_playwright() as tool:
                browser = tool.chromium.launch(
                    executable_path=args.chromium, headless=True, args=["--no-sandbox"]
                )
                for width, height in [(1440, 1000), (390, 844)]:
                    page = browser.new_page(viewport={"width": width, "height": height})
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    origin = f"http://127.0.0.1:{server.server_port}"
                    page.route(
                        "**/*",
                        lambda route: (
                            route.continue_()
                            if route.request.url.startswith(origin)
                            else route.abort()
                        ),
                    )
                    response = page.goto(origin + "/?quick=1")
                    assert response.status == 200
                    page.wait_for_selector('[data-stats-ready="1"]')
                    dialog = page.locator("#statsImportDialog")
                    trigger = page.locator("#statsOpenImport")
                    assert not dialog.is_visible()
                    trigger.focus()
                    trigger.click()
                    assert dialog.is_visible()
                    assert (
                        page.evaluate('document.activeElement.closest("dialog")?.id')
                        == "statsImportDialog"
                    ), page.evaluate(
                        '({tag:document.activeElement.tagName,id:document.activeElement.id,focused:document.hasFocus(),open:document.querySelector("#statsImportDialog").open,modal:document.querySelector("#statsImportDialog").matches(":modal")})'
                    )
                    # Native modality keeps page controls inert. Chromium may
                    # legitimately Tab into browser chrome (document.hasFocus false).
                    for _ in range(20):
                        page.keyboard.press("Tab")
                        assert page.evaluate(
                            '!document.hasFocus() || document.activeElement.closest("dialog")?.id === "statsImportDialog"'
                        )
                    page.locator("#statsSep").focus()
                    page.locator(".stats-group__input").first.evaluate(
                        "(node) => node.focus()"
                    )
                    assert (
                        page.evaluate('document.activeElement.closest("dialog")?.id')
                        == "statsImportDialog"
                    )
                    page.keyboard.press("Escape")
                    assert not dialog.is_visible()
                    assert trigger.evaluate("(node) => node === document.activeElement")
                    trigger.click()
                    with page.expect_file_chooser() as picker:
                        page.locator("#statsChooseFile").click()
                    picker.value.set_files(
                        {
                            "name": "synthetic.csv",
                            "mimeType": "text/csv",
                            "buffer": b"a;b;c\n1;10;100\n2;20;200\n",
                        }
                    )
                    page.wait_for_function(
                        'document.querySelectorAll("#statsColPickList input").length === 3'
                    )
                    page.locator("#statsColPickList input").nth(1).uncheck()
                    before = page.locator(".stats-group__input").evaluate_all(
                        "(nodes) => nodes.map(n => n.value)"
                    )
                    page.locator("#statsColPickCancel").click()
                    assert not dialog.is_visible()
                    assert (
                        page.locator(".stats-group__input").evaluate_all(
                            "(nodes) => nodes.map(n => n.value)"
                        )
                        == before
                    )
                    trigger.click()
                    assert (
                        not page.locator("#statsColPickList input").nth(1).is_checked()
                    )
                    box = dialog.bounding_box()
                    assert (
                        box["x"] >= 0
                        and box["x"] + box["width"] <= width + 1
                        and box["height"] <= height
                    )
                    theme_colors = []
                    for theme in ["light", "dark"]:
                        page.evaluate(
                            '(theme) => document.documentElement.setAttribute("data-theme", theme)',
                            theme,
                        )
                        theme_colors.append(
                            dialog.evaluate(
                                "(node) => getComputedStyle(node).backgroundColor"
                            )
                        )
                        page.screenshot(
                            path=str(output / f"import-dialog-{width}-{theme}.png")
                        )
                    assert theme_colors[0] != theme_colors[1]
                    page.locator("#statsColPickImport").click()
                    assert not dialog.is_visible()
                    assert page.locator(".stats-group__input").evaluate_all(
                        "(nodes) => nodes.map(n => n.value)"
                    ) == ["1 2", "100 200"]
                    assert (
                        "Semicolon" in page.locator("#statsImportSummary").inner_text()
                    )
                    assert trigger.evaluate("(node) => node === document.activeElement")
                    assert not errors, errors
                    page.goto(origin + "/?project=fixture")
                    page.wait_for_selector('[data-stats-ready="1"]')
                    trigger.click()
                    assert "Project data" in trigger.inner_text()
                    page.locator(
                        '.stats-project__import[data-file="measurements.tsv"]'
                    ).click()
                    page.wait_for_function(
                        'document.querySelector("#statsSepState").textContent.includes(".tsv default")'
                    )
                    assert page.locator("#statsSep").is_visible()
                    page.locator("#statsSep").select_option("\t")
                    assert "your choice" in page.locator("#statsSepState").inner_text()
                    page.locator("#statsImportClose").click()
                    assert not dialog.is_visible()
                    assert (
                        project / "measurements.tsv"
                    ).read_text() == "x\ty\n1\t10\n2\t20\n"
                    receipts.append(
                        {
                            "viewport": [width, height],
                            "native_modal_focus_containment": True,
                            "escape_returns_focus": True,
                            "cancel_preserves_groups_and_column_selection": True,
                            "file_chooser": True,
                            "project_file_and_explicit_separator": True,
                            "selected_columns_imported": True,
                            "dialog_fits_viewport": True,
                            "light_dark_backgrounds": theme_colors,
                            "page_errors": errors,
                        }
                    )
                    page.close()
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        (output / "browser-receipt.json").write_text(
            json.dumps(receipts, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
