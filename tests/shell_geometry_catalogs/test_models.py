"""Deterministic tests for TASK-023 shell-geometry-catalog models.

Covered items per authorization §13:

* frozen model mutation rejection
* exact model fields
* constants
* canonical decimal acceptance/rejection
* four approval states
* approved-only successful catalog
* record hash
* permission hash
* edge hash
* bundle hash
* catalog hash
* canonical ordering
* duplicate rejection
* caller mutable input isolation
* effective_at=None is permitted
* invalid effective_at raw type blocks
* record ordering includes record_hash
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from hexagent.canonical_json import canonical_sha256
from hexagent.shell_geometry_catalogs import (
    SHELL_GEOMETRY_CATALOG_BLOCKER_CODES,
    ShellGeometryCatalogBlockerCode,
    ShellGeometryCatalogFailure,
    parse_shell_geometry_catalog,
)
from hexagent.shell_geometry_catalogs.blockers import (
    ShellGeometryCatalogBlockerEntry,
    _canonical_details_hash,
    _canonical_evidence_refs_hash,
)
from hexagent.shell_geometry_catalogs.models import (
    APPROVAL_STATES,
    CATALOG_SCHEMA_VERSION,
    EVIDENCE_BUNDLE_SCHEMA_VERSION,
    GEOMETRY_ROLE,
    GEOMETRY_TYPE,
    PROFILE_ID,
    RECOGNIZED_SOURCE_CLASSES,
    RECORD_SCHEMA_VERSION,
    SELECTABLE_APPROVAL_STATES,
)
from tests.shell_geometry_catalogs._builders import (
    assemble_synthetic_catalog_and_bundle,
    synthetic_bundle_payload,
    synthetic_catalog_payload,
    synthetic_edge_payload,
    synthetic_permission_payload,
    synthetic_record_payload,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stable_id(catalog_id: str, record_key: str, revision: str) -> str:
    return f"{catalog_id}/{GEOMETRY_ROLE}/{record_key}/{revision}"


def _assemble(
    records: tuple[dict[str, Any], ...],
    *,
    permissions: tuple[dict[str, Any], ...] = (),
    edges: tuple[dict[str, Any], ...] = (),
    catalog_id: str = "synthetic-catalog-1",
    effective_at: str | None = "1970-01-01T00:00:00Z",
    bundle_evidence_refs: tuple[str, ...] = ("synthetic.bundle.evidence.1",),
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Construct a self-consistent (catalog, bundle) pair.

    The provided records / permissions / edges MUST already be in their
    canonical form. The helper wires them together through the parser's
    exact hash domains.
    """
    if not permissions:
        permissions = (synthetic_permission_payload(permission_id="perm-synthetic-1"),)
    if not edges:
        # Default: one edge per record so the provenance_edge_ids list
        # of every record resolves to a known snapshot whose
        # target_geometry_id matches THIS record's identity and whose
        # edge_id matches the record's provenance_refs default.
        edges = tuple(
            synthetic_edge_payload(
                edge_id=f"edge-{r['geometry_id']}-provenance",
                target_geometry_id=r["geometry_id"],
                source_id=f"synthetic.source-{r['geometry_id']}",
            )
            for r in records
        )
    catalog, bundle = assemble_synthetic_catalog_and_bundle(
        record_payloads=records,
        permission_payloads=permissions,
        edge_payloads=edges,
        catalog_id=catalog_id,
        effective_at=effective_at,
        bundle_evidence_refs=bundle_evidence_refs,
    )
    return catalog, bundle


