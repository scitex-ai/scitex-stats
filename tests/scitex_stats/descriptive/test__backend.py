"""Backend recognition preserves real tensors without eager optional imports."""

import numpy as np

from scitex_stats.descriptive._backend import get_torch_backend, is_torch_tensor


def test_numpy_array_is_not_a_tensor():
    # Arrange
    value = np.array([1.0])
    # Act
    detected = is_torch_tensor(value)
    # Assert
    assert detected is False


def test_loaded_tensor_is_recognized():
    # Arrange
    import torch

    value = torch.tensor([1.0])
    # Act
    detected = is_torch_tensor(value)
    # Assert
    assert detected is True


def test_tensor_subclass_is_recognized():
    # Arrange
    import torch

    class CustomTensor(torch.Tensor):
        pass

    value = torch.tensor([1.0]).as_subclass(CustomTensor)
    # Act
    detected = is_torch_tensor(value)
    # Assert
    assert detected is True


def test_python_list_is_not_a_tensor():
    # Arrange
    value = [1.0, 2.0]
    # Act
    detected = is_torch_tensor(value)
    # Assert
    assert detected is False


def test_requested_backend_is_the_actual_loaded_torch_module():
    # Arrange
    import torch

    # Act
    backend = get_torch_backend()
    # Assert
    assert backend is torch
