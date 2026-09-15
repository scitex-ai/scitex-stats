#!/usr/bin/env python3
# File: src/scitex_stats/reporting/_pdf/_html.py
"""Report model -> self-contained HTML (print CSS for the PDF, no network fetches)."""

from __future__ import annotations

import base64
import html
from typing import Any, Dict, List

from scitex_stats._utils._apa._segments import Segment

_TAGS = {
    "sym": ('<i class="sym">', "</i>"),
    "greek": ('<span class="greek">', "</span>"),
    "sub": ("<sub>", "</sub>"),
    "sup": ("<sup>", "</sup>"),
    "strong": ("<strong>", "</strong>"),
    "code": ('<code>', "</code>"),
}

# Latin first (italic faces exist), CJK fallback for Japanese group names and titles.
FONT_STACK = ('"Liberation Sans", "Arial", "Helvetica Neue", "Noto Sans", "DejaVu Sans", '
              '"Noto Sans CJK JP", "Noto Sans JP", "IPAexGothic", "Hiragino Sans", sans-serif')

CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm;
  @bottom-left { content: "scitex-stats report"; font-size: 7.5pt; color: #6b7686; }
  @bottom-right { content: "Page " counter(page) " of " counter(pages); font-size: 7.5pt; color: #6b7686; } }
html { font-family: FONTS; font-size: 9.5pt; line-height: 1.45; color: #1d2430; }
body { margin: 0; padding: 0 16px; max-width: 60rem; margin-inline: auto; }
@media print { body { padding: 0; max-width: none; } }
h1 { font-size: 18pt; margin: 0 0 2pt; color: #1a2a40; }
.subtitle { color: #44546a; margin: 0 0 12pt; }
h2 { font-size: 12pt; color: #1a2a40; border-bottom: 1px solid #c9d1dc; padding-bottom: 2pt; margin: 16pt 0 6pt;
  break-after: avoid; }
h2 .num { color: #6b7686; font-weight: normal; margin-right: 4pt; }
p { margin: 4pt 0; }
i.sym { font-style: italic; }
.greek { font-style: normal; }
sub, sup { font-size: 70%; line-height: 0; }
code { font-family: "Liberation Mono", "DejaVu Sans Mono", monospace; font-size: 8pt; word-break: break-all; }
.table-wrap { margin: 6pt 0 10pt; }
@media screen { .table-wrap { overflow-x: auto; } }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt; break-inside: auto; }
caption { caption-side: top; text-align: left; font-style: italic; color: #44546a; padding-bottom: 3pt; }
th, td { text-align: left; vertical-align: top; padding: 3pt 5pt; }
thead th { border-top: 1.2px solid #1d2430; border-bottom: 0.8px solid #1d2430; font-weight: 600; }
tbody tr:last-child td { border-bottom: 1.2px solid #1d2430; }
tr { break-inside: avoid; }
.tnote { font-size: 8pt; color: #44546a; margin-top: 3pt; }
table.kv th { width: 30%; font-weight: 600; color: #44546a; border: 0; }
table.kv td, table.kv th { border-bottom: 0.5px solid #e2e7ee; }
p.lead { font-size: 10pt; }
p.apa { font-size: 10.5pt; background: #f3f6fa; border-left: 3px solid #1a2a40; padding: 5pt 8pt; }
p.note { color: #44546a; }
p.label { font-weight: 700; letter-spacing: .04em; color: #7a4b00; font-size: 8pt; }
p.caution { background: #fff6e5; border-left: 3px solid #d18b00; padding: 5pt 8pt; }
p.methods { background: #f7f7f2; border: 1px solid #deded2; padding: 7pt 9pt; break-inside: avoid; }
table.posthoc td:not(:first-child) { white-space: nowrap; }
table.kv tbody tr:last-child td { border-bottom: 0.5px solid #e2e7ee; }
figure { margin: 6pt 0; break-inside: avoid; }
figure img { max-width: 100%; height: auto; display: block; }
figcaption { font-size: 8.5pt; color: #44546a; margin-top: 3pt; }
ol.refs { padding-left: 0; list-style: none; }
ol.refs li { padding-left: 2em; text-indent: -2em; margin: 2pt 0; font-size: 8.5pt; overflow-wrap: anywhere; }
""".replace("FONTS", FONT_STACK)


def segments_html(segments: List[Segment]) -> str:
    out = []
    for s in segments:
        start, end = _TAGS.get(s["kind"], ("", ""))
        out.append(start + html.escape(str(s["text"])) + end)
    return "".join(out)


def _table(block: Dict[str, Any]) -> str:
    cls = f' class="{html.escape(block["class"])}"' if block.get("class") else ""
    head = "".join(f'<th scope="col">{segments_html(c)}</th>' for c in block["columns"])
    body = "".join("<tr>" + "".join(f"<td>{segments_html(c)}</td>" for c in row) + "</tr>" for row in block["rows"])
    caption = f"<caption>{html.escape(block['caption'])}</caption>" if block.get("caption") else ""
    note = f'<p class="tnote"><i>Note.</i> {segments_html(block["note"])}</p>' if block.get("note") else ""
    return f'<div class="table-wrap"><table{cls}>{caption}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>{note}</div>'


def _block(block: Dict[str, Any]) -> str:
    kind = block["type"]
    if kind == "paragraph":
        cls = f' class="{block["style"]}"' if block.get("style") else ""
        return f"<p{cls}>{segments_html(block['segments'])}</p>"
    if kind == "table":
        return _table(block)
    if kind == "kv":
        rows = "".join(f'<tr><th scope="row">{segments_html(a)}</th><td>{segments_html(v)}</td></tr>' for a, v in block["rows"])
        return f'<div class="table-wrap"><table class="kv"><tbody>{rows}</tbody></table></div>'
    if kind == "list":
        items = "".join(f"<li>{segments_html(i)}</li>" for i in block["items"])
        return f'<ol class="refs">{items}</ol>'
    if kind == "figure":
        data = base64.b64encode(block["svg"].encode("utf-8")).decode("ascii")
        return (f'<figure><img alt="Group comparison figure" src="data:image/svg+xml;base64,{data}">'
                f"<figcaption>{segments_html(block['caption'])}</figcaption></figure>")
    raise ValueError(f"unknown block type {kind!r}")


def render_html(model: Dict[str, Any]) -> str:
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(model['title'])}</title>",
        f'<meta name="generator" content="scitex-stats">',
        f"<style>{CSS}</style></head><body>",
        f"<h1>{html.escape(model['title'])}</h1>",
        f'<p class="subtitle">{html.escape(model["subtitle"])}</p>',
    ]
    for n, section in enumerate(model["sections"], start=1):
        parts.append(f'<section id="{section["id"]}"><h2><span class="num">{n}.</span> {html.escape(section["title"])}</h2>')
        parts.extend(_block(b) for b in section["blocks"])
        parts.append("</section>")
    parts.append("</body></html>")
    return "\n".join(parts)


__all__ = ["CSS", "FONT_STACK", "render_html", "segments_html"]

# EOF
