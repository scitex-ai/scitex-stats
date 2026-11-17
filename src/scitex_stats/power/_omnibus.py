"""Private ANOVA and goodness-of-fit chi-square power calculations."""

import math


def _minimum_n(power_at, target, minimum, maximum):
    """Find the first feasible integer within the existing supported range."""
    if not math.isfinite(target) or not 0 < target < 1:
        raise ValueError("target power must be finite and strictly between 0 and 1")

    def attained(n):
        value = power_at(n)
        if not math.isfinite(value):
            raise ValueError(f"Power is undefined at sample size {n}")
        return value >= target

    if not attained(maximum):
        raise ValueError(
            f"Target power {target} is not attained within sample sizes "
            f"{minimum}..{maximum}"
        )
    low, high = minimum, maximum
    while low < high:
        middle = (low + high) // 2
        if attained(middle):
            high = middle
        else:
            low = middle + 1
    return low


def _power_anova(
    effect_size: float | None,
    alpha: float,
    power: float,
    n: int | None,
    n_groups: int,
) -> dict:
    """ANOVA power calculation."""
    from scipy import stats as scipy_stats

    if effect_size is None:
        raise ValueError("effect_size required for ANOVA power")

    if n is not None:
        df1 = n_groups - 1
        df2 = n_groups * n - n_groups
        nc = effect_size**2 * n * n_groups
        f_crit = scipy_stats.f.ppf(1 - alpha, df1, df2)
        power_val = 1 - scipy_stats.ncf.cdf(f_crit, df1, df2, nc)
        return {
            "mode": "power_calculation",
            "power": power_val,
            "n_per_group": n,
            "n_groups": n_groups,
            "effect_size_f": effect_size,
            "alpha": alpha,
        }
    else:
        def power_at(sample_size):
            n = sample_size
            df1 = n_groups - 1
            df2 = n_groups * n - n_groups
            nc = effect_size**2 * n * n_groups
            f_crit = scipy_stats.f.ppf(1 - alpha, df1, df2)
            power_val = 1 - scipy_stats.ncf.cdf(f_crit, df1, df2, nc)
            return power_val

        n_max = _minimum_n(power_at, power, 2, 1000)

        return {
            "mode": "sample_size_calculation",
            "required_n_per_group": n_max,
            "total_n": n_max * n_groups,
            "n_groups": n_groups,
            "effect_size_f": effect_size,
            "target_power": power,
            "alpha": alpha,
        }


def _power_chi2(
    effect_size: float | None,
    alpha: float,
    power: float,
    n: int | None,
    n_groups: int,
) -> dict:
    """Chi-square power calculation."""
    from scipy import stats as scipy_stats

    if effect_size is None:
        raise ValueError("effect_size (w) required for chi2 power")

    df = n_groups - 1  # Simplified: using n_groups as number of cells

    if n is not None:
        nc = effect_size**2 * n
        chi2_crit = scipy_stats.chi2.ppf(1 - alpha, df)
        power_val = 1 - scipy_stats.ncx2.cdf(chi2_crit, df, nc)
        return {
            "mode": "power_calculation",
            "power": power_val,
            "n": n,
            "df": df,
            "effect_size_w": effect_size,
            "alpha": alpha,
        }
    else:
        def power_at(sample_size):
            n = sample_size
            nc = effect_size**2 * n
            chi2_crit = scipy_stats.chi2.ppf(1 - alpha, df)
            power_val = 1 - scipy_stats.ncx2.cdf(chi2_crit, df, nc)
            return power_val

        n_max = _minimum_n(power_at, power, 10, 10000)

        return {
            "mode": "sample_size_calculation",
            "required_n": n_max,
            "df": df,
            "effect_size_w": effect_size,
            "target_power": power,
            "alpha": alpha,
        }
