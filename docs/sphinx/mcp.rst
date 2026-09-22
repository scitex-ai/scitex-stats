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

.. list-table:: **Table 1.** Ten MCP tools for AI-assisted statistical analysis. All tools accept JSON parameters and return JSON results.
   :header-rows: 1
   :widths: 25 75

   * - Tool
     - Description
   * - ``recommend_tests``
     - Recommend appropriate tests based on data characteristics
   * - ``run_test``
     - Execute a statistical test on provided data
   * - ``format_results``
     - Format results in journal style (APA, Nature, etc.)
   * - ``power_analysis``
     - Calculate statistical power or required sample size
   * - ``correct_pvalues``
     - Apply multiple comparison correction (FDR, Bonferroni, etc.)
   * - ``describe``
     - Calculate descriptive statistics
   * - ``effect_size``
     - Calculate effect size between groups
   * - ``normality_test``
     - Test whether data follows normal distribution
   * - ``posthoc_test``
     - Run post-hoc pairwise comparisons
   * - ``p_to_stars``
     - Convert p-value to significance stars

Diagnostics
-----------

.. code-block:: bash

   scitex-stats mcp doctor          # Check dependencies and server health
   scitex-stats mcp list-tools -vv  # List tools with descriptions
