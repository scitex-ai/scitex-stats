MCP Server
==========

SciTeX Stats exposes its leaf-owned statistical operations through a Model
Context Protocol server. Install the package into the environment used by the
client:

.. code-block:: bash

   pip install scitex-stats

Discover the installed catalog
------------------------------

The registered server catalog owns tool names, descriptions and input schemas.
Read it instead of relying on a copied tool count:

.. code-block:: bash

   scitex-stats mcp list-tools -vv
   scitex-stats mcp list-tools --json -v
   scitex-stats skills get 13_mcp-tools

Verbose JSON adds a ``schemas`` map keyed by tool name. The CLI and native
``scitex_stats._mcp.tool_schemas.get_tool_schemas()`` use the same registered
metadata; discovery invokes no statistical tools. This is the default package
catalog, not authenticated discovery for a hosted user's session.

Standalone names include ``run_test``, ``verify_result`` and ``p_to_stars``.
A dispatcher may namespace mounted tools; use that dispatcher's own discovery
for the names available to its clients. The bundled MCP skill describes tool
contracts, numerical scope and links to their owning implementations/tests.

Start or preview the server
---------------------------

.. code-block:: bash

   scitex-stats mcp start --dry-run
   scitex-stats mcp start --transport sse --dry-run
   scitex-stats mcp start

The CLI accepts ``stdio`` (default) and ``sse``. The two previews return launch
plans without starting a server. The final command runs the stdio server until
its client closes the connection.

Stdio client configuration
--------------------------

Use the executable from the intended environment; it must be available to the
client through its PATH or an absolute path:

.. code-block:: json

   {
     "mcpServers": {
       "scitex-stats": {
         "command": "scitex-stats",
         "args": ["mcp", "start"]
       }
     }
   }

This configures a local stdio process. Each desktop client has its own config
location and reload procedure. A valid snippet or launch preview does not prove
that a desktop client or hosted service has connected.

Interpret results at the appropriate layer
-----------------------------------------

A request rejected by the published schema can return an MCP protocol error.
An admitted request can instead return a JSON handler payload with
``success: false`` and an error. For ``verify_result``, ``success: true`` means
the verification ran: ``verified`` can still be false. Inspect its checks
before reporting a result as verified. See the bundled provenance guide:

.. code-block:: bash

   scitex-stats skills get 17_provenance-verify

Diagnostics and scope
---------------------

.. code-block:: bash

   scitex-stats mcp doctor

The current doctor checks FastMCP availability, default catalog discovery and
whether ``scitex-stats`` is on PATH. It does not perform a client handshake or
execute a statistical tool, so it does not establish remote/hosted server
health or scientific validity.

Owning sources are ``_server.py``, ``_mcp/tool_schemas.py`` and ``_cli/mcp.py``.
Existing discovery controls live in
``tests/scitex_stats/_mcp/test_tool_schemas.py`` and
``tests/scitex_stats/_cli/test_mcp.py``; actual stdio behavior is covered by
``tests/integration/test_mcp_describe_stdio.py``. Rendering, desktop-client
adoption and hosted authentication require separate evidence.
