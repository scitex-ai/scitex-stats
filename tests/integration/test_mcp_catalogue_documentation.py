"""Keep the documented MCP catalogue aligned with the registered server."""

from pathlib import Path
import re

from scitex_dev._ecosystem._mcp import get_tools_sync
from scitex_stats._server import mcp


def test_documented_mcp_catalogue_matches_registered_tools():
    # Arrange: inspect registration without invoking any statistical tool.
    path = Path(__file__).resolve().parents[2] / "docs" / "sphinx" / "mcp.rst"
    page = path.read_text()
    registered = set(get_tools_sync(mcp))
    # Act
    documented = re.findall(r"^   \* - ``([a-z_]+)``$", page, flags=re.MULTILINE)
    caption = re.search(r"(\d+) registered MCP tools", page)
    # Assert
    assert (set(documented), len(documented), caption.group(1) if caption else None) == (
        registered, len(registered), str(len(registered)),
    )
