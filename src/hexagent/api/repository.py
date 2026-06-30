"""TASK-010 in-memory RunRepository with CAS state machine.

Implements contract §7.4:
- RunState enum: CLAIMED, RUNNING, COMPLETE, FAILED, STALE
- RunRecord frozen dataclass
- ClaimOutcome / ClaimResult
- CAS on all mutating operations (owner_token + expected_version)
- Lease management with STALE detection
- Thread-safe via threading.Lock
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

# ---------------------------------------------------------------------------
# Frozen state enum
# ---------------------------------------------------------------------------


class RunState:
    """Run lifecycle states per contract §7.4."""

    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    STALE = "stale"

    _VALID: frozenset[str] = frozenset(
        {
            CLAIMED,
            RUNNING,
            COMPLETE,
            FAILED,
            STALE,
        }
    )

    # Allowed transitions: (from_state, to_state) → True
    _TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
        {
            (CLAIMED, RUNNING),
            (CLAIMED, FAILED),
            (RUNNING, COMPLETE),
            (RUNNING, FAILED),
            # STALE transitions handled via takeover
        }
    )

    @classmethod
    def is_valid(cls, state: str) -> bool:
        return state in cls._VALID

    @classmethod
    def check_transition(cls, from_state: str, to_state: str) -> bool:
        return (from_state, to_state) in cls._TRANSITIONS


# ---------------------------------------------------------------------------
# Claim outcome
# ---------------------------------------------------------------------------


class ClaimOutcome:
    """Outcomes of a claim() call per contract §7.4."""

    NEW_CLAIM = "new_claim"
    COMPLETE_REPLAY = "complete_replay"
    IN_PROGRESS = "in_progress"
    FAILED_REPLAY = "failed_replay"
    STALE_REJECTED = "stale_rejected"
    STALE_TAKEOVER = "stale_takeover"


@dataclass(frozen=True)
class ClaimResult:
    """Result of a claim() call."""

    outcome: str  # ClaimOutcome value
    record: RunRecord


# ---------------------------------------------------------------------------
# RunRecord
# ---------------------------------------------------------------------------


@dataclass
class RunRecord:
    """Immutable run record (mutated only via CAS-protected repository methods)."""

    run_id: UUID
    namespace_digest: str
    request_digest: str
    operation: str
    state: str  # RunState value
    owner_token: UUID
    record_version: int
    claimed_at: datetime
    lease_expires_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    envelope: Any | None = None
    artifact_bundle: Any | None = None
    failure: Any | None = None


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
    """Thread-safe in-memory run repository with CAS semantics."""

    def __init__(self, *, clock: Any | None = None) -> None:
        self._lock = threading.Lock()
        self._records: dict[UUID, RunRecord] = {}
        self._by_namespace: dict[str, UUID] = {}
        self._clock = clock  # injectable for testing

    def _now(self) -> datetime:
        if self._clock is not None:
            return self._clock()  # type: ignore[no-any-return]
        return _now_utc()

    def _is_stale(self, record: RunRecord) -> bool:
        return (
            record.state in (RunState.CLAIMED, RunState.RUNNING)
            and self._now() > record.lease_expires_at
        )

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

            # --- STALE_TAKEOVER: atomic CAS takeover ---
            return self._stale_takeover(record=record, request_digest=request_digest)

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
        now = self._now()
        new_token = uuid.uuid4()

        record.owner_token = new_token
        record.record_version += 1
        record.request_digest = request_digest
        record.claimed_at = now
        record.lease_expires_at = now + LEASE_DURATION
        record.state = RunState.CLAIMED
        record.started_at = None
        record.completed_at = None
        record.failed_at = None
        record.envelope = None
        record.artifact_bundle = None
        record.failure = None

        # Old token is immediately invalid — CAS will reject it
        return ClaimResult(outcome=ClaimOutcome.STALE_TAKEOVER, record=record)

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
            record.state = RunState.RUNNING
            record.started_at = self._now()
            record.lease_expires_at = self._now() + LEASE_DURATION
            return record

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
            record.lease_expires_at = self._now() + LEASE_DURATION
            return record

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
            record.state = RunState.COMPLETE
            record.completed_at = self._now()
            record.envelope = envelope
            record.artifact_bundle = artifact_bundle
            return record

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
            record.state = RunState.FAILED
            record.failed_at = self._now()
            record.failure = failure
            return record

    def get_by_run_id(self, run_id: UUID) -> RunRecord | None:
        with self._lock:
            return self._records.get(run_id)

    def get_by_namespace(self, namespace_digest: str) -> RunRecord | None:
        with self._lock:
            run_id = self._by_namespace.get(namespace_digest)
            if run_id is None:
                return None
            return self._records.get(run_id)

    def _find_by_owner(self, owner_token: UUID, expected_version: int) -> RunRecord:
        """CAS lookup — find record by owner_token and version."""
        for record in self._records.values():
            if record.owner_token == owner_token:
                if record.record_version != expected_version:
                    raise CASCasError(
                        f"version mismatch: expected {expected_version}, "
                        f"got {record.record_version}"
                    )
                return record
        raise CASCasError(f"owner_token {owner_token} not found")


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class RepositoryError(Exception):
    """Base repository error."""


class CASCasError(RepositoryError):
    """CAS failure: owner_token not found or version mismatch."""


class RepositoryStateError(RepositoryError):
    """Invalid state transition."""


class IdempotencyConflictError(RepositoryError):
    """Same namespace, different request_digest."""
