#!/usr/bin/env python3
# File: src/scitex_stats/reporting/_pdf/_markdown.py
"""Report model -> Markdown (pandoc turns it into DOCX with italics intact)."""

from __future__ import annotations

from typing import Any, Dict, List

from scitex_stats._utils._apa._segments import Segment, plain


def segments_md(segments: List[Segment]) -> str:
    out = []
    for s in segments:
        text, kind = str(s["text"]), s["kind"]
        if kind == "sym":
            out.append(f"*{text}*")
        elif kind == "strong":
            out.append(f"**{text}**")
        elif kind == "code":
            out.append(f"`{text}`")
        elif kind in ("sub", "sup"):
            out.append(plain([s]))
        else:
            out.append(text.replace("|", "\\|").replace("*", "\\*"))
    return "".join(out)


def _table(columns, rows) -> List[str]:
    lines = ["| " + " | ".join(segments_md(c) for c in columns) + " |",
             "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(segments_md(c) for c in row) + " |" for row in rows]
    return lines


def render_markdown(model: Dict[str, Any]) -> str:
    lines = [f"# {model['title']}", "", model["subtitle"], ""]
    for n, section in enumerate(model["sections"], start=1):
        lines += [f"## {n}. {section['title']}", ""]
        for b in section["blocks"]:
            if b["type"] == "paragraph":
                text = segments_md(b["segments"])
                lines += [f"> {text}" if b.get("style") in ("caution", "apa") else text, ""]
            elif b["type"] == "table":
                if b.get("caption"):
                    lines += [f"*{b['caption']}*", ""]
                lines += _table(b["columns"], b["rows"]) + [""]
                if b.get("note"):
                    lines += [f"*Note.* {segments_md(b['note'])}", ""]
            elif b["type"] == "kv":
                lines += _table([[{"text": "Field", "kind": "text"}], [{"text": "Value", "kind": "text"}]], b["rows"]) + [""]
            elif b["type"] == "list":
                lines += [f"{i}. {segments_md(item)}" for i, item in enumerate(b["items"], start=1)] + [""]
            elif b["type"] == "figure":
                lines += [f"![Figure]({b.get('file', 'figure-1.svg')})", "", segments_md(b["caption"]), ""]
    return "\n".join(lines).rstrip() + "\n"


__all__ = ["render_markdown", "segments_md"]

# EOF
