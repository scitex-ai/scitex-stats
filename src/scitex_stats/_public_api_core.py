"""Private executor for the existing public Stats compatibility request.

No Django or SDK dependency is imported here. The historical optional
umbrella backend is resolved only when the executor is called.
"""


def run_recommend(body: dict) -> dict:
    """Delegate the existing public parameters without coercion or new defaults."""
    try:
        import scitex as stx
    except ImportError:
        raise

    context = stx.stats.StatContext(
        n_groups=body.get("n_groups", 2),
        sample_sizes=body.get("sample_sizes"),
        outcome_type=body.get("outcome_type", "continuous"),
        design=body.get("design", "between"),
        paired=body.get("paired", False),
        has_control_group=body.get("has_control_group", False),
    )
    recommendations = stx.stats.recommend_tests(context, top_k=body.get("top_k", 5))
    return {"recommendations": recommendations}
