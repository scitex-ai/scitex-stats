"""Observe real native calls without substituting implementations."""

from contextlib import contextmanager
import threading

import pytest


@pytest.fixture
def observe_native():
    """Record arguments of an actual operation running in an executor thread."""
    @contextmanager
    def observe(operation):
        calls = []
        previous = threading.getprofile()

        def profile(frame, event, arg):
            if event == "call" and frame.f_code is operation.__code__:
                calls.append(dict(frame.f_locals))
            if previous is not None:
                previous(frame, event, arg)

        threading.setprofile(profile)
        try:
            yield calls
        finally:
            threading.setprofile(previous)

    return observe
