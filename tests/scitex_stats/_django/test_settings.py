"""The standalone settings module must render the shell its template extends.

The view tests configure Django themselves, with their OWN INSTALLED_APPS, so
they cannot see a settings module that omits the app which ships
`scitex_app/app_shell.html` — the base template stats.html extends. Leaving it
out made every page of the real standalone server return 500 while the suite
stayed green. This runs the REAL settings module in a child interpreter.
"""

from __future__ import annotations

import os
import subprocess
import sys

RENDER_INDEX_IN_CHILD = """
import django
from django.test import Client

django.setup()
client = Client()
print(client.get("/").status_code)
"""


def _render_index_with_standalone_settings():
    env = dict(os.environ)
    env["DJANGO_SETTINGS_MODULE"] = "scitex_stats._django.settings"
    return subprocess.run(
        [sys.executable, "-c", RENDER_INDEX_IN_CHILD],
        capture_output=True,
        text=True,
        env=env,
    )


def test_standalone_settings_render_the_index():
    # Arrange
    # Act
    proc = _render_index_with_standalone_settings()
    # Assert
    assert (proc.returncode, proc.stdout.strip()) == (0, "200"), proc.stderr[-2000:]
