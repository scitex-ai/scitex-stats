"""Partial leaf-owned declarations for existing core Python/MCP operations.

The selected scope covers native/MCP adapters. Remaining public APIs and MCP
tools need classification. These plain data describe interface bindings;
implementation tests, installed registration and host availability are separate.
"""


def get_capabilities() -> dict:
    """Return fresh version-one core-operation declarations without Dev imports."""
    operations = (
        ("normality_test", "Test a numeric sample for normality with a supported method.",
         "tests/integration/test_normality_python_api.py"),
        ("effect_size", "Compute a supported two-group effect size with supported pooling.",
         "tests/integration/test_effect_size_python_api.py"),
        ("format_results", "Format a statistical result in a supported publication style.",
         "tests/integration/test_format_results_python_api.py"),
        ("correct_pvalues", "Adjust a family of p-values with a supported correction method.",
         "tests/integration/test_correction_python_api.py"),
        ("check_applicability", "Assess supported tests and their assumptions for grouped data.",
         "tests/integration/test_recommendation_mcp_threading.py"),
        ("recommend_test", "Recommend a primary test from the design and data assumptions.",
         "tests/integration/test_recommendation_mcp_threading.py"),
        ("run_all_applicable", "Run a primary test and applicable sensitivity analyses.",
         "tests/integration/test_recommendation_mcp_threading.py"),
        ("validate_apa", "Validate statistical text and HTML against the native APA reporting rules.",
         "tests/integration/test_apa_mcp_threading.py"),
        ("verify", "Verify result receipts, inputs and recomputation with native default options.",
         "tests/integration/test_verify_python_mcp.py"),
    )
    mcp_names = {"verify": "verify_result"}
    return {
        "schema_version": 1,
        "distribution": "scitex-stats",
        "provider": "core-operations",
        "capabilities": [
            {"name": name, "purpose": purpose,
             "python": [f"scitex_stats.{name}"], "mcp": [mcp_names.get(name, name)],
             "test_references": [reference]}
            for name, purpose, reference in operations
        ],
    }
