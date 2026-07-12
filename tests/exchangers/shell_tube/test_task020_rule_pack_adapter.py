"""TASK-020-S2 top-level adapter tests — real TASK-012 integration.

These tests drive the S2 adapter's public entry point
``ConfigurationRulePackAdapter.validate`` through REAL
``hexagent.rule_packs.loader.load_rule_pack`` and
``hexagent.rule_packs.validation.validate_rule_pack``. They cover:

* top-level happy-path success;
* valid pack produces ConfigurationRuleEvaluation shape with
  EvaluatedRulePackAuthority;
* cross-input consistency blocker on identity disagreement;
* rule-count mismatch between loaded and report;
* ``validation_report.status != "ok"`` emits
  STC_RULE_PACK_VALIDATION_FAILED;
* minimum-fail-shape report accepted without manifest / rule_count;
* minimum-fail-shape report rejected as such on the fail path;
* success report without manifest rejected;
* success report without rule_count rejected;
* cross-input consistency uses TASK-012 directive identity fields.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final, cast

import pytest

from hexagent.exchangers.shell_tube.errors import BlockerError
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
UNAPPROVED_PACK: Final[Path] = FIXTURE_ROOT / "rule_packs/unapproved_rule_pack"
LICENSE_PACK: Final[Path] = FIXTURE_ROOT / "rule_packs/license_blocked_rule_pack"
CONFLICTING_PACK: Final[Path] = FIXTURE_ROOT / "rule_packs/conflicting_configuration_pack"


def _manifest_id(pack: Path) -> tuple[str, str, str]:
    m = json.loads((pack / "manifest.json").read_text())
    return m["rule_pack_id"], m["rule_pack_version"], m["canonical_hash"]


def _case_auth() -> CaseRevisionAuthority:
    return CaseRevisionAuthority(
        revision_id="rev-rpac",
        payload_hash="a" * 64,
        domain_snapshot_hash="b" * 64,
        revision_status=CaseRevisionStatus.COMMITTED,
    )


def _request_for(pack: Path) -> ShellAndTubeConfigurationRequest:
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
# Real-TASK-012 integration: real valid pack succeeds end-to-end
# ---------------------------------------------------------------------------


def test_real_valid_pack_validator_status_ok() -> None:
    """§5 — real validate_rule_pack returns ``ok`` for valid pack."""
    result = validate_rule_pack(VALID_PACK)
    assert result["status"] == "ok"


def test_real_valid_pack_adapter_succeeds() -> None:
    """§5 — adapter returns ConfigurationRuleEvaluation on valid pack."""
    loader_dict = load_rule_pack(VALID_PACK)
    validate_dict = validate_rule_pack(VALID_PACK)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    report = rule_pack_validation_report_from_validate_dict(validate_dict)
    request = _request_for(VALID_PACK)
    evaluation = ConfigurationRulePackAdapter.validate(request, loaded, report)
    assert evaluation.evaluated_rule_pack_authority.rule_pack_id.startswith("task020.")
    assert len(evaluation.evaluated_rule_pack_authority.selected_rule_authorities) == 7


def test_configuration_rule_evaluation_has_required_fields() -> None:
    """§20.D — ConfigurationRuleEvaluation has the two frozen fields."""
    loader_dict = load_rule_pack(VALID_PACK)
    validate_dict = validate_rule_pack(VALID_PACK)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    report = rule_pack_validation_report_from_validate_dict(validate_dict)
    request = _request_for(VALID_PACK)
    evaluation = ConfigurationRulePackAdapter.validate(request, loaded, report)
    assert evaluation.normalized_construction_family == ConstructionFamily.FIXED_TUBESHEET
    era = evaluation.evaluated_rule_pack_authority
    assert era.validation_status == "ok"
    assert era.rule_pack_canonical_hash  # non-empty


# ---------------------------------------------------------------------------
# Real-TASK-012 fail packs
# ---------------------------------------------------------------------------


def test_real_unapproved_pack_validator_status_fail() -> None:
    """§5 — TASK-012 reports fail for the unapproved pack (manifest §15.6 rejection)."""
    result = validate_rule_pack(UNAPPROVED_PACK)
    assert result["status"] == "fail"


def test_real_unapproved_pack_adapter_emits_validation_failed() -> None:
    """§5 — adapter emits STC_RULE_PACK_VALIDATION_FAILED for unapproved pack."""
    loader_dict = load_rule_pack(UNAPPROVED_PACK)
    validate_dict = validate_rule_pack(UNAPPROVED_PACK)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    report = rule_pack_validation_report_from_validate_dict(validate_dict)
    request = _request_for(UNAPPROVED_PACK)
    with pytest.raises(BlockerError) as exc:
        ConfigurationRulePackAdapter.validate(request, loaded, report)
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_FAILED"


def test_real_license_pack_validator_status_fail() -> None:
    """§5 — TASK-012 reports fail for the license-blocked pack."""
    result = validate_rule_pack(LICENSE_PACK)
    assert result["status"] == "fail"


def test_real_license_pack_adapter_emits_validation_failed() -> None:
    """§5 — adapter emits STC_RULE_PACK_VALIDATION_FAILED for license pack."""
    loader_dict = load_rule_pack(LICENSE_PACK)
    validate_dict = validate_rule_pack(LICENSE_PACK)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    report = rule_pack_validation_report_from_validate_dict(validate_dict)
    request = _request_for(LICENSE_PACK)
    with pytest.raises(BlockerError) as exc:
        ConfigurationRulePackAdapter.validate(request, loaded, report)
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_FAILED"


# ---------------------------------------------------------------------------
# Real-TASK-012 conflicting pack drives STC_RULE_DUPLICATE_IDENTITY (already
# covered in test_task020_rule_profile_adapter.py). This is the dedicated
# integration test.
# ---------------------------------------------------------------------------


def test_real_conflicting_pack_validator_status_ok() -> None:
    """§5 — TASK-012 schema passes; the conflict is purely TASK-020 logical."""
    result = validate_rule_pack(CONFLICTING_PACK)
    assert result["status"] == "ok"


def test_real_conflicting_pack_adapter_emits_duplicate_identity() -> None:
    """§5 — adapter emits STC_RULE_DUPLICATE_IDENTITY from the real TASK-012 loader."""
    loader_dict = load_rule_pack(CONFLICTING_PACK)
    validate_dict = validate_rule_pack(CONFLICTING_PACK)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    report = rule_pack_validation_report_from_validate_dict(validate_dict)
    request = _request_for(CONFLICTING_PACK)
    with pytest.raises(BlockerError) as exc:
        ConfigurationRulePackAdapter.validate(request, loaded, report)
    assert str(exc.value.code) == "STC_RULE_DUPLICATE_IDENTITY"


# ---------------------------------------------------------------------------
# §6.3.3 cross-input consistency (Round-2 §6)
# ---------------------------------------------------------------------------


def test_cross_input_identity_mismatch_emits_mismatch_blocker() -> None:
    """§6.3.3 — request's rule_pack_id disagrees with loaded/report."""
    loader_dict = load_rule_pack(VALID_PACK)
    validate_dict = validate_rule_pack(VALID_PACK)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    report = rule_pack_validation_report_from_validate_dict(validate_dict)
    rid, rver, rhash = _manifest_id(VALID_PACK)
    # Forge a request whose identity triple disagrees.
    request = ShellAndTubeConfigurationRequest(
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
            rule_pack_id="WRONG-PACK-ID",
            rule_pack_version=rver,
            rule_pack_canonical_hash=rhash,
        ),
    )
    with pytest.raises(BlockerError) as exc:
        ConfigurationRulePackAdapter.validate(request, loaded, report)
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"


