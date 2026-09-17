#!/usr/bin/env python3
"""Tests for `scitex_stats.report` (PDF + HTML + Markdown files, `reporting/_pdf/_api.py`)."""

from __future__ import annotations

import pytest

import scitex_stats as ss
from scitex_stats.reporting._pdf import SECTIONS, pdf_renderer
from scitex_stats.reporting._pdf._fonts import cjk_font_available

THREE = {"対照群": [5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7], "Drug A": [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2],
         "Drug B": [5.9, 6.2, 6.0, 5.8, 6.4, 6.1]}
STAMP = "2026-01-01T00:00:00Z"

needs_pdf = pytest.mark.skipif(pdf_renderer() is None, reason="WeasyPrint not installed")
needs_cjk = pytest.mark.skipif(
    not cjk_font_available(),
    reason="no CJK font installed (Noto Sans CJK JP / IPAexGothic) - the Japanese rendering assertions need one",
)


def _pdf_text(path) -> str:
    fitz = pytest.importorskip("fitz")
    with fitz.open(path) as doc:
        return "".join(page.get_text() for page in doc)


@pytest.fixture(scope="module")
def pdf_report(tmp_path_factory):
    if pdf_renderer() is None:
        pytest.skip("WeasyPrint not installed")
    out = tmp_path_factory.mktemp("report") / "report.pdf"
    return ss.report(THREE, design="between", output=out, timestamp=STAMP)


@needs_pdf
def test_pdf_contains_every_section_heading(pdf_report):
    # Arrange
    text = _pdf_text(pdf_report["paths"]["pdf"])
    # Act
    missing = [title for _, title in SECTIONS if title not in text]
    # Assert
    assert missing == []


@needs_pdf
@needs_cjk
def test_pdf_embeds_a_japanese_font_for_japanese_group_names(pdf_report):
    # Arrange
    fitz = pytest.importorskip("fitz")
    # Act
    with fitz.open(pdf_report["paths"]["pdf"]) as doc:
        fonts = {f[3] for page in doc for f in page.get_fonts()}
    # Assert
    assert any(("JP" in name or "CJK" in name or "IPA" in name) for name in fonts)


@needs_pdf
@needs_cjk
def test_pdf_text_keeps_japanese_group_names(pdf_report):
    # Arrange
    path = pdf_report["paths"]["pdf"]
    # Act
    text = _pdf_text(path)
    # Assert
    assert "対照群" in text


@needs_pdf
def test_pdf_text_is_identical_apart_from_timestamp(tmp_path):
    # Arrange
    first = ss.report(THREE, output=tmp_path / "a.pdf", formats=["pdf"])
    second = ss.report(THREE, output=tmp_path / "b.pdf", formats=["pdf"])
    # Act
    a, b = (_pdf_text(r["paths"]["pdf"]).splitlines() for r in (first, second))
    # Assert
    assert [x for x, y in zip(a, b) if x != y and not x.startswith("20")] == []


def test_html_and_markdown_are_written_next_to_the_pdf_path(tmp_path):
    # Arrange
    out = tmp_path / "nested" / "report.pdf"
    # Act
    result = ss.report(THREE, output=out, formats=["html", "md"], timestamp=STAMP)
    # Assert
    assert sorted(result["paths"]) == ["figure", "html", "md"]


def test_markdown_references_the_written_figure(tmp_path):
    # Arrange
    ss.report(THREE, output=tmp_path / "r.pdf", formats=["md"], timestamp=STAMP)
    # Act
    md = (tmp_path / "r.md").read_text(encoding="utf-8")
    # Assert
    assert "](r-figure-1.svg)" in md


def test_output_none_returns_content_in_memory():
    # Arrange
    formats = ["html"]
    # Act
    result = ss.report(THREE, output=None, formats=formats, timestamp=STAMP)
    # Assert
    assert result["paths"] == {} and "<h1>Statistical report</h1>" in result["html"]


