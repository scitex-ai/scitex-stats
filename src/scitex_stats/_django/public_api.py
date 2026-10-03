"""Leaf-owned compatibility views for the existing public Statistics API.

The recommendation callable preserves the public Hub 0fe90e4 interface.
It is separate from the calculator's current GUI recommendation protocol.
API discovery and host activation remain the generic consumer's responsibility.
"""

import json

import scitex_logging as slogging

try:
    from django.http import JsonResponse
    from django.views.decorators.csrf import csrf_exempt
    from django.views.decorators.http import require_POST
except ImportError as error:
    raise ImportError(
        "scitex_stats._django.public_api needs Django. "
        "Install the optional stack: pip install 'scitex-stats[server]'"
    ) from error

logger = slogging.getLogger("scitex")


def run_recommend(body: dict) -> dict:
    """Delegate the existing public parameters without coercion or new defaults."""
    import scitex as stx

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


@csrf_exempt
@require_POST
def stats_recommend(request, editor=None) -> JsonResponse:
    """Preserve the stateless, anonymous, JSON-only public recommendation view."""
    try:
        body = json.loads(request.body)
        try:
            import scitex  # noqa: F401
        except ImportError as error:
            logger.error("Failed to import scitex: %s", error)
            return JsonResponse(
                {"success": False, "error": "scitex package not available"}, status=503
            )
        result = run_recommend(body)
        return JsonResponse({"success": True, "recommendations": result["recommendations"]})
    except Exception as error:
        logger.error("Error in stats_recommend: %s", error, exc_info=True)
        return JsonResponse({"success": False, "error": str(error)}, status=500)
