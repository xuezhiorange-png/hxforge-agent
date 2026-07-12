"""TASK-020-S2 rule profile adapter tests — closed profile, types, dedup.

Maps to §14.2.2 + §19.H minimum coverage for
``tests/exchangers/shell_tube/test_task020_rule_profile_adapter.py``:

- closed profile_id ``task020.configuration-rule.v1`` (§12.2);
- five frozen rule types (§12.3);
- deterministic §12.4 sort key;
- duplicate / conflict / intersection behavior (§12.5).

All rule payloads use the synthetic ``INTERNAL_ENGINEERING_RULE``
token vocabulary defined in the §14.2.3 fixtures. No engineering
value, numeric coefficient, expected output or restricted-standard
text is asserted anywhere in this file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from hexagent.exchangers.shell_tube.errors import BlockerError
from hexagent.exchangers.shell_tube.models import (
    AuthorityMode,
    BlockerCode,
    CaseRevisionAuthority,
    CaseRevisionStatus,
    ComponentTokens,
    ConstructionFamily,
    EquipmentFamily,
    EvaluatedRulePackAuthority,
    Orientation,
    RequestedRulePackIdentity,
    SelectedRuleAuthority,
    ShellAndTubeConfigurationRequest,
)
from hexagent.exchangers.shell_tube.rule_pack_adapter import (
    ConfigurationRulePackAdapter,
    loaded_rule_pack_view_from_loader_dict,
    rule_pack_validation_report_from_validate_dict,
)

PROFILE = "task020.configuration-rule.v1"

# ---------------------------------------------------------------------------
# Fixtures loader — reads from the §14.2.3 fixture allowlist (no glob / no
# recursive / no invented paths).
# ---------------------------------------------------------------------------

FIXTURE_ROOT = Path(__file__).resolve().parent.parent.parent / "fixtures" / "task020"


def _load_fixture(relpath: str) -> dict[str, Any]:
    path = FIXTURE_ROOT / relpath
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    return cast(dict[str, Any], raw) if isinstance(raw, dict) else {}


def _load_pack_payload(pack_dir: str) -> dict[str, Any]:
    pack_root: Path = FIXTURE_ROOT / "rule_packs" / pack_dir
    manifest_obj = json.loads((pack_root / "manifest.json").read_text(encoding="utf-8"))
    manifest = cast(dict[str, Any], manifest_obj) if isinstance(manifest_obj, dict) else {}
    rules: dict[str, dict[str, Any]] = {}
    for fp in sorted((pack_root / "rules").glob("*.json")):
        rule: dict[str, Any] = json.loads(fp.read_text(encoding="utf-8"))
        rule_id = rule.get("rule_id")
        if not isinstance(rule_id, str) or not rule_id:
            raise ValueError(f"rule at {fp} missing string rule_id (loader contract violation)")
        rules[rule_id] = rule
    provenance_edges = []
    for fp in sorted((pack_root / "provenance").glob("*.json")):
        provenance_edges.append(json.loads(fp.read_text(encoding="utf-8")))
    result: dict[str, Any] = {
        "manifest": manifest,
        "rules": rules,
        "provenance_edges": provenance_edges,
        "permission_evidence": {},
    }
    return cast(dict[str, Any], result)


def _make_valid_pack_payload() -> dict[str, Any]:
    return _load_pack_payload("valid_configuration_pack")


def _make_valid_report_payload() -> dict[str, Any]:
    pack = _make_valid_pack_payload()
    manifest = pack["manifest"]
    return {
        "status": "ok",
        "manifest": dict(manifest),
        "rule_count": len(pack["rules"]),
        "errors": [],
    }


def _make_matching_report_payload(payload: dict[str, Any], *, status: str = "ok") -> dict[str, Any]:
    """Build a validation-report dict whose manifest + rule_count match
    the given (possibly mutated) loaded-pack payload."""
    manifest = payload.get("manifest", {})
    rules = payload.get("rules", {})
    return {
        "status": status,
        "manifest": dict(manifest),
        "rule_count": len(rules),
        "errors": [],
    }


def _make_request_for_adapter() -> ShellAndTubeConfigurationRequest:
    case = CaseRevisionAuthority(
        revision_id="rev-001-committed",
        payload_hash="a" * 64,
        domain_snapshot_hash="b" * 64,
        revision_status=CaseRevisionStatus.COMMITTED,
    )
    requested_id = RequestedRulePackIdentity(
        rule_pack_id="task020-internal-engineering-rule-pack-v1",
        rule_pack_version="v1",
        rule_pack_canonical_hash="3" * 64,
    )
    return ShellAndTubeConfigurationRequest(
        schema_version="task020.configuration-request.v1",
        case_authority=case,
        equipment_family=EquipmentFamily.SHELL_AND_TUBE,
        authority_mode=AuthorityMode.APPROVED_RULE_PACK,
        construction_family=ConstructionFamily.FIXED_TUBESHEET,
        orientation=Orientation.HORIZONTAL,
        shell_pass_count=2,
        tube_pass_count=4,
        component_tokens=ComponentTokens(
            front_head="IER_FT_HEAD_A",
            shell="IER_SHELL_A",
            rear_head="IER_RH_HEAD_A",
        ),
        standard_system_id="INTERNAL_ENGINEERING_RULE",
        requested_rule_pack_identity=requested_id,
        evidence_refs=(),
    )


# ---------------------------------------------------------------------------
# §12.2 — closed profile_id
# ---------------------------------------------------------------------------


def test_cross_profile_rule_is_silently_ignored() -> None:
    """A rule whose ``profile_id`` is not the frozen TASK-020 profile
    is silently ignored (no blocker, no warning)."""
    payload = _make_valid_pack_payload()
    payload["rules"]["misc-rule-001"] = {
        "profile_id": "different.profile.v1",
        "rule_type": "COMPONENT_TOKEN_ALLOWLIST",
        "rule_id": "misc-rule-001",
        "rule_version": "v1",
        "constraint_id": "misc-front",
        "priority": 0,
        "applies_to_authority_modes": ["APPROVED_RULE_PACK"],
        "applies_to_construction_families": ["FIXED_TUBESHEET"],
        "component_slot": "front_head",
        "nullable": False,
        "allowed_tokens": ["IER_FT_HEAD_B"],
        "canonical_hash": "0" * 63 + "e",
        "source_class": "INTERNAL_ENGINEERING_RULE",
        "approval_status": "approved",
        "license_evidence": {"id": "internal-engineering-license-2026"},
        "evidence_refs": ["misc-evidence"],
        "provenance_edges": ["misc-edge"],
    }
    loaded = loaded_rule_pack_view_from_loader_dict(payload)
    report = rule_pack_validation_report_from_validate_dict(_make_matching_report_payload(payload))
    request = _make_request_for_adapter()

    evaluation = ConfigurationRulePackAdapter.validate(
        request=request,
        loaded_rule_pack=loaded,
        validation_report=report,
    )

    rule_ids = [
        r.rule_id for r in evaluation.evaluated_rule_pack_authority.selected_rule_authorities
    ]
    assert "misc-rule-001" not in rule_ids


def test_unknown_rule_type_with_task020_profile_emits_type_unrecognized() -> None:
    """A rule with the TASK-020 profile and a ``rule_type`` outside
    the closed §12.3 set emits ``STC_RULE_TYPE_UNRECOGNIZED``."""
    payload = _make_valid_pack_payload()
    payload["manifest"] = dict(payload["manifest"])
    payload["rules"] = dict(payload["rules"])
    payload["rules"]["bogus-type-001"] = {
        "profile_id": PROFILE,
        "rule_type": "WIDGET_FROBNICATION",
        "rule_id": "bogus-type-001",
        "rule_version": "v1",
        "constraint_id": "bogus-cfg",
        "priority": 99,
        "applies_to_authority_modes": ["APPROVED_RULE_PACK"],
        "applies_to_construction_families": ["FIXED_TUBESHEET"],
        "canonical_hash": "c" * 63 + "9",
        "source_class": "INTERNAL_ENGINEERING_RULE",
        "approval_status": "approved",
        "license_evidence": {"id": "internal-engineering-license-2026"},
        "evidence_refs": ["bogus-evidence"],
        "provenance_edges": ["bogus-edge"],
    }
    loaded = loaded_rule_pack_view_from_loader_dict(payload)
    report = rule_pack_validation_report_from_validate_dict(_make_matching_report_payload(payload))
    request = _make_request_for_adapter()
    with pytest.raises(BlockerError) as info:
        ConfigurationRulePackAdapter.validate(
            request=request,
            loaded_rule_pack=loaded,
            validation_report=report,
        )
    assert info.value.code == BlockerCode.STC_RULE_TYPE_UNRECOGNIZED.value


# ---------------------------------------------------------------------------
# §12.3 — five frozen rule types present in the §14.2.3 valid pack
# ---------------------------------------------------------------------------


def test_valid_pack_contains_all_five_frozen_rule_types() -> None:
    """The valid_configuration_pack fixture carries exactly the five
    frozen §12.3 rule types (the set, deduplicated)."""
    pack = _load_pack_payload("valid_configuration_pack")
    rule_types = sorted({rule["rule_type"] for rule in pack["rules"].values()})
    assert rule_types == sorted(
        [
            "COMPONENT_TOKEN_ALLOWLIST",
            "CONFIGURATION_COMBINATION_BLOCKLIST",
            "CONSTRUCTION_FAMILY_NORMALIZATION",
            "ORIENTATION_ALLOWLIST",
            "PASS_COUNT_ALLOWED_RANGE",
        ]
    )


def test_applicability_for_non_normalization_rule_uses_construction_families() -> None:
    """For non-CONSTRUCTION_FAMILY_NORMALIZATION rule types, an empty
    ``applies_to_construction_families`` array emits
    ``STC_RULE_APPLICABILITY_UNRESOLVED``."""
    payload = _make_valid_pack_payload()
    payload["rules"]["stc-cta-front-001"]["applies_to_construction_families"] = []
    loaded = loaded_rule_pack_view_from_loader_dict(payload)
    report = rule_pack_validation_report_from_validate_dict(_make_matching_report_payload(payload))
    request = _make_request_for_adapter()
    with pytest.raises(BlockerError) as info:
        ConfigurationRulePackAdapter.validate(
            request=request,
            loaded_rule_pack=loaded,
            validation_report=report,
        )
    assert info.value.code == BlockerCode.STC_RULE_APPLICABILITY_UNRESOLVED.value


def test_normalization_rule_applies_via_input_value_not_applies_to_families() -> None:
    """Per §12.8.3, CONSTRUCTION_FAMILY_NORMALIZATION does NOT carry an
    ``applies_to_construction_families`` field. The adapter reads
    ``input_value`` for applicability. A rule whose ``input_value``
    equals the request's construction family applies even if it
    carries no ``applies_to_construction_families`` field."""
    payload = _make_valid_pack_payload()
    payload["rules"]["stc-cfn-001"].pop("applies_to_construction_families", None)
    loaded = loaded_rule_pack_view_from_loader_dict(payload)
    report = rule_pack_validation_report_from_validate_dict(_make_matching_report_payload(payload))
    request = _make_request_for_adapter()
    evaluation = ConfigurationRulePackAdapter.validate(
        request=request,
        loaded_rule_pack=loaded,
        validation_report=report,
    )
    assert evaluation.normalized_construction_family == ConstructionFamily.FIXED_TUBESHEET


def test_normalization_rule_with_empty_input_value_emits_type_unrecognized() -> None:
    """A CONSTRUCTION_FAMILY_NORMALIZATION rule with empty/missing
    ``input_value`` is malformed and emits ``STC_RULE_TYPE_UNRECOGNIZED``."""
    payload = _make_valid_pack_payload()
    payload["rules"]["stc-cfn-001"]["input_value"] = ""
    loaded = loaded_rule_pack_view_from_loader_dict(payload)
    report = rule_pack_validation_report_from_validate_dict(_make_matching_report_payload(payload))
    request = _make_request_for_adapter()
    with pytest.raises(BlockerError) as info:
        ConfigurationRulePackAdapter.validate(
            request=request,
            loaded_rule_pack=loaded,
            validation_report=report,
        )
    assert info.value.code == BlockerCode.STC_RULE_TYPE_UNRECOGNIZED.value


# ---------------------------------------------------------------------------
# §12.4 — six-field sort key + silent dedup
# ---------------------------------------------------------------------------


def test_six_field_key_sort_orders_ascending() -> None:
    """The selected_rule_authorities are returned in ascending order
    under the §12.4 six-field key
    ``(priority, rule_type, constraint_id, rule_id, rule_version,
    rule_artifact_canonical_hash)``.
    """
    payload = _make_valid_pack_payload()
    loaded = loaded_rule_pack_view_from_loader_dict(payload)
    report = rule_pack_validation_report_from_validate_dict(_make_matching_report_payload(payload))
    request = _make_request_for_adapter()
    evaluation = ConfigurationRulePackAdapter.validate(
        request=request,
        loaded_rule_pack=loaded,
        validation_report=report,
    )
    sras = evaluation.evaluated_rule_pack_authority.selected_rule_authorities

    # Build the cross-check sequence by re-sorting the original rules
    # under the §12.4 six-tuple key, then comparing rule_id orderings.
    from hexagent.exchangers.shell_tube.rule_pack_adapter import _six_field_key

    expected_order = sorted(payload["rules"].values(), key=_six_field_key)
    expected_ids = [r["rule_id"] for r in expected_order]
    actual_ids = [r.rule_id for r in sras]
    assert actual_ids == expected_ids
    for entry in sras:
        assert isinstance(entry, SelectedRuleAuthority)


def test_exact_six_field_duplicate_is_silently_deduplicated() -> None:
    """Two surviving rules with **exactly equal** complete six-field
    keys represent the same authority and are silently deduplicated."""
    payload = _make_valid_pack_payload()
    src = dict(payload["rules"]["stc-cta-front-001"])
    payload["rules"]["stc-cta-front-001-dup"] = dict(src)
    payload["rules"]["stc-cta-front-001-dup"]["rule_id"] = src["rule_id"]
    loaded = loaded_rule_pack_view_from_loader_dict(payload)
    report = rule_pack_validation_report_from_validate_dict(_make_matching_report_payload(payload))
    request = _make_request_for_adapter()
    evaluation = ConfigurationRulePackAdapter.validate(
        request=request,
        loaded_rule_pack=loaded,
        validation_report=report,
    )
    front_rules = [
        r
        for r in evaluation.evaluated_rule_pack_authority.selected_rule_authorities
        if r.rule_id == "stc-cta-front-001"
    ]
    assert len(front_rules) == 1


# ---------------------------------------------------------------------------
# §12.5 / §20.B — divergent-identity blocker + normalization conflict
# ---------------------------------------------------------------------------


def test_same_logical_identity_divergent_authority_emits_duplicate_identity() -> None:
    """Two surviving rules sharing
    ``(profile_id, rule_type, constraint_id)`` but differing in
    any complete six-field key emit ``STC_RULE_DUPLICATE_IDENTITY``."""
    payload = _make_valid_pack_payload()
    src = dict(payload["rules"]["stc-cfn-001"])
    payload["rules"]["stc-cfn-divergent"] = dict(src)
    payload["rules"]["stc-cfn-divergent"]["rule_id"] = "stc-cfn-divergent"
    payload["rules"]["stc-cfn-divergent"]["canonical_hash"] = "d" * 63 + "7"
    loaded = loaded_rule_pack_view_from_loader_dict(payload)
    report = rule_pack_validation_report_from_validate_dict(_make_matching_report_payload(payload))
    request = _make_request_for_adapter()
    with pytest.raises(BlockerError) as info:
        ConfigurationRulePackAdapter.validate(
            request=request,
            loaded_rule_pack=loaded,
            validation_report=report,
        )
    assert info.value.code == BlockerCode.STC_RULE_DUPLICATE_IDENTITY.value


def test_normalization_conflict_emits_stc_rule_normalization_conflict() -> None:
    """Two applicable normalization rules with differing
    ``normalized_value`` results emit
    ``STC_RULE_NORMALIZATION_CONFLICT`` (per §12.5 item 2).

    Different ``constraint_id`` keeps the divergent-identity blocker
    (§12.5 item 1, §20.B) from firing first.
    """
    payload = _make_valid_pack_payload()
    payload["rules"]["stc-cfn-002"] = dict(payload["rules"]["stc-cfn-001"])
    payload["rules"]["stc-cfn-002"]["rule_id"] = "stc-cfn-002"
    payload["rules"]["stc-cfn-002"]["constraint_id"] = "conflicting-cfn-b"
    payload["rules"]["stc-cfn-002"]["normalized_value"] = "U_TUBE"
    payload["rules"]["stc-cfn-002"]["canonical_hash"] = "e" * 63 + "8"
    loaded = loaded_rule_pack_view_from_loader_dict(payload)
    report = rule_pack_validation_report_from_validate_dict(_make_matching_report_payload(payload))
    request = _make_request_for_adapter()
    with pytest.raises(BlockerError) as info:
        ConfigurationRulePackAdapter.validate(
            request=request,
            loaded_rule_pack=loaded,
            validation_report=report,
        )
    assert info.value.code == BlockerCode.STC_RULE_NORMALIZATION_CONFLICT.value


# ---------------------------------------------------------------------------
# §12.5 item 8 — empty applicability
# ---------------------------------------------------------------------------


def test_empty_authority_modes_in_rule_emits_unresolved() -> None:
    """A rule whose ``applies_to_authority_modes`` array is empty
    emits ``STC_RULE_APPLICABILITY_UNRESOLVED``."""
    payload = _make_valid_pack_payload()
    payload["rules"]["stc-cta-front-001"]["applies_to_authority_modes"] = []
    loaded = loaded_rule_pack_view_from_loader_dict(payload)
    report = rule_pack_validation_report_from_validate_dict(_make_matching_report_payload(payload))
    request = _make_request_for_adapter()
    with pytest.raises(BlockerError) as info:
        ConfigurationRulePackAdapter.validate(
            request=request,
            loaded_rule_pack=loaded,
            validation_report=report,
        )
    assert info.value.code == BlockerCode.STC_RULE_APPLICABILITY_UNRESOLVED.value


# ---------------------------------------------------------------------------
# §20.D — frozen ConfigurationRuleEvaluation value object
# ---------------------------------------------------------------------------


def test_valid_pack_yields_full_selected_rule_authorities() -> None:
    """The valid_configuration_pack evaluation produces the full
    selected_rule_authorities tuple with one SelectedRuleAuthority
    per §12.4-sorted surviving rule."""
    payload = _make_valid_pack_payload()
    loaded = loaded_rule_pack_view_from_loader_dict(payload)
    report = rule_pack_validation_report_from_validate_dict(_make_matching_report_payload(payload))
    request = _make_request_for_adapter()
    evaluation = ConfigurationRulePackAdapter.validate(
        request=request,
        loaded_rule_pack=loaded,
        validation_report=report,
    )
    assert isinstance(evaluation.evaluated_rule_pack_authority, EvaluatedRulePackAuthority)
    assert len(evaluation.evaluated_rule_pack_authority.selected_rule_authorities) >= 1
    # No parallel selected_rule_ids list exists; only the typed
    # tuple of SelectedRuleAuthority is part of the §20.D value object.
    assert isinstance(evaluation.evaluated_rule_pack_authority.selected_rule_authorities, tuple)
    for entry in evaluation.evaluated_rule_pack_authority.selected_rule_authorities:
        # §6.3.5.1 — eight-field typed value object.
        assert entry.rule_id
        assert entry.rule_version
        assert entry.rule_artifact_canonical_hash
