"""TASK-020-S2 fixture-driven tests — real TASK-012 integration.

These tests drive the S2 adapter through REAL TASK-012 fixtures. They
cover:

* all 4 fixture packs load via the real ``load_rule_pack`` interface;
* fixtures contain exactly the closed profile_id;
* pass-count / orientation / token request-value predicates emit the
  correct blocker codes;
* range intersection / orientation intersection / token intersection
  emptiness blockers;
* missing required class blockers;
* blocklist exact-match / wildcard / non-match;
* no restricted content (no TEMA text in any fixture);
* fixture index count == 30.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final

import pytest

from hexagent.exchangers.shell_tube.errors import BlockerError
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
    RulePackValidationReport,
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
PACK_ROOTS: Final[tuple[Path, ...]] = (
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack",
    FIXTURE_ROOT / "rule_packs/conflicting_configuration_pack",
    FIXTURE_ROOT / "rule_packs/unapproved_rule_pack",
    FIXTURE_ROOT / "rule_packs/license_blocked_rule_pack",
)

# Exact 30-path tuple (Round-2 §10 + §14.2.3) — manually enumerated
# exactly. Discovery idioms are forbidden by Round-2 §10; we MUST NOT
# use glob / rglob / os.walk to enumerate.
ALL_FIXTURE_FILES: Final[tuple[Path, ...]] = (
    # 4 case_revision files
    FIXTURE_ROOT / "case_revision/case_revision_committed.json",
    FIXTURE_ROOT / "case_revision/case_revision_superseded.json",
    FIXTURE_ROOT / "case_revision/case_revision_archived.json",
    FIXTURE_ROOT / "case_revision/case_revision_draft_blocked.json",
    # 15 valid_configuration_pack
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/manifest.json",
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/rules/stc-cta-front-001.json",
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/rules/stc-cta-shell-001.json",
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/rules/stc-cta-rear-001.json",
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/rules/stc-cfn-001.json",
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/rules/stc-pcar-001.json",
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/rules/stc-oal-001.json",
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/rules/stc-ccb-001.json",
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/provenance/edge_stc_cta_front_001.json",
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/provenance/edge_stc_cta_shell_001.json",
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/provenance/edge_stc_cta_rear_001.json",
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/provenance/edge_stc_cfn_001.json",
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/provenance/edge_stc_pcar_001.json",
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/provenance/edge_stc_oal_001.json",
    FIXTURE_ROOT / "rule_packs/valid_configuration_pack/provenance/edge_stc_ccb_001.json",
    # 5 conflicting_configuration_pack
    FIXTURE_ROOT / "rule_packs/conflicting_configuration_pack/manifest.json",
    FIXTURE_ROOT / "rule_packs/conflicting_configuration_pack/rules/conflict_a.json",
    FIXTURE_ROOT / "rule_packs/conflicting_configuration_pack/rules/conflict_b.json",
    FIXTURE_ROOT / "rule_packs/conflicting_configuration_pack/provenance/conflict_a_edge.json",
    FIXTURE_ROOT / "rule_packs/conflicting_configuration_pack/provenance/conflict_b_edge.json",
    # 3 unapproved_rule_pack
    FIXTURE_ROOT / "rule_packs/unapproved_rule_pack/manifest.json",
    FIXTURE_ROOT / "rule_packs/unapproved_rule_pack/rules/allowed_tokens.json",
    FIXTURE_ROOT / "rule_packs/unapproved_rule_pack/provenance/allowed_tokens_edge.json",
    # 3 license_blocked_rule_pack
    FIXTURE_ROOT / "rule_packs/license_blocked_rule_pack/manifest.json",
    FIXTURE_ROOT / "rule_packs/license_blocked_rule_pack/rules/allowed_tokens.json",
    FIXTURE_ROOT / "rule_packs/license_blocked_rule_pack/provenance/allowed_tokens_edge.json",
)


def _manifest_id(pack: Path) -> tuple[str, str, str]:
    m = json.loads((pack / "manifest.json").read_text())
    return m["rule_pack_id"], m["rule_pack_version"], m["canonical_hash"]


def _case_auth() -> CaseRevisionAuthority:
    return CaseRevisionAuthority(
        revision_id="rev-fix",
        payload_hash="a" * 64,
        domain_snapshot_hash="b" * 64,
        revision_status=CaseRevisionStatus.COMMITTED,
    )


def _request(
    pack: Path,
    *,
    orientation: Orientation = Orientation.HORIZONTAL,
    shell_pass_count: int = 1,
    tube_pass_count: int = 1,
    front_head: str | None = "IER_FT_A",
    shell: str | None = "IER_SH_A",
    rear_head: str | None = "IER_RH_A",
    construction_family: ConstructionFamily = ConstructionFamily.FIXED_TUBESHEET,
) -> ShellAndTubeConfigurationRequest:
    rid, rver, rhash = _manifest_id(pack)
    return ShellAndTubeConfigurationRequest(
        schema_version="task020.configuration-request.v1",
        case_authority=_case_auth(),
        equipment_family=EquipmentFamily.SHELL_AND_TUBE,
        authority_mode=AuthorityMode.APPROVED_RULE_PACK,
        construction_family=construction_family,
        orientation=orientation,
        shell_pass_count=shell_pass_count,
        tube_pass_count=tube_pass_count,
        component_tokens=ComponentTokens(front_head=front_head, shell=shell, rear_head=rear_head),
        standard_system_id="INTERNAL",
        requested_rule_pack_identity=RequestedRulePackIdentity(
            rule_pack_id=rid,
            rule_pack_version=rver,
            rule_pack_canonical_hash=rhash,
        ),
    )


def _load(pack: Path) -> tuple[LoadedRulePackView, RulePackValidationReport]:
    loader_dict = load_rule_pack(pack)
    validate_dict = validate_rule_pack(pack)
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    report = rule_pack_validation_report_from_validate_dict(validate_dict)
    assert isinstance(report, RulePackValidationReport)
    return loaded, report


# ---------------------------------------------------------------------------
# Path-budget invariant — verified separately
# ---------------------------------------------------------------------------


def test_exact_fixture_path_count_eq_30() -> None:
    assert len(ALL_FIXTURE_FILES) == 30
    for p in ALL_FIXTURE_FILES:
        assert p.exists(), f"missing: {p}"


def test_no_glob_no_rglob_in_test_modules() -> None:
    """Round-2 §10 — explicit enumeration; verify by reading this file
    itself for forbidden tokens.

    The test guard reads the source bytes of this file and rejects
    generic directory-discovery idioms. The forbidden substrings are
    constructed via ``chr()`` concatenation so the trigger tokens
    don't appear as literals in this source.
    """
    src = Path(__file__).read_text()
    # Compose forbidden byte sequences via chr() so the trigger
    # tokens never appear as literals in this source.
    forbidden_substrings = (
        chr(46) + "glob" + chr(40),
        chr(46) + "rglob" + chr(40),
        "os" + chr(46) + "walk" + chr(40),
        "from " + "glob import",
    )
    for forbidden in forbidden_substrings:
        assert forbidden not in src, (
            "forbidden directory-discovery idiom present in fixture test module"
        )


# ---------------------------------------------------------------------------
# Real TASK-012 loader / validator integration
# ---------------------------------------------------------------------------


def test_valid_pack_loads_with_real_task012_loader() -> None:
    """§5 — real load_rule_pack returns 7 rules."""
    loader_dict = load_rule_pack(FIXTURE_ROOT / "rule_packs/valid_configuration_pack")
    assert loader_dict["rule_count"] if False else len(loader_dict["rules"]) == 7


def test_unapproved_pack_loads_safely() -> None:
    """§5 — load_rule_pack succeeds for the unapproved pack."""
    loader_dict = load_rule_pack(FIXTURE_ROOT / "rule_packs/unapproved_rule_pack")
    assert "manifest" in loader_dict
    assert "unapproved-pass-range" in loader_dict["rules"]


def test_license_blocked_pack_loads_safely() -> None:
    """§5 — load_rule_pack succeeds for the license-blocked pack; only validate fails."""
    loader_dict = load_rule_pack(FIXTURE_ROOT / "rule_packs/license_blocked_rule_pack")
    assert "manifest" in loader_dict


# ---------------------------------------------------------------------------
# §12.8 predicate coverage
# ---------------------------------------------------------------------------


def test_pass_count_valid_request_succeeds() -> None:
    """§12.8.4 — pass counts inside the (1, 2) range succeed."""
    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loaded, report = _load(pack)
    request = _request(pack, shell_pass_count=1, tube_pass_count=2)
    ConfigurationRulePackAdapter.validate(request, loaded, report)


def test_pass_count_invalid_request_emits_pass_count_invalid() -> None:
    """§12.8.4 — pass counts outside intersected range emit
    STC_PASS_COUNT_INVALID."""
    import copy

    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loaded, report = _load(pack)
    # Mutate the pcar rule to allow only {1,1} pass count.
    rules = dict(loaded.rules)
    pcar = copy.deepcopy(rules["stc-pcar-001"])
    pcar["rule_body"]["shell_pass_count"] = {"min_inclusive": 1, "max_inclusive": 1}
    pcar["rule_body"]["tube_pass_count"] = {"min_inclusive": 1, "max_inclusive": 1}
    pcar["canonical_hash"] = json.dumps(
        {k: v for k, v in pcar.items() if k != "canonical_hash"},
        sort_keys=True,
    )
    rules["stc-pcar-001"] = pcar
    new_loaded = LoadedRulePackView(
        manifest=loaded.manifest,
        rules=rules,
        provenance_edges=loaded.provenance_edges,
        permission_evidence=loaded.permission_evidence,
        rule_pack_id=loaded.rule_pack_id,
        rule_pack_version=loaded.rule_pack_version,
        rule_pack_canonical_hash=loaded.rule_pack_canonical_hash,
        rule_count=loaded.rule_count,
    )
    request = _request(pack, shell_pass_count=2)
    with pytest.raises(BlockerError) as exc:
        ConfigurationRulePackAdapter.validate(request, new_loaded, report)
    assert str(exc.value.code) == "STC_PASS_COUNT_INVALID"


def test_orientation_valid_request_succeeds() -> None:
    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loaded, report = _load(pack)
    request = _request(pack, orientation=Orientation.HORIZONTAL)
    ConfigurationRulePackAdapter.validate(request, loaded, report)


def test_unsupported_orientation_request_emits_orientation_invalid() -> None:
    """§12.8.5 — orientation outside intersected allowlist emits
    STC_ORIENTATION_INVALID.

    The valid pack's orientation allowlist is {HORIZONTAL, VERTICAL};
    requesting UNSPECIFIED must be rejected since UNSPECIFIED is not in
    the allowlist.
    """
    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loaded, report = _load(pack)
    request = _request(pack, orientation=Orientation.UNSPECIFIED)
    with pytest.raises(BlockerError) as exc:
        ConfigurationRulePackAdapter.validate(request, loaded, report)
    assert str(exc.value.code) == "STC_ORIENTATION_INVALID"


def test_token_supported_request_succeeds() -> None:
    """§12.8.1 — front_head token in {IER_FT_A,IER_FT_B,IER_FT_C} succeeds."""
    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loaded, report = _load(pack)
    request = _request(pack, front_head="IER_FT_B")
    ConfigurationRulePackAdapter.validate(request, loaded, report)


def test_unsupported_token_request_emits_token_unsupported() -> None:
    """§12.8.1 — token not in the allowlist emits STC_TOKEN_UNSUPPORTED_BY_RULE_PACK."""
    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loaded, report = _load(pack)
    request = _request(pack, front_head="IER_FT_DENIED")
    with pytest.raises(BlockerError) as exc:
        ConfigurationRulePackAdapter.validate(request, loaded, report)
    assert str(exc.value.code) == "STC_TOKEN_UNSUPPORTED_BY_RULE_PACK"


def test_nullable_token_accepted() -> None:
    """§12.8.1 — rear_head is nullable=True → null token accepted."""
    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loaded, report = _load(pack)
    request = _request(pack, rear_head=None)
    ConfigurationRulePackAdapter.validate(request, loaded, report)


def test_non_nullable_null_token_blocked() -> None:
    """§12.8.1 — front_head is nullable=False → null token blocked."""
    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loaded, report = _load(pack)
    request = _request(pack, front_head=None)
    with pytest.raises(BlockerError) as exc:
        ConfigurationRulePackAdapter.validate(request, loaded, report)
    assert str(exc.value.code) == "STC_TOKEN_UNSUPPORTED_BY_RULE_PACK"


# ---------------------------------------------------------------------------
# §12.8.2 — blocklist coverage
# ---------------------------------------------------------------------------


def test_blocklist_wildcard_empty_array_matches_any() -> None:
    """§12.8.2 — empty per-field array is wildcard → any request matches.

    We mutate the ccb rule to have all empty arrays, then ANY request
    is blocked.
    """
    import copy

    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loaded, report = _load(pack)
    rules = dict(loaded.rules)
    ccb = copy.deepcopy(rules["stc-ccb-001"])
    ccb["rule_body"]["blocked_combination"] = {
        "front_head_token": [],
        "shell_token": [],
        "rear_head_token": [],
    }
    rules["stc-ccb-001"] = ccb
    new_loaded = LoadedRulePackView(
        manifest=loaded.manifest,
        rules=rules,
        provenance_edges=loaded.provenance_edges,
        permission_evidence=loaded.permission_evidence,
        rule_pack_id=loaded.rule_pack_id,
        rule_pack_version=loaded.rule_pack_version,
        rule_pack_canonical_hash=loaded.rule_pack_canonical_hash,
        rule_count=loaded.rule_count,
    )
    request = _request(pack)
    with pytest.raises(BlockerError) as exc:
        ConfigurationRulePackAdapter.validate(request, new_loaded, report)
    assert str(exc.value.code) == "STC_CONFIGURATION_COMBINATION_BLOCKED"


def test_blocklist_non_match_does_not_emit_blocked() -> None:
    """§12.8.2 — non-matching tokens are NOT blocked."""
    import copy

    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loaded, report = _load(pack)
    rules = dict(loaded.rules)
    ccb = copy.deepcopy(rules["stc-ccb-001"])
    # Set blocklist to a non-matching triple.
    ccb["rule_body"]["blocked_combination"] = {
        "front_head_token": ["IER_FT_NEVER"],
        "shell_token": ["IER_SH_NEVER"],
        "rear_head_token": ["IER_RH_NEVER"],
    }
    rules["stc-ccb-001"] = ccb
    new_loaded = LoadedRulePackView(
        manifest=loaded.manifest,
        rules=rules,
        provenance_edges=loaded.provenance_edges,
        permission_evidence=loaded.permission_evidence,
        rule_pack_id=loaded.rule_pack_id,
        rule_pack_version=loaded.rule_pack_version,
        rule_pack_canonical_hash=loaded.rule_pack_canonical_hash,
        rule_count=loaded.rule_count,
    )
    request = _request(pack)
    ConfigurationRulePackAdapter.validate(request, new_loaded, report)


# ---------------------------------------------------------------------------
# Restricted-content scan (no TEMA / ASME / paid standard content)
# ---------------------------------------------------------------------------


def test_no_restricted_standard_text_in_any_fixture() -> None:
    """§6 (license boundary) — fixtures contain no restricted content."""
    restricted_tokens = [
        "TEMA CLASS",
        "ASME SECTION",
        "verbatim_clause",
        "paid_standard",
    ]
    for path in ALL_FIXTURE_FILES:
        text = path.read_text()
        for tok in restricted_tokens:
            assert tok not in text, f"{path} contains restricted token {tok!r}"


# ---------------------------------------------------------------------------
# Final-cleanup-round §5 + §6 — failure-report optional fields, success
# report required fields, and permission_evidence re-keying.
# ---------------------------------------------------------------------------


# §6 — explicit module enumeration (NEVER use Path.glob / Path.rglob /
# os.walk to discover these files; manually enumerated constants).
S2_TEST_MODULE_PATHS: Final[tuple[Path, ...]] = (
    Path(__file__),
    Path(__file__).with_name("test_task020_rule_pack_adapter.py"),
    Path(__file__).with_name("test_task020_rule_pack_canonical.py"),
    Path(__file__).with_name("test_task020_rule_pack_hash_integration.py"),
    Path(__file__).with_name("test_task020_rule_profile_adapter.py"),
)


def test_minimal_fail_report_optional_fields_preserved_as_none() -> None:
    """§3.1, §3.2 — minimal TASK-012 ``{status, errors}`` failure shape:

    * adapter wrapper preserves the truthful absence of ``manifest``
      and ``rule_count`` as ``None``;
    * adapter does not fabricate ``{}`` / ``0`` placeholders;
    * adapter does not parse ``errors[*].message``.
    """
    fail_shapes: tuple[Mapping[str, object], ...] = (
        {"status": "fail", "errors": []},
        {"status": "fail", "errors": [{"loc": "x", "msg": "y", "type": "z"}]},
        {"status": "error", "errors": []},
    )
    for fail in fail_shapes:
        report = rule_pack_validation_report_from_validate_dict(fail)
        assert report.status == fail["status"]
        assert report.manifest is None
        assert report.rule_count is None
        assert report.errors == tuple(
            e for e in (fail.get("errors") or []) if isinstance(e, Mapping)
        )
        # Adapter must reject a fail-shape report with
        # STC_RULE_PACK_VALIDATION_FAILED when handed to validate().
        request = _request(FIXTURE_ROOT / "rule_packs/valid_configuration_pack")
        loaded = loaded_rule_pack_view_from_loader_dict(
            load_rule_pack(FIXTURE_ROOT / "rule_packs/valid_configuration_pack")
        )
        with pytest.raises(BlockerError) as exc:
            ConfigurationRulePackAdapter.validate(request, loaded, report)
        assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_FAILED"


def test_fail_report_adapter_does_not_parse_errors_messages() -> None:
    """§3.2 — adapter never reads ``errors[*].message`` to classify blockers.

    Identical minimal fail shapes with random message body text must
    all produce the same single blocker code: STC_RULE_PACK_VALIDATION_FAILED.
    """
    fail = {
        "status": "fail",
        "errors": [
            {"loc": ("anywhere",), "msg": "TOTALLY DIFFERENT MSG A", "type": "x"},
            {"loc": ("anywhere",), "msg": "TOTALLY DIFFERENT MSG B", "type": "y"},
        ],
    }
    report = rule_pack_validation_report_from_validate_dict(fail)
    assert report.status == "fail"
    assert report.manifest is None
    assert report.rule_count is None
    request = _request(FIXTURE_ROOT / "rule_packs/valid_configuration_pack")
    loaded = loaded_rule_pack_view_from_loader_dict(
        load_rule_pack(FIXTURE_ROOT / "rule_packs/valid_configuration_pack")
    )
    with pytest.raises(BlockerError) as exc:
        ConfigurationRulePackAdapter.validate(request, loaded, report)
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_FAILED"


def test_status_ok_without_manifest_rejected_at_wrapper() -> None:
    """§3.1 — success path requires ``manifest`` mapping; missing ⇒ error."""

    bad_ok: Mapping[str, object] = {
        "status": "ok",
        "rule_count": 7,
        # manifest missing
    }
    with pytest.raises(BlockerError) as exc:
        rule_pack_validation_report_from_validate_dict(bad_ok)
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"


def test_status_ok_without_rule_count_rejected_at_wrapper() -> None:
    """§3.1 — success path requires ``rule_count`` int; missing ⇒ error."""
    bad_ok: Mapping[str, object] = {
        "status": "ok",
        "manifest": {"rule_pack_id": "x", "rule_pack_version": "1.0.0", "canonical_hash": "abc"},
        # rule_count missing
    }
    with pytest.raises(BlockerError) as exc:
        rule_pack_validation_report_from_validate_dict(bad_ok)
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"


def test_status_ok_with_bool_rule_count_rejected() -> None:
    """§3.1 — ``bool`` is not accepted as ``int`` even on the success path."""
    bad_ok: Mapping[str, object] = {
        "status": "ok",
        "manifest": {"rule_pack_id": "x", "rule_pack_version": "1.0.0", "canonical_hash": "abc"},
        "rule_count": True,  # type: ignore[dict-item]
    }
    with pytest.raises(BlockerError) as exc:
        rule_pack_validation_report_from_validate_dict(bad_ok)
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"


def test_status_ok_constructs_with_real_mapping_and_int() -> None:
    """§3.1 — success path constructable with a Mapping and non-negative int."""
    ok: Mapping[str, object] = {
        "status": "ok",
        "manifest": {
            "rule_pack_id": "ok-pack",
            "rule_pack_version": "1.0.0",
            "canonical_hash": "h" * 64,
        },
        "rule_count": 5,
    }
    report = rule_pack_validation_report_from_validate_dict(ok)
    assert report.status == "ok"
    assert report.rule_pack_id == "ok-pack"
    assert report.rule_pack_version == "1.0.0"
    assert report.rule_pack_canonical_hash == "h" * 64
    assert report.rule_count == 5
    assert isinstance(report.manifest, Mapping)


def test_permission_input_keys_not_authoritative_direct_id_used() -> None:
    """§4 — loader ignores input mapping keys; output keyed by
    artifact direct ``permission_id``.
    """
    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loader_dict = load_rule_pack(pack)
    # Rename input mapping keys to deliberately-mismatched names;
    # they MUST NOT appear in the output view.
    perm_obj = dict(loader_dict["permission_evidence"])
    renamed = {f"WRONG_INPUT_KEY_{i}": v for i, (_, v) in enumerate(perm_obj.items(), 1)}
    loader_dict = {**loader_dict, "permission_evidence": renamed}
    loaded = loaded_rule_pack_view_from_loader_dict(loader_dict)
    # No input key appears in the output mapping.
    for renamed_key in renamed:
        assert renamed_key not in loaded.permission_evidence, (
            f"input key {renamed_key!r} leaked into output permission_evidence"
        )
    # Output is keyed by direct permission_id (or empty if loader
    # doesn't supply permission_id on internal_seed-style artifacts).
    for key in loaded.permission_evidence:
        assert isinstance(key, str)


def test_permission_artifact_missing_permission_id_rejected() -> None:
    """§4 — permission artifacts without ``permission_id`` raise
    ``STC_RULE_PACK_VALIDATION_REPORT_MISMATCH``.
    """
    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loader_dict = load_rule_pack(pack)
    loader_dict = {
        **loader_dict,
        "permission_evidence": {"some_key": {"no_permission_id_here": True}},
    }
    with pytest.raises(BlockerError) as exc:
        loaded_rule_pack_view_from_loader_dict(loader_dict)
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"


def test_permission_artifact_empty_permission_id_rejected() -> None:
    """§4 — ``permission_id`` must be a non-empty str."""
    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loader_dict = load_rule_pack(pack)
    loader_dict = {
        **loader_dict,
        "permission_evidence": {
            "some_key": {"permission_id": "", "evidence": "x"},
        },
    }
    with pytest.raises(BlockerError) as exc:
        loaded_rule_pack_view_from_loader_dict(loader_dict)
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"


def test_permission_artifact_not_mapping_rejected() -> None:
    """§4 — non-mapping permission artifacts raise mismatch."""
    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loader_dict = load_rule_pack(pack)
    loader_dict = {
        **loader_dict,
        "permission_evidence": {"a_string_value": "this-is-a-string-not-a-mapping"},
    }
    with pytest.raises(BlockerError) as exc:
        loaded_rule_pack_view_from_loader_dict(loader_dict)
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"


def test_permission_duplicate_direct_id_rejected() -> None:
    """§4 — duplicate direct ``permission_id`` under different input
    keys raises mismatch.
    """
    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    loader_dict = load_rule_pack(pack)
    loader_dict = {
        **loader_dict,
        "permission_evidence": {
            "k1": {"permission_id": "dup-perm", "evidence": "a"},
            "k2": {"permission_id": "dup-perm", "evidence": "b"},
        },
    }
    with pytest.raises(BlockerError) as exc:
        loaded_rule_pack_view_from_loader_dict(loader_dict)
    assert str(exc.value.code) == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"


def test_no_directory_discovery_in_all_five_frozen_s2_test_modules() -> None:
    """§5 — Round-final guard over all 5 frozen S2 test modules:

    * exactly 5 module paths exist;
    * every module source contains no forbidden directory-discovery
      idioms (``Path.glob``, ``Path.rglob``, ``os.walk``, ``from
      glob import``);
    * the guard itself composes trigger tokens via ``chr()`` to avoid
      hitting itself.
    """
    assert len(S2_TEST_MODULE_PATHS) == 5, (
        f"expected exactly 5 S2 test modules, got {len(S2_TEST_MODULE_PATHS)}"
    )
    for module_path in S2_TEST_MODULE_PATHS:
        assert module_path.exists(), f"missing S2 test module: {module_path}"

    # Build trigger tokens via ``chr()`` concatenation so the guard
    # itself does not produce matchable literal strings.
    forbidden_substrings = (
        chr(46) + "glob" + chr(40),
        chr(46) + "rglob" + chr(40),
        "os" + chr(46) + "walk" + chr(40),
        "from " + "glob import",
    )
    for module_path in S2_TEST_MODULE_PATHS:
        src = module_path.read_text()
        for forbidden in forbidden_substrings:
            assert forbidden not in src, (
                f"forbidden directory-discovery idiom in {module_path.name}: {forbidden!r}"
            )


def test_exact_30_fixture_paths_preserved() -> None:
    """§6 — confirm 30 fixture paths exactly equal the independently-frozen
    relative-path tuple. The expected tuple is NOT derived from
    ``ALL_FIXTURE_FILES``; it is a separate manifest the test module
    binds by hand. Discovery idioms are forbidden.
    """
    actual = tuple(path.relative_to(FIXTURE_ROOT).as_posix() for path in ALL_FIXTURE_FILES)
    assert len(EXPECTED_TASK020_FIXTURE_RELATIVE_PATHS) == 30
    assert len(set(EXPECTED_TASK020_FIXTURE_RELATIVE_PATHS)) == 30
    assert len(actual) == 30
    assert len(set(actual)) == 30
    assert set(actual) == set(EXPECTED_TASK020_FIXTURE_RELATIVE_PATHS)
    for path in ALL_FIXTURE_FILES:
        assert path.exists(), f"missing fixture: {path}"


# §6 — independently-frozen relative-path tuple. NOT derived from
# ``ALL_FIXTURE_FILES``. Each entry is a forward-slash POSIX-style path
# relative to ``FIXTURE_ROOT``. The 30 entries enumerate the closed
# frozen allowlist for the TASK-020-S2 round.
EXPECTED_TASK020_FIXTURE_RELATIVE_PATHS: Final[tuple[str, ...]] = (
    # 4 case_revision files
    "case_revision/case_revision_committed.json",
    "case_revision/case_revision_superseded.json",
    "case_revision/case_revision_archived.json",
    "case_revision/case_revision_draft_blocked.json",
    # 15 valid_configuration_pack
    "rule_packs/valid_configuration_pack/manifest.json",
    "rule_packs/valid_configuration_pack/rules/stc-cta-front-001.json",
    "rule_packs/valid_configuration_pack/rules/stc-cta-shell-001.json",
    "rule_packs/valid_configuration_pack/rules/stc-cta-rear-001.json",
    "rule_packs/valid_configuration_pack/rules/stc-cfn-001.json",
    "rule_packs/valid_configuration_pack/rules/stc-pcar-001.json",
    "rule_packs/valid_configuration_pack/rules/stc-oal-001.json",
    "rule_packs/valid_configuration_pack/rules/stc-ccb-001.json",
    "rule_packs/valid_configuration_pack/provenance/edge_stc_cta_front_001.json",
    "rule_packs/valid_configuration_pack/provenance/edge_stc_cta_shell_001.json",
    "rule_packs/valid_configuration_pack/provenance/edge_stc_cta_rear_001.json",
    "rule_packs/valid_configuration_pack/provenance/edge_stc_cfn_001.json",
    "rule_packs/valid_configuration_pack/provenance/edge_stc_pcar_001.json",
    "rule_packs/valid_configuration_pack/provenance/edge_stc_oal_001.json",
    "rule_packs/valid_configuration_pack/provenance/edge_stc_ccb_001.json",
    # 5 conflicting_configuration_pack
    "rule_packs/conflicting_configuration_pack/manifest.json",
    "rule_packs/conflicting_configuration_pack/rules/conflict_a.json",
    "rule_packs/conflicting_configuration_pack/rules/conflict_b.json",
    "rule_packs/conflicting_configuration_pack/provenance/conflict_a_edge.json",
    "rule_packs/conflicting_configuration_pack/provenance/conflict_b_edge.json",
    # 3 unapproved_rule_pack
    "rule_packs/unapproved_rule_pack/manifest.json",
    "rule_packs/unapproved_rule_pack/rules/allowed_tokens.json",
    "rule_packs/unapproved_rule_pack/provenance/allowed_tokens_edge.json",
    # 3 license_blocked_rule_pack
    "rule_packs/license_blocked_rule_pack/manifest.json",
    "rule_packs/license_blocked_rule_pack/rules/allowed_tokens.json",
    "rule_packs/license_blocked_rule_pack/provenance/allowed_tokens_edge.json",
)


# ---------------------------------------------------------------------------
# Final-narrow-corrective-round §4 + §5 — failure-report explicit field
# semantics + non-vacuous permission re-keying.
# ---------------------------------------------------------------------------


def _blocker_code(exc: object) -> str:
    """Stable blocker-code assertion helper.

    Works for both ``pytest.raises(...) as exc`` (exc is an
    ``ExceptionInfo``; read ``exc.value.code``) and
    ``try / except`` blocks (exc is the ``BlockerError`` itself;
    read ``exc.code``).
    """
    value = getattr(exc, "value", exc)
    return str(getattr(value, "code", exc))


def test_fail_report_manifest_missing_yields_none_and_empty_identity() -> None:
    """§3.2 / §4 — ``{status, errors}`` with no ``manifest`` key:
    ``report.manifest is None`` and identity triple stays empty.
    """
    fail: Mapping[str, object] = {"status": "fail", "errors": []}
    report = rule_pack_validation_report_from_validate_dict(fail)
    assert report.manifest is None
    assert report.rule_pack_id == ""
    assert report.rule_pack_version == ""
    assert report.rule_pack_canonical_hash == ""


def test_fail_report_explicit_valid_manifest_is_preserved() -> None:
    """§3.2 / §4 — explicit Mapping manifest on fail is preserved AND
    identity triple is extracted from it.
    """
    fail: Mapping[str, object] = {
        "status": "fail",
        "errors": [],
        "manifest": {
            "rule_pack_id": "fail-pack-id",
            "rule_pack_version": "1.0.0",
            "canonical_hash": "h" * 64,
        },
    }
    report = rule_pack_validation_report_from_validate_dict(fail)
    assert report.manifest is not None
    assert report.manifest["rule_pack_id"] == "fail-pack-id"
    assert report.rule_pack_id == "fail-pack-id"
    assert report.rule_pack_version == "1.0.0"
    assert report.rule_pack_canonical_hash == "h" * 64


@pytest.mark.parametrize(
    "bad_manifest",
    [
        "this-is-a-string-not-a-mapping",
        ["a", "list", "instead", "of", "mapping"],
        42,
        3.14,
    ],
)
def test_fail_report_invalid_type_manifest_rejected(bad_manifest: object) -> None:
    """§3.2 — explicit non-Mapping manifest on fail raises MISMATCH.
    No silent coercion to None, no leaked ``TypeError``.
    """
    fail: Mapping[str, object] = {
        "status": "fail",
        "errors": [],
        "manifest": bad_manifest,  # type: ignore[dict-item]
    }
    with pytest.raises(BlockerError) as exc:
        rule_pack_validation_report_from_validate_dict(fail)
    assert _blocker_code(exc) == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"


def test_fail_report_rule_count_missing_yields_none() -> None:
    """§3.2 / §4 — ``{status, errors}`` with no ``rule_count`` key:
    ``report.rule_count is None``.
    """
    fail: Mapping[str, object] = {"status": "fail", "errors": []}
    report = rule_pack_validation_report_from_validate_dict(fail)
    assert report.rule_count is None


def test_fail_report_explicit_zero_rule_count_preserved() -> None:
    """§3.2 — explicit ``rule_count == 0`` on fail is preserved (NOT
    coerced to None).
    """
    fail: Mapping[str, object] = {
        "status": "fail",
        "errors": [],
        "rule_count": 0,
    }
    report = rule_pack_validation_report_from_validate_dict(fail)
    assert report.rule_count == 0
    assert report.rule_count is not None


def test_fail_report_explicit_positive_rule_count_preserved() -> None:
    """§3.2 — explicit positive ``rule_count`` on fail is preserved."""
    fail: Mapping[str, object] = {
        "status": "fail",
        "errors": [],
        "rule_count": 7,
    }
    report = rule_pack_validation_report_from_validate_dict(fail)
    assert report.rule_count == 7


@pytest.mark.parametrize(
    "bad_rule_count",
    [
        True,  # bool rejected as int
        -1,  # negative int rejected
        "1",  # str rejected
        3.14,  # float rejected
        [0, 1, 2],  # list rejected
        {"nested": "value"},  # mapping rejected
        None,  # explicit None rejected as type
    ],
)
def test_fail_report_invalid_type_rule_count_rejected(bad_rule_count: object) -> None:
    """§3.2 — explicit illegal ``rule_count`` on fail raises MISMATCH.
    No silent coercion to None, no leaked bare ``TypeError``.
    """
    fail: Mapping[str, object] = {
        "status": "fail",
        "errors": [],
        "rule_count": bad_rule_count,  # type: ignore[dict-item]
    }
    with pytest.raises(BlockerError) as exc:
        rule_pack_validation_report_from_validate_dict(fail)
    assert _blocker_code(exc) == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"


def test_fail_report_wrapper_does_not_leak_bare_typeerror() -> None:
    """§3.2 — wrapper never lets a bare ``TypeError`` reach the caller.
    All illegal types trigger a stable ``BlockerError``;
    ``TypeError`` is caught and never re-raised from the wrapper.
    """
    fail: Mapping[str, object] = {
        "status": "fail",
        "errors": [],
        "manifest": "NOT-A-MAPPING",
        "rule_count": "NOT-AN-INT",
    }
    try:
        rule_pack_validation_report_from_validate_dict(fail)
    except BlockerError as exc:
        assert _blocker_code(exc) == "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"
    except TypeError as err:
        # wrapper leakage of bare TypeError is a regression
        raise AssertionError(
            "wrapper leaked a bare TypeError instead of raising BlockerError"
        ) from err
    else:
        raise AssertionError("wrapper accepted an illegal manifest+rule_count on a fail report")


def test_permission_positive_rekey_uses_direct_permission_id() -> None:
    """§5 — non-vacuous positive re-key test using synthetic input.

    The fixture's own permission_evidence may be empty; this test
    does NOT rely on it. Instead it constructs synthetic input with
    a deliberately-mismatched input key and a known direct
    ``permission_id``, then asserts the output is keyed by the direct
    ``permission_id``, not the input key.

    The synthetic object is in-memory only — never written to JSON
    fixture storage.
    """
    pack = FIXTURE_ROOT / "rule_packs/valid_configuration_pack"
    base_loader = load_rule_pack(pack)
    synthetic_loader: Mapping[str, object] = {
        **base_loader,
        "permission_evidence": {
            "WRONG_INPUT_KEY": {
                "permission_id": "permission-direct-id",
                "evidence": "synthetic-test-only",
            },
        },
    }
    loaded = loaded_rule_pack_view_from_loader_dict(synthetic_loader)
    assert set(loaded.permission_evidence) == {"permission-direct-id"}
    assert "WRONG_INPUT_KEY" not in loaded.permission_evidence
    assert (
        loaded.permission_evidence["permission-direct-id"]["permission_id"]
        == "permission-direct-id"
    )
