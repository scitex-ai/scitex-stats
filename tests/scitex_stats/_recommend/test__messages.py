"""Reason messages: English text plus a translatable msgid; every one has a JA entry."""

from __future__ import annotations

from pathlib import Path

from scitex_stats._recommend import recommend_test, run_all_applicable
from scitex_stats._recommend import _messages as messages

_PO = Path(__file__).resolve().parents[3] / "src/scitex_stats/_django/locale/ja/LC_MESSAGES/djangojs.po"


def _msgids():
    from babel.messages.pofile import read_po

    with _PO.open("rb") as f:
        return {m.id for m in read_po(f) if m.id and m.string}


def _emitted(fixtures):
    ids = set()
    for data, kw in fixtures:
        rec = recommend_test(data, **kw)
        items = rec["decision_path"] + rec["notes"] + [a["why_item"] for a in rec["alternatives"]]
        items += [i for row in rec["applicability"] for i in row["reason_items"]]
        if rec["primary"]:
            items.append(rec["primary"]["reason_item"])
            ids.add(rec["primary"]["label"])
        ids |= {i["msg"] for i in items} | {a for i in items for a in i["args"] if isinstance(a, str) and a.islower()}
        ids |= {row["label"] for row in rec["applicability"]}
    return ids


def test_text_renders_args():
    # Arrange
    # Act
    item = messages.fail("Needs exactly 2 groups; there are %s", 3)
    # Assert
    assert item["text"] == "Needs exactly 2 groups; there are 3"


def test_fmt_p_is_apa():
    # Arrange
    # Act
    text = messages.fmt_p(0.0004)
    # Assert
    assert text == "< .001"


def test_every_emitted_message_has_a_japanese_translation(
    sample_ui, nonnormal_small, paired_normal, three_normal_unequal, small_expected_table, large_expected_table
):
    # Arrange
    fixtures = [
        (sample_ui, {}),
        (nonnormal_small, {"design": "independent"}),
        (paired_normal, {"design": "paired"}),
        (three_normal_unequal, {"design": "independent"}),
        (three_normal_unequal, {"design": "paired", "scale": "ordinal"}),
        (small_expected_table, {"design": "independent", "scale": "categorical"}),
        (large_expected_table, {"design": "independent", "scale": "categorical"}),
    ]
    emitted = _emitted(fixtures)
    emitted.add(run_all_applicable(sample_ui, design="independent")["warning_item"]["msg"])
    # Act
    missing = emitted - _msgids()
    # Assert
    assert not missing, sorted(missing)
