"""Closed raw request decoder for TASK-032 S00-S04."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, cast

from hexagent.exchangers.shell_tube.tube_layout.canonical import freeze_known_fragment
from hexagent.exchangers.shell_tube.tube_side_thermal import PhaseRegion, PropertySnapshot

from .blocker_registry import make_blocker
from .models import (
    MASS_FLOW_AUTHORITY_FIELDS,
    PROFILE_ID,
    PROPERTY_SNAPSHOT_FIELDS,
    REQUEST_FIELDS,
    REQUEST_SCHEMA_VERSION,
    TASK031_GEOMETRY_FIELDS,
    TASK031_RESULT_FIELDS,
    BlockerCode,
    ShellSideFlowStateRequest,
    ShellSideMassFlowAuthority,
    Task031GeometryBinding,
    Task031ResultBinding,
)

_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


class SchemaFailure(Exception):
    def __init__(
        self,
        *,
        stage: str,
        blockers: tuple[Any, ...],
        raw_failing_field: Any,
        normalized_context: Any = (),
    ) -> None:
        super().__init__(stage)
        self.stage = stage
        self.blockers = blockers
        self.raw_failing_field = raw_failing_field
        self.normalized_context = normalized_context


def _is_dict(value: Any) -> bool:
    return type(value) is dict


def _is_list(value: Any) -> bool:
    return type(value) is list


def _is_str(value: Any) -> bool:
    return type(value) is str


def _hex(value: Any) -> bool:
    return _is_str(value) and _HEX_RE.fullmatch(value) is not None


def _message(
    code: BlockerCode,
    *,
    stage: str,
    field_path: str | None,
    value: Any = None,
) -> Any:
    payload = None if value is None else {"value": value}
    return make_blocker(code, stage=stage, field_path=field_path, payload=payload)


def _canonical_decimal(
    value: Any,
    field_path: str,
    blockers: list[Any],
    *,
    stage: str = "S01",
) -> Decimal | None:
    if not _is_str(value) or value != value.strip() or value.startswith("+"):
        blockers.append(
            _message(
                BlockerCode.SSFS_DECIMAL_LEXICAL_INVALID,
                stage=stage,
                field_path=field_path,
                value=value,
            )
        )
        return None
    if not value or "e" in value.lower():
        blockers.append(
            _message(
                BlockerCode.SSFS_DECIMAL_LEXICAL_INVALID,
                stage=stage,
                field_path=field_path,
                value=value,
            )
        )
        return None
    try:
        parsed = Decimal(value)
    except Exception:
        parsed = Decimal("NaN")
    if not parsed.is_finite() or format(parsed, "f") != value:
        blockers.append(
            _message(
                BlockerCode.SSFS_DECIMAL_LEXICAL_INVALID,
                stage=stage,
                field_path=field_path,
                value=value,
            )
        )
        return None
    return parsed


def _hash_field(value: Any, field_path: str, blockers: list[Any]) -> str | None:
    if not _hex(value):
        blockers.append(
            _message(
                BlockerCode.SSFS_PROPERTY_SNAPSHOT_INVALID,
                stage="S03",
                field_path=field_path,
                value=value,
            )
        )
        return None
    return cast(str, value)


def _refs(
    value: Any, field_path: str, blockers: list[Any], *, stage: str
) -> tuple[str, ...] | None:
    if not _is_list(value) or not value or any(not _is_str(item) or not item for item in value):
        blockers.append(
            _message(
                BlockerCode.SSFS_EVIDENCE_REFS_INVALID,
                stage=stage,
                field_path=field_path,
            )
        )
        return None
    if len(set(value)) != len(value):
        blockers.append(
            _message(
                BlockerCode.SSFS_EVIDENCE_REFS_INVALID,
                stage=stage,
                field_path=field_path,
            )
        )
        return None
    return tuple(sorted(value))


def _freeze(value: Any, field_path: str, blockers: list[Any], *, stage: str) -> Any:
    try:
        return freeze_known_fragment(value)
    except Exception:
        blockers.append(
            _message(BlockerCode.SSFS_RAW_TYPE_INVALID, stage=stage, field_path=field_path)
        )
        return None


def _fragment_tuple(
    value: Any, field_path: str, blockers: list[Any], *, stage: str
) -> tuple[Any, ...]:
    if not _is_list(value):
        blockers.append(
            _message(BlockerCode.SSFS_RAW_TYPE_INVALID, stage=stage, field_path=field_path)
        )
        return ()
    result: list[Any] = []
    for index, item in enumerate(value):
        frozen = _freeze(item, f"{field_path}[{index}]", blockers, stage=stage)
        if frozen is not None:
            result.append(frozen)
    return tuple(result)


def _provenance(
    value: Any, field_path: str, blockers: list[Any], *, stage: str
) -> tuple[tuple[str, Any], ...]:
    if not _is_list(value):
        blockers.append(
            _message(BlockerCode.SSFS_RAW_TYPE_INVALID, stage=stage, field_path=field_path)
        )
        return ()
    result: list[tuple[str, Any]] = []
    for index, item in enumerate(value):
        if not _is_list(item) or len(item) != 2 or not _is_str(item[0]):
            blockers.append(
                _message(
                    BlockerCode.SSFS_RAW_TYPE_INVALID,
                    stage=stage,
                    field_path=f"{field_path}[{index}]",
                )
            )
            continue
        frozen = _freeze(item[1], f"{field_path}[{index}][1]", blockers, stage=stage)
        if frozen is not None:
            result.append((item[0], frozen))
    return tuple(result)


def _require_closed(
    value: Any, fields: tuple[str, ...], path: str, blockers: list[Any], *, stage: str
) -> bool:
    if not _is_dict(value):
        blockers.append(_message(BlockerCode.SSFS_RAW_TYPE_INVALID, stage=stage, field_path=path))
        return False
    allowed = set(fields)
    for key in value:
        if not _is_str(key):
            blockers.append(_message(BlockerCode.SSFS_UNKNOWN_FIELD, stage=stage, field_path=path))
        elif key not in allowed:
            blockers.append(
                _message(BlockerCode.SSFS_UNKNOWN_FIELD, stage=stage, field_path=f"{path}.{key}")
            )
    missing = [field for field in fields if field not in value]
    if missing:
        blockers.append(
            _message(
                BlockerCode.SSFS_RAW_TYPE_INVALID, stage=stage, field_path=f"{path}.{missing[0]}"
            )
        )
    return not blockers


def _parse_geometry(value: Any) -> Task031GeometryBinding:
    blockers: list[Any] = []
    _require_closed(
        value, TASK031_GEOMETRY_FIELDS, "task031_result.geometry", blockers, stage="S02"
    )
    if blockers:
        raise SchemaFailure(stage="S02", blockers=tuple(blockers), raw_failing_field=value)
    assert isinstance(value, dict)
    required_string_fields = {
        "schema_version",
        "geometry_id",
        "geometry_hash",
        "request_hash",
        "task020_configuration_id",
        "task020_configuration_hash",
        "task021_layout_id",
        "task021_layout_hash",
        "task022_geometry_id",
        "task022_geometry_hash",
        "task024_geometry_id",
        "task024_geometry_hash",
        "engineering_authority_id",
        "engineering_authority_hash",
        "formula_a_id",
        "formula_b_id",
        "pattern_family",
        "flow_region_identity",
        "central_inter_baffle_spacing_m",
        "central_crossflow_flow_area_m2",
        "shell_side_equivalent_hydraulic_diameter_m",
    }
    for name in required_string_fields:
        if not _is_str(value[name]):
            blockers.append(
                _message(
                    BlockerCode.SSFS_TASK031_RESULT_INVALID,
                    stage="S02",
                    field_path=f"task031_result.geometry.{name}",
                )
            )
    warnings = _fragment_tuple(
        value["warnings"], "task031_result.geometry.warnings", blockers, stage="S02"
    )
    upstream_blockers = _fragment_tuple(
        value["blockers"], "task031_result.geometry.blockers", blockers, stage="S02"
    )
    deferred_raw = value["deferred_capabilities"]
    if not _is_list(deferred_raw) or any(not _is_str(item) for item in deferred_raw):
        blockers.append(
            _message(
                BlockerCode.SSFS_TASK031_RESULT_INVALID,
                stage="S02",
                field_path="task031_result.geometry.deferred_capabilities",
            )
        )
        deferred = ()
    else:
        deferred = tuple(deferred_raw)
    provenance = _provenance(
        value["provenance"], "task031_result.geometry.provenance", blockers, stage="S02"
    )
    if blockers:
        raise SchemaFailure(stage="S02", blockers=tuple(blockers), raw_failing_field=value)
    return Task031GeometryBinding(
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
        task024_geometry_id=value["task024_geometry_id"],
        task024_geometry_hash=value["task024_geometry_hash"],
        engineering_authority_id=value["engineering_authority_id"],
        engineering_authority_hash=value["engineering_authority_hash"],
        formula_a_id=value["formula_a_id"],
        formula_b_id=value["formula_b_id"],
        pattern_family=value["pattern_family"],
        flow_region_identity=value["flow_region_identity"],
        central_inter_baffle_spacing_m=value["central_inter_baffle_spacing_m"],
        central_crossflow_flow_area_m2=value["central_crossflow_flow_area_m2"],
        shell_side_equivalent_hydraulic_diameter_m=value[
            "shell_side_equivalent_hydraulic_diameter_m"
        ],
        warnings=warnings,
        blockers=upstream_blockers,
        deferred_capabilities=deferred,
        provenance=provenance,
    )


def _parse_task031(value: Any) -> Task031ResultBinding:
    blockers: list[Any] = []
    if not _require_closed(value, TASK031_RESULT_FIELDS, "task031_result", blockers, stage="S02"):
        raise SchemaFailure(stage="S02", blockers=tuple(blockers), raw_failing_field=value)
    assert isinstance(value, dict)
    if value["status"] != "VALID":
        blockers.append(
            _message(
                BlockerCode.SSFS_TASK031_RESULT_INVALID,
                stage="S02",
                field_path="task031_result.status",
            )
        )
    geometry_value = value["geometry"]
    geometry = None if geometry_value is None else _parse_geometry(geometry_value)
    warnings = _fragment_tuple(value["warnings"], "task031_result.warnings", blockers, stage="S02")
    upstream_blockers = _fragment_tuple(
        value["blockers"], "task031_result.blockers", blockers, stage="S02"
    )
    deferred_raw = value["deferred_capabilities"]
    if not _is_list(deferred_raw) or any(not _is_str(item) for item in deferred_raw):
        blockers.append(
            _message(
                BlockerCode.SSFS_TASK031_RESULT_INVALID,
                stage="S02",
                field_path="task031_result.deferred_capabilities",
            )
        )
        deferred = ()
    else:
        deferred = tuple(deferred_raw)
    blocked_hash = value["blocked_result_hash"]
    if blocked_hash is not None and not _is_str(blocked_hash):
        blockers.append(
            _message(
                BlockerCode.SSFS_TASK031_RESULT_INVALID,
                stage="S02",
                field_path="task031_result.blocked_result_hash",
            )
        )
        blocked_hash = None
    if blockers:
        raise SchemaFailure(stage="S02", blockers=tuple(blockers), raw_failing_field=value)
    return Task031ResultBinding(
        status=value["status"],
        geometry=geometry,
        warnings=warnings,
        blockers=upstream_blockers,
        deferred_capabilities=deferred,
        blocked_result_hash=blocked_hash,
    )


def _unsafe_snapshot(values: dict[str, Any]) -> PropertySnapshot:
    snapshot = object.__new__(PropertySnapshot)
    for name, value in values.items():
        object.__setattr__(snapshot, name, value)
    return snapshot


def _parse_property_snapshot(value: Any) -> PropertySnapshot:
    blockers: list[Any] = []
    _require_closed(value, PROPERTY_SNAPSHOT_FIELDS, "property_snapshot", blockers, stage="S03")
    if blockers:
        raise SchemaFailure(stage="S03", blockers=tuple(blockers), raw_failing_field=value)
    assert isinstance(value, dict)
    numeric: dict[str, Decimal] = {}
    for name in PROPERTY_SNAPSHOT_FIELDS[:6]:
        parsed = _canonical_decimal(value[name], f"property_snapshot.{name}", blockers, stage="S03")
        if parsed is None:
            continue
        if parsed <= 0:
            blockers.append(
                _message(
                    BlockerCode.SSFS_PROPERTY_SNAPSHOT_INVALID,
                    stage="S03",
                    field_path=f"property_snapshot.{name}",
                )
            )
        numeric[name] = parsed
    phase_raw = value["phase_region"]
    if not _is_str(phase_raw):
        blockers.append(
            _message(
                BlockerCode.SSFS_PROPERTY_SNAPSHOT_INVALID,
                stage="S03",
                field_path="property_snapshot.phase_region",
            )
        )
        phase: Any = phase_raw
    else:
        try:
            phase = PhaseRegion(phase_raw)
        except ValueError:
            # Keep the lexical token so S06 can report the closed applicability blocker.
            phase = phase_raw
    source_id = value["property_source_id"]
    source_version = value["property_source_version"]
    if not _is_str(source_id) or not source_id or not _is_str(source_version) or not source_version:
        blockers.append(
            _message(
                BlockerCode.SSFS_PROPERTY_SNAPSHOT_INVALID,
                stage="S03",
                field_path="property_snapshot.property_source_id",
            )
        )
    snapshot_hash = _hash_field(
        value["property_snapshot_hash"], "property_snapshot.property_snapshot_hash", blockers
    )
    if blockers:
        raise SchemaFailure(stage="S03", blockers=tuple(blockers), raw_failing_field=value)
    values: dict[str, Any] = {
        **numeric,
        "phase_region": phase,
        "property_source_id": source_id,
        "property_source_version": source_version,
        "property_snapshot_hash": snapshot_hash,
    }
    if isinstance(phase, PhaseRegion):
        try:
            return PropertySnapshot(**values)
        except Exception as exc:
            raise SchemaFailure(
                stage="S03",
                blockers=(
                    _message(
                        BlockerCode.SSFS_PROPERTY_SNAPSHOT_INVALID,
                        stage="S03",
                        field_path="property_snapshot",
                    ),
                ),
                raw_failing_field=value,
            ) from exc
    return _unsafe_snapshot(values)


def _parse_mass_flow_authority(value: Any) -> ShellSideMassFlowAuthority:
    blockers: list[Any] = []
    _require_closed(value, MASS_FLOW_AUTHORITY_FIELDS, "mass_flow_authority", blockers, stage="S04")
    if blockers:
        raise SchemaFailure(stage="S04", blockers=tuple(blockers), raw_failing_field=value)
    assert isinstance(value, dict)
    string_fields = {
        "schema_version",
        "authority_profile_id",
        "shell_side_case_id",
        "shell_side_stream_id",
        "shell_side_fluid_id",
        "rheology_model",
        "task020_configuration_id",
        "task020_configuration_hash",
        "task031_geometry_id",
        "task031_geometry_hash",
        "property_snapshot_hash",
        "property_state_role",
        "mass_flow_sign_convention",
        "authority_source_id",
        "authority_source_version",
        "authority_hash",
    }
    for name in string_fields:
        if not _is_str(value[name]):
            blockers.append(
                _message(
                    BlockerCode.SSFS_MASS_FLOW_AUTHORITY_INVALID,
                    stage="S04",
                    field_path=f"mass_flow_authority.{name}",
                )
            )
    mass_flow = _canonical_decimal(
        value["mass_flow_rate_kg_s"],
        "mass_flow_authority.mass_flow_rate_kg_s",
        blockers,
        stage="S04",
    )
    refs = _refs(value["evidence_refs"], "mass_flow_authority.evidence_refs", blockers, stage="S04")
    if refs is None:
        refs = ()
    if not _hex(value["authority_hash"]):
        blockers.append(
            _message(
                BlockerCode.SSFS_MASS_FLOW_AUTHORITY_INVALID,
                stage="S04",
                field_path="mass_flow_authority.authority_hash",
            )
        )
    if blockers:
        raise SchemaFailure(stage="S04", blockers=tuple(blockers), raw_failing_field=value)
    assert mass_flow is not None
    return ShellSideMassFlowAuthority(
        schema_version=value["schema_version"],
        authority_profile_id=value["authority_profile_id"],
        shell_side_case_id=value["shell_side_case_id"],
        shell_side_stream_id=value["shell_side_stream_id"],
        shell_side_fluid_id=value["shell_side_fluid_id"],
        rheology_model=value["rheology_model"],
        task020_configuration_id=value["task020_configuration_id"],
        task020_configuration_hash=value["task020_configuration_hash"],
        task031_geometry_id=value["task031_geometry_id"],
        task031_geometry_hash=value["task031_geometry_hash"],
        property_snapshot_hash=value["property_snapshot_hash"],
        property_state_role=value["property_state_role"],
        mass_flow_rate_kg_s=mass_flow,
        mass_flow_sign_convention=value["mass_flow_sign_convention"],
        authority_source_id=value["authority_source_id"],
        authority_source_version=value["authority_source_version"],
        evidence_refs=refs,
        authority_hash=value["authority_hash"],
    )


def parse_request(raw_request: Any) -> ShellSideFlowStateRequest:
    """Decode exact built-in dict input; raise a staged SchemaFailure."""

    if type(raw_request) is not dict:
        raise SchemaFailure(
            stage="S00",
            blockers=(_message(BlockerCode.SSFS_RAW_TYPE_INVALID, stage="S00", field_path=None),),
            raw_failing_field=raw_request,
        )
    blockers: list[Any] = []
    _require_closed(raw_request, REQUEST_FIELDS, "request", blockers, stage="S01")
    if raw_request.get("schema_version") != REQUEST_SCHEMA_VERSION:
        blockers.append(
            _message(
                BlockerCode.SSFS_SCHEMA_VERSION_UNSUPPORTED,
                stage="S01",
                field_path="schema_version",
            )
        )
    if raw_request.get("profile_id") != PROFILE_ID:
        blockers.append(
            _message(BlockerCode.SSFS_PROFILE_ID_UNSUPPORTED, stage="S01", field_path="profile_id")
        )
    if "task031_result" not in raw_request:
        blockers.append(
            _message(
                BlockerCode.SSFS_TASK031_RESULT_MISSING, stage="S01", field_path="task031_result"
            )
        )
    if "property_snapshot" not in raw_request:
        blockers.append(
            _message(
                BlockerCode.SSFS_PROPERTY_SNAPSHOT_MISSING,
                stage="S01",
                field_path="property_snapshot",
            )
        )
    if "mass_flow_authority" not in raw_request:
        blockers.append(
            _message(
                BlockerCode.SSFS_MASS_FLOW_AUTHORITY_MISSING,
                stage="S01",
                field_path="mass_flow_authority",
            )
        )
    if "evidence_refs" in raw_request:
        _refs(raw_request["evidence_refs"], "evidence_refs", blockers, stage="S01")
    if blockers:
        raise SchemaFailure(stage="S01", blockers=tuple(blockers), raw_failing_field=raw_request)
    task031 = _parse_task031(raw_request["task031_result"])
    property_snapshot = _parse_property_snapshot(raw_request["property_snapshot"])
    mass_flow = _parse_mass_flow_authority(raw_request["mass_flow_authority"])
    refs = _refs(raw_request["evidence_refs"], "evidence_refs", [], stage="S01")
    assert refs is not None
    property_hash = raw_request["property_snapshot_hash"]
    if not _hex(property_hash):
        raise SchemaFailure(
            stage="S03",
            blockers=(
                _message(
                    BlockerCode.SSFS_PROPERTY_SNAPSHOT_INVALID,
                    stage="S03",
                    field_path="property_snapshot_hash",
                ),
            ),
            raw_failing_field=property_hash,
        )
    return ShellSideFlowStateRequest(
        schema_version=raw_request["schema_version"],
        profile_id=raw_request["profile_id"],
        task031_result=task031,
        property_snapshot_hash=property_hash,
        property_snapshot=property_snapshot,
        mass_flow_authority=mass_flow,
        evidence_refs=refs,
    )


__all__ = ["SchemaFailure", "parse_request"]
