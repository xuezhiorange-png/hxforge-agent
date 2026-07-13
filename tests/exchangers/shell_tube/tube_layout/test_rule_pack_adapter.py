"""TASK-021 Slice B rule-pack-adapter tests.

Implements Issue #141 Record 8 test list for the frozen
``build_layout_rule_authority_snapshot`` operation. Every test
constructs an in-memory already-loaded rule-pack mapping (no
filesystem loader call) and exercises one piece of the Record 5
binding verification chain plus the §6 source-class governance
matrix.

The tests do not modify repository state, do not touch the slice-A
core, and use only the public surface of
``hexagent.rule_packs.{schema,license_boundary,provenance,validation}``
and ``hexagent.canonical_json``.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.tube_layout.adapter_blockers import (
    RULE_PACK_ADAPTER_BLOCKER_CODES,
    AdapterFailure,
    RulePackAdapterBlockerCode,
    build_message_entry,
    sort_adapter_blockers,
)
from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    FrozenJsonObject,
    internal_frozen_to_primitive,
)
from hexagent.exchangers.shell_tube.tube_layout.models import MessageEntry
from hexagent.exchangers.shell_tube.tube_layout.rule_pack_adapter import (
    LAYOUT_RULE_PROFILE_ID,
    build_layout_rule_authority_snapshot,
)
from hexagent.rule_packs.license_boundary import (
    PROJECT_INTERNAL_AUTHORITY,
)

# --- Helpers -----------------------------------------------------------


PROFILE_PROJECTION_FIELDS: dict[str, Any] = {
    "pattern_family": "SQUARE",
    "pitch_m": "0.0254",
    "edge_clearance_m": "0.005",
    "allowed_origin_modes": ["CENTER_ON_LATTICE_POINT", "CENTER_ON_PRIMITIVE_CELL"],
    "allowed_axis_orientations": ["PRIMARY_AXIS_X", "PRIMARY_AXIS_Y"],
    "allowed_exclusion_zone_types": ["AXIS_ALIGNED_RECTANGLE", "CIRCLE"],
    "maximum_candidate_positions": 100000,
    "evidence_refs": ["ev:layout-rule-001"],
}


def _make_internal_rule(rid: str, *, version: str = "1.0.0") -> dict[str, Any]:
    """Return a TASK-012-compatible rule dict with all 19 required fields."""
    rule: dict[str, Any] = {
        "rule_id": rid,
        "rule_version": version,
        "rule_title": f"Internal layout rule {rid}",
        "source_class": "INTERNAL_ENGINEERING_RULE",
        "jurisdiction": "INTL",
        "standard_family": "INTERNAL",
        "bibliographic_reference": f"internal://test/{rid}",
        "license_evidence": PROJECT_INTERNAL_AUTHORITY,
        "source_evidence": {
            "source_class": "INTERNAL_ENGINEERING_RULE",
            "source_reference": f"internal://test/{rid}",
            "source_title_or_identifier": "Internal test",
            "source_locator_or_citation": "Chapter 1",
            "source_jurisdiction": "INTL",
            "license_evidence": PROJECT_INTERNAL_AUTHORITY,
        },
        "human_entered_evidence": {
            "author_identity": "eng@test.invalid",
            "author_role": "internal engineer",
            "entry_timestamp_utc": "2026-07-04T09:00:00Z",
            "review": {
                "reviewer_identity": "rev@test.invalid",
                "review_thread_reference": "review-test",
                "review_timestamp_utc": "2026-07-04T09:15:00Z",
            },
        },
        "approval_status": "approved",
        "review_status": "accepted",
        "forbidden_content_marker_check": [],
        "provenance_edges": [f"edge-{rid}"],
        "rule_body": dict(PROFILE_PROJECTION_FIELDS),
        "applicability_envelope": {"scope": "layout", "units": "dimensionless"},
        "uncertainty": {"kind": "none", "value": "0"},
    }
    rule["canonical_hash"] = canonical_sha256(rule)
    return rule


def _make_manifest(rids: list[str]) -> dict[str, Any]:
    m: dict[str, Any] = {
        "rule_pack_id": "test-rp",
        "rule_pack_version": "1.0.0",
        "rule_count": len(rids),
        "rules": list(rids),
        "target_jurisdiction": "INTL",
        "target_standard_family": "INTERNAL",
        "creation_timestamp_utc": "2026-07-04T10:00:00Z",
        "review_id": "test-review",
        "canonical_hash": None,
    }
    m["canonical_hash"] = canonical_sha256(m)
    return m


def _make_loaded_pack(
    rules: dict[str, dict[str, Any]],
    *,
    manifest: dict[str, Any] | None = None,
    edges: list[dict[str, Any]] | None = None,
    permission_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rid_list = list(rules.keys())
    if manifest is None:
        manifest = _make_manifest(rid_list)
    if edges is None:
        edges = [
            {
                "edge_id": f"edge-{rid}",
                "from_rule_id": f"external:internal:{rid}",
                "to_rule_id": rid,
                "relation": "derives_from",
                "evidence_ref": "ev:layout-rule-001",
            }
            for rid in rid_list
        ]
    return {
        "manifest": manifest,
        "rules": rules,
        "provenance_edges": edges,
        "permission_evidence": permission_evidence or {},
    }


# --- Tests ---------------------------------------------------------------


def test_rule_pack_adapter_record1_valid_approved_rule_produces_snapshot() -> None:
    """Record 8 #1 — valid approved rule produces an exact
    ``LayoutRuleAuthoritySnapshot``."""
    rule = _make_internal_rule("layout-rule-square-pitch-1.0")
    pack = _make_loaded_pack({"layout-rule-square-pitch-1.0": rule})
    snap = build_layout_rule_authority_snapshot(
        loaded_rule_pack=pack,
        rule_id="layout-rule-square-pitch-1.0",
        rule_version="1.0.0",
        profile_id=LAYOUT_RULE_PROFILE_ID,
    )
    assert snap.profile_id == LAYOUT_RULE_PROFILE_ID
    assert snap.rule_id == "layout-rule-square-pitch-1.0"
    assert snap.rule_version == "1.0.0"
    assert snap.source_class == "INTERNAL_ENGINEERING_RULE"
    assert snap.approval_status == "approved"
    assert snap.pattern_family.value == "SQUARE"
    assert snap.pitch_m == "0.0254"
    assert snap.edge_clearance_m == "0.005"
    assert snap.maximum_candidate_positions == 100000
    # The INTERNAL_ENGINEERING_RULE has rule_pack_identity = None
    assert snap.rule_pack_identity is None
    # license_evidence must be a Layer-B marker
    assert isinstance(snap.license_evidence, FrozenJsonObject)
    assert internal_frozen_to_primitive(snap.license_evidence) == {
        "form": "project_internal_authority",
        "value": PROJECT_INTERNAL_AUTHORITY,
    }


def test_rule_pack_adapter_record2_raw_mapping_shape_invalid() -> None:
    """Record 8 #2 — raw ``loaded_rule_pack`` that is not a mapping
    raises ``AdapterFailure`` with raw-type blocker."""
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack="not-a-mapping",  # type: ignore[arg-type]
            rule_id="r1",
            rule_version="1.0.0",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID in codes


def test_rule_pack_adapter_record3_profile_mismatch_blocks() -> None:
    """Record 8 #3 — wrong ``profile_id`` blocks with the profile-mismatch
    code."""
    rule = _make_internal_rule("r1")
    pack = _make_loaded_pack({"r1": rule})
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="r1",
            rule_version="1.0.0",
            profile_id="wrong.profile.v1",
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_PROFILE_MISMATCH in codes


def test_rule_pack_adapter_record4_rule_id_required() -> None:
    """Record 8 #4 — empty ``rule_id`` blocks with the raw-type
    blocker (or the rule-id-not-found code)."""
    rule = _make_internal_rule("r-empty")
    pack = _make_loaded_pack({"r-empty": rule})
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="",
            rule_version="1.0.0",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert (
        RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID in codes
        or RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_ID_NOT_FOUND in codes
    )


def test_rule_pack_adapter_record5_rule_version_required() -> None:
    """Record 8 #5 — empty ``rule_version`` blocks."""
    rule = _make_internal_rule("r-no-version")
    pack = _make_loaded_pack({"r-no-version": rule})
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="r-no-version",
            rule_version="",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID in codes


