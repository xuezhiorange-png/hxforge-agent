"""In-memory repository implementations for development and testing.

All state lives in plain Python dicts.  Ordering is deterministic: revisions
are sorted by ``revision_number``, runs by ``created_at``.

Deep-copy policy
~~~~~~~~~~~~~~~~
Every ``add()`` stores a **deep copy** of the entity; every ``get()`` returns a
**deep copy**.  This guarantees that callers cannot mutate repository state
through retrieved objects.
"""

from __future__ import annotations

import copy
from uuid import UUID

from hexagent.domain.provenance import ProvenanceGraph, ProvenanceNodeType
from hexagent.domain.revisions import (
    CalculationRun,
    CalculationRunStatus,
    DesignCaseRevision,
    DuplicateIdError,
    IntegrityError,
    InvalidStateTransitionError,
    MissingParentError,
    RevisionNumberConflictError,
)

# ---------------------------------------------------------------------------


class EmptyProvenanceGraphError(ValueError):
    """Raised when a persisted run has an empty provenance graph."""

    def __init__(self, run_id: UUID) -> None:
        super().__init__(f"Persisted run {run_id} must have a non-empty provenance graph")
        self.run_id = run_id


class OrphanProvenanceNodeError(ValueError):
    """Raised when a WARNING/BLOCKER node lacks an upstream lineage edge."""

    def __init__(self, node_type: str, node_id: UUID) -> None:
        super().__init__(
            f"Provenance {node_type} node {node_id} has no incoming edge "
            f"from an approved upstream node type"
        )
        self.node_type = node_type
        self.node_id = node_id


# ---------------------------------------------------------------------------


class InMemoryDesignCaseRevisionRepository:
    """Dict-backed store for :class:`DesignCaseRevision` objects.

    All stored and retrieved objects are deeply copied to prevent
    external mutation of repository state.

    Chain-invariant enforcement
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ``add()`` verifies:
    - No duplicate revision IDs.
    - No duplicate ``(case_id, revision_number)`` pairs.
    - Parent revision exists (if specified).
    - ``parent.case_id == child.case_id`` (same-case parentage).
    - ``child.revision_number == parent.revision_number + 1`` (sequential).
    """

    def __init__(self) -> None:
        self._by_id: dict[UUID, DesignCaseRevision] = {}
        self._by_case: dict[UUID, dict[int, DesignCaseRevision]] = {}

    # -- public API ----------------------------------------------------------

    def add(self, revision: DesignCaseRevision) -> None:
        """Persist a new revision with full constraint checking.

        Stores a **deep copy** — the caller retains ownership of the
        original object.

        Raises
        ------
        DuplicateIdError
            If a revision with the same ``revision_id`` already exists.
        RevisionNumberConflictError
            If a revision for the same ``case_id`` with the same
            ``revision_number`` already exists.
        MissingParentError
            If ``parent_revision_id`` is set but the parent does not exist.
        IntegrityError
            If the parent belongs to a different case, or the revision
            number is not exactly ``parent.revision_number + 1``.
        """
        # 1. Duplicate ID
        if revision.revision_id in self._by_id:
            raise DuplicateIdError("DesignCaseRevision", str(revision.revision_id))

        # 2. Revision number conflict
        case_rev_map = self._by_case.setdefault(revision.case_id, {})
        if revision.revision_number in case_rev_map:
            raise RevisionNumberConflictError(
                revision.case_id,
                revision.revision_number,
            )

        # 3. Missing parent
        if revision.parent_revision_id is not None:
            parent = self._by_id.get(revision.parent_revision_id)
            if parent is None:
                raise MissingParentError(str(revision.parent_revision_id))

            # 4. Same-case parentage
            if parent.case_id != revision.case_id:
                raise IntegrityError(
                    f"Parent revision {parent.revision_id} belongs to case "
                    f"{parent.case_id}, but child {revision.revision_id} "
                    f"belongs to case {revision.case_id}"
                )

            # 5. Sequential revision number
            expected_number = parent.revision_number + 1
            if revision.revision_number != expected_number:
                raise IntegrityError(
                    f"Revision number {revision.revision_number} is not "
                    f"exactly parent.revision_number + 1 "
                    f"(expected {expected_number})"
                )

        # 6. Store deep copy
        snapshot = copy.deepcopy(revision)
        self._by_id[revision.revision_id] = snapshot
        case_rev_map[revision.revision_number] = snapshot

    def get(self, revision_id: UUID) -> DesignCaseRevision:
        """Return a **deep copy** of the revision."""
        try:
            return copy.deepcopy(self._by_id[revision_id])
        except KeyError as err:
            raise KeyError(f"DesignCaseRevision not found: {revision_id}") from err

    def latest(self, case_id: UUID) -> DesignCaseRevision | None:
        """Return a deep copy of the most recent revision, or ``None``."""
        case_rev_map = self._by_case.get(case_id)
        if not case_rev_map:
            return None
        latest_number = max(case_rev_map)
        return copy.deepcopy(case_rev_map[latest_number])

    def list_by_case(self, case_id: UUID) -> tuple[DesignCaseRevision, ...]:
        """Return deep copies of all revisions ordered by revision_number ASC."""
        case_rev_map = self._by_case.get(case_id)
        if not case_rev_map:
            return ()
        return tuple(copy.deepcopy(case_rev_map[n]) for n in sorted(case_rev_map))


