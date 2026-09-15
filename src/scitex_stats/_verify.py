#!/usr/bin/env python3
# File: src/scitex_stats/_verify.py

"""Verify a scitex-stats result against its provenance receipt.

``verify(result, data=...)`` answers "is this number really what scitex-stats
computes for this data?" with four independent checks:

- ``receipt``   — the receipt's own hash matches (metadata not edited);
- ``result``    — the result's hash matches the receipt (statistics not edited);
- ``inputs``    — the supplied data (or the embedded copy) hashes to the
  recorded per-input SHA-256;
- ``recompute`` — re-running the recorded test with the recorded parameters and
  seed on that data reproduces the stored result bit-for-bit.

``verified`` is True only when all four pass. Library-version drift is
reported as a warning (it is the usual cause of a recompute mismatch).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np

from ._provenance import SCHEMA, hash_array, hash_result, library_versions, receipt_hash

# Recorded from the caller's container (list vs ndarray, None vs NaN); not recomputable.
_CALLER_FORMAT_FIELDS = ("coercion", "none_as_nan")


def _decode_values(values: Any) -> Any:
    if isinstance(values, list):
        return [_decode_values(v) for v in values]
    if isinstance(values, dict) and "__float__" in values:
        return float(values["__float__"])
    return values


def _check(name: str, ok: Optional[bool], detail: str, **extra: Any) -> Dict[str, Any]:
    status = "skip" if ok is None else ("pass" if ok else "fail")
    return {"name": name, "status": status, "detail": detail, **extra}


def _load(result: Union[Dict[str, Any], str, Path]) -> Dict[str, Any]:
    if isinstance(result, (str, Path)):
        return json.loads(Path(result).read_text())
    return result


def _supplied_inputs(prov, data, data2, groups) -> Dict[str, Any]:
    supplied: Dict[str, Any] = {}
    if prov["api"] == "mcp.run_test":
        for i, g in enumerate(data or []):
            supplied[f"data[{i}]"] = g
        return supplied
    if data is not None:
        supplied["data"] = data
    if data2 is not None:
        supplied["data2"] = data2
    for i, g in enumerate(groups or []):
        supplied[f"groups[{i}]"] = g
    return supplied


def _resolve_inputs(prov, supplied):
    """Pick the data to verify with: caller-supplied first, else embedded values."""
    resolved, rows = {}, []
    for name, rec in prov["inputs"].items():
        if name in supplied:
            values, origin = supplied[name], "supplied"
        elif "values" in rec:
            values, origin = _decode_values(rec["values"]), "embedded"
        else:
            rows.append({"input": name, "match": None, "origin": "missing"})
            continue
        try:
            arr = np.asarray(values, dtype=float)
        except (TypeError, ValueError) as exc:
            rows.append({"input": name, "match": False, "origin": origin, "error": str(exc)})
            continue
        got = hash_array(arr)
        match = got == rec["sha256"]
        if origin == "supplied" and "values" in rec:
            match = match and hash_array(np.asarray(_decode_values(rec["values"]), float)) == got
        rows.append({"input": name, "match": match, "origin": origin, "sha256": got})
        resolved[name] = values
    extra = sorted(set(supplied) - set(prov["inputs"]))
    for name in extra:
        rows.append({"input": name, "match": False, "origin": "supplied", "error": "not in receipt"})
    return resolved, rows


def _recompute(prov: Dict[str, Any], inputs: Dict[str, Any], source_result) -> Dict[str, Any]:
    api = prov["api"]
    params = dict(prov["test"]["parameters"])
    name = prov["test"]["name"]
    if api == "run_test":
        from ._dispatch import run_test

        groups = [inputs[k] for k in sorted(inputs, key=_group_index) if k.startswith("groups[")]
        params["plot"] = False
        return run_test(
            name,
            data=inputs.get("data"),
            data2=inputs.get("data2"),
            groups=groups or None,
            **params,
        )
    if api == "full_report":
        from .reporting._full_report import full_report

        if source_result is None:
            raise LookupError("full_report recompute needs source_result= (the run_test result)")
        return full_report(source_result, data=inputs.get("data"), data2=inputs.get("data2"), **params)
    if api == "mcp.run_test":
        from ._mcp._handlers._run_test import run_test_sync

        data = [inputs[k] for k in sorted(inputs, key=_group_index)]
        return run_test_sync(name, data=data, **params)
    raise LookupError(f"no recompute rule for api {api!r}")


def _group_index(key: str) -> int:
    return int(key[key.index("[") + 1 : -1]) if "[" in key else -1


def _comparable_integrity(integrity: Any) -> Any:
    """Drop fields describing the caller's container, which a recompute cannot reproduce."""
    if not isinstance(integrity, dict):
        return integrity
    out = dict(integrity)
    out["inputs"] = {
        name: {k: v for k, v in rep.items() if k not in _CALLER_FORMAT_FIELDS}
        for name, rep in (integrity.get("inputs") or {}).items()
    }
    return out