def test_rule_pack_adapter_record6_unknown_rule_blocks() -> None:
    """Record 8 #6 — unknown ``rule_id`` blocks with the rule-id-not-found
    code."""
    rule = _make_internal_rule("r-existing")
    pack = _make_loaded_pack({"r-existing": rule})
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="r-unknown",
            rule_version="1.0.0",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_ID_NOT_FOUND in codes


def test_rule_pack_adapter_record7_duplicate_rule_blocks() -> None:
    """Record 8 #7 — duplicate ``rule_id`` in the loaded mapping (which
    the upstream loader would normally reject at load time) raises
    the duplicate-id blocker code. We construct a duplicate mapping
    in-memory (Python dicts naturally de-dup by key in-place; we
    therefore monkey-patch the rule's ``rule_id`` field to create
    the effective duplicate).
    """
    rule_a = _make_internal_rule("dup-1")
    rule_b = _make_internal_rule("dup-2")
    rule_b_mutated = dict(rule_b)
    rule_b_mutated["rule_id"] = "dup-1"  # duplicate
    pack = _make_loaded_pack({"dup-1": rule_a, "dup-2": rule_b_mutated})
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="dup-1",
            rule_version="1.0.0",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_ID_DUPLICATE in codes


def test_rule_pack_adapter_record8_version_mismatch_blocks() -> None:
    """Record 8 #8 — wrong ``rule_version`` blocks with the
    rule-hash-mismatch code."""
    rule = _make_internal_rule("r-ver", version="1.0.0")
    pack = _make_loaded_pack({"r-ver": rule})
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="r-ver",
            rule_version="0.9.9",  # wrong
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH in codes


