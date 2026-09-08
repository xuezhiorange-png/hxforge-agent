"""TASK-167 fail-closed validation and screening service."""

from __future__ import annotations

import uuid
from dataclasses import replace
from decimal import Decimal, DecimalException
from typing import Any

from hexagent.exchangers.shell_tube import canonical as task020_canonical
from hexagent.exchangers.shell_tube.bell_delaware import authority as task166_authority
from hexagent.exchangers.shell_tube.bell_delaware import canonical as task166_canonical
from hexagent.exchangers.shell_tube.bell_delaware.models import Task166Result
from hexagent.exchangers.shell_tube.models import ShellAndTubeConfiguration
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    IMPLEMENTATION_SOFTWARE_VERSION as TASK026_IMPL_VERSION,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    SCHEMA_VERSION as TASK026_SCHEMA_VERSION,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    TASK026_VERSION,
    PhaseRegion,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.property_snapshot import PropertySnapshot
from hexagent.exchangers.shell_tube.tube_side_thermal.provenance import FrozenProvenance
from hexagent.exchangers.shell_tube.tube_side_thermal.request import TubeSideThermalRequest
from hexagent.exchangers.shell_tube.tube_side_thermal.result import TubeSideThermalResult
from hexagent.exchangers.shell_tube.tube_side_thermal.single_phase import SinglePhaseOutputs
from hexagent.exchangers.shell_tube.tube_side_thermal.stage_pipeline import (
    RESULT_ID_NAME_PREFIX as TASK026_RESULT_ID_PREFIX,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.stage_pipeline import (
    RESULT_ID_NAMESPACE as TASK026_RESULT_ID_NAMESPACE,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.stage_pipeline import (
    _compute_success_result_hash as task026_success_hash,
)

from . import authority
from .canonical import (
    blocked_hash,
    blocked_id,
    raw_blocked_hash,
    raw_blocked_id,
    request_hash,
    result_hash,
    result_id,
    sha256_domain_hex,
)
from .cleanability import build_cleanability_screen
from .construction import build_construction_screen
from .erosion import build_erosion_screen
from .errors import Blocker, BlockerCode, FailureStage, ScreeningFailure, WarningCode
from .models import (
    ApplicabilityCheck,
    ApplicabilityLedger,
    CompletenessLedger,
    ScreenRecord,
    ScreenStatus,
    Task167BlockedResult,
    Task167RawBoundaryBlockedResult,
    Task167Request,
    Task167Result,
    Task167ValidationResult,
    ValidationStatus,
)
from .provenance import build_provenance, semantic_input_hashes
from .raw_projection import RawProjectionFailure, project_raw
from .rule_pack import validate_approved_rule_pack
from .schema import SchemaFailure, parse_request
from .thermal_expansion import build_thermal_expansion_screen
from .velocity import build_velocity_screens
from .vibration import build_fiv_screen


def _blocker(
    code: BlockerCode,
    stage: FailureStage,
    field_path: str | None = None,
    message: str = "",
    evidence_refs: tuple[str, ...] = (),
) -> Blocker:
    return Blocker(
        code=code, stage=stage, field_path=field_path, message=message, evidence_refs=evidence_refs
    )


def _typed_branch(request_hash_value: str, blockers: list[Blocker]) -> Task167ValidationResult:
    item = Task167BlockedResult(
        request_hash=request_hash_value,
        blockers=tuple(blockers),
    )
    item = replace(item, result_hash=blocked_hash(item))
    item = replace(item, result_id=blocked_id(item.result_hash))
    return Task167ValidationResult(status=ValidationStatus.TYPED_BLOCKED, typed_blocked=item)


def _raw_branch(code: BlockerCode, projection_hash: str) -> Task167ValidationResult:
    item = Task167RawBoundaryBlockedResult(
        raw_request_projection_hash=projection_hash,
        blockers=(_blocker(code, FailureStage.RAW_BOUNDARY),),
    )
    item = replace(item, result_hash=raw_blocked_hash(item))
    item = replace(item, result_id=raw_blocked_id(item.result_hash))
    return Task167ValidationResult(
        status=ValidationStatus.RAW_BOUNDARY_BLOCKED,
        raw_boundary_blocked=item,
    )


def _configuration_replay(configuration: ShellAndTubeConfiguration) -> bool:
    """Replay the existing TASK-020 canonical configuration identity."""
    try:
        config = {
            "equipment_family": configuration.equipment_family.value,
            "authority_mode": configuration.authority_mode.value,
            "standard_claim_status": configuration.standard_claim_status.value,
            "construction_family": configuration.construction_family.value,
            "orientation": configuration.orientation.value,
            "shell_pass_count": configuration.shell_pass_count,
            "tube_pass_count": configuration.tube_pass_count,
            "component_tokens": {
                "front_head": configuration.component_tokens.front_head,
                "shell": configuration.component_tokens.shell,
                "rear_head": configuration.component_tokens.rear_head,
            },
        }
        case = {
            "revision_id": configuration.case_authority.revision_id,
            "payload_hash": configuration.case_authority.payload_hash,
            "domain_snapshot_hash": configuration.case_authority.domain_snapshot_hash,
            "revision_status": configuration.case_authority.revision_status.value,
        }
        binding = configuration.authority_binding
        evaluated = binding.evaluated_rule_pack_authority
        binding_payload: dict[str, Any] = {
            "authority_mode": binding.authority_mode.value,
            "standard_system_id": binding.standard_system_id,
            "case_authority": case,
            "case_authority_evidence_refs": list(binding.case_authority_evidence_refs),
            "evaluated_rule_pack_authority": None,
        }
        evaluated_payload: dict[str, Any] | None = None
        if evaluated is not None:
            evaluated_payload = {
                "rule_pack_id": evaluated.rule_pack_id,
                "rule_pack_version": evaluated.rule_pack_version,
                "rule_pack_canonical_hash": evaluated.rule_pack_canonical_hash,
                "validation_status": evaluated.validation_status,
                "selected_rule_authorities": [
                    {
                        "rule_id": item.rule_id,
                        "rule_version": item.rule_version,
                        "rule_artifact_canonical_hash": item.rule_artifact_canonical_hash,
                        "source_class": item.source_class,
                        "license_evidence": item.license_evidence,
                        "approval_status": item.approval_status,
                        "provenance_edge_ids": list(item.provenance_edge_ids),
                        "evidence_refs": list(item.evidence_refs),
                    }
                    for item in evaluated.selected_rule_authorities
                ],
            }
            binding_payload["evaluated_rule_pack_authority"] = evaluated_payload
        payload = task020_canonical.canonical_payload(
            config,
            case_authority=case,
            evaluated_rule_pack_authority=evaluated_payload,
            canonical_warnings=[
                {
                    "code": item.code,
                    "field_path": item.field_path,
                    "message_key": item.message_key,
                    "evidence_refs": list(item.evidence_refs),
                    "details": item.details,
                }
                for item in configuration.warnings
            ],
            canonical_blockers=[
                {
                    "code": item.code,
                    "field_path": item.field_path,
                    "message_key": item.message_key,
                    "evidence_refs": list(item.evidence_refs),
                    "details": item.details,
                }
                for item in configuration.blockers
            ],
            deferred_capabilities=configuration.deferred_capabilities,
            authority_binding=binding_payload,
            schema_version=configuration.schema_version,
        )
        expected_hash = task020_canonical.configuration_hash(payload)
        return (
            expected_hash == configuration.configuration_hash
            and task020_canonical.configuration_id(expected_hash) == configuration.configuration_id
        )
    except Exception:
        return False


def _replay_task166(
    result: Task166Result, configuration: ShellAndTubeConfiguration
) -> list[Blocker]:
    blockers: list[Blocker] = []
    if result.source_definition_id != task166_authority.SOURCE_DEFINITION_ID:
        blockers.append(
            _blocker(
                BlockerCode.TASK166_AUTHORITY_INVALID,
                FailureStage.UPSTREAM_REPLAY,
                "task166_result.source_definition_id",
            )
        )
    try:
        expected_hash = task166_canonical.result_hash(result)
        expected_id = task166_canonical.result_id(expected_hash)
    except Exception:
        blockers.append(
            _blocker(
                BlockerCode.TASK166_IDENTITY_REPLAY_FAILED,
                FailureStage.UPSTREAM_REPLAY,
                "task166_result",
            )
        )
    else:
        if result.result_hash != expected_hash or result.result_id != expected_id:
            blockers.append(
                _blocker(
                    BlockerCode.TASK166_IDENTITY_REPLAY_FAILED,
                    FailureStage.UPSTREAM_REPLAY,
                    "task166_result.identity",
                )
            )
    if (
        result.provenance is None
        or result.provenance.self_edge_count != 0
        or result.provenance.cycle_count != 0
    ):
        blockers.append(
            _blocker(
                BlockerCode.TASK166_AUTHORITY_INVALID,
                FailureStage.UPSTREAM_REPLAY,
                "task166_result.provenance",
            )
        )
    if result.task020_evidence:
        evidence = dict(result.task020_evidence)
        if evidence.get("configuration_id") not in (None, configuration.configuration_id):
            blockers.append(
                _blocker(
                    BlockerCode.UPSTREAM_CASE_BINDING_MISMATCH,
                    FailureStage.UPSTREAM_REPLAY,
                    "task166_result.task020_evidence.configuration_id",
                )
            )
        if evidence.get("configuration_hash") not in (None, configuration.configuration_hash):
            blockers.append(
                _blocker(
                    BlockerCode.UPSTREAM_CASE_BINDING_MISMATCH,
                    FailureStage.UPSTREAM_REPLAY,
                    "task166_result.task020_evidence.configuration_hash",
                )
            )
    return blockers


def _replay_tube(result: TubeSideThermalResult) -> list[Blocker]:
    blockers: list[Blocker] = []
    if result.provenance is None or not isinstance(result.provenance, FrozenProvenance):
        blockers.append(
            _blocker(
                BlockerCode.TUBE_SIDE_IDENTITY_REPLAY_FAILED,
                FailureStage.UPSTREAM_REPLAY,
                "tube_side_result.provenance",
            )
        )
        return blockers
    try:
        # The TASK-026 success hash helper is the producer-owned canonical
        # replay.  Its request only needs fields included in that frozen
        # 21-field success preimage; the property scalar values are not
        # copied into TASK-167.
        snapshot = PropertySnapshot(
            density_kg_m3=Decimal("1"),
            dynamic_viscosity_pa_s=Decimal("1"),
            thermal_conductivity_w_m_k=Decimal("1"),
            specific_heat_capacity_j_kg_k=Decimal("1"),
            bulk_temperature_k=Decimal("1"),
            bulk_pressure_pa=Decimal("1"),
            phase_region=PhaseRegion(result.phase_assertion.value),
            property_source_id="task167-replay-placeholder",
            property_source_version="task167-replay-placeholder",
            property_snapshot_hash=result.property_snapshot_hash,
        )
        request = TubeSideThermalRequest(
            schema_version=TASK026_SCHEMA_VERSION,
            task026_version=TASK026_VERSION,
            implementation_software_version=TASK026_IMPL_VERSION,
            property_snapshot_hash=result.property_snapshot_hash,
            property_snapshot=snapshot,
            phase_assertion=result.phase_assertion,
            thermal_boundary_condition=result.thermal_boundary_condition,
            mass_flow_rate_kg_s=result.mass_flow_rate_kg_s,
            deferred_capabilities=result.deferred_capabilities,
            provenance=result.provenance,
        )
        output = SinglePhaseOutputs(
            bulk_velocity_m_s=result.bulk_velocity_m_s,
            reynolds_number=result.reynolds_number,
            prandtl_number=result.prandtl_number,
            nusselt_number=result.nusselt_number,
            tube_side_heat_transfer_coefficient_w_m2_k=result.tube_side_heat_transfer_coefficient_w_m2_k,
            flow_regime=result.flow_regime,
            correlation_id=result.correlation_id,
            correlation_version=result.correlation_version,
        )
        expected_hash = task026_success_hash(
            request_hash=result.request_hash,
            upstream_geometry_hash=result.upstream_geometry_hash,
            request=request,
            out=output,
            provenance=result.provenance,
        )
        expected_id = uuid.uuid5(
            uuid.UUID(TASK026_RESULT_ID_NAMESPACE),
            TASK026_RESULT_ID_PREFIX + expected_hash,
        )
        if result.result_hash != expected_hash or result.result_id != str(expected_id):
            blockers.append(
                _blocker(
                    BlockerCode.TUBE_SIDE_IDENTITY_REPLAY_FAILED,
                    FailureStage.UPSTREAM_REPLAY,
                    "tube_side_result.identity",
                )
            )
    except Exception:
        blockers.append(
            _blocker(
                BlockerCode.TUBE_SIDE_IDENTITY_REPLAY_FAILED,
                FailureStage.UPSTREAM_REPLAY,
                "tube_side_result",
            )
        )
    return blockers


def _pairs(value: Any) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return tuple(
            (str(item[0]), str(item[1])) for item in value if type(item) is tuple and len(item) == 2
        )
    return ()


def _applicability() -> ApplicabilityLedger:
    return ApplicabilityLedger(
        checks=tuple(
            ApplicabilityCheck(item, "PASS") for item in authority.TASK167_APPLICABILITY_CHECKS
        ),
        status="APPLICABLE",
    )


def _completeness() -> CompletenessLedger:
    return CompletenessLedger(
        required_fields=authority.TASK167_COMPLETENESS_FIELDS,
        present_fields=authority.TASK167_COMPLETENESS_FIELDS,
        status="COMPLETE",
    )


def _screen_blockers(
    code_pairs: tuple[tuple[BlockerCode, str], ...] | list[tuple[BlockerCode, str]],
) -> tuple[Blocker, ...]:
    return tuple(_blocker(code, FailureStage.SCREENING, path) for code, path in code_pairs)


def _warning_codes(screens: tuple[ScreenRecord, ...], fiv: Any) -> tuple[str, ...]:
    values: list[str] = []
    for screen in screens:
        if screen.status is ScreenStatus.WARN and screen.reason_code not in values:
            values.append(screen.reason_code)
    for item in (
        WarningCode.GENERIC_SCREEN_NO_STANDARD_CLAIM.value,
        WarningCode.DETAILED_MECHANICAL_ANALYSIS_DEFERRED.value,
    ):
        if item not in values:
            values.append(item)
    if fiv is not None:
        for item in (
            WarningCode.FIV_PRELIMINARY_ONLY.value,
            WarningCode.FIV_LIMIT_AUTHORITY_MISSING.value,
        ):
            if item not in values:
                values.append(item)
    return tuple(values)


def _calculate(
    request: Task167Request, request_hash_value: str
) -> Task167Result | tuple[Blocker, ...]:
    if not _configuration_replay(request.task020_configuration):
        return (
            _blocker(
                BlockerCode.TASK020_AUTHORITY_INVALID,
                FailureStage.UPSTREAM_REPLAY,
                "task020_configuration.identity",
            ),
        )
    task166_blockers = _replay_task166(request.task166_result, request.task020_configuration)
    tube_blockers = _replay_tube(request.tube_side_result)
    upstream_blockers = task166_blockers + tube_blockers
    if upstream_blockers:
        return tuple(upstream_blockers)
    rule_blockers = tuple(
        _blocker(code, FailureStage.RULE_PACK, path)
        for code, path in validate_approved_rule_pack(request)
    )
    if rule_blockers:
        return rule_blockers

    velocity_screens, velocity_blockers = build_velocity_screens(request)
    erosion_screen = build_erosion_screen(request)
    cleanability_screen, cleanability_blockers = build_cleanability_screen(request)
    expansion_screen, expansion_blockers = build_thermal_expansion_screen(request)
    construction_screen, construction_blockers = build_construction_screen(request)
    fiv_screen = build_fiv_screen(request)
    all_screens = velocity_screens + (
        erosion_screen,
        cleanability_screen,
        expansion_screen,
        construction_screen,
    )
    screen_pairs = (
        list(velocity_blockers)
        + list(cleanability_blockers)
        + list(expansion_blockers)
        + list(construction_blockers)
    )
    if screen_pairs:
        return _screen_blockers(screen_pairs)
    if any(item.status is ScreenStatus.BLOCKED for item in all_screens):
        return tuple(
            _blocker(BlockerCode.PARTIAL_RESULT_FORBIDDEN, FailureStage.SCREENING, item.screen_id)
            for item in all_screens
            if item.status is ScreenStatus.BLOCKED
        )

    applicability = _applicability()
    completeness = _completeness()
    warnings = _warning_codes(all_screens, fiv_screen)
    result = Task167Result(
        source_definition_id=request.source_definition_id,
        request_hash=request_hash_value,
        configuration_evidence=(
            ("configuration_id", request.task020_configuration.configuration_id),
            ("configuration_hash", request.task020_configuration.configuration_hash),
        ),
        task166_evidence=(
            ("result_hash", request.task166_result.result_hash),
            ("result_id", request.task166_result.result_id),
        ),
        tube_side_evidence=(
            ("result_hash", request.tube_side_result.result_hash),
            ("result_id", request.tube_side_result.result_id),
        ),
        screening_requirements_evidence=(
            ("requirement_id", request.screening_requirements.requirement_id),
            ("snapshot_hash", request.screening_requirements.snapshot_hash),
        ),
        screening_property_evidence=(
            ("snapshot_id", request.screening_property_snapshot.snapshot_id),
            ("snapshot_hash", request.screening_property_snapshot.snapshot_hash),
        ),
        nozzle_geometry_evidence=()
        if request.nozzle_geometry is None
        else (
            ("authority_id", request.nozzle_geometry.authority_id),
            ("snapshot_hash", request.nozzle_geometry.snapshot_hash),
        ),
        velocity_screens=velocity_screens,
        erosion_screen=erosion_screen,
        fouling_cleanability_screen=cleanability_screen,
        thermal_expansion_screen=expansion_screen,
        construction_family_suitability_screen=construction_screen,
        fiv_screen=fiv_screen,
        aggregate_screening_status=(
            ScreenStatus.WARN
            if any(item.status is ScreenStatus.WARN for item in all_screens)
            or fiv_screen.status is not None
            else ScreenStatus.PASS
        ),
        warnings=warnings,
        blockers=(),
        applicability=applicability,
        completeness=completeness,
    )
    semantic = semantic_input_hashes(
        request,
        velocity_screens=velocity_screens,
        erosion_screen=erosion_screen,
        fouling_screen=cleanability_screen,
        thermal_screen=expansion_screen,
        construction_screen=construction_screen,
        fiv_screen=fiv_screen,
        applicability=applicability,
        completeness=completeness,
        request_hash_value=request_hash_value,
    )
    result = replace(result, provenance_semantic_inputs=semantic)
    calculated_hash = result_hash(result)
    result = replace(result, result_hash=calculated_hash, result_id=result_id(calculated_hash))
    semantic_again, graph = build_provenance(
        request,
        result,
        velocity_screens=velocity_screens,
        erosion_screen=erosion_screen,
        fouling_screen=cleanability_screen,
        thermal_screen=expansion_screen,
        construction_screen=construction_screen,
        fiv_screen=fiv_screen,
        applicability=applicability,
        completeness=completeness,
        request_hash_value=request_hash_value,
    )
    if semantic_again != semantic or graph.self_edge_count != 0 or graph.cycle_count != 0:
        return (_blocker(BlockerCode.PROVENANCE_INVALID, FailureStage.PROVENANCE, "provenance"),)
    return replace(result, provenance=graph)


def validate_request(raw_request: object) -> Task167ValidationResult:
    """The sole public business boundary; raw failures never escape."""
    try:
        raw_projection = project_raw(raw_request)
        raw_projection_hash = sha256_domain_hex("task167.raw-request-projection.v1", raw_projection)
    except RawProjectionFailure as exc:
        # The raw projection itself is intentionally not serialized with
        # repr.  A stable error-only projection is sufficient for this
        # branch's deterministic identity.
        projection_hash = sha256_domain_hex("task167.raw-error.v1", exc.code.value)
        return _raw_branch(exc.code, projection_hash)
    except BaseException:
        projection_hash = sha256_domain_hex(
            "task167.raw-error.v1", BlockerCode.RAW_BOUNDARY_INVALID.value
        )
        return _raw_branch(BlockerCode.RAW_BOUNDARY_INVALID, projection_hash)
    try:
        request = parse_request(raw_request)
    except SchemaFailure as exc:
        return _typed_branch(
            raw_projection_hash,
            [_blocker(exc.code, FailureStage.TYPED_VALIDATION, exc.field_path)],
        )
    try:
        request_hash_value = request_hash(request)
        calculated = _calculate(request, request_hash_value)
        if isinstance(calculated, tuple):
            return _typed_branch(request_hash_value, list(calculated))
        return Task167ValidationResult(status=ValidationStatus.VALID, valid=calculated)
    except ScreeningFailure as exc:
        return _typed_branch(
            request_hash_value if "request_hash_value" in locals() else raw_projection_hash,
            [_blocker(exc.code, FailureStage.SCREENING, exc.field_path)],
        )
    except (DecimalException, ValueError, TypeError, KeyError):
        return _typed_branch(
            request_hash_value if "request_hash_value" in locals() else raw_projection_hash,
            [_blocker(BlockerCode.NONFINITE_ENGINEERING_RESULT, FailureStage.SCREENING)],
        )
    except BaseException:
        return _typed_branch(
            request_hash_value if "request_hash_value" in locals() else raw_projection_hash,
            [_blocker(BlockerCode.CANONICALIZATION_FAILED, FailureStage.IDENTITY)],
        )


__all__ = ["validate_request"]
