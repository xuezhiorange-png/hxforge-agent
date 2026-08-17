"""TASK-024 Round 6 public validation producer (Stage 19 + orchestration)."""

from __future__ import annotations

import decimal
import json
import uuid
from decimal import Decimal
from enum import Enum
from typing import Any, Final

from hexagent.exchangers.shell_tube.baffle_geometry import authority as _authority
from hexagent.exchangers.shell_tube.baffle_geometry import canonical as _canonical
from hexagent.exchangers.shell_tube.baffle_geometry import geometry as _geometry
from hexagent.exchangers.shell_tube.baffle_geometry import models as _models
from hexagent.exchangers.shell_tube.baffle_geometry import schema as _schema
from hexagent.exchangers.shell_tube.baffle_geometry.geometry import (
    _BafflePlaneFoundation,
    _CutChordFoundation,
)
from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    FrozenJsonArray,
    FrozenJsonObject,
)

IMPLEMENTATION_SOFTWARE_VERSION: Final[str] = "task024.minimal-compute-v1"
GIT_COMMIT: Final[str] = "82ce66fa1e479c5affd64f08c98496425d8bc09b"

_GEOMETRY_URN_PREFIX: Final[str] = "urn:hxforge:task024:baffle-geometry:v1:"

_COORDINATE_QUANTUM: Final[Decimal] = Decimal(_canonical.COORDINATE_QUANTUM_M)

_PROVENANCE_FIELD_ORDER: Final[tuple[str, ...]] = (
    "task_id",
    "design_contract_path",
    "profile_id",
    "software_version",
    "git_commit",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task020_case_authority",
    "task021_layout_id",
    "task021_layout_hash",
    "task021_tube_geometry_snapshot_hash",
    "task021_layout_rule_snapshot_hash",
    "task022_geometry_id",
    "task022_geometry_hash",
    "task022_shell_authority_mode",
    "task022_shell_authority_identity",
    "task022_geometry_rule_snapshot_hash",
    "axial_span_authority_hash",
    "baffle_design_authority_hash",
    "request_hash",
    "source_claim_status",
    "automatic_selection_performed",
    "nozzle_position_inference_performed",
    "flow_area_calculation_performed",
    "warnings",
    "deferred_capabilities",
)


class _CanonicalizationError(Exception):
    """Internal canonicalization failure."""


def _local_decimal_context() -> decimal.Context:
    return decimal.Context(
        prec=_canonical.DECIMAL_PRECISION,
        rounding=decimal.ROUND_HALF_EVEN,
    )


def _quantize_coordinate(value: Decimal) -> str:
    with decimal.localcontext(_local_decimal_context()):
        quantized = value.quantize(_COORDINATE_QUANTUM)
    return _canonical.canonical_decimal_string(quantized)


def to_canonical_primitive(value: Any) -> Any:
    """Project a validated value into the canonical JSON domain."""
    if value is None:
        return None
    value_type = type(value)
    if value_type is bool or value_type is int or value_type is str:
        return value
    if value_type is FrozenJsonObject:
        frozen_obj: FrozenJsonObject = value
        return {
            key: to_canonical_primitive(item) for key, item in sorted(frozen_obj.values.items())
        }
    if value_type is FrozenJsonArray:
        frozen_arr: FrozenJsonArray = value
        return [to_canonical_primitive(item) for item in frozen_arr.values]
    if isinstance(value, Enum):
        for _token, py_type, members in _canonical.STATIC_RECOGNIZED_ENUMS:
            if value_type is py_type:
                for member_obj, member_token in members:
                    if value is member_obj:
                        return member_token
                raise _CanonicalizationError("recognized enum member unavailable")
        raise _CanonicalizationError("unsupported enum type")
    for _token, py_type, fields in _canonical.STATIC_RECOGNIZED_DATACLASSES:
        if value_type is py_type:
            projected: dict[str, Any] = {}
            for name in fields:
                projected[name] = to_canonical_primitive(object.__getattribute__(value, name))
            return projected
    if value_type is tuple:
        return [to_canonical_primitive(item) for item in value]
    if value_type is list:
        return [to_canonical_primitive(item) for item in value]
    if value_type is dict:
        dict_value: dict[Any, Any] = value
        return {key: to_canonical_primitive(item) for key, item in dict_value.items()}
    raise _CanonicalizationError(f"unsupported canonical value: {value_type.__name__}")


