"""Canonical MCP test names shared by execution and schema metadata."""

_TEST_DISPATCH = {
    # Parametric tests
    "ttest_ind": ("parametric", "test_ttest_ind"),
    "ttest_paired": ("parametric", "test_ttest_rel"),
    "ttest_1samp": ("parametric", "test_ttest_1samp"),
    "anova": ("parametric", "test_anova"),
    "anova_rm": ("parametric", "test_anova_rm"),
    "anova_2way": ("parametric", "test_anova_2way"),
    # Nonparametric tests
    "brunner_munzel": ("nonparametric", "test_brunner_munzel"),
    "mannwhitneyu": ("nonparametric", "test_mannwhitneyu"),
    "wilcoxon": ("nonparametric", "test_wilcoxon"),
    "kruskal": ("nonparametric", "test_kruskal"),
    "friedman": ("nonparametric", "test_friedman"),
    # Correlation tests
    "pearson": ("correlation", "test_pearson"),
    "spearman": ("correlation", "test_spearman"),
    "kendall": ("correlation", "test_kendall"),
    "theilsen": ("correlation", "test_theilsen"),
    # Categorical tests
    "chi2": ("categorical", "test_chi2"),
    "fisher_exact": ("categorical", "test_fisher"),
    "mcnemar": ("categorical", "test_mcnemar"),
    "cochran_q": ("categorical", "test_cochran_q"),
    # Normality tests
    "shapiro": ("normality", "test_shapiro"),
    "normality": ("normality", "test_normality"),
    "ks_1samp": ("normality", "test_ks_1samp"),
    "ks_2samp": ("normality", "test_ks_2samp"),
}
