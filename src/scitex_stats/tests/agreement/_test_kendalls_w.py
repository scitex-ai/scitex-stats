#!/usr/bin/env python3
# Timestamp: "2026-06-03 10:15:00 (ywatanabe)"
# File: scitex_stats/tests/agreement/_test_kendalls_w.py
# ----------------------------------------
from __future__ import annotations

"""
Functionalities:
  - Compute Kendall's coefficient of concordance W (Kendall & Babington
    Smith 1939) on a (n_subjects, k_raters) matrix of scores
  - Return W, chi-squared significance approximation, and degrees of
    freedom in a uniform result dict / DataFrame

Dependencies:
  - packages: numpy, pandas, scipy

IO:
  - input: 2-D matrix of scores (rows = subjects, cols = raters), or a
    long-format DataFrame with subj/rater/score columns
  - output: result dict / DataFrame with W, chi2, dof, pvalue, n, k
"""

import os
from typing import Literal, Optional, Union

import numpy as np
import pandas as pd
from scipy.stats import chi2 as _chi2_dist
from scipy.stats import rankdata

from scitex_stats._logging import getLogger
from scitex_stats._utils._formatters import fmt_stat, fmt_sym, p2stars
from scitex_stats._utils._normalizers import convert_results, force_dataframe

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)

logger = getLogger(__name__)


def interpret_kendalls_w(W: float) -> str:
    """Interpret Kendall's W magnitude.

    Common rough guideposts (Schmidt 1997, citing Landis & Koch):
        W < 0.1   : negligible agreement
        0.1-0.3   : weak
        0.3-0.5   : moderate
        0.5-0.7   : strong
        ≥ 0.7     : very strong / unusually high
    """
    w_abs = abs(W)
    if w_abs < 0.1:
        return "negligible"
    if w_abs < 0.3:
        return "weak"
    if w_abs < 0.5:
        return "moderate"
    if w_abs < 0.7:
        return "strong"
    return "very strong"


def _as_matrix(
    data: Union[np.ndarray, pd.DataFrame, dict],
    *,
    subj_col: Optional[str] = None,
    rater_col: Optional[str] = None,
    score_col: Optional[str] = None,
) -> np.ndarray:
    """Coerce input to a 2-D (n_subjects, k_raters) ndarray."""
    if isinstance(data, np.ndarray):
        mat = data
    elif isinstance(data, pd.DataFrame):
        if (subj_col and rater_col and score_col
                and {subj_col, rater_col, score_col}.issubset(data.columns)):
            mat = (data.pivot_table(index=subj_col, columns=rater_col,
                                    values=score_col)
                       .to_numpy())
        else:
            mat = data.to_numpy()
    elif isinstance(data, dict):
        mat = pd.DataFrame(data).to_numpy()
    else:
        mat = np.asarray(data)
    if mat.ndim != 2:
        raise ValueError(
            "Kendall's W requires a 2-D (n_subjects, k_raters) matrix;"
            f" got shape {mat.shape}"
        )
    return mat.astype(float)