def test_unknown_format_is_rejected():
    # Arrange
    formats = ["docx"]
    # Act
    def call():
        return ss.report(THREE, output=None, formats=formats)

    # Assert
    with pytest.raises(ValueError, match="Unknown format"):
        call()


def test_csv_path_input_is_accepted(tmp_path):
    # Arrange
    csv = tmp_path / "data.csv"
    csv.write_text("a,b,c\n5.1,6.3,5.9\n4.9,6.8,6.2\n5.6,6.1,6.0\n5.8,7.0,5.8\n6.0,6.6,6.4\n5.4,6.9,\n", encoding="utf-8")
    # Act
    result = ss.report(csv, output=None, formats=["md"], timestamp=STAMP)
    # Assert
    assert result["summary"]["n"] == [6, 6, 5]


FONT_FILE_TYPES = ("/FontFile", "/FontFile2", "/FontFile3")


def _fonts_and_objects(path):
    """(embedded font programs, everything else), keyed by xref.

    The font programs are separated out because that is the one part of a
    WeasyPrint PDF that is not reproducible byte for byte - measured, not assumed:
    two renders of the same report differed at byte 25226 of 50938/50936, inside an
    object carrying `/Length1 ... /Filter /FlateDecode` (an embedded subset), with
    identical metadata and zero differing pages.
    """
    fitz = pytest.importorskip("fitz")
    fonts, others = {}, {}
    with fitz.open(path) as doc:
        for xref in range(1, doc.xref_length()):
            kind = doc.xref_get_key(xref, "Type")[1]
            raw = doc.xref_stream_raw(xref)
            if raw is None:
                continue
            (fonts if kind in FONT_FILE_TYPES else others)[xref] = (kind, raw)
    return fonts, others


@needs_pdf
def test_pdf_is_content_deterministic_for_the_same_input_and_timestamp(tmp_path):
    """Same input and timestamp -> the same report CONTENT.

    Asserted: identical page text, identical metadata, identical page count, and
    identical bytes for every object that is not an embedded font program. The
    creation date comes from the report timestamp (`dcterms.created`), so the
    artifact is dated by the analysis rather than by the render moment.

    Deliberately NOT asserted: byte-identical files. The embedded font subset is
    the one part WeasyPrint does not reproduce byte for byte (see the helper), and
    claiming otherwise would be a claim the bytes do not support.
    """
    # Arrange
    fitz = pytest.importorskip("fitz")
    first = ss.report(THREE, design="between", output=tmp_path / "a.pdf", formats=["pdf"], timestamp=STAMP)
    second = ss.report(THREE, design="between", output=tmp_path / "b.pdf", formats=["pdf"], timestamp=STAMP)
    # Act
    with fitz.open(first["paths"]["pdf"]) as a, fitz.open(second["paths"]["pdf"]) as b:
        texts = ["".join(page.get_text() for page in doc) for doc in (a, b)]
        metas = [dict(doc.metadata) for doc in (a, b)]
        counts = [doc.page_count for doc in (a, b)]
        created = str(a.metadata.get("creationDate", ""))
    objects = [_fonts_and_objects(r["paths"]["pdf"])[1] for r in (first, second)]
    fonts = [_fonts_and_objects(r["paths"]["pdf"])[0] for r in (first, second)]
    # Assert
    # Booleans, not the heavy objects: a dict of them prints in full when it fails,
    # so CI names WHICH fact broke instead of truncating a tuple of byte strings.
    facts = {
        "page_text": texts[0] == texts[1],
        "metadata": metas[0] == metas[1],
        "page_count": counts[0] == counts[1],
        "other_objects": objects[0] == objects[1],
        "font_count": len(fonts[0]) == len(fonts[1]),
        "dated_by_the_report": "20260101000000" in created,
    }
    assert facts == {key: True for key in facts} == (True, True, True, True, True, True)


# EOF
