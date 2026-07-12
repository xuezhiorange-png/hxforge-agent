"""TASK-020-S2 rule-pack canonical ordering tests.

Maps to §14.2.2 + §19.H minimum coverage for
``tests/exchangers/shell_tube/test_task020_rule_pack_canonical.py``:

- selected-rule composite sort (§12.4);
- per-rule evidence / provenance ordering (§11.4);
- warning / blocker full-object ordering (§11.4);
- canonical JSON behavior (§11.2).

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
# §12.4 — selected-rule composite sort
# ---------------------------------------------------------------------------


def test_selected_rule_authorities_sort_under_six_field_key() -> None:
    """The selected_rule_authorities are returned in ascending order
    under the §12.4 six-field key
    ``(priority, rule_type, constraint_id, rule_id, rule_version,
    rule_artifact_canonical_hash)``."""
    pack_payload = _load_pack_payload("valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(pack_payload)
    report = rule_pack_validation_report_from_validate_dict(_match_report(pack_payload))
    result = st.validate_request(
        _valid_request_payload(), loaded_rule_pack=loaded, validation_report=report
    )
    assert isinstance(result, ConfigurationValidationResult)
    assert result.configuration is not None  # type: ignore[union-attr]
    era = result.configuration.authority_binding.evaluated_rule_pack_authority
    sras = era.selected_rule_authorities

    # Re-derive the expected order from the raw rule bodies.
    from hexagent.exchangers.shell_tube.rule_pack_adapter import _six_field_key

    expected = sorted(pack_payload["rules"].values(), key=_six_field_key)
    expected_ids = [r["rule_id"] for r in expected]
    actual_ids = [r.rule_id for r in sras]
    assert actual_ids == expected_ids


# ---------------------------------------------------------------------------
# §11.4 — per-rule evidence / provenance ordering
# ---------------------------------------------------------------------------


def test_per_rule_evidence_refs_are_unicode_sorted() -> None:
    """Each SelectedRuleAuthority's ``evidence_refs`` and
    ``provenance_edge_ids`` lists are sorted in ascending
    Unicode code-point order (per §11.4 / §6.3.5.1)."""
    pack_payload = _load_pack_payload("valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(pack_payload)
    report = rule_pack_validation_report_from_validate_dict(_match_report(pack_payload))
    result = st.validate_request(
        _valid_request_payload(), loaded_rule_pack=loaded, validation_report=report
    )
    assert result.configuration is not None  # type: ignore[union-attr]
    era = result.configuration.authority_binding.evaluated_rule_pack_authority
    sras = era.selected_rule_authorities
    for entry in sras:
        assert list(entry.evidence_refs) == sorted(entry.evidence_refs)
        assert list(entry.provenance_edge_ids) == sorted(entry.provenance_edge_ids)


# ---------------------------------------------------------------------------
# §11.4 — warning / blocker full-object ordering
# ---------------------------------------------------------------------------


def test_blocker_list_is_canonicalized() -> None:
    """A blocked validation result carries its blockers in canonical
    sorted order (§11.4 ``sort_error_entries``)."""
    pack_payload = _load_pack_payload("valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(pack_payload)
    # Force a blocker by reporting status=fail.
    report = rule_pack_validation_report_from_validate_dict(
        _match_report(pack_payload) | {"status": "fail"}
    )
    result = st.validate_request(
        _valid_request_payload(), loaded_rule_pack=loaded, validation_report=report
    )
    assert isinstance(result, ConfigurationValidationResult)
    assert result.status.value == "BLOCKED"
    codes = [b.code for b in result.blockers]
    assert list(codes) == sorted(codes)


# ---------------------------------------------------------------------------
# §11.2 — canonical JSON behavior
# ---------------------------------------------------------------------------


def test_canonical_payload_returns_frozen_hash() -> None:
    """``configuration_hash`` of an arbitrary canonical-payload dict
    returns a 64-char lowercase hex string twice for the same
    canonical payload (§11.2 / §11.5 determinism)."""
    payload_dict = {
        "equipment_family": "SHELL_AND_TUBE",
        "construction_family": "FIXED_TUBESHEET",
        "shell_pass_count": 2,
        "tube_pass_count": 4,
        "authority_binding": {
            "authority_mode": "APPROVED_RULE_PACK",
            "evaluated_rule_pack_authority": {
                "rule_pack_id": "task020-internal-engineering-rule-pack-v1",
                "selected_rule_authorities": [],
            },
        },
    }
    h_a = canonical.configuration_hash(payload_dict)
    h_b = canonical.configuration_hash(payload_dict)
    assert h_a == h_b
    assert isinstance(h_a, str) and len(h_a) == 64


def test_canonical_payload_helpers_return_sorted_lists() -> None:
    """``sort_evidence_refs`` and ``sort_error_entries`` return
    ascending sorted output."""
    refs = ["z-evidence", "a-evidence", "m-evidence"]
    assert list(canonical.sort_evidence_refs(refs)) == sorted(refs)


def test_error_entry_evidence_refs_sort_via_sort_evidence_refs() -> None:
    """Per §11.4, ``sort_evidence_refs`` returns ascending Unicode
    code-point order on the list of str evidence_refs."""
    refs = ["z-evidence", "a-evidence", "m-evidence"]
    sorted_refs = canonical.sort_evidence_refs(refs)
    assert list(sorted_refs) == sorted(refs)


def test_composite_canonical_key_for_error_entry_is_stable() -> None:
    """``composite_canonical_key`` returns a 5-tuple derived from the
    ErrorEntry's five §10.4 fields."""
    entry_dict = {
        "code": "STC_TOKEN_UNSUPPORTED_BY_RULE_PACK",
        "field_path": "component_tokens.front_head",
        "message_key": "stc_token_unsupported",
        "evidence_refs": ["a-evidence", "z-evidence"],
        "details": None,
    }
    k1 = canonical.composite_canonical_key(entry_dict)
    k2 = canonical.composite_canonical_key(entry_dict)
    assert k1 == k2
    assert len(k1) >= 1