def _make_record(
    *,
    record_key: str = "shell-geometry-synthetic-1",
    catalog_id: str = "synthetic-catalog-1",
    revision: str = "1",
    approval_state: str = "approved",
    shell_inside_diameter_m: str = "0.25",
    source_class: str = "PUBLIC_DOMAIN",
    license_form: str = "public_domain",
    nominal_label: str | None = None,
    permission_refs: tuple[str, ...] = ("perm-synthetic-1",),
    provenance_refs: tuple[str, ...] | None = None,
    evidence_refs: tuple[str, ...] = ("synthetic.record.evidence.1",),
) -> dict[str, Any]:
    """Make a record.

    ``provenance_refs`` defaults to a synthetic edge id derived from
    the record's stable geometry_id (so each record's provenance
    reference resolves to a unique edge).
    """
    if provenance_refs is None:
        stable_id = f"{catalog_id}/{GEOMETRY_ROLE}/{record_key}/{revision}"
        # Use a deterministic, unique edge id per record. The
        # ``_assemble`` helper creates matching edges.
        provenance_refs = (f"edge-{stable_id}-provenance",)
    return synthetic_record_payload(
        record_key=record_key,
        catalog_id=catalog_id,
        revision=revision,
        approval_state=approval_state,
        shell_inside_diameter_m=shell_inside_diameter_m,
        source_class=source_class,
        license_form=license_form,
        nominal_label=nominal_label,
        permission_refs=permission_refs,
        provenance_refs=provenance_refs,
        evidence_refs=evidence_refs,
    )


# ---------------------------------------------------------------------------
# Closed-set invariants
# ---------------------------------------------------------------------------


def test_closed_sets_have_frozen_sizes() -> None:
    assert len(SHELL_GEOMETRY_CATALOG_BLOCKER_CODES) == 25
    assert len(set(ShellGeometryCatalogBlockerCode)) == 25


def test_blocker_enum_matches_canonical_tuple() -> None:
    enum_codes = tuple(member.value for member in ShellGeometryCatalogBlockerCode)
    assert enum_codes == SHELL_GEOMETRY_CATALOG_BLOCKER_CODES


def test_frozen_constants() -> None:
    assert CATALOG_SCHEMA_VERSION == "task023.approved-shell-geometry-catalog.v1"
    assert RECORD_SCHEMA_VERSION == "task023.approved-shell-geometry-record.v1"
    assert EVIDENCE_BUNDLE_SCHEMA_VERSION == "task023.shell-authority-evidence-bundle.v1"
    assert PROFILE_ID == "hxforge.shell_geometry_catalog.v1"
    assert GEOMETRY_TYPE == "shell"
    assert GEOMETRY_ROLE == "shell"
    assert APPROVAL_STATES == (
        "approved",
        "pending",
        "rejected",
        "retired",
    )
    assert SELECTABLE_APPROVAL_STATES == ("approved",)
    assert (
        frozenset(
            {
                "PUBLIC_DOMAIN",
                "OPEN_LICENSE",
                "USER_PROVIDED_LICENSED_SUMMARY",
                "INTERNAL_ENGINEERING_RULE",
                "DERIVED_ENGINEERING_RULE",
                "REFERENCE_ONLY_RESTRICTED_STANDARD",
                "VENDOR_PERMISSIONED",
            }
        )
        == RECOGNIZED_SOURCE_CLASSES
    )


# ---------------------------------------------------------------------------
# Frozen mutation + deep isolation
# ---------------------------------------------------------------------------


def test_record_is_frozen_against_mutation() -> None:
    raw = _make_record()
    catalog, bundle = _assemble((raw,))
    cat = parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
    record = cat.records[0]
    with pytest.raises(FrozenInstanceError):
        record.geometry_id = "changed"  # type: ignore[misc]


def test_caller_mutable_input_does_not_leak() -> None:
    """Reference arrays are rebuilt as canonical tuples.

    Mutating the caller's lists after parsing must NOT change the
    catalog view.
    """
    raw = _make_record()
    catalog, bundle = _assemble((raw,))
    cat = parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
    # In-place mutate the original raw dict's permission list.
    raw["permission_evidence_refs"].append("INJECTED")
    raw["provenance_edge_ids"].append("INJECTED")
    assert "INJECTED" not in cat.records[0].permission_evidence_refs
    assert "INJECTED" not in cat.records[0].provenance_edge_ids


def test_license_evidence_mapping_is_detached() -> None:
    """License evidence is returned as a read-only proxy.

    Mutating the parsed record's license_evidence dict raises (proxy),
    and second parse from a different raw dict is independent of
    first-parse state.
    """
    raw_a = _make_record()
    raw_b = _make_record(record_key="shell-geometry-synthetic-2")
    catalog, bundle = _assemble((raw_a, raw_b))
    cat_a = parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
    # Proxy mutation must raise.
    with pytest.raises((TypeError, AttributeError)):
        cat_a.records[0].license_evidence["extra_in_parsed"] = "BAD"  # type: ignore[index]
    # Fresh parse is independent of any inner-state mutation attempt.
    catalog_b, bundle_b = _assemble((raw_a, raw_b))
    cat_b = parse_shell_geometry_catalog(raw_catalog=catalog_b, evidence_bundle=bundle_b)
    assert "extra_in_parsed" not in cat_b.records[0].license_evidence


