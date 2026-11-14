Public interface scope plan
===========================

This page is a maintainer plan. The MCP guide lists the registered tool names;
the migration candidates below are proposals. They are not additional commands
or runtime settings. Existing audit findings remain open until implementation
and qualification establish the intended contracts.

Choose the interface by the caller
----------------------------------

Python callers need numerical primitives, NumPy and pandas values, plotting
objects, and reusable formatting helpers. Keep these library operations
available through their owning modules. An exported Python name alone does not
justify another CLI command or MCP tool.

Use CLI and MCP operations for scientific workflows: select a test, run a named
test, describe data, calculate effects or power, correct p-values, format
results, produce a report, and verify a result receipt. The existing test
dispatcher can represent several numerical functions through a test-name
argument. Check every mapping against its owning implementation; shared names
and test families do not establish equivalent argument support or results.

Keep plotting-object adapters and return-format helpers in Python. A remote
operation needs an explicit serializable request and result before it can
expose those capabilities. GUI integration belongs to the leaf application
and SciTeX SDK. HTTP schemas and route admission belong to the SDK; a host
must enable a route before it is available over HTTP.

Keep the public catalogue small
-------------------------------

Group CLI workflows under the existing command tree. Delegate development
inspection and enforcement to scitex-dev. Do not generate commands from every
member of ``__all__`` or register separate tools for aliases of the same
operation. List skill discovery through the existing skills tools.

The leaf owns the capability mapping and the reason an operation belongs to a
particular interface. Dev should discover and validate those declarations;
the leaf owns statistical behavior and its executable checks. The current
name-based audit is still a required check. This plan adds no allowlist,
exemption, skip rule or replacement acceptance threshold.

Normalize names through a migration
-----------------------------------

Use a verb followed by its object for MCP operation names. Preserve registered
names while defining and testing the migration for existing clients.

.. list-table:: Initial naming candidates; none is registered by this plan.
   :header-rows: 1
   :widths: 25 30 45

   * - Current MCP name
     - Candidate
     - Work required first
   * - ``describe``
     - ``describe_data``
     - Define the descriptive-data contract and compatible client transition.
   * - ``effect_size``
     - ``calculate_effect_size``
     - Keep measure selection and pooling semantics consistent.
   * - ``normality_test``
     - ``test_normality``
     - Resolve the existing Python operation with that name and its different signature.
   * - ``power_analysis``
     - ``analyze_power``
     - Preserve achieved-power and sample-size calculation modes.
   * - ``posthoc_test``
     - ``run_posthoc``
     - Resolve the existing Python selector and qualify the named statistical methods.
   * - ``p_to_stars``
     - ``format_pvalue``
     - Compare the existing CLI formatter's arguments and result before aligning names.

Keep a documented compatibility period, qualify both routes, and remove an old
name only through a versioned release transition. Avoid publishing transport
wrappers as synchronous Python APIs merely to make name counts agree.

Acceptance work
---------------

1. Inventory current Python exports, registered MCP tools and CLI paths through
   existing Dev discovery. Distinguish aliases, primitives and workflow operations.
2. Bind each proposed workflow to a leaf-owned callable or dispatcher entry.
   Compare arguments, returned values, errors and file effects in executable tests.
3. Record interface-specific applicability with domain reasons and evidence.
   Qualify any shared policy-provider support before changing the generic audit.
4. Validate the migration with current and proposed clients. Keep package source,
   installed distribution, enabled host routes and live availability separate.

The MCP catalogue check in
``tests/integration/test_mcp_catalogue_documentation.py`` compares documented
names and the caption count with the server's registered tools. It does not
invoke statistical tools or establish numerical correctness, argument parity,
installed-wheel acceptance or hosted availability.
