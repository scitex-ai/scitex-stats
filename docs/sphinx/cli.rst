CLI Reference
=============

SciTeX Stats exposes the owning leaf command line through ``scitex-stats``.
Inspect the installed interface before choosing commands:

.. code-block:: bash

   scitex-stats --help
   scitex-stats --help-recursive
   scitex-stats tests --help

Tests and verification
----------------------

.. code-block:: bash

   scitex-stats tests list
   scitex-stats tests execute ttest_ind data.csv --x group_a --y group_b
   scitex-stats tests describe data.csv -c group_a
   scitex-stats tests recommend --n-groups 2 --sample-sizes 30,28
   scitex-stats verify result.json

Save an execution result as JSON before passing its path to ``verify``.
Verification exits 0 only when verified and 1 otherwise. Full-report
recomputation also needs ``--source-result original-result.json``.

Bundled references
------------------

The leaf-owned skills provide the command inventory and a complete synthetic
CSV workflow, including fixture data and result verification:

.. code-block:: bash

   scitex-stats skills get 04_cli-reference
   scitex-stats skills get 12_cli-reference
   scitex-stats skills get 17_provenance-verify

MCP discovery and launch preview
--------------------------------

.. code-block:: bash

   scitex-stats mcp list-tools -vv
   scitex-stats mcp start --dry-run
   scitex-stats mcp start --transport sse --dry-run

The CLI accepts ``stdio`` and ``sse`` transports. Launch previews do not start
a server or establish client connectivity. Use the bundled command references
and installed help for the remaining GUI, report, APA validation,
introspection and skill commands.
