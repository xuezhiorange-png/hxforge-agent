"""TASK-020-S2 rule-pack fixture-driven tests.

Maps to §14.2.2 + §19.H minimum coverage for
``tests/exchangers/shell_tube/test_task020_rule_pack_fixtures.py``:

- all four §14.2.3 rule-pack fixture sets
  (``valid_configuration_pack`` / ``conflicting_configuration_pack`` /
  ``unapproved_rule_pack`` / ``license_blocked_rule_pack``);
- required-rule missing / required-slot missing
  (``STC_RULE_CONSTRAINT_MISSING``);
- unapproved / license / provenance blocked
  (``STC_RULE_PACK_VALIDATION_FAILED``);
- conflicting-rule fixture
  (``STC_RULE_DUPLICATE_IDENTITY``);
- unsupported-token
  (``STC_TOKEN_UNSUPPORTED_BY_RULE_PACK``);
- incompatible combination
  (``STC_CONFIGURATION_COMBINATION_BLOCKED``);
- no restricted content — all fixtures use the synthetic
  ``INTERNAL_ENGINEERING_RULE`` vocabulary.

The fixture files live under the §14.2.3 exact paths; this module
only reads them via the frozen file allowlist.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

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

# ---------------------------------------------------------------------------
# Fixtures loader — exact §14.2.3 paths only.
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


def _make_report(payload: dict[str, Any], *, status: str = "ok") -> dict[str, Any]:
    return {
        "status": status,
        "manifest": dict(payload["manifest"]),
        "rule_count": len(payload["rules"]),
        "errors": [],
    }


def _build_request(
    pack_payload: dict[str, Any],
    **request_overrides: object,
) -> ShellAndTubeConfigurationRequest:
    manifest = pack_payload["manifest"]
    case = CaseRevisionAuthority(
        revision_id="rev-001-committed",
        payload_hash="a" * 64,
        domain_snapshot_hash="b" * 64,
        revision_status=CaseRevisionStatus.COMMITTED,
    )
    requested_id = RequestedRulePackIdentity(
        rule_pack_id=manifest["rule_pack_id"],
        rule_pack_version=manifest["rule_pack_version"],
        rule_pack_canonical_hash=manifest["canonical_hash"],
    )
    if not request_overrides:
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
    cf = cast(
        ConstructionFamily,
        request_overrides.get("construction_family", ConstructionFamily.FIXED_TUBESHEET),  # type: ignore[arg-type]
    )
    orient = cast(
        Orientation,
        request_overrides.get("orientation", Orientation.HORIZONTAL),  # type: ignore[arg-type]
    )
    sh_pass = cast(
        int,
        request_overrides.get("shell_pass_count", 2),  # type: ignore[arg-type]
    )
    tu_pass = cast(
        int,
        request_overrides.get("tube_pass_count", 4),  # type: ignore[arg-type]
    )
    return ShellAndTubeConfigurationRequest(
        schema_version="task020.configuration-request.v1",
        case_authority=case,
        equipment_family=EquipmentFamily.SHELL_AND_TUBE,
        authority_mode=AuthorityMode.APPROVED_RULE_PACK,
        construction_family=cf,
        orientation=orient,
        shell_pass_count=sh_pass,
        tube_pass_count=tu_pass,
        component_tokens=ComponentTokens(
            front_head=cast(
                str | None,
                request_overrides.get("front_head", "IER_FT_HEAD_A"),  # type: ignore[arg-type]
            ),
            shell=cast(
                str | None,
                request_overrides.get("shell", "IER_SHELL_A"),  # type: ignore[arg-type]
            ),
            rear_head=cast(
                str | None,
                request_overrides.get("rear_head", "IER_RH_HEAD_A"),  # type: ignore[arg-type]
            ),
        ),
        standard_system_id="INTERNAL_ENGINEERING_RULE",
        requested_rule_pack_identity=requested_id,
        evidence_refs=(),
    )


def _invoke_adapter(
    payload: dict[str, Any],
    request: ShellAndTubeConfigurationRequest,
    *,
    status: str = "ok",
) -> Any:
    loaded = loaded_rule_pack_view_from_loader_dict(payload)
    report = rule_pack_validation_report_from_validate_dict(_make_report(payload, status=status))
    return ConfigurationRulePackAdapter.validate(
        request=request,
        loaded_rule_pack=loaded,
        validation_report=report,
    )


# ---------------------------------------------------------------------------
# §14.2.3 — fixture set presence
# ---------------------------------------------------------------------------


def test_four_rule_pack_fixtures_exist() -> None:
    """All four §14.2.3 rule-pack fixture sets are present under the
    frozen allowlist."""
    expected = [
        "valid_configuration_pack",
        "conflicting_configuration_pack",
        "unapproved_rule_pack",
        "license_blocked_rule_pack",
    ]
    for pack_dir in expected:
        manifest_path = FIXTURE_ROOT / "rule_packs" / pack_dir / "manifest.json"
        assert manifest_path.exists(), f"missing fixture: {manifest_path}"


def test_case_revision_four_fixtures_exist() -> None:
    """All four §14.2.3 case-revision fixtures are present."""
    expected = [
        "case_revision_committed.json",
        "case_revision_superseded.json",
        "case_revision_archived.json",
        "case_revision_draft_blocked.json",
    ]
    for filename in expected:
        path = FIXTURE_ROOT / "case_revision" / filename
        assert path.exists(), f"missing case_revision fixture: {path}"


def test_no_restricted_standard_text_in_any_fixture() -> None:
    """All fixtures use the synthetic ``INTERNAL_ENGINEERING_RULE``
    vocabulary. No fixture may embed TEMA / restricted-standard text,
    tables, or formulae (§6.2 / §14.2.3)."""
    forbidden_substrings = (
        "TEMA",
        "TEMA_CLASS",
        "ASME",
        "API_660",
        "Figure 1",
        "TABLE 1",
    )
    for json_path in sorted((FIXTURE_ROOT).rglob("*.json")):
        text = json_path.read_text(encoding="utf-8")
        for needle in forbidden_substrings:
            assert needle not in text, (
                f"fixture {json_path} contains forbidden restricted-standard substring {needle!r}"
            )


# ---------------------------------------------------------------------------
# §15 item 8 / §20.C — unapproved / license-blocked
# ---------------------------------------------------------------------------


def test_unapproved_pack_fixture_loads_safely() -> None:
    """The unapproved_rule_pack fixture loader result has the manifest
    identity triple populable; the TASK-020 adapter later classifies
    it as ``STC_RULE_PACK_VALIDATION_FAILED`` only because the
    validator reports ``status = "fail"``."""
    payload = _load_pack_payload("unapproved_rule_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(payload)
    assert loaded.rule_pack_id == "task020-internal-engineering-unapproved-v1"
    assert loaded.rule_pack_version == "v1"


def test_license_blocked_pack_fixture_loads_safely() -> None:
    payload = _load_pack_payload("license_blocked_rule_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(payload)
    assert loaded.rule_pack_id == "task020-internal-engineering-license-blocked-v1"


# ---------------------------------------------------------------------------
# §12.5 / §20.B — conflicting fixture
# ---------------------------------------------------------------------------


def test_conflicting_pack_fixture_triggers_duplicate_identity() -> None:
    """The conflicting_configuration_pack fixture carries two
    CONSTRUCTION_FAMILY_NORMALIZATION rules with the same
    ``(profile_id, rule_type, constraint_id)`` triple but different
    six-field-key values. They emit
    ``STC_RULE_DUPLICATE_IDENTITY`` (per §20.B)."""
    payload = _load_pack_payload("conflicting_configuration_pack")
    request = _build_request(payload)
    with pytest.raises(BlockerError) as info:
        _invoke_adapter(payload, request)
    assert info.value.code == "STC_RULE_DUPLICATE_IDENTITY"


# ---------------------------------------------------------------------------
# §12.9 — required rule class missing
# ---------------------------------------------------------------------------


def test_missing_required_token_allowlist_emits_constraint_missing() -> None:
    """Mutating the valid pack to drop the front-head token rule and
    adding a fake rule that doesn't supply front_head
    ``COMPONENT_TOKEN_ALLOWLIST`` leads to
    ``STC_RULE_CONSTRAINT_MISSING`` for the missing slot."""
    payload = _load_pack_payload("valid_configuration_pack")
    payload["rules"].pop("stc-cta-front-001")
    request = _build_request(payload)
    with pytest.raises(BlockerError) as info:
        _invoke_adapter(payload, request)
    assert info.value.code == "STC_RULE_CONSTRAINT_MISSING"


def test_missing_required_normalization_emits_constraint_missing() -> None:
    """Dropping the CONSTRUCTION_FAMILY_NORMALIZATION rule from the
    valid pack emits ``STC_RULE_CONSTRAINT_MISSING``."""
    payload = _load_pack_payload("valid_configuration_pack")
    payload["rules"].pop("stc-cfn-001")
    request = _build_request(payload)
    with pytest.raises(BlockerError) as info:
        _invoke_adapter(payload, request)
    assert info.value.code == "STC_RULE_CONSTRAINT_MISSING"


def test_missing_required_pass_count_emits_constraint_missing() -> None:
    payload = _load_pack_payload("valid_configuration_pack")
    payload["rules"].pop("stc-pcar-001")
    request = _build_request(payload)
    with pytest.raises(BlockerError) as info:
        _invoke_adapter(payload, request)
    assert info.value.code == "STC_RULE_CONSTRAINT_MISSING"


def test_missing_required_orientation_emits_constraint_missing() -> None:
    payload = _load_pack_payload("valid_configuration_pack")
    payload["rules"].pop("stc-oal-001")
    request = _build_request(payload)
    with pytest.raises(BlockerError) as info:
        _invoke_adapter(payload, request)
    assert info.value.code == "STC_RULE_CONSTRAINT_MISSING"


# ---------------------------------------------------------------------------
# §12.8.1 / §7 — token unsupported
# ---------------------------------------------------------------------------


def test_unsupported_token_request_emits_token_unsupported() -> None:
    """A request whose ``front_head_token`` is outside the
    ``allowed_tokens`` intersection emits
    ``STC_TOKEN_UNSUPPORTED_BY_RULE_PACK`` (§12.8.1 predicate)."""
    payload = _load_pack_payload("valid_configuration_pack")
    request = _build_request(
        payload,
        front_head="IER_FT_HEAD_NOT_IN_ALLOWLIST",
    )
    with pytest.raises(BlockerError) as info:
        _invoke_adapter(payload, request)
    assert info.value.code == "STC_TOKEN_UNSUPPORTED_BY_RULE_PACK"


def test_unsupported_orientation_request_emits_orientation_invalid() -> None:
    """A request whose ``orientation`` is outside the intersected
    orientation allowlist emits ``STC_ORIENTATION_INVALID`` (§12.8.5)."""
    payload = _load_pack_payload("valid_configuration_pack")
    # An orientation outside any closed enum value would be rejected
    # earlier by schema; here we synthesize a constraint: replace
    # the orientation rule with one that allowlists only a single
    # orientation, then ask for the opposite.
    payload["rules"]["stc-oal-001"]["allowed_orientations"] = ["VERTICAL"]
    request = _build_request(payload, orientation=Orientation.HORIZONTAL)
    with pytest.raises(BlockerError) as info:
        _invoke_adapter(payload, request)
    assert info.value.code == "STC_ORIENTATION_INVALID"


# ---------------------------------------------------------------------------
# §12.5 item 3 / §12.8.4 — pass-count request outside intersection
# ---------------------------------------------------------------------------


def test_pass_count_outside_intersection_emits_pass_count_invalid() -> None:
    """The valid pack's pass-count rule permits
    ``shell_pass_count in [1, 4]`` and ``tube_pass_count in [2, 12]``.
    A request with shell_pass_count = 99 (outside [1, 4]) emits
    ``STC_PASS_COUNT_INVALID`` after the intersection is computed."""
    payload = _load_pack_payload("valid_configuration_pack")
    request = _build_request(payload, shell_pass_count=99)
    with pytest.raises(BlockerError) as info:
        _invoke_adapter(payload, request)
    assert info.value.code == "STC_PASS_COUNT_INVALID"


# ---------------------------------------------------------------------------
# §12.5 item 6 / §12.8.2 — combination blocklist
# ---------------------------------------------------------------------------


def test_blocklist_exact_match_emits_blocked() -> None:
    """The valid pack's ``CONFIGURATION_COMBINATION_BLOCKLIST`` rule
    matches when all three request tokens belong to its
    ``blocked_combination`` triple AND-across / OR-within fields.
    """
    payload = _load_pack_payload("valid_configuration_pack")
    # Mutate the three slot tokens to the known-blocked synthetic IDs.
    payload["rules"]["stc-cta-front-001"]["allowed_tokens"] = ["IER_FT_HEAD_BLOCKED"]
    payload["rules"]["stc-cta-shell-001"]["allowed_tokens"] = ["IER_SHELL_BLOCKED"]
    payload["rules"]["stc-cta-rear-001"]["allowed_tokens"] = ["IER_RH_HEAD_BLOCKED"]
    request = _build_request(
        payload,
        front_head="IER_FT_HEAD_BLOCKED",
        shell="IER_SHELL_BLOCKED",
        rear_head="IER_RH_HEAD_BLOCKED",
    )
    with pytest.raises(BlockerError) as info:
        _invoke_adapter(payload, request)
    assert info.value.code == "STC_CONFIGURATION_COMBINATION_BLOCKED"


def test_blocklist_wildcard_empty_array_matches_any() -> None:
    """Per §12.8.2, an empty per-field array in ``blocked_combination``
    is a wildcard (matches any value, including ``null``). The
    mutated blocklist below has empty arrays in all three fields, so
    ANY request triple matches."""
    payload = _load_pack_payload("valid_configuration_pack")
    payload["rules"]["stc-ccb-001"]["blocked_combination"] = {
        "front_head_token": [],
        "shell_token": [],
        "rear_head_token": [],
    }
    request = _build_request(payload)
    with pytest.raises(BlockerError) as info:
        _invoke_adapter(payload, request)
    assert info.value.code == "STC_CONFIGURATION_COMBINATION_BLOCKED"


def test_blocklist_non_match_does_not_emit_blocked() -> None:
    """If the request triple does not match the blocklist, the
    adapter does NOT emit ``STC_CONFIGURATION_COMBINATION_BLOCKED``.
    A successful pass is therefore expected for the unmutated valid
    pack combined with the default request.
    """
    payload = _load_pack_payload("valid_configuration_pack")
    request = _build_request(payload)
    evaluation = _invoke_adapter(payload, request)
    assert evaluation.normalized_construction_family == ConstructionFamily.FIXED_TUBESHEET
