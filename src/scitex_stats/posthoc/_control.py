"""Shared-error Dunnett control comparisons owned by the statistics leaf."""

from inspect import signature

import numpy as np
from scipy import stats


def _dunnett_control(groups, control_group=0):
    """Run two-sided single-step Dunnett with repeatable local QMC integration.

    ``p_unadjusted`` is the marginal t tail using the shared pooled error/df;
    ``p_adjusted`` is the backend's multiple-to-control probability. This
    helper does not use or qualify the separate legacy ``posthoc_dunnett``.
    """
    if not 0 <= control_group < len(groups):
        raise ValueError("control_group must be a zero-based index of an input group")
    arrays = [np.asarray(group, dtype=float) for group in groups]
    if len(arrays) < 2 or any(
        g.ndim != 1 or g.size == 0 or not np.isfinite(g).all() for g in arrays
    ):
        raise ValueError("Dunnett requires at least two non-empty finite 1D groups")
    df = sum(g.size for g in arrays) - len(arrays)
    pooled_variance = (
        sum(float(np.sum((g - g.mean()) ** 2)) for g in arrays) / df
        if df > 0 else float("nan")
    )
    if not np.isfinite(pooled_variance) or pooled_variance <= 0:
        raise ValueError("Dunnett requires finite positive pooled error and degrees of freedom")
    try:
        from scipy.stats import dunnett
    except ImportError as error:
        raise ImportError(
            "Dunnett backend requires scipy.stats.dunnett (SciPy >= 1.11); "
            "cannot run the requested method."
        ) from error

    indices = [i for i in range(len(arrays)) if i != control_group]
    # rng supersedes random_state in SciPy1.15; both use a private Generator.
    rng_keyword = "rng" if "rng" in signature(dunnett).parameters else "random_state"
    result = dunnett(
        *(arrays[i] for i in indices), control=arrays[control_group],
        alternative="two-sided", **{rng_keyword: np.random.default_rng(42)},
    )
    if not (np.isfinite(result.statistic).all() and np.isfinite(result.pvalue).all()
            and np.all((result.pvalue >= 0) & (result.pvalue <= 1))):
        raise ValueError("Dunnett backend returned undefined statistics or probabilities")
    return [{
        "i": i, "control": control_group,
        "mean_diff": float(arrays[i].mean() - arrays[control_group].mean()),
        "statistic": float(statistic), "df": int(df),
        "p_unadjusted": float(2 * stats.t.sf(abs(statistic), df)),
        "p_adjusted": float(probability),
    } for i, statistic, probability in zip(indices, result.statistic, result.pvalue)]
