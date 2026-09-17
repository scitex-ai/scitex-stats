#!/usr/bin/env python3
# File: src/scitex_stats/reporting/_pdf/_fonts.py
"""Font availability for the report renderers.

WeasyPrint (PDF) and matplotlib (figure) draw text with whatever the system
installed. Latin-only images render a Japanese group name as missing glyphs and
say nothing about it, so the report asks this module whether a CJK-capable face
exists and warns in its own output when one does not.
"""

from __future__ import annotations

# Families the figure spec already prefers, plus the common Linux packages.
CJK_FAMILIES = (
    "Noto Sans CJK JP",
    "Noto Serif CJK JP",
    "Noto Sans JP",
    "Source Han Sans JP",
    "IPAexGothic",
    "IPAGothic",
    "TakaoGothic",
    "Hiragino Sans",
)


def cjk_font_available() -> bool:
    """True when a CJK-capable family is installed for the renderers to use."""
    try:
        from matplotlib import font_manager
    except Exception:  # noqa: BLE001 - no matplotlib means no figure, and no answer either
        return False
    installed = {face.name for face in font_manager.fontManager.ttflist}
    return any(family in installed for family in CJK_FAMILIES)


def has_cjk(text: str) -> bool:
    """True when ``text`` contains a character only a CJK font can draw."""
    return any(
        "\u3040" <= char <= "\u30ff"  # hiragana, katakana
        or "\u3400" <= char <= "\u4dbf"  # CJK extension A
        or "\u4e00" <= char <= "\u9fff"  # CJK unified ideographs
        or "\uf900" <= char <= "\ufaff"  # compatibility ideographs
        for char in text
    )


__all__ = ["CJK_FAMILIES", "cjk_font_available", "has_cjk"]

# EOF