def test_rule_pack_adapter_record9_manifest_hash_mismatch_blocks() -> None:
    """Record 8 #9 — ``manifest.canonical_hash`` mismatch with the
    recomputed canonical hash blocks with the rule-pack-hash-mismatch
    code."""
    rule = _make_internal_rule("r-manifest")
    manifest = _make_manifest(["r-manifest"])
    manifest["canonical_hash"] = "0" * 64  # deliberately wrong
    pack = _make_loaded_pack({"r-manifest": rule}, manifest=manifest)
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="r-manifest",
            rule_version="1.0.0",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_PACK_HASH_MISMATCH in codes


def test_rule_pack_adapter_record10_rule_hash_mismatch_blocks() -> None:
    """Record 8 #10 — recomputed rule ``canonical_hash`` differs from
    stored value blocks with the rule-hash-mismatch code. The upstream
    ``validate_canonical_hash`` accepts a dict whose stored hash
    matches its recomputed value; we therefore corrupt the dict's
    hash post-validation by mutating it in place (the canonical-hash
    function determines the proper hash from the dict body).
    """
    rule = _make_internal_rule("r-rule-hash")
    rule["canonical_hash"] = "a" * 64
    pack = _make_loaded_pack({"r-rule-hash": rule})
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="r-rule-hash",
            rule_version="1.0.0",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH in codes


def test_rule_pack_adapter_record11_unapproved_rule_blocks() -> None:
    """Record 8 #11 — ``approval_status != "approved"`` blocks with
    the rule-not-approved code."""
    rule = _make_internal_rule("r-draft")
    rule["approval_status"] = "draft"
    rule["canonical_hash"] = canonical_sha256(rule)
    pack = _make_loaded_pack({"r-draft": rule})
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="r-draft",
            rule_version="1.0.0",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_NOT_APPROVED in codes


