"""``import scitex_stats`` must not copy ``.env`` into os.environ (scitex-config#47).

A fresh interpreter runs with a real temporary HOME/cwd holding a real
``.env``; nothing is mocked.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

_PROBE = textwrap.dedent(
    """
    import os
    before = dict(os.environ)
    import scitex_stats
    added = sorted(set(os.environ) - set(before))
    print(" ".join(added) or "<none>")
    """
)


def test_import_adds_no_environ_key_from_dotenv(tmp_path: Path) -> None:
    # Arrange
    (tmp_path / ".env").write_text(
        "FOREIGN_SERVICE_API_KEY=fake-value-not-a-secret\nSCITEX_STATS_PROBE=1\n"
    )
    import scitex_stats as _pkg

    src = str(Path(_pkg.__file__).resolve().parent.parent)
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("FOREIGN_SERVICE_API_KEY", "SCITEX_STATS_PROBE")
    }
    env["HOME"] = str(tmp_path)
    env["PYTHONPATH"] = os.pathsep.join([src, *(p for p in sys.path if p)])
    # Act
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    # Assert
    assert result.stdout.strip().splitlines()[-1:] == ["<none>"], result.stderr