def _message_projection(entry: _models.MessageEntry) -> dict[str, Any]:
    return {
        "code": entry.code,
        "field_path": entry.field_path,
        "message_key": entry.message_key,
        "evidence_refs": list(entry.evidence_refs),
        "details": [[key, val] for key, val in entry.details],
    }


def _schema_message_key(code: str) -> str:
    if code.startswith("BFG_"):
        return code[4:].lower()
    return code.lower()


def _schema_blockers_to_messages(
    blockers: tuple[tuple[str, str, Any], ...],
) -> tuple[_models.MessageEntry, ...]:
    messages: list[_models.MessageEntry] = []
    for code, field_path, _raw_component in blockers:
        normalized_path = field_path if field_path else None
        if normalized_path == "":
            normalized_path = None
        messages.append(
            _models.MessageEntry(
                code=code,
                field_path=normalized_path,
                message_key=_schema_message_key(code),
                evidence_refs=(),
                details=(),
            )
        )
    return tuple(messages)


def _sha256_hex(value: Any) -> str:
    return _canonical.sha256_canonical(value).hex()


def _request_projection(request: _models.BaffleGeometryRequest) -> dict[str, Any]:
    return {
        "schema_version": request.schema_version,
        "configuration": to_canonical_primitive(request.configuration),
        "tube_layout": to_canonical_primitive(request.tube_layout),
        "shell_bundle_geometry": to_canonical_primitive(request.shell_bundle_geometry),
        "axial_span": to_canonical_primitive(request.axial_span),
        "design_authority": to_canonical_primitive(request.design_authority),
        "evidence_refs": list(request.evidence_refs),
    }


def _compute_request_hash(request: _models.BaffleGeometryRequest) -> str:
    return _sha256_hex(_request_projection(request))


def _raw_blocked_identity(raw_request: Any) -> dict[str, Any]:
    projection_bytes = _canonical.raw_blocked_projection(raw_request)
    decoded = json.loads(projection_bytes.decode("utf-8"))
    if type(decoded) is not dict:
        raise _CanonicalizationError("raw blocked projection must decode to mapping")
    return decoded


def _blocked_result_hash(
    *,
    request_identity: str | dict[str, Any],
    warnings: tuple[_models.MessageEntry, ...],
    blockers: tuple[_models.MessageEntry, ...],
) -> str:
    payload = {
        "request_identity": request_identity,
        "warnings": [_message_projection(item) for item in warnings],
        "blockers": [_message_projection(item) for item in blockers],
        "deferred_capabilities": list(_models.DEFERRED_CAPABILITIES),
        "profile_id": _models.PROFILE_ID,
        "design_contract_path": _models.DESIGN_CONTRACT_PATH,
    }
    return _sha256_hex(payload)


def _blocked(
    *,
    warnings: tuple[_models.MessageEntry, ...],
    blockers: tuple[_models.MessageEntry, ...],
    request_identity: str | dict[str, Any],
) -> _models.BaffleGeometryValidationResult:
    return _models.BaffleGeometryValidationResult(
        status=_models.ValidationStatus.BLOCKED,
        geometry=None,
        warnings=warnings,
        blockers=blockers,
        deferred_capabilities=_models.DEFERRED_CAPABILITIES,
        blocked_result_hash=_blocked_result_hash(
            request_identity=request_identity,
            warnings=warnings,
            blockers=blockers,
        ),
    )


def _cut_chord_from_foundation(chord: _CutChordFoundation) -> _models.CutChordGeometry:
    return _models.CutChordGeometry(
        normal_x=chord.normal_x,
        normal_y=chord.normal_y,
        half_plane_offset_m=_quantize_coordinate(chord.half_plane_offset_m),
        chord_half_length_m=_quantize_coordinate(chord.chord_half_length_m),
        endpoint_a_x_m=_quantize_coordinate(chord.endpoint_a_x_m),
        endpoint_a_y_m=_quantize_coordinate(chord.endpoint_a_y_m),
        endpoint_b_x_m=_quantize_coordinate(chord.endpoint_b_x_m),
        endpoint_b_y_m=_quantize_coordinate(chord.endpoint_b_y_m),
    )


