"""TASK-010 in-memory RunRepository with CAS state machine.

Implements contract §7.4:
- RunState StrEnum: CLAIMED, RUNNING, COMPLETE, FAILED, STALE
- RunRecord frozen dataclass (frozen=True, slots=True, truly immutable)
- ClaimOutcome StrEnum / ClaimResult
- CAS on all mutating operations (owner_token + expected_version + lease)
- All mutating methods return NEW frozen records (never mutate in place)
- Lease management with STALE detection
- Thread-safe via threading.Lock
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

UTC = UTC
try:
    from enum import StrEnum  # Python 3.11+
except ImportError:  # pragma: no cover
    from enum import Enum

    class StrEnum(str, Enum):  # type: ignore[no-redef]  # noqa: UP042  # Python 3.10 shim
        """Minimal StrEnum backport for Python 3.10."""

        def __str__(self) -> str:
            return self.value  # type: ignore[no-any-return]


from typing import Any, Protocol  # noqa: E402
from uuid import UUID  # noqa: E402

# ---------------------------------------------------------------------------
# Frozen failure payload (C5) — stores exact HTTP failure for replay
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FrozenFailurePayload:
    """Immutable snapshot of a failed run's HTTP response.

    Stored on RunRecord.failure so FAILED_REPLAY can return the exact
    same status code and error body without re-executing.
    """

    status_code: int
    error_code: str
    error_message: str
    request_digest: str | None
    operation: str


# ---------------------------------------------------------------------------
# Frozen state enum
# ---------------------------------------------------------------------------


class RunState(StrEnum):
    """Run lifecycle states per contract §7.4."""

    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    STALE = "stale"


# Allowed transitions: (from_state, to_state) → True
_VALID_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        (RunState.CLAIMED, RunState.RUNNING),
        (RunState.CLAIMED, RunState.FAILED),
        (RunState.RUNNING, RunState.COMPLETE),
        (RunState.RUNNING, RunState.FAILED),
        # STALE transitions handled via takeover
    }
)


def _check_transition(from_state: RunState, to_state: RunState) -> bool:
    return (from_state, to_state) in _VALID_TRANSITIONS


# ---------------------------------------------------------------------------
# Claim outcome
# ---------------------------------------------------------------------------


class ClaimOutcome(StrEnum):
    """Outcomes of a claim() call per contract §7.4."""

    NEW_CLAIM = "new_claim"
    COMPLETE_REPLAY = "complete_replay"
    IN_PROGRESS = "in_progress"
    FAILED_REPLAY = "failed_replay"
    STALE_REJECTED = "stale_rejected"
    STALE_TAKEOVER = "stale_takeover"


# ---------------------------------------------------------------------------
# RunRecord — truly immutable via frozen=True, slots=True
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RunRecord:
    """Immutable run record.

    All mutating operations in the repository create a NEW RunRecord via
    dataclasses.replace() with an incremented record_version.  The frozen
    + slots combination prevents any attribute reassignment.
    """

    run_id: UUID
    namespace_digest: str
    request_digest: str
    operation: str
    state: RunState
    owner_token: UUID
    record_version: int
    claimed_at: datetime
    lease_expires_at: datetime
    heartbeat_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    envelope: Any | None = None
    artifact_bundle: Any | None = None
    failure: Any | None = None


# ---------------------------------------------------------------------------
# Claim result (forward-ref-safe because RunRecord is now defined)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ClaimResult:
    """Result of a claim() call."""

    outcome: ClaimOutcome
    record: RunRecord


# ---------------------------------------------------------------------------
# Repository Protocol
# ---------------------------------------------------------------------------


class RunRepository(Protocol):
    """Protocol for run repository per contract §7.4."""

    def claim(
        self,
        *,
        namespace_digest: str,
        request_digest: str,
        operation: str,
        takeover: bool = False,
    ) -> ClaimResult: ...

    def start(
        self,
        *,
        owner_token: UUID,
        expected_version: int,
    ) -> RunRecord: ...

    def heartbeat(
        self,
        *,
        owner_token: UUID,
        expected_version: int,
    ) -> RunRecord: ...

    def complete(
        self,
        *,
        owner_token: UUID,
        expected_version: int,
        envelope: Any,
        artifact_bundle: Any,
    ) -> RunRecord: ...

    def fail(
        self,
        *,
        owner_token: UUID,
        expected_version: int,
        failure: Any,
    ) -> RunRecord: ...

    def get_by_run_id(self, run_id: UUID) -> RunRecord | None: ...

    def get_by_namespace(self, namespace_digest: str) -> RunRecord | None: ...


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------

LEASE_DURATION = timedelta(seconds=30)
HEARTBEAT_INTERVAL = timedelta(seconds=10)


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


class InMemoryRunRepository:
    """Thread-safe in-memory run repository with CAS semantics.

    Every mutating operation creates a NEW frozen RunRecord with
    record_version += 1 and atomically replaces the stored record.
    The old record object is never modified.
    """

    def __init__(self, *, clock: Any | None = None) -> None:
        self._lock = threading.Lock()
        self._records: dict[UUID, RunRecord] = {}
        self._by_namespace: dict[str, UUID] = {}
        self._clock = clock  # injectable for testing

    # -- helpers -----------------------------------------------------------

    def _now(self) -> datetime:
        if self._clock is not None:
            return self._clock()  # type: ignore[no-any-return]
        return _now_utc()

    def _is_stale(self, record: RunRecord) -> bool:
        return (
            record.state in (RunState.CLAIMED, RunState.RUNNING)
            and self._now() > record.lease_expires_at
        )

    def _find_by_owner(self, owner_token: UUID, expected_version: int) -> RunRecord:
        """CAS lookup — find record by owner_token and version.

        Also validates that the lease has not expired; an expired lease is
        treated as a CAS failure because the record is effectively STALE.
        """
        for record in self._records.values():
            if record.owner_token == owner_token:
                # Lease check — expired lease means CAS failure
                if self._now() > record.lease_expires_at:
                    raise CASCasError(f"lease expired for owner_token {owner_token}")
                if record.record_version != expected_version:
                    raise CASCasError(
                        f"version mismatch: expected {expected_version}, "
                        f"got {record.record_version}"
                    )
                return record
        raise CASCasError(f"owner_token {owner_token} not found")

    def _replace_record(self, old: RunRecord, **overrides: Any) -> RunRecord:
        """Create a new frozen record with record_version + 1."""
        new_record = replace(
            old,
            record_version=old.record_version + 1,
            **overrides,
        )
        self._records[new_record.run_id] = new_record
        return new_record

    # -- claim -------------------------------------------------------------

    def claim(
        self,
        *,
        namespace_digest: str,
        request_digest: str,
        operation: str,
        takeover: bool = False,
    ) -> ClaimResult:
        with self._lock:
            existing_id = self._by_namespace.get(namespace_digest)

            # --- New namespace → NEW_CLAIM ---
            if existing_id is None:
                return self._new_claim(
                    namespace_digest=namespace_digest,
                    request_digest=request_digest,
                    operation=operation,
                )

            record = self._records[existing_id]

            # --- COMPLETE: replay or conflict ---
            if record.state == RunState.COMPLETE:
                if record.request_digest == request_digest:
                    return ClaimResult(
                        outcome=ClaimOutcome.COMPLETE_REPLAY,
                        record=record,
                    )
                # Different digest → conflict
                raise IdempotencyConflictError(
                    f"namespace {namespace_digest[:16]}… already COMPLETE "
                    f"with different request_digest"
                )

            # --- FAILED: replay or conflict ---
            if record.state == RunState.FAILED:
                if record.request_digest == request_digest:
                    return ClaimResult(
                        outcome=ClaimOutcome.FAILED_REPLAY,
                        record=record,
                    )
                raise IdempotencyConflictError(
                    f"namespace {namespace_digest[:16]}… already FAILED "
                    f"with different request_digest"
                )

            # --- CLAIMED/RUNNING with valid lease → IN_PROGRESS ---
            if not self._is_stale(record):
                return ClaimResult(
                    outcome=ClaimOutcome.IN_PROGRESS,
                    record=record,
                )

            # --- STALE ---
            if not takeover:
                return ClaimResult(
                    outcome=ClaimOutcome.STALE_REJECTED,
                    record=record,
                )

            # --- STALE_TAKEOVER: verify request_digest parity first ---
            return self._stale_takeover(
                record=record,
                request_digest=request_digest,
            )

    def _new_claim(
        self,
        *,
        namespace_digest: str,
        request_digest: str,
        operation: str,
    ) -> ClaimResult:
        now = self._now()
        record = RunRecord(
            run_id=uuid.uuid4(),
            namespace_digest=namespace_digest,
            request_digest=request_digest,
            operation=operation,
            state=RunState.CLAIMED,
            owner_token=uuid.uuid4(),
            record_version=1,
            claimed_at=now,
            lease_expires_at=now + LEASE_DURATION,
        )
        self._records[record.run_id] = record
        self._by_namespace[namespace_digest] = record.run_id
        return ClaimResult(outcome=ClaimOutcome.NEW_CLAIM, record=record)

    def _stale_takeover(
        self,
        *,
        record: RunRecord,
        request_digest: str,
    ) -> ClaimResult:
        """Take over a stale run.

        If the request_digest differs from the existing record, this is an
        idempotency conflict — not a takeover.  A takeover is only allowed
        when the request_digest matches (same logical request retried).
        """
        if record.request_digest != request_digest:
            raise IdempotencyConflictError(
                f"namespace {record.namespace_digest[:16]}… is STALE "
                f"but request_digest differs — idempotency conflict"
            )

        now = self._now()
        new_token = uuid.uuid4()

        # Create a NEW frozen record — never mutate the old one
        new_record = self._replace_record(
            record,
            owner_token=new_token,
            request_digest=request_digest,
            claimed_at=now,
            lease_expires_at=now + LEASE_DURATION,
            state=RunState.CLAIMED,
            heartbeat_at=None,
            started_at=None,
            completed_at=None,
            failed_at=None,
            envelope=None,
            artifact_bundle=None,
            failure=None,
        )

        return ClaimResult(outcome=ClaimOutcome.STALE_TAKEOVER, record=new_record)

    # -- mutating operations (all return NEW frozen records) ---------------

    def start(
        self,
        *,
        owner_token: UUID,
        expected_version: int,
    ) -> RunRecord:
        with self._lock:
            record = self._find_by_owner(owner_token, expected_version)
            if record.state != RunState.CLAIMED:
                raise RepositoryStateError(f"start() requires CLAIMED state, got {record.state}")
            now = self._now()
            new_record = self._replace_record(
                record,
                state=RunState.RUNNING,
                started_at=now,
                lease_expires_at=now + LEASE_DURATION,
            )
            return new_record

    def heartbeat(
        self,
        *,
        owner_token: UUID,
        expected_version: int,
    ) -> RunRecord:
        with self._lock:
            record = self._find_by_owner(owner_token, expected_version)
            if record.state not in (RunState.CLAIMED, RunState.RUNNING):
                raise RepositoryStateError(
                    f"heartbeat() requires CLAIMED/RUNNING, got {record.state}"
                )
            now = self._now()
            new_record = self._replace_record(
                record,
                heartbeat_at=now,
                lease_expires_at=now + LEASE_DURATION,
            )
            return new_record

    def complete(
        self,
        *,
        owner_token: UUID,
        expected_version: int,
        envelope: Any,
        artifact_bundle: Any,
    ) -> RunRecord:
        with self._lock:
            record = self._find_by_owner(owner_token, expected_version)
            if record.state != RunState.RUNNING:
                raise RepositoryStateError(f"complete() requires RUNNING state, got {record.state}")

            # Operation parity
            if hasattr(envelope, "operation") and envelope.operation != record.operation:
                raise RepositoryStateError("envelope.operation != record.operation")

            # Request digest parity
            if (
                hasattr(envelope, "request_digest")
                and envelope.request_digest != record.request_digest
            ):  # noqa: E501
                raise IdempotencyConflictError("envelope.request_digest mismatch")

            # Bundle type check
            if record.operation == "rateDoublePipe":
                from hexagent.api.artifacts import RatingRunArtifacts

                if artifact_bundle is not None and not isinstance(
                    artifact_bundle, RatingRunArtifacts
                ):  # noqa: E501
                    raise RepositoryStateError("rateDoublePipe requires RatingRunArtifacts")
            elif record.operation == "sizeDoublePipe":
                from hexagent.api.artifacts import SizingRunArtifacts

                if artifact_bundle is not None and not isinstance(
                    artifact_bundle, SizingRunArtifacts
                ):  # noqa: E501
                    raise RepositoryStateError("sizeDoublePipe requires SizingRunArtifacts")

            # Bundle identity (value equality, not reference)
            if (
                hasattr(envelope, "artifact_bundle")
                and envelope.artifact_bundle is not None
                and artifact_bundle is not None
                and envelope.artifact_bundle != artifact_bundle
            ):
                raise RepositoryStateError("envelope.artifact_bundle != artifact_bundle")

            # Store and transition
            now = self._now()
            new_record = self._replace_record(
                record,
                state=RunState.COMPLETE,
                completed_at=now,
                envelope=envelope,
                artifact_bundle=artifact_bundle,
            )
            return new_record

    def fail(
        self,
        *,
        owner_token: UUID,
        expected_version: int,
        failure: Any,
    ) -> RunRecord:
        with self._lock:
            record = self._find_by_owner(owner_token, expected_version)
            if record.state not in (RunState.CLAIMED, RunState.RUNNING):
                raise RepositoryStateError(f"fail() requires CLAIMED/RUNNING, got {record.state}")
            now = self._now()
            new_record = self._replace_record(
                record,
                state=RunState.FAILED,
                failed_at=now,
                failure=failure,
            )
            return new_record

    # -- getters (frozen dataclass is safe to return directly) -------------

    def get_by_run_id(self, run_id: UUID) -> RunRecord | None:
        with self._lock:
            record = self._records.get(run_id)
            return record  # frozen dataclass — safe to expose

    def get_by_namespace(self, namespace_digest: str) -> RunRecord | None:
        with self._lock:
            run_id = self._by_namespace.get(namespace_digest)
            if run_id is None:
                return None
            return self._records.get(run_id)  # frozen dataclass — safe


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class RepositoryError(Exception):
    """Base repository error."""


class CASCasError(RepositoryError):
    """CAS failure: owner_token not found, version mismatch, or expired lease."""


class RepositoryStateError(RepositoryError):
    """Invalid state transition."""


class IdempotencyConflictError(RepositoryError):
    """Same namespace, different request_digest."""