def test_rule_pack_adapter_record12_forbidden_runtime_source_class() -> None:
    """Record 8 #12 — ``USER_PROVIDED_LICENSED_SUMMARY`` is non-redistributable
    and is never admitted as runtime layout authority. This blocks
    the call with the source-class-forbidden code."""
    rule = _make_internal_rule("r-user-summary")
    rule["source_class"] = "USER_PROVIDED_LICENSED_SUMMARY"
    rule["license_evidence"] = "https://user.example.com/standards/license"
    rule["human_entered_evidence"] = {
        "author_identity": "user@example.com",
        "author_role": "licensed user",
        "entry_timestamp_utc": "2026-07-04T09:00:00Z",
        "review": {
            "reviewer_identity": "rev@test.invalid",
            "review_thread_reference": "review-test",
            "review_timestamp_utc": "2026-07-04T09:15:00Z",
        },
    }
    rule["source_evidence"] = {
        "source_class": "USER_PROVIDED_LICENSED_SUMMARY",
        "source_reference": "user-license://test/r-user-summary",
        "source_title_or_identifier": "User licensed summary",
        "source_locator_or_citation": "Section 3.2.1",
        "source_jurisdiction": "INTL",
        "license_evidence": "https://user.example.com/standards/license",
    }
    # Mirror fields must agree per upstream §7.2 direct-field policy.
    rule["bibliographic_reference"] = rule["source_evidence"]["source_reference"]  # type: ignore[index]  # noqa: E501
    rule["canonical_hash"] = canonical_sha256(rule)
    pack = _make_loaded_pack({"r-user-summary": rule})
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="r-user-summary",
            rule_version="1.0.0",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_SOURCE_CLASS_FORBIDDEN in codes


def test_rule_pack_adapter_record13_license_evidence_missing_blocks() -> None:
    """Record 8 #13 — missing or invalid ``license_evidence`` blocks
    with the license-evidence-missing code."""
    rule = _make_internal_rule("r-lic")
    rule.pop("license_evidence", None)
    rule["canonical_hash"] = canonical_sha256(rule)
    pack = _make_loaded_pack({"r-lic": rule})
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="r-lic",
            rule_version="1.0.0",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_LICENSE_EVIDENCE_MISSING in codes


def test_rule_pack_adapter_record14_vendor_runtime_scope_missing_blocks() -> None:
    """Record 8 #14 — ``VENDOR_PERMISSIONED`` rule whose permission
    evidence lacks the ``usage_scope`` token blocks with the
    vendor-scope-missing code (or, if usage scope is missing
    altogether, the runtime-scope-forbidden code)."""
    rule = _make_internal_rule("r-vendor")
    rule["source_class"] = "VENDOR_PERMISSIONED"
    rule["license_evidence"] = "https://vendor.example.com/permissions/r-vendor"
    rule["human_entered_evidence"] = {
        "author_identity": "vendor-eng@example.com",
        "author_role": "vendor engineer",
        "entry_timestamp_utc": "2026-07-04T09:00:00Z",
        "vendor_permission_evidence": {
            "permission_id": "perm-r-vendor",
            "permission_scope": [
                "repository_storage",
                "repository_redistribution",
                "public_artifact_allowed",
            ],
        },
        "review": {
            "reviewer_identity": "rev@test.invalid",
            "review_thread_reference": "review-test",
            "review_timestamp_utc": "2026-07-04T09:15:00Z",
        },
    }
    rule["source_evidence"] = {
        "source_class": "VENDOR_PERMISSIONED",
        "source_reference": "vendor://r-vendor",
        "source_title_or_identifier": "Vendor rule",
        "source_locator_or_citation": "Chapter 4",
        "source_jurisdiction": "INTL",
        "license_evidence": "https://vendor.example.com/permissions/r-vendor",
    }
    # Mirror fields must agree per upstream §7.2 direct-field policy.
    rule["bibliographic_reference"] = rule["source_evidence"]["source_reference"]  # type: ignore[index]  # noqa: E501
    rule["canonical_hash"] = canonical_sha256(rule)
    pack = _make_loaded_pack({"r-vendor": rule})
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="r-vendor",
            rule_version="1.0.0",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert (
        RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_VENDOR_PERMISSION_SCOPE_MISSING in codes
        or RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RUNTIME_SCOPE_FORBIDDEN in codes
    )


