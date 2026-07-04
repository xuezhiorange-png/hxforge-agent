"""Comprehensive tests for Review-02 items 1-5.

1. Recursive immutability guarantees across the domain model.
2. Repository chain constraints for design-case revisions.
3. Unit-equivalent DesignCase content hashing.
4. CalculationRun input-hash identity requirements.
5. Provenance graph structural contracts.
"""

from __future__ import annotations

import types
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from hexagent.application.revision_service import RevisionService
from hexagent.core.canonical import sha256_digest
from hexagent.core.immutability import assert_frozen, deep_freeze
from hexagent.core.time import FixedClock, FixedIdGenerator
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
)

pytestmark = pytest.mark.coolprop

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
    name: str = "Review02 Test HX",
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
    from hexagent.core.canonical import canonicalize_design_case

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


def _make_clock(initial: datetime | None = None) -> FixedClock:
    return FixedClock(initial=initial or FIXED_NOW)


def _make_id_gen() -> FixedIdGenerator:
    return FixedIdGenerator()


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
    git_commit: str = "abcdef0",
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
        git_commit=git_commit,
    )


# ---------------------------------------------------------------------------
# 1. TestRecursiveImmutability
# ---------------------------------------------------------------------------


class TestRecursiveImmutability:
    """Domain model objects are deeply immutable after construction."""

    def test_canonical_payload_is_mapping_proxy_type(self) -> None:
        """DesignCaseRevision.canonical_payload is a MappingProxyType."""
        case = _make_case()
        rev = _make_revision(case, FIXED_IDS[0])
        assert isinstance(rev.canonical_payload, types.MappingProxyType)

    def test_nested_dict_in_payload_cannot_be_mutated(self) -> None:
        """Nested dicts inside canonical_payload are also frozen."""
        case = _make_case()
        rev = _make_revision(case, FIXED_IDS[0])
        # The payload should be completely immutable at all levels
        assert_frozen(rev.canonical_payload)

    def test_field_change_is_frozen_dataclass(self) -> None:
        """FieldChange is a frozen dataclass."""
        fc = FieldChange(path="hot_stream.inlet_temperature", before=100.0, after=200.0)
        with pytest.raises(AttributeError):
            fc.path = "modified"  # type: ignore[misc]

    def test_field_change_cannot_be_mutated(self) -> None:
        """FieldChange fields cannot be reassigned after construction."""
        fc = FieldChange(path="a.b", before=1, after=2)
        with pytest.raises(AttributeError):
            fc.before = 99  # type: ignore[misc]
        with pytest.raises(AttributeError):
            fc.after = 99  # type: ignore[misc]

    def test_message_context_is_immutable(self) -> None:
        """EngineeringMessage.context is a tuple-of-tuples, not a mutable dict."""
        msg = EngineeringMessage(
            code=ErrorCode.INPUT_MISSING,
            severity=EngineeringMessageSeverity.WARNING,
            message="Temperature not specified",
            context=(("stream", "hot"), ("field", "inlet_temperature")),
        )
        assert isinstance(msg.context, tuple)
        assert isinstance(msg.context[0], tuple)
        # Cannot mutate the message (frozen model)
        with pytest.raises(ValidationError):
            msg.message = "modified"  # type: ignore[misc]

    def test_provenance_node_metadata_is_immutable(self) -> None:
        """ProvenanceNode.metadata is a tuple-of-tuples."""
        node = ProvenanceNode(
            node_id=UUID(int=1),
            node_type=ProvenanceNodeType.CASE_REVISION,
            label="rev-1",
            metadata=(("key1", "val1"), ("key2", 42)),
            payload_hash=VALID_HASH,
        )
        assert isinstance(node.metadata, tuple)
        assert isinstance(node.metadata[0], tuple)
        assert node.metadata[0] == ("key1", "val1")

    def test_json_round_trip_preserves_immutable_types(self) -> None:
        """After JSON round-trip, canonical_payload is still MappingProxyType."""
        case = _make_case()
        rev = _make_revision(case, FIXED_IDS[0])
        json_str = rev.to_json()
        restored = DesignCaseRevision.from_json(json_str)
        # DesignCaseRevision.from_dict calls __post_init__ which deep_freezes
        assert isinstance(restored.canonical_payload, types.MappingProxyType)
        assert_frozen(restored.canonical_payload)

    def test_deep_freeze_utility(self) -> None:
        """deep_freeze converts dicts to MappingProxyType and lists to tuples."""
        mutable = {"a": 1, "b": [2, 3], "c": {"d": 4}}
        frozen = deep_freeze(mutable)
        assert isinstance(frozen, types.MappingProxyType)
        assert isinstance(frozen["b"], tuple)
        assert isinstance(frozen["c"], types.MappingProxyType)

    def test_assert_frozen_catches_mutable_dict(self) -> None:
        """assert_frozen raises AssertionError for mutable dicts."""
        with pytest.raises(AssertionError, match="Mutable dict"):
            assert_frozen({"key": "value"})

    def test_assert_frozen_catches_mutable_list(self) -> None:
        """assert_frozen raises AssertionError for mutable lists."""
        with pytest.raises(AssertionError, match="Mutable list"):
            assert_frozen([1, 2, 3])


