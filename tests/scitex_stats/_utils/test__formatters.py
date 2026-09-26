#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: "2025-11-11"

"""Tests for scitex.stats._utils._formatters module."""

import numpy as np
import pandas as pd
import pytest

from scitex_stats._utils._formatters import _p2stars_scalar, fmt_sym_md, p2stars


def test_fmt_sym_md_italicizes_plain_symbol():
    # Arrange
    symbol = "t"
    # Act
    out = fmt_sym_md(symbol)
    # Assert
    assert out == "*t*"


def test_fmt_sym_md_keeps_lowercase_n_subscript_verbatim():
    # Arrange
    symbol = "n_x"
    # Act
    out = fmt_sym_md(symbol)
    # Assert
    assert out == "*n*_x"


def test_fmt_sym_md_keeps_uppercase_n_subscript_verbatim():
    # Arrange
    symbol = "N_subjects"
    # Act
    out = fmt_sym_md(symbol)
    # Assert
    assert out == "*N*_subjects"


def test_fmt_sym_md_does_not_conflate_upper_and_lower_n():
    # Arrange
    lower = fmt_sym_md("n_windows")
    # Act
    upper = fmt_sym_md("N_subjects")
    # Assert
    assert lower != upper


class TestP2stars:
    """Test p2stars function."""

    def test_highly_significant_p2stars(self):
        """Test p < 0.001."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.0001) == "***"

    def test_highly_significant_p2stars_2(self):
        """Test p < 0.001."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.0005) == "***"

    def test_very_significant_p2stars(self):
        """Test 0.001 <= p < 0.01."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.005) == "**"

    def test_very_significant_p2stars_2(self):
        """Test 0.001 <= p < 0.01."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.009) == "**"

    def test_significant_p2stars_1(self):
        """Test 0.01 <= p < 0.05."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.023) == "*"

    def test_significant_p2stars_2(self):
        """Test 0.01 <= p < 0.05."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.049) == "*"

    def test_not_significant_ns_p2stars(self):
        """Test p >= 0.05."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.051) == "ns"

    def test_not_significant_ns_p2stars_2(self):
        """Test p >= 0.05."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.15) == "ns"

    def test_not_significant_ns_p2stars_3(self):
        """Test p >= 0.05."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.999) == "ns"

    def test_exact_thresholds_p2stars(self):
        """Test at exact threshold values."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.05) == "*"  # p <= 0.05 → True, so *

    def test_exact_thresholds_p2stars_2(self):
        """Test at exact threshold values."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.01) == "**"  # p <= 0.01 → True, so **

    def test_exact_thresholds_p2stars_3(self):
        """Test at exact threshold values."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.001) == "***"  # p <= 0.001 → True, so ***

    def test_exact_thresholds_p2stars_4(self):
        """Test at exact threshold values."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.049) == "*"  # p <= 0.05 → True

    def test_exact_thresholds_p2stars_5(self):
        """Test at exact threshold values."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.0099) == "**"  # p <= 0.01 → True

    def test_exact_thresholds_p2stars_6(self):
        """Test at exact threshold values."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.0009) == "***"  # p <= 0.001 → True

    def test_boundary_cases_p2stars(self):
        """Test boundary p-values."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.0) == "***"

    def test_boundary_cases_ns_p2stars(self):
        """Test boundary p-values."""
        # Arrange
        # Act
        # Assert
        assert p2stars(1.0) == "ns"

    def test_no_ns_symbol_p2stars(self):
        """Test without ns symbol."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.15, ns_symbol=False) == ""

    def test_no_ns_symbol_p2stars_2(self):
        """Test without ns symbol."""
        # Arrange
        # Act
        # Assert
        assert p2stars(0.001, ns_symbol=False) == "***"  # 0.001 <= 0.001 is True

    def test_array_input_case_1(self):
        """Test with numpy array."""
        # Arrange
        pvals = np.array([0.0001, 0.005, 0.045, 0.15])
        # Act
        result = p2stars(pvals)
        # Assert
        assert result[0] == "***"

    def test_array_input_case_2(self):
        """Test with numpy array."""
        # Arrange
        pvals = np.array([0.0001, 0.005, 0.045, 0.15])
        # Act
        result = p2stars(pvals)
        # Assert
        assert result[1] == "**"

    def test_array_input_case_3(self):
        """Test with numpy array."""
        # Arrange
        pvals = np.array([0.0001, 0.005, 0.045, 0.15])
        # Act
        result = p2stars(pvals)
        # Assert
        assert result[2] == "*"

    def test_array_input_ns(self):
        """Test with numpy array."""
        # Arrange
        pvals = np.array([0.0001, 0.005, 0.045, 0.15])
        # Act
        result = p2stars(pvals)
        # Assert
        assert result[3] == "ns"

    def test_series_input_case_1(self):
        """Test with pandas Series."""
        # Arrange
        pvals = pd.Series([0.001, 0.02, 0.08])
        # Act
        result = p2stars(pvals)
        # Assert
        assert isinstance(result, pd.Series)

    def test_series_input_iloc(self):
        """Test with pandas Series."""
        # Arrange
        pvals = pd.Series([0.001, 0.02, 0.08])
        # Act
        result = p2stars(pvals)
        # Assert
        assert result.iloc[0] == "***"  # 0.001 <= 0.001 is True

    def test_series_input_iloc_2(self):
        """Test with pandas Series."""
        # Arrange
        pvals = pd.Series([0.001, 0.02, 0.08])
        # Act
        result = p2stars(pvals)
        # Assert
        assert result.iloc[1] == "*"

    def test_series_input_ns_iloc(self):
        """Test with pandas Series."""
        # Arrange
        pvals = pd.Series([0.001, 0.02, 0.08])
        # Act
        result = p2stars(pvals)
        # Assert
        assert result.iloc[2] == "ns"

    def test_dataframe_input_series(self):
        """Test with pandas DataFrame."""
        # Arrange
        df = pd.DataFrame({"pvalue": [0.001, 0.05, 0.15]})
        # Act
        result = p2stars(df["pvalue"])
        # Assert
        assert isinstance(result, pd.Series)

    def test_dataframe_input_case_2(self):
        """Test with pandas DataFrame."""
        # Arrange
        df = pd.DataFrame({"pvalue": [0.001, 0.05, 0.15]})
        # Act
        result = p2stars(df["pvalue"])
        # Assert
        assert len(result) == 3

    def test_custom_thresholds_stars(self):
        """Test with custom thresholds."""
        # Arrange
        # Act
        stars = p2stars(
            0.005,  # 0.005 < 0.001 is False, 0.005 < 0.01 is True → '**'
            thresholds=(0.0001, 0.001, 0.01),
            symbols=("****", "***", "**", "ns"),
        )
        # Assert
        assert stars == "**"

    def test_invalid_pvalue_case_1(self):
        """Test with invalid p-value (should warn but not crash)."""
        # Arrange
        # Act
        result = p2stars(-0.1)
        # Assert
        assert result == "invalid"
        result = p2stars(1.5)

    def test_invalid_pvalue_case_2(self):
        """Test with invalid p-value (should warn but not crash)."""
        # Arrange
        result = p2stars(-0.1)
        # Act
        result = p2stars(1.5)
        # Assert
        assert result == "invalid"

    def test_nan_pvalue_case(self):
        """Test with NaN p-value."""
        # Arrange
        # Act
        result = p2stars(np.nan)
        # Assert
        assert result == "NaN"

    def test_invalid_threshold_order(self):
        """Test error with unordered thresholds."""
        # Arrange
        # Act
        # Assert
        with pytest.raises(ValueError, match="ascending order"):
            p2stars(0.05, thresholds=(0.05, 0.01, 0.001))

    def test_invalid_symbols_length(self):
        """Test error with wrong number of symbols."""
        # Arrange
        # Act
        # Assert
        with pytest.raises(ValueError, match="one more than thresholds"):
            p2stars(0.05, thresholds=(0.001, 0.01, 0.05), symbols=("***", "**"))


class TestP2starsScalar:
    """Test _p2stars_scalar helper function."""

    def test_scalar_basic_p2stars_scalar_thresholds_symbols(self):
        """Test basic scalar conversion."""
        # Arrange
        thresholds = (0.001, 0.01, 0.05)
        symbols = ("***", "**", "*", "ns")
        # Act
        # Assert
        assert _p2stars_scalar(0.0001, thresholds, symbols, True) == "***"

    def test_scalar_basic_p2stars_scalar_thresholds_symbols_2(self):
        """Test basic scalar conversion."""
        # Arrange
        thresholds = (0.001, 0.01, 0.05)
        symbols = ("***", "**", "*", "ns")
        # Act
        # Assert
        assert _p2stars_scalar(0.005, thresholds, symbols, True) == "**"

    def test_scalar_basic_p2stars_scalar_thresholds_symbols_3(self):
        """Test basic scalar conversion."""
        # Arrange
        thresholds = (0.001, 0.01, 0.05)
        symbols = ("***", "**", "*", "ns")
        # Act
        # Assert
        assert _p2stars_scalar(0.02, thresholds, symbols, True) == "*"

    def test_scalar_basic_ns_p2stars_scalar_thresholds_symbols(self):
        """Test basic scalar conversion."""
        # Arrange
        thresholds = (0.001, 0.01, 0.05)
        symbols = ("***", "**", "*", "ns")
        # Act
        # Assert
        assert _p2stars_scalar(0.1, thresholds, symbols, True) == "ns"

    def test_scalar_no_ns(self):
        """Test scalar without ns."""
        # Arrange
        thresholds = (0.001, 0.01, 0.05)
        symbols = ("***", "**", "*", "")
        # Act
        # Assert
        assert _p2stars_scalar(0.1, thresholds, symbols, False) == ""


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: /home/ywatanabe/proj/scitex-code/src/scitex/stats/utils/_formatters.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # Timestamp: "2025-10-01 14:45:00 (ywatanabe)"
# # File: /home/ywatanabe/proj/scitex_repo/src/scitex/stats/utils/_formatters.py
#
# """
# Functionalities:
#   - Convert p-values to significance stars for scientific reporting
#   - Format p-values according to publication standards
#   - Support pandas DataFrames and numpy arrays
#
# Dependencies:
#   - packages: numpy, pandas
#
# IO:
#   - input: p-values (float, array, or DataFrame)
#   - output: formatted strings with significance indicators
# """
#
# """Imports"""
# import sys
# import argparse
# import numpy as np
# import pandas as pd
# from typing import Union
# import scitex as stx
# from scitex.logging import getLogger
#
# logger = getLogger(__name__)
#
# """Functions"""
#
#
# def p2stars(
#     pvalue: Union[float, np.ndarray, pd.Series, pd.DataFrame],
#     thresholds: tuple = (0.001, 0.01, 0.05),
#     symbols: tuple = ("***", "**", "*", "ns"),
#     ns_symbol: bool = True,
# ) -> Union[str, np.ndarray, pd.Series, pd.DataFrame]:
#     """
#     Convert p-values to significance stars.
#
#     Parameters
#     ----------
#     pvalue : float, array, Series, or DataFrame
#         P-value(s) to convert to stars
#     thresholds : tuple of float, default (0.001, 0.01, 0.05)
#         Significance thresholds (must be in ascending order)
#     symbols : tuple of str, default ('***', '**', '*', 'ns')
#         Symbols for each threshold level
#         Length must be len(thresholds) + 1
#     ns_symbol : bool, default True
#         Whether to include 'ns' for non-significant results
#         If False, returns empty string for non-significant
#
#     Returns
#     -------
#     str, array, Series, or DataFrame
#         Significance symbols matching input type
#
#     Notes
#     -----
#     Default thresholds and symbols:
#     - p < 0.001: '***' (highly significant)
#     - p < 0.01:  '**'  (very significant)
#     - p < 0.05:  '*'   (significant)
#     - p >= 0.05: 'ns'  (not significant)
#
#     Examples
#     --------
#     >>> p2stars(0.001)
#     '***'
#
#     >>> p2stars(0.023)
#     '*'
#
#     >>> p2stars(0.15)
#     'ns'
#
#     >>> p2stars(0.15, ns_symbol=False)
#     ''
#
#     >>> # Works with arrays
#     >>> pvals = np.array([0.0001, 0.005, 0.045, 0.15])
#     >>> p2stars(pvals)
#     array(['***', '**', '*', 'ns'], dtype='<U3')
#
#     >>> # Works with DataFrames
#     >>> df = pd.DataFrame({'pvalue': [0.001, 0.05, 0.15]})
#     >>> df['pstars'] = p2stars(df['pvalue'])
#     """
#     # Validate inputs
#     if len(symbols) != len(thresholds) + 1:
#         raise ValueError(
#             f"symbols must have {len(thresholds) + 1} elements "
#             f"(one more than thresholds)"
#         )
#
#     if not all(thresholds[i] < thresholds[i + 1] for i in range(len(thresholds) - 1)):
#         raise ValueError("thresholds must be in ascending order")
#
#     # Handle different input types
#     if isinstance(pvalue, (pd.DataFrame, pd.Series)):
#         # Apply to DataFrame/Series
#         return pvalue.apply(
#             lambda p: _p2stars_scalar(p, thresholds, symbols, ns_symbol)
#         )
#     elif isinstance(pvalue, np.ndarray):
#         # Vectorized for numpy arrays
#         return np.vectorize(
#             lambda p: _p2stars_scalar(p, thresholds, symbols, ns_symbol)
#         )(pvalue)
#     else:
#         # Single value
#         return _p2stars_scalar(pvalue, thresholds, symbols, ns_symbol)
#
#
# def _p2stars_scalar(
#     pvalue: float, thresholds: tuple, symbols: tuple, ns_symbol: bool
# ) -> str:
#     """Convert single p-value to stars (internal function)."""
#     # Handle NaN
#     if pd.isna(pvalue):
#         return "NaN"
#
#     # Handle invalid p-values
#     if pvalue < 0 or pvalue > 1:
#         logger.warning(f"Invalid p-value: {pvalue}. Should be between 0 and 1.")
#         return "invalid"
#
#     # Find appropriate symbol (use <= to include boundary values)
#     for i, threshold in enumerate(thresholds):
#         if pvalue <= threshold:
#             return symbols[i]
#
#     # Non-significant
#     return symbols[-1] if ns_symbol else ""
#
#
# """Main function"""
#
#
# def main(args):
#     """Demonstrate p2stars functionality."""
#     logger.info("Demonstrating p2stars functionality")
#
#     # Example 1: Single p-values
#     logger.info("\n=== Example 1: Single p-values ===")
#     test_pvalues = [0.0001, 0.005, 0.023, 0.049, 0.051, 0.15]
#
#     for p in test_pvalues:
#         stars = p2stars(p)
#         logger.info(f"p = {p:6.4f} → {stars:3s}")
#
#     # Example 2: Array of p-values
#     logger.info("\n=== Example 2: Array of p-values ===")
#     pvals_array = np.array([0.0001, 0.005, 0.023, 0.049, 0.051, 0.15])
#     stars_array = p2stars(pvals_array)
#
#     logger.info(f"P-values: {pvals_array}")
#     logger.info(f"Stars:    {stars_array}")
#
#     # Example 3: DataFrame
#     logger.info("\n=== Example 3: DataFrame ===")
#     df = pd.DataFrame(
#         {
#             "test": ["Test 1", "Test 2", "Test 3", "Test 4"],
#             "pvalue": [0.0001, 0.023, 0.051, 0.15],
#         }
#     )
#
#     df["pstars"] = p2stars(df["pvalue"])
#     logger.info(f"\n{df}")
#
#     # Example 4: Custom thresholds
#     logger.info("\n=== Example 4: Custom thresholds (more stringent) ===")
#     custom_stars = p2stars(
#         0.01, thresholds=(0.0001, 0.001, 0.01), symbols=("****", "***", "**", "ns")
#     )
#     logger.info(f"p = 0.01 with custom thresholds → {custom_stars}")
#
#     # Example 5: Without 'ns' symbol
#     logger.info("\n=== Example 5: Without 'ns' symbol ===")
#     for p in [0.001, 0.05, 0.15]:
#         stars = p2stars(p, ns_symbol=False)
#         logger.info(f"p = {p:6.4f} → '{stars}'")
#
#     # Create visualization
#     logger.info("\n=== Creating visualization ===")
#     fig, ax = stx.plt.subplots(figsize=(10, 6))
#
#     # Generate range of p-values
#     pvals = np.logspace(-4, 0, 100)  # 0.0001 to 1.0
#     stars = p2stars(pvals)
#
#     # Color map for stars
#     color_map = {"***": "red", "**": "orange", "*": "yellow", "ns": "lightgray"}
#     colors = [color_map.get(s, "gray") for s in stars]
#
#     # Plot
#     ax.scatter(pvals, range(len(pvals)), c=colors, alpha=0.6, s=50)
#     ax.set_xscale("log")
#     ax.set_xlabel("P-value")
#     ax.set_ylabel("Test index")
#     ax.set_title("P-value to Stars Conversion")
#
#     # Add vertical lines for thresholds
#     for threshold in [0.001, 0.01, 0.05]:
#         ax.axvline(threshold, color="black", linestyle="--", alpha=0.3)
#         ax.text(
#             threshold,
#             len(pvals) * 0.95,
#             f"{threshold}",
#             ha="center",
#             va="bottom",
#             fontsize=10,
#         )
#
#     # Add legend
#     from matplotlib.patches import Patch
#
#     legend_elements = [
#         Patch(facecolor="red", label="p < 0.001 (***)"),
#         Patch(facecolor="orange", label="p < 0.01 (**)"),
#         Patch(facecolor="yellow", label="p < 0.05 (*)"),
#         Patch(facecolor="lightgray", label="p ≥ 0.05 (ns)"),
#     ]
#     ax.legend(handles=legend_elements, loc="upper left")
#
#     # Save
#     stx.io.save(fig, "./p2stars_demo.jpg")
#     logger.info("Visualization saved")
#
#     return 0
#
#
# def parse_args():
#     """Parse command line arguments."""
#     parser = argparse.ArgumentParser(
#         description="Demonstrate p-value to stars conversion"
#     )
#     parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
#     return parser.parse_args()
#
#
# def run_main():
#     """Initialize SciTeX framework and run main."""
#     global CONFIG, sys, plt, rng
#
#     import sys
#     import matplotlib.pyplot as plt
#
#     args = parse_args()
#
#     CONFIG, sys.stdout, sys.stderr, plt, CC, rng = stx.session.start(
#         sys,
#         plt,
#         args=args,
#         file=__file__,
#         verbose=args.verbose,
#         agg=True,
#     )
#
#     exit_status = main(args)
#
#     stx.session.close(
#         CONFIG,
#         verbose=args.verbose,
#         exit_status=exit_status,
#     )
#
#
# if __name__ == "__main__":
#     run_main()
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: /home/ywatanabe/proj/scitex-code/src/scitex/stats/utils/_formatters.py
# --------------------------------------------------------------------------------
