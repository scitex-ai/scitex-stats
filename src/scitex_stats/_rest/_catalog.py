#!/usr/bin/env python3
# File: src/scitex_stats/_rest/_catalog.py

"""The catalogue of tests ``run_test`` accepts, described for a caller.

One entry per accepted name (aliases included, as
:func:`scitex_stats.available_tests` lists them): the function it runs, its
other names, a one-line description, and the request fields it reads — so an
agent can call ``POST /api/v1/stats/tests/{test_id}/run`` without reading the
source.
"""

from __future__ import annotations

from typing import Dict, List

from scitex_stats import _dispatch

#: How each test kind reads the request, in the order of ``_dispatch``.
KINDS = {
    "two_sample": {
        "sets": _dispatch._TWO_SAMPLE,
        "required": ["data", "data2"],
        "optional": ["alternative", "group_names"],
        "inputs": "data and data2: two independent samples (or, for a "
        "correlation, two paired variables of equal length)",
    },
    "paired": {
        "sets": _dispatch._PAIRED,
        "required": ["data", "data2"],
        "optional": ["alternative", "group_names"],
        "inputs": "data and data2: paired measurements of equal length",
    },
    "one_sample": {
        "sets": _dispatch._ONE_SAMPLE,
        "required": ["data"],
        "optional": ["group_names"],
        "inputs": "data: one sample",
    },
    "one_sample_mean": {
        "sets": _dispatch._ONE_SAMPLE_MEAN,
        "required": ["data"],
        "optional": ["popmean", "group_names"],
        "inputs": "data: one sample; popmean: the hypothesised mean (default 0)",
    },
    "groups": {
        "sets": _dispatch._GROUP,
        "required": ["groups"],
        "optional": ["group_names"],
        "inputs": "groups: two or more independent samples",
    },
    "repeated_groups": {
        "sets": _dispatch._STACKED_GROUP,
        "required": ["groups"],
        "optional": ["group_names"],
        "inputs": "groups: three or more conditions measured on the same "
        "subjects (equal lengths, one value per subject)",
    },
    "contingency": {
        "sets": _dispatch._CONTINGENCY,
        "required": ["groups"],
        "optional": [],
        "inputs": "groups: the contingency table, one array of counts per row "
        "(fisher: a 2 x 2 table); or data and data2 as its two rows",
    },
}

_NOTES = {
    "ttest_welch": "Welch's t-test (unequal variances, equal_var=False).",
    "ttest": "Student's t-test for independent samples (alias of ttest_ind).",
}


def kind_of(test_id: str) -> str:
    for kind, spec in KINDS.items():
        if test_id in spec["sets"]:
            return kind
    raise LookupError(test_id)  # pragma: no cover - every alias has a kind


def _summary(function: str) -> str:
    import scitex_stats.tests as tests

    doc = (getattr(tests, function).__doc__ or "").strip()
    return doc.splitlines()[0].strip() if doc else ""


def describe_test(test_id: str) -> Dict:
    """The catalogue entry of one accepted test name."""
    function = _dispatch._ALIASES[test_id]
    kind = kind_of(test_id)
    spec = KINDS[kind]
    aliases = sorted(
        name
        for name, f in _dispatch._ALIASES.items()
        if f == function and name != test_id
    )
    return {
        "id": test_id,
        "function": function,
        "aliases": aliases,
        "kind": kind,
        "description": _NOTES.get(test_id) or _summary(function),
        "inputs": spec["inputs"],
        "required": list(spec["required"]),
        "optional": list(spec["optional"]),
    }


def catalogue() -> List[Dict]:
    return [describe_test(name) for name in _dispatch.available_tests()]


# EOF
