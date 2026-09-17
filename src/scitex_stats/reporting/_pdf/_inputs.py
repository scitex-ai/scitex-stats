#!/usr/bin/env python3
# File: src/scitex_stats/reporting/_pdf/_inputs.py
"""Turn report input (CSV path, DataFrame, dict, list of lists) into named groups.

Nothing is dropped silently: every excluded cell is listed with its reason, and the
SHA-256 the report shows as "Input SHA-256" covers the cells AS GIVEN - non-numeric
text included - while "Analysis data SHA-256" covers the normalized float arrays the
tests actually ran on.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

DESIGNS = ("between", "within")
_DESIGN_ALIASES = {"between": "between", "independent": "between", "unpaired": "between",
                   "within": "within", "paired": "within", "repeated": "within", "repeated_measures": "within"}


@dataclass
class Prepared:
    names: List[str]
    groups: List[np.ndarray]
    design: str
    exclusions: List[Dict[str, Any]] = field(default_factory=list)
    n_raw: List[int] = field(default_factory=list)
    input_sha256: str = ""
    analysis_sha256: str = ""
    source: str = ""


def _design(design: Any) -> Dict[str, Any]:
    spec = dict(design) if isinstance(design, dict) else {"type": design or "between"}
    kind = _DESIGN_ALIASES.get(str(spec.get("type", "between")).lower())
    if kind is None:
        raise ValueError(f"design must be one of {sorted(_DESIGN_ALIASES)}, got {spec.get('type')!r}")
    spec["type"] = kind
    return spec


def _cell(value: Any):
    """(float or None, reason-if-excluded)."""
    if value is None:
        return None, "empty cell"
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None, "empty cell"
        try:
            value = float(text)
        except ValueError:
            return None, f"non-numeric value {text[:30]!r}"
    if isinstance(value, (bool, np.bool_)):
        return None, f"non-numeric value {value!r}"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, f"non-numeric value {str(value)[:30]!r}"
    if math.isnan(number):
        return None, "missing value (NaN)"
    if math.isinf(number):
        return None, "infinite value"
    return number, None


def _read_path(path: Path):
    import pandas as pd

    sep = "\t" if path.suffix.lower() in (".tsv", ".tab") else ","
    return pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)


def _columns(data: Any, spec: Dict[str, Any]) -> Dict[str, List[Any]]:
    """Ordered name -> raw cells, before any cleaning."""
    import pandas as pd

    if isinstance(data, (str, Path)):
        data = _read_path(Path(data))
    if isinstance(data, pd.DataFrame):
        group_col, value_col = spec.get("group_col"), spec.get("value_col")
        if group_col and value_col:
            out: Dict[str, List[Any]] = {}
            subject_col = spec.get("subject_col")
            if subject_col:
                # Align BY SUBJECT ID, because the ids are the only thing that says
                # which B value belongs to which A value. Sorting by subject and then
                # discarding the id appended each condition independently, so a
                # missing cell paired subject 2's A with subject 3's B - different
                # people compared against each other.
                per_condition: Dict[str, Dict[Any, Any]] = {}
                for subject, key, value in zip(data[subject_col], data[group_col].astype(str), data[value_col]):
                    per_condition.setdefault(key, {})[subject] = value
                shared = sorted(set.intersection(*(set(v) for v in per_condition.values()))) if per_condition else []
                spec["subject_exclusions"] = [
                    {"group": key, "subject": subject, "reason": "subject has no cell in every condition (listwise)"}
                    for key, values in per_condition.items()
                    for subject in sorted(set(values) - set(shared))
                ]
                return {key: [values[subject] for subject in shared] for key, values in per_condition.items()}
            frame = data
            for key, value in zip(frame[group_col].astype(str), frame[value_col]):
                out.setdefault(key, []).append(value)
            return out
        cols = spec.get("columns") or list(data.columns)
        return {str(c): data[c].tolist() for c in cols}
    if isinstance(data, dict):
        return {str(k): list(np.asarray(v, dtype=object).ravel()) for k, v in data.items()}
    if isinstance(data, np.ndarray) and data.ndim == 2:
        return {f"Group {i + 1}": data[:, i].tolist() for i in range(data.shape[1])}
    if isinstance(data, Sequence):
        return {f"Group {i + 1}": list(np.asarray(g, dtype=object).ravel()) for i, g in enumerate(data)}
    raise TypeError(f"Unsupported report data type: {type(data).__name__}")


def _trim_trailing_empty(cells: List[Any]) -> List[Any]:
    """Wide CSVs pad shorter columns with empty cells; those are not data."""
    end = len(cells)
    while end and (cells[end - 1] is None or (isinstance(cells[end - 1], str) and not cells[end - 1].strip())):
        end -= 1
    return cells[:end]


def prepare(data: Any, design: Any = "between", group_names: Optional[Sequence[str]] = None) -> Prepared:
    from scitex_stats import _provenance

    spec = _design(design)
    columns = _columns(data, spec)
    if group_names:
        if len(group_names) != len(columns):
            raise ValueError(f"Expected {len(columns)} group names, got {len(group_names)}")
        columns = dict(zip((str(n) for n in group_names), columns.values()))
    if len(columns) < 2:
        raise ValueError("A report compares at least 2 groups; got "
                         f"{len(columns)}. Pass one column per group, or group_col + value_col.")

    within = spec["type"] == "within"
    names = list(columns)
    cleaned: Dict[str, List[Optional[float]]] = {}
    exclusions: List[Dict[str, Any]] = []
    raw_arrays: Dict[str, np.ndarray] = {}
    n_raw = []
    for name in names:
        cells = columns[name] if within else _trim_trailing_empty(columns[name])
        values = []
        for row, cell in enumerate(cells, start=1):
            number, reason = _cell(cell)
            values.append(number)
            if reason and not within:
                exclusions.append({"group": name, "row": row, "value": "" if cell is None else str(cell), "reason": reason})
        cleaned[name] = values
        n_raw.append(len(cells))
        raw_arrays[name] = np.array([np.nan if v is None else v for v in values], dtype=float)

    if within:
        lengths = {len(v) for v in cleaned.values()}
        if len(lengths) != 1:
            raise ValueError(f"Within-subject design needs equal-length conditions, got {sorted(lengths)}")
        for row in range(lengths.pop()):
            bad = [n for n in names if cleaned[n][row] is None]
            for name in bad:
                cell = columns[name][row]
                _, reason = _cell(cell)
                exclusions.append({"group": name, "row": row + 1, "value": "" if cell is None else str(cell), "reason": reason})
            if bad:
                for name in names:
                    if name not in bad:
                        exclusions.append({"group": name, "row": row + 1, "value": str(cleaned[name][row]),
                                           "reason": f"row excluded listwise (missing in {', '.join(bad)})"})
        keep = [all(cleaned[n][r] is not None for n in names) for r in range(len(cleaned[names[0]]))]
        groups = [np.array([v for v, k in zip(cleaned[n], keep) if k], dtype=float) for n in names]
    else:
        groups = [np.array([v for v in cleaned[n] if v is not None], dtype=float) for n in names]

    for name, g in zip(names, groups):
        if g.size < 2:
            raise ValueError(f"Group {name!r} has {g.size} usable value(s); at least 2 are needed.")

    # TWO digests, because they answer different questions. `input_sha256` covers the
    # cells AS GIVEN (non-numeric text included), so inputs that differ only as "foo"
    # versus "bar" no longer collide; `analysis_sha256` covers the normalized float
    # arrays the analysis actually ran on. The report shows both.
    raw_records = {
        f"{i}:{name}": ["" if cell is None else str(cell) for cell in columns[name]]
        for i, name in enumerate(names)
    }
    digest = _provenance.hash_json(raw_records)
    analysis_digest = _provenance.combine_hashes(
        {f"{i}:{n}": _provenance.hash_array(raw_arrays[n]) for i, n in enumerate(names)}
    )
    for item in spec.get("subject_exclusions", []):
        if item["group"] in names:
            exclusions.append({"group": item["group"], "row": 0, "value": str(item["subject"]),
                               "reason": item["reason"]})
    exclusions.sort(key=lambda e: (names.index(e["group"]), e["row"]))
    source = str(data) if isinstance(data, (str, Path)) else type(data).__name__
    return Prepared(names=names, groups=groups, design=spec["type"], exclusions=exclusions, n_raw=n_raw,
                    input_sha256=digest, analysis_sha256=analysis_digest,
                    source=Path(source).name if isinstance(data, (str, Path)) else source)


__all__ = ["DESIGNS", "Prepared", "prepare"]

# EOF