def test_kendalls_w(
    data: Union[np.ndarray, pd.DataFrame, dict],
    *,
    subj_col: Optional[str] = None,
    rater_col: Optional[str] = None,
    score_col: Optional[str] = None,
    use_abs: bool = False,
    alpha: float = 0.05,
    return_as: Literal["dict", "dataframe"] = "dict",
    decimals: int = 3,
    verbose: bool = False,
) -> Union[dict, pd.DataFrame]:
    """
    Kendall's coefficient of concordance W.

    Parameters
    ----------
    data : ndarray | DataFrame | dict
        2-D matrix of scores (rows = subjects, cols = raters), or a
        long-format DataFrame with (subj, rater, score) triples (pass
        ``subj_col``, ``rater_col``, ``score_col`` to pivot).
    subj_col, rater_col, score_col : str, optional
        Column names for the long-format input. Ignored if ``data`` is
        already a wide matrix.
    use_abs : bool, default False
        If True, rank ``|score|`` instead of ``score``. Useful when the
        sign of the score is irrelevant to the agreement question
        (e.g. ranking channels by absolute effect size).
    alpha : float, default 0.05
        Significance level (used only for the formatted summary).
    return_as : {"dict", "dataframe"}, default "dict"
        Output container.
    decimals : int, default 3
        Rounding for the formatted summary.
    verbose : bool, default False

    Returns
    -------
    dict | DataFrame
        Keys: name, statistic, W, S, n, k, dof, chi2, pvalue, alpha,
        significant, formatted, sym, stars, effect_size,
        effect_size_label, interpretation.

    Notes
    -----
    W is computed on the within-rater ranks of each subject. Ties are
    handled by ``scipy.stats.rankdata`` (average ranks). With k raters
    and n subjects:

    .. math::

        S = \\sum_{i=1}^{n} \\Big(R_i - \\bar{R}\\Big)^2,
        \\qquad W = \\frac{12 S}{k^2 (n^3 - n)}

    The significance approximation uses Friedman's chi-square statistic
    :math:`\\chi^2 = k(n-1) W` with :math:`n-1` degrees of freedom.
    The approximation is reasonable for :math:`n \\ge 5`.

    References
    ----------
    Kendall, M. G. & Babington Smith, B. (1939). The Problem of m Rankings.
    Annals of Mathematical Statistics, 10(3), 275-287.
    Schmidt, F. (1997). Managing Project Risk and Uncertainty.
    Legendre, P. (2005). Species associations: the Kendall coefficient of
    concordance revisited. Journal of Agricultural, Biological, and
    Environmental Statistics, 10(2), 226-245.
    """
    mat = _as_matrix(data, subj_col=subj_col, rater_col=rater_col,
                     score_col=score_col)
    if np.isnan(mat).any():
        keep = ~np.isnan(mat).any(axis=1)
        dropped = int(mat.shape[0] - keep.sum())
        if verbose and dropped:
            logger.info(
                "test_kendalls_w: dropping %d subjects with NaN ratings",
                dropped,
            )
        mat = mat[keep]
    n, k = mat.shape
    if n < 2 or k < 2:
        result = {
            "name": "Kendall's W (coefficient of concordance)",
            "statistic": float("nan"),
            "W": float("nan"),
            "S": float("nan"),
            "n": int(n),
            "k": int(k),
            "dof": 0,
            "chi2": float("nan"),
            "pvalue": float("nan"),
            "alpha": alpha,
            "significant": False,
            "formatted": "Kendall's W: insufficient data",
            "sym": "",
            "stars": "",
            "effect_size": float("nan"),
            "effect_size_label": "Kendall's W",
            "interpretation": "n/a (insufficient data)",
        }
        return convert_results(result, return_as=return_as)

    target = np.abs(mat) if use_abs else mat
    ranks = np.apply_along_axis(rankdata, 0, target)
    R = ranks.sum(axis=1)
    S = float(((R - R.mean()) ** 2).sum())
    W = 12.0 * S / (k ** 2 * (n ** 3 - n))
    chi2_stat = k * (n - 1) * W
    dof = n - 1
    pvalue = float(1.0 - _chi2_dist.cdf(chi2_stat, dof))

    interp = interpret_kendalls_w(W)
    significant = pvalue < alpha
    stars = p2stars(pvalue)
    sym = fmt_sym("W")
    stat_str = fmt_stat("W", W, fmt=f".{decimals}f", stars=stars)
    formatted = (
        f"Kendall's W = {W:.{decimals}f}, "
        f"χ²({dof}) = {chi2_stat:.{decimals}f}, "
        f"p = {pvalue:.{decimals}f} {stars} "
        f"(n = {n}, k = {k}, {interp})"
    )

    result = {
        "name": "Kendall's W (coefficient of concordance)",
        "statistic": float(W),
        "W": float(W),
        "S": S,
        "n": int(n),
        "k": int(k),
        "dof": int(dof),
        "chi2": float(chi2_stat),
        "pvalue": pvalue,
        "alpha": alpha,
        "significant": significant,
        "formatted": formatted,
        "stat_str": stat_str,
        "sym": sym,
        "stars": stars,
        "effect_size": float(W),
        "effect_size_label": "Kendall's W",
        "interpretation": interp,
    }
    if verbose:
        logger.info(formatted)
    return convert_results(result, return_as=return_as)