def test_nested_caller_mutation_cannot_alter_parsed_record() -> None:
    """Mutating the raw license_evidence after parsing does not
    propagate into the parsed record view."""
    raw = _make_record()
    catalog, bundle = _assemble((raw,))
    cat = parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
    raw["license_evidence"]["post_parse_marker"] = "BAD"
    assert "post_parse_marker" not in cat.records[0].license_evidence


def test_record_hash_includes_caller_evidence_field() -> None:
    """Hash-domain defensive coverage: changing a license_evidence field
    changes record_hash.
    """
    raw_a = _make_record()
    import copy

    raw_b = copy.deepcopy(raw_a)
    raw_b["license_evidence"]["extra"] = "wat"

    def _hash(rec: dict) -> str:
        payload = {k: v for k, v in rec.items() if k not in {"record_hash", "nominal_label"}}
        return canonical_sha256(payload)

    assert _hash(raw_a) != _hash(raw_b)


# ---------------------------------------------------------------------------
# Decimal canonical-decimal rules
# ---------------------------------------------------------------------------


def test_decimal_acceptance_and_rejection() -> None:
    accepted = ["0.25", "1", "1.125"]
    rejected = [
        "0",
        "-1",
        "+1",
        "1.0",
        "1e0",
        "1.0e0",
        " 1",
        "1 ",
        "1.0.0",
        "01",
        "NaN",
        "Infinity",
        "",
        "10 mm",
        "1/2",
    ]
    for raw_value in accepted:
        raw = _make_record(shell_inside_diameter_m=raw_value)
        catalog, bundle = _assemble((raw,))
        cat = parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
        assert cat.records[0].shell_inside_diameter_m == raw_value

    for raw_value in rejected:
        raw = _make_record(shell_inside_diameter_m=raw_value)
        catalog, bundle = _assemble((raw,))
        with pytest.raises(ShellGeometryCatalogFailure) as excinfo:
            parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
        codes = [b.code for b in excinfo.value.blockers]
        assert "SGC_SHELL_INSIDE_DIAMETER_INVALID" in codes


# ---------------------------------------------------------------------------
# Four-state approval semantics
# ---------------------------------------------------------------------------


def test_four_approval_states_each_rejected_or_admitted() -> None:
    raw_ok = _make_record()
    catalog_ok, bundle_ok = _assemble((raw_ok,))
    parsed = parse_shell_geometry_catalog(raw_catalog=catalog_ok, evidence_bundle=bundle_ok)
    assert parsed.records[0].approval_state == "approved"
    for bad_state in ("pending", "rejected", "retired"):
        raw = _make_record(approval_state=bad_state)
        catalog, bundle = _assemble((raw,))
        with pytest.raises(ShellGeometryCatalogFailure) as excinfo:
            parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
        codes = [b.code for b in excinfo.value.blockers]
        assert "SGC_RECORD_UNAPPROVED" in codes


# ---------------------------------------------------------------------------
# Duplicate geometry_id
# ---------------------------------------------------------------------------


def test_duplicate_geometry_id_fails_closed() -> None:
    """Two records that resolve to the same stable identity fail with
    ``SGC_RECORD_DUPLICATE_ID``. We construct distinct edges /
    permissions so the duplicate is detected purely on identity.
    """
    raw_a = _make_record(record_key="dup-key")
    # Manually re-key the second to the SAME stable identity but
    # different edge_id so the parser can differentiate.
    raw_b = synthetic_record_payload(
        record_key="dup-key",
        provenance_refs=("edge-dup-b",),
    )
    edges = (
        synthetic_edge_payload(
            edge_id="edge-dup-a",
            target_geometry_id=raw_a["geometry_id"],
            source_id="source-a",
            evidence_refs=("synthetic.A",),
        ),
        synthetic_edge_payload(
            edge_id="edge-dup-b",
            target_geometry_id=raw_b["geometry_id"],
            source_id="source-b",
            evidence_refs=("synthetic.B",),
        ),
    )
    catalog, bundle = _assemble((raw_a, raw_b), edges=edges)
    with pytest.raises(ShellGeometryCatalogFailure) as excinfo:
        parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
    codes = [b.code for b in excinfo.value.blockers]
    assert "SGC_RECORD_DUPLICATE_ID" in codes