def _diff(stored: Dict[str, Any], fresh: Dict[str, Any]) -> List[Dict[str, Any]]:
    skip = {"provenance", "timestamp"}
    keys = sorted((set(stored) | set(fresh)) - skip)
    out = []
    for k in keys:
        a, b = stored.get(k, "<absent>"), fresh.get(k, "<absent>")
        if k == "input_integrity":
            a, b = _comparable_integrity(a), _comparable_integrity(b)
        if hash_result({"v": a}) != hash_result({"v": b}):
            out.append({"field": k, "stored": a, "recomputed": b})
    return out


def verify(
    result: Union[Dict[str, Any], str, Path],
    data: Optional[Any] = None,
    data2: Optional[Any] = None,
    groups: Optional[Sequence[Any]] = None,
    *,
    source_result: Optional[Dict[str, Any]] = None,
    recompute: bool = True,
) -> Dict[str, Any]:
    """Check a result's receipt, input hashes and statistics; recompute to confirm.

    Parameters
    ----------
    result : dict or path
        A result carrying ``provenance`` (or a JSON file saved from one, e.g.
        via ``scitex_io.save``).
    data, data2, groups : array-like, optional
        The data you believe the result was computed from, in the same slots
        as ``run_test``. For an MCP result pass the MCP ``data`` list as
        ``data``. When omitted, the copy embedded in the receipt is used.
    source_result : dict, optional
        For a ``full_report`` result: the ``run_test`` result it was built from.
    recompute : bool, default True
        Re-run the test and compare bit-for-bit.

    Returns
    -------
    dict
        ``{"verified": bool, "checks": [...], "summary": str}``. Each check has
        ``status`` pass / fail / skip; ``verified`` requires every check to pass.

    Examples
    --------
    >>> import scitex_stats as ss
    >>> r = ss.run_test("ttest_ind", data=[1.0, 2.0, 3.0, 4.0], data2=[2.0, 3.5, 4.0, 6.0])
    >>> ss.verify(r, data=[1.0, 2.0, 3.0, 4.0], data2=[2.0, 3.5, 4.0, 6.0])["verified"]
    True
    """
    res = _load(result)
    prov = res.get("provenance") if isinstance(res, dict) else None
    checks: List[Dict[str, Any]] = []
    if not isinstance(prov, dict) or prov.get("schema") != SCHEMA:
        checks.append(_check("receipt", False, f"no {SCHEMA} provenance on this result"))
        return {"verified": False, "checks": checks, "summary": "no provenance receipt"}

    ok = receipt_hash(prov) == prov.get("receipt_sha256")
    checks.append(_check("receipt", ok, "receipt hash matches" if ok else "receipt was modified"))

    got = hash_result(res)
    ok = got == prov.get("result_sha256")
    checks.append(
        _check(
            "result",
            ok,
            "result hash matches receipt" if ok else "result fields differ from what was recorded",
            expected=prov.get("result_sha256"),
            actual=got,
        )
    )

    inputs, rows = _resolve_inputs(prov, _supplied_inputs(prov, data, data2, groups))
    if any(r["match"] is None for r in rows):
        in_ok = None if all(r["match"] is not False for r in rows) else False
        detail = "some inputs were not embedded and not supplied"
    else:
        in_ok = all(r["match"] for r in rows)
        detail = "all input hashes match" if in_ok else "input data does not match the receipt"
    checks.append(_check("inputs", in_ok, detail, inputs=rows))

    if not recompute:
        checks.append(_check("recompute", None, "recompute=False"))
    elif in_ok is not True:
        checks.append(_check("recompute", None, "skipped: inputs not verified"))
    else:
        try:
            fresh = _recompute(prov, inputs, source_result)
        except Exception as exc:  # the failure itself is the finding
            checks.append(_check("recompute", False, f"recompute raised {type(exc).__name__}: {exc}"))
        else:
            diffs = _diff(res, fresh)
            ok = not diffs
            checks.append(
                _check(
                    "recompute",
                    ok,
                    "recomputed result is bit-identical" if ok else f"{len(diffs)} field(s) differ",
                    differences=diffs,
                )
            )

    now = library_versions()
    drift = {
        k: {"recorded": v, "current": now.get(k)}
        for k, v in prov.get("versions", {}).items()
        if now.get(k) != v
    }
    warnings = [f"version drift: {drift}"] if drift else []

    verified = all(c["status"] == "pass" for c in checks)
    failed = [c["name"] for c in checks if c["status"] != "pass"]
    summary = "verified" if verified else f"NOT verified ({', '.join(failed)})"
    return {
        "verified": verified,
        "test": prov["test"]["name"],
        "api": prov["api"],
        "input_sha256": prov.get("input_sha256"),
        "result_sha256": prov.get("result_sha256"),
        "checks": checks,
        "warnings": warnings,
        "summary": summary,
    }


__all__ = ["verify"]

# EOF
