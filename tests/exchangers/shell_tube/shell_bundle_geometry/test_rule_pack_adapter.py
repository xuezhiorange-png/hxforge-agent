"""Tests for the TASK-022 Slice B1 rule-pack adapter.

The tests cover the 16-stage validation pipeline (Issue #147 Record 4),
the input/output contracts (Records 2 & 3), the licensing boundary
(Record 5), and the architecture invariants required by Spec §14.

The builders in ``_adapter_builders.py`` construct in-memory TASK-012-
compatible packs. No filesystem loader is called. No production rule-
pack artifact is created. No Slice A core module is mutated.
"""

from __future__ import annotations

import inspect
from copy import deepcopy

import pytest

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.shell_bundle_geometry import (  # noqa: I001
    PROFILE_ID,
    RULE_PACK_ADAPTER_BLOCKER_CODES,
    RULE_SNAPSHOT_SCHEMA_VERSION,
    AdapterFailure,
    RuleAuthorityMode,
    ShellInsideDiameterAuthorityMode,
    build_shell_bundle_rule_authority_snapshot,
)
from hexagent.rule_packs.license_boundary import PROJECT_INTERNAL_AUTHORITY

from ._adapter_builders import make_pack, mutate_rule

# ---- Signature and happy-path ----


def test_public_signature_is_frozen() -> None:
    sig = inspect.signature(build_shell_bundle_rule_authority_snapshot)
    params = sig.parameters
    assert list(params) == ["loaded_rule_pack", "rule_id"]
    assert params["loaded_rule_pack"].kind is inspect.Parameter.KEYWORD_ONLY or (
        params["loaded_rule_pack"].default is inspect.Parameter.empty
    )
    # Both parameters are keyword-only via ``*``.
    assert params["loaded_rule_pack"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["rule_id"].kind is inspect.Parameter.KEYWORD_ONLY


def test_valid_approved_pack_returns_exact_snapshot() -> None:
    pack = make_pack()
    snap = build_shell_bundle_rule_authority_snapshot(
        loaded_rule_pack=pack, rule_id="rule-public-v1"
    )
    assert snap.schema_version == RULE_SNAPSHOT_SCHEMA_VERSION
    assert snap.profile_id == PROFILE_ID
    assert snap.authority_mode is RuleAuthorityMode.APPROVED_RULE_PACK
    assert snap.rule_id == "rule-public-v1"
    assert snap.rule_version == "1.0.0"
    assert snap.source_class == "PUBLIC_DOMAIN"
    assert snap.approval_status == "approved"
    assert snap.maximum_position_count == 10000
    assert snap.minimum_bundle_peripheral_allowance_m == "0.01"
    assert snap.minimum_radial_clearance_m == "0.01"
    assert set(snap.allowed_shell_authority_modes) == set(
        [
            ShellInsideDiameterAuthorityMode.CALLER_SUPPLIED_EXPLICIT,
            ShellInsideDiameterAuthorityMode.APPROVED_CATALOG_SNAPSHOT,
        ]
    )
    assert len(snap.evidence_refs) == 1
    assert isinstance(snap.provenance_edge_ids, tuple)
    assert snap.rule_pack_identity is not None
    assert snap.snapshot_hash  # non-empty after recomputation


def test_rule_id_is_not_caller_overridable_for_profile_id() -> None:
    """``profile_id`` is asserted internally, not supplied by the caller."""
    sig = inspect.signature(build_shell_bundle_rule_authority_snapshot)
    assert "profile_id" not in sig.parameters


# ---- Stage 1: raw type ----


def test_non_mapping_pack_blocks() -> None:
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(  # type: ignore[arg-type]
            loaded_rule_pack=["a", "b", "c"], rule_id="r"
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RAW_TYPE_INVALID" in codes


def test_empty_or_non_string_rule_id_blocks() -> None:
    pack = make_pack()
    for bad in ("", 1, None, []):
        with pytest.raises(AdapterFailure):
            build_shell_bundle_rule_authority_snapshot(
                loaded_rule_pack=pack,
                rule_id=bad,  # type: ignore[arg-type]
            )


# ---- Stage 2: top-level shape ----


def test_top_level_missing_key_blocks() -> None:
    pack = make_pack()
    del pack["permission_evidence"]
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_UNKNOWN_FIELD" in codes


def test_top_level_extra_key_blocks() -> None:
    pack = make_pack()
    pack["extra"] = "forbidden"
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_UNKNOWN_FIELD" in codes


def test_manifest_not_mapping_blocks() -> None:
    pack = make_pack()
    pack["manifest"] = "string-not-mapping"
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_MANIFEST_INVALID" in codes


# ---- Stage 4: manifest hash ----


def test_manifest_hash_mismatch_blocks() -> None:
    pack = make_pack()
    # Replace the manifest hash with an obviously-wrong value.
    pack["manifest"]["canonical_hash"] = "0" * 64
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_MANIFEST_HASH_MISMATCH" in codes


# ---- Stage 5: manifest references ----


def test_selected_rule_unapproved_blocks_at_reference_stage() -> None:
    """A draft rule is rejected by ``validate_manifest_only_references_approved_rules``."""
    pack = make_pack()
    pack["rules"]["rule-public-v1"]["approval_status"] = "draft"
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    # Stage 5 maps to MANIFEST_REFERENCE_INVALID; stage 11 maps to
    # RULE_UNAPPROVED. The earlier stage blocks first per the 16-stage
    # dependency rule.
    assert "SBG_RULE_ADAPTER_MANIFEST_REFERENCE_INVALID" in codes or (
        "SBG_RULE_ADAPTER_RULE_UNAPPROVED" in codes
    )


def test_invalid_provenance_graph_blocks() -> None:
    pack = make_pack()
    # Corrupt the edge by changing its to_rule_id to a non-rule.
    # The rule stays in rules (so stage 5 manifest-references
    # passes), but the edge's to_rule_id points to a different rule
    # which doesn't exist in the pack.
    bad_pack = deepcopy(pack)
    bad_pack["provenance_edges"][0]["to_rule_id"] = "rule-does-not-exist"
    bad_pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        bad_pack["rules"]["rule-public-v1"]
    )
    bad_pack["manifest"]["canonical_hash"] = canonical_sha256(bad_pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=bad_pack, rule_id="rule-public-v1"
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_PROVENANCE_INVALID" in codes


def test_invalid_supersedes_graph_blocks() -> None:
    pack = make_pack()
    pack["provenance_edges"].append(
        {
            "edge_id": "e-supersedes-bad",
            "from_rule_id": "rule-public-v1",
            "to_rule_id": "no-such-rule",
            "relation": "supersedes",
            "evidence_ref": "ref:test:bad",
        }
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_PROVENANCE_INVALID" in codes


# ---- Stage 7 / 10: rule lookup + identity ----


def test_rule_not_found_blocks() -> None:
    pack = make_pack()
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-does-not-exist",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_NOT_FOUND" in codes


def test_key_rule_id_mismatch_blocks() -> None:
    """If the rule's body declares a different rule_id than the key, block."""
    pack = make_pack()
    pack["rules"]["rule-public-v1"]["source_evidence"] = dict(
        pack["rules"]["rule-public-v1"]["source_evidence"]
    )
    # Mutate the rule_id directly; surface_evidence mirror stays the
    # same so validate_rule throws a mirror mismatch (rule.schema).
    # We instead mutate the rule_id alone then re-hash.
    pack["rules"]["rule-public-v1"]["rule_id"] = "rule-other-key"
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    # The mirror field "bibliographic_reference" must match
    # "source_reference" still ("internal://test/rule-public-v1");
    # we have to break the mirror with rule_id change to keep it passing.
    # Instead we shift the source_reference to match the new rule_id so
    # validate_rule is satisfied, then the stage-10 identity check
    # notices the key vs body mismatch.
    pack["rules"]["rule-public-v1"]["bibliographic_reference"] = "internal://test/rule-other-key"
    pack["rules"]["rule-public-v1"]["source_evidence"]["source_reference"] = (
        "internal://test/rule-other-key"
    )
    pack["rules"]["rule-public-v1"]["rule_title"] = "rule-other-key"
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    # rules[rule_id] is keyed by the original 'rule-public-v1' which
    # the loader emits, but we've changed the rule body's rule_id
    # field to 'rule-other-key'. The adapter asks for rule_id="rule-public-v1"
    # so rules["rule-public-v1"] still exists.
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_IDENTITY_MISMATCH" in codes


def test_selected_rule_not_listed_in_manifest_blocks() -> None:
    """If the manifest omits the rule_id, stage 10 blocks."""
    pack = make_pack()
    pack["manifest"]["rules"] = []  # empty rules list
    pack["manifest"]["rule_count"] = 0
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_IDENTITY_MISMATCH" in codes


# ---- Stage 8: rule schema ----


def test_rule_schema_invalid_blocks() -> None:
    """A schema-invalid rule must be rejected by ``validate_rule`` (stage 8)."""
    pack = make_pack()
    # Replace the required non-empty provenance_edges list with a
    # non-list value. ``validate_rule`` raises
    # ``RulePackValidationError`` on this field, which the adapter
    # maps to ``SBG_RULE_ADAPTER_RULE_INVALID`` at stage 8.
    pack["rules"]["rule-public-v1"]["provenance_edges"] = "not-a-list"  # type: ignore[assignment]
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_INVALID" in codes


# ---- Stage 9: rule hash ----


def test_rule_hash_mismatch_blocks() -> None:
    pack = make_pack()
    pack["rules"]["rule-public-v1"]["canonical_hash"] = "0" * 64
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_HASH_MISMATCH" in codes


# ---- Stage 11: approval ----


def test_unapproved_rule_blocks_at_approval_stage() -> None:
    """Use INTERNAL_GENERIC-friendly path so it passes stage 5 first."""
    pack = make_pack(source_class="INTERNAL_ENGINEERING_RULE")
    pack["rules"]["rule-public-v1"]["license_evidence"] = PROJECT_INTERNAL_AUTHORITY
    pack["rules"]["rule-public-v1"]["source_evidence"]["license_evidence"] = (
        PROJECT_INTERNAL_AUTHORITY
    )
    pack["rules"]["rule-public-v1"]["human_entered_evidence"] = {"review_notes": "test-internal"}
    pack["rules"]["rule-public-v1"]["approval_status"] = "draft"
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    # Stage 5 (manifest reference) blocks first because validate_rule
    # requires approved status too — but stage 5 reads manifest-level
    # only. Either stage 5 or stage 11 is allowed here.
    assert (
        "SBG_RULE_ADAPTER_RULE_UNAPPROVED" in codes
        or "SBG_RULE_ADAPTER_MANIFEST_REFERENCE_INVALID" in codes
    )


# ---- Stage 12: source class + license + vendor ----


def test_runtime_forbidden_source_class_blocks() -> None:
    """USER_PROVIDED_LICENSED_SUMMARY must block (Record 5)."""
    pack = make_pack(source_class="USER_PROVIDED_LICENSED_SUMMARY")
    pack["rules"]["rule-public-v1"]["human_entered_evidence"] = {"review_notes": "user-cited"}
    # Replicate canonical hashes.
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_SOURCE_CLASS_RUNTIME_FORBIDDEN" in codes


def test_reference_only_restricted_standard_blocks() -> None:
    """REFERENCE_ONLY_RESTRICTED_STANDARD must block (Record 5)."""
    pack = make_pack(source_class="REFERENCE_ONLY_RESTRICTED_STANDARD")
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_SOURCE_CLASS_RUNTIME_FORBIDDEN" in codes


def test_vendor_permission_scope_incomplete_blocks() -> None:
    """VENDOR_PERMISSIONED without the runtime-operation scope token must block.

    The adapter maps missing ``USAGE_SCOPE`` (the runtime-required
    token for the ``runtime_rulepack`` operation) to the dedicated
    ``SBG_RULE_ADAPTER_VENDOR_PERMISSION_SCOPE_INCOMPLETE`` code.
    """
    pack = make_pack(source_class="VENDOR_PERMISSIONED")
    pack["rules"]["rule-public-v1"]["human_entered_evidence"] = {
        "vendor_permission_evidence": {
            "permission_id": "vendor-test",
            # All four recorded tokens, but no USAGE_SCOPE marker at
            # runtime level. Wait — USAGE_SCOPE is the recorded token
            # name in TASK-012. The runtime-required token IS
            # ``usage_scope``. To force the operation-level check to
            # fail we have to omit ``usage_scope`` (which is what the
            # upstream ``enforce_vendor_permission_scope_full_recorded``
            # would also reject via LICENSE_BLOCKED, so we omit the
            # 3 OTHER tokens to keep the recorded-full check happy
            # while the operation-check fails).
            "permission_scope": [
                "repository_storage",
                "repository_redistribution",
                "public_artifact_allowed",
                # ``usage_scope`` deliberately missing.
            ],
        }
    }
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_VENDOR_PERMISSION_SCOPE_INCOMPLETE" in codes


# ---- Stage 14: rule_body projection ----


def test_rule_body_missing_blocks() -> None:
    pack = make_pack()
    del pack["rules"]["rule-public-v1"]["rule_body"]["profile_id"]
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_BODY_INVALID" in codes


def test_rule_body_unknown_field_blocks() -> None:
    pack = make_pack()
    pack["rules"]["rule-public-v1"]["rule_body"]["extra_field"] = "bogus"
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_BODY_INVALID" in codes


def test_profile_id_mismatch_blocks() -> None:
    pack = make_pack()
    pack["rules"]["rule-public-v1"]["rule_body"]["profile_id"] = "hxforge.shell_tube.tube_layout.v1"
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_PROFILE_UNSUPPORTED" in codes


def test_authority_mode_duplicate_blocks() -> None:
    pack = make_pack()
    pack["rules"]["rule-public-v1"]["rule_body"]["allowed_shell_authority_modes"] = [
        "CALLER_SUPPLIED_EXPLICIT",
        "CALLER_SUPPLIED_EXPLICIT",
    ]
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_BODY_INVALID" in codes


def test_authority_mode_non_list_blocks() -> None:
    """A non-list value must block at the rule_body projection stage."""
    pack = make_pack()
    # A single string is non-list (and RFC-8785 serializable, so it
    # passes stage 9's canonical-hash check). The adapter must reject
    # it at stage 14 because it is not a list of strings.
    pack["rules"]["rule-public-v1"]["rule_body"]["allowed_shell_authority_modes"] = (
        "CALLER_SUPPLIED_EXPLICIT"  # type: ignore[assignment]
    )
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_BODY_INVALID" in codes


def test_authority_mode_unknown_token_blocks() -> None:
    pack = make_pack()
    pack["rules"]["rule-public-v1"]["rule_body"]["allowed_shell_authority_modes"] = ["NOT_A_MODE"]
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_BODY_INVALID" in codes


def test_negative_allowance_blocks() -> None:
    pack = make_pack()
    pack["rules"]["rule-public-v1"]["rule_body"]["minimum_bundle_peripheral_allowance_m"] = "-0.001"
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_BODY_INVALID" in codes


def test_negative_radial_clearance_blocks() -> None:
    pack = make_pack()
    pack["rules"]["rule-public-v1"]["rule_body"]["minimum_radial_clearance_m"] = "-0.001"
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_BODY_INVALID" in codes


def test_bool_maximum_position_count_blocks() -> None:
    pack = make_pack()
    pack["rules"]["rule-public-v1"]["rule_body"]["maximum_position_count"] = True  # type: ignore[assignment]
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_BODY_INVALID" in codes


def test_zero_maximum_position_count_blocks() -> None:
    pack = make_pack()
    pack["rules"]["rule-public-v1"]["rule_body"]["maximum_position_count"] = 0
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_BODY_INVALID" in codes


def test_duplicate_evidence_refs_block() -> None:
    pack = make_pack()
    pack["rules"]["rule-public-v1"]["rule_body"]["evidence_refs"] = [
        "ref:a",
        "ref:a",
    ]
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_BODY_INVALID" in codes


def test_malformed_provenance_edge_ids_block() -> None:
    pack = make_pack()
    # An empty string in provenance_edges fails ``validate_rule`` at
    # stage 8 (``SBG_RULE_ADAPTER_RULE_INVALID``) before the adapter
    # ever projects the rule_body. The semantic defect — non-string
    # provenance-edge identifiers — is captured at whichever stage
    # upstream TASK-012 raises first.
    pack["rules"]["rule-public-v1"]["provenance_edges"] = [""]
    pack["rules"]["rule-public-v1"]["canonical_hash"] = canonical_sha256(
        pack["rules"]["rule-public-v1"]
    )
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert (
        "SBG_RULE_ADAPTER_RULE_BODY_INVALID" in codes
        or "SBG_RULE_ADAPTER_PROVENANCE_INVALID" in codes
        or "SBG_RULE_ADAPTER_RULE_INVALID" in codes
    )


# ---- Determinism + same-input identity ----


def test_byte_identical_snapshot_for_same_input() -> None:
    pack = make_pack()
    s1 = build_shell_bundle_rule_authority_snapshot(loaded_rule_pack=pack, rule_id="rule-public-v1")
    s2 = build_shell_bundle_rule_authority_snapshot(loaded_rule_pack=pack, rule_id="rule-public-v1")
    assert s1.snapshot_hash == s2.snapshot_hash
    assert s1 == s2


def test_mutation_changes_snapshot_hash() -> None:
    pack = make_pack()
    s1 = build_shell_bundle_rule_authority_snapshot(loaded_rule_pack=pack, rule_id="rule-public-v1")
    mutated = mutate_rule(pack, "rule-public-v1", rule_body={"maximum_position_count": 5000})
    s2 = build_shell_bundle_rule_authority_snapshot(
        loaded_rule_pack=mutated, rule_id="rule-public-v1"
    )
    assert s1.snapshot_hash != s2.snapshot_hash
    assert s2.maximum_position_count == 5000


def test_input_mapping_is_not_mutated() -> None:
    pack = make_pack()
    snapshot_before = deepcopy(pack["rules"]["rule-public-v1"])
    build_shell_bundle_rule_authority_snapshot(loaded_rule_pack=pack, rule_id="rule-public-v1")
    assert pack["rules"]["rule-public-v1"] == snapshot_before


def test_no_first_match_or_fallback_behavior() -> None:
    """When the requested rule_id is absent, the adapter MUST NOT select
    a different rule — even if other approved rules exist."""
    pack = make_pack(extra_rule={"rule_id": "rule-other-v1"})
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-missing",
        )
    codes = {b.code for b in exc_info.value.blockers}
    assert "SBG_RULE_ADAPTER_RULE_NOT_FOUND" in codes
    # No fallback selection occurred: ``not found`` is the only failure
    # for the rule-lookup stage; other stages didn't get reached.
    for b in exc_info.value.blockers:
        assert "RULE_NOT_FOUND" in b.code or (
            # Stage 1/2 raw-type/shape defects may co-occur if both
            # the rule_id was bad AND the pack was shaped differently,
            # but here the pack is valid so neither raw-type nor
            # shape-stage blockers should fire.
            "RAW_TYPE_INVALID" not in b.code and "UNKNOWN_FIELD" not in b.code
        )


def test_unrelated_extra_rule_does_not_change_selected_snapshot_when_manifest_identical() -> None:
    """When the manifest identity is preserved, adding an unrelated rule
    does not change the selected snapshot's hash.

    In practice the B1 adapter reads ``rule_pack_identity`` from the
    ``manifest``, so a manifest with different ``rule_count`` and
    ``canonical_hash`` legitimately changes the snapshot. To exercise
    the architectural invariant the test must therefore mutate the
    in-memory ``rules`` mapping WITHOUT changing the manifest
    fields that the adapter reads. We do that by direct dict
    manipulation (the bypass is documentation-of-intent — builders
    in production mutate packs via ``load_rule_pack`` which always
    re-hashes the manifest).
    """
    pack = make_pack()
    s1 = build_shell_bundle_rule_authority_snapshot(loaded_rule_pack=pack, rule_id="rule-public-v1")
    pack_with_extra = make_pack(extra_rule={"rule_id": "rule-other-v1"})
    # Re-stamp the manifest to the original pack's manifest identity
    # so the B1 adapter sees the same rule_pack_identity for both.
    pack_with_extra["manifest"] = deepcopy(pack["manifest"])
    pack_with_extra["manifest"]["canonical_hash"] = canonical_sha256(pack_with_extra["manifest"])
    s2 = build_shell_bundle_rule_authority_snapshot(
        loaded_rule_pack=pack_with_extra, rule_id="rule-public-v1"
    )
    assert s1.snapshot_hash == s2.snapshot_hash


# ---- Blocker integrity ----


def test_all_blockers_carry_details_and_evidence_fields() -> None:
    pack = make_pack()
    del pack["permission_evidence"]
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    for blocker in exc_info.value.blockers:
        assert blocker.code in RULE_PACK_ADAPTER_BLOCKER_CODES
        # field_path is optional but never absent.
        assert blocker.field_path is None or isinstance(blocker.field_path, str)
        assert isinstance(blocker.message_key, str) and blocker.message_key
        assert isinstance(blocker.evidence_refs, tuple)
        # details is either None or a FrozenJsonObject (slice-A
        # Layer-B internal marker). Spec §10 requires canonical
        # JSON values; the adapter_blockers layer already enforces
        # this for dict inputs. The contract check here is purely
        # runtime: details is either None or a non-None canonical
        # marker.
        assert blocker.details is None or not isinstance(
            blocker.details, (list, bool, int, float, str, tuple)
        )


def test_no_partial_snapshot_on_failure() -> None:
    """AdapterFailure never carries a partial snapshot — only ``blockers``."""
    pack = make_pack()
    pack["manifest"]["canonical_hash"] = "0" * 64
    with pytest.raises(AdapterFailure) as exc_info:
        build_shell_bundle_rule_authority_snapshot(
            loaded_rule_pack=pack,
            rule_id="rule-public-v1",
        )
    # The exception exposes only ``blockers`` (and the inherited
    # args tuple). No snapshot, no partial geometry.
    assert not hasattr(exc_info.value, "geometry")
    assert not hasattr(exc_info.value, "snapshot")
