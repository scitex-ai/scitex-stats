#!/usr/bin/env python3
# File: src/scitex_stats/_utils/_pairwise_counts.py

"""Exact pairwise dominance counts in O((n + m) log m) time and O(n + m) memory.

Cliff's delta and the probability of superiority both need, over every pair
``(x_i, y_j)``, how many have ``x_i > y_j`` and how many ``x_i < y_j``. The
broadcast ``x[:, None] > y`` materialises an ``n x m`` matrix (2.5 GB for two
50 000-value samples); sorting ``y`` once and binary-searching every ``x_i``
gives the same integers without it.
"""

from __future__ import annotations

import numpy as np

__all__ = ["pairwise_counts"]


def pairwise_counts(x: np.ndarray, y: np.ndarray) -> tuple:
    """``(#{x_i > y_j}, #{x_i < y_j})`` over all pairs, ties counted in neither.

    ``x`` and ``y`` must be NaN-free one-dimensional numeric arrays.
    """
    sorted_y = np.sort(np.asarray(y, dtype=float))
    x = np.asarray(x, dtype=float)
    below = np.searchsorted(sorted_y, x, side="left")  # y_j < x_i
    not_above = np.searchsorted(sorted_y, x, side="right")  # y_j <= x_i
    # NumPy integers on purpose: callers divide by nx * ny, and an empty
    # sample must stay a NaN (with NumPy's warning), not a ZeroDivisionError.
    more = below.sum(dtype=np.int64)
    less = (sorted_y.size - not_above).sum(dtype=np.int64)
    return more, less


# EOF
