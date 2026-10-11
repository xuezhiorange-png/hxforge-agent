"""Regression guards for TASK173 sizing performance recovery (execution-only)."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.task173_integrated_rating import service
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    TASK173_COOLPROP_CACHE_SIZE,
)
from hexagent.properties.coolprop_provider import CoolPropProvider


def test_mesh_sequence_provider_factory_reuses_default_instance() -> None:
    factory = service._mesh_sequence_provider_factory(None)
    first = factory()
    second = factory()
    assert first is second
    assert isinstance(first, CoolPropProvider)
    assert first.cache_size == TASK173_COOLPROP_CACHE_SIZE


def test_mesh_sequence_provider_factory_honors_injected_provider() -> None:
    injected = CoolPropProvider(cache_size=64)
    factory = service._mesh_sequence_provider_factory(injected)
    assert factory() is injected
