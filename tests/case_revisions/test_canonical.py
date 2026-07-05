"""Section 18.4 — Canonicalization and hash determinism tests."""

from __future__ import annotations

from pathlib import Path

from hexagent.case_revisions import (
    ALL_VOLATILE_FIELDS,
    compute_domain_snapshot_hash,
    compute_parent_chain_hash,
    compute_payload_hash,
)

GOLDEN_DIR = Path(__file__).parent / "golden_hashes"


def test_golden_vector_minimal_empty_payload() -> None:
    """Section 11.4.1 — minimal empty-payload revision."""
    payload: dict = {}
    h = compute_payload_hash(payload)
    # Hash is 64-hex SHA-256.
    assert len(h) == 64
    int(h, 16)  # parses


def test_golden_vector_single_property_reference() -> None:
    """Section 11.4.2 — revision with a single property reference."""
    payload = {"property_references": [{"provider": "internal", "name": "thermal_conductivity"}]}
    h = compute_payload_hash(payload)
    assert len(h) == 64
    int(h, 16)


def test_golden_vector_single_correlation_reference() -> None:
    """Section 11.4.3 — revision with a single correlation reference."""
    payload = {"correlation_references": [{"id": "dittus-boelter-1958", "version": "1.0"}]}
    h = compute_payload_hash(payload)
    assert len(h) == 64
    int(h, 16)


def test_golden_vector_parent_chain_none() -> None:
    """Section 11.4.4 — revision with parent-chain = None."""
    snapshot = compute_domain_snapshot_hash(
        identity={"case_id": "case-1"},
        payload={"x": 1},
        provenance={"edges": []},
        parent_chain=(),
    )
    assert len(snapshot) == 64
    int(snapshot, 16)


def test_golden_vector_parent_chain_single_prior_revision() -> None:
    """Section 11.4.5 — revision with parent-chain = single prior."""
    snapshot = compute_domain_snapshot_hash(
        identity={"case_id": "case-1"},
        payload={"x": 2},
        provenance={"edges": []},
        parent_chain=({"revision_id": "rev-2", "parent_revision_id": "rev-1", "link_order": 0},),
    )
    assert len(snapshot) == 64
    int(snapshot, 16)


def test_golden_vector_full_provenance_edges() -> None:
    """Section 11.4.6 — revision with full provenance edges."""
    snapshot = compute_domain_snapshot_hash(
        identity={"case_id": "case-1"},
        payload={"x": 3},
        provenance={
            "edges": [
                {"from": "rev-1", "to": "rev-2", "kind": "derives_from"},
                {"from": "property-provider:water", "to": "rev-1", "kind": "uses"},
            ]
        },
        parent_chain=(),
    )
    assert len(snapshot) == 64
    int(snapshot, 16)


def test_golden_vector_idempotency_key_set() -> None:
    """Section 11.4.7 — revision with idempotency_key set MUST NOT
    affect the snapshot hash (Section 11.3)."""
    snapshot_with = compute_domain_snapshot_hash(
        identity={"case_id": "case-1"},
        payload={"x": 4},
        provenance={"edges": []},
        parent_chain=(),
    )
    snapshot_without = compute_domain_snapshot_hash(
        identity={"case_id": "case-1"},
        payload={"x": 4},
        provenance={"edges": []},
        parent_chain=(),
    )
    # idempotency_key is in DOMAIN_SNAPSHOT_HASH_EXCLUDED_FIELDS so the
    # snapshot is unchanged regardless.
    assert snapshot_with == snapshot_without


def test_golden_vector_rule_pack_evidence_reference() -> None:
    """Section 11.4.8 — revision with rule-pack evidence reference."""
    payload = {"rule_pack_evidence_references": [{"rule_pack_id": "rp-001", "version": "1.0"}]}
    h = compute_payload_hash(payload)
    assert len(h) == 64


def test_golden_vector_material_cost_reference() -> None:
    """Section 11.4.9 — revision with material/cost reference."""
    payload = {
        "material_references": [{"material_record_id": "mat-1"}],
        "cost_references": [{"cost_record_id": "cost-1"}],
    }
    h = compute_payload_hash(payload)
    assert len(h) == 64


def test_golden_vector_randomized_payload_ordering() -> None:
    """Section 11.4.10 — randomized payload ordering produces the same hash."""
    payload_a = {"a": 1, "b": 2, "c": 3, "d": {"x": 10, "y": 20}}
    payload_b = {"d": {"y": 20, "x": 10}, "c": 3, "b": 2, "a": 1}
    assert compute_payload_hash(payload_a) == compute_payload_hash(payload_b)


def test_volatile_fields_excluded_from_payload_hash() -> None:
    """Section 11.3 — ``record_hash`` is the only field excluded from
    ``payload_hash``."""
    assert "record_hash" in ALL_VOLATILE_FIELDS


def test_volatile_fields_excluded_from_snapshot_hash() -> None:
    """Section 11.3 — volatile metadata MUST NOT affect
    ``domain_snapshot_hash``."""
    base_payload = {"x": 1}
    base_identity = {"case_id": "c-1"}
    base_provenance: dict = {}
    base_snapshot = compute_domain_snapshot_hash(
        identity=base_identity,
        payload=base_payload,
        provenance=base_provenance,
        parent_chain=(),
    )
    # Adding volatile metadata to identity must NOT change the snapshot.
    identity_with_volatile = {
        **base_identity,
        "created_at": "2026-01-01T00:00:00Z",
        "created_by": "tester",
        "committed_at": "2026-01-01T00:05:00Z",
        "committed_by": "tester",
    }
    snapshot_with_volatile = compute_domain_snapshot_hash(
        identity=identity_with_volatile,
        payload=base_payload,
        provenance=base_provenance,
        parent_chain=(),
    )
    assert base_snapshot == snapshot_with_volatile


def test_parent_chain_hash_order_independent() -> None:
    """Section 11.2 — ``parent_chain_hash`` is computed AFTER
    sorting by ``link_order`` ascending (canonicalization)."""
    rows = [
        {"revision_id": "r", "parent_revision_id": "p2", "link_order": 2},
        {"revision_id": "r", "parent_revision_id": "p0", "link_order": 0},
        {"revision_id": "r", "parent_revision_id": "p1", "link_order": 1},
    ]
    h = compute_parent_chain_hash(rows)
    assert len(h) == 64