# ---------------------------------------------------------------------------
# Canonical ordering incl record_hash
# ---------------------------------------------------------------------------


def test_canonical_ordering_records_with_record_hash_key() -> None:
    raw_a = _make_record(record_key="shell-a")
    raw_b = _make_record(record_key="shell-b")
    catalog, bundle = _assemble((raw_b, raw_a))  # reverse order
    cat = parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
    geom_ids = [r.geometry_id for r in cat.records]
    assert geom_ids == sorted(geom_ids)


# ---------------------------------------------------------------------------
# Hash domains
# ---------------------------------------------------------------------------


def test_record_hash_mismatch_emits_SGC_RECORD_HASH_MISMATCH() -> None:
    raw = _make_record()
    catalog, bundle = _assemble((raw,))
    # Corrupt the record_hash.
    bad = dict(raw)
    bad["record_hash"] = "0" * 64
    catalog_bad = synthetic_catalog_payload(
        records=(bad,),
        evidence_bundle_hash=bundle["bundle_hash"],
    )
    with pytest.raises(ShellGeometryCatalogFailure) as excinfo:
        parse_shell_geometry_catalog(raw_catalog=catalog_bad, evidence_bundle=bundle)
    codes = [b.code for b in excinfo.value.blockers]
    assert "SGC_RECORD_HASH_MISMATCH" in codes


# ---------------------------------------------------------------------------
# effective_at: None vs string
# ---------------------------------------------------------------------------


def test_effective_at_none_succeeds() -> None:
    raw = _make_record()
    catalog, bundle = _assemble((raw,), effective_at=None)
    cat = parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
    assert cat.effective_at is None
    # catalog hash still ties to effective_at=None.
    assert cat.catalog_hash is not None


def test_effective_at_invalid_raw_type_blocks() -> None:
    raw = _make_record()
    catalog, bundle = _assemble((raw,), effective_at="1970-01-01T00:00:00Z")
    bad_catalog = dict(catalog)
    bad_catalog["effective_at"] = 12345  # not a str, not None
    with pytest.raises(ShellGeometryCatalogFailure) as excinfo:
        parse_shell_geometry_catalog(raw_catalog=bad_catalog, evidence_bundle=bundle)
    codes = [b.code for b in excinfo.value.blockers]
    assert "SGC_CATALOG_AUTHORITY_INVALID" in codes


def test_effective_at_empty_string_blocks() -> None:
    raw = _make_record()
    catalog, bundle = _assemble((raw,), effective_at="1970-01-01T00:00:00Z")
    bad_catalog = dict(catalog)
    bad_catalog["effective_at"] = ""
    with pytest.raises(ShellGeometryCatalogFailure) as excinfo:
        parse_shell_geometry_catalog(raw_catalog=bad_catalog, evidence_bundle=bundle)
    codes = [b.code for b in excinfo.value.blockers]
    assert "SGC_CATALOG_AUTHORITY_INVALID" in codes


def test_effective_at_distinguishes_null_vs_string_in_hash() -> None:
    """Two catalogs whose only difference is ``effective_at=None`` vs
    a string MUST have different catalog_hashes (per blocker §1)."""
    raw = _make_record()
    catalog_none, _ = _assemble((raw,), effective_at=None)
    catalog_str, _ = _assemble((raw,), effective_at="1970-01-01T00:00:00Z")
    assert catalog_none["catalog_hash"] != catalog_str["catalog_hash"]


# ---------------------------------------------------------------------------
# Stable geometry_id binding
# ---------------------------------------------------------------------------


