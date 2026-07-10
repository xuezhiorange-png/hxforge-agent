"""TASK-020 domain model tests — Slice A.

Asserts the §7 / §9 frozen value-object contract. Tests do NOT
exercise any engineering numerical behavior.
"""

from __future__ import annotations

import dataclasses

import pytest

from hexagent.exchangers.shell_tube.models import (
    DEFERRED_CAPABILITIES,
    AuthorityMode,
    BlockerCode,
    CaseRevisionAuthority,
    CaseRevisionStatus,
    ComponentTokens,
    ConfigurationAuthorityBinding,
    ConfigurationValidationResult,
    ConstructionFamily,
    EquipmentFamily,
    ErrorEntry,
    EvaluatedRulePackAuthority,
    Orientation,
    SelectedRuleAuthority,
    ShellAndTubeConfiguration,
    ShellAndTubeConfigurationRequest,
    StandardClaimStatus,
    ValidationStatus,
    WarningCode,
)

SHA_PAYLOAD = "a" * 64
SHA_DOMAIN = "b" * 64
SHA_RULE_PACK = "c" * 64


def _make_case_authority(**overrides: object) -> CaseRevisionAuthority:
    """Return a fresh valid CaseRevisionAuthority."""
    return CaseRevisionAuthority(
        revision_id=str(overrides.get("revision_id", "rev-001")),
        payload_hash=str(overrides.get("payload_hash", SHA_PAYLOAD)),
        domain_snapshot_hash=str(overrides.get("domain_snapshot_hash", SHA_DOMAIN)),
        revision_status=CaseRevisionStatus(str(overrides.get("revision_status", "committed"))),
    )


class TestCaseRevisionAuthority:
    def test_valid_authority_constructs(self) -> None:
        cra = _make_case_authority()
        assert cra.revision_id == "rev-001"
        assert cra.payload_hash == SHA_PAYLOAD
        assert cra.domain_snapshot_hash == SHA_DOMAIN
        assert cra.revision_status == CaseRevisionStatus.COMMITTED

    def test_authority_is_frozen(self) -> None:
        cra = _make_case_authority()
        with pytest.raises(dataclasses.FrozenInstanceError):
            cra.revision_id = "rev-002"  # type: ignore[misc]

    def test_authority_rejects_non_string_revision_id(self) -> None:
        with pytest.raises(TypeError):
            CaseRevisionAuthority(
                revision_id=123,  # type: ignore[arg-type]
                payload_hash=SHA_PAYLOAD,
                domain_snapshot_hash=SHA_DOMAIN,
                revision_status=CaseRevisionStatus.COMMITTED,
            )

    def test_authority_rejects_unknown_status(self) -> None:
        with pytest.raises(ValueError):
            CaseRevisionStatus("draft")  # not in accepted subset

    def test_authority_accepted_status_subset(self) -> None:
        for status in ("committed", "superseded", "archived"):
            CaseRevisionStatus(status)  # no raise