def _classification_audit_hash(
    *,
    baffle_index: int,
    orientation: _models.BaffleOrientation,
    cut_chord: _models.CutChordGeometry,
    classifications: tuple[_models.TubeHoleClassification, ...],
    window_position_ids: tuple[str, ...],
    crossflow_reference_position_ids: tuple[str, ...],
    outer_tangent_position_ids: tuple[str, ...],
    pairwise_tangent_position_pairs: tuple[tuple[str, str], ...],
) -> str:
    payload = {
        "baffle_index": baffle_index,
        "orientation": orientation.value,
        "cut_chord": to_canonical_primitive(cut_chord),
        "tube_hole_classifications": [
            to_canonical_primitive(classification) for classification in classifications
        ],
        "window_position_ids": list(window_position_ids),
        "crossflow_reference_position_ids": list(crossflow_reference_position_ids),
        "outer_tangent_position_ids": list(outer_tangent_position_ids),
        "pairwise_tangent_position_pairs": [
            [lower_id, higher_id] for lower_id, higher_id in pairwise_tangent_position_pairs
        ],
    }
    return _sha256_hex(payload)


def _baffle_plane_from_foundation(plane: _BafflePlaneFoundation) -> _models.BafflePlaneGeometry:
    cut_chord = _cut_chord_from_foundation(plane.cut_chord)
    classifications = plane.classifications
    audit_hash = _classification_audit_hash(
        baffle_index=plane.baffle_index,
        orientation=plane.orientation,
        cut_chord=cut_chord,
        classifications=classifications.classifications,
        window_position_ids=classifications.window_position_ids,
        crossflow_reference_position_ids=classifications.crossflow_reference_position_ids,
        outer_tangent_position_ids=classifications.outer_tangent_position_ids,
        pairwise_tangent_position_pairs=classifications.pairwise_tangent_position_pairs,
    )
    return _models.BafflePlaneGeometry(
        baffle_index=plane.baffle_index,
        center_coordinate_m=plane.center_coordinate_m,
        occupied_start_coordinate_m=plane.occupied_start_coordinate_m,
        occupied_end_coordinate_m=plane.occupied_end_coordinate_m,
        orientation=plane.orientation,
        cut_chord=cut_chord,
        window_region_semantics=plane.window_region_semantics,
        baffle_covered_region_semantics=plane.baffle_covered_region_semantics,
        crossflow_reference_region_semantics=plane.crossflow_reference_region_semantics,
        tube_hole_classifications=classifications.classifications,
        window_position_ids=classifications.window_position_ids,
        crossflow_reference_position_ids=classifications.crossflow_reference_position_ids,
        outer_tangent_position_ids=classifications.outer_tangent_position_ids,
        pairwise_tangent_position_pairs=classifications.pairwise_tangent_position_pairs,
        classification_audit_hash=audit_hash,
    )


def _task022_shell_authority_identity(
    shell_bundle_geometry: Any,
) -> dict[str, Any]:
    mode = shell_bundle_geometry.shell_authority_mode
    mode_token = mode.value if isinstance(mode, Enum) else str(mode)
    caller = shell_bundle_geometry.caller_supplied_shell
    approved = shell_bundle_geometry.approved_shell_geometry
    return {
        "shell_authority_mode": mode_token,
        "caller_supplied_shell": (None if caller is None else to_canonical_primitive(caller)),
        "approved_shell_geometry": (None if approved is None else to_canonical_primitive(approved)),
    }


