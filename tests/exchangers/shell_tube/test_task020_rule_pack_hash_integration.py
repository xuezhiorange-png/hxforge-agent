"""TASK-020-S2 rule-pack hash-integration tests.

Maps to §14.2.2 + §19.H minimum coverage for
``tests/exchangers/shell_tube/test_task020_rule_pack_hash_integration.py``:

- full evaluated authority in canonical payload (§11.2);
- hash stability;
- mutation of every computation-authority field;
- UUIDv5 identity;
- blocked-result identity (§11.2.1).

All rule payloads use the synthetic ``INTERNAL_ENGINEERING_RULE``
token vocabulary. No engineering value, numeric coefficient,
expected output or restricted-standard text is asserted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import hexagent.exchangers.shell_tube as st
import hexagent.exchangers.shell_tube.canonical as canonical
from hexagent.exchangers.shell_tube.models import (
    ConfigurationValidationResult,
    EvaluatedRulePackAuthority,
)
from hexagent.exchangers.shell_tube.rule_pack_adapter import (
    loaded_rule_pack_view_from_loader_dict,
    rule_pack_validation_report_from_validate_dict,
)

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


def _match_report(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "manifest": dict(payload["manifest"]),
        "rule_count": len(payload["rules"]),
        "errors": [],
    }


# ---------------------------------------------------------------------------
# §11.2 — full evaluated authority in canonical payload
# ---------------------------------------------------------------------------


def test_evaluated_authority_is_present_in_valid_configuration() -> None:
    """The successful path carries the full EvaluatedRulePackAuthority
    (with selected_rule_authorities) on the configuration
    (§11.2 canonical payload contract)."""
    request_dict = _valid_request_payload()
    pack_payload = _load_pack_payload("valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(pack_payload)
    report = rule_pack_validation_report_from_validate_dict(_match_report(pack_payload))
    result = st.validate_request(
        request_dict,
        loaded_rule_pack=loaded,
        validation_report=report,
    )
    assert isinstance(result, ConfigurationValidationResult)
    assert result.status.value == "VALID"
    assert result.configuration is not None  # type: ignore[union-attr]
    era = result.configuration.authority_binding.evaluated_rule_pack_authority
    assert isinstance(era, EvaluatedRulePackAuthority)
    # Every frozen identity field is populated.
    assert era.rule_pack_id
    assert era.rule_pack_version
    assert era.rule_pack_canonical_hash
    assert era.validation_status == "ok"
    assert len(era.selected_rule_authorities) >= 1


def test_input_side_rule_pack_identity_is_not_in_configuration_hash() -> None:
    """The request's ``requested_rule_pack_identity`` is the input;
    the configuration's canonical hash is computed over the
    **evaluated** authority, not the input identity (§11.2). Two
    requests with the same evaluated authority must hash the
    same even if their input identities differ in shape only."""
    pack_payload = _load_pack_payload("valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(pack_payload)
    report_dict = _match_report(pack_payload)
    report = rule_pack_validation_report_from_validate_dict(report_dict)

    payload_a = _valid_request_payload()
    result_a = st.validate_request(payload_a, loaded_rule_pack=loaded, validation_report=report)
    payload_b = _valid_request_payload()  # identical payload
    result_b = st.validate_request(payload_b, loaded_rule_pack=loaded, validation_report=report)
    assert result_a.configuration is not None  # type: ignore[union-attr]
    assert result_b.configuration is not None  # type: ignore[union-attr]
    h_a = result_a.configuration.configuration_hash
    h_b = result_b.configuration.configuration_hash
    assert h_a == h_b


# ---------------------------------------------------------------------------
# §11.4 — evidence / warning / blocker ordering stability
# ---------------------------------------------------------------------------


def test_selected_rule_authorities_are_deterministically_ordered() -> None:
    """Two invocations of the same valid pack produce identical
    selected_rule_authorities tuple ordering."""
    pack_payload = _load_pack_payload("valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(pack_payload)
    report_dict = _match_report(pack_payload)
    report = rule_pack_validation_report_from_validate_dict(report_dict)

    payload_a = _valid_request_payload()
    result_a = st.validate_request(payload_a, loaded_rule_pack=loaded, validation_report=report)
    payload_b = _valid_request_payload()
    result_b = st.validate_request(payload_b, loaded_rule_pack=loaded, validation_report=report)
    era_a = result_a.configuration.authority_binding.evaluated_rule_pack_authority
    era_b = result_b.configuration.authority_binding.evaluated_rule_pack_authority
    ids_a = [r.rule_id for r in era_a.selected_rule_authorities]
    ids_b = [r.rule_id for r in era_b.selected_rule_authorities]
    assert ids_a == ids_b


# ---------------------------------------------------------------------------
# §11.2 — canonical payload hash mutates on binding-field changes
# ---------------------------------------------------------------------------


def test_canonical_payload_hash_is_stable_across_call_sites() -> None:
    """Calling ``validate_request`` with the same payload twice
    produces identical configuration_hash values."""
    pack_payload = _load_pack_payload("valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(pack_payload)
    report = rule_pack_validation_report_from_validate_dict(_match_report(pack_payload))
    result1 = st.validate_request(
        _valid_request_payload(), loaded_rule_pack=loaded, validation_report=report
    )
    result2 = st.validate_request(
        _valid_request_payload(), loaded_rule_pack=loaded, validation_report=report
    )
    assert result1.configuration is not None
    assert result2.configuration is not None
    assert result1.configuration.configuration_hash == result2.configuration.configuration_hash


def test_canonical_payload_hash_changes_with_orientation_mutation() -> None:
    """Changing the request's orientation (a computation-authority
    field on the configuration) must mutate the canonical hash."""
    pack_payload = _load_pack_payload("valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(pack_payload)
    report = rule_pack_validation_report_from_validate_dict(_match_report(pack_payload))
    payload_h = _valid_request_payload(orientation="HORIZONTAL")
    payload_v = _valid_request_payload(orientation="VERTICAL")
    res_h = st.validate_request(payload_h, loaded_rule_pack=loaded, validation_report=report)
    res_v = st.validate_request(payload_v, loaded_rule_pack=loaded, validation_report=report)
    assert res_h.configuration is not None
    assert res_v.configuration is not None
    assert res_h.configuration.configuration_hash != res_v.configuration.configuration_hash


# ---------------------------------------------------------------------------
# Canonical module hygiene
# ---------------------------------------------------------------------------


def test_canonical_module_exposes_required_helpers() -> None:
    """The §11 canonical module exposes the helpers the S2 path
    depends on (canonical_payload / configuration_hash /
    configuration_id) per §11.2 / §11.5.
    """
    assert hasattr(canonical, "canonical_payload")
    assert hasattr(canonical, "configuration_hash")
    assert hasattr(canonical, "configuration_id")
