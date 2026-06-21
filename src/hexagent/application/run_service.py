"""Run service for managing calculation run lifecycle.

Each state transition returns a NEW frozen CalculationRun —
no in-place mutation is ever performed.
"""

from __future__ import annotations

from uuid import UUID

from hexagent.core.time import Clock, IdGenerator
from hexagent.domain.messages import EngineeringMessage, RunFailure
from hexagent.domain.provenance import ProvenanceGraph
from hexagent.domain.revisions import (
    CalculationRun,
    CalculationRunStatus,
    CalculationRunType,
    InvalidStateTransitionError,
    is_valid_transition,
)
from hexagent.repositories.base import (
    CalculationRunRepository,
    DesignCaseRevisionRepository,
)


class RunService:
    """Manages the lifecycle of CalculationRun objects."""

    def __init__(
        self,
        run_repo: CalculationRunRepository,
        revision_repo: DesignCaseRevisionRepository,
    ) -> None:
        self._run_repo = run_repo
        self._revision_repo = revision_repo

    def create_run(
        self,
        case_revision_id: UUID,
        run_type: CalculationRunType,
        software_version: str,
        git_commit: str,
        clock: Clock,
        id_gen: IdGenerator,
        provenance_graph: ProvenanceGraph | None = None,
    ) -> CalculationRun:
        """Create a new PENDING calculation run.

        Parameters
        ----------
        provenance_graph:
            A non-empty provenance graph with at least ``CASE_REVISION``
            and ``CALCULATION_RUN`` nodes.  Required by the persistence
            contract — an empty graph is rejected at persist time.
        """
        revision = self._revision_repo.get(case_revision_id)
        now = clock.utcnow()
        graph = provenance_graph or ProvenanceGraph(nodes=(), edges=())
        run = CalculationRun(
            run_id=id_gen.new_id(),
            case_id=revision.case_id,
            case_revision_id=case_revision_id,
            run_type=run_type,
            status=CalculationRunStatus.PENDING,
            started_at=now,
            software_version=software_version,
            git_commit=git_commit,
            input_hash=revision.content_hash,
            provenance_graph=graph,
        )
        self._run_repo.add(run)
        return run

    def start_run(
        self,
        run: CalculationRun,
        clock: Clock,
    ) -> CalculationRun:
        """Transition PENDING → RUNNING."""
        self._check_transition(run, CalculationRunStatus.RUNNING)
        new = run.model_copy(
            update={
                "status": CalculationRunStatus.RUNNING,
                "started_at": clock.utcnow(),
            }
        )
        self._run_repo.update(new)
        return new

    def succeed_run(
        self,
        run: CalculationRun,
        result_hash: str,
        clock: Clock,
    ) -> CalculationRun:
        """Transition RUNNING → SUCCEEDED."""
        self._check_transition(run, CalculationRunStatus.SUCCEEDED)
        now = clock.utcnow()
        new = run.model_copy(
            update={
                "status": CalculationRunStatus.SUCCEEDED,
                "result_hash": result_hash,
                "completed_at": now,
            }
        )
        self._run_repo.update(new)
        return new

    def fail_run(
        self,
        run: CalculationRun,
        failure: RunFailure,
        clock: Clock,
    ) -> CalculationRun:
        """Transition RUNNING → FAILED."""
        self._check_transition(run, CalculationRunStatus.FAILED)
        now = clock.utcnow()
        new = run.model_copy(
            update={
                "status": CalculationRunStatus.FAILED,
                "failure": failure,
                "completed_at": now,
            }
        )
        self._run_repo.update(new)
        return new

    def block_run(
        self,
        run: CalculationRun,
        blockers: tuple[EngineeringMessage, ...],
        clock: Clock,
    ) -> CalculationRun:
        """Transition RUNNING → BLOCKED."""
        self._check_transition(run, CalculationRunStatus.BLOCKED)
        now = clock.utcnow()
        new = run.model_copy(
            update={
                "status": CalculationRunStatus.BLOCKED,
                "blockers": blockers,
                "completed_at": now,
            }
        )
        self._run_repo.update(new)
        return new

    def cancel_run(self, run: CalculationRun, clock: Clock) -> CalculationRun:
        """Transition PENDING/RUNNING → CANCELLED."""
        self._check_transition(run, CalculationRunStatus.CANCELLED)
        now = clock.utcnow()
        new = run.model_copy(
            update={
                "status": CalculationRunStatus.CANCELLED,
                "completed_at": now,
            }
        )
        self._run_repo.update(new)
        return new

    def verify_run_integrity(
        self,
        run: CalculationRun,
    ) -> bool:
        """Verify run data integrity."""
        revision = self._revision_repo.get(run.case_revision_id)
        if revision.content_hash != run.input_hash:
            return False
        if run.status == CalculationRunStatus.SUCCEEDED and (
            not run.result_hash or not _is_valid_hash(run.result_hash)
        ):
            return False
        if run.status == CalculationRunStatus.FAILED and run.failure is None:
            return False
        if run.status == CalculationRunStatus.BLOCKED and not run.blockers:
            return False
        return not (run.completed_at and run.started_at and run.completed_at <= run.started_at)

    def _check_transition(
        self,
        run: CalculationRun,
        target: CalculationRunStatus,
    ) -> None:
        """Validate and raise on illegal transitions."""
        if not is_valid_transition(run.status, target):
            raise InvalidStateTransitionError(run.status, target)


def _is_valid_hash(h: str) -> bool:
    """Return True if *h* matches ``sha256:<64-hex>``."""
    if not h.startswith("sha256:"):
        return False
    hex_part = h[7:]
    if len(hex_part) != 64:
        return False
    try:
        int(hex_part, 16)
        return True
    except ValueError:
        return False
