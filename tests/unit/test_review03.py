"""Comprehensive tests for TASK-004 Engineering Review Round 3, items 1-5.

1. Repository chain invariants (real InMemoryDesignCaseRevisionRepository).
2. Full DesignCase unit-equivalent hashing.
3. Recursive depth immutability.
4. Provenance persistence contract (real InMemoryCalculationRunRepository).
5. git_commit validation.
"""

from __future__ import annotations

import types
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from hexagent.core.canonical import canonicalize_design_case, sha256_digest
from hexagent.core.immutability import deep_freeze
from hexagent.domain.messages import (
    EngineeringMessage,
    EngineeringMessageSeverity,
    ErrorCode,
    RunFailure,
)
from hexagent.domain.models import (
    DesignCase,
    DesignConstraints,
    FluidSpec,
    FoulingResistanceSpec,
    FoulingSource,
    FoulingSourceType,
    StreamSpec,
    VerificationStatus,
)
from hexagent.domain.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)
from hexagent.domain.quantities import (
    AbsolutePressure,
    AbsoluteTemperature,
    FoulingResistance,
    Length,
    MassFlow,
)
from hexagent.domain.revisions import (
    CalculationRun,
    CalculationRunStatus,
    CalculationRunType,
    DesignCaseRevision,
    FieldChange,
    IntegrityError,
    RevisionDiff,
)
from hexagent.repositories.memory import (
    EmptyProvenanceGraphError,
    InMemoryCalculationRunRepository,
    InMemoryDesignCaseRevisionRepository,
    OrphanProvenanceNodeError,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

FIXED_NOW = datetime(2026, 1, 1, tzinfo=UTC)
FIXED_IDS = [UUID(int=i) for i in range(1, 40)]
VALID_HASH = "sha256:" + "a" * 64
VALID_HASH_B = "sha256:" + "b" * 64
VALID_HASH_C = "sha256:" + "c" * 64


def _make_fluid(name: str = "Water") -> FluidSpec:
    return FluidSpec(backend="CoolProp", name=name)


def _make_fouling_source() -> FoulingSource:
    return FoulingSource(
        source_type=FoulingSourceType.STANDARD,
        reference_id="TEMA",
        edition="2019",
        table_or_clause="Table RGP-K-2",
        verification_status=VerificationStatus.VERIFIED,
        note="Clean water fouling",
    )


def _make_fouling_spec() -> FoulingResistanceSpec:
    return FoulingResistanceSpec(
        value=FoulingResistance(value=0.0002, unit="m^2*K/W"),
        source=_make_fouling_source(),
    )


def _make_stream(
    *,
    name: str = "Water",
    mass_flow: float = 1.0,
    mass_flow_unit: str = "kg/s",
    inlet_temp: float = 350.0,
    inlet_temp_unit: str = "K",
    outlet_temp: float = 310.0,
    inlet_pressure: float = 200000.0,
    inlet_pressure_unit: str = "Pa",
) -> StreamSpec:
    return StreamSpec(
        fluid=_make_fluid(name),
        mass_flow=MassFlow(value=mass_flow, unit=mass_flow_unit),
        inlet_temperature=AbsoluteTemperature(value=inlet_temp, unit=inlet_temp_unit),
        inlet_pressure=AbsolutePressure(value=inlet_pressure, unit=inlet_pressure_unit),
        fouling_resistance=_make_fouling_spec(),
        outlet_temperature=AbsoluteTemperature(value=outlet_temp, unit="K"),
    )


def _make_constraints(
    *,
    corrosion_allowance: float = 0.003,
    corrosion_unit: str = "m",
) -> DesignConstraints:
    return DesignConstraints(
        design_pressure_hot=AbsolutePressure(value=250000.0, unit="Pa"),
        design_pressure_cold=AbsolutePressure(value=200000.0, unit="Pa"),
        design_temperature_hot=AbsoluteTemperature(value=370.0, unit="K"),
        design_temperature_cold=AbsoluteTemperature(value=350.0, unit="K"),
        corrosion_allowance=Length(value=corrosion_allowance, unit=corrosion_unit),
        required_area_margin_fraction=0.1,
    )


def _make_case(
    case_id: UUID | None = None,
    outlet_temp: float = 310.0,
    name: str = "Review03 Test HX",
) -> DesignCase:
    return DesignCase(
        id=case_id or FIXED_IDS[0],
        name=name,
        hot_stream=_make_stream(inlet_temp=350.0, outlet_temp=outlet_temp),
        cold_stream=_make_stream(
            inlet_temp=290.0,
            outlet_temp=330.0,
            mass_flow=0.8,
        ),
        constraints=_make_constraints(),
    )


def _make_revision(
    case: DesignCase,
    revision_id: UUID,
    *,
    revision_number: int = 1,
    parent_revision_id: UUID | None = None,
    created_by: str = "test-agent",
) -> DesignCaseRevision:
    """Build a valid DesignCaseRevision with correct content hash."""
    cp = canonicalize_design_case(case)
    h = sha256_digest(cp)
    return DesignCaseRevision(
        revision_id=revision_id,
        case_id=case.id,
        revision_number=revision_number,
        design_case=case,
        canonical_payload=cp,
        content_hash=h,
        created_at=FIXED_NOW,
        created_by=created_by,
        parent_revision_id=parent_revision_id,
        change_summary="",
        changed_fields=(),
    )


def _minimal_valid_provenance_graph() -> ProvenanceGraph:
    """Build a minimal valid provenance graph (CASE_REVISION + CALCULATION_RUN)."""
    case_node = ProvenanceNode(
        node_id=UUID(int=30),
        node_type=ProvenanceNodeType.CASE_REVISION,
        label="rev",
        payload_hash=VALID_HASH,
    )
    calc_node = ProvenanceNode(
        node_id=UUID(int=31),
        node_type=ProvenanceNodeType.CALCULATION_RUN,
        label="run",
        payload_hash=VALID_HASH_B,
    )
    edge = ProvenanceEdge(
        source_id=UUID(int=30),
        target_id=UUID(int=31),
        relation="triggers",
    )
    return ProvenanceGraph(
        nodes=(case_node, calc_node),
        edges=(edge,),
    )


def _succeeded_provenance_graph() -> ProvenanceGraph:
    """Build a provenance graph suitable for a SUCCEEDED run (with RESULT node)."""
    case_node = ProvenanceNode(
        node_id=UUID(int=40),
        node_type=ProvenanceNodeType.CASE_REVISION,
        label="rev",
        payload_hash=VALID_HASH,
    )
    calc_node = ProvenanceNode(
        node_id=UUID(int=41),
        node_type=ProvenanceNodeType.CALCULATION_RUN,
        label="run",
        payload_hash=VALID_HASH_B,
    )
    result_node = ProvenanceNode(
        node_id=UUID(int=42),
        node_type=ProvenanceNodeType.RESULT,
        label="result",
        payload_hash=VALID_HASH_C,
    )
    edge1 = ProvenanceEdge(
        source_id=UUID(int=40),
        target_id=UUID(int=41),
        relation="triggers",
    )
    edge2 = ProvenanceEdge(
        source_id=UUID(int=41),
        target_id=UUID(int=42),
        relation="produces",
    )
    return ProvenanceGraph(
        nodes=(case_node, calc_node, result_node),
        edges=(edge1, edge2),
    )


def _make_calculation_run(
    *,
    run_id: UUID | None = None,
    case_id: UUID | None = None,
    case_revision_id: UUID | None = None,
    status: CalculationRunStatus = CalculationRunStatus.PENDING,
    input_hash: str = VALID_HASH,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    result_hash: str | None = None,
    failure: RunFailure | None = None,
    blockers: tuple[EngineeringMessage, ...] = (),
    provenance_graph: ProvenanceGraph | None = None,
) -> CalculationRun:
    return CalculationRun(
        run_id=run_id or FIXED_IDS[10],
        case_id=case_id or FIXED_IDS[0],
        case_revision_id=case_revision_id or FIXED_IDS[1],
        run_type=CalculationRunType.SCREEN,
        status=status,
        started_at=started_at or FIXED_NOW,
        completed_at=completed_at,
        input_hash=input_hash,
        result_hash=result_hash,
        failure=failure,
        blockers=blockers,
        provenance_graph=provenance_graph or _minimal_valid_provenance_graph(),
    )


# ===========================================================================
# 1. TestRepositoryChainInvariants
# ===========================================================================


class TestRepositoryChainInvariants:
    """InMemoryDesignCaseRevisionRepository enforces revision chain invariants."""

    def test_add_rejects_cross_case_parent(self) -> None:
        """Create rev#1 for case A, then try rev#2 for case B with parent=rev_A1
        → must raise IntegrityError (parent.case_id != child.case_id)."""
        case_a = _make_case(case_id=FIXED_IDS[0])
        case_b = _make_case(case_id=FIXED_IDS[1], name="Case B")
        repo = InMemoryDesignCaseRevisionRepository()

        # Add rev#1 for case A
        rev_a1 = _make_revision(case_a, FIXED_IDS[20], revision_number=1)
        repo.add(rev_a1)

        # Try rev#2 for case B with parent=rev_A1 → should fail
        rev_b2 = _make_revision(
            case_b,
            FIXED_IDS[21],
            revision_number=2,
            parent_revision_id=rev_a1.revision_id,
        )
        with pytest.raises(IntegrityError, match="belongs to case"):
            repo.add(rev_b2)

    def test_add_rejects_numbering_gap(self) -> None:
        """Create rev#1, then try rev#3 with parent=rev1
        → must raise IntegrityError (child.revision_number != parent.revision_number + 1)."""
        case = _make_case(case_id=FIXED_IDS[0])
        repo = InMemoryDesignCaseRevisionRepository()

        rev1 = _make_revision(case, FIXED_IDS[22], revision_number=1)
        repo.add(rev1)

        # Try rev#3 with parent=rev1 (should be rev#2)
        rev3 = _make_revision(
            case,
            FIXED_IDS[23],
            revision_number=3,
            parent_revision_id=rev1.revision_id,
        )
        with pytest.raises(IntegrityError, match="not exactly parent.revision_number"):
            repo.add(rev3)

    def test_add_rejects_non_sequential(self) -> None:
        """Create rev#1 and rev#2 for case A, then try rev#4 with parent=rev2
        → must raise IntegrityError."""
        case = _make_case(case_id=FIXED_IDS[0])
        repo = InMemoryDesignCaseRevisionRepository()

        rev1 = _make_revision(case, FIXED_IDS[24], revision_number=1)
        rev2 = _make_revision(
            case,
            FIXED_IDS[25],
            revision_number=2,
            parent_revision_id=rev1.revision_id,
        )
        repo.add(rev1)
        repo.add(rev2)

        # Try rev#4 with parent=rev2 (should be rev#3)
        rev4 = _make_revision(
            case,
            FIXED_IDS[26],
            revision_number=4,
            parent_revision_id=rev2.revision_id,
        )
        with pytest.raises(IntegrityError, match="not exactly parent.revision_number"):
            repo.add(rev4)

    def test_add_accepts_valid_sequential_chain(self) -> None:
        """rev#1 → rev#2 → rev#3 all succeed."""
        case = _make_case(case_id=FIXED_IDS[0])
        repo = InMemoryDesignCaseRevisionRepository()

        rev1 = _make_revision(case, FIXED_IDS[27], revision_number=1)
        repo.add(rev1)

        case_v2 = _make_case(case_id=FIXED_IDS[0], outlet_temp=305.0)
        rev2 = _make_revision(
            case_v2,
            FIXED_IDS[28],
            revision_number=2,
            parent_revision_id=rev1.revision_id,
        )
        repo.add(rev2)

        case_v3 = _make_case(case_id=FIXED_IDS[0], outlet_temp=300.0)
        rev3 = _make_revision(
            case_v3,
            FIXED_IDS[29],
            revision_number=3,
            parent_revision_id=rev2.revision_id,
        )
        repo.add(rev3)

        # Verify all three are stored
        stored = repo.list_by_case(FIXED_IDS[0])
        assert len(stored) == 3
        assert [r.revision_number for r in stored] == [1, 2, 3]

    def test_add_validates_case_id_match(self) -> None:
        """Parent from case A, child from case A → OK.
        Parent from case A, child from case B → rejected."""
        case_a = _make_case(case_id=FIXED_IDS[0])
        case_b = _make_case(case_id=FIXED_IDS[1], name="Case B")
        repo = InMemoryDesignCaseRevisionRepository()

        # Add rev#1 for case A
        rev_a1 = _make_revision(case_a, FIXED_IDS[30], revision_number=1)
        repo.add(rev_a1)

        # rev#2 for case A with parent=rev_A1 → OK
        case_a2 = _make_case(case_id=FIXED_IDS[0], outlet_temp=305.0)
        rev_a2 = _make_revision(
            case_a2,
            FIXED_IDS[31],
            revision_number=2,
            parent_revision_id=rev_a1.revision_id,
        )
        repo.add(rev_a2)

        # rev#2 for case B with parent=rev_A1 → rejected
        rev_b2 = _make_revision(
            case_b,
            FIXED_IDS[32],
            revision_number=2,
            parent_revision_id=rev_a1.revision_id,
        )
        with pytest.raises(IntegrityError, match="belongs to case"):
            repo.add(rev_b2)


# ===========================================================================
# 2. TestUnitEquivalentHashing
# ===========================================================================


class TestUnitEquivalentHashing:
    """canonicalize_design_case() produces identical canonical payloads for
    physically equivalent quantities expressed in different units."""

    def test_complete_case_celsius_kelvin_equivalence(self) -> None:
        """hot_stream.inlet_temperature in °C vs K must produce same canonical payload."""
        case_k = _make_case()
        case_c = _make_case()

        # Override hot_stream with °C equivalent of 350 K = 76.85 °C
        case_c_celsius = DesignCase(
            id=case_c.id,
            name=case_c.name,
            hot_stream=_make_stream(inlet_temp=76.85, inlet_temp_unit="degC"),
            cold_stream=case_c.cold_stream,
            constraints=case_c.constraints,
        )
        cp_k = canonicalize_design_case(case_k)
        cp_c = canonicalize_design_case(case_c_celsius)
        assert cp_k == cp_c

    def test_complete_case_bar_pascal_equivalence(self) -> None:
        """hot_stream.inlet_pressure in bar vs Pa must produce same canonical payload."""
        case_pa = _make_case()
        # 200000 Pa = 2 bar
        case_bar = _make_case()
        case_bar_with_bar = DesignCase(
            id=case_bar.id,
            name=case_bar.name,
            hot_stream=_make_stream(
                inlet_temp=350.0,
                inlet_pressure=2.0,
                inlet_pressure_unit="bar",
            ),
            cold_stream=case_bar.cold_stream,
            constraints=case_bar.constraints,
        )
        cp_pa = canonicalize_design_case(case_pa)
        cp_bar = canonicalize_design_case(case_bar_with_bar)
        assert cp_pa == cp_bar

    def test_complete_case_mm_m_equivalence(self) -> None:
        """constraints.corrosion_allowance in mm vs m must produce same canonical payload."""
        case_m = _make_case()
        case_mm = _make_case()
        constraints_mm = _make_constraints(corrosion_allowance=3.0, corrosion_unit="mm")
        case_mm_obj = DesignCase(
            id=case_mm.id,
            name=case_mm.name,
            hot_stream=case_mm.hot_stream,
            cold_stream=case_mm.cold_stream,
            constraints=constraints_mm,
        )
        cp_m = canonicalize_design_case(case_m)
        cp_mm = canonicalize_design_case(case_mm_obj)
        assert cp_m == cp_mm

    def test_complete_case_kgh_kgs_equivalence(self) -> None:
        """hot_stream.mass_flow in kg/h vs kg/s must produce same canonical payload."""
        case_kgs = _make_case()
        # 3600 kg/h = 1.0 kg/s
        case_kgh = _make_case()
        case_kgh_obj = DesignCase(
            id=case_kgh.id,
            name=case_kgh.name,
            hot_stream=_make_stream(inlet_temp=350.0, mass_flow=3600.0, mass_flow_unit="kg/h"),
            cold_stream=case_kgh.cold_stream,
            constraints=case_kgh.constraints,
        )
        cp_kgs = canonicalize_design_case(case_kgs)
        cp_kgh = canonicalize_design_case(case_kgh_obj)
        assert cp_kgs == cp_kgh

    def test_real_physical_value_change_changes_hash(self) -> None:
        """Changing a real physical value must change the canonical hash."""
        case1 = _make_case(outlet_temp=310.0)
        case2 = _make_case(outlet_temp=320.0)

        h1 = sha256_digest(canonicalize_design_case(case1))
        h2 = sha256_digest(canonicalize_design_case(case2))
        assert h1 != h2

    def test_canonical_payload_uses_si_values(self) -> None:
        """Canonical payload contains si_value fields, not raw user values."""
        case = _make_case()
        cp = canonicalize_design_case(case)

        # The hot_stream.inlet_temperature should have si_value, not raw value+unit
        hot = cp["hot_stream"]
        inlet_temp = hot["inlet_temperature"]
        assert "si_value" in inlet_temp
        assert "kind" in inlet_temp
        # 350 K in SI is 350.0 K
        assert inlet_temp["si_value"] == 350.0

        # Mass flow should also have si_value
        mass = hot["mass_flow"]
        assert "si_value" in mass
        assert mass["si_value"] == 1.0  # 1.0 kg/s

        # Pressure should have si_value
        inlet_pres = hot["inlet_pressure"]
        assert "si_value" in inlet_pres
        assert inlet_pres["si_value"] == 200000.0  # 200000 Pa


# ===========================================================================
# 3. TestRecursiveDepthImmutability
# ===========================================================================


class TestRecursiveDepthImmutability:
    """Domain model objects are deeply immutable after construction,
    including nested dicts, lists, and through JSON round-trips."""

    def test_field_change_freezes_nested_dict(self) -> None:
        """FieldChange with nested dict → before/after must be MappingProxyType,
        and nested must also be frozen."""
        fc = FieldChange(path="x", before={"a": {"b": 1}}, after={"a": {"b": 2}})
        assert isinstance(fc.before, types.MappingProxyType)
        assert isinstance(fc.after, types.MappingProxyType)
        # Nested dict should also be frozen
        assert isinstance(fc.before["a"], types.MappingProxyType)
        assert isinstance(fc.after["a"], types.MappingProxyType)

    def test_field_change_freezes_nested_list(self) -> None:
        """FieldChange with nested list → before/after must be tuples with frozen inner tuples."""
        fc = FieldChange(path="x", before=[1, [2, 3]], after=[4, [5, 6]])
        assert isinstance(fc.before, tuple)
        assert isinstance(fc.after, tuple)
        # Inner lists become tuples
        assert isinstance(fc.before[1], tuple)
        assert isinstance(fc.after[1], tuple)
        assert fc.before == (1, (2, 3))
        assert fc.after == (4, (5, 6))

    def test_field_change_json_round_trip_immutable(self) -> None:
        """FieldChange → serialize via RevisionDiff → deserialize → verify still frozen."""
        fc = FieldChange(
            path="x",
            before={"a": {"b": 1}},
            after=[4, [5, 6]],
        )
        rd = RevisionDiff(
            from_revision_id=UUID(int=1),
            to_revision_id=UUID(int=2),
            content_hash_before=VALID_HASH,
            content_hash_after=VALID_HASH_B,
            field_changes=(fc,),
        )
        json_str = rd.to_json()
        rd2 = RevisionDiff.from_json(json_str)
        fc2 = rd2.field_changes[0]
        assert isinstance(fc2.before, types.MappingProxyType)
        assert isinstance(fc2.before["a"], types.MappingProxyType)
        assert isinstance(fc2.after, tuple)
        assert isinstance(fc2.after[1], tuple)

    def test_message_context_freezes_nested_dict(self) -> None:
        """EngineeringMessage with nested dict in context freezes values."""
        msg = EngineeringMessage(
            code=ErrorCode.INPUT_MISSING,
            severity=EngineeringMessageSeverity.WARNING,
            message="Temperature not specified",
            context=((("k", {"nested": "dict"}),)),
        )
        assert isinstance(msg.context, tuple)
        assert isinstance(msg.context[0], tuple)
        assert isinstance(msg.context[0][1], types.MappingProxyType)

    def test_message_context_json_round_trip(self) -> None:
        """EngineeringMessage → to_json → from_json → context values still frozen."""
        msg = EngineeringMessage(
            code=ErrorCode.INPUT_MISSING,
            severity=EngineeringMessageSeverity.WARNING,
            message="test",
            # Use list values (serializable via JSON) to test round-trip
            context=((("k", [1, 2, 3]),)),
        )
        json_str = msg.to_json()
        msg2 = EngineeringMessage.from_json(json_str)
        assert isinstance(msg2.context, tuple)
        assert isinstance(msg2.context[0], tuple)
        # List in context becomes tuple after round-trip
        assert isinstance(msg2.context[0][1], tuple)
        assert msg2.context[0][1] == (1, 2, 3)

    def test_provenance_node_metadata_freezes_nested(self) -> None:
        """ProvenanceNode with nested dict in metadata → metadata values must be frozen."""
        node = ProvenanceNode(
            node_id=UUID(int=1),
            node_type=ProvenanceNodeType.CASE_REVISION,
            label="test",
            metadata=((("key", {"data": [1, 2]}),)),
            payload_hash=VALID_HASH,
        )
        assert isinstance(node.metadata, tuple)
        assert isinstance(node.metadata[0], tuple)
        assert isinstance(node.metadata[0][1], types.MappingProxyType)
        # Nested list in dict becomes tuple
        assert isinstance(node.metadata[0][1]["data"], tuple)

    def test_provenance_edge_metadata_freezes_nested(self) -> None:
        """ProvenanceEdge with nested dict in metadata → metadata values must be frozen."""
        edge = ProvenanceEdge(
            source_id=UUID(int=1),
            target_id=UUID(int=2),
            relation="triggers",
            metadata=((("key", {"data": [1, 2]}),)),
        )
        assert isinstance(edge.metadata, tuple)
        assert isinstance(edge.metadata[0], tuple)
        assert isinstance(edge.metadata[0][1], types.MappingProxyType)
        assert isinstance(edge.metadata[0][1]["data"], tuple)

    def test_deep_freeze_rejects_unknown_mutable(self) -> None:
        """deep_freeze() on a custom mutable class should raise TypeError."""

        class MyCustomContainer:
            """A truly custom mutable class that doesn't inherit from any known type."""

            def __init__(self, data: list) -> None:
                self.data = data

            def __iter__(self):  # type: ignore[override]
                return iter(self.data)

        with pytest.raises(TypeError, match="deep_freeze does not support type"):
            deep_freeze(MyCustomContainer([1, 2, 3]))

    def test_nested_mutation_attempt_after_construction(self) -> None:
        """Create FieldChange with nested dict, try to modify the inner dict → must fail."""
        fc = FieldChange(
            path="x",
            before={"a": {"b": 1}},
            after={"a": {"b": 2}},
        )
        # Can't mutate MappingProxyType
        with pytest.raises(TypeError):
            fc.before["a"]["b"] = 99  # type: ignore[index]
        # Can't add new keys
        with pytest.raises((TypeError, AttributeError)):
            fc.before["c"] = 3  # type: ignore[index]


# ===========================================================================
# 4. TestProvenancePersistenceContract
# ===========================================================================


class TestProvenancePersistenceContract:
    """InMemoryCalculationRunRepository enforces provenance graph contracts."""

    def test_empty_graph_rejected_on_add(self) -> None:
        """add() with empty provenance graph → must raise EmptyProvenanceGraphError."""
        graph = ProvenanceGraph(nodes=(), edges=())
        run = _make_calculation_run(provenance_graph=graph)
        repo = InMemoryCalculationRunRepository()
        with pytest.raises(EmptyProvenanceGraphError):
            repo.add(run)

    def test_add_requires_case_revision_node(self) -> None:
        """Graph with only CALCULATION_RUN → ProvenanceGraph rejects at construction."""
        with pytest.raises(ValueError, match="CASE_REVISION"):
            ProvenanceGraph(
                nodes=(
                    ProvenanceNode(
                        node_id=UUID(int=31),
                        node_type=ProvenanceNodeType.CALCULATION_RUN,
                        label="run",
                        payload_hash=VALID_HASH_B,
                    ),
                ),
                edges=(),
            )

    def test_add_requires_calculation_run_node(self) -> None:
        """Graph with only CASE_REVISION → ProvenanceGraph rejects at construction."""
        with pytest.raises(ValueError, match="CALCULATION_RUN"):
            ProvenanceGraph(
                nodes=(
                    ProvenanceNode(
                        node_id=UUID(int=30),
                        node_type=ProvenanceNodeType.CASE_REVISION,
                        label="rev",
                        payload_hash=VALID_HASH,
                    ),
                ),
                edges=(),
            )

    def test_succeeded_without_result_rejected(self) -> None:
        """Update run to SUCCEEDED without RESULT node → must raise ValueError."""
        # First add a PENDING run
        graph = _minimal_valid_provenance_graph()
        run = _make_calculation_run(provenance_graph=graph)
        repo = InMemoryCalculationRunRepository()
        repo.add(run)

        # Transition to RUNNING
        run_running = _make_calculation_run(
            run_id=run.run_id,
            case_id=run.case_id,
            case_revision_id=run.case_revision_id,
            status=CalculationRunStatus.RUNNING,
            provenance_graph=graph,
        )
        repo.update(run_running)

        # Try SUCCEEDED with valid result_hash but no RESULT node in graph
        run_succeeded = _make_calculation_run(
            run_id=run.run_id,
            case_id=run.case_id,
            case_revision_id=run.case_revision_id,
            status=CalculationRunStatus.SUCCEEDED,
            completed_at=datetime(2026, 1, 2, tzinfo=UTC),
            result_hash=VALID_HASH_C,
            provenance_graph=graph,
        )
        with pytest.raises(ValueError, match="RESULT node"):
            repo.update(run_succeeded)

    def test_orphan_warning_rejected(self) -> None:
        """Graph with WARNING node that has no incoming edges → OrphanProvenanceNodeError."""
        case_node = ProvenanceNode(
            node_id=UUID(int=30),
            node_type=ProvenanceNodeType.CASE_REVISION,
            label="rev",
            payload_hash=VALID_HASH,
        )
        calc_node = ProvenanceNode(
            node_id=UUID(int=31),
            node_type=ProvenanceNodeType.CALCULATION_RUN,
            label="run",
            payload_hash=VALID_HASH_B,
        )
        warn_node = ProvenanceNode(
            node_id=UUID(int=32),
            node_type=ProvenanceNodeType.WARNING,
            label="warn",
            payload_hash=VALID_HASH_C,
        )
        edge = ProvenanceEdge(
            source_id=UUID(int=30),
            target_id=UUID(int=31),
            relation="triggers",
        )
        # WARNING node has no incoming edge
        graph = ProvenanceGraph(
            nodes=(case_node, calc_node, warn_node),
            edges=(edge,),
        )
        run = _make_calculation_run(provenance_graph=graph)
        repo = InMemoryCalculationRunRepository()
        with pytest.raises(OrphanProvenanceNodeError):
            repo.add(run)

    def test_orphan_blocker_rejected(self) -> None:
        """Graph with BLOCKER node that has no incoming edges → OrphanProvenanceNodeError."""
        case_node = ProvenanceNode(
            node_id=UUID(int=30),
            node_type=ProvenanceNodeType.CASE_REVISION,
            label="rev",
            payload_hash=VALID_HASH,
        )
        calc_node = ProvenanceNode(
            node_id=UUID(int=31),
            node_type=ProvenanceNodeType.CALCULATION_RUN,
            label="run",
            payload_hash=VALID_HASH_B,
        )
        blocker_node = ProvenanceNode(
            node_id=UUID(int=32),
            node_type=ProvenanceNodeType.BLOCKER,
            label="blocker",
            payload_hash=VALID_HASH_C,
        )
        edge = ProvenanceEdge(
            source_id=UUID(int=30),
            target_id=UUID(int=31),
            relation="triggers",
        )
        # BLOCKER node has no incoming edge
        graph = ProvenanceGraph(
            nodes=(case_node, calc_node, blocker_node),
            edges=(edge,),
        )
        run = _make_calculation_run(provenance_graph=graph)
        repo = InMemoryCalculationRunRepository()
        with pytest.raises(OrphanProvenanceNodeError):
            repo.add(run)

    def test_warning_with_valid_upstream_accepted(self) -> None:
        """Graph with WARNING node that has incoming edge from CALCULATION_RUN → OK."""
        case_node = ProvenanceNode(
            node_id=UUID(int=30),
            node_type=ProvenanceNodeType.CASE_REVISION,
            label="rev",
            payload_hash=VALID_HASH,
        )
        calc_node = ProvenanceNode(
            node_id=UUID(int=31),
            node_type=ProvenanceNodeType.CALCULATION_RUN,
            label="run",
            payload_hash=VALID_HASH_B,
        )
        warn_node = ProvenanceNode(
            node_id=UUID(int=32),
            node_type=ProvenanceNodeType.WARNING,
            label="warn",
            payload_hash=VALID_HASH_C,
        )
        edge1 = ProvenanceEdge(
            source_id=UUID(int=30),
            target_id=UUID(int=31),
            relation="triggers",
        )
        edge2 = ProvenanceEdge(
            source_id=UUID(int=31),
            target_id=UUID(int=32),
            relation="triggers",
        )
        graph = ProvenanceGraph(
            nodes=(case_node, calc_node, warn_node),
            edges=(edge1, edge2),
        )
        run = _make_calculation_run(provenance_graph=graph)
        repo = InMemoryCalculationRunRepository()
        # Should succeed without raising
        repo.add(run)
        retrieved = repo.get(run.run_id)
        assert retrieved.run_id == run.run_id

    def test_blocker_from_property_call_accepted(self) -> None:
        """Graph with BLOCKER from PROPERTY_CALL → OK."""
        case_node = ProvenanceNode(
            node_id=UUID(int=30),
            node_type=ProvenanceNodeType.CASE_REVISION,
            label="rev",
            payload_hash=VALID_HASH,
        )
        calc_node = ProvenanceNode(
            node_id=UUID(int=31),
            node_type=ProvenanceNodeType.CALCULATION_RUN,
            label="run",
            payload_hash=VALID_HASH_B,
        )
        prop_node = ProvenanceNode(
            node_id=UUID(int=32),
            node_type=ProvenanceNodeType.PROPERTY_CALL,
            label="prop",
            payload_hash=VALID_HASH_C,
        )
        blocker_node = ProvenanceNode(
            node_id=UUID(int=33),
            node_type=ProvenanceNodeType.BLOCKER,
            label="blocker",
            payload_hash=VALID_HASH,
        )
        edge1 = ProvenanceEdge(
            source_id=UUID(int=30),
            target_id=UUID(int=31),
            relation="triggers",
        )
        edge2 = ProvenanceEdge(
            source_id=UUID(int=31),
            target_id=UUID(int=32),
            relation="calls",
        )
        edge3 = ProvenanceEdge(
            source_id=UUID(int=32),
            target_id=UUID(int=33),
            relation="triggers",
        )
        graph = ProvenanceGraph(
            nodes=(case_node, calc_node, prop_node, blocker_node),
            edges=(edge1, edge2, edge3),
        )
        run = _make_calculation_run(provenance_graph=graph)
        repo = InMemoryCalculationRunRepository()
        # Should succeed without raising
        repo.add(run)
        retrieved = repo.get(run.run_id)
        assert retrieved.run_id == run.run_id

    def test_warning_from_intermediate_rejected(self) -> None:
        """Graph with WARNING from INTERMEDIATE node (not in approved upstream set)
        → OrphanProvenanceNodeError."""
        case_node = ProvenanceNode(
            node_id=UUID(int=30),
            node_type=ProvenanceNodeType.CASE_REVISION,
            label="rev",
            payload_hash=VALID_HASH,
        )
        calc_node = ProvenanceNode(
            node_id=UUID(int=31),
            node_type=ProvenanceNodeType.CALCULATION_RUN,
            label="run",
            payload_hash=VALID_HASH_B,
        )
        interm_node = ProvenanceNode(
            node_id=UUID(int=32),
            node_type=ProvenanceNodeType.INTERMEDIATE,
            label="interm",
            payload_hash=VALID_HASH_C,
        )
        warn_node = ProvenanceNode(
            node_id=UUID(int=33),
            node_type=ProvenanceNodeType.WARNING,
            label="warn",
            payload_hash=VALID_HASH,
        )
        edge1 = ProvenanceEdge(
            source_id=UUID(int=30),
            target_id=UUID(int=31),
            relation="triggers",
        )
        edge2 = ProvenanceEdge(
            source_id=UUID(int=31),
            target_id=UUID(int=32),
            relation="produces",
        )
        edge3 = ProvenanceEdge(
            source_id=UUID(int=32),
            target_id=UUID(int=33),
            relation="triggers",
        )
        graph = ProvenanceGraph(
            nodes=(case_node, calc_node, interm_node, warn_node),
            edges=(edge1, edge2, edge3),
        )
        run = _make_calculation_run(provenance_graph=graph)
        repo = InMemoryCalculationRunRepository()
        with pytest.raises(OrphanProvenanceNodeError):
            repo.add(run)


# ===========================================================================
# 5. TestGitCommitValidation
# ===========================================================================


class TestGitCommitValidation:
    """CalculationRun.git_commit validates: 7-40 hex or exactly 'no-git'."""

    def _base_run_kwargs(self, git_commit: str) -> dict:
        """Return minimal CalculationRun kwargs with the given git_commit."""
        return dict(
            run_id=FIXED_IDS[35],
            case_id=FIXED_IDS[0],
            case_revision_id=FIXED_IDS[1],
            run_type=CalculationRunType.SCREEN,
            status=CalculationRunStatus.PENDING,
            started_at=FIXED_NOW,
            input_hash=VALID_HASH,
            git_commit=git_commit,
            provenance_graph=_minimal_valid_provenance_graph(),
        )

    def test_valid_hex_sha_accepted(self) -> None:
        """git_commit='abcdef01234567890' (17 chars hex) → OK."""
        run = CalculationRun(**self._base_run_kwargs("abcdef01234567890"))
        assert run.git_commit == "abcdef01234567890"

    def test_no_git_sentinel_accepted(self) -> None:
        """git_commit='no-git' → OK."""
        run = CalculationRun(**self._base_run_kwargs("no-git"))
        assert run.git_commit == "no-git"

    def test_empty_string_rejected(self) -> None:
        """git_commit='' → ValidationError."""
        with pytest.raises(ValidationError):
            CalculationRun(**self._base_run_kwargs(""))

    def test_short_hex_rejected(self) -> None:
        """git_commit='abc123' (6 chars) → ValidationError."""
        with pytest.raises(ValidationError):
            CalculationRun(**self._base_run_kwargs("abc123"))

    def test_long_hex_rejected(self) -> None:
        """git_commit='a' * 41 → ValidationError."""
        with pytest.raises(ValidationError):
            CalculationRun(**self._base_run_kwargs("a" * 41))

    def test_non_hex_rejected(self) -> None:
        """git_commit='xyz1234' → ValidationError."""
        with pytest.raises(ValidationError):
            CalculationRun(**self._base_run_kwargs("xyz1234"))

    def test_mixed_case_normalized(self) -> None:
        """git_commit='ABCDef01' → stored as 'abcdef01'."""
        run = CalculationRun(**self._base_run_kwargs("ABCDef01"))
        assert run.git_commit == "abcdef01"

    def test_git_commit_json_round_trip(self) -> None:
        """Construction → to_json → from_json → git_commit preserved."""
        run = CalculationRun(**self._base_run_kwargs("abcdef01234567890"))
        json_str = run.to_json()
        run2 = CalculationRun.from_json(json_str)
        assert run2.git_commit == "abcdef01234567890"
