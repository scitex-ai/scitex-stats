"""Synchronous native power-analysis dispatch shared by Python and MCP."""

from __future__ import annotations

import numpy as np

__all__ = ["power_analysis"]


def power_analysis(
    test_type: str = "ttest",
    effect_size: float | None = None,
    alpha: float = 0.05,
    power: float = 0.8,
    n: int | None = None,
    n_groups: int = 2,
    ratio: float = 1.0,
) -> dict:
    """Calculate power or a sample size using the existing method policies.

    Return numerical fields including ``test_type`` and ``mode``. Errors raise
    normally; timestamps and success/error envelopes belong to the transport.
    ANOVA and goodness-of-fit chi-square planning use their bounded native
    searches. This dispatcher preserves the existing t-test and Fisher-z
    correlation approximations and does not add general input validation.
    """
    from ._omnibus import _power_anova, _power_chi2
    from ._power import power_ttest, sample_size_ttest

    result = {}

    if test_type == "ttest":
        if n is not None and effect_size is not None:
            # Calculate power given n and effect size
            calculated_power = power_ttest(
                effect_size=effect_size,
                n1=n,
                n2=int(n * ratio),
                alpha=alpha,
                test_type="two-sample",
            )
            result = {
                "mode": "power_calculation",
                "power": calculated_power,
                "n1": n,
                "n2": int(n * ratio),
                "effect_size": effect_size,
                "alpha": alpha,
            }
        elif effect_size is not None:
            # Calculate required sample size
            n1, n2 = sample_size_ttest(
                effect_size=effect_size,
                power=power,
                alpha=alpha,
                ratio=ratio,
            )
            result = {
                "mode": "sample_size_calculation",
                "required_n1": n1,
                "required_n2": n2,
                "total_n": n1 + n2,
                "effect_size": effect_size,
                "target_power": power,
                "alpha": alpha,
            }
        else:
            raise ValueError("Either n or effect_size must be provided")

    elif test_type == "anova":
        result = _power_anova(effect_size, alpha, power, n, n_groups)

    elif test_type == "correlation":
        result = _power_correlation(effect_size, alpha, power, n)

    elif test_type == "chi2":
        result = _power_chi2(effect_size, alpha, power, n, n_groups)

    else:
        raise ValueError(f"Unknown test_type: {test_type}")

    return {"test_type": test_type, **result}


def _power_correlation(
    effect_size: float | None,
    alpha: float,
    power: float,
    n: int | None,
) -> dict:
    """Correlation power calculation."""
    from scipy import stats as scipy_stats

    if effect_size is None:
        raise ValueError("effect_size (r) required for correlation power")

    if n is not None:
        # Calculate power
        z = 0.5 * np.log((1 + effect_size) / (1 - effect_size))
        se = 1 / np.sqrt(n - 3)
        z_crit = scipy_stats.norm.ppf(1 - alpha / 2)
        power_val = (
            1
            - scipy_stats.norm.cdf(z_crit - z / se)
            + scipy_stats.norm.cdf(-z_crit - z / se)
        )
        return {
            "mode": "power_calculation",
            "power": power_val,
            "n": n,
            "effect_size_r": effect_size,
            "alpha": alpha,
        }
    else:
        # Calculate required n
        z = 0.5 * np.log((1 + effect_size) / (1 - effect_size))
        z_crit = scipy_stats.norm.ppf(1 - alpha / 2)
        z_power = scipy_stats.norm.ppf(power)
        required_n = int(np.ceil(((z_crit + z_power) / z) ** 2 + 3))
        return {
            "mode": "sample_size_calculation",
            "required_n": required_n,
            "effect_size_r": effect_size,
            "target_power": power,
            "alpha": alpha,
        }