# ---------------------------------------------------------------------------
# CalculationRun repository
# ---------------------------------------------------------------------------


# Immutable identity fields that must not change during an update.
_IMMUTABLE_RUN_FIELDS: frozenset[str] = frozenset(
    {
        "case_id",
        "case_revision_id",
        "run_type",
        "input_hash",
        "git_commit",
        "software_version",
        "schema_version",
    }
)


class InMemoryCalculationRunRepository:
    """Dict-backed store for :class:`CalculationRun` objects.

    All stored and retrieved objects are deeply copied to prevent
    external mutation of repository state.

    Persistence contracts
    ~~~~~~~~~~~~~~~~~~~~~
    - ``add()`` only accepts ``PENDING`` runs with a non-empty provenance
      graph containing at least ``CASE_REVISION`` and ``CALCULATION_RUN``
      node types.
    - ``update()`` enforces legal state transitions, immutable identity
      fields, status-dependent invariants, and terminal-state provenance
      requirements (non-empty graph, required node types, RESULT for
      SUCCEEDED).
    """

    def __init__(self) -> None:
        self._by_id: dict[UUID, CalculationRun] = {}
        self._by_revision: dict[UUID, list[UUID]] = {}  # revision_id → [run_id, …]

    # -- public API ----------------------------------------------------------

    def add(self, run: CalculationRun) -> None:
        """Persist a new run with duplicate-ID and provenance checks.

        Only accepts ``PENDING`` as initial status.  ``RUNNING``
        must be reached through a legal state transition via ``update()``.

        Every persisted run must have a non-empty provenance graph
        containing at least ``CASE_REVISION`` and ``CALCULATION_RUN``
        node types.

        Raises
        ------
        DuplicateIdError
            If a run with the same ``run_id`` already exists.
        InvalidStateTransitionError
            If the initial status is not PENDING.
        EmptyProvenanceGraphError
            If the provenance graph is empty.
        ValueError
            If the provenance graph lacks required node types.
        """
        if run.run_id in self._by_id:
            raise DuplicateIdError("CalculationRun", str(run.run_id))

        # Only PENDING is allowed as initial status
        if run.status != CalculationRunStatus.PENDING:
            raise InvalidStateTransitionError(
                "(new)",
                run.status,
            )

        # Provenance graph must be non-empty for all persisted runs
        if not run.provenance_graph.nodes:
            raise EmptyProvenanceGraphError(run.run_id)

        # Must contain CASE_REVISION and CALCULATION_RUN
        node_types = {n.node_type for n in run.provenance_graph.nodes}
        if ProvenanceNodeType.CASE_REVISION not in node_types:
            raise ValueError(f"Persisted run {run.run_id} graph must contain a CASE_REVISION node")
        if ProvenanceNodeType.CALCULATION_RUN not in node_types:
            raise ValueError(
                f"Persisted run {run.run_id} graph must contain a CALCULATION_RUN node"
            )

        # Validate WARNING/BLOCKER lineage
        _validate_warning_blocker_lineage(run.provenance_graph)

        snapshot = copy.deepcopy(run)
        self._by_id[run.run_id] = snapshot
        self._by_revision.setdefault(run.case_revision_id, []).append(run.run_id)

    def get(self, run_id: UUID) -> CalculationRun:
        """Return a **deep copy** of the run."""
        try:
            return copy.deepcopy(self._by_id[run_id])
        except KeyError as err:
            raise KeyError(f"CalculationRun not found: {run_id}") from err

    def update(self, run: CalculationRun) -> None:
        """Replace the stored run record with strict invariant checks.

        Validates:
        1. State transition is legal.
        2. Immutable identity fields have not changed.
        3. Status-dependent invariants are satisfied.
        4. Terminal states require non-empty graph with required types.
        5. SUCCEEDED requires RESULT node.
        6. WARNING/BLOCKER lineage is valid.

        Stores a **deep copy**.

        Raises
        ------
        KeyError
            If no run with ``run.run_id`` exists in the store.
        InvalidStateTransitionError
            If the new status is not reachable from the stored status.
        IntegrityError-like ValueError
            If immutable fields are changed or invariants are violated.
        """
        stored = self._by_id.get(run.run_id)
        if stored is None:
            raise KeyError(f"CalculationRun not found: {run.run_id}")

        # 1. State transition
        from hexagent.domain.revisions import is_valid_transition

        if not is_valid_transition(stored.status, run.status):
            raise InvalidStateTransitionError(stored.status, run.status)

        # 2. Immutable identity fields
        for field_name in _IMMUTABLE_RUN_FIELDS:
            old_val = getattr(stored, field_name)
            new_val = getattr(run, field_name)
            if old_val != new_val:
                raise ValueError(
                    f"Cannot change immutable field '{field_name}' "
                    f"during update: {old_val!r} → {new_val!r}"
                )

        # 3. Status-dependent invariants
        _validate_run_invariants(run)

        # 4. Terminal states: graph must be non-empty with required node types
        terminal = run.status in (
            CalculationRunStatus.SUCCEEDED,
            CalculationRunStatus.FAILED,
            CalculationRunStatus.BLOCKED,
        )
        if terminal:
            if not run.provenance_graph.nodes:
                raise ValueError("Terminal run must have a non-empty provenance graph")
            node_types = {n.node_type for n in run.provenance_graph.nodes}
            if ProvenanceNodeType.CASE_REVISION not in node_types:
                raise ValueError("Terminal run graph must contain a CASE_REVISION node")
            if ProvenanceNodeType.CALCULATION_RUN not in node_types:
                raise ValueError("Terminal run graph must contain a CALCULATION_RUN node")
            result_missing = ProvenanceNodeType.RESULT not in node_types
            if run.status == CalculationRunStatus.SUCCEEDED and result_missing:
                raise ValueError("SUCCEEDED run must have a RESULT node in its provenance graph")

        # 5. Validate WARNING/BLOCKER lineage for all runs with nodes
        if run.provenance_graph.nodes:
            _validate_warning_blocker_lineage(run.provenance_graph)

        snapshot = copy.deepcopy(run)
        self._by_id[run.run_id] = snapshot

    def list_by_revision(self, revision_id: UUID) -> tuple[CalculationRun, ...]:
        """Return deep copies of all runs ordered by creation time ASC."""
        run_ids = self._by_revision.get(revision_id, ())
        if not run_ids:
            return ()
        runs = [self._by_id[rid] for rid in run_ids]
        return tuple(copy.deepcopy(r) for r in sorted(runs, key=lambda r: r.started_at))


