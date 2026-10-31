"""Run-scoped exact TP cache for experimental Task173 mesh (MVP only)."""

# ruff: noqa: E501

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from hexagent.properties.base import FluidIdentifier, FluidState
from hexagent.properties.coolprop_provider import _COOLPROP_STATE_LOCK, CoolPropProvider


def _tp_key(
    fluid: FluidIdentifier | str, temperature_k: float, pressure_pa: float
) -> tuple[Any, ...]:
    if isinstance(fluid, FluidIdentifier):
        fluid_key = (
            fluid.name,
            fluid.equation_of_state_backend,
            fluid.components,
        )
    else:
        fluid_key = ("str", fluid)
    return (
        fluid_key,
        struct.pack("!d", float(temperature_k)),
        struct.pack("!d", float(pressure_pa)),
    )


def _fluid_name_from_key(key: tuple[Any, ...]) -> str:
    fluid_key = key[0]
    if isinstance(fluid_key, tuple) and fluid_key and fluid_key[0] != "str":
        return str(fluid_key[0])
    if isinstance(fluid_key, tuple) and len(fluid_key) >= 2 and fluid_key[0] == "str":
        return str(fluid_key[1])
    return "Water"


@dataclass
class EphemeralTpCacheStats:
    provider_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    unique_keys: int = 0
    configuration_verifications: int = 0
    _keys_seen: set[tuple[Any, ...]] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        duplicate_calls = self.provider_calls - self.unique_keys
        duplicate_rate = duplicate_calls / self.provider_calls if self.provider_calls > 0 else 0.0
        return {
            "provider_calls": self.provider_calls,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "unique_tp_keys": self.unique_keys,
            "exact_duplicate_tp_queries": duplicate_calls,
            "exact_duplicate_rate": duplicate_rate,
            "configuration_verifications": self.configuration_verifications,
        }


def _verify_provider_configuration(provider: CoolPropProvider, fluid_name: str) -> str:
    with _COOLPROP_STATE_LOCK:
        return provider._verify_configuration(fluid_name)


def install_ephemeral_tp_cache(
    provider: CoolPropProvider,
) -> tuple[EphemeralTpCacheStats, dict[tuple[Any, ...], FluidState]]:
    """Bind exact-key cache on provider.state_tp; preserves CoolPropProvider identity.

    Cache hits re-run the native configuration and DEF reference-state checks before
    returning a cached FluidState. If configuration drift is detected, the native
    provider fails closed (same as an uncached query).
    """
    stats = EphemeralTpCacheStats()
    store: dict[tuple[Any, ...], FluidState] = {}
    original_state_tp = provider.state_tp

    def cached_state_tp(
        fluid: FluidIdentifier | str,
        temperature_k: float,
        pressure_pa: float,
    ) -> FluidState:
        key = _tp_key(fluid, temperature_k, pressure_pa)
        stats.provider_calls += 1
        if key not in stats._keys_seen:
            stats._keys_seen.add(key)
            stats.unique_keys = len(stats._keys_seen)
        fluid_name = _fluid_name_from_key(key)
        _verify_provider_configuration(provider, fluid_name)
        stats.configuration_verifications += 1
        if key in store:
            stats.cache_hits += 1
            return store[key]
        stats.cache_misses += 1
        state = original_state_tp(fluid, temperature_k, pressure_pa)
        store[key] = state
        return state

    provider.state_tp = cached_state_tp  # type: ignore[method-assign]
    return stats, store