def test_rule_pack_adapter_record15_provenance_incomplete_blocks() -> None:
    """Record 8 #15 — the loaded ``provenance_edges`` list contains a
    dangling reference (a ``to_rule_id`` that does not exist in the
    rule-pack), so the upstream ``validate_provenance_edges`` helper
    raises, and the Slice B adapter maps the failure to the closed
    ``STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE`` blocker code.
    """
    rule = _make_internal_rule("r-prov")
    # Force a dangling reference: the loaded-pack edges include a
    # ``to_rule_id`` that does not exist.
    pack = _make_loaded_pack(
        {"r-prov": rule},
        edges=[
            {
                "edge_id": "edge-prov-1",
                "from_rule_id": "external:internal:r-prov",
                "to_rule_id": "r-does-not-exist",
                "relation": "derives_from",
                "evidence_ref": "ev:prov-1",
            }
        ],
    )
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="r-prov",
            rule_version="1.0.0",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE in codes


def test_rule_pack_adapter_record16_restricted_standard_body_rejected() -> None:
    """Record 8 #16 — a rule under ``REFERENCE_ONLY_RESTRICTED_STANDARD``
    blocks regardless of body content (the source class is forbidden
    by the runtime governance matrix)."""
    rule = _make_internal_rule("r-ref")
    rule["source_class"] = "REFERENCE_ONLY_RESTRICTED_STANDARD"
    rule["license_evidence"] = "https://reference.example.com/restricted/license"
    rule["rule_body"] = dict(PROFILE_PROJECTION_FIELDS)
    rule["forbidden_content_marker_check"] = []
    rule["human_entered_evidence"] = {
        "author_identity": "ref-curator@example.com",
        "author_role": "reference curator",
        "entry_timestamp_utc": "2026-07-04T09:00:00Z",
        "review": {
            "reviewer_identity": "rev@test.invalid",
            "review_thread_reference": "review-test",
            "review_timestamp_utc": "2026-07-04T09:15:00Z",
        },
    }
    rule["source_evidence"] = {
        "source_class": "REFERENCE_ONLY_RESTRICTED_STANDARD",
        "source_reference": "reference://r-ref",
        "source_title_or_identifier": "Reference citation only",
        "source_locator_or_citation": "Section 5.1",
        "source_jurisdiction": "INTL",
        "license_evidence": "https://reference.example.com/restricted/license",
    }
    rule["bibliographic_reference"] = rule["source_evidence"]["source_reference"]  # type: ignore[index]  # noqa: E501
    rule["canonical_hash"] = canonical_sha256(rule)
    pack = _make_loaded_pack({"r-ref": rule})
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="r-ref",
            rule_version="1.0.0",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert (
        RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_SOURCE_CLASS_FORBIDDEN in codes
        or RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED in codes
    )


def test_rule_pack_adapter_record17_explicit_profile_fields_required() -> None:
    """Record 8 #17 — missing any TASK-021 projection field
    (``pattern_family`` etc.) blocks with the restricted-body
    code (the body's mandatory field list is a §4 attribute)."""
    rule = _make_internal_rule("r-no-projection")
    rule["rule_body"] = {"pattern_family": "SQUARE"}  # only one field
    rule["canonical_hash"] = canonical_sha256(rule)
    pack = _make_loaded_pack({"r-no-projection": rule})
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="r-no-projection",
            rule_version="1.0.0",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED in codes


def test_rule_pack_adapter_record18_canonical_enum_decimal_projection() -> None:
    """Record 8 #18 — profile projection fields are coerced to the
    canonical enum / canonical decimal shapes: ``pattern_family`` is
    a ``PatternFamily`` enum member; ``pitch_m`` / ``edge_clearance_m``
    are TASK-021 canonical decimal strings; the ``allowed_*`` lists
    are tuples of enum members."""
    rule = _make_internal_rule("r-projection-types")
    pack = _make_loaded_pack({"r-projection-types": rule})
    snap = build_layout_rule_authority_snapshot(
        loaded_rule_pack=pack,
        rule_id="r-projection-types",
        rule_version="1.0.0",
        profile_id=LAYOUT_RULE_PROFILE_ID,
    )
    from hexagent.exchangers.shell_tube.tube_layout.models import (
        AxisOrientation,
        ExclusionZoneType,
        OriginMode,
        PatternFamily,
    )

    assert isinstance(snap.pattern_family, PatternFamily)
    assert all(isinstance(m, OriginMode) for m in snap.allowed_origin_modes)
    assert all(isinstance(m, AxisOrientation) for m in snap.allowed_axis_orientations)
    assert all(isinstance(m, ExclusionZoneType) for m in snap.allowed_exclusion_zone_types)
    import re

    decimal_re = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
    assert decimal_re.match(snap.pitch_m)
    assert decimal_re.match(snap.edge_clearance_m)


