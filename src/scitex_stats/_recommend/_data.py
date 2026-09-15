#!/usr/bin/env python3
# File: src/scitex_stats/_recommend/_data.py
"""Normalise user data into cleaned groups (or a contingency table).

Nothing is inferred silently: when the caller leaves ``design`` or ``scale``
unset, the default taken is recorded as a note that every downstream output
carries.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from ._messages import note

DESIGNS = {
    "independent": "independent",
    "between": "independent",
    "unpaired": "independent",
    "paired": "paired",
    "within": "paired",
    "repeated": "paired",
    "repeated_measures": "paired",
    "related": "paired",
}
SCALES = ("continuous", "ordinal", "categorical")


@dataclass
class Prepared:
    names: List[str]
    groups: List[np.ndarray]
    raw_n: List[int]
    invalid: List[int]
    design: str
    design_specified: bool
    scale: str
    scale_specified: bool
    table: Optional[np.ndarray] = None
    pairs_dropped: int = 0
    paired_length_mismatch: bool = False
    notes: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def k(self) -> int:
        if self.table is not None:
            return int(self.table.shape[0])
        return len(self.groups)

    @property
    def n(self) -> List[int]:
        if self.table is not None:
            return [int(v) for v in self.table.sum(axis=1)]
        return [int(len(g)) for g in self.groups]

    def summary(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "n_groups": self.k,
            "group_names": list(self.names),
            "n_per_group": self.n,
            "design": self.design,
            "design_specified": self.design_specified,
            "scale": self.scale,
            "scale_specified": self.scale_specified,
        }
        if self.table is None:
            out["n_raw_per_group"] = list(self.raw_n)
            out["invalid_removed_per_group"] = list(self.invalid)
            if self.design == "paired":
                out["pairs_dropped"] = self.pairs_dropped
                out["paired_length_mismatch"] = self.paired_length_mismatch
        else:
            out["table_shape"] = list(self.table.shape)
        return out


def _to_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _split(data: Any, group_names: Optional[List[str]]):
    """Return (names, list-of-raw-sequences) from the accepted input forms."""
    try:
        import pandas as pd

        if isinstance(data, pd.DataFrame):
            return [str(c) for c in data.columns], [data[c].tolist() for c in data.columns]
    except ImportError:  # pragma: no cover - pandas is a hard dependency
        pass
    if isinstance(data, dict):
        return [str(k) for k in data], [list(v) for v in data.values()]
    if isinstance(data, np.ndarray):
        data = data.tolist() if data.ndim == 2 else [data.tolist()]
    if not isinstance(data, (list, tuple)):
        raise TypeError(
            "data must be a list of groups, a dict of name -> values, "
            "a pandas DataFrame (one column per group) or a 2-D array"
        )
    seqs = [list(g) if isinstance(g, (list, tuple, np.ndarray)) else [g] for g in data]
    names = list(group_names) if group_names else []
    names += [f"Group {i + 1}" for i in range(len(names), len(seqs))]
    return [str(n) for n in names[: len(seqs)]], seqs


def prepare(
    data: Any,
    design: Optional[str] = None,
    scale: Optional[str] = None,
    group_names: Optional[List[str]] = None,
) -> Prepared:
    """Clean the input and record every default that had to be taken."""
    notes: List[Dict[str, Any]] = []

    if design is None:
        design_key, design_specified = "independent", False
        notes.append(note("Design not specified: treated as independent groups. Set design='paired' for repeated measurements on the same subjects."))
    else:
        design_key = DESIGNS.get(str(design).lower())
        if design_key is None:
            raise ValueError(f"design must be one of {sorted(set(DESIGNS))}, got {design!r}")
        design_specified = True

    if scale is None:
        scale_key, scale_specified = "continuous", False
        notes.append(note("Measurement scale not specified: treated as continuous."))
    else:
        scale_key = str(scale).lower()
        if scale_key not in SCALES:
            raise ValueError(f"scale must be one of {list(SCALES)}, got {scale!r}")
        scale_specified = True

    names, seqs = _split(data, group_names)

    if scale_key == "categorical":
        cells = [[_to_float(v) for v in row] for row in seqs]
        width = max((len(r) for r in cells), default=0)
        if any(len(r) != width for r in cells) or any(
            v is None or v < 0 or v != int(v) for r in cells for v in r
        ):
            raise ValueError(
                "categorical data must be a contingency table: rows of equal length "
                "holding non-negative whole-number counts"
            )
        table = np.asarray(cells, dtype=float).reshape(len(cells), width)
        return Prepared(
            names=names, groups=[], raw_n=[], invalid=[], design=design_key,
            design_specified=design_specified, scale=scale_key,
            scale_specified=scale_specified, table=table, notes=notes,
        )

    parsed = [[_to_float(v) for v in s] for s in seqs]
    raw_n = [len(p) for p in parsed]
    invalid = [sum(v is None for v in p) for p in parsed]
    pairs_dropped = 0
    mismatch = False

    if design_key == "paired" and parsed:
        if len(set(raw_n)) > 1:
            mismatch = True
            groups = [np.asarray([v for v in p if v is not None]) for p in parsed]
        else:
            rows = list(zip(*parsed))
            keep = [r for r in rows if all(v is not None for v in r)]
            pairs_dropped = len(rows) - len(keep)
            groups = [np.asarray([r[j] for r in keep]) for j in range(len(parsed))]
            if pairs_dropped:
                notes.append(note("%s incomplete pair(s) removed (a value was missing or not a number).", pairs_dropped))
    else:
        groups = [np.asarray([v for v in p if v is not None]) for p in parsed]

    for name, bad in zip(names, invalid):
        if bad:
            notes.append(note("%s: %s missing or non-numeric value(s) removed.", name, bad))

    return Prepared(
        names=names, groups=groups, raw_n=raw_n, invalid=invalid, design=design_key,
        design_specified=design_specified, scale=scale_key, scale_specified=scale_specified,
        pairs_dropped=pairs_dropped, paired_length_mismatch=mismatch, notes=notes,
    )


# EOF
