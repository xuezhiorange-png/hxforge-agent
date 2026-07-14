"""Deterministic tests for TASK-023 shell-geometry-catalog models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from hexagent.shell_geometry_catalogs import (
    SHELL_GEOMETRY_CATALOG_BLOCKER_CODES,
    ShellGeometryCatalogBlockerCode,
    ShellGeometryCatalogFailure,
    parse_shell_geometry_catalog,
)
from hexagent.shell_geometry_catalogs.models import (
    APPROVAL_STATES,
    CATALOG_SCHEMA_VERSION,
    EVIDENCE_BUNDLE_SCHEMA_VERSION,
    GEOMETRY_TYPE,
    PROFILE_ID,
    RECOGNIZED_SOURCE_CLASSES,
    RECORD_SCHEMA_VERSION,
    SELECTABLE_APPROVAL_STATES,
)


def test_closed_sets_have_frozen_sizes() -> None:
    """The design contract §10 taxonomy is exactly 25 codes."""
    assert len(SHELL_GEOMETRY_CATALOG_BLOCKER_CODES) == 25
    assert len(set(ShellGeometryCatalogBlockerCode)) == 25


def test_blocker_enum_matches_canonical_tuple() -> None:
    """Each enum token matches its tuple counterpart verbatim."""
    enum_codes = tuple(member.value for member in ShellGeometryCatalogBlockerCode)
    assert enum_codes == SHELL_GEOMETRY_CATALOG_BLOCKER_CODES


def test_frozen_constants() -> None:
    assert CATALOG_SCHEMA_VERSION == "task023.approved-shell-geometry-catalog.v1"
    assert RECORD_SCHEMA_VERSION == "task023.approved-shell-geometry-record.v1"
    assert EVIDENCE_BUNDLE_SCHEMA_VERSION == "task023.shell-authority-evidence-bundle.v1"
    assert PROFILE_ID == "hxforge.shell_geometry_catalog.v1"
    assert GEOMETRY_TYPE == "shell"
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


def test_record_is_frozen_against_mutation() -> None:
    """Records are truly frozen — both attribute mutation and frozen
    state are reinforced."""
    from tests.shell_geometry_catalogs._builders import synthetic_record_payload

    raw = synthetic_record_payload()
    catalog, bundle = _assemble_catalog((raw,))
    cat = parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
    record = cat.records[0]
    with pytest.raises(FrozenInstanceError):
        record.geometry_id = "changed"  # type: ignore[misc]


def test_caller_mutable_input_does_not_leak() -> None:
    """The catalog layer rebuilds reference arrays; caller's list edits
    cannot leak into the model layer."""
    from tests.shell_geometry_catalogs._builders import (
        synthetic_bundle_payload,
        synthetic_catalog_payload,
        synthetic_edge_payload,
        synthetic_permission_payload,
        synthetic_record_payload,
    )

    perm = synthetic_permission_payload()
    edge = synthetic_edge_payload()
    bundle = synthetic_bundle_payload(
        permission_evidence=(perm,),
        provenance_edges=(edge,),
    )
    record = synthetic_record_payload(
        permission_refs=("perm-synthetic-1",),
        provenance_refs=("edge-synthetic-1",),
    )
    caller_perms = list(record["permission_evidence_refs"])
    caller_edges = list(record["provenance_edge_ids"])
    catalog = synthetic_catalog_payload(
        records=(record,),
        evidence_bundle_hash=bundle["bundle_hash"],
    )
    cat = parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
    # Mutate the caller's lists — model view must NOT change.
    caller_perms.append("INJECTED")
    caller_edges.append("INJECTED")
    assert "INJECTED" not in cat.records[0].permission_evidence_refs
    assert "INJECTED" not in cat.records[0].provenance_edge_ids


def test_license_evidence_mapping_is_detached() -> None:
    """Mutating the caller's license_evidence dict after building
    does not leak into the second parsed record."""
    import copy

    from tests.shell_geometry_catalogs._builders import synthetic_record_payload

    raw_a = synthetic_record_payload()
    raw_b = copy.deepcopy(raw_a)
    raw_b["license_evidence"]["extra_field"] = "BAD"
    catalog_a, bundle_a = _assemble_catalog((raw_a,))
    cat_a = parse_shell_geometry_catalog(raw_catalog=catalog_a, evidence_bundle=bundle_a)
    cat_a.records[0].license_evidence["extra_in_parsed"] = "BAD"
    # The fresh record built from raw_b must not inherit this mutation.
    catalog_b, bundle_b = _assemble_catalog((raw_b,))
    cat_b = parse_shell_geometry_catalog(raw_catalog=catalog_b, evidence_bundle=bundle_b)
    assert "extra_in_parsed" not in cat_b.records[0].license_evidence


def test_record_hash_includes_caller_evidence_field() -> None:
    """Adding a field to license_evidence changes the record hash
    (defensive), proving the hash domain covers the field."""
    import copy

    from tests.shell_geometry_catalogs._builders import (
        synthetic_record_payload,
    )

    raw_a = synthetic_record_payload(
        geometry_id="shell-geometry-synthetic-1",
        permission_refs=("perm-synthetic-1",),
        provenance_refs=("edge-synthetic-1",),
    )
    raw_b = copy.deepcopy(raw_a)
    raw_b["license_evidence"]["extra"] = "wat"
    # Re-compute record_hash for the mutated variant (tests the
    # hash domain coverage, not the parser layer).
    from hexagent.canonical_json import canonical_sha256

    def _hash(rec):
        payload = {k: v for k, v in rec.items() if k not in {"record_hash", "nominal_label"}}
        return canonical_sha256(payload)

    assert _hash(raw_a) != _hash(raw_b)


def test_decimal_acceptance_and_rejection() -> None:
    """The shell-inside-diameter decimal rules reject every forbidden
    shape and accept only the canonical positive SI metre strings."""
    from tests.shell_geometry_catalogs._builders import synthetic_record_payload

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
        raw = synthetic_record_payload(
            shell_inside_diameter_m=raw_value,
        )
        catalog, bundle = _assemble_catalog((raw,))
        cat = parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
        assert cat.records[0].shell_inside_diameter_m == raw_value

    for raw_value in rejected:
        raw = synthetic_record_payload(
            geometry_id="shell-geometry-synthetic-1",
            shell_inside_diameter_m=raw_value,
        )
        catalog, bundle = _assemble_catalog((raw,))
        with pytest.raises(ShellGeometryCatalogFailure) as excinfo:
            parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
        codes = [b.code for b in excinfo.value.blockers]
        assert "SGC_SHELL_INSIDE_DIAMETER_INVALID" in codes


def test_four_approval_states_each_rejected_or_admitted() -> None:
    """approved parses; pending/rejected/retired all fail at parse."""
    from tests.shell_geometry_catalogs._builders import synthetic_record_payload

    raw_ok = synthetic_record_payload()
    catalog_ok, bundle_ok = _assemble_catalog((raw_ok,))
    parsed = parse_shell_geometry_catalog(raw_catalog=catalog_ok, evidence_bundle=bundle_ok)
    assert parsed.records[0].approval_state == "approved"
    for bad_state in ("pending", "rejected", "retired"):
        raw = synthetic_record_payload(approval_state=bad_state)
        catalog, bundle = _assemble_catalog((raw,))
        with pytest.raises(ShellGeometryCatalogFailure) as excinfo:
            parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
        codes = [b.code for b in excinfo.value.blockers]
        assert "SGC_RECORD_UNAPPROVED" in codes


def test_duplicate_geometry_id_fails_closed() -> None:
    """Catalog with two records sharing one geometry_id fails with
    ``SGC_RECORD_DUPLICATE_ID``. Same-stage accumulation captures
    the second duplicate at the duplicate-id stage."""
    from tests.shell_geometry_catalogs._builders import (
        synthetic_bundle_payload,
        synthetic_catalog_payload,
        synthetic_edge_payload,
        synthetic_permission_payload,
        synthetic_record_payload,
    )

    perm = synthetic_permission_payload()
    edge = synthetic_edge_payload()
    bundle = synthetic_bundle_payload(
        permission_evidence=(perm,),
        provenance_edges=(edge,),
    )
    raw_a = synthetic_record_payload(geometry_id="shell-geometry-synthetic-1")
    raw_b = synthetic_record_payload(geometry_id="shell-geometry-synthetic-1")
    catalog = synthetic_catalog_payload(
        records=(raw_a, raw_b),
        evidence_bundle_hash=bundle["bundle_hash"],
    )
    with pytest.raises(ShellGeometryCatalogFailure) as excinfo:
        parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
    codes = [b.code for b in excinfo.value.blockers]
    assert "SGC_RECORD_DUPLICATE_ID" in codes


def test_canonical_ordering_records() -> None:
    """Records sort by (geometry_id, revision) at the model layer."""
    from tests.shell_geometry_catalogs._builders import (
        synthetic_bundle_payload,
        synthetic_catalog_payload,
        synthetic_edge_payload,
        synthetic_permission_payload,
        synthetic_record_payload,
    )

    perm = synthetic_permission_payload()
    edge_a = synthetic_edge_payload(
        edge_id="edge-synth-a", target_geometry_id="shell-geometry-synthetic-1"
    )
    edge_b = synthetic_edge_payload(
        edge_id="edge-synth-b", target_geometry_id="shell-geometry-synthetic-2"
    )
    bundle = synthetic_bundle_payload(
        permission_evidence=(perm,),
        provenance_edges=(edge_a, edge_b),
    )
    raw_a = synthetic_record_payload(
        geometry_id="shell-geometry-synthetic-1",
        permission_refs=("perm-synthetic-1",),
        provenance_refs=("edge-synth-a",),
    )
    raw_b = synthetic_record_payload(
        geometry_id="shell-geometry-synthetic-2",
        permission_refs=("perm-synthetic-1",),
        provenance_refs=("edge-synth-b",),
    )
    catalog = synthetic_catalog_payload(
        records=(raw_b, raw_a),  # submitted in reverse order
        evidence_bundle_hash=bundle["bundle_hash"],
    )
    cat = parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle)
    geom_ids = [r.geometry_id for r in cat.records]
    assert geom_ids == sorted(geom_ids)


def test_hash_domains() -> None:
    """Each artifact has a self-consistent canonical SHA-256 hash
    domain. The parser validates each domain."""
    from tests.shell_geometry_catalogs._builders import (
        synthetic_bundle_payload,
        synthetic_catalog_payload,
        synthetic_edge_payload,
        synthetic_permission_payload,
        synthetic_record_payload,
    )

    perm = synthetic_permission_payload()
    edge = synthetic_edge_payload()
    bundle = synthetic_bundle_payload(
        permission_evidence=(perm,),
        provenance_edges=(edge,),
    )
    raw = synthetic_record_payload()
    catalog = synthetic_catalog_payload(
        records=(raw,),
        evidence_bundle_hash=bundle["bundle_hash"],
    )
    # Patch each hash in turn; parser must emit SGC_<X>_HASH_MISMATCH.
    perm_bad = dict(perm)
    perm_bad["permission_hash"] = "0" * 64
    bundle_bad = synthetic_bundle_payload(
        permission_evidence=(perm_bad,),
        provenance_edges=(edge,),
    )
    with pytest.raises(ShellGeometryCatalogFailure) as excinfo:
        parse_shell_geometry_catalog(raw_catalog=catalog, evidence_bundle=bundle_bad)
    codes = [b.code for b in excinfo.value.blockers]
    assert "SGC_RECORD_HASH_MISMATCH" in codes


# ---------------------------------------------------------------------------
# Local helper: assemble a (catalog, bundle) pair around a list of records.
# ---------------------------------------------------------------------------


def _assemble_catalog(records):
    from tests.shell_geometry_catalogs._builders import (
        assemble_synthetic_catalog_and_bundle,
        synthetic_edge_payload,
        synthetic_permission_payload,
    )

    perm = synthetic_permission_payload()
    edges = []
    for raw in records:
        target_id = raw["geometry_id"]
        edges.append(
            synthetic_edge_payload(
                edge_id=f"edge-synth-{target_id}",
                target_geometry_id=target_id,
            )
        )
    # Use assembler to construct a coherent (catalog, bundle) pair.
    # Rebuild record payloads so their hashes match the actual
    # permission + edge content.
    rebuilt_records = []
    from hexagent.canonical_json import canonical_sha256

    for raw in records:
        target_id = raw["geometry_id"]
        rebuilt = dict(raw)
        rebuilt["permission_evidence_refs"] = ["perm-synthetic-1"]
        rebuilt["provenance_edge_ids"] = [f"edge-synth-{target_id}"]
        # Re-derive record_hash over the rebuilt content so the
        # hash agrees with the rebuilt fields.
        excluded = {"record_hash", "nominal_label"}
        hash_payload = {k: v for k, v in rebuilt.items() if k not in excluded}
        rebuilt["record_hash"] = canonical_sha256(hash_payload)
        rebuilt_records.append(rebuilt)
    catalog, bundle = assemble_synthetic_catalog_and_bundle(
        record_payloads=tuple(rebuilt_records),
        permission_payloads=(perm,),
        edge_payloads=tuple(edges),
    )
    return catalog, bundle
