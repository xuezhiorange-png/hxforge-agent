"""Strict typed admission for TASK-167."""

from __future__ import annotations

from dataclasses import fields
from decimal import Decimal
from typing import Any, NoReturn, cast

from hexagent.exchangers.shell_tube.bell_delaware.models import Task166Result
from hexagent.exchangers.shell_tube.models import (
    AuthorityMode,
    EvaluatedRulePackAuthority,
    ShellAndTubeConfiguration,
    StandardClaimStatus,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import TubeSideThermalResult

from . import authority
from .errors import BlockerCode
from .models import (
    FoulingTendency,
    NozzleGeometryAuthority,
    ScreeningPropertySnapshot,
    ScreeningRequirements,
    Task167Request,
)


class SchemaFailure(ValueError):
    def __init__(self, code: BlockerCode, field_path: str, message: str = "") -> None:
        super().__init__(message or code.value)
        self.code = code
        self.field_path = field_path


def _fail(code: BlockerCode, path: str, message: str = "") -> NoReturn:
    raise SchemaFailure(code, path, message)


def _nonempty(value: Any, path: str) -> str:
    if type(value) is not str or not value:
        _fail(BlockerCode.INVALID_REQUEST_SCHEMA, path)
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise SchemaFailure(BlockerCode.RAW_UNICODE_ENCODING_FAILURE, path) from exc
    return value


def _finite_decimal(value: Any, path: str, *, positive: bool = False) -> Decimal:
    if type(value) is not Decimal or not value.is_finite() or (positive and value <= Decimal("0")):
        _fail(BlockerCode.SCREENING_PROPERTY_AUTHORITY_INVALID, path)
    return value


def _metadata(value: Any) -> tuple[tuple[str, str], ...]:
    if type(value) is not tuple:
        _fail(BlockerCode.INVALID_REQUEST_SCHEMA, "request_metadata")
    seen: set[str] = set()
    for index, item in enumerate(value):
        if type(item) is not tuple or len(item) != 2:
            _fail(BlockerCode.INVALID_REQUEST_SCHEMA, f"request_metadata[{index}]")
        key, val = item
        if type(key) is not str or type(val) is not str:
            _fail(BlockerCode.INVALID_REQUEST_SCHEMA, f"request_metadata[{index}]")
        if key in seen:
            _fail(BlockerCode.INVALID_REQUEST_SCHEMA, f"request_metadata[{index}].key")
        seen.add(key)
        try:
            key.encode("utf-8", "strict")
            val.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise SchemaFailure(
                BlockerCode.RAW_UNICODE_ENCODING_FAILURE, f"request_metadata[{index}]"
            ) from exc
    return cast(tuple[tuple[str, str], ...], value)


def _check_configuration(value: Any) -> ShellAndTubeConfiguration:
    if type(value) is not ShellAndTubeConfiguration:
        _fail(BlockerCode.INVALID_TASK020_CONFIGURATION, "task020_configuration")
    if value.blockers:
        _fail(BlockerCode.TASK020_AUTHORITY_INVALID, "task020_configuration.blockers")
    if type(value.authority_mode) is not AuthorityMode:
        _fail(BlockerCode.TASK020_AUTHORITY_INVALID, "task020_configuration.authority_mode")
    if type(value.standard_claim_status) is not StandardClaimStatus:
        _fail(BlockerCode.TASK020_AUTHORITY_INVALID, "task020_configuration.standard_claim_status")
    if value.authority_mode is AuthorityMode.INTERNAL_GENERIC:
        if value.standard_claim_status is not StandardClaimStatus.NO_STANDARD_CLAIM:
            _fail(
                BlockerCode.TASK020_AUTHORITY_INVALID, "task020_configuration.standard_claim_status"
            )
    elif value.standard_claim_status is not StandardClaimStatus.RULE_PACK_VALIDATED:
        _fail(BlockerCode.TASK020_AUTHORITY_INVALID, "task020_configuration.standard_claim_status")
    if type(value.shell_pass_count) is not int or type(value.tube_pass_count) is not int:
        _fail(BlockerCode.INVALID_TASK020_CONFIGURATION, "task020_configuration.pass_count")
    if not value.configuration_id or not value.configuration_hash:
        _fail(BlockerCode.INVALID_TASK020_CONFIGURATION, "task020_configuration.identity")
    return value


def _check_task166(value: Any) -> Task166Result:
    if type(value) is not Task166Result:
        _fail(BlockerCode.TASK166_AUTHORITY_INVALID, "task166_result")
    if value.blockers:
        _fail(BlockerCode.TASK166_AUTHORITY_INVALID, "task166_result.blockers")
    if value.applicability is None or value.applicability.status.value != "APPLICABLE":
        _fail(BlockerCode.TASK166_NOT_APPLICABLE, "task166_result.applicability")
    if value.completeness is None or value.completeness.status != "COMPLETE":
        _fail(BlockerCode.TASK166_NOT_COMPLETE, "task166_result.completeness")
    if value.bell_geometry is None or not value.result_hash or not value.result_id:
        _fail(BlockerCode.TASK166_AUTHORITY_INVALID, "task166_result.identity")
    return value


def _check_tube(value: Any) -> TubeSideThermalResult:
    if type(value) is not TubeSideThermalResult:
        _fail(BlockerCode.TUBE_SIDE_AUTHORITY_INVALID, "tube_side_result")
    if value.blockers:
        _fail(BlockerCode.TUBE_SIDE_AUTHORITY_INVALID, "tube_side_result.blockers")
    if not value.result_hash or not value.result_id:
        _fail(BlockerCode.TUBE_SIDE_IDENTITY_REPLAY_FAILED, "tube_side_result.identity")
    _finite_decimal(value.bulk_velocity_m_s, "tube_side_result.bulk_velocity_m_s", positive=True)
    _finite_decimal(
        value.mass_flow_rate_kg_s, "tube_side_result.mass_flow_rate_kg_s", positive=True
    )
    return value


def _check_requirements(value: Any) -> ScreeningRequirements:
    if type(value) is not ScreeningRequirements:
        _fail(BlockerCode.SCREENING_REQUIREMENTS_INVALID, "screening_requirements")
    if type(value.authority_mode) is not AuthorityMode:
        _fail(BlockerCode.SCREENING_REQUIREMENTS_INVALID, "screening_requirements.authority_mode")
    if type(value.shell_side_fouling_tendency) is not FoulingTendency:
        _fail(
            BlockerCode.SCREENING_REQUIREMENTS_INVALID,
            "screening_requirements.shell_side_fouling_tendency",
        )
    if type(value.tube_side_fouling_tendency) is not FoulingTendency:
        _fail(
            BlockerCode.SCREENING_REQUIREMENTS_INVALID,
            "screening_requirements.tube_side_fouling_tendency",
        )
    for name in (
        "shell_side_mechanical_cleaning_required",
        "tube_side_mechanical_cleaning_required",
        "thermal_expansion_accommodation_required",
        "removable_bundle_required",
    ):
        item = getattr(value, name)
        if item is not None and type(item) is not bool:
            _fail(BlockerCode.SCREENING_REQUIREMENTS_INVALID, f"screening_requirements.{name}")
    if type(value.nozzle_velocity_screen_required) is not bool:
        _fail(
            BlockerCode.SCREENING_REQUIREMENTS_INVALID,
            "screening_requirements.nozzle_velocity_screen_required",
        )
    for name in ("requirement_id", "source_id", "source_version", "evidence_ref", "snapshot_hash"):
        item = getattr(value, name)
        _nonempty(item, f"screening_requirements.{name}")
    return value


def _check_snapshot(value: Any) -> ScreeningPropertySnapshot:
    if type(value) is not ScreeningPropertySnapshot:
        _fail(BlockerCode.SCREENING_PROPERTY_AUTHORITY_INVALID, "screening_property_snapshot")
    for name in ("snapshot_id", "source_id", "source_version", "evidence_ref", "snapshot_hash"):
        _nonempty(getattr(value, name), f"screening_property_snapshot.{name}")
    decimal_names = tuple(
        item.name
        for item in fields(value)
        if item.name
        not in {"snapshot_id", "source_id", "source_version", "evidence_ref", "snapshot_hash"}
    )
    for name in decimal_names:
        item = getattr(value, name)
        if item is not None:
            _finite_decimal(item, f"screening_property_snapshot.{name}")
    positive_names = (
        "fluid_density_kg_m3",
        "nozzle_mass_flow_rate_kg_s",
        "nozzle_density_kg_m3",
        "tube_free_span_m",
        "tube_material_density_kg_m3",
        "tube_mass_per_length_kg_m",
        "young_modulus_pa",
        "coefficient_thermal_expansion_per_k",
        "effective_length_m",
        "natural_frequency_hz",
    )
    for name in positive_names:
        item = getattr(value, name)
        if item is not None and item <= Decimal("0"):
            _fail(
                BlockerCode.SCREENING_PROPERTY_AUTHORITY_INVALID,
                f"screening_property_snapshot.{name}",
            )
    for name in ("shell_bulk_velocity_m_s", "shell_crossflow_velocity_m_s"):
        item = getattr(value, name)
        if item is not None and item < Decimal("0"):
            _fail(
                BlockerCode.SCREENING_PROPERTY_AUTHORITY_INVALID,
                f"screening_property_snapshot.{name}",
            )
    if value.added_mass_kg_m is not None and value.added_mass_kg_m < Decimal("0"):
        _fail(
            BlockerCode.SCREENING_PROPERTY_AUTHORITY_INVALID,
            "screening_property_snapshot.added_mass_kg_m",
        )
    if value.damping_ratio is not None and value.damping_ratio < Decimal("0"):
        _fail(
            BlockerCode.SCREENING_PROPERTY_AUTHORITY_INVALID,
            "screening_property_snapshot.damping_ratio",
        )
    return value


def _check_nozzle(value: Any) -> NozzleGeometryAuthority | None:
    if value is None:
        return None
    if type(value) is not NozzleGeometryAuthority:
        _fail(BlockerCode.NOZZLE_AUTHORITY_INVALID, "nozzle_geometry")
    for name in ("authority_id", "source_id", "source_version", "evidence_ref", "snapshot_hash"):
        _nonempty(getattr(value, name), f"nozzle_geometry.{name}")
    _finite_decimal(value.flow_area_m2, "nozzle_geometry.flow_area_m2", positive=True)
    return cast(NozzleGeometryAuthority | None, value)


def parse_request(raw: object) -> Task167Request:
    if type(raw) is Task167Request:
        request = raw
    elif type(raw) is dict:
        allowed = {
            "schema_version",
            "task167_version",
            "source_definition_id",
            "task020_configuration",
            "task166_result",
            "tube_side_result",
            "screening_requirements",
            "screening_property_snapshot",
            "nozzle_geometry",
            "approved_rule_pack_authority",
            "request_metadata",
        }
        if set(raw) - allowed:
            _fail(BlockerCode.INVALID_REQUEST_SCHEMA, "request")
        required = {
            "schema_version",
            "task167_version",
            "source_definition_id",
            "task020_configuration",
            "task166_result",
            "tube_side_result",
            "screening_requirements",
            "screening_property_snapshot",
        }
        if not required.issubset(raw):
            _fail(BlockerCode.INVALID_REQUEST_SCHEMA, "request")
        request = Task167Request(
            schema_version=raw["schema_version"],
            task167_version=raw["task167_version"],
            source_definition_id=raw["source_definition_id"],
            task020_configuration=raw["task020_configuration"],
            task166_result=raw["task166_result"],
            tube_side_result=raw["tube_side_result"],
            screening_requirements=raw["screening_requirements"],
            screening_property_snapshot=raw["screening_property_snapshot"],
            nozzle_geometry=raw.get("nozzle_geometry"),
            approved_rule_pack_authority=raw.get("approved_rule_pack_authority"),
            request_metadata=raw.get("request_metadata", ()),
        )
    else:
        _fail(BlockerCode.INVALID_REQUEST_SCHEMA, "request")

    if request.schema_version != authority.REQUEST_SCHEMA_VERSION:
        _fail(BlockerCode.INVALID_REQUEST_SCHEMA, "schema_version")
    if request.task167_version != authority.TASK167_VERSION:
        _fail(BlockerCode.INVALID_REQUEST_SCHEMA, "task167_version")
    if request.source_definition_id != authority.SOURCE_DEFINITION_ID:
        _fail(BlockerCode.SOURCE_DEFINITION_MISMATCH, "source_definition_id")
    _check_configuration(request.task020_configuration)
    _check_task166(request.task166_result)
    _check_tube(request.tube_side_result)
    requirements = _check_requirements(request.screening_requirements)
    if requirements.authority_mode is not request.task020_configuration.authority_mode:
        _fail(BlockerCode.SCREENING_REQUIREMENTS_INVALID, "screening_requirements.authority_mode")
    _check_snapshot(request.screening_property_snapshot)
    _check_nozzle(request.nozzle_geometry)
    _metadata(request.request_metadata)
    if request.task020_configuration.authority_mode is AuthorityMode.APPROVED_RULE_PACK:
        if type(request.approved_rule_pack_authority) is not EvaluatedRulePackAuthority:
            _fail(BlockerCode.RULE_PACK_REQUIRED, "approved_rule_pack_authority")
    elif request.approved_rule_pack_authority is not None:
        _fail(BlockerCode.RULE_PACK_INVALID, "approved_rule_pack_authority")
    return request


__all__ = ["SchemaFailure", "parse_request"]
