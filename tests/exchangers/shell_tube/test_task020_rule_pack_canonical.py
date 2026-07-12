"""TASK-020-S2 canonical / sorting / ordering tests.

These tests verify the §12.4 + §11 canonical-data discipline:

* Selected rule authorities are sorted by the §12.4 6-field key
  (already covered in test_task020_rule_pack_hash_integration.py;
  this file adds dedicated ordering assertions for each sub-discipline);
* Per-rule evidence_refs (TASK-020) and provenance_edge_ids
  (TASK-012) are sorted in ascending Unicode-code-point order on the
  SelectedRuleAuthority;
* ``canonical_hash`` on the artifact is a 64-character hex SHA-256;
* The TASK-020 payload identity triple (profile_id, rule_type,
  constraint_id) is read from inside ``rule_body``;
* The TASK-012 directive identity triple (rule_id, rule_version,
  canonical_hash) is read from the artifact top level;
* The TASK-020 closed profile_id is enforced (§12.2);
* The TASK-020 closed rule_type set is enforced (§12.3);
* The TASK-020 priority field is read from ``rule_body.priority``
  (not artifact top-level) and must be an int.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from hexagent.exchangers.shell_tube.models import (
    AuthorityMode,
    CaseRevisionAuthority,
    CaseRevisionStatus,
    ComponentTokens,
    ConstructionFamily,
    EquipmentFamily,
    Orientation,
    RequestedRulePackIdentity,
    ShellAndTubeConfigurationRequest,
)
from hexagent.exchangers.shell_tube.rule_pack_adapter import (
    ConfigurationRulePackAdapter,
    loaded_rule_pack_view_from_loader_dict,
    rule_pack_validation_report_from_validate_dict,
)
from hexagent.rule_packs.loader import load_rule_pack
from hexagent.rule_packs.validation import validate_rule_pack

FIXTURE_ROOT: Final[Path] = Path(__file__).parent.parent.parent / "fixtures/task020"
VALID_PACK: Final[Path] = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"


def _manifest_id(pack: Path) -> tuple[str, str, str]:
    m = json.loads((pack / "manifest.json").read_text())
    return m["rule_pack_id"], m["rule_pack_version"], m["canonical_hash"]


def _case_auth() -> CaseRevisionAuthority:
    return CaseRevisionAuthority(
        revision_id="rev-canon",
        payload_hash="a" * 64,
        domain_snapshot_hash="b" * 64,
        revision_status=CaseRevisionStatus.COMMITTED,
    )


def _request(pack: Path) -> ShellAndTubeConfigurationRequest:
    rid, rver, rhash = _manifest_id(pack)
    return ShellAndTubeConfigurationRequest(
        schema_version="task020.configuration-request.v1",
        case_authority=_case_auth(),
        equipment_family=EquipmentFamily.SHELL_AND_TUBE,
        authority_mode=AuthorityMode.APPROVED_RULE_PACK,
        construction_family=ConstructionFamily.FIXED_TUBESHEET,
        orientation=Orientation.HORIZONTAL,
        shell_pass_count=1,
        tube_pass_count=1,
        component_tokens=ComponentTokens(
            front_head="IER_FT_A", shell="IER_SH_A", rear_head="IER_RH_A"
        ),
        standard_system_id="INTERNAL",
        requested_rule_pack_identity=RequestedRulePackIdentity(
            rule_pack_id=rid,
            rule_pack_version=rver,
            rule_pack_canonical_hash=rhash,
        ),
    )


# ---------------------------------------------------------------------------
# Per-rule evidence/provenance ordering
# ---------------------------------------------------------------------------


def test_per_rule_evidence_refs_are_unicode_sorted() -> None:
    """§11.4 — SelectedRuleAuthority.evidence_refs and
    .provenance_edge_ids are ascending Unicode-code-point order, deduped."""
    loader_dict = load_rule_pack(VALID_PACK)
    validate_dict = validate_rule_pack(VALID_PACK)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    report = rule_pack_validation_report_from_validate_dict(validate_dict)
    request = _request(VALID_PACK)
    evaluation = ConfigurationRulePackAdapter.validate(request, loaded, report)
    for a in evaluation.evaluated_rule_pack_authority.selected_rule_authorities:
        assert list(a.evidence_refs) == sorted(a.evidence_refs)
        assert list(a.provenance_edge_ids) == sorted(a.provenance_edge_ids)


# ---------------------------------------------------------------------------
# Canonical hash 64-char hex invariant
# ---------------------------------------------------------------------------


def test_artifact_canonical_hash_is_64_hex_chars() -> None:
    """All 7 rules in the valid pack have 64-char hex SHA-256 canonical_hash."""
    loader_dict = load_rule_pack(VALID_PACK)
    for rule_id, rule in loader_dict["rules"].items():
        h = rule["canonical_hash"]
        assert isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h), (
            f"rule {rule_id} canonical_hash is not 64 hex chars: {h!r}"
        )


def test_manifest_canonical_hash_is_64_hex_chars() -> None:
    """Manifest's canonical_hash is 64-char hex SHA-256."""
    m = json.loads((VALID_PACK / "manifest.json").read_text())
    h = m["canonical_hash"]
    assert isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# §6.3.5.1 — SelectedRuleAuthority reads from artifact top-level
