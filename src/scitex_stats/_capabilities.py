"""Partial leaf-owned declarations for existing core Python/MCP operations.

The initial scope covers four existing adapters. Remaining public APIs and MCP
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
    )
    return {
        "schema_version": 1,
        "distribution": "scitex-stats",
        "provider": "core-operations",
        "capabilities": [
            {"name": name, "purpose": purpose,
             "python": [f"scitex_stats.{name}"], "mcp": [name],
             "test_references": [reference]}
            for name, purpose, reference in operations
        ],
    }