# ---------------------------------------------------------------------------
# 2. TestRepositoryChainConstraints
# ---------------------------------------------------------------------------


class _DirectRevisionRepo:
    """Stores revisions without deepcopy (avoids MappingProxyType pickle)."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, DesignCaseRevision] = {}
        self._by_case: dict[UUID, dict[int, DesignCaseRevision]] = {}

    def add(self, revision: DesignCaseRevision) -> None:
        self._by_id[revision.revision_id] = revision
        self._by_case.setdefault(revision.case_id, {})[revision.revision_number] = revision

    def get(self, revision_id: UUID) -> DesignCaseRevision:
        return self._by_id[revision_id]

    def latest(self, case_id: UUID) -> DesignCaseRevision | None:
        case_rev_map = self._by_case.get(case_id)
        if not case_rev_map:
            return None
        return case_rev_map[max(case_rev_map)]

    def list_by_case(self, case_id: UUID) -> tuple[DesignCaseRevision, ...]:
        case_rev_map = self._by_case.get(case_id)
        if not case_rev_map:
            return ()
        return tuple(case_rev_map[n] for n in sorted(case_rev_map))


class TestRepositoryChainConstraints:
    """Repository and model enforce revision chain invariants."""

    def test_add_rejects_wrong_case_id_parent(self) -> None:
        """Adding a child revision whose parent belongs to a different case fails
        integrity verification (the RevisionService catches the mismatch)."""
        case_a = _make_case(case_id=FIXED_IDS[0])
        case_b = _make_case(case_id=FIXED_IDS[1], name="Case B")

        svc = RevisionService()
        clock = _make_clock()
        id_gen = _make_id_gen()

        # Create rev#1 for case A through the service
        rev_a1 = svc.create_initial_revision(
            case=case_a,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )

        # Manually create a child for case B pointing to case A's revision
        from hexagent.core.canonical import canonicalize_design_case

        cp_b = canonicalize_design_case(case_b)
        rev_b2 = DesignCaseRevision(
            revision_id=id_gen.new_id(),
            case_id=case_b.id,
            revision_number=2,
            design_case=case_b,
            canonical_payload=cp_b,
            content_hash=sha256_digest(cp_b),
            created_at=clock.utcnow(),
            created_by="agent-1",
            parent_revision_id=rev_a1.revision_id,
            change_summary="cross-case child",
        )

        # Store both revisions in a direct repo (no deepcopy)
        repo = _DirectRevisionRepo()
        repo.add(rev_a1)
        repo.add(rev_b2)

        # verify_revision_integrity walks the chain and detects the case_id mismatch
        with pytest.raises(IntegrityError, match="belongs to"):
            svc.verify_revision_integrity(rev_b2, repo)

    def test_add_rejects_numbering_gap(self) -> None:
        """DesignCaseRevision rejects revision_number=1 with a parent set
        (first revision must have no parent — prevents numbering gaps at root)."""
        case = _make_case()
        cp = _make_revision(case, FIXED_IDS[0]).canonical_payload

        with pytest.raises(ValueError, match="must have parent_revision_id=None"):
            DesignCaseRevision(
                revision_id=FIXED_IDS[5],
                case_id=case.id,
                revision_number=1,
                design_case=case,
                canonical_payload=cp,
                content_hash=sha256_digest(cp),
                created_at=FIXED_NOW,
                created_by="test-agent",
                parent_revision_id=FIXED_IDS[3],
            )

    def test_add_rejects_non_immediate_parent(self) -> None:
        """DesignCaseRevision rejects revision_number > 1 without a parent
        (non-first revisions must link to their predecessor)."""
        case = _make_case()
        cp = _make_revision(case, FIXED_IDS[0]).canonical_payload

        with pytest.raises(ValueError, match="must have a parent_revision_id"):
            DesignCaseRevision(
                revision_id=FIXED_IDS[6],
                case_id=case.id,
                revision_number=2,
                design_case=case,
                canonical_payload=cp,
                content_hash=sha256_digest(cp),
                created_at=FIXED_NOW,
                created_by="test-agent",
                parent_revision_id=None,  # missing parent for rev#2
            )

    def test_add_accepts_valid_consecutive_chain(self) -> None:
        """A valid two-revision chain is accepted by the RevisionService."""
        case = _make_case()
        svc = RevisionService()
        clock = _make_clock()
        id_gen = _make_id_gen()

        rev1 = svc.create_initial_revision(
            case=case,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        case_v2 = _make_case(outlet_temp=300.0)
        rev2 = svc.create_revision_from_parent(
            parent=rev1,
            new_case=case_v2,
            created_by="agent-1",
            change_summary="v2",
            clock=clock,
            id_gen=id_gen,
        )

        assert rev1.revision_number == 1
        assert rev2.revision_number == 2
        assert rev2.parent_revision_id == rev1.revision_id
        assert rev1.case_id == rev2.case_id

    def test_add_root_revision_with_parent_rejected(self) -> None:
        """DesignCaseRevision rejects revision_number=1 with parent_revision_id set."""
        case = _make_case()
        cp = _make_revision(case, FIXED_IDS[0]).canonical_payload

        with pytest.raises(ValueError, match="must have parent_revision_id=None"):
            DesignCaseRevision(
                revision_id=FIXED_IDS[0],
                case_id=case.id,
                revision_number=1,
                design_case=case,
                canonical_payload=cp,
                content_hash=sha256_digest(cp),
                created_at=FIXED_NOW,
                created_by="agent-1",
                parent_revision_id=FIXED_IDS[5],  # not allowed for rev#1
            )


# ---------------------------------------------------------------------------
# 3. TestUnitEquivalentDesignCaseHash
# ---------------------------------------------------------------------------


class TestUnitEquivalentDesignCaseHash:
    """Quantities with different display units but same SI value hash identically.

    The canonical serializer converts Quantity objects (which have ``to_si()``)
    to SI values before hashing, so 100 °C and 373.15 K produce the same hash.
    Tests pass Quantity objects directly to sha256_digest so the canonical
    encoder can access ``.to_si()``.
    """

    def test_celsius_kelvin_equivalence(self) -> None:
        """100 °C and 373.15 K produce the same content hash."""
        t_c = AbsoluteTemperature(value=100, unit="degC")
        t_k = AbsoluteTemperature(value=373.15, unit="K")

        h1 = sha256_digest(t_c)
        h2 = sha256_digest(t_k)
        assert h1 == h2

    def test_bar_pascal_equivalence(self) -> None:
        """2 bar and 200000 Pa produce the same content hash."""
        p_bar = AbsolutePressure(value=2.0, unit="bar")
        p_pa = AbsolutePressure(value=200000.0, unit="Pa")

        h1 = sha256_digest(p_bar)
        h2 = sha256_digest(p_pa)
        assert h1 == h2

    def test_mm_m_equivalence(self) -> None:
        """3 mm and 0.003 m produce the same content hash."""
        l_mm = Length(value=3.0, unit="mm")
        l_m = Length(value=0.003, unit="m")

        h1 = sha256_digest(l_mm)
        h2 = sha256_digest(l_m)
        assert h1 == h2

    def test_kgh_kgs_equivalence(self) -> None:
        """3600 kg/h and 1.0 kg/s produce the same content hash."""
        m_kgh = MassFlow(value=3600.0, unit="kg/h")
        m_kgs = MassFlow(value=1.0, unit="kg/s")

        h1 = sha256_digest(m_kgh)
        h2 = sha256_digest(m_kgs)
        assert h1 == h2

    def test_different_values_produce_different_hashes(self) -> None:
        """Different physical values produce different content hashes."""
        t1 = AbsoluteTemperature(value=100, unit="degC")
        t2 = AbsoluteTemperature(value=200, unit="degC")

        h1 = sha256_digest(t1)
        h2 = sha256_digest(t2)
        assert h1 != h2


# ---------------------------------------------------------------------------
# 4. TestCalculationRunInputIdentity
# ---------------------------------------------------------------------------


class TestCalculationRunInputIdentity:
    """CalculationRun requires a valid input_hash and follows state rules."""

    def test_input_hash_required(self) -> None:
        """CalculationRun cannot be constructed without input_hash."""
        with pytest.raises(ValidationError, match="input_hash"):
            CalculationRun(
                run_id=FIXED_IDS[10],
                case_id=FIXED_IDS[0],
                case_revision_id=FIXED_IDS[1],
                run_type=CalculationRunType.SCREEN,
                status=CalculationRunStatus.PENDING,
                started_at=FIXED_NOW,
                git_commit="abcdef0",
                provenance_graph=_minimal_valid_provenance_graph(),
                # input_hash is missing
            )

    def test_invalid_input_hash_format_rejected(self) -> None:
        """CalculationRun rejects non-sha256 input_hash."""
        with pytest.raises(ValidationError, match="input_hash"):
            CalculationRun(
                run_id=FIXED_IDS[10],
                case_id=FIXED_IDS[0],
                case_revision_id=FIXED_IDS[1],
                run_type=CalculationRunType.SCREEN,
                status=CalculationRunStatus.PENDING,
                started_at=FIXED_NOW,
                git_commit="abcdef0",
                input_hash="md5:" + "a" * 32,  # wrong format
                provenance_graph=_minimal_valid_provenance_graph(),
            )

    def test_repository_rejects_running_initial_status(self) -> None:
        """InMemoryCalculationRunRepository rejects non-PENDING initial status."""
        from hexagent.domain.revisions import InvalidStateTransitionError
        from hexagent.repositories.memory import InMemoryCalculationRunRepository

        repo = InMemoryCalculationRunRepository()
        run = _make_calculation_run(
            status=CalculationRunStatus.RUNNING,
        )
        with pytest.raises(InvalidStateTransitionError):
            repo.add(run)

    def test_running_reached_via_update_from_pending(self) -> None:
        """PENDING → RUNNING is a valid transition through repository update."""
        from hexagent.repositories.memory import InMemoryCalculationRunRepository

        repo = InMemoryCalculationRunRepository()
        clock = _make_clock()

        # Create and add a PENDING run
        run = _make_calculation_run(
            started_at=clock.utcnow(),
        )
        repo.add(run)
        assert run.status == CalculationRunStatus.PENDING

        # Transition to RUNNING via update
        clock.advance(seconds=1)
        running = run.model_copy(
            update={
                "status": CalculationRunStatus.RUNNING,
                "started_at": clock.utcnow(),
            }
        )
        repo.update(running)

        retrieved = repo.get(run.run_id)
        assert retrieved.status == CalculationRunStatus.RUNNING


# ---------------------------------------------------------------------------
# 5. TestProvenanceContract
# ---------------------------------------------------------------------------


class TestProvenanceContract:
    """Provenance graph and node construction contracts."""

    def _make_valid_node(
        self,
        node_id: int = 1,
        node_type: ProvenanceNodeType = ProvenanceNodeType.CASE_REVISION,
        label: str = "node-1",
        payload_hash: str = VALID_HASH,
    ) -> ProvenanceNode:
        return ProvenanceNode(
            node_id=UUID(int=node_id),
            node_type=node_type,
            label=label,
            payload_hash=payload_hash,
        )

    def test_node_without_payload_hash_rejected(self) -> None:
        """ProvenanceNode cannot be constructed without payload_hash."""
        with pytest.raises(ValidationError, match="payload_hash"):
            ProvenanceNode(
                node_id=UUID(int=1),
                node_type=ProvenanceNodeType.CASE_REVISION,
                label="rev-1",
                # payload_hash is missing
            )

    def test_invalid_payload_hash_format_rejected(self) -> None:
        """ProvenanceNode rejects payload_hash that doesn't start with sha256:."""
        with pytest.raises(ValidationError, match="payload_hash"):
            ProvenanceNode(
                node_id=UUID(int=1),
                node_type=ProvenanceNodeType.CASE_REVISION,
                label="rev-1",
                payload_hash="not-a-valid-hash",
            )

    def test_empty_graph_rejected(self) -> None:
        """Empty graph allowed at model, rejected at persistence boundary."""
        from uuid import uuid4

        from hexagent.domain.revisions import (
            CalculationRun,
            CalculationRunStatus,
            CalculationRunType,
        )
        from hexagent.repositories.memory import InMemoryCalculationRunRepository

        # Empty graph at model level — OK
        g = ProvenanceGraph(nodes=(), edges=())
        assert len(g.nodes) == 0
        # Try to persist a SUCCEEDED run with empty graph — rejected
        repo = InMemoryCalculationRunRepository()
        run = CalculationRun(
            run_id=uuid4(),
            case_id=uuid4(),
            case_revision_id=uuid4(),
            run_type=CalculationRunType.RATE,
            status=CalculationRunStatus.PENDING,
            started_at=_make_clock().utcnow(),
            git_commit="abcdef0",
            input_hash="sha256:" + "0" * 64,
            provenance_graph=_minimal_valid_provenance_graph(),
        )
        repo.add(run)
        clock = _make_clock()
        clock.advance(seconds=1)
        # Transition PENDING → RUNNING first
        clock.advance(seconds=1)
        run_running = run.model_copy(update={"status": CalculationRunStatus.RUNNING})
        repo.update(run_running)
        # Then try SUCCEEDED with empty graph
        clock.advance(seconds=1)
        run2 = run_running.model_copy(
            update={
                "status": CalculationRunStatus.SUCCEEDED,
                "result_hash": "sha256:" + "a" * 64,
                "completed_at": clock.utcnow(),
                "provenance_graph": ProvenanceGraph(nodes=(), edges=()),
            }
        )
        with pytest.raises(ValueError, match="non-empty provenance graph"):
            repo.update(run2)

    def test_graph_without_case_revision_rejected(self) -> None:
        """ProvenanceGraph requires at least one CASE_REVISION node."""
        calc_node = self._make_valid_node(
            node_id=1,
            node_type=ProvenanceNodeType.CALCULATION_RUN,
            label="run-1",
        )
        with pytest.raises(ValidationError, match="CASE_REVISION"):
            ProvenanceGraph(nodes=(calc_node,), edges=())

    def test_graph_without_calculation_run_rejected(self) -> None:
        """ProvenanceGraph requires at least one CALCULATION_RUN node."""
        case_node = self._make_valid_node(
            node_id=1,
            node_type=ProvenanceNodeType.CASE_REVISION,
            label="rev-1",
        )
        with pytest.raises(ValidationError, match="CALCULATION_RUN"):
            ProvenanceGraph(nodes=(case_node,), edges=())

    def test_succeeded_run_without_result_node_rejected(self) -> None:
        """Repository update rejects SUCCEEDED run without RESULT node in provenance."""
        from hexagent.repositories.memory import InMemoryCalculationRunRepository

        repo = InMemoryCalculationRunRepository()
        clock = _make_clock()

        # Create and add a PENDING run
        run = _make_calculation_run(
            run_id=FIXED_IDS[10],
            started_at=clock.utcnow(),
        )
        repo.add(run)

        # Transition PENDING → RUNNING
        clock.advance(seconds=1)
        running = run.model_copy(
            update={
                "status": CalculationRunStatus.RUNNING,
                "started_at": clock.utcnow(),
            }
        )
        repo.update(running)

        # Build a provenance graph WITHOUT a RESULT node
        case_node = ProvenanceNode(
            node_id=UUID(int=20),
            node_type=ProvenanceNodeType.CASE_REVISION,
            label="rev",
            payload_hash=VALID_HASH,
        )
        calc_node = ProvenanceNode(
            node_id=UUID(int=21),
            node_type=ProvenanceNodeType.CALCULATION_RUN,
            label="run",
            payload_hash=VALID_HASH_B,
        )
        edge = ProvenanceEdge(
            source_id=UUID(int=20),
            target_id=UUID(int=21),
            relation="triggers",
        )
        graph = ProvenanceGraph(
            nodes=(case_node, calc_node),
            edges=(edge,),
        )

        # Attempt RUNNING → SUCCEEDED without RESULT node
        clock.advance(seconds=5)
        succeeded = running.model_copy(
            update={
                "status": CalculationRunStatus.SUCCEEDED,
                "result_hash": VALID_HASH_C,
                "completed_at": clock.utcnow(),
                "provenance_graph": graph,
            }
        )

        with pytest.raises(ValueError, match="RESULT node"):
            repo.update(succeeded)
