"""Enforces SciTeX skills quality checklist §1–§4.
Canonical: src/scitex/_skills/general/21_scitex-package-quality-checklist.md

The root is computed and then ASSERTED (mirrors scitex-scholar): a package
that ships ``_skills/`` must never satisfy this file by skipping. If the
layout moves, ``test_the_skill_corpus_is_not_empty`` goes RED and names the
directory it looked in, instead of the helper answering an empty corpus
with tests that skip (pytest exits 0 when every test skips).
"""

from pathlib import Path

import pytest

from scitex_dev._skills_quality_pytest import make_skill_quality_tests

# The repository root: the directory holding pyproject.toml, found by walking
# up from this file. Anchored on a file that only the root has, so moving
# this test to another depth cannot silently repoint it.
PACKAGE_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file()
)

SKILLS_DIR = PACKAGE_ROOT / "src" / "scitex_stats" / "_skills"


def test_the_skill_corpus_is_not_empty():
    """The gate must fail, not skip, when it cannot find what it grades."""
    # Arrange
    expected = True
    # Act
    found = SKILLS_DIR.is_dir() and any(SKILLS_DIR.iterdir())
    # Assert
    assert found is expected, (
        f"no skills found under {SKILLS_DIR} — scitex-stats ships a skill "
        "corpus, so an empty result means this test is looking in the wrong "
        "place, not that the package has no skills. Fix PACKAGE_ROOT rather "
        "than letting the quality checks skip."
    )


test_skills_quality = make_skill_quality_tests(package_root=PACKAGE_ROOT)
