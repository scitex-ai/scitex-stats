"""Tensor detection without importing an optional engine for NumPy inputs."""

from __future__ import annotations

import sys
from types import ModuleType


def is_torch_tensor(value: object) -> bool:
    """Recognize tensors from an already loaded Torch engine, including subclasses.

    Constructing a Torch tensor requires its module to be loaded first. Looking
    it up avoids backend initialization during API discovery or NumPy use.
    """
    backend = sys.modules.get("torch")
    return backend is not None and isinstance(value, getattr(backend, "Tensor", ()))


def get_torch_backend() -> ModuleType:
    """Load the optional engine only when a tensor operation requests it."""
    try:
        import torch
    except ImportError as exc:
        raise ImportError(
            "Torch tensor operations require torch; install scitex-stats[all]."
        ) from exc
    return torch
