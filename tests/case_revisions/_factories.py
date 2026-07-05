"""Shared fixtures for TASK-014 implementation tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hexagent.case_revisions.canonical import (
    compute_domain_snapshot_hash,
    compute_payload_hash,
)
from hexagent.case_revisions.models import (
    CaseRevision,
    RevisionStatus,
)
from hexagent.case_revisions.optimistic import mint_optimistic_concurrency_token

FIXED_NOW = datetime(2026, 1, 1, tzinfo=UTC)
FIXED_LATER = datetime(2026, 1, 1, 0, 5, tzinfo=UTC)


def _identity() -> dict:
    return {
        "case_id": "case-1",
        "effective_date": "2026-01-01",
        "issuing_body": "INTERNAL",
        "designation": "INTERNAL-NOTE-1",
    }


def _provenance() -> dict:
    return {"edges": []}


def _payload(variant: str = "base") -> dict:
    return {
        "case_id": "case-1",
        "variant": variant,
        "duty_w": 1000.0,
    }


def build_revision(
    *,
    revision_id: str = "rev-1",
    root_case_id: str = "case-1",
    case_id: str = "case-1",
    revision_number: int = 1,
    parent_revision_id: str | None = None,
    payload: dict | None = None,
    identity: dict | None = None,
    provenance: dict | None = None,
    status: RevisionStatus = RevisionStatus.COMMITTED,
    created_at: datetime = FIXED_NOW,
    committed_at: datetime | None = FIXED_LATER,
    expected_parent_revision_id: str | None = None,
    idempotency_key: str | None = None,
    parent_chain_rows: tuple[dict, ...] = (),
) -> CaseRevision:
    """Build a fully-hashed ``CaseRevision`` for tests."""
    p = payload if payload is not None else _payload()
    i = identity if identity is not None else _identity()
    pr = provenance if provenance is not None else _provenance()
    ph = compute_payload_hash(p)
    sh = compute_domain_snapshot_hash(
        identity=i, payload=p, provenance=pr, parent_chain=parent_chain_rows
    )
    return CaseRevision(
        revision_id=revision_id,
        case_id=case_id,
        root_case_id=root_case_id,
        revision_number=revision_number,
        parent_revision_id=parent_revision_id,
        parent_chain_hash=None,
        payload_hash=ph,
        domain_snapshot_hash=sh,
        payload=p,
        identity=i,
        provenance=pr,
        created_at=created_at,
        created_by="tester",
        committed_at=committed_at,
        committed_by="tester",
        status=status,
        expected_parent_revision_id=expected_parent_revision_id,
        idempotency_key=idempotency_key,
        optimistic_concurrency_token=mint_optimistic_concurrency_token(
            revision_id=revision_id, created_at_iso=created_at.isoformat()
        ),
    )


@pytest.fixture
def base_revision() -> CaseRevision:
    return build_revision()