class TestRequestModel:
    def test_request_is_frozen(self) -> None:
        request = ShellAndTubeConfigurationRequest(
            schema_version="task020.configuration-request.v1",
            case_authority=_make_case_authority(),
            equipment_family=EquipmentFamily.SHELL_AND_TUBE,
            authority_mode=AuthorityMode.INTERNAL_GENERIC,
            construction_family=ConstructionFamily.FIXED_TUBESHEET,
            orientation=Orientation.HORIZONTAL,
            shell_pass_count=1,
            tube_pass_count=2,
            component_tokens=ComponentTokens(front_head="A", shell="B", rear_head="C"),
            standard_system_id=None,
            requested_rule_pack_identity=None,
            evidence_refs=(),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            request.shell_pass_count = 99  # type: ignore[misc]

    def test_request_evidence_refs_normalized_to_tuple(self) -> None:
        request = ShellAndTubeConfigurationRequest(
            schema_version="task020.configuration-request.v1",
            case_authority=_make_case_authority(),
            equipment_family=EquipmentFamily.SHELL_AND_TUBE,
            authority_mode=AuthorityMode.INTERNAL_GENERIC,
            construction_family=ConstructionFamily.FIXED_TUBESHEET,
            orientation=Orientation.HORIZONTAL,
            shell_pass_count=1,
            tube_pass_count=2,
            component_tokens=ComponentTokens(front_head=None, shell=None, rear_head=None),
            standard_system_id=None,
            requested_rule_pack_identity=None,
            evidence_refs=("ref-c", "ref-a", "ref-b"),
        )
        # The constructor does not sort; the canonicalizer does.
        # Here we test that the type is a tuple (immutable) and the
        # elements are preserved in input order.
        assert isinstance(request.evidence_refs, tuple)
        assert tuple(request.evidence_refs) == ("ref-c", "ref-a", "ref-b")


class TestConfigurationModel:
    def test_configuration_carries_deferred_capabilities(self) -> None:
        request = ShellAndTubeConfigurationRequest(
            schema_version="task020.configuration-request.v1",
            case_authority=_make_case_authority(),
            equipment_family=EquipmentFamily.SHELL_AND_TUBE,
            authority_mode=AuthorityMode.INTERNAL_GENERIC,
            construction_family=ConstructionFamily.FIXED_TUBESHEET,
            orientation=Orientation.HORIZONTAL,
            shell_pass_count=1,
            tube_pass_count=2,
            component_tokens=ComponentTokens(front_head=None, shell=None, rear_head=None),
            standard_system_id=None,
            requested_rule_pack_identity=None,
            evidence_refs=(),
        )
        binding = ConfigurationAuthorityBinding(
            authority_mode=AuthorityMode.INTERNAL_GENERIC,
            standard_system_id=None,
            case_authority=request.case_authority,
            evaluated_rule_pack_authority=None,
            case_authority_evidence_refs=(),
        )
        configuration = ShellAndTubeConfiguration(
            schema_version="task020.configuration.v1",
            configuration_id="00000000-0000-5000-8000-000000000000",
            configuration_hash="0" * 64,
            equipment_family=request.equipment_family,
            authority_mode=request.authority_mode,
            standard_claim_status=StandardClaimStatus.NO_STANDARD_CLAIM,
            construction_family=request.construction_family,
            orientation=request.orientation,
            shell_pass_count=request.shell_pass_count,
            tube_pass_count=request.tube_pass_count,
            component_tokens=request.component_tokens,
            authority_binding=binding,
            case_authority=request.case_authority,
            warnings=(),
            blockers=(),
        )
        # §9.3 closed initial deferred_capabilities set is bound
        # to the configuration by default.
        assert configuration.deferred_capabilities == DEFERRED_CAPABILITIES
        assert "TUBE_LAYOUT_NOT_COMPUTABLE" in configuration.deferred_capabilities
        assert "PRESSURE_DROP_NOT_COMPUTABLE" in configuration.deferred_capabilities


class TestErrorEntry:
    def test_error_entry_is_frozen(self) -> None:
        entry = ErrorEntry(
            code="STC_UNKNOWN_FIELD",
            field_path="case_authority",
            message_key="STC_UNKNOWN_FIELD",
            evidence_refs=(),
            details=None,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            entry.code = "STC_OTHER"  # type: ignore[misc]

    def test_error_entry_default_evidence_refs_is_empty_tuple(self) -> None:
        entry = ErrorEntry(code="STC_X", field_path=None, message_key="STC_X")
        assert entry.evidence_refs == ()


class TestBlockerCode:
    def test_blocker_code_values_are_stc_prefixed(self) -> None:
        for code in BlockerCode:
            assert code.value.startswith("STC_"), code.value

    def test_known_blockers_present(self) -> None:
        expected = {
            "STC_SCHEMA_VERSION_UNSUPPORTED",
            "STC_UNKNOWN_FIELD",
            "STC_CASE_AUTHORITY_MISSING",
            "STC_CASE_REVISION_STATUS_BLOCKED",
            "STC_CASE_PAYLOAD_HASH_INVALID",
            "STC_CASE_DOMAIN_SNAPSHOT_HASH_INVALID",
            "STC_CASE_REVISION_ID_MISSING",
            "STC_EQUIPMENT_FAMILY_INVALID",
            "STC_AUTHORITY_MODE_INVALID",
            "STC_CONSTRUCTION_FAMILY_INVALID",
            "STC_ORIENTATION_INVALID",
            "STC_PASS_COUNT_INVALID",
            "STC_TOKEN_MALFORMED",
            "STC_AUTHORITY_FIELDS_INCONSISTENT",
            "STC_RULE_PACK_REQUIRED",
        }
        actual = {c.value for c in BlockerCode}
        for s in expected:
            assert s in actual, f"missing {s}"

    def test_obsolete_blocker_codes_absent(self) -> None:
        """P1-5: STC_RULE_PROFILE_UNRECOGNIZED and
        STC_RULE_PRIORITY_CONFLICT must NOT be in the active closed
        set."""
        actual = {c.value for c in BlockerCode}
        assert "STC_RULE_PROFILE_UNRECOGNIZED" not in actual
        assert "STC_RULE_PRIORITY_CONFLICT" not in actual


class TestWarningCode:
    def test_warning_code_values_are_stc_prefixed(self) -> None:
        for code in WarningCode:
            assert code.value.startswith("STC_"), code.value


class TestSelectedRuleAuthority:
    def test_8_fields_required(self) -> None:
        with pytest.raises(TypeError):
            SelectedRuleAuthority(  # type: ignore[call-arg]
                rule_id="r1",
                rule_version="v1",
                rule_artifact_canonical_hash=SHA_RULE_PACK,
            )

    def test_default_evidence_refs_and_provenance_edge_ids_empty(self) -> None:
        sra = SelectedRuleAuthority(
            rule_id="r1",
            rule_version="v1",
            rule_artifact_canonical_hash=SHA_RULE_PACK,
            source_class="STANDARD",
            license_evidence={"license_id": "X"},
            approval_status="approved",
        )
        assert sra.provenance_edge_ids == ()
        assert sra.evidence_refs == ()

    def test_is_frozen(self) -> None:
        sra = SelectedRuleAuthority(
            rule_id="r1",
            rule_version="v1",
            rule_artifact_canonical_hash=SHA_RULE_PACK,
            source_class="STANDARD",
            license_evidence=None,
            approval_status="approved",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            sra.rule_id = "r2"  # type: ignore[misc]


class TestEvaluatedRulePackAuthority:
    def test_default_selected_rule_authorities_empty(self) -> None:
        rpa = EvaluatedRulePackAuthority(
            rule_pack_id="rp1",
            rule_pack_version="v1",
            rule_pack_canonical_hash=SHA_RULE_PACK,
            validation_status="ok",
        )
        assert rpa.selected_rule_authorities == ()


class TestFrozenShape:
    def test_validation_result_status_valid_carries_configuration(
        self,
    ) -> None:
        cra = _make_case_authority()
        binding = ConfigurationAuthorityBinding(
            authority_mode=AuthorityMode.INTERNAL_GENERIC,
            standard_system_id=None,
            case_authority=cra,
            evaluated_rule_pack_authority=None,
            case_authority_evidence_refs=(),
        )
        configuration = ShellAndTubeConfiguration(
            schema_version="task020.configuration.v1",
            configuration_id="00000000-0000-5000-8000-000000000000",
            configuration_hash="0" * 64,
            equipment_family=EquipmentFamily.SHELL_AND_TUBE,
            authority_mode=AuthorityMode.INTERNAL_GENERIC,
            standard_claim_status=StandardClaimStatus.NO_STANDARD_CLAIM,
            construction_family=ConstructionFamily.FIXED_TUBESHEET,
            orientation=Orientation.HORIZONTAL,
            shell_pass_count=1,
            tube_pass_count=2,
            component_tokens=ComponentTokens(front_head=None, shell=None, rear_head=None),
            authority_binding=binding,
            case_authority=cra,
            warnings=(),
            blockers=(),
        )
        result = ConfigurationValidationResult(
            status=ValidationStatus.VALID,
            configuration=configuration,
        )
        assert result.status == ValidationStatus.VALID
        assert result.configuration is configuration

    def test_validation_result_status_blocked_carries_no_configuration(
        self,
    ) -> None:
        blockers = (
            ErrorEntry(
                code="STC_RULE_PACK_REQUIRED",
                field_path="authority_mode",
                message_key="STC_RULE_PACK_REQUIRED",
                evidence_refs=(),
            ),
        )
        result = ConfigurationValidationResult(
            status=ValidationStatus.BLOCKED,
            configuration=None,
            blockers=blockers,
        )
        assert result.status == ValidationStatus.BLOCKED
        assert result.configuration is None
        assert len(result.blockers) == 1
