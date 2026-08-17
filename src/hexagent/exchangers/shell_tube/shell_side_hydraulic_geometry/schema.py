# ruff: noqa: E501
"""TASK-031 Stage 1-2 schema parser."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, cast

from hexagent.exchangers.shell_tube.baffle_geometry import models as task024_models
from hexagent.exchangers.shell_tube.models import Orientation
from hexagent.exchangers.shell_tube.tube_layout import models as task021_models
from hexagent.exchangers.shell_tube.tube_layout import schema as task021_schema
from hexagent.exchangers.shell_tube.tube_layout.canonical import force_frozen_canonical

from .models import (
    AGGREGATE_AUTHORITY_PROFILE_ID,
    ENGINEERING_AUTHORITY_REQUEST_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    BlockerCode,
    EngineeringAuthorityRequestBinding,
    MessageEntry,
    ShellSideHydraulicGeometryRequest,
)

_SCHEMA_STAGE = 1
_DECODE_STAGE = 2
_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

_TOP_LEVEL_FIELDS: frozenset[str] = frozenset(
    {
        "schema_version",
        "tube_layout",
        "baffle_geometry_result",
        "engineering_authority",
        "evidence_refs",
    }
)


class SchemaFailure(Exception):
    def __init__(
        self,
        *,
        stage: int,
        blockers: tuple[MessageEntry, ...],
        raw_failing_field: Any,
        normalized_context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__("SchemaFailure")
        self.stage = stage
        self.blockers = blockers
        self.raw_failing_field = raw_failing_field
        self.normalized_context = {} if normalized_context is None else dict(normalized_context)


def _message(
    code: BlockerCode,
    field_path: str | None,
    message_key: str,
) -> MessageEntry:
    token = code.value
    return MessageEntry(
        code=token,
        field_path=field_path,
        message_key=message_key[5:].lower() if message_key.startswith("SSHG_") else message_key,
        evidence_refs=(),
        details=(),
    )


def _schema_message_key(code: BlockerCode) -> str:
    return code.value[5:].lower()


def _is_exact_dict(value: Any) -> bool:
    return type(value) is dict


def _is_exact_list(value: Any) -> bool:
    return type(value) is list


def _is_exact_str(value: Any) -> bool:
    return type(value) is str


def _is_exact_int(value: Any) -> bool:
    return type(value) is int and not isinstance(value, bool)


def _is_decimal_lexical_string(value: str) -> bool:
    if value != value.strip() or value.startswith("+"):
        return False
    if "e" in value or "E" in value:
        return False
    try:
        from decimal import Decimal

        parsed = Decimal(value)
    except Exception:
        return False
    return parsed.is_finite()


def _decimal_lexical(value: Any, field_path: str, blockers: list[MessageEntry]) -> str | None:
    if not _is_exact_str(value) or not _is_decimal_lexical_string(value):
        blockers.append(
            _message(
                BlockerCode.SSHG_DECIMAL_LEXICAL_INVALID,
                field_path,
                _schema_message_key(BlockerCode.SSHG_DECIMAL_LEXICAL_INVALID),
            )
        )
        return None
    return str(value)


def _evidence_refs(
    value: Any,
    field_path: str,
    blockers: list[MessageEntry],
) -> tuple[str, ...] | None:
    if not _is_exact_list(value) or not value:
        blockers.append(
            _message(
                BlockerCode.SSHG_EVIDENCE_REFS_INVALID,
                field_path,
                _schema_message_key(BlockerCode.SSHG_EVIDENCE_REFS_INVALID),
            )
        )
        return None
    items: list[str] = []
    for index, item in enumerate(value):
        if not _is_exact_str(item) or not item:
            blockers.append(
                _message(
                    BlockerCode.SSHG_RAW_TYPE_INVALID,
                    f"{field_path}[{index}]",
                    _schema_message_key(BlockerCode.SSHG_RAW_TYPE_INVALID),
                )
            )
            return None
        items.append(item)
    if len(set(items)) != len(items) or items != sorted(items):
        blockers.append(
            _message(
                BlockerCode.SSHG_EVIDENCE_REFS_INVALID,
                field_path,
                _schema_message_key(BlockerCode.SSHG_EVIDENCE_REFS_INVALID),
            )
        )
        return None
    return tuple(items)


def _parse_message_entry(
    value: Any, field_path: str, blockers: list[MessageEntry]
) -> MessageEntry | None:
    if not _is_exact_dict(value):
        blockers.append(
            _message(
                BlockerCode.SSHG_RAW_TYPE_INVALID,
                field_path,
                _schema_message_key(BlockerCode.SSHG_RAW_TYPE_INVALID),
            )
        )
        return None
    code = value.get("code")
    message_key = value.get("message_key")
    if not _is_exact_str(code) or not _is_exact_str(message_key):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_INVALID,
                field_path,
                "task024_result_invalid",
            )
        )
        return None
    field_path_value = value.get("field_path")
    if field_path_value is not None and not _is_exact_str(field_path_value):
        blockers.append(
            _message(
                BlockerCode.SSHG_RAW_TYPE_INVALID,
                f"{field_path}.field_path",
                _schema_message_key(BlockerCode.SSHG_RAW_TYPE_INVALID),
            )
        )
        return None
    evidence_raw = value.get("evidence_refs", [])
    if not _is_exact_list(evidence_raw):
        evidence_refs: tuple[str, ...] = ()
    else:
        evidence_refs = tuple(str(item) for item in evidence_raw if _is_exact_str(item))
    details_raw = value.get("details", [])
    details: list[tuple[str, str]] = []
    if _is_exact_list(details_raw):
        for item in details_raw:
            if (
                _is_exact_list(item)
                and len(item) == 2
                and all(_is_exact_str(part) for part in item)
            ):
                details.append((item[0], item[1]))
    return MessageEntry(
        code=code,
        field_path=field_path_value,
        message_key=message_key,
        evidence_refs=evidence_refs,
        details=tuple(details),
    )


def _parse_tube_layout(
    value: Any, blockers: list[MessageEntry]
) -> task021_models.TubeLayout | None:
    if not _is_exact_dict(value):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK021_LAYOUT_INVALID,
                "tube_layout",
                "task021_layout_invalid",
            )
        )
        return None
    expected = {
        "schema_version",
        "layout_id",
        "layout_hash",
        "request_hash",
        "task020_configuration_id",
        "task020_configuration_hash",
        "case_authority",
        "construction_family",
        "equipment_orientation",
        "shell_pass_count",
        "tube_pass_count",
        "tube_geometry",
        "layout_rule_authority",
        "placement_envelope",
        "origin_mode",
        "axis_orientation",
        "exclusion_zones",
        "positions",
        "tube_hole_count",
        "physical_tube_count",
        "boundary_rejection_count",
        "exclusion_rejection_count",
        "exclusion_audit",
        "warnings",
        "blockers",
        "deferred_capabilities",
        "provenance",
    }
    for key in value:
        if not _is_exact_str(key) or key not in expected:
            blockers.append(
                _message(
                    BlockerCode.SSHG_UNKNOWN_FIELD,
                    f"tube_layout.{key}" if _is_exact_str(key) else "tube_layout",
                    _schema_message_key(BlockerCode.SSHG_UNKNOWN_FIELD),
                )
            )
    try:
        tube_geometry = task021_schema.parse_geometry(value["tube_geometry"])
        layout_rule = task021_schema.parse_layout_rule(value["layout_rule_authority"])
        placement_envelope = task021_schema.parse_envelope(value["placement_envelope"])
    except task021_schema.SchemaFailure:
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK021_LAYOUT_INVALID,
                "tube_layout",
                "task021_layout_invalid",
            )
        )
        return None
    if value.get("schema_version") != task021_models.LAYOUT_SCHEMA_VERSION:
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK021_LAYOUT_INVALID,
                "tube_layout.schema_version",
                "task021_layout_schema_version_unsupported",
            )
        )
        return None
    positions: list[task021_models.TubePosition] = []
    positions_raw = value.get("positions")
    if not _is_exact_list(positions_raw):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK021_LAYOUT_INVALID,
                "tube_layout.positions",
                "task021_layout_invalid",
            )
        )
        return None
    for index, pos in enumerate(positions_raw):
        if not _is_exact_dict(pos):
            blockers.append(
                _message(
                    BlockerCode.SSHG_TASK021_LAYOUT_INVALID,
                    f"tube_layout.positions[{index}]",
                    "task021_layout_invalid",
                )
            )
            return None
        x_m = _decimal_lexical(pos.get("x_m"), f"tube_layout.positions[{index}].x_m", blockers)
        y_m = _decimal_lexical(pos.get("y_m"), f"tube_layout.positions[{index}].y_m", blockers)
        if x_m is None or y_m is None:
            return None
        if (
            not _is_exact_str(pos.get("position_id"))
            or not _is_exact_int(pos.get("u"))
            or not _is_exact_int(pos.get("v"))
        ):
            blockers.append(
                _message(
                    BlockerCode.SSHG_TASK021_LAYOUT_INVALID,
                    f"tube_layout.positions[{index}]",
                    "task021_layout_invalid",
                )
            )
            return None
        positions.append(
            task021_models.TubePosition(
                position_id=pos["position_id"],
                u=pos["u"],
                v=pos["v"],
                x_m=x_m,
                y_m=y_m,
            )
        )
    warnings: list[task021_models.MessageEntry] = []
    for _index, item in enumerate(value.get("warnings", [])):
        if not _is_exact_dict(item):
            continue
        warnings.append(
            task021_models.MessageEntry(
                code=item.get("code", ""),
                field_path=item.get("field_path"),
                message_key=item.get("message_key", ""),
                evidence_refs=tuple(item.get("evidence_refs", [])),
                details=item.get("details"),
            )
        )
    blockers_raw = value.get("blockers", [])
    layout_blockers: list[task021_models.MessageEntry] = []
    if _is_exact_list(blockers_raw):
        for item in blockers_raw:
            if _is_exact_dict(item):
                layout_blockers.append(
                    task021_models.MessageEntry(
                        code=item.get("code", ""),
                        field_path=item.get("field_path"),
                        message_key=item.get("message_key", ""),
                        evidence_refs=tuple(item.get("evidence_refs", [])),
                        details=item.get("details"),
                    )
                )
    deferred_raw = value.get("deferred_capabilities", [])
    deferred = tuple(deferred_raw) if _is_exact_list(deferred_raw) else ()
    try:
        origin_mode = task021_schema._enum(
            value["origin_mode"],
            task021_models.OriginMode,
            "tube_layout.origin_mode",
            stage=_DECODE_STAGE,
        )
        axis_orientation = task021_schema._enum(
            value["axis_orientation"],
            task021_models.AxisOrientation,
            "tube_layout.axis_orientation",
            stage=_DECODE_STAGE,
        )
    except task021_schema.SchemaFailure:
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK021_LAYOUT_INVALID,
                "tube_layout",
                "task021_layout_invalid",
            )
        )
        return None
    exclusion_zones = ()
    return task021_models.TubeLayout(
        schema_version=value["schema_version"],
        layout_id=value["layout_id"],
        layout_hash=value["layout_hash"],
        request_hash=value["request_hash"],
        task020_configuration_id=value["task020_configuration_id"],
        task020_configuration_hash=value["task020_configuration_hash"],
        case_authority=force_frozen_canonical(value["case_authority"]),
        construction_family=value["construction_family"],
        equipment_orientation=task021_schema._enum(
            value["equipment_orientation"],
            Orientation,
            "tube_layout.equipment_orientation",
            stage=_DECODE_STAGE,
        ),
        shell_pass_count=value["shell_pass_count"],
        tube_pass_count=value["tube_pass_count"],
        tube_geometry=tube_geometry,
        layout_rule_authority=layout_rule,
        placement_envelope=placement_envelope,
        origin_mode=origin_mode,
        axis_orientation=axis_orientation,
        exclusion_zones=exclusion_zones,
        positions=tuple(positions),
        tube_hole_count=value["tube_hole_count"],
        physical_tube_count=value["physical_tube_count"],
        boundary_rejection_count=value["boundary_rejection_count"],
        exclusion_rejection_count=value["exclusion_rejection_count"],
        exclusion_audit=(),
        warnings=tuple(warnings),
        blockers=tuple(layout_blockers),
        deferred_capabilities=deferred,
        provenance=force_frozen_canonical(value["provenance"]),
    )


def _parse_baffle_result(
    value: Any, blockers: list[MessageEntry]
) -> task024_models.BaffleGeometryValidationResult | None:
    if not _is_exact_dict(value):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_INVALID,
                "baffle_geometry_result",
                "task024_result_invalid",
            )
        )
        return None
    expected = {
        "status",
        "geometry",
        "warnings",
        "blockers",
        "deferred_capabilities",
        "blocked_result_hash",
    }
    for key in value:
        if not _is_exact_str(key) or key not in expected:
            blockers.append(
                _message(
                    BlockerCode.SSHG_UNKNOWN_FIELD,
                    f"baffle_geometry_result.{key}"
                    if _is_exact_str(key)
                    else "baffle_geometry_result",
                    _schema_message_key(BlockerCode.SSHG_UNKNOWN_FIELD),
                )
            )
    status_raw = value.get("status")
    if not _is_exact_str(status_raw):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_INVALID,
                "baffle_geometry_result.status",
                "task024_result_invalid",
            )
        )
        return None
    try:
        status = task024_models.ValidationStatus(status_raw)
    except ValueError:
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_INVALID,
                "baffle_geometry_result.status",
                "task024_result_invalid",
            )
        )
        return None
    warnings_list: list[task024_models.MessageEntry] = []
    for index, item in enumerate(value.get("warnings", [])):
        parsed = _parse_t024_message(item, f"baffle_geometry_result.warnings[{index}]", blockers)
        if parsed is not None:
            warnings_list.append(parsed)
    blockers_list: list[task024_models.MessageEntry] = []
    for index, item in enumerate(value.get("blockers", [])):
        parsed = _parse_t024_message(item, f"baffle_geometry_result.blockers[{index}]", blockers)
        if parsed is not None:
            blockers_list.append(parsed)
    deferred_raw = value.get("deferred_capabilities", [])
    deferred = tuple(deferred_raw) if _is_exact_list(deferred_raw) else ()
    geometry_raw = value.get("geometry")
    geometry: task024_models.BaffleGeometry | None = None
    if geometry_raw is not None:
        if not _is_exact_dict(geometry_raw):
            blockers.append(
                _message(
                    BlockerCode.SSHG_TASK024_RESULT_INVALID,
                    "baffle_geometry_result.geometry",
                    "task024_result_invalid",
                )
            )
            return None
        geometry = _parse_baffle_geometry(geometry_raw, blockers)
    blocked_hash = value.get("blocked_result_hash")
    if blocked_hash is not None and (
        not _is_exact_str(blocked_hash) or not _HEX_RE.match(blocked_hash)
    ):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_INVALID,
                "baffle_geometry_result.blocked_result_hash",
                "task024_result_invalid",
            )
        )
        return None
    return task024_models.BaffleGeometryValidationResult(
        status=status,
        geometry=geometry,
        warnings=tuple(warnings_list),
        blockers=tuple(blockers_list),
        deferred_capabilities=deferred,
        blocked_result_hash=blocked_hash,
    )


def _parse_t024_message(
    value: Any, field_path: str, blockers: list[MessageEntry]
) -> task024_models.MessageEntry | None:
    parsed = _parse_message_entry(value, field_path, blockers)
    if parsed is None:
        return None
    details: list[tuple[str, str]] = []
    if _is_exact_dict(value):
        details_raw = value.get("details", [])
        if _is_exact_list(details_raw):
            for item in details_raw:
                if (
                    _is_exact_list(item)
                    and len(item) == 2
                    and all(_is_exact_str(part) for part in item)
                ):
                    details.append((item[0], item[1]))
    return task024_models.MessageEntry(
        code=parsed.code,
        field_path=parsed.field_path,
        message_key=parsed.message_key,
        evidence_refs=parsed.evidence_refs,
        details=tuple(details),
    )


def _parse_cut_chord(
    value: Any, field_path: str, blockers: list[MessageEntry]
) -> task024_models.CutChordGeometry | None:
    if not _is_exact_dict(value):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_INVALID,
                field_path,
                "task024_result_invalid",
            )
        )
        return None
    try:
        return task024_models.CutChordGeometry(
            normal_x=value["normal_x"],
            normal_y=value["normal_y"],
            half_plane_offset_m=value["half_plane_offset_m"],
            chord_half_length_m=value["chord_half_length_m"],
            endpoint_a_x_m=value["endpoint_a_x_m"],
            endpoint_a_y_m=value["endpoint_a_y_m"],
            endpoint_b_x_m=value["endpoint_b_x_m"],
            endpoint_b_y_m=value["endpoint_b_y_m"],
        )
    except (KeyError, TypeError):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_INVALID,
                field_path,
                "task024_result_invalid",
            )
        )
        return None


def _parse_physical_tube_disk_audit(
    value: Any,
    field_path: str,
    blockers: list[MessageEntry],
) -> task024_models.PhysicalTubeDiskAudit | None:
    if not _is_exact_dict(value):
        return None
    try:
        return task024_models.PhysicalTubeDiskAudit(
            physical_tube_radius_m=value["physical_tube_radius_m"],
            signed_window_distance_m=value["signed_window_distance_m"],
            cut_boundary_margin_m=value["cut_boundary_margin_m"],
            classification=task024_models.TubeRegionClassification(value["classification"]),
        )
    except (KeyError, ValueError):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_INVALID,
                field_path,
                "task024_result_invalid",
            )
        )
        return None


def _parse_tube_hole_classification(
    value: Any,
    field_path: str,
    blockers: list[MessageEntry],
) -> task024_models.TubeHoleClassification | None:
    if not _is_exact_dict(value):
        return None
    audit = _parse_physical_tube_disk_audit(
        value.get("physical_tube_disk_audit"),
        f"{field_path}.physical_tube_disk_audit",
        blockers,
    )
    if audit is None:
        return None
    try:
        return task024_models.TubeHoleClassification(
            position_id=value["position_id"],
            center_x_m=value["center_x_m"],
            center_y_m=value["center_y_m"],
            physical_tube_radius_m=value["physical_tube_radius_m"],
            baffle_hole_radius_m=value["baffle_hole_radius_m"],
            signed_window_distance_m=value["signed_window_distance_m"],
            cut_boundary_margin_m=value["cut_boundary_margin_m"],
            classification=task024_models.TubeRegionClassification(value["classification"]),
            outer_boundary_margin_squared_m2=value["outer_boundary_margin_squared_m2"],
            physical_tube_disk_audit=audit,
        )
    except (KeyError, ValueError):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_INVALID,
                field_path,
                "task024_result_invalid",
            )
        )
        return None


def _parse_baffle_plane(
    value: Any,
    field_path: str,
    blockers: list[MessageEntry],
) -> task024_models.BafflePlaneGeometry | None:
    if not _is_exact_dict(value):
        return None
    cut_chord = _parse_cut_chord(value.get("cut_chord"), f"{field_path}.cut_chord", blockers)
    if cut_chord is None:
        return None
    classifications: list[task024_models.TubeHoleClassification] = []
    raw_classifications = value.get("tube_hole_classifications", [])
    if _is_exact_list(raw_classifications):
        for index, item in enumerate(raw_classifications):
            parsed = _parse_tube_hole_classification(
                item,
                f"{field_path}.tube_hole_classifications[{index}]",
                blockers,
            )
            if parsed is not None:
                classifications.append(parsed)
    try:
        orientation = task024_models.BaffleOrientation(value["orientation"])
        window_ids = tuple(value.get("window_position_ids", []))
        crossflow_ids = tuple(value.get("crossflow_reference_position_ids", []))
        outer_ids = tuple(value.get("outer_tangent_position_ids", []))
        pairs_raw = value.get("pairwise_tangent_position_pairs", [])
        pairs: list[tuple[str, str]] = []
        if _is_exact_list(pairs_raw):
            for item in pairs_raw:
                if _is_exact_list(item) and len(item) == 2:
                    pairs.append((item[0], item[1]))
        return task024_models.BafflePlaneGeometry(
            baffle_index=value["baffle_index"],
            center_coordinate_m=value["center_coordinate_m"],
            occupied_start_coordinate_m=value["occupied_start_coordinate_m"],
            occupied_end_coordinate_m=value["occupied_end_coordinate_m"],
            orientation=orientation,
            cut_chord=cut_chord,
            window_region_semantics=value["window_region_semantics"],
            baffle_covered_region_semantics=value["baffle_covered_region_semantics"],
            crossflow_reference_region_semantics=value["crossflow_reference_region_semantics"],
            tube_hole_classifications=tuple(classifications),
            window_position_ids=window_ids,
            crossflow_reference_position_ids=crossflow_ids,
            outer_tangent_position_ids=outer_ids,
            pairwise_tangent_position_pairs=tuple(pairs),
            classification_audit_hash=value["classification_audit_hash"],
        )
    except (KeyError, ValueError):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_INVALID,
                field_path,
                "task024_result_invalid",
            )
        )
        return None


def _parse_baffle_geometry(
    value: dict[str, Any],
    blockers: list[MessageEntry],
) -> task024_models.BaffleGeometry | None:
    design_raw_any = value.get("design_authority")
    axial_raw_any = value.get("axial_span")
    if not _is_exact_dict(design_raw_any) or not _is_exact_dict(axial_raw_any):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_INVALID,
                "baffle_geometry_result.geometry",
                "task024_result_invalid",
            )
        )
        return None
    design_raw = cast(dict[str, Any], design_raw_any)
    axial_raw = cast(dict[str, Any], axial_raw_any)
    spacing_raw = design_raw.get("spacing_sequence_m")
    if not _is_exact_list(spacing_raw):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_INVALID,
                "baffle_geometry_result.geometry.design_authority.spacing_sequence_m",
                "task024_result_invalid",
            )
        )
        return None
    spacing_list = cast(list[Any], spacing_raw)
    spacing = tuple(str(item) for item in spacing_list)
    try:
        baffle_type = task024_models.BaffleType(design_raw["baffle_type"])
        orientation_sequence = tuple(
            task024_models.BaffleOrientation(item) for item in design_raw["orientation_sequence"]
        )
    except (KeyError, ValueError):
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_INVALID,
                "baffle_geometry_result.geometry.design_authority",
                "task024_result_invalid",
            )
        )
        return None
    design = task024_models.CallerSuppliedBaffleDesignAuthority(
        schema_version=design_raw["schema_version"],
        baffle_type=baffle_type,
        baffle_count=design_raw["baffle_count"],
        baffle_thickness_m=design_raw["baffle_thickness_m"],
        spacing_sequence_m=spacing,
        baffle_cut_fraction=design_raw["baffle_cut_fraction"],
        orientation_sequence=orientation_sequence,
        shell_to_baffle_diametral_clearance_m=design_raw["shell_to_baffle_diametral_clearance_m"],
        tube_to_baffle_hole_diametral_clearance_m=design_raw[
            "tube_to_baffle_hole_diametral_clearance_m"
        ],
        evidence_refs=tuple(design_raw.get("evidence_refs", [])),
        authority_hash=design_raw["authority_hash"],
    )
    axial = task024_models.CallerSuppliedBaffleAxialSpan(
        schema_version=axial_raw["schema_version"],
        axial_start_coordinate_m=axial_raw["axial_start_coordinate_m"],
        axial_end_coordinate_m=axial_raw["axial_end_coordinate_m"],
        evidence_refs=tuple(axial_raw.get("evidence_refs", [])),
        authority_hash=axial_raw["authority_hash"],
    )
    baffle_planes: list[task024_models.BafflePlaneGeometry] = []
    planes_raw = value.get("baffle_planes", [])
    if _is_exact_list(planes_raw):
        for index, plane in enumerate(planes_raw):
            parsed_plane = _parse_baffle_plane(
                plane,
                f"baffle_geometry_result.geometry.baffle_planes[{index}]",
                blockers,
            )
            if parsed_plane is not None:
                baffle_planes.append(parsed_plane)
    warnings_list: list[task024_models.MessageEntry] = []
    for index, item in enumerate(value.get("warnings", [])):
        parsed = _parse_t024_message(
            item, f"baffle_geometry_result.geometry.warnings[{index}]", blockers
        )
        if parsed is not None:
            warnings_list.append(parsed)
    blockers_list: list[task024_models.MessageEntry] = []
    for index, item in enumerate(value.get("blockers", [])):
        parsed = _parse_t024_message(
            item, f"baffle_geometry_result.geometry.blockers[{index}]", blockers
        )
        if parsed is not None:
            blockers_list.append(parsed)
    deferred_raw = value.get("deferred_capabilities", [])
    deferred = tuple(deferred_raw) if _is_exact_list(deferred_raw) else ()
    provenance_raw = value.get("provenance", [])
    provenance_items: list[tuple[str, Any]] = []
    if _is_exact_list(provenance_raw):
        for item in provenance_raw:
            if _is_exact_list(item) and len(item) == 2:
                provenance_items.append((item[0], item[1]))
    return task024_models.BaffleGeometry(
        schema_version=value["schema_version"],
        geometry_id=value["geometry_id"],
        geometry_hash=value["geometry_hash"],
        request_hash=value["request_hash"],
        task020_configuration_id=value["task020_configuration_id"],
        task020_configuration_hash=value["task020_configuration_hash"],
        task021_layout_id=value["task021_layout_id"],
        task021_layout_hash=value["task021_layout_hash"],
        task022_geometry_id=value["task022_geometry_id"],
        task022_geometry_hash=value["task022_geometry_hash"],
        construction_family=value["construction_family"],
        equipment_orientation=value["equipment_orientation"],
        shell_pass_count=value["shell_pass_count"],
        tube_pass_count=value["tube_pass_count"],
        shell_inside_diameter_m=value["shell_inside_diameter_m"],
        tube_outer_diameter_m=value["tube_outer_diameter_m"],
        axial_span=axial,
        design_authority=design,
        usable_baffle_span_m=value["usable_baffle_span_m"],
        baffle_diameter_m=value["baffle_diameter_m"],
        baffle_radius_m=value["baffle_radius_m"],
        baffle_hole_diameter_m=value["baffle_hole_diameter_m"],
        baffle_hole_radius_m=value["baffle_hole_radius_m"],
        cut_height_m=value["cut_height_m"],
        chord_offset_from_center_m=value["chord_offset_from_center_m"],
        baffle_planes=tuple(baffle_planes),
        position_count=value.get("position_count", 0),
        warnings=tuple(warnings_list),
        blockers=tuple(blockers_list),
        deferred_capabilities=deferred,
        provenance=tuple(provenance_items),
    )


def _parse_engineering_authority(
    value: Any,
    blockers: list[MessageEntry],
) -> EngineeringAuthorityRequestBinding | None:
    if not _is_exact_dict(value):
        blockers.append(
            _message(
                BlockerCode.SSHG_RAW_TYPE_INVALID,
                "engineering_authority",
                _schema_message_key(BlockerCode.SSHG_RAW_TYPE_INVALID),
            )
        )
        return None
    expected = {"schema_version", "authority_profile_id", "authority_hash", "evidence_refs"}
    for key in value:
        if not _is_exact_str(key) or key not in expected:
            blockers.append(
                _message(
                    BlockerCode.SSHG_UNKNOWN_FIELD,
                    f"engineering_authority.{key}"
                    if _is_exact_str(key)
                    else "engineering_authority",
                    _schema_message_key(BlockerCode.SSHG_UNKNOWN_FIELD),
                )
            )
    if value.get("schema_version") != ENGINEERING_AUTHORITY_REQUEST_SCHEMA_VERSION:
        blockers.append(
            _message(
                BlockerCode.SSHG_RAW_TYPE_INVALID,
                "engineering_authority.schema_version",
                "schema_version_unsupported",
            )
        )
    if value.get("authority_profile_id") != AGGREGATE_AUTHORITY_PROFILE_ID:
        blockers.append(
            _message(
                BlockerCode.SSHG_RAW_TYPE_INVALID,
                "engineering_authority.authority_profile_id",
                "authority_profile_id_invalid",
            )
        )
    authority_hash = value.get("authority_hash")
    if not _is_exact_str(authority_hash) or not _HEX_RE.match(authority_hash):
        blockers.append(
            _message(
                BlockerCode.SSHG_RAW_TYPE_INVALID,
                "engineering_authority.authority_hash",
                "authority_hash_invalid",
            )
        )
    evidence = _evidence_refs(
        value.get("evidence_refs"), "engineering_authority.evidence_refs", blockers
    )
    if blockers:
        return None
    assert evidence is not None and authority_hash is not None
    return EngineeringAuthorityRequestBinding(
        schema_version=ENGINEERING_AUTHORITY_REQUEST_SCHEMA_VERSION,
        authority_profile_id=AGGREGATE_AUTHORITY_PROFILE_ID,
        authority_hash=authority_hash,
        evidence_refs=evidence,
    )


def parse_request(raw_request: Any) -> ShellSideHydraulicGeometryRequest:
    if not _is_exact_dict(raw_request):
        raise SchemaFailure(
            stage=_SCHEMA_STAGE,
            blockers=(_message(BlockerCode.SSHG_RAW_TYPE_INVALID, None, "raw_type_invalid"),),
            raw_failing_field=raw_request,
        )
    blockers: list[MessageEntry] = []
    for key in raw_request:
        if not _is_exact_str(key):
            blockers.append(
                _message(
                    BlockerCode.SSHG_RAW_TYPE_INVALID,
                    None,
                    _schema_message_key(BlockerCode.SSHG_RAW_TYPE_INVALID),
                )
            )
        elif key not in _TOP_LEVEL_FIELDS:
            blockers.append(
                _message(
                    BlockerCode.SSHG_UNKNOWN_FIELD,
                    key,
                    _schema_message_key(BlockerCode.SSHG_UNKNOWN_FIELD),
                )
            )
    schema_version = raw_request.get("schema_version")
    if schema_version != REQUEST_SCHEMA_VERSION:
        blockers.append(
            _message(
                BlockerCode.SSHG_SCHEMA_VERSION_UNSUPPORTED,
                "schema_version",
                _schema_message_key(BlockerCode.SSHG_SCHEMA_VERSION_UNSUPPORTED),
            )
        )
    evidence_refs = _evidence_refs(raw_request.get("evidence_refs"), "evidence_refs", blockers)
    if "tube_layout" not in raw_request:
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK021_LAYOUT_MISSING,
                "tube_layout",
                _schema_message_key(BlockerCode.SSHG_TASK021_LAYOUT_MISSING),
            )
        )
    if "baffle_geometry_result" not in raw_request:
        blockers.append(
            _message(
                BlockerCode.SSHG_TASK024_RESULT_MISSING,
                "baffle_geometry_result",
                _schema_message_key(BlockerCode.SSHG_TASK024_RESULT_MISSING),
            )
        )
    if "engineering_authority" not in raw_request:
        blockers.append(
            _message(
                BlockerCode.SSHG_UNKNOWN_FIELD,
                "engineering_authority",
                _schema_message_key(BlockerCode.SSHG_UNKNOWN_FIELD),
            )
        )
    if blockers:
        raise SchemaFailure(
            stage=_SCHEMA_STAGE,
            blockers=tuple(blockers),
            raw_failing_field=raw_request,
            normalized_context={},
        )
    tube_layout = _parse_tube_layout(raw_request["tube_layout"], blockers)
    baffle_result = _parse_baffle_result(raw_request["baffle_geometry_result"], blockers)
    engineering_authority = _parse_engineering_authority(
        raw_request["engineering_authority"], blockers
    )
    if blockers:
        raise SchemaFailure(
            stage=_DECODE_STAGE,
            blockers=tuple(blockers),
            raw_failing_field=raw_request,
            normalized_context={
                "request_schema_version": schema_version,
                "evidence_refs": list(evidence_refs or ()),
            },
        )
    assert tube_layout is not None
    assert baffle_result is not None
    assert engineering_authority is not None
    assert evidence_refs is not None
    return ShellSideHydraulicGeometryRequest(
        schema_version=REQUEST_SCHEMA_VERSION,
        tube_layout=tube_layout,
        baffle_geometry_result=baffle_result,
        engineering_authority=engineering_authority,
        evidence_refs=evidence_refs,
        raw_baffle_geometry_result=raw_request["baffle_geometry_result"],
    )


__all__ = ["SchemaFailure", "parse_request"]
