"""Tensor detection without importing an optional engine for NumPy inputs."""

from __future__ import annotations

import sys


def is_torch_tensor(value: object) -> bool:
    """Recognize tensors from an already loaded Torch engine, including subclasses.

    Constructing a Torch tensor requires its module to be loaded first. Looking
    it up avoids backend initialization during API discovery or NumPy use.
    """
    backend = sys.modules.get("torch")
    return backend is not None and isinstance(value, getattr(backend, "Tensor", ()))
