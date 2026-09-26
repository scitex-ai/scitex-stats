#!/usr/bin/env python3
# File: src/scitex_stats/_provenance.py

"""Result provenance ("receipt") for scitex-stats.

Every ``run_test`` / ``full_report`` / MCP ``run_test`` result carries
``result["provenance"]`` recording exactly what was computed: the test and
all parameters, a SHA-256 per input (with n), the seed, library versions and
a UTC timestamp, plus ``result_sha256`` over the result itself. The receipt is
plain JSON, so saving the result with ``scitex_io.save`` stores it inside the
file that scitex-clew already hashes; :func:`scitex_stats.verify` recomputes
from it.

Hash conventions (``schema = scitex-stats/provenance@1``)
---------------------------------------------------------
- Arrays: values as little-endian float64 in C order, ``-0.0`` folded to
  ``0.0``, every NaN folded to one bit pattern; digest input is
  ``b"scitex-stats:ndarray:v1:<f8:" + shape + b"\\0" + bytes``.
- Results and receipts: JSON with sorted keys, no whitespace, floats in
  Python's shortest round-trip repr, NaN/inf spelled ``{"__float__": ...}``.
- Combined input hash: scitex-clew's ``combine_hashes`` (sorted
  ``name:digest``) when clew is installed, an identical local copy otherwise.
"""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

SCHEMA = "scitex-stats/provenance@1"
DEFAULT_SEED = 42
NAN_POLICIES = ("omit", "raise")
# Keys never covered by result_sha256 (the receipt itself, wall-clock fields).
RESULT_HASH_EXCLUDE = ("provenance", "timestamp")
# Inputs up to this many values are embedded so verify() can recompute alone.
EMBED_MAX_VALUES = 100_000

_VERSION_PACKAGES = (
    "scitex-stats",
    "numpy",
    "scipy",
    "pandas",
    "statsmodels",
    "pingouin",
    "scitex-clew",
)


class InputIntegrityError(ValueError):
    """Input data rejected: non-numeric, infinite, empty, or NaN under ``nan_policy='raise'``."""


# ---------------------------------------------------------------------------
# Canonical hashing
# ---------------------------------------------------------------------------


def _canonical_float_array(arr: np.ndarray) -> np.ndarray:
    a = np.ascontiguousarray(arr, dtype="<f8")
    a = np.where(np.isnan(a), np.float64("nan"), a)
    return a + 0.0  # folds -0.0 into 0.0


def hash_array(values: Any) -> str:
    """SHA-256 of numeric data under the canonical float64 convention."""
    a = _canonical_float_array(np.asarray(values, dtype=float))
    header = f"scitex-stats:ndarray:v1:<f8:{list(a.shape)}".encode()
    return hashlib.sha256(header + b"\0" + a.tobytes()).hexdigest()


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [_jsonable(v) for v in obj.tolist()]
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        f = float(obj)
        if np.isnan(f):
            return {"__float__": "nan"}
        if np.isinf(f):
            return {"__float__": "inf" if f > 0 else "-inf"}
        return f
    if obj is None or isinstance(obj, str):
        return obj
    return {"__repr__": type(obj).__name__}