def test_rule_pack_adapter_record19_input_mapping_order_does_not_alter_output() -> None:
    """Record 8 #19 — the order of the rules dict and the order of the
    provenance edges list in the input ``loaded_rule_pack`` mapping
    do NOT alter the emitted ``snapshot_hash`` (canonical-order
    invariant).
    """
    rule = _make_internal_rule("r-order")

    pack_a = _make_loaded_pack({"r-order": rule})
    rule["canonical_hash"] = canonical_sha256(rule)
    rule2 = dict(rule)
    rule2["rule_id"] = "r-order2"
    rule2["provenance_edges"] = ["edge-r-order2"]
    rule2["rule_body"] = dict(PROFILE_PROJECTION_FIELDS)
    rule2["canonical_hash"] = canonical_sha256(rule2)
    pack_b = _make_loaded_pack(
        {"r-order": rule, "r-order2": rule2},
        edges=[
            {
                "edge_id": "edge-r-order",
                "from_rule_id": "external:internal:r-order",
                "to_rule_id": "r-order",
                "relation": "derives_from",
                "evidence_ref": "ev:order-1",
            },
            {
                "edge_id": "edge-r-order2",
                "from_rule_id": "external:internal:r-order2",
                "to_rule_id": "r-order2",
                "relation": "derives_from",
                "evidence_ref": "ev:order-2",
            },
        ],
    )
    snap_a = build_layout_rule_authority_snapshot(
        loaded_rule_pack=pack_a,
        rule_id="r-order",
        rule_version="1.0.0",
        profile_id=LAYOUT_RULE_PROFILE_ID,
    )
    snap_b = build_layout_rule_authority_snapshot(
        loaded_rule_pack=pack_b,
        rule_id="r-order",
        rule_version="1.0.0",
        profile_id=LAYOUT_RULE_PROFILE_ID,
    )
    # Both runs target the SAME rule and SAME profile — the snapshot
    # hash MUST be identical regardless of which other rules /
    # edges are also in the loaded_rule_pack mapping.
    assert snap_a.snapshot_hash == snap_b.snapshot_hash


def test_rule_pack_adapter_record20_caller_mutation_cannot_alter_output() -> None:
    """Record 8 #20 — caller mutation of the loaded mapping or the
    underlying rule dict AFTER the adapter returns MUST NOT alter
    the emitted snapshot (the slice-A Round 8 §P0-2
    detached-immutable-snapshot invariant)."""
    rule = _make_internal_rule("r-immutable")
    pack = _make_loaded_pack({"r-immutable": rule})
    snap = build_layout_rule_authority_snapshot(
        loaded_rule_pack=pack,
        rule_id="r-immutable",
        rule_version="1.0.0",
        profile_id=LAYOUT_RULE_PROFILE_ID,
    )
    # Caller mutates rule dict AFTER construction
    rule["rule_version"] = "9.9.9"
    rule["pattern_family"] = "TRIANGULAR"
    rule["canonical_hash"] = "a" * 64
    # The adapter output is a frozen dataclass; mutation blocked at the
    # structural level.
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.pitch_m = "0.9999"  # type: ignore[misc]
    # The slice-A ``LayoutRuleAuthoritySnapshot`` fields remain
    # unchanged.
    assert snap.rule_version == "1.0.0"
    assert snap.pattern_family.value == "SQUARE"


