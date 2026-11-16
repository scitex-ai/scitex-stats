"""Comparison tools belong to the second workspace pane."""

import pytest

from .test_views import client as client


@pytest.mark.parametrize(
    "control",
    [
        "statsCorrMethod",
        "statsCorrP",
        "statsCorrect",
        "statsCorrOut",
        "statsPhMethod",
        "statsPosthoc",
        "statsPhOut",
    ],
)
def test_comparison_tools_belong_to_test_selection(client, control):
    # Arrange
    from html.parser import HTMLParser

    class PaneParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.sections = []
            self.owners = {}

        def handle_starttag(self, tag, attrs):
            attributes = dict(attrs)
            if tag == "section":
                self.sections.append(attributes.get("data-stx-pane"))
            if attributes.get("id") == control:
                self.owners[control] = [s for s in self.sections if s]

        def handle_endtag(self, tag):
            if tag == "section":
                self.sections.pop()

    parser = PaneParser()
    # Act
    parser.feed(client.get("/").content.decode())
    # Assert
    assert "test" in parser.owners[control]
