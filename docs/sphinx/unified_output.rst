Unified Output Format
=====================

Every test in SciTeX Stats returns a **unified result dictionary** with consistent
keys. This means you can write generic code that works with any test output.

Result Dictionary
-----------------

.. code-block:: json

   {
     "test_method": "Student's t-test (independent)",
     "statistic": -3.210,
     "stat_symbol": "t",
     "alternative": "two-sided",
     "n_x": 30,
     "n_y": 30,
     "pvalue": 0.0022,
     "stars": "**",
     "alpha": 0.05,
     "significant": true,
     "effect_size": -0.829,
     "effect_size_metric": "Cohen's d",
     "effect_size_interpretation": "large",
     "power": 0.884,
     "H0": "μ(x) = μ(y)",
     "formatted": "t = -3.210, p = 0.0022, Cohen's d = -0.829, **"
   }

Key Fields
----------

.. list-table:: **Table 1.** Unified result dictionary keys. All 25 tests return these fields (with test-specific additions where appropriate).
   :header-rows: 1
   :widths: 25 15 60

   * - Key
     - Type
     - Description
   * - ``test_method``
     - str
     - Human-readable test name
   * - ``statistic``
     - float
     - Test statistic value
   * - ``stat_symbol``
     - str
     - Symbol for the statistic (t, F, U, W, χ², r, ρ)
   * - ``pvalue``
     - float
     - p-value
   * - ``stars``
     - str
     - Significance stars: ``***`` (p<0.001), ``**`` (p<0.01), ``*`` (p<0.05), ``ns``
   * - ``alpha``
     - float
     - Significance level (default 0.05)
   * - ``significant``
     - bool
     - Whether to reject H0
   * - ``effect_size``
     - float
     - Effect size value
   * - ``effect_size_metric``
     - str
     - Which metric (Cohen's d, eta², Cramér's V, r, ρ, etc.)
   * - ``effect_size_interpretation``
     - str
     - Magnitude: negligible, small, medium, or large
   * - ``power``
     - float
     - Statistical power (when calculable)
   * - ``H0``
     - str
     - Null hypothesis in plain text
   * - ``formatted``
     - str
     - APA-style formatted string, ready for publication

Null Hypotheses
---------------

Every test now includes ``H0``, the null hypothesis in plain language:

.. list-table:: **Table 2.** Null hypotheses for all test families.
   :header-rows: 1
   :widths: 30 70

   * - Test
     - H0
   * - t-test (independent)
     - μ(x) = μ(y)
   * - t-test (paired)
     - μ(before - after) = 0
   * - t-test (1-sample)
     - μ(sample) = 0
   * - Mann-Whitney U
     - Distributions of x and y have equal medians
   * - Wilcoxon signed-rank
     - median(before - after) = 0
   * - Brunner-Munzel
     - P(x > y) = 0.5
   * - ANOVA
     - All groups have equal population means
   * - Kruskal-Wallis
     - All groups have the same population median
   * - Friedman
     - All conditions have the same distribution
   * - Pearson
     - No linear correlation between x and y
   * - Spearman
     - No monotonic correlation between x and y
   * - Kendall
     - No monotonic association between x and y
   * - Shapiro-Wilk
     - Data are normally distributed
   * - Chi-squared
     - Two variables are independent
   * - Fisher's exact
     - Two variables are independent (OR = 1)
   * - McNemar
     - Marginal proportions are equal (no change)

Significance Stars
------------------

The ``stars`` field follows the standard convention:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Stars
     - p-value range
     - Interpretation
   * - ``***``
     - p < 0.001
     - Highly significant
   * - ``**``
     - p < 0.01
     - Very significant
   * - ``*``
     - p < 0.05
     - Significant
   * - ``ns``
     - p >= 0.05
     - Not significant

Working with Results
--------------------

.. code-block:: python

   import scitex_stats as ss

   result = ss.run_test("ttest_ind", data=group1, data2=group2)

   # Quick report
   print(result["formatted"])

   # Programmatic access
   if result["significant"]:
       print(f"Reject H0: {result['H0']}")
       print(f"Effect: {result['effect_size_interpretation']}")

   # Convert to significance stars
   stars = ss.p_to_stars(0.003)  # "**"