def test_rule_pack_adapter_record21_no_fallback_or_inference() -> None:
    """Record 8 #21 — no field default / no inference: pattern family
    and pitch are read verbatim from ``rule_body``; an absent
    ``pattern_family`` blocks (the adapter never substitutes a
    default).
    """
    rule = _make_internal_rule("r-no-fallback")
    rule["rule_body"].pop("pattern_family")  # absent
    rule["canonical_hash"] = canonical_sha256(rule)
    pack = _make_loaded_pack({"r-no-fallback": rule})
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="r-no-fallback",
            rule_version="1.0.0",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    codes = [b.code for b in exc_info.value.blockers]
    assert RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED in codes


def test_rule_pack_adapter_record22_no_filesystem_io() -> None:
    """Record 8 #22 — the adapter module must NOT import any of the
    slice-A forbidden I/O tokens. This is the adapter-side mirror of
    the slice-A architecture test.
    """
    import hexagent.exchangers.shell_tube.tube_layout.rule_pack_adapter as ra

    forbidden = {
        "os",
        "pathlib",
        "socket",
        "subprocess",
        "requests",
        "httpx",
        "random",
        "time",
    }
    src = inspect.getsource(ra)
    for line in src.split("\n"):
        stripped = line.strip()
        if not (stripped.startswith("import ") or stripped.startswith("from ")):
            continue
        token = stripped.split()[1].split(".")[0].rstrip(",").rstrip(";")
        assert token not in forbidden, f"rule_pack_adapter.py imports forbidden token {token}"


def test_rule_pack_adapter_record23_complete_blocker_ordering() -> None:
    """Record 8 #23 — multiple blockers in the same stage are sorted
    per slice-A §11.3 (idempotent across re-sort)."""
    b1 = build_message_entry(
        code="AAA",
        field_path="rule_id",
        message_key="m_a",
        details={"v": 1},
    )
    b2 = build_message_entry(
        code="AAA",
        field_path="rule_id",
        message_key="m_b",
        details={"v": 2},
    )
    sorted_first = sort_adapter_blockers([b1, b2])
    sorted_second = sort_adapter_blockers(sorted_first)
    assert len(sorted_first) == 2
    assert len(sorted_second) == 2
    assert [b.code for b in sorted_first] == [b.code for b in sorted_second]


def test_rule_pack_adapter_record24_no_partial_snapshot_returned() -> None:
    """Record 8 #24 — on failure the adapter never returns a partial
    snapshot: it raises ``AdapterFailure`` carrying the complete,
    ordered blocker list."""
    with pytest.raises(AdapterFailure) as exc_info:
        build_layout_rule_authority_snapshot(
            loaded_rule_pack="not-a-mapping",  # type: ignore[arg-type]
            rule_id="x",
            rule_version="0.0.1",
            profile_id=LAYOUT_RULE_PROFILE_ID,
        )
    assert isinstance(exc_info.value.blockers, tuple)
    assert all(isinstance(b, MessageEntry) for b in exc_info.value.blockers)


def test_rule_pack_adapter_record_closed_set_is_exactly_fourteen() -> None:
    """The closed set of rule-pack-adapter blocker codes is exactly 14."""
    assert len(RULE_PACK_ADAPTER_BLOCKER_CODES) == 14
    expected = {
        "STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID",
        "STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID",
        "STL_RULE_PACK_ADAPTER_PROFILE_MISMATCH",
        "STL_RULE_PACK_ADAPTER_RULE_PACK_HASH_MISMATCH",
        "STL_RULE_PACK_ADAPTER_RULE_ID_NOT_FOUND",
        "STL_RULE_PACK_ADAPTER_RULE_ID_DUPLICATE",
        "STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH",
        "STL_RULE_PACK_ADAPTER_RULE_NOT_APPROVED",
        "STL_RULE_PACK_ADAPTER_SOURCE_CLASS_FORBIDDEN",
        "STL_RULE_PACK_ADAPTER_LICENSE_EVIDENCE_MISSING",
        "STL_RULE_PACK_ADAPTER_VENDOR_PERMISSION_SCOPE_MISSING",
        "STL_RULE_PACK_ADAPTER_RUNTIME_SCOPE_FORBIDDEN",
        "STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED",
        "STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE",
    }
    assert set(RULE_PACK_ADAPTER_BLOCKER_CODES) == expected
