MCP Server
==========

SciTeX Stats provides a `Model Context Protocol <https://modelcontextprotocol.io/>`_ (MCP)
server, enabling AI agents to run statistical tests and format publication-ready results
autonomously.

Installation
------------

.. code-block:: bash

   pip install scitex-stats

Starting the Server
-------------------

.. code-block:: bash

   scitex-stats mcp start

MCP Client Configuration
-------------------------

Add to your MCP client configuration (e.g., Claude Desktop, Cursor):

.. code-block:: json

   {
     "mcpServers": {
       "scitex-stats": {
         "command": "scitex-stats",
         "args": ["mcp", "start"]
       }
     }
   }

Available Tools
---------------

.. list-table:: **Table 1.** 18 registered MCP tools. Tools accept JSON parameters and return JSON results.
   :header-rows: 1
   :widths: 25 75

   * - Tool
     - Description
   * - ``recommend_tests``
     - Recommend tests from group counts, sample sizes and study design.
   * - ``check_applicability``
     - Check which tests apply to grouped data and the stated design.
   * - ``recommend_test``
     - Select a primary test from grouped data and the stated design.
   * - ``run_all_applicable``
     - Run analyses selected by the applicability checks.
   * - ``run_test``
     - Run one named test on arrays or selected columns from a data file.
   * - ``describe``
     - Calculate descriptive statistics for a numeric sequence.
   * - ``normality_test``
     - Run a normality test using the selected method.
   * - ``posthoc_test``
     - Run the selected post-hoc pairwise comparison procedure.
   * - ``effect_size``
     - Calculate an effect size between two groups.
   * - ``power_analysis``
     - Calculate achieved power or required sample size.
   * - ``correct_pvalues``
     - Apply multiple-comparison correction to p-values.
   * - ``format_results``
     - Format a statistical result in the requested journal style.
   * - ``p_to_stars``
     - Convert a p-value to significance stars.
   * - ``validate_apa``
     - Check statistical text, HTML or a result against APA rules.
   * - ``generate_report``
     - Generate a statistical report from grouped data or a data file.
   * - ``verify_result``
     - Check a result or result file against its provenance receipt.
   * - ``skills_list``
     - List discoverable Stats skills.
   * - ``skills_get``
     - Read a discoverable Stats skill.

Diagnostics
-----------

.. code-block:: bash

   scitex-stats mcp doctor          # Check dependencies and server health
   scitex-stats mcp list-tools -vv  # List tools with descriptions

The catalogue lists bare names registered by the standalone leaf server.
Client-qualified names and umbrella aliases depend on the configured server;
discover that server's actual tool list before using an alias. Standalone
registration does not establish that every alias is available in a facade.

The tool catalogue describes registered MCP names. Python library exports and
CLI command paths have their own signatures. Maintainers can find the proposed
exposure scopes and naming migrations in :doc:`interface_scope`.

The ``run_test`` input accepts the same equivalent spellings as the Python
dispatcher: ``ttest`` for ``ttest_ind``, ``ttest_rel`` for ``ttest_paired``,
``brunnermunzel`` for ``brunner_munzel``, ``mann_whitney`` for
``mannwhitneyu`` and ``fisher`` for ``fisher_exact``. Results and provenance
receipts retain the requested spelling.
These are test-name inputs to the existing tool.
