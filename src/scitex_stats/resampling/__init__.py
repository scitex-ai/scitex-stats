#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resampling and confidence-interval utilities.

Analytic and resampling-based intervals for metrics that the test suite in
``scitex_stats.tests`` does not cover, notably classifier discrimination:

- ``auc_ci``: CI for a single ROC-AUC (DeLong or stratified bootstrap)
- ``delta_auc_ci``: CI and test for the difference of two CORRELATED AUCs
  measured on the same samples (the paired model-comparison case)
- ``bootstrap_ci``: generic percentile-bootstrap CI for any metric

The DeLong estimators use the fast Sun & Xu (2014) midrank algorithm and
depend on numpy only (DeLong et al., 1988).
"""

from ._auc_ci import auc_ci
from ._bootstrap_ci import bootstrap_ci
from ._delong_core import compute_midrank, delong_covariance
from ._delta_auc_ci import delta_auc_ci

__all__ = [
    "auc_ci",
    "delta_auc_ci",
    "bootstrap_ci",
    "delong_covariance",
    "compute_midrank",
]

# EOF