# ---------------------------------------------------------------------------
# Provenance lineage validation
# ---------------------------------------------------------------------------

# Node types that are valid as immediate upstream parents of WARNING/BLOCKER.
_UPSTREAM_LINEAGE_TYPES: frozenset[ProvenanceNodeType] = frozenset(
    {
        ProvenanceNodeType.INPUT_FILE,
        ProvenanceNodeType.CALCULATION_RUN,
        ProvenanceNodeType.PROPERTY_CALL,
        ProvenanceNodeType.CORRELATION,
        ProvenanceNodeType.CASE_REVISION,
    }
)


def _validate_warning_blocker_lineage(graph: ProvenanceGraph) -> None:
    """Verify that every WARNING/BLOCKER node has an incoming edge from
    an approved upstream node type.

    Raises ``OrphanProvenanceNodeError`` if a WARNING/BLOCKER node
    has no incoming edges at all, or only from unapproved sources.
    """
    # Build adjacency: target → set of source node types
    incoming_by_target: dict[UUID, set[ProvenanceNodeType]] = {}
    for edge in graph.edges:
        incoming_by_target.setdefault(edge.target_id, set())
    # Build node_id → node_type map
    node_type_map: dict[UUID, ProvenanceNodeType] = {n.node_id: n.node_type for n in graph.nodes}
    for edge in graph.edges:
        src_type = node_type_map.get(edge.source_id)
        if src_type is not None:
            incoming_by_target.setdefault(edge.target_id, set()).add(src_type)

    # Check WARNING/BLOCKER nodes
    for node in graph.nodes:
        if node.node_type in (ProvenanceNodeType.WARNING, ProvenanceNodeType.BLOCKER):
            incoming = incoming_by_target.get(node.node_id, set())
            if not incoming:
                raise OrphanProvenanceNodeError(node.node_type.value, node.node_id)
            if not incoming.intersection(_UPSTREAM_LINEAGE_TYPES):
                raise OrphanProvenanceNodeError(node.node_type.value, node.node_id)


