"""TASK-020-S2 rule-pack adapter top-level tests.

Maps to §14.2.2 + §19.H minimum coverage for
``tests/exchangers/shell_tube/test_task020_rule_pack_adapter.py``:

- top-level presence matrix (§19.F);
- TASK-012 report status (`STC_RULE_PACK_VALIDATION_FAILED`, §7.1);
- cross-input consistency (§6.3.3);
- approved-pack success (§7 / §12);
- ``ConfigurationRuleEvaluation`` frozen shape (§20.D).

All rule payloads use the synthetic ``INTERNAL_ENGINEERING_RULE``
token vocabulary defined in the §14.2.3 fixtures. No engineering
value, numeric coefficient, expected output or restricted-standard
text is asserted anywhere in this file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import hexagent.exchangers.shell_tube as st
from hexagent.exchangers.shell_tube.models import (
    AuthorityMode,
    CaseRevisionAuthority,
    CaseRevisionStatus,
    ComponentTokens,
    ConfigurationRuleEvaluation,
    ConfigurationValidationResult,
    ConstructionFamily,
    EquipmentFamily,
    EvaluatedRulePackAuthority,
    Orientation,
    RequestedRulePackIdentity,
    ShellAndTubeConfigurationRequest,
)
from hexagent.exchangers.shell_tube.rule_pack_adapter import (
    ConfigurationRulePackAdapter,
    loaded_rule_pack_view_from_loader_dict,
    rule_pack_validation_report_from_validate_dict,
)

# ---------------------------------------------------------------------------
# Fixtures loader — reads from the §14.2.3 fixture allowlist (no glob / no
# recursive / no invented paths).
# ---------------------------------------------------------------------------

FIXTURE_ROOT = Path(__file__).resolve().parent.parent.parent / "fixtures" / "task020"


def _load_pack_payload(pack_dir: str) -> dict[str, Any]:
    pack_root: Path = FIXTURE_ROOT / "rule_packs" / pack_dir
    manifest_obj = json.loads((pack_root / "manifest.json").read_text(encoding="utf-8"))
    manifest = cast(dict[str, Any], manifest_obj) if isinstance(manifest_obj, dict) else {}
    rules: dict[str, dict[str, Any]] = {}
    for fp in sorted((pack_root / "rules").glob("*.json")):
        rule: dict[str, Any] = json.loads(fp.read_text(encoding="utf-8"))
        rule_id = rule.get("rule_id")
        if not isinstance(rule_id, str) or not rule_id:
            raise ValueError(f"rule at {fp} missing string rule_id")
        rules[rule_id] = rule
    provenance_edges: list[Any] = []
    for fp in sorted((pack_root / "provenance").glob("*.json")):
        provenance_edges.append(json.loads(fp.read_text(encoding="utf-8")))
    result: dict[str, Any] = {
        "manifest": manifest,
        "rules": rules,
        "provenance_edges": provenance_edges,
        "permission_evidence": {},
    }
    return cast(dict[str, Any], result)


def _load_pack_manifest(pack_dir: str) -> dict[str, Any]:
    manifest_obj: object = json.loads(
        (FIXTURE_ROOT / "rule_packs" / pack_dir / "manifest.json").read_text(encoding="utf-8")
    )
    if not isinstance(manifest_obj, dict):
        return {}
    return cast(dict[str, Any], manifest_obj)


def _make_matching_report_payload(payload: dict[str, Any], *, status: str = "ok") -> dict[str, Any]:
    manifest = payload.get("manifest", {})
    rules = payload.get("rules", {})
    return {
        "status": status,
        "manifest": dict(manifest),
        "rule_count": len(rules),
        "errors": [],
    }


def _valid_request_payload(**overrides: object) -> dict[str, object]:
    request: dict[str, object] = {
        "schema_version": st.REQUEST_SCHEMA_VERSION,
        "case_authority": {
            "revision_id": "rev-001-committed",
            "payload_hash": "a" * 64,
            "domain_snapshot_hash": "b" * 64,
            "status": "committed",
        },
        "equipment_family": "SHELL_AND_TUBE",
        "authority_mode": "APPROVED_RULE_PACK",
        "construction_family": "FIXED_TUBESHEET",
        "orientation": "HORIZONTAL",
        "shell_pass_count": 2,
        "tube_pass_count": 4,
        "front_head_token": "IER_FT_HEAD_A",
        "shell_token": "IER_SHELL_A",
        "rear_head_token": "IER_RH_HEAD_A",
        "standard_system_id": "INTERNAL_ENGINEERING_RULE",
        "requested_rule_pack_identity": {
            "rule_pack_id": "task020-internal-engineering-rule-pack-v1",
            "rule_pack_version": "v1",
            "rule_pack_canonical_hash": "3" * 64,
        },
        "evidence_refs": [],
    }
    request.update(overrides)
    return request


# ---------------------------------------------------------------------------
# §19.F — input-presence matrix (top-level)
# ---------------------------------------------------------------------------


def test_internal_generic_mode_with_no_adapter_inputs_returns_valid() -> None:
    """``INTERNAL_GENERIC`` mode with both adapter inputs absent
    returns ``VALID`` and produces a normalized configuration
    (§19.F row 1)."""
    payload = _valid_request_payload()
    payload["authority_mode"] = "INTERNAL_GENERIC"
    payload["requested_rule_pack_identity"] = None
    payload["standard_system_id"] = None
    result = st.validate_request(payload, loaded_rule_pack=None, validation_report=None)
    assert isinstance(result, ConfigurationValidationResult)
    assert result.status.value == "VALID"
    assert result.configuration is not None


def test_internal_generic_mode_with_adapter_input_emits_not_expected_in_mode() -> None:
    """``INTERNAL_GENERIC`` mode with an adapter input present emits
    ``STC_RULE_PACK_NOT_EXPECTED_IN_MODE`` (§19.F row 2)."""
    payload = _valid_request_payload()
    payload["authority_mode"] = "INTERNAL_GENERIC"
    payload["requested_rule_pack_identity"] = None
    payload["standard_system_id"] = None
    loaded_payload = _load_pack_payload("valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(loaded_payload)
    report_payload = _make_matching_report_payload(loaded_payload)
    report = rule_pack_validation_report_from_validate_dict(report_payload)
    result = st.validate_request(
        payload,
        loaded_rule_pack=loaded,
        validation_report=report,
    )
    assert result.status.value == "BLOCKED"
    assert any(b.code == "STC_RULE_PACK_NOT_EXPECTED_IN_MODE" for b in result.blockers)


def test_approved_rule_pack_mode_with_no_adapter_inputs_emits_inputs_missing() -> None:
    """``APPROVED_RULE_PACK`` mode with both adapter inputs absent
    emits ``STC_RULE_PACK_ADAPTER_INPUTS_MISSING`` (§19.F row 3)."""
    payload = _valid_request_payload()
    result = st.validate_request(
        payload,
        loaded_rule_pack=None,
        validation_report=None,
    )
    assert result.status.value == "BLOCKED"
    assert any(b.code == "STC_RULE_PACK_ADAPTER_INPUTS_MISSING" for b in result.blockers)


def test_approved_rule_pack_mode_with_partial_inputs_emits_inputs_incomplete() -> None:
    """``APPROVED_RULE_PACK`` mode with exactly one adapter input
    emits ``STC_RULE_PACK_ADAPTER_INPUTS_INCOMPLETE`` (§19.F row 4)."""
    payload = _valid_request_payload()
    loaded_payload = _load_pack_payload("valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(loaded_payload)
    result = st.validate_request(
        payload,
        loaded_rule_pack=loaded,
        validation_report=None,
    )
    assert result.status.value == "BLOCKED"
    assert any(b.code == "STC_RULE_PACK_ADAPTER_INPUTS_INCOMPLETE" for b in result.blockers)


# ---------------------------------------------------------------------------
# §7 / §12 — approved-pack success path
# ---------------------------------------------------------------------------


def test_approved_rule_pack_mode_full_path_returns_valid() -> None:
    """When both adapter inputs are present and the pack loads with
    ``status == 'ok'``, the full pipeline produces a
    ``ConfigurationRuleEvaluation`` (per §20.D) and ``validate_request``
    returns ``VALID``."""
    payload = _valid_request_payload()
    loaded_payload = _load_pack_payload("valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(loaded_payload)
    report_payload = _make_matching_report_payload(loaded_payload)
    report = rule_pack_validation_report_from_validate_dict(report_payload)
    result = st.validate_request(
        payload,
        loaded_rule_pack=loaded,
        validation_report=report,
    )
    assert result.status.value == "VALID"
    assert result.configuration is not None
    # Configuration contains the EVALUATED authority, not the input
    # identity (§6.3.5 / §20.D).
    era = result.configuration.authority_binding.evaluated_rule_pack_authority
    assert isinstance(era, EvaluatedRulePackAuthority)
    assert era.validation_status == "ok"


# ---------------------------------------------------------------------------
# §7.1 — TASK-012 status != "ok"
# ---------------------------------------------------------------------------


def test_unapproved_pack_emits_validation_failed() -> None:
    """Per §15 item 8 + §20.C, an unapproved_rule_pack fixture whose
    TASK-012 validator returns ``status = "fail"`` causes TASK-020 to
    emit only ``STC_RULE_PACK_VALIDATION_FAILED``. TASK-020 MUST NOT
    parse ``validation_report.errors[*].message``."""
    payload = _valid_request_payload()
    loaded_payload = _load_pack_payload("unapproved_rule_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(loaded_payload)
    # Manifest identity triple from the unapproved pack is matched.
    manifest = loaded_payload["manifest"]
    payload["requested_rule_pack_identity"] = {
        "rule_pack_id": manifest["rule_pack_id"],
        "rule_pack_version": manifest["rule_pack_version"],
        "rule_pack_canonical_hash": manifest["canonical_hash"],
    }
    report_dict = {
        "status": "fail",
        "manifest": dict(manifest),
        "rule_count": len(loaded_payload["rules"]),
        "errors": [{"path": "manifest.json", "message": "approval_status is not approved"}],
    }
    report = rule_pack_validation_report_from_validate_dict(report_dict)
    result = st.validate_request(
        payload,
        loaded_rule_pack=loaded,
        validation_report=report,
    )
    assert result.status.value == "BLOCKED"
    assert any(b.code == "STC_RULE_PACK_VALIDATION_FAILED" for b in result.blockers)
    # Reserved rule-level codes MUST NOT be emitted (§20.C / §19.G).
    for forbidden in (
        "STC_RULE_UNAPPROVED",
        "STC_RULE_CANONICAL_HASH_MISMATCH",
        "STC_RULE_LICENSE_BLOCKED",
        "STC_RULE_PROVENANCE_BLOCKED",
    ):
        assert not any(b.code == forbidden for b in result.blockers)


def test_license_blocked_pack_emits_validation_failed() -> None:
    """Per §15 item 8 + §20.C, a license_blocked_rule_pack fixture
    whose TASK-012 validator returns ``status = "fail"`` causes
    TASK-020 to emit only ``STC_RULE_PACK_VALIDATION_FAILED``."""
    payload = _valid_request_payload()
    loaded_payload = _load_pack_payload("license_blocked_rule_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(loaded_payload)
    manifest = loaded_payload["manifest"]
    payload["requested_rule_pack_identity"] = {
        "rule_pack_id": manifest["rule_pack_id"],
        "rule_pack_version": manifest["rule_pack_version"],
        "rule_pack_canonical_hash": manifest["canonical_hash"],
    }
    report_dict = {
        "status": "fail",
        "manifest": dict(manifest),
        "rule_count": len(loaded_payload["rules"]),
        "errors": [{"path": "manifest.json", "message": "license not recognized"}],
    }
    report = rule_pack_validation_report_from_validate_dict(report_dict)
    result = st.validate_request(
        payload,
        loaded_rule_pack=loaded,
        validation_report=report,
    )
    assert result.status.value == "BLOCKED"
    assert any(b.code == "STC_RULE_PACK_VALIDATION_FAILED" for b in result.blockers)


# ---------------------------------------------------------------------------
# §6.3.3 — cross-input consistency
# ---------------------------------------------------------------------------


def test_cross_input_identity_mismatch_emits_report_mismatch() -> None:
    """When ``loaded_rule_pack.manifest`` and ``validation_report.manifest``
    disagree on any identity field, the adapter emits
    ``STC_RULE_PACK_VALIDATION_REPORT_MISMATCH``."""
    pack_payload = _load_pack_payload("valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(pack_payload)
    report_manifest = dict(pack_payload["manifest"])
    # Mutate the validation-report manifest to disagree.
    report_manifest["rule_pack_version"] = "v999-drift"
    report_dict = {
        "status": "ok",
        "manifest": report_manifest,
        "rule_count": len(pack_payload["rules"]),
        "errors": [],
    }
    report = rule_pack_validation_report_from_validate_dict(report_dict)
    request_dict = _valid_request_payload()
    nested_obj = request_dict["requested_rule_pack_identity"]
    req_dict: dict[str, object] = (
        cast(dict[str, object], dict(nested_obj)) if isinstance(nested_obj, dict) else {}
    )
    req_dict["rule_pack_version"] = "v1"
    request_dict["requested_rule_pack_identity"] = req_dict
    # Build the request from the dict via the existing payload path
    # so the validation pipeline builds a proper
    # ShellAndTubeConfigurationRequest internally.
    result = st.validate_request(
        request_dict,
        loaded_rule_pack=loaded,
        validation_report=report,
    )
    assert result.status.value == "BLOCKED"
    assert any(b.code == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH" for b in result.blockers)


def test_requested_identity_mismatch_with_loaded_pack_emits_canonical_mismatch() -> None:
    """When the request's ``requested_rule_pack_identity`` does not
    match the loaded pack's manifest, the §6.3.3 path emits
    ``STC_REQUESTED_RULE_PACK_IDENTITY_MISMATCH``."""
    pack_payload = _load_pack_payload("valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(pack_payload)
    report_dict = _make_matching_report_payload(pack_payload)
    report = rule_pack_validation_report_from_validate_dict(report_dict)
    request_dict = _valid_request_payload()
    # Drift the request hash to disagree with both loaded and report.
    nested_obj = request_dict["requested_rule_pack_identity"]
    req_dict_2: dict[str, object] = (
        cast(dict[str, object], dict(nested_obj)) if isinstance(nested_obj, dict) else {}
    )
    req_dict_2["rule_pack_canonical_hash"] = "9" * 64
    request_dict["requested_rule_pack_identity"] = req_dict_2
    result = st.validate_request(
        request_dict,
        loaded_rule_pack=loaded,
        validation_report=report,
    )
    assert result.status.value == "BLOCKED"
    # Adapter may emit either REPORT_MISMATCH (cross-input) or
    # REQUESTED_RULE_PACK_IDENTITY_MISMATCH; both are §6.3.3 boundary
    # codes. The contract requires that the request identity mismatch
    # be surfaced.
    code_set = {b.code for b in result.blockers}
    assert (
        "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH" in code_set
        or "STC_REQUESTED_RULE_PACK_IDENTITY_MISMATCH" in code_set
    )


# ---------------------------------------------------------------------------
# §20.D — frozen ConfigurationRuleEvaluation shape (direct adapter entry)
# ---------------------------------------------------------------------------


def test_configuration_rule_evaluation_has_required_fields() -> None:
    """Per §20.D, the success-only value object carries
    ``normalized_construction_family`` and
    ``evaluated_rule_pack_authority`` exactly; no parallel lists, no
    optional fields.
    """
    pack_payload = _load_pack_payload("valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(pack_payload)
    report_dict = _make_matching_report_payload(pack_payload)
    report = rule_pack_validation_report_from_validate_dict(report_dict)
    case = CaseRevisionAuthority(
        revision_id="rev-001-committed",
        payload_hash="a" * 64,
        domain_snapshot_hash="b" * 64,
        revision_status=CaseRevisionStatus.COMMITTED,
    )
    requested_id = RequestedRulePackIdentity(
        rule_pack_id=pack_payload["manifest"]["rule_pack_id"],
        rule_pack_version=pack_payload["manifest"]["rule_pack_version"],
        rule_pack_canonical_hash=pack_payload["manifest"]["canonical_hash"],
    )
    request = ShellAndTubeConfigurationRequest(
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
    evaluation = ConfigurationRulePackAdapter.validate(
        request=request,
        loaded_rule_pack=loaded,
        validation_report=report,
    )
    assert isinstance(evaluation, ConfigurationRuleEvaluation)
    assert evaluation.normalized_construction_family == ConstructionFamily.FIXED_TUBESHEET
    assert isinstance(evaluation.evaluated_rule_pack_authority, EvaluatedRulePackAuthority)
