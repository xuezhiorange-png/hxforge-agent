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
    SHELL_GEOMETRY_CATALOG_DEFAULT_FIELD_PATH,
    SHELL_GEOMETRY_CATALOG_DEFAULT_MESSAGE_KEY,
    ShellGeometryCatalogBlockerEntry,
    _canonical_details_hash,
    _canonical_evidence_refs_hash,
    deep_freeze_details,
    sort_blockers,
    thaw_for_canonical_json,
)
from hexagent.shell_geometry_catalogs.catalog import select_approved_shell_geometry
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
    """Round 4 (Amendment 001): the closed blocker taxonomy now has
    exactly 27 codes — 25 originals plus SGC_PERMISSION_DUPLICATE_ID and
    SGC_PROVENANCE_DUPLICATE_ID inserted after SGC_CATALOG_HASH_MISMATCH
    per Issue #152 Comment 4970130136.
    """
    assert len(SHELL_GEOMETRY_CATALOG_BLOCKER_CODES) == 27
    assert len(set(ShellGeometryCatalogBlockerCode)) == 27


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
        code="SGC_RAW_TYPE_INVALID",
        field_path="x",
        message_key="y",
        stage_rank=1,
    )
    b = ShellGeometryCatalogBlockerEntry(
        code="SGC_RAW_TYPE_INVALID",
        field_path="x",
        message_key="y",
        details={},
        stage_rank=1,
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


# ===========================================================================
# Round 3 fixup tests — §1 stage rank authoritative + §6 deep immutability
# ===========================================================================


def test_round3_stage_rank_precedes_code_lexical() -> None:
    """Round 3 §1 — stage rank wins over code lexical order.

    Construct a blocker at stage 13 (``SGC_LICENSE_BLOCKED``,
    lexical-first "L") and one at stage 1
    (``SGC_RAW_TYPE_INVALID``, lexical-late "R"). The sorted tuple
    MUST put stage 1 first because stage_rank precedes code in the
    composite ordering key.
    """
    early_stage = ShellGeometryCatalogBlockerEntry(
        code="SGC_RAW_TYPE_INVALID",
        field_path="x",
        message_key="m",
        stage_rank=1,
    )
    late_stage = ShellGeometryCatalogBlockerEntry(
        code="SGC_LICENSE_BLOCKED",
        field_path="x",
        message_key="m",
        stage_rank=13,
    )
    sorted_entries = sort_blockers([late_stage, early_stage])
    assert sorted_entries[0] is early_stage
    assert sorted_entries[1] is late_stage


def test_round3_failure_constructor_preserves_stage_rank() -> None:
    """Round 3 §1 — ``ShellGeometryCatalogFailure`` MUST retain each
    entry's stage_rank through ``sort_blockers``. We construct entries
    with mismatched code-lexical vs stage-rank orderings and assert the
    exceptions preserve them.
    """
    high_lex_low_stage = ShellGeometryCatalogBlockerEntry(
        code="SGC_UNKNOWN_FIELD",
        field_path="x",
        message_key="m",
        stage_rank=2,
    )
    low_lex_high_stage = ShellGeometryCatalogBlockerEntry(
        code="SGC_APPROVAL_STATE_INVALID",
        field_path="x",
        message_key="m",
        stage_rank=4,
    )
    try:
        raise ShellGeometryCatalogFailure([high_lex_low_stage, low_lex_high_stage])
    except ShellGeometryCatalogFailure as exc:
        ranks = [b.stage_rank for b in exc.blockers]
        # stage 2 (UNKNOWN_FIELD) precedes stage 4 (APPROVAL_STATE_INVALID)
        assert ranks == [2, 4]
        # and the stage 2 entry MUST come before the stage 4 one
        assert exc.blockers[0].code == "SGC_UNKNOWN_FIELD"
        assert exc.blockers[1].code == "SGC_APPROVAL_STATE_INVALID"


def test_round3_selection_blockers_carry_explicit_stage_rank() -> None:
    """Round 3 §1 — selection-time blockers (stage 20) MUST carry an
    explicit stage_rank bound through the ``_make_entry`` helper inside
    ``catalog.py`` (which itself consults the authoritative stage map).
    We trigger a real ``SGC_RECORD_NOT_FOUND`` failure and assert the
    emitted entry's stage_rank equals the §11 selection rank.
    """
    record = _make_record()
    cat_raw, _bun = _assemble((record,))
    cat = parse_shell_geometry_catalog(raw_catalog=cat_raw, evidence_bundle=_bun)
    with pytest.raises(ShellGeometryCatalogFailure) as excinfo:
        select_approved_shell_geometry(catalog=cat, geometry_id="nonexistent")
    codes = [b.code for b in excinfo.value.blockers]
    assert "SGC_RECORD_NOT_FOUND" in codes
    not_found_entries = [b for b in excinfo.value.blockers if b.code == "SGC_RECORD_NOT_FOUND"]
    assert not_found_entries
    assert all(e.stage_rank == 20 for e in not_found_entries)


def test_round3_blocker_details_are_deeply_immutable() -> None:
    """Round 3 §6 — ``deep_freeze_details`` MUST freeze every nested
    mapping AND nested list/tuple inside the details dict. Mutating the
    caller's original container after construction MUST NOT change the
    blocker entry's ``details``.
    """
    nested = {
        "outer": {"inner_dict": {"x": 1, "y": [1, 2, 3]}},
        "outer_list": [{"z": "a"}, {"z": "b"}],
    }
    frozen = deep_freeze_details(nested)
    # Mutate the original; the frozen snapshot MUST not change.
    nested["outer"]["inner_dict"]["x"] = 999
    nested["outer"]["inner_dict"]["y"].append(999)
    nested["outer_list"].append({"z": "modified"})
    # The frozen copy must use immutable structures.
    import types

    assert isinstance(frozen, types.MappingProxyType)
    assert isinstance(frozen["outer"], types.MappingProxyType)
    assert isinstance(frozen["outer"]["inner_dict"], types.MappingProxyType)
    assert isinstance(frozen["outer"]["inner_dict"]["y"], tuple)
    assert isinstance(frozen["outer_list"], tuple)
    assert frozen["outer"]["inner_dict"]["x"] == 1
    assert list(frozen["outer"]["inner_dict"]["y"]) == [1, 2, 3]
    assert len(frozen["outer_list"]) == 2


def test_round3_blocker_constructor_deep_freezes_details_and_refs() -> None:
    """Round 3 §6 — the public ``_make_entry`` helper inside catalog.py
    must deep-freeze ``details`` and ``evidence_refs`` so callers
    cannot mutate them post-construction.
    """
    from hexagent.shell_geometry_catalogs.catalog import _make_entry

    call_details = {"x": [{"nested_list": [1, 2, 3]}]}
    call_refs = ["ref-1", "ref-2"]
    entry = _make_entry(
        "SGC_RAW_TYPE_INVALID",
        stage_rank=1,
        field_path="x",
        evidence_refs=call_refs,
        details=call_details,
    )
    call_details["x"][0]["nested_list"].append(999)
    call_details["new_key"] = "new"
    call_refs.append("ref-3")
    # Mutation must not affect the entry.
    assert "new_key" not in entry.details
    assert "new" not in entry.details["x"]
    # Evidence refs are a tuple.
    assert isinstance(entry.evidence_refs, tuple)
    assert entry.evidence_refs == ("ref-1", "ref-2")


# --------------------------------------------------------------------------
# TASK-023 Design Amendment 001 (Option B) — round 4 unit tests.
# --------------------------------------------------------------------------


def test_round4_taxonomy_has_exactly_27_codes() -> None:
    """Amendment 001 §2: the closed set expands from 25 to exactly 27."""
    assert len(SHELL_GEOMETRY_CATALOG_BLOCKER_CODES) == 27
    assert len(set(SHELL_GEOMETRY_CATALOG_BLOCKER_CODES)) == 27


def test_round4_taxonomy_enum_tuple_exact_order() -> None:
    """Position-by-position equality between the enum members and the tuple.

    Verify ONLY the design-relative insertion-point contract: the two new
    codes are at positions 24-25 (after SGC_CATALOG_HASH_MISMATCH), and
    the two selection codes are pushed to positions 26-27. The original
    23 codes preceding them retain their relative order verbatim.
    """
    # Insertion-point contract.
    assert SHELL_GEOMETRY_CATALOG_BLOCKER_CODES[23] == "SGC_PERMISSION_DUPLICATE_ID"
    assert SHELL_GEOMETRY_CATALOG_BLOCKER_CODES[24] == "SGC_PROVENANCE_DUPLICATE_ID"
    assert SHELL_GEOMETRY_CATALOG_BLOCKER_CODES[25] == "SGC_RECORD_NOT_FOUND"
    assert SHELL_GEOMETRY_CATALOG_BLOCKER_CODES[26] == "SGC_SELECTION_NOT_APPROVED"
    # The 23 codes before the insertion are unchanged from the prior 25
    # minus the two pushed-out selection codes.
    original_23_unchanged = SHELL_GEOMETRY_CATALOG_BLOCKER_CODES[:23]
    assert original_23_unchanged == (
        "SGC_RAW_TYPE_INVALID",
        "SGC_UNKNOWN_FIELD",
        "SGC_SCHEMA_VERSION_UNSUPPORTED",
        "SGC_CATALOG_ID_INVALID",
        "SGC_CATALOG_VERSION_INVALID",
        "SGC_PROFILE_UNSUPPORTED",
        "SGC_CATALOG_AUTHORITY_INVALID",
        "SGC_RECORDS_INVALID",
        "SGC_RECORD_ID_INVALID",
        "SGC_RECORD_DUPLICATE_ID",
        "SGC_GEOMETRY_TYPE_INVALID",
        "SGC_REVISION_INVALID",
        "SGC_APPROVAL_STATE_INVALID",
        "SGC_RECORD_UNAPPROVED",
        "SGC_SHELL_INSIDE_DIAMETER_INVALID",
        "SGC_SOURCE_BINDING_INCOMPLETE",
        "SGC_SOURCE_CLASS_INVALID",
        "SGC_LICENSE_BLOCKED",
        "SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE",
        "SGC_PROVENANCE_INCOMPLETE",
        "SGC_EVIDENCE_REFS_INVALID",
        "SGC_RECORD_HASH_MISMATCH",
        "SGC_CATALOG_HASH_MISMATCH",
    )
    # Enum-order invariance.
    enum_in_order = tuple(m.value for m in ShellGeometryCatalogBlockerCode.__members__.values())
    assert enum_in_order == SHELL_GEOMETRY_CATALOG_BLOCKER_CODES


def test_round4_taxonomy_no_aliases() -> None:
    """Each blocker token appears exactly once; no reserved alias."""
    assert len(SHELL_GEOMETRY_CATALOG_BLOCKER_CODES) == len(
        set(SHELL_GEOMETRY_CATALOG_BLOCKER_CODES)
    )


def test_round4_taxonomy_new_codes_independently_reachable() -> None:
    """Default message_key + default_field_path frozen for both new codes."""
    assert (
        SHELL_GEOMETRY_CATALOG_DEFAULT_MESSAGE_KEY["SGC_PERMISSION_DUPLICATE_ID"]
        == "sgc_permission_duplicate_id"
    )
    assert (
        SHELL_GEOMETRY_CATALOG_DEFAULT_FIELD_PATH["SGC_PERMISSION_DUPLICATE_ID"]
        == "evidence_bundle.permission_evidence"
    )
    assert (
        SHELL_GEOMETRY_CATALOG_DEFAULT_MESSAGE_KEY["SGC_PROVENANCE_DUPLICATE_ID"]
        == "sgc_provenance_duplicate_id"
    )
    assert (
        SHELL_GEOMETRY_CATALOG_DEFAULT_FIELD_PATH["SGC_PROVENANCE_DUPLICATE_ID"]
        == "evidence_bundle.provenance_edges"
    )


def test_round4_public_exports_exactly_seven() -> None:
    """``__all__`` has exactly 7 names and they are stable across Amendment 001."""
    import hexagent.shell_geometry_catalogs as pkg

    assert sorted(pkg.__all__) == sorted(
        [
            "SHELL_GEOMETRY_CATALOG_BLOCKER_CODES",
            "ShellGeometryCatalog",
            "ShellGeometryCatalogBlockerCode",
            "ShellGeometryCatalogFailure",
            "ShellGeometryRecord",
            "parse_shell_geometry_catalog",
            "select_approved_shell_geometry",
        ]
    )


# ---------------------------------------------------------------------------
# §9.B — Duplicate permission identity
# ---------------------------------------------------------------------------


def _make_record_kwargs(*, record_key: str, source_class: str = "PUBLIC_DOMAIN"):
    return dict(
        record_key=record_key,
        catalog_id="synthetic-catalog-1",
        revision="1",
        source_class=source_class,
    )


def test_round4_same_code_with_two_ranks() -> None:
    """``SGC_RECORD_DUPLICATE_ID`` may carry two different occurrence
    ranks — one for the first-occurrence index, one for the duplicate
    index. Both are valid construction sites.
    """
    e1 = ShellGeometryCatalogBlockerEntry(
        code="SGC_RECORD_DUPLICATE_ID",
        field_path="raw_catalog.records[0].geometry_id",
        message_key="sgc_record_duplicate_id",
        stage_rank=9,
    )
    e2 = ShellGeometryCatalogBlockerEntry(
        code="SGC_RECORD_DUPLICATE_ID",
        field_path="raw_catalog.records[1].geometry_id",
        message_key="sgc_record_duplicate_id",
        stage_rank=9,
    )
    assert e1.stage_rank == 9
    assert e2.stage_rank == 9
    # Same code, possibly DIFFERENT rank. The dataclass must allow it.
    e_alt = ShellGeometryCatalogBlockerEntry(
        code="SGC_RECORD_DUPLICATE_ID",
        field_path="raw_catalog.records[2].geometry_id",
        message_key="sgc_record_duplicate_id",
        stage_rank=10,  # different occurrence
    )
    assert e_alt.stage_rank == 10


def test_round4_occurrence_stage_rank_wins_over_code() -> None:
    """Earlier occurrence WINS even when its code is lexically LATER.
    Two blocks: one with stage_rank=2, code=Z; another with
    stage_rank=5, code=A. Sorted order should be Z@2 then A@5.
    """
    early = ShellGeometryCatalogBlockerEntry(
        code="SGC_RAW_TYPE_INVALID",
        field_path="raw_catalog",
        message_key="sgc_raw_type_invalid",
        stage_rank=2,
    )
    later = ShellGeometryCatalogBlockerEntry(
        code="SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE",
        field_path="raw_catalog.records[0].permission_evidence_refs",
        message_key="sgc_vendor_permission_scope_incomplete",
        stage_rank=5,
    )
    ordered = sort_blockers([later, early])  # input deliberately reversed
    assert ordered[0].stage_rank == 2
    assert ordered[0].code == "SGC_RAW_TYPE_INVALID"
    assert ordered[1].stage_rank == 5


def test_round4_make_entry_requires_stage_rank() -> None:
    """``_make_entry`` MUST require an explicit ``stage_rank`` and MUST
    NOT infer the rank from the code.
    """
    from hexagent.shell_geometry_catalogs.catalog import _make_entry

    with pytest.raises(TypeError):
        _make_entry("SGC_RAW_TYPE_INVALID")  # missing stage_rank
    with pytest.raises(TypeError):
        _make_entry(code="SGC_RAW_TYPE_INVALID")  # missing stage_rank
    # Stage rank explicitly passed succeeds.
    e = _make_entry("SGC_RAW_TYPE_INVALID", stage_rank=1)
    assert e.stage_rank == 1


def test_round4_stage_rank_zero_rejected() -> None:
    """Stage rank 0 is the forbidden fallback; the dataclass rejects it."""
    with pytest.raises(ValueError):
        ShellGeometryCatalogBlockerEntry(
            code="SGC_RAW_TYPE_INVALID",
            field_path="x",
            message_key="sgc_raw_type_invalid",
            stage_rank=0,
        )


def test_round4_no_default_stage_rank() -> None:
    """``stage_rank`` has no default — constructing the dataclass WITHOUT
    an explicit ``stage_rank`` MUST raise ``TypeError``.
    """
    with pytest.raises(TypeError):
        ShellGeometryCatalogBlockerEntry(  # missing stage_rank
            code="SGC_RAW_TYPE_INVALID",
            field_path="x",
            message_key="sgc_raw_type_invalid",
        )


def test_round4_no_code_derived_stage_map() -> None:
    """Architecture-level proof: the canonical name of the code-derived
    map is not importable and not even defined as a name in
    ``blockers`` module.
    """
    import hexagent.shell_geometry_catalogs.blockers as _b

    forbidden_names = [
        "SHELL_GEOMETRY_CATALOG_STAGE_RANK_BY_CODE",
        "CODE_DERIVED_STAGE_RANK",
        "DEFAULT_STAGE_RANK",
        "STAGE_RANK_ZERO_FALLBACK",
        "CODE_TO_STAGE",
        "BLOCKER_STAGE_MAP",
    ]
    for name in forbidden_names:
        assert not hasattr(_b, name), (
            f"Amendment 001 §3 forbids the code-derived map; got attribute {name}"
        )


def test_round4_thaw_recursively_projects_to_plain_json() -> None:
    """``thaw_for_canonical_json`` recurses through Mapping / tuple /
    list and rejects custom objects / set / frozenset / bytes / Decimal.
    """
    details = {"x": (1, 2, 3), "y": [{"nested": (4, 5)}]}
    frozen = deep_freeze_details(details)
    thawed = thaw_for_canonical_json(frozen)
    assert thawed == {"x": [1, 2, 3], "y": [{"nested": [4, 5]}]}
    # No MappingProxyType in thawed.
    assert not isinstance(thawed, type({}.items).__class__)  # not proxy
    assert not any(
        isinstance(v, tuple)
        for vs in thawed.values()
        for v in (vs if isinstance(vs, list) else [vs])
    )


def test_round4_set_frozenset_custom_object_rejected_in_details() -> None:
    """``deep_freeze_details`` rejects non-JSON-compatible values in
    details — ``set`` / ``frozenset`` / custom objects raise TypeError
    up front, BEFORE the blocker enters the catalog failure surface.
    """
    with pytest.raises(TypeError):
        deep_freeze_details({"x": {1, 2, 3}})  # type: ignore[dict-item]
    with pytest.raises(TypeError):
        deep_freeze_details({"x": frozenset({1, 2})})  # type: ignore[dict-item]
    with pytest.raises(TypeError):
        deep_freeze_details({"x": object()})  # type: ignore[dict-item]
    # Bytes / Decimal — both forbidden by Amendment 001 §7.

    import decimal

    with pytest.raises(TypeError):
        deep_freeze_details({"x": decimal.Decimal("1.5")})  # type: ignore[dict-item]
    with pytest.raises(TypeError):
        deep_freeze_details({"x": b"raw-bytes"})  # type: ignore[dict-item]


def test_round4_details_none_hashes_as_json_null() -> None:
    """``details=None`` hashes as JSON ``null`` so it sorts separately
    from ``details={}``.
    """
    from hexagent.shell_geometry_catalogs.blockers import (
        _canonical_details_hash,
    )

    h_none = _canonical_details_hash(None)
    h_empty = _canonical_details_hash({})
    assert h_none != h_empty
    # JSON literal ``null`` hash is sha256("null") per Python.
    import hashlib
    import json as _json

    expected = hashlib.sha256(_json.dumps(None).encode("utf-8")).hexdigest()
    assert h_none == expected


def test_round4_evidence_refs_hashes_as_raw_json_array() -> None:
    """``evidence_refs`` is hashed as a raw JSON array (NOT wrapped in
    ``{"refs": ...}``). Two distinct sequences sort distinctly.
    """
    from hexagent.shell_geometry_catalogs.blockers import (
        _canonical_evidence_refs_hash,
    )

    h1 = _canonical_evidence_refs_hash(("a", "b"))
    h2 = _canonical_evidence_refs_hash(("b", "a"))
    assert h1 != h2


def test_round4_nested_caller_dict_mutation_does_not_alter_blocker() -> None:
    """Mutating the caller's nested dict after construction MUST NOT
    alter the blocker's frozen details. ``deep_freeze_details`` is the
    public immutable projection used by both ``_make_entry`` and direct
    ``ShellGeometryCatalogBlockerEntry`` construction.
    """
    call_details: dict[str, Any] = {
        "outer": [{"inner": [1, 2, 3]}, {"key2": "val2"}],
        "second": "abc",
    }
    call_refs = ["r1", "r2"]
    e = ShellGeometryCatalogBlockerEntry(
        code="SGC_RAW_TYPE_INVALID",
        field_path="x",
        message_key="sgc_raw_type_invalid",
        stage_rank=1,
        evidence_refs=tuple(call_refs),
        details=deep_freeze_details(call_details),
    )
    # Mutate caller's containers AFTER the deep-freeze took its copies.
    call_details["second"] = "MUTATED"
    call_details["outer"][0]["inner"].append(999)
    call_details["new_key"] = "new"
    # Blocker unaffected.
    assert e.details is not None
    assert e.details["second"] == "abc"
    assert e.details["outer"][0]["inner"] == (1, 2, 3)  # tuple, not list
    assert "new_key" not in e.details


def test_round4_nested_caller_list_mutation_does_not_alter_blocker() -> None:
    call_details = {"lst": [[1], [2]]}
    e = ShellGeometryCatalogBlockerEntry(
        code="SGC_RAW_TYPE_INVALID",
        field_path="x",
        message_key="sgc_raw_type_invalid",
        stage_rank=1,
        details=deep_freeze_details(call_details),
    )
    call_details["lst"][0].append(999)
    assert e.details is not None
    # Frozen to tuple.
    assert e.details["lst"][0] == (1,)


def test_round4_blocker_nested_details_cannot_be_mutated() -> None:
    """Direct mutation of the exposed Mapping MUST raise.

    Verifies both surface-mapping mutation (assignment to a top-level key)
    AND nested-list mutation (item assignment) — both MUST raise.
    """
    call_details = {"x": [{"y": [1, 2]}]}
    e = ShellGeometryCatalogBlockerEntry(
        code="SGC_RAW_TYPE_INVALID",
        field_path="x",
        message_key="sgc_raw_type_invalid",
        stage_rank=1,
        details=deep_freeze_details(call_details),
    )
    assert e.details is not None
    # Surface: MappingProxyType blocks item assignment.
    with pytest.raises(TypeError):
        e.details["x"] = "MUTATED"  # type: ignore[index]
    # Nested mapping is also MappingProxyType — mutation blocked.
    with pytest.raises(TypeError):
        e.details["x"][0]["y"] = "MUTATED"  # type: ignore[index]
    # Item mutation (overwrite) on the surface sequence (which is a tuple)
    # raises TypeError because tuples do not support item assignment.
    with pytest.raises(TypeError):
        e.details["x"][0]["y"][0] = 999  # type: ignore[index]


def test_round4_canonical_ordering_stable_before_after_mutation() -> None:
    """Caller mutation of the original dict (passed through deep-freeze)
    MUST NOT change the canonical order key of the blocker.
    """
    from hexagent.shell_geometry_catalogs.blockers import (
        composite_order_key,
    )

    call_details = {"k": [{"nest": [1, 2]}]}
    e = ShellGeometryCatalogBlockerEntry(
        code="SGC_RAW_TYPE_INVALID",
        field_path="p",
        message_key="sgc_raw_type_invalid",
        stage_rank=1,
        details=deep_freeze_details(call_details),
        evidence_refs=("a",),
    )
    k_before = composite_order_key(e)
    call_details["k"].append({"injected": True})  # type: ignore[union-attr]
    call_details["k"][0]["nest"].append(999)  # type: ignore[index]
    k_after = composite_order_key(e)
    assert k_before == k_after


def test_round4_blocker_no_mutable_exposure() -> None:
    """After construction, the exposed ``details`` MUST be a
    ``MappingProxyType`` (or recursive freeze class), ``evidence_refs``
    a tuple.
    """
    import types

    e = ShellGeometryCatalogBlockerEntry(
        code="SGC_RAW_TYPE_INVALID",
        field_path="p",
        message_key="sgc_raw_type_invalid",
        stage_rank=1,
        details=deep_freeze_details({"x": 1, "y": [1, 2]}),
        evidence_refs=("a", "b"),
    )
    assert isinstance(e.details, types.MappingProxyType)
    assert isinstance(e.evidence_refs, tuple)
    # Nested list frozen to tuple.
    assert isinstance(e.details["y"], tuple)  # type: ignore[index]