# ---------------------------------------------------------------------------
# Run invariant validation (centralised)
# ---------------------------------------------------------------------------


def _validate_run_invariants(run: CalculationRun) -> None:
    """Validate status-dependent invariants on a CalculationRun.
    Raises ``ValueError`` if invariants are violated.
    """
    status = run.status

    # SUCCEEDED: must have a real result_hash
    if status == CalculationRunStatus.SUCCEEDED:
        if not run.result_hash or not _is_valid_hash(run.result_hash):
            raise ValueError(
                f"SUCCEEDED run must have a valid result_hash (got {run.result_hash!r})"
            )
        if run.failure is not None:
            raise ValueError("SUCCEEDED run must not have a failure record")

    # FAILED: must have a failure record
    if status == CalculationRunStatus.FAILED:
        if run.failure is None:
            raise ValueError("FAILED run must have a failure record")
        if run.result_hash and _is_valid_hash(run.result_hash):
            raise ValueError("FAILED run must not have a valid result_hash")

    # BLOCKED: must have at least one blocker
    if status == CalculationRunStatus.BLOCKED and not run.blockers:
        raise ValueError("BLOCKED run must have at least one blocker")

    # Terminal states must have completed_at
    if status in (
        CalculationRunStatus.SUCCEEDED,
        CalculationRunStatus.FAILED,
        CalculationRunStatus.BLOCKED,
        CalculationRunStatus.CANCELLED,
    ):
        if run.completed_at is None:
            raise ValueError(f"Terminal status {status.value} requires completed_at")
        if run.completed_at <= run.started_at:
            raise ValueError(
                f"completed_at ({run.completed_at}) must be after started_at ({run.started_at})"
            )

    # Non-terminal: must NOT have completed_at
    non_terminal = status in (CalculationRunStatus.PENDING, CalculationRunStatus.RUNNING)
    if non_terminal and run.completed_at is not None:
        raise ValueError(f"Non-terminal status {status.value} must not have completed_at")


def _is_valid_hash(h: str) -> bool:
    """Return True if *h* is a valid ``sha256:<64-hex>`` string."""
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


__all__ = [
    "EmptyProvenanceGraphError",
    "InMemoryCalculationRunRepository",
    "InMemoryDesignCaseRevisionRepository",
    "OrphanProvenanceNodeError",
]
