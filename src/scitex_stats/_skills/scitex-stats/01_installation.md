---
description: |
  [TOPIC] Installation
  [DETAILS] pip install standalone or umbrella, optional extras, verifying.
tags: [scitex-stats-installation, scitex-stats]
---


# Installation

## Standalone (recommended for stats-only workflows)

```bash
pip install scitex-stats
```

This exposes the package as `scitex_stats` (also importable as `scitex_stats`):

```python
import scitex_stats as sst
sst.run_test("ttest_ind", group1, group2)
```

`pip install scitex-stats` alone does **not** expose the umbrella `scitex`
namespace; `import scitex.stats` will raise `ModuleNotFoundError`.

## Umbrella (use with the rest of SciTeX)

```bash
pip install scitex          # also installs scitex-stats as a dep
```

Then either form works:

```python
import scitex.stats as sst   # umbrella form
import scitex_stats as sst   # standalone form (same module)
```

## Optional extras

```bash
pip install 'scitex-stats[server]'  # Statistics GUI app (django + scitex-app + scitex-ui)
pip install 'scitex-stats[dev]'     # test/lint tooling
```

## Verifying the install

```bash
scitex-stats --version
scitex-stats tests list --no-json | head
scitex-stats mcp doctor            # only if [mcp] extra is installed
```

## Python / dependency requirements

- Python ≥ 3.10
- `numpy`, `scipy`, `pandas`, `statsmodels` (installed automatically)

See [SKILL.md](SKILL.md) for the package overview and entry points.