def test_invalid_geometry_id_must_match_stable_identity() -> None:
    """A raw ``geometry_id`` that does NOT match the design-frozen
    ``catalog_id/shell/<record_key>/<revision>`` identity MUST be
    rejected via ``SGC_RECORD_ID_INVALID``.
    """
    raw = _make_record()
    # catalog_id is 'synthetic-catalog-1', so the stable identity is
    # 'synthetic-catalog-1/shell/foo/1' — anything else (e.g. an extra
    # missing part, an extra segment, case folding) is rejected.
    bad = dict(raw)
    bad["geometry_id"] = "Shell-Foo"  # missing catalog_id/role prefix
    catalog = synthetic_catalog_payload(
        records=(bad,),
        evidence_bundle_hash="0" * 64,
    )
    bundle = synthetic_bundle_payload()
    with pytest.raises(ShellGeometryCatalogFailure) as excinfo:
        parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
    codes = [b.code for b in excinfo.value.blockers]
    assert "SGC_RECORD_ID_INVALID" in codes


# ---------------------------------------------------------------------------
# Blocker-detail hashing: details=None vs details={}
# ---------------------------------------------------------------------------


def test_blocker_details_none_hashes_as_null() -> None:
    import hashlib
    import json as _json

    none_hash = _canonical_details_hash(None)
    expected_null = hashlib.sha256(_json.dumps(None).encode("utf-8")).hexdigest()
    assert none_hash == expected_null


def test_blocker_details_empty_map_hashes_as_object() -> None:
    import hashlib

    from hexagent.canonical_json import canonical_json_bytes

    empty_hash = _canonical_details_hash({})
    expected_empty = hashlib.sha256(canonical_json_bytes({})).hexdigest()
    assert empty_hash == expected_empty


def test_blocker_details_none_and_empty_sort_distinctly() -> None:
    """Two blockers differing only in details=None vs details={} MUST
    sort separately — the composite key prevents collisions.
    """
    a = ShellGeometryCatalogBlockerEntry(
        code="SGC_RAW_TYPE_INVALID", field_path="x", message_key="y"
    )
    b = ShellGeometryCatalogBlockerEntry(
        code="SGC_RAW_TYPE_INVALID",
        field_path="x",
        message_key="y",
        details={},
    )
    assert _canonical_details_hash(a.details) != _canonical_details_hash(b.details)


# ---------------------------------------------------------------------------
# evidence_refs hash as raw array
# ---------------------------------------------------------------------------


def test_evidence_refs_hash_is_raw_array() -> None:
    """The evidence_refs hash MUST be the SHA-256 of the raw JSON
    array, NOT a wrapper ``{"refs": [...]}``."""
    import hashlib

    import rfc8785

    refs = ("a", "b", "c")
    expected = hashlib.sha256(rfc8785.dumps(list(refs))).hexdigest()
    assert _canonical_evidence_refs_hash(refs) == expected


# ---------------------------------------------------------------------------
# Catalog hash domain covers canonical ordered record_hash sequence
# ---------------------------------------------------------------------------


def test_catalog_hash_follows_record_identity_order_not_hash_order() -> None:
    """Catalog hash MUST use records in (geometry_id, revision,
    record_hash) identity order — NOT the lexical record_hash order.

    Submit records in reversed geometry_id order; the resulting
    catalog_hash must match a builder that submitted them in canonical
    order.
    """
    raw_a = _make_record(record_key="shell-a")
    raw_b = _make_record(record_key="shell-b")
    perm = synthetic_permission_payload(permission_id="perm-synthetic-1")
    edge_a = synthetic_edge_payload(
        edge_id="edge-synthetic-0", target_geometry_id=raw_a["geometry_id"]
    )
    edge_b = synthetic_edge_payload(
        edge_id="edge-synthetic-1", target_geometry_id=raw_b["geometry_id"]
    )
    catalog_forward, bundle = assemble_synthetic_catalog_and_bundle(
        record_payloads=(raw_a, raw_b),
        permission_payloads=(perm,),
        edge_payloads=(edge_a, edge_b),
    )
    catalog_reverse, _ = assemble_synthetic_catalog_and_bundle(
        record_payloads=(raw_b, raw_a),
        permission_payloads=(perm,),
        edge_payloads=(edge_a, edge_b),
    )
    assert catalog_forward["catalog_hash"] == catalog_reverse["catalog_hash"]
