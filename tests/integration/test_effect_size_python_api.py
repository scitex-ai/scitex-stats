"""Native effect-size values, exceptions and MCP adapter parity."""

import asyncio
import inspect

import pytest
import scitex_stats as ss


def test_python_effect_size_returns_the_cohens_d_reference_value():
    # Arrange: mean difference=-2 and pooled variance=2.5.
    group1, group2 = [1.0, 2.0, 3.0], [2.0, 4.0, 6.0]
    # Act
    result = ss.effect_size(group1=group1, group2=group2)
    # Assert
    assert (inspect.iscoroutinefunction(ss.effect_size), isinstance(result, dict),
            set(result) & {"success", "timestamp"}, result["value"],
            result["group1_n"], result["group2_n"]) == (
                False, True, set(), pytest.approx(-1.2649110640673518), 3, 3,
            )


@pytest.mark.parametrize("measure", ["cohens_d", "hedges_g", "glass_delta", "cliffs_delta"])
def test_python_effect_size_refuses_unsupported_pooling(measure):
    # Arrange: the native operation owns the same pooling constraint.
    group1, group2 = [1.0, 2.0, 3.0], [2.0, 4.0, 6.0]
    # Act
    # Assert
    with pytest.raises(ValueError, match="pooled=False is not supported"):
        ss.effect_size(group1=group1, group2=group2, measure=measure, pooled=False)


def test_python_effect_size_refuses_an_unknown_measure():
    # Arrange
    group1, group2 = [1.0, 2.0, 3.0], [2.0, 4.0, 6.0]
    # Act
    # Assert
    with pytest.raises(ValueError, match="Unknown measure: made_up"):
        ss.effect_size(group1=group1, group2=group2, measure="made_up")


@pytest.mark.parametrize("measure", ["cohens_d", "hedges_g", "glass_delta", "cliffs_delta"])
def test_effect_size_mcp_payload_equals_the_native_python_result(measure):
    # Arrange
    from scitex_stats._mcp._handlers._effect_size import effect_size_handler

    group1, group2 = [1.0, 2.0, 3.0, 4.0], [2.0, 4.0, 8.0, 16.0]
    expected = ss.effect_size(group1=group1, group2=group2, measure=measure)
    # Act
    result = asyncio.run(effect_size_handler(group1=group1, group2=group2, measure=measure))
    payload = {key: value for key, value in result.items() if key not in {"success", "timestamp"}}
    # Assert
    assert (result["success"], payload) == (True, expected)


def test_effect_size_mcp_delegates_all_arguments_to_the_public_api(monkeypatch):
    # Arrange
    from scitex_stats._mcp._handlers._effect_size import effect_size_handler

    calls = []

    def native(group1, group2, measure, pooled):
        calls.append((group1, group2, measure, pooled))
        return {"native_sentinel": 23}

    monkeypatch.setattr(ss, "effect_size", native)
    # Act
    result = asyncio.run(effect_size_handler(group1=[1.0], group2=[2.0], measure="cliffs_delta"))
    # Assert
    assert (calls, result["success"], result.get("native_sentinel")) == (
        [([1.0], [2.0], "cliffs_delta", True)], True, 23,
    )