def canonical_json(obj: Any) -> str:
    """Deterministic JSON text used for every non-array hash."""
    return json.dumps(
        _jsonable(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def hash_json(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def hash_result(result: Dict[str, Any]) -> str:
    """SHA-256 of a result dict, excluding the receipt and wall-clock keys."""
    return hash_json({k: v for k, v in result.items() if k not in RESULT_HASH_EXCLUDE})


def combine_hashes(hashes: Dict[str, str]) -> str:
    """Combined input digest; delegates to scitex-clew when installed."""
    try:
        from scitex_clew._hash import combine_hashes as clew_combine
    except Exception:
        hasher = hashlib.sha256()
        for key in sorted(hashes):
            hasher.update(f"{key}:{hashes[key]}".encode())
        return hasher.hexdigest()
    return clew_combine(hashes)


# ---------------------------------------------------------------------------
# Input integrity
# ---------------------------------------------------------------------------


def _to_float_array(name: str, values: Any) -> Tuple[np.ndarray, Optional[str], int]:
    """Coerce to float64, returning (array, coercion note, count of None values)."""
    source = type(values).__name__
    if hasattr(values, "to_numpy") and not isinstance(values, np.ndarray):
        values = values.to_numpy()
    arr = np.asarray(values)
    kind = arr.dtype.kind
    n_none = 0
    if kind == "f":
        out = arr.astype(float, copy=False)
    elif kind in "iub":
        out = arr.astype(float)
    elif kind == "O":
        flat = []
        for v in arr.ravel().tolist():
            if v is None:
                n_none += 1
                flat.append(np.nan)
            elif isinstance(v, (bool, int, float, np.number, np.bool_)):
                flat.append(float(v))
            else:
                raise InputIntegrityError(
                    f"'{name}' contains a non-numeric value {v!r} ({type(v).__name__}); "
                    "convert it explicitly before testing"
                )
        out = np.asarray(flat, dtype=float).reshape(arr.shape)
    else:
        raise InputIntegrityError(
            f"'{name}' has non-numeric dtype {arr.dtype} ({source}); "
            "strings are never coerced implicitly"
        )
    coercion = None if kind == "f" and source == "ndarray" else f"{source}[{arr.dtype}] -> ndarray[float64]"
    return out, coercion, n_none


def _check_finite(name: str, arr: np.ndarray) -> None:
    if np.isinf(arr).any():
        idx = np.flatnonzero(np.isinf(arr.ravel()))[:10].tolist()
        raise InputIntegrityError(f"'{name}' contains infinite values (flat indices {idx})")


def _report(name, raw, used_mask, coercion, n_none, reason_nan):
    n_input = int(raw.shape[0]) if raw.ndim else 1
    excluded = np.flatnonzero(~used_mask).tolist() if used_mask is not None else []
    rep = {
        "n_input": n_input,
        "n_used": n_input - len(excluded),
        "n_excluded": len(excluded),
        "excluded_indices": excluded,
        "excluded_reason": ({reason_nan: len(excluded)} if excluded else {}),
        "coercion": coercion,
    }
    if n_none:
        rep["none_as_nan"] = n_none
    return rep


def sanitize_inputs(
    inputs: Dict[str, Any],
    *,
    paired: bool = False,
    table: bool = False,
    nan_policy: str = "omit",
) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray], Dict[str, Any]]:
    """Validate and clean named inputs without silently dropping anything.

    Returns ``(raw, used, integrity)``: ``raw`` is each input as float64 (what
    the receipt hashes), ``used`` is what the test receives, ``integrity`` is
    the per-input exclusion/coercion report stored in the result.

    ``paired=True`` removes a position from EVERY input when any input is NaN
    there (paired / correlation / repeated-measures designs). ``table=True``
    (contingency tables) rejects NaN outright. Infinite values, non-numeric
    values and empty inputs always raise :class:`InputIntegrityError`.
    """
    if nan_policy not in NAN_POLICIES:
        raise ValueError(f"nan_policy must be one of {NAN_POLICIES}, got {nan_policy!r}")

    raw: Dict[str, np.ndarray] = {}
    notes: Dict[str, Tuple[Optional[str], int]] = {}
    for name, values in inputs.items():
        if values is None:
            continue
        arr, coercion, n_none = _to_float_array(name, values)
        if arr.size == 0:
            raise InputIntegrityError(f"'{name}' is empty")
        _check_finite(name, arr)
        raw[name] = arr
        notes[name] = (coercion, n_none)

    def _nan_rows(a: np.ndarray) -> np.ndarray:
        return np.isnan(a) if a.ndim == 1 else np.isnan(a.reshape(a.shape[0], -1)).any(axis=1)

    for name, arr in raw.items():
        if np.isnan(arr).any() and (table or nan_policy == "raise"):
            where = "contingency tables cannot contain NaN" if table else "nan_policy='raise'"
            raise InputIntegrityError(
                f"'{name}' contains {int(np.isnan(arr).sum())} NaN value(s) ({where})"
            )

    used: Dict[str, np.ndarray] = {}
    integrity: Dict[str, Any] = {"nan_policy": nan_policy, "inputs": {}}
    if table:
        for name, arr in raw.items():
            used[name] = arr
            integrity["inputs"][name] = _report(name, arr, None, *notes[name], "nan")
        return raw, used, integrity

    if paired and len(raw) > 1:
        lengths = {name: arr.shape[0] for name, arr in raw.items()}
        if len(set(lengths.values())) != 1:
            raise InputIntegrityError(f"paired inputs must have equal length, got {lengths}")
        keep = np.ones(next(iter(lengths.values())), dtype=bool)
        for arr in raw.values():
            keep &= ~_nan_rows(arr)
        for name, arr in raw.items():
            used[name] = arr[keep]
            integrity["inputs"][name] = _report(name, arr, keep, *notes[name], "nan_pairwise")
    else:
        for name, arr in raw.items():
            keep = ~_nan_rows(arr)
            used[name] = arr[keep]
            integrity["inputs"][name] = _report(name, arr, keep, *notes[name], "nan")

    for name, arr in used.items():
        if arr.shape[0] == 0:
            raise InputIntegrityError(f"'{name}' has no values left after excluding NaN")
    integrity["n_excluded_total"] = sum(r["n_excluded"] for r in integrity["inputs"].values())
    return raw, used, integrity


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------


def library_versions() -> Dict[str, Optional[str]]:
    from importlib.metadata import PackageNotFoundError, version

    out: Dict[str, Optional[str]] = {}
    for pkg in _VERSION_PACKAGES:
        try:
            out[pkg] = version(pkg)
        except PackageNotFoundError:
            out[pkg] = None
    out["python"] = platform.python_version()
    out["platform"] = f"{platform.system()}-{platform.machine()}"
    return out


def describe_inputs(raw: Dict[str, np.ndarray], embed: bool = True) -> Dict[str, Any]:
    total = sum(int(a.size) for a in raw.values())
    out = {}
    for name, arr in raw.items():
        entry = {
            "sha256": hash_array(arr),
            "n": int(arr.shape[0]) if arr.ndim else 1,
            "shape": list(arr.shape),
        }
        if embed and total <= EMBED_MAX_VALUES:
            entry["values"] = _jsonable(arr.tolist())
        out[name] = entry
    return out


def build_provenance(
    *,
    api: str,
    test_name: str,
    function: Optional[str],
    parameters: Dict[str, Any],
    raw_inputs: Dict[str, np.ndarray],
    result: Dict[str, Any],
    seed: Optional[int] = None,
    stochastic: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble the receipt for ``result`` (not attached; see :func:`attach`)."""
    inputs = describe_inputs(raw_inputs)
    prov: Dict[str, Any] = {
        "schema": SCHEMA,
        "api": api,
        "test": {"name": test_name, "function": function, "parameters": _jsonable(parameters)},
        "inputs": inputs,
        "input_sha256": combine_hashes({k: v["sha256"] for k, v in inputs.items()}),
        "randomness": {
            "stochastic": bool(stochastic),
            "seed": seed,
            "generator": "numpy.random.default_rng (PCG64)" if stochastic else None,
        },
        "versions": library_versions(),
        "result_sha256": hash_result(result),
        "hash_algorithm": "sha256",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    }
    if extra:
        prov.update(_jsonable(extra))
    prov["receipt_sha256"] = receipt_hash(prov)
    return prov


def receipt_hash(prov: Dict[str, Any]) -> str:
    return hash_json({k: v for k, v in prov.items() if k != "receipt_sha256"})


def attach(result: Any, **kwargs: Any) -> Any:
    """Attach a receipt to a dict result in place; other return types pass through."""
    if isinstance(result, dict):
        result["provenance"] = build_provenance(result=result, **kwargs)
    return result


def input_names(groups: Optional[Iterable[Any]]) -> List[str]:
    return [f"groups[{i}]" for i, _ in enumerate(groups or [])]


__all__ = [
    "SCHEMA",
    "DEFAULT_SEED",
    "InputIntegrityError",
    "attach",
    "build_provenance",
    "canonical_json",
    "combine_hashes",
    "hash_array",
    "hash_result",
    "library_versions",
    "receipt_hash",
    "sanitize_inputs",
]

# EOF
