"""Shared pytest fixtures."""

import pytest


@pytest.fixture
def clean_converter_registry():
    """Snapshot/restore the global converter registry for test isolation."""
    from kliamka._converters import _CONVERTERS

    snapshot = dict(_CONVERTERS)
    try:
        yield
    finally:
        _CONVERTERS.clear()
        _CONVERTERS.update(snapshot)
