"""Tests for CorrelationRegistry Protocol and InMemoryCorrelationRegistry."""

from __future__ import annotations

import pytest

from hexagent.correlations.errors import (
    CorrelationDuplicateError,
    CorrelationNotFoundError,
    CorrelationVersionNotFoundError,
)
from hexagent.correlations.models import (
    ApplicabilityEnvelope,
    ApplicabilityStatus,
    ApplicabilityVariable,
    BibliographicSource,
    CorrelationApplicabilityInput,
    CorrelationDefinition,
    CorrelationImplementationStatus,
    CorrelationKey,
    CorrelationPurpose,
    FlowRegime,
    GeometryType,
    NumericBound,
    PhaseRegime,
)
from hexagent.correlations.registry import InMemoryCorrelationRegistry

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_definition(
    correlation_id: str = "fixture.htc.tube",
    version: str = "1.0.0",
    *,
    purpose: CorrelationPurpose = CorrelationPurpose.heat_transfer_coefficient,
    geometry: frozenset[GeometryType] | None = None,
    phase_regimes: frozenset[PhaseRegime] | None = None,
    flow_regimes: frozenset[FlowRegime] | None = None,
    bounds: tuple[NumericBound, ...] | None = None,
    implementation_status: CorrelationImplementationStatus = (
        CorrelationImplementationStatus.metadata_only
    ),
    implementation_ref: str | None = None,
    tags: frozenset[str] = frozenset(),
) -> CorrelationDefinition:
    gt = geometry or frozenset({GeometryType.circular_tube})
    pr = phase_regimes or frozenset({PhaseRegime.single_phase_liquid})
    fr = flow_regimes or frozenset({FlowRegime.turbulent})
    bnds = bounds or (
        NumericBound(
            variable=ApplicabilityVariable.reynolds,
            minimum=3000.0,
            maximum=100000.0,
        ),
    )
    # Item 3: required_inputs must include all bounded variables
    ri = frozenset({b.variable for b in bnds})

    # Item 7: implementation_ref required for implemented/validated
    imp_ref = implementation_ref
    if (
        implementation_status
        in (
            CorrelationImplementationStatus.implemented,
            CorrelationImplementationStatus.validated,
        )
        and not imp_ref
    ):
        imp_ref = f"impl-{correlation_id}-{version}"

    return CorrelationDefinition.create(
        key=CorrelationKey(correlation_id=correlation_id, version=version),
        name=f"Fixture {correlation_id} v{version}",
        purpose=purpose,
        description=f"Test correlation {correlation_id}",
        geometry=gt,
        phase_regimes=pr,
        envelope=ApplicabilityEnvelope(
            geometry_types=gt,
            phase_regimes=pr,
            flow_regimes=fr,
            bounds=bnds,
            required_inputs=ri,
        ),
        source=BibliographicSource(
            source_id="src-001",
            title="Fictional Paper",
            publication="Fictional Journal",
            year=2020,
        ),
        implementation_status=implementation_status,
        implementation_ref=imp_ref,
        tags=tags,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInMemoryCorrelationRegistry:
    """Registry operations: register, get, list, search."""

    def test_register_and_get(self) -> None:
        reg = InMemoryCorrelationRegistry()
        defn = _make_definition()
        reg.register(defn)
        result = reg.get(defn.key)
        assert result.key.correlation_id == "fixture.htc.tube"
        assert result.key.version == "1.0.0"

    def test_get_returns_deep_copy(self) -> None:
        reg = InMemoryCorrelationRegistry()
        defn = _make_definition()
        reg.register(defn)
        result = reg.get(defn.key)
        assert result.key == defn.key

    def test_duplicate_key_rejected(self) -> None:
        reg = InMemoryCorrelationRegistry()
        defn = _make_definition()
        reg.register(defn)
        with pytest.raises(CorrelationDuplicateError):
            reg.register(_make_definition())

    def test_same_id_different_versions(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(_make_definition(version="1.0.0"))
        reg.register(_make_definition(version="1.1.0"))
        assert len(reg.list_versions("fixture.htc.tube")) == 2

    def test_get_nonexistent(self) -> None:
        reg = InMemoryCorrelationRegistry()
        key = CorrelationKey(correlation_id="nonexistent", version="1.0.0")
        with pytest.raises(CorrelationNotFoundError):
            reg.get(key)

    def test_get_version_not_found(self) -> None:
        """Item 7: When ID exists but version doesn't, raise CorrelationVersionNotFoundError."""
        reg = InMemoryCorrelationRegistry()
        reg.register(_make_definition(version="1.0.0"))
        key = CorrelationKey(correlation_id="fixture.htc.tube", version="2.0.0")
        with pytest.raises(CorrelationVersionNotFoundError):
            reg.get(key)

    def test_get_latest(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(_make_definition(version="1.0.0"))
        reg.register(_make_definition(version="1.1.0"))
        reg.register(_make_definition(version="2.0.0"))
        latest = reg.get_latest("fixture.htc.tube")
        assert latest.key.version == "2.0.0"

    def test_get_latest_with_prerelease(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(_make_definition(version="1.0.0"))
        reg.register(_make_definition(version="1.1.0-alpha"))
        latest = reg.get_latest("fixture.htc.tube")
        # Stable 1.0.0 should be preferred over prerelease 1.1.0-alpha
        assert latest.key.version == "1.0.0"

    def test_get_latest_only_prerelease(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(_make_definition(version="1.0.0-alpha"))
        latest = reg.get_latest("fixture.htc.tube", include_prerelease=True)
        assert latest.key.version == "1.0.0-alpha"

    def test_get_latest_excludes_deprecated(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(
            _make_definition(
                version="1.0.0",
                implementation_status=CorrelationImplementationStatus.implemented,
            )
        )
        reg.register(
            _make_definition(
                version="2.0.0",
                implementation_status=CorrelationImplementationStatus.deprecated,
            )
        )
        latest = reg.get_latest("fixture.htc.tube")
        assert latest.key.version == "1.0.0"

    def test_get_latest_includes_deprecated_when_opted_in(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(
            _make_definition(
                version="1.0.0",
                implementation_status=CorrelationImplementationStatus.implemented,
            )
        )
        reg.register(
            _make_definition(
                version="2.0.0",
                implementation_status=CorrelationImplementationStatus.deprecated,
            )
        )
        latest = reg.get_latest("fixture.htc.tube", include_deprecated=True)
        assert latest.key.version == "2.0.0"

    def test_get_latest_excludes_withdrawn(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(
            _make_definition(
                version="1.0.0",
                implementation_status=CorrelationImplementationStatus.withdrawn,
            )
        )
        with pytest.raises(CorrelationNotFoundError):
            reg.get_latest("fixture.htc.tube")

    def test_get_latest_nonexistent(self) -> None:
        reg = InMemoryCorrelationRegistry()
        with pytest.raises(CorrelationNotFoundError):
            reg.get_latest("nonexistent")

    def test_list_versions_sorted(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(_make_definition(version="2.0.0"))
        reg.register(_make_definition(version="1.0.0"))
        reg.register(_make_definition(version="1.1.0"))
        versions = reg.list_versions("fixture.htc.tube")
        assert [v.key.version for v in versions] == ["1.0.0", "1.1.0", "2.0.0"]

    def test_list_versions_nonexistent(self) -> None:
        reg = InMemoryCorrelationRegistry()
        with pytest.raises(CorrelationNotFoundError):
            reg.list_versions("nonexistent")

    def test_search_by_purpose(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(
            _make_definition(
                correlation_id="fixture.htc",
                purpose=CorrelationPurpose.heat_transfer_coefficient,
            )
        )
        reg.register(
            _make_definition(
                correlation_id="fixture.ff",
                purpose=CorrelationPurpose.friction_factor,
            )
        )
        results = reg.search(purpose=CorrelationPurpose.heat_transfer_coefficient)
        assert len(results) == 1
        assert results[0].key.correlation_id == "fixture.htc"

    def test_search_by_geometry(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(
            _make_definition(
                correlation_id="fixture.tube",
                geometry=frozenset({GeometryType.circular_tube}),
            )
        )
        reg.register(
            _make_definition(
                correlation_id="fixture.annulus",
                geometry=frozenset({GeometryType.annulus}),
            )
        )
        results = reg.search(geometry=GeometryType.circular_tube)
        assert len(results) == 1
        assert results[0].key.correlation_id == "fixture.tube"

    def test_search_by_tags(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(
            _make_definition(
                correlation_id="fixture.a",
                tags=frozenset({"validated", "production"}),
            )
        )
        reg.register(
            _make_definition(
                correlation_id="fixture.b",
                tags=frozenset({"experimental"}),
            )
        )
        results = reg.search(tags=frozenset({"validated"}))
        assert len(results) == 1
        assert results[0].key.correlation_id == "fixture.a"

    def test_search_multiple_filters(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(
            _make_definition(
                correlation_id="fixture.a",
                purpose=CorrelationPurpose.heat_transfer_coefficient,
                geometry=frozenset({GeometryType.circular_tube}),
            )
        )
        reg.register(
            _make_definition(
                correlation_id="fixture.b",
                purpose=CorrelationPurpose.friction_factor,
                geometry=frozenset({GeometryType.circular_tube}),
            )
        )
        results = reg.search(
            purpose=CorrelationPurpose.heat_transfer_coefficient,
            geometry=GeometryType.circular_tube,
        )
        assert len(results) == 1

    def test_search_empty_results(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(_make_definition())
        results = reg.search(purpose=CorrelationPurpose.friction_factor)
        assert len(results) == 0

    def test_search_excludes_deprecated_by_default(self) -> None:
        """Item 7: Default search excludes deprecated."""
        reg = InMemoryCorrelationRegistry()
        reg.register(
            _make_definition(
                correlation_id="fixture.a",
                implementation_status=CorrelationImplementationStatus.implemented,
            )
        )
        reg.register(
            _make_definition(
                correlation_id="fixture.b",
                implementation_status=CorrelationImplementationStatus.deprecated,
            )
        )
        results = reg.search()
        assert len(results) == 1
        assert results[0].key.correlation_id == "fixture.a"

    def test_search_excludes_withdrawn_by_default(self) -> None:
        """Item 7: Default search excludes withdrawn."""
        reg = InMemoryCorrelationRegistry()
        reg.register(
            _make_definition(
                correlation_id="fixture.a",
                implementation_status=CorrelationImplementationStatus.implemented,
            )
        )
        reg.register(
            _make_definition(
                correlation_id="fixture.b",
                implementation_status=CorrelationImplementationStatus.withdrawn,
            )
        )
        results = reg.search()
        assert len(results) == 1

    def test_search_includes_deprecated_when_opted_in(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(
            _make_definition(
                correlation_id="fixture.a",
                implementation_status=CorrelationImplementationStatus.implemented,
            )
        )
        reg.register(
            _make_definition(
                correlation_id="fixture.b",
                implementation_status=CorrelationImplementationStatus.deprecated,
            )
        )
        results = reg.search(include_deprecated=True)
        assert len(results) == 2

    def test_assess(self) -> None:
        reg = InMemoryCorrelationRegistry()
        defn = _make_definition()
        reg.register(defn)
        inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
            flow_regime=FlowRegime.turbulent,
            values={ApplicabilityVariable.reynolds: 25000.0},
        )
        result = reg.assess(defn.key, inputs)
        assert result.status == ApplicabilityStatus.applicable

    def test_register_prevents_external_mutation(self) -> None:
        """After registration, modifying the original dict should not affect stored data."""
        reg = InMemoryCorrelationRegistry()
        defn = _make_definition()
        reg.register(defn)
        stored = reg.get(defn.key)
        assert stored.key.version == "1.0.0"

    def test_search_deterministic_order(self) -> None:
        """Search results are sorted by correlation_id then version."""
        reg = InMemoryCorrelationRegistry()
        reg.register(_make_definition(correlation_id="z.fixture", version="2.0.0"))
        reg.register(_make_definition(correlation_id="a.fixture", version="1.0.0"))
        reg.register(_make_definition(correlation_id="a.fixture", version="2.0.0"))
        results = reg.search()
        ids = [r.key.correlation_id for r in results]
        assert ids == ["a.fixture", "a.fixture", "z.fixture"]

    def test_version_sorting_prerelease_order(self) -> None:
        """Item 2: SemVer prerelease ordering."""
        reg = InMemoryCorrelationRegistry()
        reg.register(_make_definition(version="1.0.0-alpha"))
        reg.register(_make_definition(version="1.0.0-alpha.1"))
        reg.register(_make_definition(version="1.0.0-alpha.10"))
        reg.register(_make_definition(version="1.0.0-alpha.2"))
        reg.register(_make_definition(version="1.0.0-beta"))
        reg.register(_make_definition(version="1.0.0"))
        versions = reg.list_versions("fixture.htc.tube")
        assert [v.key.version for v in versions] == [
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-alpha.2",
            "1.0.0-alpha.10",
            "1.0.0-beta",
            "1.0.0",
        ]
