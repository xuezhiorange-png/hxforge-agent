"""Typed PropertyProvider test doubles for deterministic HXForge tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Literal, TypeAlias, cast

from hexagent.properties.base import (
    FluidIdentifier,
    FluidState,
    PropertyCacheInfo,
    PropertyProvider,
    PropertyQueryType,
    PropertyResult,
    ReferenceStatePolicy,
    SaturationState,
)

QueryTypeName: TypeAlias = Literal["TP", "PH", "SATURATION_P", "SATURATION_T"]
FailureKey: TypeAlias = tuple[PropertyQueryType, int]

_QUERY_TYPES: Final = tuple(PropertyQueryType)


class TestProviderError(RuntimeError):
    """Raised when a deterministic test double is misconfigured or exhausted."""


@dataclass(frozen=True, slots=True)
class ProviderQueryKey:
    """Canonical identity for one PropertyProvider request.

    Keys must be created through :meth:`from_request`; direct construction is an
    implementation detail and is intentionally not used by the public doubles API.
    """

    query_type: PropertyQueryType
    fluid_identity: str
    inputs: tuple[tuple[str, float], ...]
    reference_state: ReferenceStatePolicy | None = None

    @classmethod
    def from_request(
        cls,
        query_type: PropertyQueryType,
        fluid: FluidIdentifier | str,
        *,
        temperature_k: float | None = None,
        pressure_pa: float | None = None,
        enthalpy_j_kg: float | None = None,
        reference_state: ReferenceStatePolicy | None = None,
    ) -> ProviderQueryKey:
        """Build one canonical key from the exact provider request."""

        identity = canonical_fluid_identity(fluid)
        if query_type is PropertyQueryType.TP:
            _require_request_fields(
                query_type,
                required={"temperature_k": temperature_k, "pressure_pa": pressure_pa},
                prohibited={"enthalpy_j_kg": enthalpy_j_kg, "reference_state": reference_state},
            )
            return cls(
                query_type=query_type,
                fluid_identity=identity,
                inputs=(
                    ("pressure_pa", cast(float, pressure_pa)),
                    ("temperature_k", cast(float, temperature_k)),
                ),
            )
        if query_type is PropertyQueryType.PH:
            _require_request_fields(
                query_type,
                required={
                    "pressure_pa": pressure_pa,
                    "enthalpy_j_kg": enthalpy_j_kg,
                    "reference_state": reference_state,
                },
                prohibited={"temperature_k": temperature_k},
            )
            return cls(
                query_type=query_type,
                fluid_identity=identity,
                inputs=(
                    ("enthalpy_j_kg", cast(float, enthalpy_j_kg)),
                    ("pressure_pa", cast(float, pressure_pa)),
                ),
                reference_state=reference_state,
            )
        if query_type is PropertyQueryType.SATURATION_P:
            _require_request_fields(
                query_type,
                required={"pressure_pa": pressure_pa},
                prohibited={
                    "temperature_k": temperature_k,
                    "enthalpy_j_kg": enthalpy_j_kg,
                    "reference_state": reference_state,
                },
            )
            return cls(
                query_type=query_type,
                fluid_identity=identity,
                inputs=(("pressure_pa", cast(float, pressure_pa)),),
            )
        if query_type is PropertyQueryType.SATURATION_T:
            _require_request_fields(
                query_type,
                required={"temperature_k": temperature_k},
                prohibited={
                    "pressure_pa": pressure_pa,
                    "enthalpy_j_kg": enthalpy_j_kg,
                    "reference_state": reference_state,
                },
            )
            return cls(
                query_type=query_type,
                fluid_identity=identity,
                inputs=(("temperature_k", cast(float, temperature_k)),),
            )
        raise TestProviderError(f"unsupported query type: {query_type!r}")


def _require_request_fields(
    query_type: PropertyQueryType,
    *,
    required: Mapping[str, object | None],
    prohibited: Mapping[str, object | None],
) -> None:
    missing = sorted(name for name, value in required.items() if value is None)
    supplied = sorted(name for name, value in prohibited.items() if value is not None)
    if missing or supplied:
        raise TestProviderError(
            f"invalid {query_type.value} request; missing={missing!r}, prohibited={supplied!r}"
        )


def canonical_fluid_identity(fluid: FluidIdentifier | str) -> str:
    """Return the production canonical cache identity for a fluid request."""

    return FluidIdentifier.from_value(fluid).cache_identity


def _zero_cache_info() -> PropertyCacheInfo:
    return PropertyCacheInfo(hits=0, misses=0, size=0, max_size=0)


def _new_counter_map() -> dict[PropertyQueryType, int]:
    return {query_type: 0 for query_type in _QUERY_TYPES}


def _require_result_type(
    key: ProviderQueryKey, result: PropertyResult
) -> FluidState | SaturationState:
    if key.query_type in {PropertyQueryType.TP, PropertyQueryType.PH}:
        if not isinstance(result, FluidState):
            raise TestProviderError(
                f"{key.query_type.value} requires FluidState, got {type(result).__name__}"
            )
        return result
    if not isinstance(result, SaturationState):
        raise TestProviderError(
            f"{key.query_type.value} requires SaturationState, got {type(result).__name__}"
        )
    return result


class StubPropertyProvider:
    """Fixed-result provider keyed by canonical request identity."""

    name = "StubPropertyProvider"
    version = "1.0"
    git_revision = "test"
    reference_state_policy = ReferenceStatePolicy.DEF

    def __init__(self) -> None:
        self._results: dict[ProviderQueryKey, PropertyResult] = {}
        self.calls: list[ProviderQueryKey] = []

    def configure_tp(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
        pressure_pa: float,
        result: FluidState,
    ) -> None:
        self._configure(
            ProviderQueryKey.from_request(
                PropertyQueryType.TP,
                fluid,
                temperature_k=temperature_k,
                pressure_pa=pressure_pa,
            ),
            result,
        )

    def configure_ph(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
        enthalpy_j_kg: float,
        *,
        reference_state: ReferenceStatePolicy,
        result: FluidState,
    ) -> None:
        self._configure(
            ProviderQueryKey.from_request(
                PropertyQueryType.PH,
                fluid,
                pressure_pa=pressure_pa,
                enthalpy_j_kg=enthalpy_j_kg,
                reference_state=reference_state,
            ),
            result,
        )

    def configure_saturation_at_pressure(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
        result: SaturationState,
    ) -> None:
        self._configure(
            ProviderQueryKey.from_request(
                PropertyQueryType.SATURATION_P,
                fluid,
                pressure_pa=pressure_pa,
            ),
            result,
        )

    def configure_saturation_at_temperature(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
        result: SaturationState,
    ) -> None:
        self._configure(
            ProviderQueryKey.from_request(
                PropertyQueryType.SATURATION_T,
                fluid,
                temperature_k=temperature_k,
            ),
            result,
        )

    def _configure(self, key: ProviderQueryKey, result: PropertyResult) -> None:
        _require_result_type(key, result)
        self._results[key] = result

    def _resolve(self, key: ProviderQueryKey) -> PropertyResult:
        self.calls.append(key)
        try:
            result = self._results[key]
        except KeyError as exc:
            raise TestProviderError(f"unconfigured property request: {key!r}") from exc
        return _require_result_type(key, result)

    def state_tp(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
        pressure_pa: float,
    ) -> FluidState:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.TP,
            fluid,
            temperature_k=temperature_k,
            pressure_pa=pressure_pa,
        )
        return cast(FluidState, self._resolve(key))

    def state_ph(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
        enthalpy_j_kg: float,
        *,
        reference_state: ReferenceStatePolicy,
    ) -> FluidState:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.PH,
            fluid,
            pressure_pa=pressure_pa,
            enthalpy_j_kg=enthalpy_j_kg,
            reference_state=reference_state,
        )
        return cast(FluidState, self._resolve(key))

    def saturation_at_pressure(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
    ) -> SaturationState:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.SATURATION_P,
            fluid,
            pressure_pa=pressure_pa,
        )
        return cast(SaturationState, self._resolve(key))

    def saturation_at_temperature(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
    ) -> SaturationState:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.SATURATION_T,
            fluid,
            temperature_k=temperature_k,
        )
        return cast(SaturationState, self._resolve(key))

    def cache_info(self) -> PropertyCacheInfo:
        return _zero_cache_info()

    def clear_cache(self) -> None:
        return None


class ReplayPropertyProvider:
    """Ordered deterministic replay for each provider query type."""

    name = "ReplayPropertyProvider"
    version = "1.0"
    git_revision = "test"
    reference_state_policy = ReferenceStatePolicy.DEF

    def __init__(
        self,
        *,
        tp: Sequence[FluidState] = (),
        ph: Sequence[FluidState] = (),
        saturation_p: Sequence[SaturationState] = (),
        saturation_t: Sequence[SaturationState] = (),
    ) -> None:
        self._queues: dict[PropertyQueryType, tuple[PropertyResult, ...]] = {
            PropertyQueryType.TP: tuple(tp),
            PropertyQueryType.PH: tuple(ph),
            PropertyQueryType.SATURATION_P: tuple(saturation_p),
            PropertyQueryType.SATURATION_T: tuple(saturation_t),
        }
        self._positions = _new_counter_map()
        self.calls: list[ProviderQueryKey] = []

    def _next(self, key: ProviderQueryKey) -> PropertyResult:
        self.calls.append(key)
        position = self._positions[key.query_type]
        queue = self._queues[key.query_type]
        if position >= len(queue):
            raise TestProviderError(
                f"replay exhausted for {key.query_type.value} at call {position + 1}"
            )
        self._positions[key.query_type] = position + 1
        return _require_result_type(key, queue[position])

    def state_tp(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
        pressure_pa: float,
    ) -> FluidState:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.TP,
            fluid,
            temperature_k=temperature_k,
            pressure_pa=pressure_pa,
        )
        return cast(FluidState, self._next(key))

    def state_ph(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
        enthalpy_j_kg: float,
        *,
        reference_state: ReferenceStatePolicy,
    ) -> FluidState:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.PH,
            fluid,
            pressure_pa=pressure_pa,
            enthalpy_j_kg=enthalpy_j_kg,
            reference_state=reference_state,
        )
        return cast(FluidState, self._next(key))

    def saturation_at_pressure(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
    ) -> SaturationState:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.SATURATION_P,
            fluid,
            pressure_pa=pressure_pa,
        )
        return cast(SaturationState, self._next(key))

    def saturation_at_temperature(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
    ) -> SaturationState:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.SATURATION_T,
            fluid,
            temperature_k=temperature_k,
        )
        return cast(SaturationState, self._next(key))

    def assert_fully_consumed(self) -> None:
        remaining = {
            query_type.value: len(self._queues[query_type]) - self._positions[query_type]
            for query_type in _QUERY_TYPES
            if self._positions[query_type] != len(self._queues[query_type])
        }
        if remaining:
            raise AssertionError(f"unconsumed replay results: {remaining!r}")

    def reset_replay(self) -> None:
        self._positions = _new_counter_map()
        self.calls.clear()

    def cache_info(self) -> PropertyCacheInfo:
        return _zero_cache_info()

    def clear_cache(self) -> None:
        return None


class SelectiveFailurePropertyProvider:
    """Fail configured 1-based query calls before delegating to the inner provider."""

    def __init__(
        self,
        inner: PropertyProvider,
        failures: Mapping[FailureKey, BaseException],
    ) -> None:
        self.inner = inner
        self.failures = dict(failures)
        self._counts = _new_counter_map()
        for query_type, index in self.failures:
            if query_type not in _QUERY_TYPES or index <= 0:
                raise ValueError(f"invalid failure key: {(query_type, index)!r}")

    @property
    def name(self) -> str:
        return self.inner.name

    @property
    def version(self) -> str:
        return self.inner.version

    @property
    def git_revision(self) -> str:
        return self.inner.git_revision

    @property
    def reference_state_policy(self) -> ReferenceStatePolicy:
        return self.inner.reference_state_policy

    def _before_delegate(self, query_type: PropertyQueryType) -> None:
        index = self._counts[query_type] + 1
        self._counts[query_type] = index
        failure = self.failures.get((query_type, index))
        if failure is not None:
            raise failure

    def state_tp(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
        pressure_pa: float,
    ) -> FluidState:
        self._before_delegate(PropertyQueryType.TP)
        return self.inner.state_tp(fluid, temperature_k, pressure_pa)

    def state_ph(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
        enthalpy_j_kg: float,
        *,
        reference_state: ReferenceStatePolicy,
    ) -> FluidState:
        self._before_delegate(PropertyQueryType.PH)
        return self.inner.state_ph(
            fluid,
            pressure_pa,
            enthalpy_j_kg,
            reference_state=reference_state,
        )

    def saturation_at_pressure(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
    ) -> SaturationState:
        self._before_delegate(PropertyQueryType.SATURATION_P)
        return self.inner.saturation_at_pressure(fluid, pressure_pa)

    def saturation_at_temperature(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
    ) -> SaturationState:
        self._before_delegate(PropertyQueryType.SATURATION_T)
        return self.inner.saturation_at_temperature(fluid, temperature_k)

    def cache_info(self) -> PropertyCacheInfo:
        return self.inner.cache_info()

    def clear_cache(self) -> None:
        self.inner.clear_cache()


class CountingPropertyProvider:
    """Count and record every provider call before delegating."""

    def __init__(self, inner: PropertyProvider) -> None:
        self.inner = inner
        self.counts = _new_counter_map()
        self.calls: list[ProviderQueryKey] = []

    @property
    def name(self) -> str:
        return self.inner.name

    @property
    def version(self) -> str:
        return self.inner.version

    @property
    def git_revision(self) -> str:
        return self.inner.git_revision

    @property
    def reference_state_policy(self) -> ReferenceStatePolicy:
        return self.inner.reference_state_policy

    def _record(self, key: ProviderQueryKey) -> None:
        self.counts[key.query_type] += 1
        self.calls.append(key)

    def state_tp(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
        pressure_pa: float,
    ) -> FluidState:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.TP,
            fluid,
            temperature_k=temperature_k,
            pressure_pa=pressure_pa,
        )
        self._record(key)
        return self.inner.state_tp(fluid, temperature_k, pressure_pa)

    def state_ph(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
        enthalpy_j_kg: float,
        *,
        reference_state: ReferenceStatePolicy,
    ) -> FluidState:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.PH,
            fluid,
            pressure_pa=pressure_pa,
            enthalpy_j_kg=enthalpy_j_kg,
            reference_state=reference_state,
        )
        self._record(key)
        return self.inner.state_ph(
            fluid,
            pressure_pa,
            enthalpy_j_kg,
            reference_state=reference_state,
        )

    def saturation_at_pressure(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
    ) -> SaturationState:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.SATURATION_P,
            fluid,
            pressure_pa=pressure_pa,
        )
        self._record(key)
        return self.inner.saturation_at_pressure(fluid, pressure_pa)

    def saturation_at_temperature(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
    ) -> SaturationState:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.SATURATION_T,
            fluid,
            temperature_k=temperature_k,
        )
        self._record(key)
        return self.inner.saturation_at_temperature(fluid, temperature_k)

    def reset_counts(self) -> None:
        self.counts = _new_counter_map()
        self.calls.clear()

    def cache_info(self) -> PropertyCacheInfo:
        return self.inner.cache_info()

    def clear_cache(self) -> None:
        self.inner.clear_cache()


if TYPE_CHECKING:
    _stub_contract: PropertyProvider = StubPropertyProvider()
    _replay_contract: PropertyProvider = ReplayPropertyProvider()
    _selective_contract: PropertyProvider = SelectiveFailurePropertyProvider(
        StubPropertyProvider(), {}
    )
    _counting_contract: PropertyProvider = CountingPropertyProvider(StubPropertyProvider())
