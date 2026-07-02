"""Integration tests for the full RevisionService → RunService workflow.

End-to-end: create a design case, make revisions, create a run, transition
through the run lifecycle, and verify integrity.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from hexagent.application.revision_service import RevisionService
from hexagent.application.run_service import RunService
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
    CalculationRunStatus,
    CalculationRunType,
    DuplicateIdError,
    InvalidStateTransitionError,
)
from hexagent.repositories.memory import (
    InMemoryCalculationRunRepository,
    InMemoryDesignCaseRevisionRepository,
)

pytestmark = pytest.mark.integration


def _make_minimal_graph() -> ProvenanceGraph:
    """Minimal provenance graph with CASE_REVISION + CALCULATION_RUN."""
    ph = "sha256:" + "a" * 64
    case_node = ProvenanceNode(
        node_id=UUID(int=100),
        node_type=ProvenanceNodeType.CASE_REVISION,
        payload_hash=ph,
    )
    run_node = ProvenanceNode(
        node_id=UUID(int=200),
        node_type=ProvenanceNodeType.CALCULATION_RUN,
        payload_hash=ph,
    )
    return ProvenanceGraph(
        nodes=(case_node, run_node),
        edges=(
            ProvenanceEdge(
                source_id=UUID(int=100),
                target_id=UUID(int=200),
                relation="triggers",
            ),
        ),
    )


def _make_succeeded_graph() -> ProvenanceGraph:
    """Provenance graph with CASE_REVISION + CALCULATION_RUN + RESULT."""
    ph = "sha256:" + "a" * 64
    case_node = ProvenanceNode(
        node_id=UUID(int=100),
        node_type=ProvenanceNodeType.CASE_REVISION,
        payload_hash=ph,
    )
    run_node = ProvenanceNode(
        node_id=UUID(int=200),
        node_type=ProvenanceNodeType.CALCULATION_RUN,
        payload_hash=ph,
    )
    result_node = ProvenanceNode(
        node_id=UUID(int=300),
        node_type=ProvenanceNodeType.RESULT,
        payload_hash=ph,
    )
    return ProvenanceGraph(
        nodes=(case_node, run_node, result_node),
        edges=(
            ProvenanceEdge(source_id=UUID(int=100), target_id=UUID(int=200), relation="triggers"),
            ProvenanceEdge(source_id=UUID(int=200), target_id=UUID(int=300), relation="produces"),
        ),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXED_IDS = [UUID(int=i) for i in range(1, 30)]


def _make_fluid(name: str = "Water") -> FluidSpec:
    return FluidSpec(backend="CoolProp", name=name)


def _make_fouling_source() -> FoulingSource:
    return FoulingSource(
        source_type=FoulingSourceType.STANDARD,
        reference_id="TEMA",
        edition="2019",
        table_or_clause="Table RGP-K-2",
        verification_status=VerificationStatus.VERIFIED,
        note="Clean water",
    )


def _make_stream(
    *,
    name: str = "Water",
    mass_flow: float = 1.0,
    inlet_temp: float = 350.0,
    outlet_temp: float = 310.0,
    inlet_pressure: float = 200000.0,
) -> StreamSpec:
    return StreamSpec(
        fluid=_make_fluid(name),
        mass_flow=MassFlow(value=mass_flow, unit="kg/s"),
        inlet_temperature=AbsoluteTemperature(value=inlet_temp, unit="K"),
        inlet_pressure=AbsolutePressure(value=inlet_pressure, unit="Pa"),
        fouling_resistance=FoulingResistanceSpec(
            value=FoulingResistance(value=0.0002, unit="m^2*K/W"),
            source=_make_fouling_source(),
        ),
        outlet_temperature=AbsoluteTemperature(value=outlet_temp, unit="K"),
    )


def _make_case(case_id: UUID | None = None, outlet_temp: float = 310.0) -> DesignCase:
    return DesignCase(
        id=case_id or FIXED_IDS[0],
        name="Integration Test HX",
        hot_stream=_make_stream(inlet_temp=350.0, outlet_temp=outlet_temp),
        cold_stream=_make_stream(inlet_temp=290.0, outlet_temp=330.0, mass_flow=0.8),
        constraints=DesignConstraints(
            design_pressure_hot=AbsolutePressure(value=250000.0, unit="Pa"),
            design_pressure_cold=AbsolutePressure(value=200000.0, unit="Pa"),
            design_temperature_hot=AbsoluteTemperature(value=370.0, unit="K"),
            design_temperature_cold=AbsoluteTemperature(value=350.0, unit="K"),
            corrosion_allowance=Length(value=0.003, unit="m"),
            required_area_margin_fraction=0.1,
        ),
    )


@pytest.fixture()
def clock() -> FixedClock:
    return FixedClock(initial=datetime(2026, 1, 1, tzinfo=UTC))


@pytest.fixture()
def id_gen() -> FixedIdGenerator:
    return FixedIdGenerator()


@pytest.fixture()
def rev_repo() -> InMemoryDesignCaseRevisionRepository:
    return InMemoryDesignCaseRevisionRepository()


@pytest.fixture()
def run_repo() -> InMemoryCalculationRunRepository:
    return InMemoryCalculationRunRepository()


@pytest.fixture()
def rev_service() -> RevisionService:
    return RevisionService()


@pytest.fixture()
def run_service(
    rev_repo: InMemoryDesignCaseRevisionRepository,
    run_repo: InMemoryCalculationRunRepository,
) -> RunService:
    return RunService(run_repo=run_repo, revision_repo=rev_repo)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFullRevisionWorkflow:
    """End-to-end: create case → initial revision → child revision."""

    def test_create_initial_revision(
        self,
        rev_service: RevisionService,
        rev_repo: InMemoryDesignCaseRevisionRepository,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        case = _make_case()
        rev = rev_service.create_initial_revision(
            case=case,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev)

        assert rev.revision_number == 1
        assert rev.parent_revision_id is None
        assert rev.case_id == case.id
        assert rev.created_by == "agent-1"
        assert rev.created_at == clock.utcnow()

    def test_create_child_revision(
        self,
        rev_service: RevisionService,
        rev_repo: InMemoryDesignCaseRevisionRepository,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        case_v1 = _make_case()
        rev1 = rev_service.create_initial_revision(
            case=case_v1,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev1)

        # Mutate the case
        case_v2 = _make_case(outlet_temp=300.0)
        rev2 = rev_service.create_revision_from_parent(
            parent=rev1,
            new_case=case_v2,
            created_by="agent-1",
            change_summary="Lowered outlet temp",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev2)

        assert rev2.revision_number == 2
        assert rev2.parent_revision_id == rev1.revision_id
        assert rev2.change_summary == "Lowered outlet temp"

    def test_revision_history(
        self,
        rev_service: RevisionService,
        rev_repo: InMemoryDesignCaseRevisionRepository,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        case = _make_case()
        rev1 = rev_service.create_initial_revision(
            case=case,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev1)

        case2 = _make_case(outlet_temp=300.0)
        rev2 = rev_service.create_revision_from_parent(
            parent=rev1,
            new_case=case2,
            created_by="agent-1",
            change_summary="v2",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev2)

        history = rev_service.get_revision_history(case.id, rev_repo)
        assert len(history) == 2
        assert history[0].revision_number == 1
        assert history[1].revision_number == 2

    def test_verify_revision_integrity(
        self,
        rev_service: RevisionService,
        rev_repo: InMemoryDesignCaseRevisionRepository,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        case = _make_case()
        rev = rev_service.create_initial_revision(
            case=case,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev)
        assert rev_service.verify_revision_integrity(rev, rev_repo) is True

    def test_wrong_case_id_rejected(
        self,
        rev_service: RevisionService,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        case1 = _make_case(case_id=FIXED_IDS[0])
        rev1 = rev_service.create_initial_revision(
            case=case1,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        case2_wrong = _make_case(case_id=FIXED_IDS[1])
        with pytest.raises(ValueError, match="does not match"):
            rev_service.create_revision_from_parent(
                parent=rev1,
                new_case=case2_wrong,
                created_by="agent-1",
                change_summary="wrong case",
                clock=clock,
                id_gen=id_gen,
            )

    def test_duplicate_revision_rejected(
        self,
        rev_service: RevisionService,
        rev_repo: InMemoryDesignCaseRevisionRepository,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        case = _make_case()
        rev1 = rev_service.create_initial_revision(
            case=case,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev1)
        with pytest.raises(DuplicateIdError):
            rev_repo.add(rev1)  # same revision again


class TestFullRunWorkflow:
    """End-to-end: revision → create run → transition through lifecycle."""

    def test_succeeded_run_lifecycle(
        self,
        rev_service: RevisionService,
        run_service: RunService,
        rev_repo: InMemoryDesignCaseRevisionRepository,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        # 1. Create a revision
        case = _make_case()
        rev = rev_service.create_initial_revision(
            case=case,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev)

        # 2. Create a PENDING run
        run = run_service.create_run(
            case_revision_id=rev.revision_id,
            run_type=CalculationRunType.SCREEN,
            software_version="0.1.0",
            git_commit="abcdef0",
            clock=clock,
            id_gen=id_gen,
            provenance_graph=_make_succeeded_graph(),
        )
        assert run.status == CalculationRunStatus.PENDING

        # 3. Start → RUNNING
        clock.advance(seconds=1)
        run = run_service.start_run(run, clock)
        assert run.status == CalculationRunStatus.RUNNING

        # 4. Succeed
        clock.advance(seconds=5)
        run = run_service.succeed_run(
            run,
            result_hash="sha256:" + "a" * 64,
            clock=clock,
        )
        assert run.status == CalculationRunStatus.SUCCEEDED
        assert run.completed_at is not None
        assert run.completed_at > run.started_at

    def test_failed_run_lifecycle(
        self,
        rev_service: RevisionService,
        run_service: RunService,
        rev_repo: InMemoryDesignCaseRevisionRepository,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        case = _make_case()
        rev = rev_service.create_initial_revision(
            case=case,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev)

        run = run_service.create_run(
            case_revision_id=rev.revision_id,
            run_type=CalculationRunType.SIZE,
            software_version="0.1.0",
            git_commit="no-git",
            clock=clock,
            id_gen=id_gen,
            provenance_graph=_make_minimal_graph(),
        )
        clock.advance(seconds=1)
        run = run_service.start_run(run, clock)

        failure = RunFailure(
            code=ErrorCode.CALCULATION_NOT_CONVERGED,
            message="Solver diverged after 50 iterations",
        )
        clock.advance(seconds=3)
        run = run_service.fail_run(run, failure=failure, clock=clock)
        assert run.status == CalculationRunStatus.FAILED
        assert run.failure is not None
        assert run.failure.code == ErrorCode.CALCULATION_NOT_CONVERGED

    def test_blocked_run_lifecycle(
        self,
        rev_service: RevisionService,
        run_service: RunService,
        rev_repo: InMemoryDesignCaseRevisionRepository,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        case = _make_case()
        rev = rev_service.create_initial_revision(
            case=case,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev)

        run = run_service.create_run(
            case_revision_id=rev.revision_id,
            run_type=CalculationRunType.SIZE,
            software_version="0.1.0",
            git_commit="no-git",
            clock=clock,
            id_gen=id_gen,
            provenance_graph=_make_minimal_graph(),
        )
        clock.advance(seconds=1)
        run = run_service.start_run(run, clock)

        blocker = EngineeringMessage(
            code=ErrorCode.PROPERTY_UNAVAILABLE,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="Fluid properties not available for the given state",
        )
        clock.advance(seconds=1)
        run = run_service.block_run(run, blockers=(blocker,), clock=clock)
        assert run.status == CalculationRunStatus.BLOCKED
        assert len(run.blockers) == 1

    def test_cancelled_from_pending(
        self,
        rev_service: RevisionService,
        run_service: RunService,
        rev_repo: InMemoryDesignCaseRevisionRepository,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        case = _make_case()
        rev = rev_service.create_initial_revision(
            case=case,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev)

        run = run_service.create_run(
            case_revision_id=rev.revision_id,
            run_type=CalculationRunType.REPORT,
            software_version="0.1.0",
            git_commit="no-git",
            clock=clock,
            id_gen=id_gen,
            provenance_graph=_make_minimal_graph(),
        )
        assert run.status == CalculationRunStatus.PENDING
        clock.advance(seconds=1)
        run = run_service.cancel_run(run, clock)
        assert run.status == CalculationRunStatus.CANCELLED

    def test_invalid_transition_raises(
        self,
        rev_service: RevisionService,
        run_service: RunService,
        rev_repo: InMemoryDesignCaseRevisionRepository,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        """Cannot go directly from PENDING → SUCCEEDED."""
        case = _make_case()
        rev = rev_service.create_initial_revision(
            case=case,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev)

        run = run_service.create_run(
            case_revision_id=rev.revision_id,
            run_type=CalculationRunType.SCREEN,
            software_version="0.1.0",
            git_commit="no-git",
            clock=clock,
            id_gen=id_gen,
            provenance_graph=_make_minimal_graph(),
        )
        with pytest.raises(InvalidStateTransitionError):
            run_service.succeed_run(run, result_hash="sha256:" + "b" * 64, clock=clock)

    def test_run_integrity_verification(
        self,
        rev_service: RevisionService,
        run_service: RunService,
        rev_repo: InMemoryDesignCaseRevisionRepository,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        """A successfully completed run passes integrity checks."""
        case = _make_case()
        rev = rev_service.create_initial_revision(
            case=case,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev)

        run = run_service.create_run(
            case_revision_id=rev.revision_id,
            run_type=CalculationRunType.SCREEN,
            software_version="0.1.0",
            git_commit="abcdef0",
            clock=clock,
            id_gen=id_gen,
            provenance_graph=_make_succeeded_graph(),
        )
        clock.advance(seconds=1)
        run = run_service.start_run(run, clock)
        clock.advance(seconds=5)
        run = run_service.succeed_run(run, result_hash="sha256:" + "a" * 64, clock=clock)

        assert run_service.verify_run_integrity(run) is True

    def test_run_integrity_fails_without_result_hash(
        self,
        rev_service: RevisionService,
        run_service: RunService,
        rev_repo: InMemoryDesignCaseRevisionRepository,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        """A SUCCEEDED run cannot be created without a valid result_hash."""
        case = _make_case()
        rev = rev_service.create_initial_revision(
            case=case,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev)

        run = run_service.create_run(
            case_revision_id=rev.revision_id,
            run_type=CalculationRunType.SCREEN,
            software_version="0.1.0",
            git_commit="no-git",
            clock=clock,
            id_gen=id_gen,
            provenance_graph=_make_minimal_graph(),
        )
        # SUCCEEDED without result_hash is now rejected at construction time
        from hexagent.domain.revisions import CalculationRun as CR

        with pytest.raises(ValidationError, match="result_hash"):
            CR(
                run_id=run.run_id,
                case_id=run.case_id,
                case_revision_id=run.case_revision_id,
                run_type=run.run_type,
                status=CalculationRunStatus.SUCCEEDED,
                started_at=run.started_at,
                completed_at=datetime(2026, 1, 1, 0, 0, 20, tzinfo=UTC),
                git_commit="abcdef0",
                input_hash=run.input_hash,
            )

    def test_multiple_runs_on_same_revision(
        self,
        rev_service: RevisionService,
        run_service: RunService,
        rev_repo: InMemoryDesignCaseRevisionRepository,
        run_repo: InMemoryCalculationRunRepository,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        """Multiple runs can target the same revision."""
        case = _make_case()
        rev = rev_service.create_initial_revision(
            case=case,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev)

        r1 = run_service.create_run(
            case_revision_id=rev.revision_id,
            run_type=CalculationRunType.SCREEN,
            software_version="0.1.0",
            git_commit="no-git",
            clock=clock,
            id_gen=id_gen,
            provenance_graph=_make_minimal_graph(),
        )
        r2 = run_service.create_run(
            case_revision_id=rev.revision_id,
            run_type=CalculationRunType.SIZE,
            software_version="0.1.0",
            git_commit="no-git",
            clock=clock,
            id_gen=id_gen,
            provenance_graph=_make_minimal_graph(),
        )
        assert r1.run_id != r2.run_id
        assert r1.run_type != r2.run_type
        # Both runs should be retrievable via the repository
        stored_r1 = run_repo.get(r1.run_id)
        stored_r2 = run_repo.get(r2.run_id)
        assert stored_r1.run_type == CalculationRunType.SCREEN
        assert stored_r2.run_type == CalculationRunType.SIZE

    def test_frozen_objects_cannot_be_mutated(
        self,
        rev_service: RevisionService,
        rev_repo: InMemoryDesignCaseRevisionRepository,
        clock: FixedClock,
        id_gen: FixedIdGenerator,
    ) -> None:
        """Both DesignCaseRevision and CalculationRun are immutable."""
        case = _make_case()
        rev = rev_service.create_initial_revision(
            case=case,
            created_by="agent-1",
            clock=clock,
            id_gen=id_gen,
        )
        rev_repo.add(rev)

        with pytest.raises(AttributeError):
            rev.revision_number = 999  # type: ignore[misc]

        run = RunService(
            run_repo=InMemoryCalculationRunRepository(),
            revision_repo=rev_repo,
        ).create_run(
            case_revision_id=rev.revision_id,
            run_type=CalculationRunType.SCREEN,
            software_version="0.1.0",
            git_commit="no-git",
            clock=clock,
            id_gen=id_gen,
            provenance_graph=_make_minimal_graph(),
        )
        with pytest.raises((ValueError, ValidationError)):
            run.status = CalculationRunStatus.SUCCEEDED  # type: ignore[misc]
