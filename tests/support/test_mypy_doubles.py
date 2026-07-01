"""Mypy authority tests for typed PropertyProvider doubles.

These tests prove structural PropertyProvider compatibility.
They are designed to be caught by mypy, not by runtime assertions.
"""

from __future__ import annotations

from typing import assert_type

import pytest

from hexagent.properties.base import PropertyProvider
from tests.support.property_provider_doubles import (
    CountingPropertyProvider,
    ReplayPropertyProvider,
    SelectiveFailurePropertyProvider,
    StubPropertyProvider,
)

pytestmark = [pytest.mark.pure]


def test_stub_is_property_provider() -> None:
    provider: PropertyProvider = StubPropertyProvider()
    assert_type(provider, PropertyProvider)


def test_replay_is_property_provider() -> None:
    provider: PropertyProvider = ReplayPropertyProvider()
    assert_type(provider, PropertyProvider)


def test_selective_failure_is_property_provider() -> None:
    provider: PropertyProvider = SelectiveFailurePropertyProvider(StubPropertyProvider(), {})
    assert_type(provider, PropertyProvider)


def test_counting_is_property_provider() -> None:
    provider: PropertyProvider = CountingPropertyProvider(StubPropertyProvider())
    assert_type(provider, PropertyProvider)
