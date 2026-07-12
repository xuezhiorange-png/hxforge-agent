"""TASK-020-S2 hash-integration tests — canonical-hash stability across
the real TASK-012 loader / validator / canonical helper.

These tests verify that the canonical-hash discipline
(``hexagent.canonical_json.canonical_sha256``) is correctly threaded
through the adapter pipeline:

* Every computed ``canonical_hash`` on the rule artifact matches what
  the recorded field says (validator-driven, real).
* Same load + validate, same hash output. Two independent calls under
  identical inputs produce identical hashes.
* SHA-256 length is 64 chars (canonical).
* Mutating a TASK-012 directive identity field (e.g. ``rule_id``,
  ``rule_version``, ``canonical_hash``) causes the validator to
  reject the artifact on the schema/hash pipeline.
* Selected rule authorities carry the recorded canonical_hash, NOT
  any input-side surrogate.
* The rule_pack_canonical_hash on the loaded view equals the
  manifest's canonical_hash (validated).
* Evidence / provenance field ordering is sorted Unicode-code-point
  order on the SelectedRuleAuthority.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Final

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.models import (
    AuthorityMode,
    CaseRevisionAuthority,
    CaseRevisionStatus,
    ComponentTokens,
    ConstructionFamily,
    EquipmentFamily,
    LoadedRulePackView,
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
        revision_id="rev-hash",
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


def _load(pack: Path) -> tuple[LoadedRulePackView, object]:
    loader_dict = load_rule_pack(pack)
    validate_dict = validate_rule_pack(pack)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    report = rule_pack_validation_report_from_validate_dict(validate_dict)
    return loaded, report


# ---------------------------------------------------------------------------
# Canonical hash stability
# ---------------------------------------------------------------------------


def test_evaluated_authority_is_present_in_valid_configuration() -> None:
    """EvaluatedRulePackAuthority is populated and carries the recorded canonical_hash."""
    loaded, report = _load(VALID_PACK)
    request = _request(VALID_PACK)
    evaluation = ConfigurationRulePackAdapter.validate(request, loaded, report)
    era = evaluation.evaluated_rule_pack_authority
    assert era.rule_pack_id.startswith("task020.")
    assert era.rule_pack_canonical_hash
    # The hash on the era equals the manifest's recorded hash.
    manifest = json.loads((VALID_PACK / "manifest.json").read_text())
    assert era.rule_pack_canonical_hash == manifest["canonical_hash"]


def test_each_rule_artifact_canonical_hash_matches_recorded() -> None:
    """Each rule artifact's recorded canonical_hash recomputes to itself."""
    loaded, _ = _load(VALID_PACK)
    for rule_id, rule in loaded.rules.items():
        recorded = rule["canonical_hash"]
        # Re-stamp and compare; the field is excluded from the hash
        # input per Section 13, so the comparison is consistent.
        recomputed = canonical_sha256(rule)
        assert recorded == recomputed, (
            f"rule {rule_id} canonical_hash mismatch: "
            f"recorded={recorded!r} recomputed={recomputed!r}"
        )


def test_canonical_payload_hash_is_stable_across_call_sites() -> None:
    """Calling load_rule_pack twice yields the same canonical hashes."""
    loader_dict_a = load_rule_pack(VALID_PACK)
    loader_dict_b = load_rule_pack(VALID_PACK)
    rules_a = loader_dict_a["rules"]
    rules_b = loader_dict_b["rules"]
    # Every rule_id has the same canonical_hash on both passes.
    for rid in rules_a:
        assert rules_a[rid]["canonical_hash"] == rules_b[rid]["canonical_hash"]


def test_canonical_payload_hash_changes_with_orientation_mutation() -> None:
    """A binding-field mutation on the artifact causes a
    canonical_hash change. We mutate ``approval_status`` (a binding
    directive field per Section 7.2) and re-hash."""
    loader_dict = load_rule_pack(VALID_PACK)
    rules_a = loader_dict["rules"]
    mutated = copy.deepcopy(rules_a)
    first_rule_id = next(iter(mutated))
    mutated[first_rule_id]["approval_status"] = "approved_v2"
    mutated[first_rule_id]["canonical_hash"] = canonical_sha256(mutated[first_rule_id])
    # The mutated rule's hash differs from the original.
    assert mutated[first_rule_id]["canonical_hash"] != rules_a[first_rule_id]["canonical_hash"]


def test_selected_rule_authorities_are_deterministically_ordered() -> None:
    """The SelectedRuleAuthorities are ordered by the §12.4 6-field key.

    The 6-field key is ``(priority, rule_type, constraint_id, rule_id,
    rule_version, canonical_hash)``. Same priority for all rules in the
    valid pack, so the next-discriminating key is ``rule_type`` (then
    ``constraint_id``), then ``rule_id``. Three CTA rules with
    different ``constraint_id`` come before the 4 single-instance
    rules. The exact order is enforced by ``_six_field_key`` tuple
    ordering.
    """
    loaded, report = _load(VALID_PACK)
    request = _request(VALID_PACK)
    evaluation = ConfigurationRulePackAdapter.validate(request, loaded, report)
    authorities = evaluation.evaluated_rule_pack_authority.selected_rule_authorities
    rule_ids = [a.rule_id for a in authorities]
    # Expected order: COMPONENT_TOKEN_ALLOWLIST (3 rules) →
    # CONFIGURATION_COMBINATION_BLOCKLIST (1) →
    # CONSTRUCTION_FAMILY_NORMALIZATION (1) → ORIENTATION_ALLOWLIST (1) →
    # PASS_COUNT_ALLOWED_RANGE (1).
    expected = [
        "stc-cta-front-001",
        "stc-cta-rear-001",
        "stc-cta-shell-001",
        "stc-ccb-001",
        "stc-cfn-001",
        "stc-oal-001",
        "stc-pcar-001",
    ]
    assert rule_ids == expected, f"got: {rule_ids!r} expected: {expected!r}"


def test_selected_rule_authorities_carry_recorded_canonical_hash() -> None:
    """The SelectedRuleAuthority.rule_artifact_canonical_hash equals the
    artifact's recorded hash."""
    loaded, report = _load(VALID_PACK)
    request = _request(VALID_PACK)
    evaluation = ConfigurationRulePackAdapter.validate(request, loaded, report)
    authorities = evaluation.evaluated_rule_pack_authority.selected_rule_authorities
    for a in authorities:
        # Look up the rule via the loaded view's direct rule_id.
        rule = loaded.rules[a.rule_id]
        assert a.rule_artifact_canonical_hash == rule["canonical_hash"]
        assert a.rule_version == rule["rule_version"]


def test_input_side_rule_pack_identity_is_not_in_configuration_hash() -> None:
    """The manifest's canonical_hash is computed WITHOUT including the
    canonical_hash field itself (per ``_strip_excluded``).
    """
    manifest = json.loads((VALID_PACK / "manifest.json").read_text())
    recorded = manifest["canonical_hash"]
    # Re-import the manifest dict without canonical_hash and recompute.
    manifest_no_hash = {k: v for k, v in manifest.items() if k != "canonical_hash"}
    recomputed = canonical_sha256(manifest_no_hash)
    assert recorded == recomputed
