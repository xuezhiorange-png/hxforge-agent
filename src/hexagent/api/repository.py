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


from collections.abc import Callable  # noqa: E402
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias  # noqa: E402
from uuid import UUID  # noqa: E402

if TYPE_CHECKING:
    from hexagent.api.artifacts import RatingRunArtifacts, SizingRunArtifacts  # noqa: F401
    from hexagent.api.envelopes import (  # noqa: F401
        RatingRunEnvelope,
        SizingRunEnvelope,
        ValidationRunEnvelope,
    )

_RunEnvelope: TypeAlias = "ValidationRunEnvelope | RatingRunEnvelope | SizingRunEnvelope"
_ArtifactBundle: TypeAlias = "RatingRunArtifacts | SizingRunArtifacts"


# ---------------------------------------------------------------------------
# Recomputed bundle digest helpers (P0-3 trust boundary)
# ---------------------------------------------------------------------------


def _recompute_rating_bundle_digest(artifact_bundle: RatingRunArtifacts) -> str:
    """Recompute the rating artifact bundle digest for parity verification."""
    from hexagent.api.artifacts import compute_rating_artifact_bundle_digest

    return compute_rating_artifact_bundle_digest(artifact_bundle)


def _recompute_sizing_bundle_digest(artifact_bundle: SizingRunArtifacts) -> str:
    """Recompute the sizing artifact bundle digest for parity verification."""
    from hexagent.api.artifacts import compute_sizing_artifact_bundle_digest

    return compute_sizing_artifact_bundle_digest(artifact_bundle)


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
    envelope: _RunEnvelope | None = None
    artifact_bundle: _ArtifactBundle | None = None
    failure: FrozenFailurePayload | None = None


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
        envelope: _RunEnvelope,
        artifact_bundle: _ArtifactBundle,
    ) -> RunRecord: ...

    def fail(
        self,
        *,
        owner_token: UUID,
        expected_version: int,
        failure: FrozenFailurePayload,
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

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._lock = threading.Lock()
        self._records: dict[UUID, RunRecord] = {}
        self._by_namespace: dict[str, UUID] = {}
        self._clock = clock  # injectable for testing

    # -- helpers -----------------------------------------------------------

    def _now(self) -> datetime:
        if self._clock is not None:
            return self._clock()
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
        envelope: _RunEnvelope,
        artifact_bundle: _ArtifactBundle,
    ) -> RunRecord:
        with self._lock:
            record = self._find_by_owner(owner_token, expected_version)
            if record.state != RunState.RUNNING:
                raise RepositoryStateError(f"complete() requires RUNNING state, got {record.state}")

            # ---- Typed operation dispatch (P0-3) ----
            if record.operation == "rateDoublePipe":
                self._complete_rating(
                    record=record,
                    envelope=envelope,
                    artifact_bundle=artifact_bundle,
                )
            elif record.operation == "sizeDoublePipe":
                self._complete_sizing(
                    record=record,
                    envelope=envelope,
                    artifact_bundle=artifact_bundle,
                )
            else:
                raise RepositoryStateError(f"complete() unsupported operation: {record.operation}")

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

    # -- typed complete sub-dispatchers (P0-3) --------------------------------

    def _complete_rating(
        self,
        *,
        record: RunRecord,
        envelope: _RunEnvelope,
        artifact_bundle: _ArtifactBundle,
    ) -> None:
        """RATING-specific complete: typed dispatch + full parity (P0-3)."""
        from hexagent.api.artifacts import RatingRunArtifacts, verify_rating_artifact_bundle
        from hexagent.api.envelopes import RatingRunEnvelope

        # 1. Typed isinstance checks
        if not isinstance(envelope, RatingRunEnvelope):
            raise RepositoryStateError(
                f"rateDoublePipe requires RatingRunEnvelope, got {type(envelope).__name__}"  # noqa: E501
            )
        if not isinstance(artifact_bundle, RatingRunArtifacts):
            raise RepositoryStateError(
                f"rateDoublePipe requires RatingRunArtifacts, got {type(artifact_bundle).__name__}"  # noqa: E501
            )

        # 2. Operation parity
        if envelope.operation != record.operation:
            raise ValueError(
                f"envelope.operation {envelope.operation!r} != record.operation {record.operation!r}"  # noqa: E501
            )

        # 3. Request digest parity
        if envelope.request_digest != record.request_digest:
            raise ValueError(
                f"envelope.request_digest {envelope.request_digest!r} != record.request_digest {record.request_digest!r}"  # noqa: E501
            )

        # 4. Bundle identity (value equality)
        if envelope.artifact_bundle != artifact_bundle:
            raise ValueError("envelope.artifact_bundle != artifact_bundle")

        # 5. Result parity
        if artifact_bundle.result != envelope.result:
            raise ValueError("artifact_bundle.result != envelope.result")

        # 6. artifact_bundle_digest parity
        if artifact_bundle.artifact_bundle_digest != envelope.artifact_bundle_digest:
            raise ValueError(
                "artifact_bundle.artifact_bundle_digest != envelope.artifact_bundle_digest"  # noqa: E501
            )

        # 7. Recomputed bundle digest parity
        recomputed = _recompute_rating_bundle_digest(artifact_bundle)
        if recomputed != envelope.artifact_bundle_digest:
            raise ValueError(
                f"recomputed bundle digest {recomputed!r} != envelope.artifact_bundle_digest {envelope.artifact_bundle_digest!r}"  # noqa: E501
            )

        # 8. Provenance parity
        if artifact_bundle.provenance_graph != envelope.provenance:
            raise ValueError("artifact_bundle.provenance_graph != envelope.provenance")

        # 9. result_hash parity
        if envelope.result.result_hash != envelope.result_hash:
            raise ValueError("result.result_hash != envelope.result_hash")

        # 10. provenance_digest parity
        if envelope.result.provenance_digest != envelope.provenance_digest:
            raise ValueError("result.provenance_digest != envelope.provenance_digest")

        # 11. Canonical request digest recomputation (P0-2)
        from hexagent.api.canonical_request import compute_api_request_digest

        if artifact_bundle.canonical_request_snapshot is not None:
            recomputed_req = compute_api_request_digest(
                artifact_bundle.canonical_request_snapshot
            )
            if recomputed_req != record.request_digest:
                raise ValueError(
                    f"canonical request digest mismatch: "
                    f"recomputed={recomputed_req!r} != record={record.request_digest!r}"
                )
            if recomputed_req != envelope.request_digest:
                raise ValueError(
                    f"canonical request digest mismatch with envelope: "
                    f"recomputed={recomputed_req!r} != envelope={envelope.request_digest!r}"
                )

        # 12. Full bundle verification
        verify_rating_artifact_bundle(artifact_bundle)

    def _complete_sizing(
        self,
        *,
        record: RunRecord,
        envelope: _RunEnvelope,
        artifact_bundle: _ArtifactBundle,
    ) -> None:
        """SIZING-specific complete: typed dispatch + full parity (P0-3)."""
        from hexagent.api.artifacts import SizingRunArtifacts, verify_sizing_artifact_bundle
        from hexagent.api.envelopes import SizingRunEnvelope

        # 1. Typed isinstance checks
        if not isinstance(envelope, SizingRunEnvelope):
            raise RepositoryStateError(
                f"sizeDoublePipe requires SizingRunEnvelope, got {type(envelope).__name__}"  # noqa: E501
            )
        if not isinstance(artifact_bundle, SizingRunArtifacts):
            raise RepositoryStateError(
                f"sizeDoublePipe requires SizingRunArtifacts, got {type(artifact_bundle).__name__}"  # noqa: E501
            )

        # 2. Operation parity
        if envelope.operation != record.operation:
            raise ValueError(
                f"envelope.operation {envelope.operation!r} != record.operation {record.operation!r}"  # noqa: E501
            )

        # 3. Request digest parity
        if envelope.request_digest != record.request_digest:
            raise ValueError(
                f"envelope.request_digest {envelope.request_digest!r} != record.request_digest {record.request_digest!r}"  # noqa: E501
            )

        # 4. Bundle identity (value equality)
        if envelope.artifact_bundle != artifact_bundle:
            raise ValueError("envelope.artifact_bundle != artifact_bundle")

        # 5. optimization_result parity (sizing uses optimization_result)
        if artifact_bundle.optimization_result != envelope.result:
            raise ValueError("artifact_bundle.optimization_result != envelope.result")

        # 6. artifact_bundle_digest parity
        if artifact_bundle.artifact_bundle_digest != envelope.artifact_bundle_digest:
            raise ValueError(
                "artifact_bundle.artifact_bundle_digest != envelope.artifact_bundle_digest"  # noqa: E501
            )

        # 7. Recomputed bundle digest parity
        recomputed = _recompute_sizing_bundle_digest(artifact_bundle)
        if recomputed != envelope.artifact_bundle_digest:
            raise ValueError(
                f"recomputed bundle digest {recomputed!r} != envelope.artifact_bundle_digest {envelope.artifact_bundle_digest!r}"  # noqa: E501
            )

        # 8. Provenance parity
        if artifact_bundle.provenance_graph != envelope.provenance:
            raise ValueError("artifact_bundle.provenance_graph != envelope.provenance")

        # 9. result_hash parity
        if envelope.result.result_hash != envelope.result_hash:
            raise ValueError("result.result_hash != envelope.result_hash")

        # 10. provenance_digest parity
        if envelope.result.provenance_digest != envelope.provenance_digest:
            raise ValueError("result.provenance_digest != envelope.provenance_digest")

        # 11. Canonical request digest recomputation (P0-2)
        from hexagent.api.canonical_request import compute_api_request_digest

        if artifact_bundle.canonical_request_snapshot is not None:
            recomputed_req = compute_api_request_digest(
                artifact_bundle.canonical_request_snapshot
            )
            if recomputed_req != record.request_digest:
                raise ValueError(
                    f"canonical request digest mismatch: "
                    f"recomputed={recomputed_req!r} != record={record.request_digest!r}"
                )
            if recomputed_req != envelope.request_digest:
                raise ValueError(
                    f"canonical request digest mismatch with envelope: "
                    f"recomputed={recomputed_req!r} != envelope={envelope.request_digest!r}"
                )

        # 12. Full bundle verification
        verify_sizing_artifact_bundle(artifact_bundle)

    def fail(
        self,
        *,
        owner_token: UUID,
        expected_version: int,
        failure: FrozenFailurePayload,
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