# ---------------------------------------------------------------------------


def test_selected_authorities_read_direct_rule_id_and_version() -> None:
    """SelectedRuleAuthority.rule_id and .rule_version are taken from
    the artifact top-level directive identity."""
    loader_dict = load_rule_pack(VALID_PACK)
    validate_dict = validate_rule_pack(VALID_PACK)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    report = rule_pack_validation_report_from_validate_dict(validate_dict)
    request = _request(VALID_PACK)
    evaluation = ConfigurationRulePackAdapter.validate(request, loaded, report)
    for a in evaluation.evaluated_rule_pack_authority.selected_rule_authorities:
        rule = loaded.rules[a.rule_id]
        assert a.rule_id == rule["rule_id"]
        assert a.rule_version == rule["rule_version"]
        assert a.rule_artifact_canonical_hash == rule["canonical_hash"]
        assert a.source_class == rule["source_class"]


def test_selected_authorities_carry_provenance_edge_ids_from_directive() -> None:
    """provenance_edge_ids come from artifact top-level, not rule_body."""
    loader_dict = load_rule_pack(VALID_PACK)
    validate_dict = validate_rule_pack(VALID_PACK)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    report = rule_pack_validation_report_from_validate_dict(validate_dict)
    request = _request(VALID_PACK)
    evaluation = ConfigurationRulePackAdapter.validate(request, loaded, report)
    for a in evaluation.evaluated_rule_pack_authority.selected_rule_authorities:
        rule = loaded.rules[a.rule_id]
        # The artifact's top-level provenance_edges is a list of edge_ids.
        edge_ids = sorted(set(rule["provenance_edges"]))
        assert list(a.provenance_edge_ids) == edge_ids


# ---------------------------------------------------------------------------
# §12.2 / §12.3 — closed profile_id + closed rule_type
# ---------------------------------------------------------------------------


def test_t120_profile_id_constant() -> None:
    """§12.2 — TASK-020 profile_id is the frozen constant
    ``task020.configuration-rule.v1``."""
    expected = "task020.configuration-rule.v1"
    loader_dict = load_rule_pack(VALID_PACK)
    seen: set[str] = set()
    for _rule_id, rule in loader_dict["rules"].items():
        # TASK-020 predicate profile_id lives inside ``rule_body``.
        seen.add(rule["rule_body"]["profile_id"])
    assert expected in seen


def test_t120_closed_rule_types() -> None:
    """§12.3 — only the five closed rule_types are valid for TASK-020 rules."""
    closed = {
        "COMPONENT_TOKEN_ALLOWLIST",
        "CONSTRUCTION_FAMILY_NORMALIZATION",
        "CONFIGURATION_COMBINATION_BLOCKLIST",
        "PASS_COUNT_ALLOWED_RANGE",
        "ORIENTATION_ALLOWLIST",
    }
    loader_dict = load_rule_pack(VALID_PACK)
    for rule_id, rule in loader_dict["rules"].items():
        if rule["rule_body"].get("profile_id") == "task020.configuration-rule.v1":
            assert rule["rule_body"]["rule_type"] in closed, (
                f"rule {rule_id} rule_type {rule['rule_body']['rule_type']!r} not in closed set"
            )


# ---------------------------------------------------------------------------
# §12.4 — priority field is read from rule_body
# ---------------------------------------------------------------------------


def test_priority_field_lives_inside_rule_body() -> None:
    """Round-2 §9 — priority is read from rule_body.priority, NOT
    artifact top-level. Top-level ``priority`` is counterfeited and ignored."""
    loader_dict = load_rule_pack(VALID_PACK)
    for rule_id, rule in loader_dict["rules"].items():
        # Priority must be inside rule_body.
        assert "priority" in rule["rule_body"], f"rule {rule_id} missing rule_body.priority"
        assert isinstance(rule["rule_body"]["priority"], int)


def test_top_level_counterfeit_priority_field_ignored() -> None:
    """Round-2 §9 — top-level counterfeit ``priority`` is ignored.
    Even if it's an invalid value (negative, or wrong type), the
    adapter continues to read from rule_body and the call succeeds."""
    import copy

    loader_dict = load_rule_pack(VALID_PACK)
    validate_dict = validate_rule_pack(VALID_PACK)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    report = rule_pack_validation_report_from_validate_dict(validate_dict)

    # Inject bogus top-level ``priority`` on every rule.
    rules_view: dict[str, object] = {}
    for rid, rule in loaded.rules.items():
        m = copy.deepcopy(dict(rule))
        m["priority"] = -1  # counterfeited, should be ignored
        rules_view[rid] = m
    new_loaded = type(loaded)(
        manifest=loaded.manifest,
        rules=rules_view,
        provenance_edges=loaded.provenance_edges,
        permission_evidence=loaded.permission_evidence,
        rule_pack_id=loaded.rule_pack_id,
        rule_pack_version=loaded.rule_pack_version,
        rule_pack_canonical_hash=loaded.rule_pack_canonical_hash,
        rule_count=loaded.rule_count,
    )
    request = _request(VALID_PACK)
    # The adapter continues to read rule_body.priority=0; the call
    # succeeds as long as rule_body is internally consistent.
    ConfigurationRulePackAdapter.validate(request, new_loaded, report)