def test_rule_count_mismatch_emits_mismatch_blocker() -> None:
    """§6.3.3 — loaded and report disagree on rule_count."""
    loader_dict = load_rule_pack(VALID_PACK)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    validate_dict = validate_rule_pack(VALID_PACK)
    _manifest_id(VALID_PACK)  # confirm manifest identity triple is fetchable
    request = _request_for(VALID_PACK)
    # Forge a report whose rule_count disagrees.
    forged = dict(validate_dict)
    forged["rule_count"] = 99  # disagree
    forged_report = rule_pack_validation_report_from_validate_dict(forged)
    with pytest.raises(BlockerError) as exc:
        ConfigurationRulePackAdapter.validate(request, loaded, forged_report)
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"


# ---------------------------------------------------------------------------
# §6.3.2 fail-shape discipline (Round-2 §6)
# ---------------------------------------------------------------------------


def test_minimal_fail_report_without_manifest_accepted() -> None:
    """Round-2 §6 — minimal {status, errors} without manifest/rule_count is accepted on fail."""
    loader_dict = load_rule_pack(VALID_PACK)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    minimal_fail = {"status": "fail", "errors": [{"path": "loader", "message": "x"}]}
    report = rule_pack_validation_report_from_validate_dict(minimal_fail)
    request = _request_for(VALID_PACK)
    with pytest.raises(BlockerError) as exc:
        ConfigurationRulePackAdapter.validate(request, loaded, report)
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_FAILED"


def test_minimal_fail_report_emits_validation_failed_blocker() -> None:
    """Round-2 §6 — minimal fail report goes to STC_RULE_PACK_VALIDATION_FAILED."""
    loader_dict = load_rule_pack(VALID_PACK)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    minimal_fail = {"status": "fail", "errors": []}
    report = rule_pack_validation_report_from_validate_dict(minimal_fail)
    request = _request_for(VALID_PACK)
    with pytest.raises(BlockerError) as exc:
        ConfigurationRulePackAdapter.validate(request, loaded, report)
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_FAILED"


def test_success_report_without_manifest_rejected() -> None:
    """Round-2 §6 — status=ok without manifest is rejected as mismatch."""
    bad_ok = {"status": "ok", "errors": [], "rule_count": 7}
    with pytest.raises(BlockerError) as exc:
        rule_pack_validation_report_from_validate_dict(cast("dict[str, object]", bad_ok))
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"


def test_success_report_without_rule_count_rejected() -> None:
    """Round-2 §6 — status=ok without rule_count is rejected as mismatch."""
    bad_ok = {"status": "ok", "errors": [], "manifest": {}}
    with pytest.raises(BlockerError) as exc:
        rule_pack_validation_report_from_validate_dict(cast("dict[str, object]", bad_ok))
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"
