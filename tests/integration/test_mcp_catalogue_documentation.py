"""Compare standalone MCP documentation with the actual registered catalogue."""

from pathlib import Path
import re

import pytest

from scitex_dev._ecosystem._mcp import get_tools_sync
from scitex_stats._server import mcp

DOCUMENTS = ["docs/sphinx/mcp.rst",
             "src/scitex_stats/_skills/scitex-stats/13_mcp-tools.md",
             "src/scitex_stats/_skills/scitex-stats/SKILL.md"]


def documented_catalogue(path):
    page = path.read_text()
    if path.suffix == ".rst":
        names = re.findall(r"^   \* - ``([a-z_]+)``$", page, flags=re.MULTILINE)
    else:
        section = page
        if path.name == "SKILL.md":
            section = page.split("## MCP Tools", 1)[1].split("## Environment", 1)[0]
        names = [name for line in section.splitlines() if line.startswith("| `")
                 for name in re.findall(r"`([a-z_]+)`", line.split("|")[1])]
    caption = re.search(r"(\d+) registered MCP tools", page)
    return names, caption.group(1) if caption else None


@pytest.mark.parametrize("relative", DOCUMENTS)
def test_documented_mcp_catalogue_matches_registered_tools(relative):
    # Arrange
    path = Path(__file__).resolve().parents[2] / relative
    registered = set(get_tools_sync(mcp))
    # Act
    documented, count = documented_catalogue(path)
    # Assert
    assert (set(documented), len(documented), count) == (registered, len(registered), str(len(registered)))
