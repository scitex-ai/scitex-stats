#!/usr/bin/env python3
# Timestamp: 2026-01-25
# File: src/scitex/stats/_mcp/_handlers/_corrections.py

"""P-value correction handler for multiple comparisons."""

from __future__ import annotations

import asyncio
from datetime import datetime

import numpy as np

__all__ = ["correct_pvalues_handler"]


async def correct_pvalues_handler(
    pvalues: list[float],
    method: str = "fdr_bh",
    alpha: float = 0.05,
) -> dict:
    """Apply multiple comparison correction to p-values."""
    try:
        loop = asyncio.get_event_loop()

        def do_correct():
            from statsmodels.stats.multitest import multipletests

            # Map method names
            method_map = {
                "bonferroni": "bonferroni",
                "fdr_bh": "fdr_bh",
                "fdr_by": "fdr_by",
                "holm": "holm",
                "sidak": "sidak",
            }
            sm_method = method_map.get(method, "fdr_bh")

            pvals = np.array(pvalues)
            reject, pvals_corrected, _, _ = multipletests(
                pvals, alpha=alpha, method=sm_method
            )

            return {
                "original_pvalues": pvalues,
                "corrected_pvalues": pvals_corrected.tolist(),
                "reject_null": reject.tolist(),
                "n_significant": int(reject.sum()),
                "n_tests": len(pvalues),
            }

        result = await loop.run_in_executor(None, do_correct)

        return {
            "success": True,
            "method": method,
            "alpha": alpha,
            **result,
            "timestamp": datetime.now().isoformat(),
        }

    except ImportError:
        # Fallback implementation without statsmodels
        try:
            n = len(pvalues)
            pvals = np.array(pvalues)

            # Unknown methods fall back to fdr_bh, mirroring the
            # statsmodels path's method_map default
            # (test_unknown_method_falls_back_to_fdr_bh). The requested
            # name is still echoed in the output's "method" field.
            correct_method = (
                method
                if method in ("bonferroni", "holm", "fdr_bh", "fdr_by", "sidak")
                else "fdr_bh"
            )

            if correct_method == "bonferroni":
                corrected = np.minimum(pvals * n, 1.0)
            elif correct_method == "holm":
                sorted_idx = np.argsort(pvals)
                corrected = np.empty(n)
                cummax = 0.0
                for rank, idx in enumerate(sorted_idx, start=1):
                    adj = min((n - rank + 1) * pvals[idx], 1.0)
                    adj = max(adj, cummax)
                    corrected[idx] = adj
                    cummax = adj
            elif correct_method == "fdr_bh":
                sorted_idx = np.argsort(pvals)
                corrected = np.empty(n)
                prev = 1.0
                for rank in range(n, 0, -1):
                    idx = sorted_idx[rank - 1]
                    bh = pvals[idx] * n / rank
                    val = min(bh, prev, 1.0)
                    corrected[idx] = val
                    prev = val
            elif correct_method == "sidak":
                corrected = 1 - (1 - pvals) ** n
            else:
                corrected = pvals

            return {
                "success": True,
                "method": method,
                "alpha": alpha,
                "original_pvalues": pvalues,
                "corrected_pvalues": corrected.tolist(),
                "reject_null": (corrected < alpha).tolist(),
                "n_significant": int((corrected < alpha).sum()),
                "n_tests": n,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    except Exception as e:
        return {"success": False, "error": str(e)}


# EOF