def _provenance_mapping(
    request: _models.BaffleGeometryRequest,
    *,
    request_hash: str,
    warnings: tuple[_models.MessageEntry, ...],
) -> dict[str, Any]:
    configuration = request.configuration
    layout = request.tube_layout
    shell_bundle_geometry = request.shell_bundle_geometry
    return {
        "task_id": "TASK-024",
        "design_contract_path": _models.DESIGN_CONTRACT_PATH,
        "profile_id": _models.PROFILE_ID,
        "software_version": IMPLEMENTATION_SOFTWARE_VERSION,
        "git_commit": GIT_COMMIT,
        "task020_configuration_id": configuration.configuration_id,
        "task020_configuration_hash": configuration.configuration_hash,
        "task020_case_authority": to_canonical_primitive(configuration.case_authority),
        "task021_layout_id": layout.layout_id,
        "task021_layout_hash": layout.layout_hash,
        "task021_tube_geometry_snapshot_hash": layout.tube_geometry.snapshot_hash,
        "task021_layout_rule_snapshot_hash": layout.layout_rule_authority.snapshot_hash,
        "task022_geometry_id": shell_bundle_geometry.geometry_id,
        "task022_geometry_hash": shell_bundle_geometry.geometry_hash,
        "task022_shell_authority_mode": (
            shell_bundle_geometry.shell_authority_mode.value
            if isinstance(shell_bundle_geometry.shell_authority_mode, Enum)
            else str(shell_bundle_geometry.shell_authority_mode)
        ),
        "task022_shell_authority_identity": _task022_shell_authority_identity(
            shell_bundle_geometry
        ),
        "task022_geometry_rule_snapshot_hash": (
            shell_bundle_geometry.geometry_rule_authority.snapshot_hash
        ),
        "axial_span_authority_hash": request.axial_span.authority_hash,
        "baffle_design_authority_hash": request.design_authority.authority_hash,
        "request_hash": request_hash,
        "source_claim_status": "NO_STANDARD_CLAIM",
        "automatic_selection_performed": False,
        "nozzle_position_inference_performed": False,
        "flow_area_calculation_performed": False,
        "warnings": [_message_projection(item) for item in warnings],
        "deferred_capabilities": list(_models.DEFERRED_CAPABILITIES),
    }


def _provenance_tuple(mapping: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    if set(mapping.keys()) != set(_PROVENANCE_FIELD_ORDER):
        raise _CanonicalizationError("provenance field set mismatch")
    return tuple((key, mapping[key]) for key in _PROVENANCE_FIELD_ORDER)


def _geometry_hash_payload(geometry: _models.BaffleGeometry) -> dict[str, Any]:
    provenance_dict = {key: value for key, value in geometry.provenance}
    return {
        "schema_version": geometry.schema_version,
        "request_hash": geometry.request_hash,
        "task020_configuration_id": geometry.task020_configuration_id,
        "task020_configuration_hash": geometry.task020_configuration_hash,
        "task021_layout_id": geometry.task021_layout_id,
        "task021_layout_hash": geometry.task021_layout_hash,
        "task022_geometry_id": geometry.task022_geometry_id,
        "task022_geometry_hash": geometry.task022_geometry_hash,
        "construction_family": geometry.construction_family,
        "equipment_orientation": geometry.equipment_orientation,
        "shell_pass_count": geometry.shell_pass_count,
        "tube_pass_count": geometry.tube_pass_count,
        "shell_inside_diameter_m": geometry.shell_inside_diameter_m,
        "tube_outer_diameter_m": geometry.tube_outer_diameter_m,
        "axial_span": to_canonical_primitive(geometry.axial_span),
        "design_authority": to_canonical_primitive(geometry.design_authority),
        "usable_baffle_span_m": geometry.usable_baffle_span_m,
        "baffle_diameter_m": geometry.baffle_diameter_m,
        "baffle_radius_m": geometry.baffle_radius_m,
        "baffle_hole_diameter_m": geometry.baffle_hole_diameter_m,
        "baffle_hole_radius_m": geometry.baffle_hole_radius_m,
        "cut_height_m": geometry.cut_height_m,
        "chord_offset_from_center_m": geometry.chord_offset_from_center_m,
        "baffle_planes": [to_canonical_primitive(plane) for plane in geometry.baffle_planes],
        "position_count": geometry.position_count,
        "warnings": [_message_projection(item) for item in geometry.warnings],
        "blockers": [_message_projection(item) for item in geometry.blockers],
        "deferred_capabilities": list(geometry.deferred_capabilities),
        "provenance": provenance_dict,
    }


def _geometry_id_from_hash(geometry_hash: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, _GEOMETRY_URN_PREFIX + geometry_hash))


