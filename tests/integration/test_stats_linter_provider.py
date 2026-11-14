"""Stats linter advice resolves and runs through the owning leaf API."""

import ast
from importlib import metadata
from pathlib import Path
import re

import pytest
from scipy import stats

import scitex_stats as ss
from scitex_stats import _linter_plugin

X = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0]
Y = [0.0, 1.0, 3.0, 6.0, 10.0, 11.0]
Z = [2.0, 4.0, 5.0, 9.0, 13.0, 21.0]
CASES = [
    ("STX-ST001", "test_ttest_ind", "ttest_ind", (X, Y), (X, Y)),
    ("STX-ST002", "test_mannwhitneyu", "mannwhitneyu", (X, Y), (X, Y)),
    ("STX-ST003", "test_pearson", "pearsonr", (X, Y), (X, Y)),
    ("STX-ST004", "test_anova", "f_oneway", ([X, Y, Z],), (X, Y, Z)),
    ("STX-ST005", "test_wilcoxon", "wilcoxon", (X, Y), (X, Y)),
    ("STX-ST006", "test_kruskal", "kruskal", ([X, Y, Z],), (X, Y, Z)),
]


@pytest.fixture
def provider():
    return _linter_plugin.get_plugin()


@pytest.mark.parametrize("rule_id, target, scipy_name, native_args, scipy_args", CASES)
def test_documented_stats_rule_calls_execute_the_real_leaf_api(
    provider, rule_id, target, scipy_name, native_args, scipy_args
):
    # Arrange
    rule = next(rule for rule in provider["rules"] if rule.id == rule_id)
    expected = getattr(stats, scipy_name)(*scipy_args)
    expression = re.findall(r"`([^`]+\([^`]*\))`", rule.suggestion)[0]
    call = ast.parse(expression, mode="eval").body
    context = {"a": X, "b": Y, "x": X, "y": Y, "groups": [X, Y, Z]}
    # Act
    args = [context[arg.id] for arg in call.args]
    result = getattr(ss, call.func.attr)(*args)
    # Assert
    assert (getattr(call.func.value, "id", None), call.func.attr,
            result["statistic"], result["pvalue"]) == (
        "scitex_stats", target, pytest.approx(float(expected.statistic)),
        pytest.approx(float(expected.pvalue)),
    )


@pytest.mark.parametrize("rule_id, target, scipy_name, native_args, scipy_args", CASES)
def test_recommended_leaf_targets_exist_and_match_scipy_control(
    rule_id, target, scipy_name, native_args, scipy_args
):
    # Arrange
    expected = getattr(stats, scipy_name)(*scipy_args)
    # Act
    result = getattr(ss, target)(*native_args)
    # Assert
    assert (result["statistic"], result["pvalue"]) == (
        pytest.approx(float(expected.statistic)), pytest.approx(float(expected.pvalue)),
    )


def test_stats_provider_does_not_require_an_unrelated_umbrella_import(provider):
    # Arrange
    rules = provider["rules"]
    # Act
    gates = {rule.id: rule.requires for rule in rules}
    # Assert
    assert gates == {row[0]: "" for row in CASES}


def test_source_entry_point_loads_the_real_provider_through_dev():
    # Arrange: source metadata is not an installed-wheel acceptance claim.
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    from scitex_dev.linter._plugin_loader import load_plugins

    root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    group = "scitex_dev.linter.plugins"
    target = project["project"]["entry-points"][group]["stats"]
    point = metadata.EntryPoint(name="stats", value=target, group=group)
    logging = next(ep for ep in metadata.entry_points(group=group)
                   if ep.name == "scitex-logging")
    # Act
    payload = load_plugins(entry_points_iter=[logging, point].__iter__)
    # Assert
    assert ({row[0] for row in CASES} <= set(payload["rules"])
            and len([rule for rule in payload["call_rules"].values()
                     if rule.id.startswith("STX-ST")]) == 12)


def test_provider_description_matches_the_declared_entry_point_group():
    # Arrange
    group = "scitex_dev.linter.plugins"
    # Act
    description = _linter_plugin.__doc__
    # Assert
    assert group in description