def _canonicalization_failed(
    request: _models.BaffleGeometryRequest,
    *,
    warnings: tuple[_models.MessageEntry, ...],
) -> _models.BaffleGeometryValidationResult:
    request_hash = _compute_request_hash(request)
    blocker = _models.MessageEntry(
        code=_models.BlockerCode.BFG_CANONICALIZATION_FAILED.value,
        field_path=None,
        message_key="canonicalization_failed",
        evidence_refs=(),
        details=(),
    )
    return _blocked(
        warnings=warnings,
        blockers=(blocker,),
        request_identity=request_hash,
    )


def validate_typed_request(
    request: _models.BaffleGeometryRequest,
) -> _models.BaffleGeometryValidationResult:
    """Run Stages 2 through 19 for a typed request."""
    authority_result = _authority.validate_authority_foundation(request)
    if authority_result.blockers:
        request_hash = _compute_request_hash(request)
        return _blocked(
            warnings=authority_result.warnings,
            blockers=authority_result.blockers,
            request_identity=request_hash,
        )

    geometry_result = _geometry.compute_geometry_foundation(request)
    warnings = authority_result.warnings + geometry_result.warnings
    if geometry_result.blockers:
        request_hash = _compute_request_hash(request)
        return _blocked(
            warnings=warnings,
            blockers=geometry_result.blockers,
            request_identity=request_hash,
        )
    if geometry_result.geometry is None:
        request_hash = _compute_request_hash(request)
        blocker = _models.MessageEntry(
            code=_models.BlockerCode.BFG_CANONICALIZATION_FAILED.value,
            field_path=None,
            message_key="geometry_foundation_missing_on_success_path",
            evidence_refs=(),
            details=(),
        )
        return _blocked(
            warnings=warnings,
            blockers=(blocker,),
            request_identity=request_hash,
        )

    try:
        request_hash = _compute_request_hash(request)
        foundation = geometry_result.geometry
        configuration = request.configuration
        layout = request.tube_layout
        shell_bundle_geometry = request.shell_bundle_geometry
        baffle_planes = tuple(
            _baffle_plane_from_foundation(plane) for plane in foundation.baffle_planes
        )
        provenance_mapping = _provenance_mapping(
            request,
            request_hash=request_hash,
            warnings=warnings,
        )
        provenance = _provenance_tuple(provenance_mapping)
        geometry_without_hashes = _models.BaffleGeometry(
            schema_version=_models.RESULT_SCHEMA_VERSION,
            geometry_id="",
            geometry_hash="",
            request_hash=request_hash,
            task020_configuration_id=configuration.configuration_id,
            task020_configuration_hash=configuration.configuration_hash,
            task021_layout_id=layout.layout_id,
            task021_layout_hash=layout.layout_hash,
            task022_geometry_id=shell_bundle_geometry.geometry_id,
            task022_geometry_hash=shell_bundle_geometry.geometry_hash,
            construction_family=configuration.construction_family.value,
            equipment_orientation=(
                shell_bundle_geometry.equipment_orientation.value
                if isinstance(shell_bundle_geometry.equipment_orientation, Enum)
                else str(shell_bundle_geometry.equipment_orientation)
            ),
            shell_pass_count=configuration.shell_pass_count,
            tube_pass_count=configuration.tube_pass_count,
            shell_inside_diameter_m=shell_bundle_geometry.shell_inside_diameter_m,
            tube_outer_diameter_m=layout.tube_geometry.outer_diameter_m,
            axial_span=request.axial_span,
            design_authority=request.design_authority,
            usable_baffle_span_m=foundation.usable_baffle_span_m,
            baffle_diameter_m=foundation.baffle_diameter_m,
            baffle_radius_m=foundation.baffle_radius_m,
            baffle_hole_diameter_m=foundation.baffle_hole_diameter_m,
            baffle_hole_radius_m=foundation.baffle_hole_radius_m,
            cut_height_m=foundation.cut_height_m,
            chord_offset_from_center_m=foundation.chord_offset_from_center_m,
            baffle_planes=baffle_planes,
            position_count=foundation.position_count,
            warnings=warnings,
            blockers=(),
            deferred_capabilities=_models.DEFERRED_CAPABILITIES,
            provenance=provenance,
        )
        geometry_hash = _sha256_hex(_geometry_hash_payload(geometry_without_hashes))
        geometry_id = _geometry_id_from_hash(geometry_hash)
        geometry = _models.BaffleGeometry(
            schema_version=geometry_without_hashes.schema_version,
            geometry_id=geometry_id,
            geometry_hash=geometry_hash,
            request_hash=geometry_without_hashes.request_hash,
            task020_configuration_id=geometry_without_hashes.task020_configuration_id,
            task020_configuration_hash=geometry_without_hashes.task020_configuration_hash,
            task021_layout_id=geometry_without_hashes.task021_layout_id,
            task021_layout_hash=geometry_without_hashes.task021_layout_hash,
            task022_geometry_id=geometry_without_hashes.task022_geometry_id,
            task022_geometry_hash=geometry_without_hashes.task022_geometry_hash,
            construction_family=geometry_without_hashes.construction_family,
            equipment_orientation=geometry_without_hashes.equipment_orientation,
            shell_pass_count=geometry_without_hashes.shell_pass_count,
            tube_pass_count=geometry_without_hashes.tube_pass_count,
            shell_inside_diameter_m=geometry_without_hashes.shell_inside_diameter_m,
            tube_outer_diameter_m=geometry_without_hashes.tube_outer_diameter_m,
            axial_span=geometry_without_hashes.axial_span,
            design_authority=geometry_without_hashes.design_authority,
            usable_baffle_span_m=geometry_without_hashes.usable_baffle_span_m,
            baffle_diameter_m=geometry_without_hashes.baffle_diameter_m,
            baffle_radius_m=geometry_without_hashes.baffle_radius_m,
            baffle_hole_diameter_m=geometry_without_hashes.baffle_hole_diameter_m,
            baffle_hole_radius_m=geometry_without_hashes.baffle_hole_radius_m,
            cut_height_m=geometry_without_hashes.cut_height_m,
            chord_offset_from_center_m=geometry_without_hashes.chord_offset_from_center_m,
            baffle_planes=geometry_without_hashes.baffle_planes,
            position_count=geometry_without_hashes.position_count,
            warnings=geometry_without_hashes.warnings,
            blockers=geometry_without_hashes.blockers,
            deferred_capabilities=geometry_without_hashes.deferred_capabilities,
            provenance=geometry_without_hashes.provenance,
        )
    except _CanonicalizationError:
        return _canonicalization_failed(request, warnings=warnings)

    provenance_warnings = dict(geometry.provenance).get("warnings")
    projected_warnings = [_message_projection(item) for item in geometry.warnings]
    if provenance_warnings != projected_warnings:
        return _canonicalization_failed(request, warnings=warnings)
    provenance_deferred = dict(geometry.provenance).get("deferred_capabilities")
    if provenance_deferred != list(geometry.deferred_capabilities):
        return _canonicalization_failed(request, warnings=warnings)
    if geometry.blockers:
        return _canonicalization_failed(request, warnings=warnings)

    return _models.BaffleGeometryValidationResult(
        status=_models.ValidationStatus.VALID,
        geometry=geometry,
        warnings=geometry.warnings,
        blockers=(),
        deferred_capabilities=geometry.deferred_capabilities,
        blocked_result_hash=None,
    )


def validate_request(raw_request: Any) -> _models.BaffleGeometryValidationResult:
    """Public TASK-024 validation entry point."""
    try:
        request = _schema.parse_request(raw_request)
    except _schema.BaffleGeometrySchemaFailure as exc:
        blockers = _schema_blockers_to_messages(exc.blockers)
        return _blocked(
            warnings=(),
            blockers=blockers,
            request_identity=_raw_blocked_identity(raw_request),
        )
    return validate_typed_request(request)
