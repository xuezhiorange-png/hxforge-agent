"""TASK-168 deterministic candidate generation and producer orchestration."""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from itertools import product
from typing import Any, cast

from hexagent.exchangers.shell_tube import validate_request as validate_task020
from hexagent.exchangers.shell_tube.baffle_geometry import canonical as task024_canonical
from hexagent.exchangers.shell_tube.baffle_geometry import validate_request as validate_task024
from hexagent.exchangers.shell_tube.baffle_geometry.models import (
    BaffleGeometry,
    BaffleOrientation,
    BaffleType,
)
from hexagent.exchangers.shell_tube.bell_delaware import canonical as task166_canonical
from hexagent.exchangers.shell_tube.bell_delaware import validate_request as validate_task166
from hexagent.exchangers.shell_tube.bell_delaware.models import Task166Result
from hexagent.exchangers.shell_tube.engineering_screening import canonical as task167_canonical
from hexagent.exchangers.shell_tube.engineering_screening import (
    validate_request as validate_task167,
)
from hexagent.exchangers.shell_tube.engineering_screening.models import Task167Result
from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority import (
    validate_request as validate_task161,
)
from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority.models import (
    Task161Result,
)
from hexagent.exchangers.shell_tube.models import ConstructionFamily, ShellAndTubeConfiguration
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua import (
    build_raw_overall_u_ua_request,
    evaluate_task038,
    service_binding_hash,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
    Task038SuccessResult,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.provenance import (
    verify_provenance as verify_task038_provenance,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.validation import (
    verify_task038_success_identity,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance import evaluate_task037
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.models import (
    Task037SuccessResult,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.validation import (
    verify_task037_success_identity,
)
from hexagent.exchangers.shell_tube.shell_bundle_geometry import canonical as task022_canonical
from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
    validate_request as validate_task022,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state import (
    validate_request as validate_task032,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.canonical import (
    mass_flow_authority_hash,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.schema import (
    parse_request as parse_task032_request,
)
from hexagent.exchangers.shell_tube.shell_side_heat_transfer import (
    validate_request as validate_task033,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    validate_request as validate_task031,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import canonical as task034_canonical
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import (
    validate_request as validate_task034,
)
from hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition import (
    validate_request as validate_task035,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure import (
    issue_success_replay_evidence,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure import (
    validate_request as validate_task162,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure.models import (
    Task162CaseAuthority,
    Task162CrossProducerBindingAuthority,
    Task162Request,
    Task162Result,
    Task162SuccessReplayEvidence,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure.service import (
    verify_task162_success,
)
from hexagent.exchangers.shell_tube.thermal_stream_state import (
    validate_request as validate_task160,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.models import Task160Result
from hexagent.exchangers.shell_tube.tube_layout import canonical as task021_canonical
from hexagent.exchangers.shell_tube.tube_layout import validate_request as validate_task021
from hexagent.exchangers.shell_tube.tube_layout.canonical import internal_frozen_to_primitive
from hexagent.exchangers.shell_tube.tube_layout.canonical import layout_id as task021_layout_id
from hexagent.exchangers.shell_tube.tube_layout.models import TubeLayout
from hexagent.exchangers.shell_tube.tube_side import (
    HeatTransferLengthAuthority,
    InternalFlowLengthAuthority,
    ReferencePlanePair,
    Task025HydraulicParticipationAuthority,
    Task025ValidResult,
    evaluate_task025,
)
from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    compute_task027_friction_pressure_drop,
)
from hexagent.exchangers.shell_tube.tube_side.hash_dag import (
    heat_transfer_authority_length_hash,
    hydraulic_authority_hash,
    internal_flow_authority_length_hash,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss import compute_task028_local_loss
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition import (
    compute_task029_composition,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    ProducerTask,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    TubeSideThermalRequest,
    build_raw_tube_side_request_envelope,
    compute_tube_side_heat_transfer_coefficient,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import TubeSideThermalResult
from hexagent.shell_geometry_catalogs.models import ShellGeometryCatalog, ShellGeometryRecord

from .canonical import (
    batch_result_hash,
    candidate_hash,
    candidate_id,
    candidate_space_hash,
    candidate_space_id,
    discrete_authority_hash,
    raw_blocked_hash,
    raw_blocked_id,
    request_hash,
    requirement_authority_hash,
    result_id,
    shell_catalog_hash,
    shell_record_hash,
    typed_blocked_hash,
    typed_blocked_id,
)
from .errors import BlockerCode
from .models import (
    DIMENSION_ORDER,
    MAX_DISCRETE_VALUES_PER_DIMENSION,
    MAX_MATERIALIZED_CANDIDATE_COUNT,
    MAX_RAW_COMBINATION_COUNT,
    REQUEST_FIELDS,
    REQUIRED_DISCRETE_ROLES,
    TASK168_BLOCKED_SCHEMA_VERSION,
    TASK168_COMPLETENESS_FIELDS,
    TASK168_IMPLEMENTATION_SOFTWARE_VERSION,
    TASK168_RAW_BLOCKED_SCHEMA_VERSION,
    TASK168_RESULT_SCHEMA_VERSION,
    TASK168_SCHEMA_VERSION,
    TASK168_SOURCE_DEFINITION_ID,
    TASK168_VERSION,
    ApplicabilityStatus,
    CandidateDimensionAuthorityBinding,
    CandidateDisposition,
    CandidateRecord,
    CandidateSpec,
    CandidateStage,
    CandidateStatus,
    CompletenessStatus,
    DiscreteAuthoritySource,
    DiscreteCandidateSetAuthority,
    DiscreteDimensionRole,
    ProvenanceGraph,
    Task168Applicability,
    Task168BatchResult,
    Task168Blocker,
    Task168Completeness,
    Task168EvaluationInputAuthority,
    Task168RawBoundaryBlockedResult,
    Task168Request,
    Task168RequirementAuthority,
    Task168TypedBlockedResult,
    Task168ValidationResult,
    Task168Warning,
    ValidationStatus,
)
from .provenance import build_batch_provenance, verify_provenance_graph
from .raw_projection import (
    RawProjectionFailure,
    project_raw,
    raw_projection_hash_from_projection,
)

TASK168_TASK160_V06_ENVELOPE_AUTHORITY_ID = "A06_V06_SHELL_TUBE_THERMAL_ENVELOPE"
TASK168_TASK160_V06_ENVELOPE_SOURCE_ID = "TASK169-V06-THERMAL-CLOSURE-AUTHORITY"
TASK168_TASK160_V06_ENVELOPE_SOURCE_VERSION = "v0.6"
TASK168_TASK160_V06_ENVELOPE_EVIDENCE_REF = "TASK169-THERMAL-CLOSURE-AUTHORITY-V06"

_DECIMAL_ROLES = frozenset(
    {
        DiscreteDimensionRole.TUBE_OUTER_DIAMETER,
        DiscreteDimensionRole.TUBE_WALL_THICKNESS,
        DiscreteDimensionRole.TUBE_LENGTH,
        DiscreteDimensionRole.TUBE_PITCH,
        DiscreteDimensionRole.BAFFLE_CUT,
        DiscreteDimensionRole.BAFFLE_SPACING,
    }
)
_INTEGER_ROLES = frozenset(
    {DiscreteDimensionRole.TUBE_PASS_COUNT, DiscreteDimensionRole.BAFFLE_COUNT}
)
_STRING_ROLES = frozenset({DiscreteDimensionRole.TUBE_LAYOUT, DiscreteDimensionRole.BAFFLE_TYPE})


def _enum_value(value: object) -> str:
    raw = getattr(value, "value", value)
    return raw if type(raw) is str else str(type(value).__name__)


def _blocker(
    code: BlockerCode | str,
    stage: CandidateStage,
    field_path: str | None = None,
    evidence_refs: Iterable[str] = (),
    message: str = "",
) -> Task168Blocker:
    return Task168Blocker(
        code=code.value if isinstance(code, BlockerCode) else code,
        stage=stage,
        field_path=field_path,
        message=message,
        evidence_refs=tuple(sorted(tuple(evidence_refs), key=lambda item: item.encode("utf-8"))),
    )


def _ordered_blockers(values: Iterable[Task168Blocker]) -> tuple[Task168Blocker, ...]:
    unique: dict[tuple[object, ...], Task168Blocker] = {}
    for item in values:
        key = (item.code, item.stage.value, item.field_path, item.evidence_refs)
        unique[key] = item
    return tuple(sorted(unique.values(), key=lambda item: item.sort_key()))


def _ordered_warnings(values: Iterable[Task168Warning]) -> tuple[Task168Warning, ...]:
    unique: dict[tuple[str, tuple[str, ...]], Task168Warning] = {}
    for item in values:
        unique[(item.code, item.evidence_refs)] = item
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                item.code,
                tuple(ref.encode("utf-8", "strict") for ref in item.evidence_refs),
            ),
        )
    )


def _raw_blocked(projection_hash: str, failure: RawProjectionFailure) -> Task168ValidationResult:
    blocker = _blocker(
        failure.code,
        CandidateStage.CANDIDATE_AUTHORITY,
        failure.field_path,
    )
    preliminary = Task168RawBoundaryBlockedResult(
        schema_version=TASK168_RAW_BLOCKED_SCHEMA_VERSION,
        task168_version=TASK168_VERSION,
        implementation_software_version=TASK168_IMPLEMENTATION_SOFTWARE_VERSION,
        raw_request_projection_hash=projection_hash,
        blockers=(blocker,),
        warnings=(),
        result_hash="",
        result_id="",
    )
    digest = raw_blocked_hash(preliminary)
    return Task168ValidationResult(
        status=ValidationStatus.RAW_BOUNDARY_BLOCKED,
        raw_boundary_blocked=replace(
            preliminary,
            result_hash=digest,
            result_id=raw_blocked_id(digest),
        ),
    )


def _typed_blocked(
    request_hash_value: str,
    blockers: Iterable[Task168Blocker],
) -> Task168ValidationResult:
    ordered = _ordered_blockers(blockers)
    preliminary = Task168TypedBlockedResult(
        schema_version=TASK168_BLOCKED_SCHEMA_VERSION,
        task168_version=TASK168_VERSION,
        implementation_software_version=TASK168_IMPLEMENTATION_SOFTWARE_VERSION,
        request_hash=request_hash_value,
        blockers=ordered,
        warnings=(),
        result_hash="",
        result_id="",
    )
    digest = typed_blocked_hash(preliminary)
    return Task168ValidationResult(
        status=ValidationStatus.TYPED_BLOCKED,
        typed_blocked=replace(
            preliminary,
            result_hash=digest,
            result_id=typed_blocked_id(digest),
        ),
    )


def _parse_request(raw: object) -> Task168Request | None:
    if type(raw) is Task168Request:
        return raw
    if type(raw) is not dict:
        return None
    if set(raw) != set(REQUEST_FIELDS):
        return None
    try:
        authorities = raw["discrete_candidate_set_authorities"]
        evaluation_inputs = raw["evaluation_input_authority"]
        metadata = raw["request_metadata"]
        if type(authorities) is list:
            authorities = tuple(authorities)
        if type(metadata) is list:
            metadata = tuple(tuple(item) for item in metadata)
        return Task168Request(
            schema_version=raw["schema_version"],
            task168_version=raw["task168_version"],
            source_definition_id=raw["source_definition_id"],
            task020_configuration=raw["task020_configuration"],
            requirement_authority=raw["requirement_authority"],
            shell_geometry_catalog=raw["shell_geometry_catalog"],
            discrete_candidate_set_authorities=authorities,
            evaluation_input_authority=evaluation_inputs,
            request_metadata=metadata,
        )
    except (KeyError, TypeError, ValueError):
        return None


def _is_finite_positive(value: object) -> bool:
    return type(value) is Decimal and value.is_finite() and value > Decimal("0")


def _valid_metadata(value: object) -> bool:
    if type(value) is not tuple:
        return False
    seen: set[str] = set()
    for item in value:
        if type(item) is not tuple or len(item) != 2:
            return False
        key, text = item
        if type(key) is not str or type(text) is not str:
            return False
        try:
            key.encode("utf-8", "strict")
            text.encode("utf-8", "strict")
        except UnicodeEncodeError:
            return False
        if key in seen:
            return False
        seen.add(key)
    return tuple(value) == tuple(
        sorted(value, key=lambda item: (item[0].encode("utf-8"), item[1].encode("utf-8")))
    )


def _valid_requirement(value: object) -> tuple[Task168Blocker, ...]:
    if type(value) is not Task168RequirementAuthority:
        return (
            _blocker(BlockerCode.REQUIREMENT_AUTHORITY_INVALID, CandidateStage.TYPED_VALIDATION),
        )
    requirement = value
    failures: list[Task168Blocker] = []
    for name in ("requirement_id", "authority_version", "source_class", "source_id"):
        if type(getattr(requirement, name)) is not str or not getattr(requirement, name):
            failures.append(
                _blocker(
                    BlockerCode.REQUIREMENT_AUTHORITY_INVALID,
                    CandidateStage.TYPED_VALIDATION,
                    f"requirement_authority.{name}",
                )
            )
    if requirement.approval_status != "APPROVED":
        failures.append(
            _blocker(
                BlockerCode.REQUIREMENT_AUTHORITY_INVALID,
                CandidateStage.TYPED_VALIDATION,
                "requirement_authority.approval_status",
            )
        )
    families = requirement.allowed_construction_families
    if (
        type(families) is not tuple
        or not families
        or any(type(item) is not ConstructionFamily for item in families)
        or len(set(families)) != len(families)
    ):
        failures.append(
            _blocker(
                BlockerCode.REQUIREMENT_AUTHORITY_INVALID,
                CandidateStage.TYPED_VALIDATION,
                "requirement_authority.allowed_construction_families",
            )
        )
    for name in ("required_duty_w", "max_tube_dp_pa", "max_shell_dp_pa"):
        item = getattr(requirement, name)
        if item is not None and not _is_finite_positive(item):
            failures.append(
                _blocker(
                    BlockerCode.REQUIREMENT_AUTHORITY_INVALID,
                    CandidateStage.TYPED_VALIDATION,
                    f"requirement_authority.{name}",
                )
            )
    if any(type(item) is not str or not item for item in requirement.evidence_refs):
        failures.append(
            _blocker(
                BlockerCode.REQUIREMENT_AUTHORITY_INVALID,
                CandidateStage.TYPED_VALIDATION,
                "requirement_authority.evidence_refs",
            )
        )
    if any(type(item) is not str or not item for item in requirement.provenance_refs):
        failures.append(
            _blocker(
                BlockerCode.REQUIREMENT_AUTHORITY_INVALID,
                CandidateStage.TYPED_VALIDATION,
                "requirement_authority.provenance_refs",
            )
        )
    try:
        if requirement.canonical_hash != requirement_authority_hash(requirement):
            failures.append(
                _blocker(
                    BlockerCode.REQUIREMENT_AUTHORITY_INVALID,
                    CandidateStage.TYPED_VALIDATION,
                    "requirement_authority.canonical_hash",
                )
            )
    except (TypeError, ValueError, UnicodeError):
        failures.append(
            _blocker(
                BlockerCode.REQUIREMENT_AUTHORITY_INVALID,
                CandidateStage.TYPED_VALIDATION,
                "requirement_authority.canonical_hash",
            )
        )
    return _ordered_blockers(failures)


def _valid_catalog(value: object) -> tuple[Task168Blocker, ...]:
    if type(value) is not ShellGeometryCatalog:
        return (_blocker(BlockerCode.SHELL_CATALOG_INVALID, CandidateStage.TYPED_VALIDATION),)
    catalog = value
    failures: list[Task168Blocker] = []
    if not catalog.records:
        failures.append(
            _blocker(BlockerCode.SHELL_CATALOG_INVALID, CandidateStage.TYPED_VALIDATION)
        )
    for index, record in enumerate(catalog.records):
        path = f"shell_geometry_catalog.records[{index}]"
        if type(record) is not ShellGeometryRecord:
            failures.append(
                _blocker(
                    BlockerCode.SHELL_CATALOG_RECORD_INVALID, CandidateStage.TYPED_VALIDATION, path
                )
            )
            continue
        if record.approval_state != "approved" or not record.geometry_id:
            failures.append(
                _blocker(
                    BlockerCode.SHELL_CATALOG_RECORD_INVALID, CandidateStage.TYPED_VALIDATION, path
                )
            )
        try:
            diameter = Decimal(record.shell_inside_diameter_m)
            if not diameter.is_finite() or diameter <= 0:
                raise InvalidOperation
            if record.record_hash != shell_record_hash(record):
                failures.append(
                    _blocker(
                        BlockerCode.SHELL_CATALOG_RECORD_INVALID,
                        CandidateStage.TYPED_VALIDATION,
                        f"{path}.record_hash",
                    )
                )
        except (InvalidOperation, ValueError, TypeError, UnicodeError):
            failures.append(
                _blocker(
                    BlockerCode.SHELL_CATALOG_RECORD_INVALID, CandidateStage.TYPED_VALIDATION, path
                )
            )
    try:
        if catalog.catalog_hash != shell_catalog_hash(catalog):
            failures.append(
                _blocker(
                    BlockerCode.SHELL_CATALOG_INVALID,
                    CandidateStage.TYPED_VALIDATION,
                    "shell_geometry_catalog.catalog_hash",
                )
            )
    except (TypeError, ValueError, UnicodeError):
        failures.append(
            _blocker(
                BlockerCode.SHELL_CATALOG_INVALID,
                CandidateStage.TYPED_VALIDATION,
                "shell_geometry_catalog.catalog_hash",
            )
        )
    return _ordered_blockers(failures)


def _value_key(value: object) -> tuple[str, object]:
    if type(value) is Decimal:
        return ("Decimal", value)
    if type(value) is int:
        return ("int", value)
    if type(value) is str:
        return ("str", value)
    if type(value) is ConstructionFamily:
        return ("ConstructionFamily", value.value)
    return (
        f"{type(value).__module__}.{type(value).__qualname__}",
        f"{type(value).__module__}.{type(value).__qualname__}",
    )


def _validate_discrete_authority(
    value: object,
    index: int,
) -> tuple[Task168Blocker, ...]:
    path = f"discrete_candidate_set_authorities[{index}]"
    if type(value) is not DiscreteCandidateSetAuthority:
        return (
            _blocker(BlockerCode.DISCRETE_AUTHORITY_INVALID, CandidateStage.TYPED_VALIDATION, path),
        )
    authority = value
    failures: list[Task168Blocker] = []
    for name in ("authority_id", "authority_version", "source_id", "source_revision"):
        if type(getattr(authority, name)) is not str or not getattr(authority, name):
            failures.append(
                _blocker(
                    BlockerCode.DISCRETE_AUTHORITY_INVALID,
                    CandidateStage.TYPED_VALIDATION,
                    f"{path}.{name}",
                )
            )
    if type(authority.dimension_role) is not DiscreteDimensionRole:
        failures.append(
            _blocker(
                BlockerCode.UNKNOWN_DIMENSION_ROLE,
                CandidateStage.TYPED_VALIDATION,
                f"{path}.dimension_role",
            )
        )
    if type(authority.source_class) is not DiscreteAuthoritySource:
        failures.append(
            _blocker(
                BlockerCode.DISCRETE_AUTHORITY_INVALID,
                CandidateStage.TYPED_VALIDATION,
                f"{path}.source_class",
            )
        )
    if authority.approval_status != "APPROVED":
        failures.append(
            _blocker(
                BlockerCode.DISCRETE_AUTHORITY_UNAPPROVED,
                CandidateStage.TYPED_VALIDATION,
                f"{path}.approval_status",
            )
        )
    if not authority.evidence_refs or any(
        type(item) is not str or not item for item in authority.evidence_refs
    ):
        failures.append(
            _blocker(
                BlockerCode.DISCRETE_AUTHORITY_EVIDENCE_MISSING,
                CandidateStage.TYPED_VALIDATION,
                f"{path}.evidence_refs",
            )
        )
    if any(type(item) is not str or not item for item in authority.provenance_refs):
        failures.append(
            _blocker(
                BlockerCode.DISCRETE_AUTHORITY_EVIDENCE_MISSING,
                CandidateStage.TYPED_VALIDATION,
                f"{path}.provenance_refs",
            )
        )
    values = authority.values
    if type(values) is not tuple or not values or len(values) > MAX_DISCRETE_VALUES_PER_DIMENSION:
        failures.append(
            _blocker(
                BlockerCode.DISCRETE_AUTHORITY_INVALID,
                CandidateStage.TYPED_VALIDATION,
                f"{path}.values",
            )
        )
    else:
        keys: list[tuple[str, object]] = []
        for value_item in values:
            role = authority.dimension_role
            valid = type(role) is DiscreteDimensionRole and (
                (
                    role is DiscreteDimensionRole.CONSTRUCTION_FAMILY
                    and type(value_item) is ConstructionFamily
                )
                or (role in _DECIMAL_ROLES and _is_finite_positive(value_item))
                or (role in _INTEGER_ROLES and type(value_item) is int and value_item > 0)
                or (role in _STRING_ROLES and type(value_item) is str and bool(value_item))
            )
            if not valid:
                failures.append(
                    _blocker(
                        BlockerCode.DISCRETE_AUTHORITY_INVALID,
                        CandidateStage.TYPED_VALIDATION,
                        f"{path}.values",
                    )
                )
            else:
                keys.append(_value_key(value_item))
        if len(keys) != len(set(keys)):
            failures.append(
                _blocker(
                    BlockerCode.DUPLICATE_DISCRETE_MEMBER,
                    CandidateStage.TYPED_VALIDATION,
                    f"{path}.values",
                )
            )
    try:
        if authority.canonical_hash != discrete_authority_hash(authority):
            failures.append(
                _blocker(
                    BlockerCode.DISCRETE_AUTHORITY_HASH_MISMATCH,
                    CandidateStage.TYPED_VALIDATION,
                    f"{path}.canonical_hash",
                )
            )
    except (TypeError, ValueError, UnicodeError):
        failures.append(
            _blocker(
                BlockerCode.DISCRETE_AUTHORITY_HASH_MISMATCH,
                CandidateStage.TYPED_VALIDATION,
                f"{path}.canonical_hash",
            )
        )
    return _ordered_blockers(failures)


def _validate_typed_request(request: Task168Request) -> tuple[Task168Blocker, ...]:
    failures: list[Task168Blocker] = []
    if request.schema_version != TASK168_SCHEMA_VERSION:
        failures.append(
            _blocker(
                BlockerCode.INVALID_REQUEST_SCHEMA,
                CandidateStage.TYPED_VALIDATION,
                "schema_version",
            )
        )
    if request.task168_version != TASK168_VERSION:
        failures.append(
            _blocker(
                BlockerCode.INVALID_REQUEST_SCHEMA,
                CandidateStage.TYPED_VALIDATION,
                "task168_version",
            )
        )
    if request.source_definition_id != TASK168_SOURCE_DEFINITION_ID:
        failures.append(
            _blocker(
                BlockerCode.SOURCE_DEFINITION_MISMATCH,
                CandidateStage.TYPED_VALIDATION,
                "source_definition_id",
            )
        )
    if type(request.task020_configuration) is not ShellAndTubeConfiguration:
        failures.append(
            _blocker(
                BlockerCode.CONFIGURATION_AUTHORITY_INVALID,
                CandidateStage.TYPED_VALIDATION,
                "task020_configuration",
            )
        )
    else:
        config = request.task020_configuration
        if not config.configuration_id or not config.configuration_hash:
            failures.append(
                _blocker(
                    BlockerCode.CONFIGURATION_AUTHORITY_INVALID,
                    CandidateStage.TYPED_VALIDATION,
                    "task020_configuration",
                )
            )
    if not _valid_metadata(request.request_metadata):
        failures.append(
            _blocker(
                BlockerCode.INVALID_REQUEST_SCHEMA,
                CandidateStage.TYPED_VALIDATION,
                "request_metadata",
            )
        )
    failures.extend(_valid_requirement(request.requirement_authority))
    failures.extend(_valid_catalog(request.shell_geometry_catalog))

    authorities = request.discrete_candidate_set_authorities
    if type(authorities) is not tuple or not authorities:
        failures.append(
            _blocker(
                BlockerCode.DISCRETE_AUTHORITY_INVALID,
                CandidateStage.TYPED_VALIDATION,
                "discrete_candidate_set_authorities",
            )
        )
    else:
        for index, item in enumerate(authorities):
            failures.extend(_validate_discrete_authority(item, index))
        roles = [
            item.dimension_role.value
            for item in authorities
            if type(item) is DiscreteCandidateSetAuthority
            and type(item.dimension_role) is DiscreteDimensionRole
        ]
        if len(roles) != len(set(roles)) or set(roles) != set(REQUIRED_DISCRETE_ROLES):
            failures.append(
                _blocker(
                    BlockerCode.DISCRETE_AUTHORITY_INVALID,
                    CandidateStage.TYPED_VALIDATION,
                    "discrete_candidate_set_authorities.dimension_role",
                )
            )
        if type(request.requirement_authority) is Task168RequirementAuthority:
            allowed = set(request.requirement_authority.allowed_construction_families)
            construction = next(
                (
                    item
                    for item in authorities
                    if type(item) is DiscreteCandidateSetAuthority
                    and item.dimension_role is DiscreteDimensionRole.CONSTRUCTION_FAMILY
                ),
                None,
            )
            if construction is not None and any(
                item not in allowed for item in construction.values
            ):
                failures.append(
                    _blocker(
                        BlockerCode.DISCRETE_AUTHORITY_INVALID,
                        CandidateStage.TYPED_VALIDATION,
                        "CONSTRUCTION_FAMILY",
                    )
                )

    evaluation_inputs = request.evaluation_input_authority
    if type(evaluation_inputs) is not Task168EvaluationInputAuthority:
        failures.append(
            _blocker(
                BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                CandidateStage.TYPED_VALIDATION,
                "evaluation_input_authority",
            )
        )
    else:
        for name in (
            "authority_id",
            "authority_version",
            "source_class",
            "source_id",
            "source_revision",
        ):
            value = getattr(evaluation_inputs, name)
            if type(value) is not str or not value:
                failures.append(
                    _blocker(
                        BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                        CandidateStage.TYPED_VALIDATION,
                        f"evaluation_input_authority.{name}",
                    )
                )
        if evaluation_inputs.approval_status != "APPROVED":
            failures.append(
                _blocker(
                    BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                    CandidateStage.TYPED_VALIDATION,
                    "evaluation_input_authority.approval_status",
                )
            )
        for name in ("evidence_refs", "provenance_refs"):
            values = getattr(evaluation_inputs, name)
            if (
                type(values) is not tuple
                or not values
                or any(type(item) is not str or not item for item in values)
            ):
                failures.append(
                    _blocker(
                        BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                        CandidateStage.TYPED_VALIDATION,
                        f"evaluation_input_authority.{name}",
                    )
                )
        try:
            from .canonical import evaluation_input_authority_hash

            if evaluation_inputs.canonical_hash != evaluation_input_authority_hash(
                evaluation_inputs
            ):
                failures.append(
                    _blocker(
                        BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                        CandidateStage.TYPED_VALIDATION,
                        "evaluation_input_authority.canonical_hash",
                    )
                )
        except (TypeError, ValueError, UnicodeError, ArithmeticError):
            failures.append(
                _blocker(
                    BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                    CandidateStage.TYPED_VALIDATION,
                    "evaluation_input_authority.canonical_hash",
                )
            )
    return _ordered_blockers(failures)


def _sort_values(values: tuple[Any, ...]) -> tuple[Any, ...]:
    def key(value: Any) -> tuple[int, object]:
        if type(value) is Decimal:
            return (0, value)
        if type(value) is int:
            return (1, value)
        if type(value) is ConstructionFamily:
            return (2, value.value.encode("utf-8"))
        if type(value) is str:
            return (3, value.encode("utf-8"))
        return (4, type(value).__qualname__.encode("utf-8"))

    return tuple(sorted(values, key=key))


def _authority_map(request: Task168Request) -> dict[str, DiscreteCandidateSetAuthority]:
    return {item.dimension_role.value: item for item in request.discrete_candidate_set_authorities}


def _candidate(
    request: Task168Request,
    authorities: dict[str, DiscreteCandidateSetAuthority],
    record: ShellGeometryRecord,
    values: tuple[Any, ...],
) -> CandidateSpec:
    by_role = dict(
        zip((role for role in DIMENSION_ORDER if role != "SHELL_GEOMETRY_ID"), values, strict=True)
    )
    bindings = [
        (
            "SHELL_GEOMETRY_ID",
            f"{request.shell_geometry_catalog.catalog_id}:{record.geometry_id}:{record.record_hash}",
        )
    ]
    for role in DIMENSION_ORDER:
        if role == "SHELL_GEOMETRY_ID":
            continue
        bindings.append((role, authorities[role].authority_id))
    dimension_authority_bindings = tuple(
        CandidateDimensionAuthorityBinding(
            dimension_role=authorities[role].dimension_role,
            authority_id=authorities[role].authority_id,
            authority_version=authorities[role].authority_version,
            canonical_hash=authorities[role].canonical_hash,
            source_class=authorities[role].source_class,
            source_id=authorities[role].source_id,
            source_revision=authorities[role].source_revision,
            evidence_refs=authorities[role].evidence_refs,
            provenance_refs=authorities[role].provenance_refs,
            selected_member=by_role[role],
        )
        for role in REQUIRED_DISCRETE_ROLES
    )
    candidate = CandidateSpec(
        candidate_id="",
        candidate_hash="",
        case_authority_id=request.task020_configuration.case_authority.revision_id,
        construction_family=cast(ConstructionFamily, by_role["CONSTRUCTION_FAMILY"]),
        shell_geometry_id=record.geometry_id,
        shell_record_hash=record.record_hash,
        shell_inside_diameter_m=Decimal(record.shell_inside_diameter_m),
        tube_outer_diameter_m=cast(Decimal, by_role["TUBE_OUTER_DIAMETER"]),
        tube_wall_thickness_m=cast(Decimal, by_role["TUBE_WALL_THICKNESS"]),
        tube_length_m=cast(Decimal, by_role["TUBE_LENGTH"]),
        tube_pitch_m=cast(Decimal, by_role["TUBE_PITCH"]),
        tube_layout=cast(str, by_role["TUBE_LAYOUT"]),
        tube_pass_count=cast(int, by_role["TUBE_PASS_COUNT"]),
        baffle_type=cast(str, by_role["BAFFLE_TYPE"]),
        baffle_cut_fraction=cast(Decimal, by_role["BAFFLE_CUT"]),
        baffle_spacing_m=cast(Decimal, by_role["BAFFLE_SPACING"]),
        baffle_count=cast(int, by_role["BAFFLE_COUNT"]),
        authority_bindings=tuple(bindings),
        dimension_authority_bindings=dimension_authority_bindings,
    )
    digest = candidate_hash(candidate)
    return replace(candidate, candidate_hash=digest, candidate_id=candidate_id(digest))


def _dimension_authority_bridge_ref(binding: CandidateDimensionAuthorityBinding) -> str:
    """Return a stable evidence edge for one selected discrete authority."""

    return (
        "TASK168_DISCRETE_AUTHORITY::"
        + binding.dimension_role.value
        + "::"
        + binding.canonical_hash
    )


def _candidate_dimension_authority_refs(
    candidate: CandidateSpec,
    roles: Iterable[str] | None = None,
) -> tuple[str, ...]:
    allowed = None if roles is None else frozenset(roles)
    refs = [
        _dimension_authority_bridge_ref(binding)
        for binding in candidate.dimension_authority_bindings
        if allowed is None or binding.dimension_role.value in allowed
    ]
    return tuple(sorted(set(refs), key=lambda item: item.encode("utf-8")))


def _merge_evidence_refs(value: object, additions: Iterable[str]) -> list[str]:
    """Add authority bridge refs while preserving canonical evidence semantics."""

    if type(value) not in {list, tuple}:
        raise TypeError("evidence_refs must be a list or tuple")
    raw_refs = list(cast(Iterable[object], value)) + list(additions)
    if any(type(item) is not str or not item for item in raw_refs):
        raise TypeError("evidence_refs must contain non-empty strings")
    refs = cast(list[str], raw_refs)
    return sorted(set(refs), key=lambda item: item.encode("utf-8", "strict"))


def _task021_candidate_geometry_authority(
    candidate: CandidateSpec,
    tube_geometry: Mapping[str, object],
) -> tuple[str, dict[str, object], str]:
    """Materialize a candidate-specific TASK-021 tube authority.

    The request template contributes the structural/base geometry authority;
    it does not authorize changed OD or wall values.  A deterministic bridge
    identity retains the base source binding and the exact selected discrete
    authority bindings, then becomes the source binding of the materialized
    snapshot consumed by TASK-021.
    """

    base_source = tube_geometry.get("source_binding")
    if type(base_source) is not dict:
        raise TypeError("tube_geometry.source_binding must be a mapping")
    source_fields = (
        "source_id",
        "source_type",
        "source_revision",
        "source_location",
        "evidence_ref",
        "approved_by",
        "approved_at",
    )
    if any(type(base_source.get(field)) is not str for field in source_fields):
        raise TypeError("tube_geometry.source_binding is incomplete")
    selected_refs = _candidate_dimension_authority_refs(
        candidate, ("TUBE_OUTER_DIAMETER", "TUBE_WALL_THICKNESS")
    )
    bridge_payload = {
        "base_geometry_id": tube_geometry.get("geometry_id"),
        "base_geometry_type": tube_geometry.get("geometry_type"),
        "base_revision": tube_geometry.get("revision"),
        "base_approval_state": tube_geometry.get("approval_state"),
        "base_source_binding": base_source,
        "candidate_hash": candidate.candidate_hash,
        "selected_authority_refs": list(selected_refs),
        "selected_outer_diameter_m": str(candidate.tube_outer_diameter_m),
        "selected_wall_thickness_m": str(candidate.tube_wall_thickness_m),
    }
    bridge_hash = task021_canonical.sha256_hex(bridge_payload)
    bridge_evidence_ref = "TASK168_TUBE_GEOMETRY_AUTHORITY::" + bridge_hash
    materialized_source = {
        "source_id": "TASK168-DERIVED-TUBE-GEOMETRY::" + bridge_hash,
        "source_type": "TASK168_DERIVED_DISCRETE_AUTHORITY",
        "source_revision": "TASK168::" + bridge_hash,
        "source_location": "task168://candidate-tube-geometry/" + bridge_hash,
        "evidence_ref": bridge_evidence_ref,
        "approved_by": "TASK168_DISCRETE_AUTHORITY_BRIDGE",
        "approved_at": base_source["approved_at"],
    }
    materialized_geometry_id = "TASK168-TUBE-GEOMETRY::" + bridge_hash
    return materialized_geometry_id, materialized_source, bridge_evidence_ref


def _base_record(
    candidate: CandidateSpec,
    *,
    stage: CandidateStage,
    blockers: Iterable[Task168Blocker] = (),
    last_successful_stage: CandidateStage | None = None,
    disposition: CandidateDisposition = CandidateDisposition.BLOCKED,
    status: CandidateStatus = CandidateStatus.BLOCKED,
    **kwargs: Any,
) -> CandidateRecord:
    return CandidateRecord(
        candidate_id=candidate.candidate_id,
        candidate_hash=candidate.candidate_hash,
        candidate=candidate,
        disposition=disposition,
        status=status,
        stage=stage,
        last_successful_stage=last_successful_stage,
        blockers=_ordered_blockers(blockers),
        **kwargs,
    )


def _structural_blockers(candidate: CandidateSpec) -> tuple[Task168Blocker, ...]:
    failures: list[Task168Blocker] = []
    if candidate.tube_outer_diameter_m <= 0:
        failures.append(
            _blocker(
                BlockerCode.CANDIDATE_GEOMETRY_INVALID,
                CandidateStage.CANDIDATE_AUTHORITY,
                "tube_outer_diameter_m",
            )
        )
    if candidate.tube_wall_thickness_m <= 0:
        failures.append(
            _blocker(
                BlockerCode.CANDIDATE_GEOMETRY_INVALID,
                CandidateStage.CANDIDATE_AUTHORITY,
                "tube_wall_thickness_m",
            )
        )
    if candidate.tube_length_m <= 0:
        failures.append(
            _blocker(
                BlockerCode.CANDIDATE_GEOMETRY_INVALID,
                CandidateStage.CANDIDATE_AUTHORITY,
                "tube_length_m",
            )
        )
    if candidate.tube_pitch_m <= 0:
        failures.append(
            _blocker(
                BlockerCode.CANDIDATE_GEOMETRY_INVALID,
                CandidateStage.CANDIDATE_AUTHORITY,
                "tube_pitch_m",
            )
        )
    if candidate.baffle_spacing_m <= 0:
        failures.append(
            _blocker(
                BlockerCode.CANDIDATE_GEOMETRY_INVALID,
                CandidateStage.BAFFLE_GEOMETRY,
                "baffle_spacing_m",
            )
        )
    if candidate.tube_wall_thickness_m * Decimal("2") >= candidate.tube_outer_diameter_m:
        failures.append(
            _blocker(
                BlockerCode.CANDIDATE_GEOMETRY_INVALID,
                CandidateStage.CANDIDATE_AUTHORITY,
                "tube_wall_thickness_m",
            )
        )
    if candidate.tube_pitch_m <= candidate.tube_outer_diameter_m:
        failures.append(
            _blocker(
                BlockerCode.CANDIDATE_GEOMETRY_INVALID,
                CandidateStage.CANDIDATE_AUTHORITY,
                "tube_pitch_m",
            )
        )
    if candidate.baffle_cut_fraction <= 0 or candidate.baffle_cut_fraction >= 1:
        failures.append(
            _blocker(
                BlockerCode.CANDIDATE_GEOMETRY_INVALID,
                CandidateStage.BAFFLE_GEOMETRY,
                "baffle_cut_fraction",
            )
        )
    if candidate.baffle_count <= 0 or candidate.tube_pass_count <= 0:
        failures.append(
            _blocker(
                BlockerCode.CANDIDATE_GEOMETRY_INVALID,
                CandidateStage.BAFFLE_GEOMETRY,
                "baffle_count",
            )
        )
    return _ordered_blockers(failures)


def _text(value: object) -> str:
    if type(value) is Decimal:
        return str(value)
    if type(value) is str:
        return value
    if type(value) is int or type(value) is bool:
        return str(value)
    return str(value)


def _evidence(value: object, *, result_name: str = "result") -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for name in (
        "result_hash",
        "result_id",
        "layout_hash",
        "layout_id",
        "geometry_hash",
        "geometry_id",
    ):
        item = getattr(value, name, None)
        if item is not None and (type(item) is str or type(item).__module__ == "uuid"):
            pairs.append((name if name != "result_hash" else result_name + "_hash", _text(item)))
    return tuple(pairs)


def _decimal_attr(value: object, name: str) -> Decimal | None:
    item = getattr(value, name, None)
    if type(item) is Decimal and item.is_finite():
        return item
    if type(item) is str:
        try:
            result = Decimal(item)
        except InvalidOperation:
            return None
        return result if result.is_finite() else None
    return None


def _legacy_context_blockers(
    request: Task168Request,
    candidate: CandidateSpec,
    context: Any,
) -> tuple[Task168Blocker, ...]:
    """Replay each producer boundary in frozen stage order."""

    try:
        configuration = _materialize_candidate_configuration(
            request.task020_configuration,
            candidate,
        )
    except _StageFailure as failure:
        return (
            _blocker(
                failure.code,
                failure.stage,
                failure.field_path,
                message=failure.message,
            ),
        )
    layout = context.task021_layout
    if type(layout) is not TubeLayout or not layout.layout_id or not layout.layout_hash:
        return (
            _blocker(
                BlockerCode.TASK021_REPLAY_FAILED, CandidateStage.TUBE_LAYOUT, "task021_layout"
            ),
        )
    try:
        if task021_layout_id(layout.layout_hash) != layout.layout_id:
            return (
                _blocker(
                    BlockerCode.TASK021_REPLAY_FAILED,
                    CandidateStage.TUBE_LAYOUT,
                    "task021_layout.layout_id",
                ),
            )
    except (TypeError, ValueError):
        return (
            _blocker(
                BlockerCode.TASK021_REPLAY_FAILED, CandidateStage.TUBE_LAYOUT, "task021_layout"
            ),
        )
    if (
        layout.task020_configuration_id != configuration.configuration_id
        or layout.task020_configuration_hash != configuration.configuration_hash
    ):
        return (
            _blocker(
                BlockerCode.UPSTREAM_CASE_BINDING_MISMATCH,
                CandidateStage.TUBE_LAYOUT,
                "task021_layout.task020_configuration",
            ),
        )

    geometry = context.task022_geometry
    if (
        geometry is None
        or not getattr(geometry, "geometry_id", "")
        or not getattr(geometry, "geometry_hash", "")
    ):
        return (
            _blocker(
                BlockerCode.TASK022_REPLAY_FAILED,
                CandidateStage.SHELL_BUNDLE_GEOMETRY,
                "task022_geometry",
            ),
        )
    if (
        getattr(geometry, "task021_layout_id", None) != layout.layout_id
        or getattr(geometry, "task021_layout_hash", None) != layout.layout_hash
    ):
        return (
            _blocker(
                BlockerCode.UPSTREAM_CASE_BINDING_MISMATCH,
                CandidateStage.SHELL_BUNDLE_GEOMETRY,
                "task022_geometry.task021_layout",
            ),
        )
    shell_diameter = _decimal_attr(geometry, "shell_inside_diameter_m")
    if shell_diameter != candidate.shell_inside_diameter_m:
        return (
            _blocker(
                BlockerCode.UPSTREAM_CASE_BINDING_MISMATCH,
                CandidateStage.SHELL_BUNDLE_GEOMETRY,
                "shell_inside_diameter_m",
            ),
        )

    baffle = context.task024_geometry
    if type(baffle) is not BaffleGeometry or not baffle.geometry_id or not baffle.geometry_hash:
        return (
            _blocker(
                BlockerCode.TASK024_REPLAY_FAILED,
                CandidateStage.BAFFLE_GEOMETRY,
                "task024_geometry",
            ),
        )
    if baffle.task021_layout_id != layout.layout_id or baffle.task022_geometry_id != getattr(
        geometry, "geometry_id", None
    ):
        return (
            _blocker(
                BlockerCode.UPSTREAM_CASE_BINDING_MISMATCH,
                CandidateStage.BAFFLE_GEOMETRY,
                "task024_geometry",
            ),
        )

    tube = context.task026_result
    pressure = context.task029_result
    if type(tube) is not TubeSideThermalResult or not tube.result_hash or not tube.result_id:
        return (
            _blocker(
                BlockerCode.TUBE_SIDE_REPLAY_FAILED, CandidateStage.TUBE_SIDE, "task026_result"
            ),
        )
    if (
        type(pressure) is not Task029SuccessResult
        or not pressure.result_hash
        or not pressure.result_id
    ):
        return (
            _blocker(
                BlockerCode.TUBE_SIDE_REPLAY_FAILED, CandidateStage.TUBE_SIDE, "task029_result"
            ),
        )
    if getattr(tube, "upstream_geometry_hash", None) not in {None, layout.layout_hash}:
        return (
            _blocker(
                BlockerCode.UPSTREAM_CASE_BINDING_MISMATCH,
                CandidateStage.TUBE_SIDE,
                "task026_result.upstream_geometry_hash",
            ),
        )

    bell = context.task166_result
    if type(bell) is not Task166Result:
        return (
            _blocker(
                BlockerCode.TASK166_REPLAY_FAILED, CandidateStage.SHELL_SIDE_BELL, "task166_result"
            ),
        )
    try:
        if (
            task166_canonical.result_hash(bell) != bell.result_hash
            or task166_canonical.result_id(bell.result_hash) != bell.result_id
        ):
            return (
                _blocker(
                    BlockerCode.TASK166_REPLAY_FAILED,
                    CandidateStage.SHELL_SIDE_BELL,
                    "task166_result.identity",
                ),
            )
    except (AttributeError, TypeError, ValueError, ArithmeticError):
        return (
            _blocker(
                BlockerCode.TASK166_REPLAY_FAILED,
                CandidateStage.SHELL_SIDE_BELL,
                "task166_result.identity",
            ),
        )
    if bell.applicability is None or getattr(bell.applicability, "status", None) != "APPLICABLE":
        return (
            _blocker(
                BlockerCode.TASK166_REPLAY_FAILED,
                CandidateStage.SHELL_SIDE_BELL,
                "task166_result.applicability",
            ),
        )
    if bell.completeness is None or getattr(bell.completeness, "status", None) != "COMPLETE":
        return (
            _blocker(
                BlockerCode.TASK166_REPLAY_FAILED,
                CandidateStage.SHELL_SIDE_BELL,
                "task166_result.completeness",
            ),
        )
    if bell.bell_geometry is None or bell.bell_geometry.layout_id != layout.layout_id:
        return (
            _blocker(
                BlockerCode.UPSTREAM_CASE_BINDING_MISMATCH,
                CandidateStage.SHELL_SIDE_BELL,
                "task166_result.bell_geometry",
            ),
        )

    resistance = context.task037_result
    ua = context.task038_result
    if type(resistance) is not Task037SuccessResult or not verify_task037_success_identity(
        resistance
    ):
        return (
            _blocker(
                BlockerCode.OVERALL_RESISTANCE_REPLAY_FAILED,
                CandidateStage.OVERALL_RESISTANCE,
                "task037_result",
            ),
        )
    if (
        type(ua) is not Task038SuccessResult
        or not verify_task038_success_identity(ua)
        or not verify_task038_provenance(ua.provenance)
    ):
        return (_blocker(BlockerCode.UA_REPLAY_FAILED, CandidateStage.UA, "task038_result"),)
    if getattr(
        ua.provenance, "task037_result_id", getattr(ua.provenance, "task037_identity_id", None)
    ) not in {None, resistance.result_id}:
        return (
            _blocker(
                BlockerCode.UPSTREAM_CASE_BINDING_MISMATCH,
                CandidateStage.UA,
                "task038_result.task037",
            ),
        )

    thermal = context.task162_result
    replay = context.task162_replay_evidence
    if type(thermal) is not Task162Result or type(replay) is not Task162SuccessReplayEvidence:
        return (
            _blocker(
                BlockerCode.TASK162_REPLAY_FAILED, CandidateStage.THERMAL_CLOSURE, "task162_result"
            ),
        )
    try:
        verification = verify_task162_success(thermal, replay)
        accepted = _enum_value(verification.status) == "ACCEPTED"
    except (AttributeError, TypeError, ValueError, ArithmeticError):
        accepted = False
    if not accepted:
        return (
            _blocker(
                BlockerCode.TASK162_REPLAY_FAILED, CandidateStage.THERMAL_CLOSURE, "task162_result"
            ),
        )
    if thermal.applicability.status != "APPLICABLE" or thermal.completeness.status != "COMPLETE":
        return (
            _blocker(
                BlockerCode.TASK162_REPLAY_FAILED,
                CandidateStage.THERMAL_CLOSURE,
                "task162_result.ledger",
            ),
        )

    screening = context.task167_result
    if type(screening) is not Task167Result:
        return (
            _blocker(
                BlockerCode.TASK167_REPLAY_FAILED,
                CandidateStage.ENGINEERING_SCREENING,
                "task167_result",
            ),
        )
    try:
        if (
            task167_canonical.result_hash(screening) != screening.result_hash
            or task167_canonical.result_id(screening.result_hash) != screening.result_id
        ):
            return (
                _blocker(
                    BlockerCode.TASK167_REPLAY_FAILED,
                    CandidateStage.ENGINEERING_SCREENING,
                    "task167_result.identity",
                ),
            )
    except (AttributeError, TypeError, ValueError, ArithmeticError):
        return (
            _blocker(
                BlockerCode.TASK167_REPLAY_FAILED,
                CandidateStage.ENGINEERING_SCREENING,
                "task167_result.identity",
            ),
        )
    if (
        screening.applicability is None
        or getattr(screening.applicability, "status", None) != "APPLICABLE"
    ):
        return (
            _blocker(
                BlockerCode.TASK167_REPLAY_FAILED,
                CandidateStage.ENGINEERING_SCREENING,
                "task167_result.applicability",
            ),
        )
    if (
        screening.completeness is None
        or getattr(screening.completeness, "status", None) != "COMPLETE"
    ):
        return (
            _blocker(
                BlockerCode.TASK167_REPLAY_FAILED,
                CandidateStage.ENGINEERING_SCREENING,
                "task167_result.completeness",
            ),
        )
    if getattr(screening, "task166_evidence", ()):
        evidence = dict(screening.task166_evidence)
        if evidence.get("result_hash") not in {None, bell.result_hash} or evidence.get(
            "result_id"
        ) not in {None, bell.result_id}:
            return (
                _blocker(
                    BlockerCode.UPSTREAM_CASE_BINDING_MISMATCH,
                    CandidateStage.ENGINEERING_SCREENING,
                    "task167_result.task166_evidence",
                ),
            )
    return ()


def _legacy_evaluate_candidate(
    request: Task168Request,
    candidate: CandidateSpec,
    context_by_id: dict[str, Any],
) -> CandidateRecord:
    structural = _structural_blockers(candidate)
    if structural:
        return _base_record(candidate, stage=structural[0].stage, blockers=structural)
    context = context_by_id.get(candidate.candidate_id)
    if context is None:
        return _base_record(
            candidate,
            stage=CandidateStage.CONFIGURATION,
            blockers=(
                _blocker(
                    BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                    CandidateStage.CONFIGURATION,
                    "evaluation_input_authority",
                ),
            ),
        )
    failures = _legacy_context_blockers(request, candidate, context)
    if failures:
        return _base_record(candidate, stage=failures[0].stage, blockers=failures)

    layout = cast(TubeLayout, context.task021_layout)
    geometry = context.task022_geometry
    tube = cast(TubeSideThermalResult, context.task026_result)
    pressure = cast(Task029SuccessResult, context.task029_result)
    ua = cast(Task038SuccessResult, context.task038_result)
    thermal = cast(Task162Result, context.task162_result)
    bell = cast(Task166Result, context.task166_result)
    screening = cast(Task167Result, context.task167_result)
    screening_status = _enum_value(screening.aggregate_screening_status)
    warnings = _ordered_warnings(Task168Warning(code=_text(item)) for item in screening.warnings)
    if screening_status == "WARN" and not warnings:
        warnings = (Task168Warning("TASK167_SCREENING_WARN"),)
    constraints: list[tuple[str, str]] = []
    constraint_failures: list[Task168Blocker] = []
    requirement = request.requirement_authority
    q_method = thermal.q_method
    tube_dp = pressure.modeled_total_tube_side_pressure_drop_pa
    shell_dp = bell.total_shell_pressure_drop
    if requirement.required_duty_w is not None:
        passed = q_method >= requirement.required_duty_w
        constraints.append(("required_duty_w", "PASS" if passed else "BLOCKED"))
        if not passed:
            constraint_failures.append(
                _blocker(
                    BlockerCode.HARD_CONSTRAINT_UNSATISFIED,
                    CandidateStage.CONSTRAINT_EVALUATION,
                    "required_duty_w",
                    requirement.evidence_refs,
                )
            )
    if requirement.max_tube_dp_pa is not None:
        passed = tube_dp <= requirement.max_tube_dp_pa
        constraints.append(("max_tube_dp_pa", "PASS" if passed else "BLOCKED"))
        if not passed:
            constraint_failures.append(
                _blocker(
                    BlockerCode.HARD_CONSTRAINT_UNSATISFIED,
                    CandidateStage.CONSTRAINT_EVALUATION,
                    "max_tube_dp_pa",
                    requirement.evidence_refs,
                )
            )
    if requirement.max_shell_dp_pa is not None:
        passed = shell_dp <= requirement.max_shell_dp_pa
        constraints.append(("max_shell_dp_pa", "PASS" if passed else "BLOCKED"))
        if not passed:
            constraint_failures.append(
                _blocker(
                    BlockerCode.HARD_CONSTRAINT_UNSATISFIED,
                    CandidateStage.CONSTRAINT_EVALUATION,
                    "max_shell_dp_pa",
                    requirement.evidence_refs,
                )
            )
    evidence = {
        "geometry": _evidence(geometry),
        "tube_layout": _evidence(layout),
        "tube_side": _evidence(tube, result_name="tube_side"),
        "bell": _evidence(bell, result_name="bell"),
        "overall": _evidence(ua, result_name="ua"),
        "thermal": _evidence(thermal, result_name="task162"),
        "tube_dp": _evidence(pressure, result_name="tube_dp"),
        "shell_dp": _evidence(bell, result_name="shell_dp"),
        "screening": _evidence(screening, result_name="task167"),
    }
    metrics = tuple(
        (key, _text(value))
        for key, value in (
            ("physical_tube_count", layout.physical_tube_count),
            ("tube_hole_count", layout.tube_hole_count),
            ("modeled_ua_w_k", ua.modeled_ua_w_k),
            ("q_method_w", thermal.q_method),
            ("q_hot_w", thermal.q_hot),
            ("q_cold_w", thermal.q_cold),
            ("shell_dp_pa", bell.total_shell_pressure_drop),
            ("tube_dp_pa", pressure.modeled_total_tube_side_pressure_drop_pa),
            ("task167_status", screening_status),
        )
    )
    if constraint_failures:
        return _base_record(
            candidate,
            stage=CandidateStage.CONSTRAINT_EVALUATION,
            blockers=constraint_failures,
            last_successful_stage=CandidateStage.ENGINEERING_SCREENING,
            geometry_evidence=evidence["geometry"],
            tube_layout_evidence=evidence["tube_layout"],
            tube_side_evidence=evidence["tube_side"],
            bell_evidence=evidence["bell"],
            overall_u_ua_evidence=evidence["overall"],
            thermal_closure_evidence=evidence["thermal"],
            tube_dp_evidence=evidence["tube_dp"],
            shell_dp_evidence=evidence["shell_dp"],
            screening_evidence=evidence["screening"],
            constraint_evaluations=tuple(constraints),
            metrics=metrics,
            warnings=warnings,
        )
    status = (
        CandidateStatus.WARN if screening_status == "WARN" or warnings else CandidateStatus.PASS
    )
    return _base_record(
        candidate,
        stage=CandidateStage.COMPLETE,
        last_successful_stage=CandidateStage.COMPLETE,
        disposition=CandidateDisposition.EVALUATED,
        status=status,
        geometry_evidence=evidence["geometry"],
        tube_layout_evidence=evidence["tube_layout"],
        tube_side_evidence=evidence["tube_side"],
        bell_evidence=evidence["bell"],
        overall_u_ua_evidence=evidence["overall"],
        thermal_closure_evidence=evidence["thermal"],
        tube_dp_evidence=evidence["tube_dp"],
        shell_dp_evidence=evidence["shell_dp"],
        screening_evidence=evidence["screening"],
        constraint_evaluations=tuple(constraints),
        metrics=metrics,
        warnings=warnings,
    )


@dataclass(slots=True)
class _ExecutionBundle:
    """Private, per-candidate outputs produced during one live run.

    This is intentionally not part of :class:`Task168Request`.  The request
    contains only base authorities and request templates; this object is
    populated after TASK-168 has generated the candidate and invoked the
    producer boundaries.
    """

    task020_configuration: ShellAndTubeConfiguration | None = None
    task021_layout: object | None = None
    task022_geometry: object | None = None
    task024_result: object | None = None
    task024_geometry: object | None = None
    task025_result: object | None = None
    task026_result: object | None = None
    task031_geometry: object | None = None
    task032_flow_state: object | None = None
    task033_heat_transfer: object | None = None
    task034_pressure_drop: object | None = None
    task035_result: object | None = None
    task166_result: object | None = None
    task037_result: object | None = None
    task038_result: object | None = None
    task162_result: object | None = None
    task162_replay_evidence: object | None = None
    task027_result: object | None = None
    task028_result: object | None = None
    task029_result: object | None = None
    task167_result: object | None = None


class _StageFailure(Exception):
    """Internal normalized failure; no producer exception escapes the service."""

    def __init__(
        self,
        stage: CandidateStage,
        code: BlockerCode | str,
        field_path: str | None = None,
        message: str = "",
    ) -> None:
        self.stage = stage
        self.code = code.value if isinstance(code, BlockerCode) else code
        self.field_path = field_path
        self.message = message
        super().__init__(self.code)


def _public_value(value: object, *, decimal_strings: bool = True) -> object:
    """Project trusted upstream models into the raw mapping each producer expects."""

    if value is None or type(value) is bool or type(value) is int or type(value) is str:
        return value
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("non-finite Decimal cannot cross a producer boundary")
        return str(value) if decimal_strings else value
    if isinstance(value, enum.Enum):
        return _public_value(value.value, decimal_strings=decimal_strings)
    if isinstance(value, uuid.UUID):
        return str(value).lower()
    if type(value) is ReferencePlanePair:
        # TASK-025 owns this immutable value object.  Keep it typed at the
        # producer boundary; its canonical representation is handled by the
        # TASK-168 identity projection, not by an ad-hoc mapping here.
        return value
    if isinstance(
        value,
        (task021_canonical.FrozenJsonArray, task021_canonical.FrozenJsonObject),
    ):
        return _public_value(internal_frozen_to_primitive(value), decimal_strings=decimal_strings)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _public_value(getattr(value, item.name), decimal_strings=decimal_strings)
            for item in dataclasses.fields(value)
        }
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("producer mapping keys must be exact strings")
            result[key] = _public_value(item, decimal_strings=decimal_strings)
        return result
    if type(value) is list or type(value) is tuple:
        return [_public_value(item, decimal_strings=decimal_strings) for item in value]
    if type(value) is bytes:
        return value.hex()
    raise TypeError(f"unsupported trusted template value {type(value).__name__}")


def _template_mapping(
    value: object | None,
    stage: CandidateStage,
    field_path: str,
) -> dict[str, object]:
    if value is None:
        raise _StageFailure(
            stage,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            field_path,
            "explicit producer request template is required",
        )
    try:
        projected = _public_value(value, decimal_strings=True)
    except (TypeError, ValueError, UnicodeError, ArithmeticError) as exc:
        raise _StageFailure(
            stage,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            field_path,
            type(exc).__name__,
        ) from exc
    if type(projected) is not dict:
        raise _StageFailure(
            stage,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            field_path,
            "request template must project to a mapping",
        )
    return cast(dict[str, object], projected)


def _task020_candidate_payload(
    base: ShellAndTubeConfiguration,
    candidate: CandidateSpec,
) -> dict[str, object]:
    """Build the exact TASK-020 request for one generated candidate.

    ``base`` is a trusted normalized TASK-020 authority and contributes only
    invariant configuration structure.  Candidate-selectable fields are
    replaced in the request mapping and are then re-admitted by TASK-020;
    TASK-168 never constructs or rewrites a configuration identity itself.
    """

    case = base.case_authority
    binding = base.authority_binding
    evaluated_rule_pack = binding.evaluated_rule_pack_authority
    requested_rule_pack: dict[str, str] | None = None
    if _status_text(base.authority_mode) == "APPROVED_RULE_PACK":
        if evaluated_rule_pack is None:
            raise _StageFailure(
                CandidateStage.CONFIGURATION,
                BlockerCode.CONFIGURATION_AUTHORITY_INVALID,
                "task020_configuration.authority_binding.evaluated_rule_pack_authority",
                "TASK-020 rule-pack identity is unavailable for candidate materialization",
            )
        requested_rule_pack = {
            "rule_pack_id": evaluated_rule_pack.rule_pack_id,
            "rule_pack_version": evaluated_rule_pack.rule_pack_version,
            "rule_pack_canonical_hash": evaluated_rule_pack.rule_pack_canonical_hash,
        }
    return {
        "schema_version": "task020.configuration-request.v1",
        "case_authority": {
            "revision_id": case.revision_id,
            "payload_hash": case.payload_hash,
            "domain_snapshot_hash": case.domain_snapshot_hash,
            "status": case.revision_status.value,
        },
        "equipment_family": _status_text(base.equipment_family),
        "authority_mode": _status_text(base.authority_mode),
        "construction_family": candidate.construction_family.value,
        "orientation": _status_text(base.orientation),
        "shell_pass_count": base.shell_pass_count,
        "tube_pass_count": candidate.tube_pass_count,
        "front_head_token": base.component_tokens.front_head,
        "shell_token": base.component_tokens.shell,
        "rear_head_token": base.component_tokens.rear_head,
        "standard_system_id": binding.standard_system_id,
        "requested_rule_pack_identity": requested_rule_pack,
        "evidence_refs": list(binding.case_authority_evidence_refs),
    }


def _materialize_candidate_configuration(
    base: ShellAndTubeConfiguration,
    candidate: CandidateSpec,
) -> ShellAndTubeConfiguration:
    """Use TASK-020's public validator to materialize one candidate config."""

    payload = _task020_candidate_payload(base, candidate)
    try:
        outcome = validate_task020(payload)
    except _StageFailure:
        raise
    except Exception as exc:
        raise _StageFailure(
            CandidateStage.CONFIGURATION,
            BlockerCode.CONFIGURATION_AUTHORITY_INVALID,
            "task020_candidate_request",
            type(exc).__name__,
        ) from exc
    if _status_text(getattr(outcome, "status", None)) != "VALID":
        blocker_codes = tuple(
            _text(getattr(item, "code", "")) for item in getattr(outcome, "blockers", ())
        )
        message = "TASK-020 rejected candidate configuration"
        if blocker_codes:
            message += ":" + ",".join(blocker_codes)
        raise _StageFailure(
            CandidateStage.CONFIGURATION,
            BlockerCode.CONFIGURATION_AUTHORITY_INVALID,
            "task020_candidate_request",
            message,
        )
    configuration = getattr(outcome, "configuration", None)
    if type(configuration) is not ShellAndTubeConfiguration:
        raise _StageFailure(
            CandidateStage.CONFIGURATION,
            BlockerCode.CONFIGURATION_AUTHORITY_INVALID,
            "task020_candidate_request.configuration",
            "TASK-020 did not return ShellAndTubeConfiguration",
        )
    if (
        configuration.construction_family is not candidate.construction_family
        or configuration.tube_pass_count != candidate.tube_pass_count
        or configuration.case_authority != base.case_authority
    ):
        raise _StageFailure(
            CandidateStage.CONFIGURATION,
            BlockerCode.CONFIGURATION_AUTHORITY_INVALID,
            "task020_candidate_request.configuration",
            "TASK-020 returned a mismatched candidate configuration",
        )
    return configuration


def _configuration_evidence(
    configuration: object | None,
) -> tuple[tuple[str, str], ...]:
    if type(configuration) is not ShellAndTubeConfiguration:
        return ()
    return (
        ("result_hash", configuration.configuration_hash),
        ("result_id", configuration.configuration_id),
        ("configuration_hash", configuration.configuration_hash),
        ("configuration_id", configuration.configuration_id),
        ("construction_family", configuration.construction_family.value),
        ("tube_pass_count", str(configuration.tube_pass_count)),
        ("case_authority_id", configuration.case_authority.revision_id),
    )


def _status_text(value: object) -> str:
    raw = getattr(value, "value", value)
    return raw if type(raw) is str else ""


def _result_payload(
    value: object,
    names: tuple[str, ...],
    stage: CandidateStage,
    field_path: str,
) -> object:
    status = getattr(value, "status", None)
    if status is not None and _status_text(status) not in {"VALID", "SUCCESS"}:
        raise _StageFailure(
            stage,
            BlockerCode.CANDIDATE_STAGE_FAILED,
            field_path + ".status",
            "producer returned a non-success status",
        )
    for name in names:
        payload = getattr(value, name, None)
        if payload is not None:
            return payload
    raise _StageFailure(
        stage,
        BlockerCode.CANDIDATE_STAGE_FAILED,
        field_path,
        "producer did not return the required success payload",
    )


def _call_stage(
    stage: CandidateStage,
    field_path: str,
    operation: Any,
) -> object:
    try:
        return operation()
    except _StageFailure:
        raise
    except Exception as exc:
        raise _StageFailure(
            stage, BlockerCode.CANDIDATE_STAGE_FAILED, field_path, type(exc).__name__
        ) from exc


def _sync_nested_identities(
    value: object,
    *,
    configuration: ShellAndTubeConfiguration,
    layout: object,
    shell_geometry: object | None = None,
    baffle_geometry: object | None = None,
) -> None:
    """Update only identity bindings in a trusted raw request template."""

    if type(value) is not dict:
        return
    mapping = cast(dict[str, object], value)
    for key, item in tuple(mapping.items()):
        if key == "task020_configuration_id":
            mapping[key] = configuration.configuration_id
        elif key == "task020_configuration_hash":
            mapping[key] = configuration.configuration_hash
        elif key == "task021_layout_id":
            mapping[key] = getattr(layout, "layout_id", item)
        elif key == "task021_layout_hash":
            mapping[key] = getattr(layout, "layout_hash", item)
        elif shell_geometry is not None and key == "task022_geometry_id":
            mapping[key] = getattr(shell_geometry, "geometry_id", item)
        elif shell_geometry is not None and key == "task022_geometry_hash":
            mapping[key] = getattr(shell_geometry, "geometry_hash", item)
        elif baffle_geometry is not None and key == "baffle_geometry_id":
            mapping[key] = getattr(baffle_geometry, "geometry_id", item)
        elif baffle_geometry is not None and key == "baffle_geometry_hash":
            mapping[key] = getattr(baffle_geometry, "geometry_hash", item)
        elif type(item) is dict:
            _sync_nested_identities(
                item,
                configuration=configuration,
                layout=layout,
                shell_geometry=shell_geometry,
                baffle_geometry=baffle_geometry,
            )
        elif type(item) is list:
            for child in item:
                _sync_nested_identities(
                    child,
                    configuration=configuration,
                    layout=layout,
                    shell_geometry=shell_geometry,
                    baffle_geometry=baffle_geometry,
                )


def _task021_payload(
    authority: Task168EvaluationInputAuthority,
    candidate: CandidateSpec,
    configuration: ShellAndTubeConfiguration,
) -> dict[str, object]:
    payload = _template_mapping(
        authority.task021_request_template,
        CandidateStage.TUBE_LAYOUT,
        "evaluation_input_authority.task021_request_template",
    )
    payload["configuration"] = configuration
    geometry = payload.get("tube_geometry")
    if type(geometry) is not dict:
        raise _StageFailure(
            CandidateStage.TUBE_LAYOUT,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "task021_request_template.tube_geometry",
        )
    tube_geometry = cast(dict[str, object], geometry)
    for name in (
        "geometry_id",
        "geometry_type",
        "revision",
        "approval_state",
        "source_binding",
    ):
        if name not in tube_geometry:
            raise _StageFailure(
                CandidateStage.TUBE_LAYOUT,
                BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                f"task021_request_template.tube_geometry.{name}",
            )
    outer = candidate.tube_outer_diameter_m
    wall = candidate.tube_wall_thickness_m
    inner = outer - (Decimal("2") * wall)
    materialized_geometry_id, materialized_source, geometry_bridge_ref = (
        _task021_candidate_geometry_authority(candidate, tube_geometry)
    )
    tube_geometry.update(
        {
            "geometry_id": materialized_geometry_id,
            "outer_diameter_m": str(outer),
            "inner_diameter_m": str(inner),
            "wall_thickness_m": str(wall),
            "source_binding": materialized_source,
        }
    )
    tube_geometry["record_hash"] = task021_canonical.sha256_hex(
        {
            key: item
            for key, item in tube_geometry.items()
            if key not in {"record_hash", "snapshot_hash"}
        }
    )
    tube_geometry["snapshot_hash"] = task021_canonical.sha256_hex(
        {key: item for key, item in tube_geometry.items() if key != "snapshot_hash"}
    )
    rule = payload.get("layout_rule_authority")
    if type(rule) is not dict:
        raise _StageFailure(
            CandidateStage.TUBE_LAYOUT,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "task021_request_template.layout_rule_authority",
        )
    layout_rule = cast(dict[str, object], rule)
    all_authority_refs = _candidate_dimension_authority_refs(candidate)
    layout_authority_refs = _candidate_dimension_authority_refs(
        candidate,
        (
            "CONSTRUCTION_FAMILY",
            "TUBE_OUTER_DIAMETER",
            "TUBE_WALL_THICKNESS",
            "TUBE_PITCH",
            "TUBE_LAYOUT",
            "TUBE_PASS_COUNT",
        ),
    )
    payload["evidence_refs"] = _merge_evidence_refs(
        payload.get("evidence_refs"),
        (*all_authority_refs, geometry_bridge_ref),
    )
    layout_rule["pattern_family"] = _task021_pattern_family(candidate.tube_layout)
    layout_rule["pitch_m"] = str(candidate.tube_pitch_m)
    layout_rule["evidence_refs"] = _merge_evidence_refs(
        layout_rule.get("evidence_refs"), layout_authority_refs
    )
    layout_rule["provenance_edge_ids"] = _merge_evidence_refs(
        layout_rule.get("provenance_edge_ids"), layout_authority_refs
    )
    if "snapshot_hash" not in layout_rule:
        raise _StageFailure(
            CandidateStage.TUBE_LAYOUT,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "task021_request_template.layout_rule_authority.snapshot_hash",
        )
    layout_rule["snapshot_hash"] = task021_canonical.sha256_hex(
        {key: item for key, item in layout_rule.items() if key != "snapshot_hash"}
    )
    return payload


def _task021_pattern_family(layout: str) -> str:
    """Translate the TASK-168 Bell layout token to TASK-021's exact token."""

    if layout == "LAYOUT_30_DEG":
        return "TRIANGULAR"
    if layout == "LAYOUT_90_DEG":
        return "SQUARE"
    if layout == "TRIANGULAR" or layout == "SQUARE":
        return layout
    raise _StageFailure(
        CandidateStage.TUBE_LAYOUT,
        BlockerCode.CANDIDATE_GEOMETRY_INVALID,
        "tube_layout",
        "candidate layout is not accepted by TASK-021",
    )


def _bell_layout_angle(layout: object) -> str:
    value = _status_text(layout)
    if value == "TRIANGULAR":
        return "LAYOUT_30_DEG"
    if value == "SQUARE":
        return "LAYOUT_90_DEG"
    return value


def _task022_shell_snapshot(record: ShellGeometryRecord) -> dict[str, object]:
    snapshot: dict[str, object] = {
        "schema_version": "task022.approved-shell-geometry.v1",
        "geometry_id": record.geometry_id,
        "geometry_type": record.geometry_type,
        "revision": record.revision,
        "approval_state": record.approval_state,
        "shell_inside_diameter_m": record.shell_inside_diameter_m,
        "record_hash": record.record_hash,
        "source_binding": _public_value(record.source_binding),
        "snapshot_hash": "",
    }
    snapshot["snapshot_hash"] = task022_canonical.sha256_hex(
        {key: item for key, item in snapshot.items() if key != "snapshot_hash"}
    )
    return snapshot


def _task022_payload(
    authority: Task168EvaluationInputAuthority,
    candidate: CandidateSpec,
    configuration: ShellAndTubeConfiguration,
    layout: object,
    record: ShellGeometryRecord,
) -> dict[str, object]:
    payload = _template_mapping(
        authority.task022_request_template,
        CandidateStage.SHELL_BUNDLE_GEOMETRY,
        "evaluation_input_authority.task022_request_template",
    )
    payload["configuration"] = configuration
    payload["tube_layout"] = layout
    payload["approved_shell_geometry"] = _task022_shell_snapshot(record)
    payload["caller_supplied_shell"] = None
    payload["shell_authority_mode"] = "APPROVED_CATALOG_SNAPSHOT"
    payload["evidence_refs"] = _merge_evidence_refs(
        payload.get("evidence_refs"), _candidate_dimension_authority_refs(candidate)
    )
    if "geometry_rule_authority" not in payload:
        raise _StageFailure(
            CandidateStage.SHELL_BUNDLE_GEOMETRY,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "task022_request_template.geometry_rule_authority",
        )
    return payload


def _task024_authority_hash(value: Mapping[str, object]) -> str:
    payload = {
        "baffle_count": value["baffle_count"],
        "baffle_cut_fraction": value["baffle_cut_fraction"],
        "baffle_thickness_m": value["baffle_thickness_m"],
        "baffle_type": _enum_value(value["baffle_type"]),
        "evidence_refs": list(cast(Iterable[object], value["evidence_refs"])),
        "orientation_sequence": [
            _enum_value(item) for item in cast(Iterable[object], value["orientation_sequence"])
        ],
        "schema_version": value["schema_version"],
        "shell_to_baffle_diametral_clearance_m": value["shell_to_baffle_diametral_clearance_m"],
        "spacing_sequence_m": list(cast(Iterable[object], value["spacing_sequence_m"])),
        "tube_to_baffle_hole_diametral_clearance_m": value[
            "tube_to_baffle_hole_diametral_clearance_m"
        ],
    }
    return hashlib.sha256(task024_canonical.canonical_json_bytes(payload)).hexdigest()


def _task024_axial_hash(value: Mapping[str, object]) -> str:
    payload = {
        "axial_end_coordinate_m": value["axial_end_coordinate_m"],
        "axial_start_coordinate_m": value["axial_start_coordinate_m"],
        "evidence_refs": list(cast(Iterable[object], value["evidence_refs"])),
        "schema_version": value["schema_version"],
    }
    return hashlib.sha256(task024_canonical.canonical_json_bytes(payload)).hexdigest()


def _task024_payload(
    authority: Task168EvaluationInputAuthority,
    candidate: CandidateSpec,
    configuration: ShellAndTubeConfiguration,
    layout: object,
    shell_geometry: object,
) -> dict[str, object]:
    payload = _template_mapping(
        authority.task024_request_template,
        CandidateStage.BAFFLE_GEOMETRY,
        "evaluation_input_authority.task024_request_template",
    )
    payload["configuration"] = configuration
    payload["tube_layout"] = layout
    payload["shell_bundle_geometry"] = shell_geometry
    axial = payload.get("axial_span")
    design = payload.get("design_authority")
    if type(axial) is not dict or type(design) is not dict:
        raise _StageFailure(
            CandidateStage.BAFFLE_GEOMETRY,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "task024_request_template",
        )
    axial_map = cast(dict[str, object], axial)
    design_map = cast(dict[str, object], design)
    axial_authority_refs = _candidate_dimension_authority_refs(
        candidate, ("TUBE_LENGTH", "BAFFLE_SPACING", "BAFFLE_COUNT")
    )
    design_authority_refs = _candidate_dimension_authority_refs(
        candidate,
        ("BAFFLE_TYPE", "BAFFLE_CUT", "BAFFLE_SPACING", "BAFFLE_COUNT"),
    )
    payload["evidence_refs"] = _merge_evidence_refs(
        payload.get("evidence_refs"), _candidate_dimension_authority_refs(candidate)
    )
    axial_map["evidence_refs"] = _merge_evidence_refs(
        axial_map.get("evidence_refs"), axial_authority_refs
    )
    design_map["evidence_refs"] = _merge_evidence_refs(
        design_map.get("evidence_refs"), design_authority_refs
    )
    try:
        start = Decimal(cast(str, axial_map["axial_start_coordinate_m"]))
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise _StageFailure(
            CandidateStage.BAFFLE_GEOMETRY,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "task024_request_template.axial_span.axial_start_coordinate_m",
        ) from exc
    expected_span = candidate.baffle_spacing_m * Decimal(candidate.baffle_count + 1)
    if expected_span != candidate.tube_length_m:
        raise _StageFailure(
            CandidateStage.BAFFLE_GEOMETRY,
            BlockerCode.CANDIDATE_GEOMETRY_INVALID,
            "tube_length_m",
            "tube length must exactly close the selected uniform baffle spacing",
        )
    axial_map["axial_end_coordinate_m"] = str(start + candidate.tube_length_m)
    axial_map["authority_hash"] = _task024_axial_hash(axial_map)
    try:
        design_map["baffle_type"] = BaffleType(candidate.baffle_type)
    except ValueError as exc:
        raise _StageFailure(
            CandidateStage.BAFFLE_GEOMETRY,
            BlockerCode.CANDIDATE_GEOMETRY_INVALID,
            "baffle_type",
            "candidate baffle type is not accepted by TASK-024",
        ) from exc
    design_map["baffle_count"] = candidate.baffle_count
    design_map["baffle_cut_fraction"] = str(candidate.baffle_cut_fraction)
    spacing = tuple(str(candidate.baffle_spacing_m) for _ in range(candidate.baffle_count + 1))
    orientations = design_map.get("orientation_sequence")
    if type(orientations) is not list:
        raise _StageFailure(
            CandidateStage.BAFFLE_GEOMETRY,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "task024_request_template.design_authority.orientation_sequence",
            "a sequence-shaped TASK-024 design template is required",
        )
    design_map["orientation_sequence"] = [
        BaffleOrientation.TOP for _ in range(candidate.baffle_count)
    ]
    design_map["spacing_sequence_m"] = list(spacing)
    design_map["authority_hash"] = _task024_authority_hash(design_map)
    return payload


def _task_result_wrapper(value: object, payload_name: str) -> dict[str, object]:
    status = _status_text(getattr(value, "status", "VALID"))
    payload = getattr(value, payload_name, None)
    return {
        "status": status,
        payload_name: _public_value(payload),
        "blocked_result": None,
        "raw_boundary_blocked_result": None,
    }


def _task031_payload(
    authority: Task168EvaluationInputAuthority,
    configuration: ShellAndTubeConfiguration,
    layout: object,
    task024_result: object,
    baffle_geometry: object,
) -> dict[str, object]:
    payload = _template_mapping(
        authority.task031_request_template,
        CandidateStage.SHELL_SIDE_BELL,
        "evaluation_input_authority.task031_request_template",
    )
    payload["tube_layout"] = _public_value(layout)
    _sync_nested_identities(
        payload,
        configuration=configuration,
        layout=layout,
        baffle_geometry=baffle_geometry,
    )
    # TASK-024's validation result is the authoritative upstream envelope.
    # Keep its exact warning/blocker/deferred/provenance projection; the
    # structural TASK-031 template is not allowed to replace those fields.
    payload["baffle_geometry_result"] = _public_value(task024_result)
    if type(payload.get("baffle_geometry_result")) is dict:
        baffle_result = cast(dict[str, object], payload["baffle_geometry_result"])
        if type(baffle_result.get("geometry")) is dict:
            baffle_result["geometry"] = _public_value(baffle_geometry)
    return payload


def _task032_payload(
    authority: Task168EvaluationInputAuthority,
    result031: Any,
    configuration: ShellAndTubeConfiguration,
    layout: Any,
) -> dict[str, object]:
    payload = _template_mapping(
        authority.task032_request_template,
        CandidateStage.SHELL_SIDE_BELL,
        "evaluation_input_authority.task032_request_template",
    )
    # TASK-032 consumes the exact TASK-031 result envelope, whose closed
    # fields are different from the generic TASK-033/034 result wrappers.
    # In particular, it uses ``blocked_result_hash`` and does not admit the
    # generic ``blocked_result`` / ``raw_boundary_blocked_result`` keys.
    payload["task031_result"] = {
        "status": _status_text(getattr(result031, "status", "VALID")),
        "geometry": _public_value(getattr(result031, "geometry", None)),
        "warnings": _public_value(getattr(result031, "warnings", ())),
        "blockers": _public_value(getattr(result031, "blockers", ())),
        "deferred_capabilities": list(getattr(result031, "deferred_capabilities", ())),
        "blocked_result_hash": getattr(result031, "blocked_result_hash", None),
    }
    if authority.task032_property_snapshot is not None:
        snapshot = _public_value(authority.task032_property_snapshot)
        payload["property_snapshot"] = snapshot
        if dataclasses.is_dataclass(authority.task032_property_snapshot):
            snapshot_hash = getattr(
                authority.task032_property_snapshot, "property_snapshot_hash", None
            )
            if type(snapshot_hash) is str:
                payload["property_snapshot_hash"] = snapshot_hash
    if authority.task032_mass_flow_authority is not None:
        payload["mass_flow_authority"] = _public_value(authority.task032_mass_flow_authority)
    _sync_nested_identities(payload, configuration=configuration, layout=layout)
    mass_flow = payload.get("mass_flow_authority")
    if type(mass_flow) is dict:
        geometry = getattr(result031, "geometry", None)
        if geometry is not None:
            mass_flow.update(
                {
                    "task020_configuration_id": configuration.configuration_id,
                    "task020_configuration_hash": configuration.configuration_hash,
                    "task031_geometry_id": geometry.geometry_id,
                    "task031_geometry_hash": geometry.geometry_hash,
                }
            )
        snapshot_hash = payload.get("property_snapshot_hash")
        if type(snapshot_hash) is str:
            mass_flow["property_snapshot_hash"] = snapshot_hash
        try:
            parsed = parse_task032_request(payload)
            mass_flow["authority_hash"] = mass_flow_authority_hash(parsed.mass_flow_authority)
        except Exception as exc:
            raise _StageFailure(
                CandidateStage.SHELL_SIDE_BELL,
                BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                "task032_request.mass_flow_authority",
                type(exc).__name__,
            ) from exc
    return payload


def _task033_payload(
    authority: Task168EvaluationInputAuthority,
    result032: Any,
    request032: Mapping[str, object],
    configuration: ShellAndTubeConfiguration,
    layout: Any,
) -> dict[str, object]:
    payload = _template_mapping(
        authority.task033_request_template,
        CandidateStage.SHELL_SIDE_BELL,
        "evaluation_input_authority.task033_request_template",
    )
    flow_state = getattr(result032, "flow_state", None)
    payload["task032_flow_state"] = _public_value(flow_state)
    # The TASK-033 authority replays the exact TASK-032 request hash.  Use the
    # candidate-specific request accepted immediately upstream rather than a
    # stale template evidence bundle.
    payload["task032_request_evidence"] = _public_value(request032)
    _sync_nested_identities(payload, configuration=configuration, layout=layout)
    return payload


def _task034_payload(
    authority: Task168EvaluationInputAuthority,
    request031: Mapping[str, object],
    result031: Any,
    result032: Any,
    result033: Any,
    request033: Mapping[str, object],
    configuration: ShellAndTubeConfiguration,
    layout: Any,
    baffle_geometry: Any,
) -> dict[str, object]:
    payload = _template_mapping(
        authority.task034_request_template,
        CandidateStage.SHELL_SIDE_BELL,
        "evaluation_input_authority.task034_request_template",
    )
    _sync_nested_identities(
        payload,
        configuration=configuration,
        layout=layout,
        baffle_geometry=baffle_geometry,
    )
    geometry = getattr(result031, "geometry", None)
    flow = getattr(result032, "flow_state", None)
    heat = getattr(result033, "heat_transfer", None)
    if geometry is None or flow is None or heat is None:
        raise _StageFailure(
            CandidateStage.SHELL_SIDE_BELL,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "task034_request_template",
            "TASK-031/032/033 success payload is required",
        )
    design = getattr(baffle_geometry, "design_authority", None)
    if design is None:
        raise _StageFailure(
            CandidateStage.SHELL_SIDE_BELL,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "task024.design_authority",
        )
    payload.update(
        {
            "task031_request_hash": geometry.request_hash,
            "shell_inside_diameter_m": baffle_geometry.shell_inside_diameter_m,
            "baffle_count": design.baffle_count,
            "uniform_spacing_sequence_m": list(design.spacing_sequence_m),
            "tube_pitch_m": layout.layout_rule_authority.pitch_m,
            "tube_outer_diameter_m": layout.tube_geometry.outer_diameter_m,
            "pattern_family": _status_text(layout.layout_rule_authority.pattern_family),
            "shell_side_case_id": flow.shell_side_case_id,
            "shell_side_stream_id": flow.shell_side_stream_id,
            "shell_side_fluid_id": flow.shell_side_fluid_id,
            "task020_configuration_id": flow.task020_configuration_id,
            "task020_configuration_hash": flow.task020_configuration_hash,
            "task031_geometry_id": geometry.geometry_id,
            "task031_geometry_hash": geometry.geometry_hash,
            "task032_request_hash": flow.request_hash,
            "task032_result_id": flow.result_id,
            "task032_result_hash": flow.result_hash,
            "task033_request_hash": heat.request_hash,
            "task033_result_id": heat.result_id,
            "task033_result_hash": heat.result_hash,
            "property_snapshot_hash": flow.property_snapshot_hash,
            "mass_flow_authority_hash": flow.mass_flow_authority_hash,
        }
    )
    wall = payload.get("shell_type_authority")
    if type(wall) is dict:
        # TASK-034 keeps shell-type authority and wall-property authority as
        # separate schemas.  Only the shell authority's two configuration
        # bindings are candidate-dependent; adding wall-property fields here
        # would violate the exact shell-type field inventory.
        wall["task020_configuration_id"] = flow.task020_configuration_id
        wall["task020_configuration_hash"] = flow.task020_configuration_hash
        if "authority_hash" in wall:
            wall["authority_hash"] = task034_canonical.shell_type_authority_hash(wall)
    # The v2 wall-property authority hash is a top-level TASK-034 request
    # field.  Recompute it after all candidate-specific upstream identities
    # have been materialized; the historical template hash cannot be reused
    # for a generated candidate.
    if "wall_property_authority_hash" in payload:
        payload["wall_property_authority_hash"] = task034_canonical.wall_property_authority_hash(
            payload
        )
    if type(payload.get("task033_upstream_evidence")) is dict:
        evidence = cast(dict[str, object], payload["task033_upstream_evidence"])
        # TASK-034 replays the exact candidate-specific TASK-033 request and
        # its nested TASK-032 evidence.  The authority template is only a
        # shape/base-authority carrier; retaining its historical request here
        # would make the live TASK-032 result identity disagree with the
        # request evidence that TASK-034 validates.
        evidence["task033_request_evidence"] = _public_value(request033)
        evidence["task033_validation_result"] = _task_result_wrapper(result033, "heat_transfer")
    payload["task031_request_evidence"] = _public_value(request031)
    return payload


def _task035_payload(
    authority: Task168EvaluationInputAuthority,
    result031: object,
    result032: object,
    result033: object,
    result034: object,
    configuration: ShellAndTubeConfiguration,
    layout: object,
) -> dict[str, object]:
    payload = _template_mapping(
        authority.task035_request_template,
        CandidateStage.SHELL_SIDE_BELL,
        "evaluation_input_authority.task035_request_template",
    )
    payload["task031_result"] = {
        "status": _status_text(getattr(result031, "status", "VALID")),
        "geometry": _public_value(getattr(result031, "geometry", None), decimal_strings=False),
        "warnings": _public_value(getattr(result031, "warnings", ()), decimal_strings=False),
        "blockers": _public_value(getattr(result031, "blockers", ()), decimal_strings=False),
        "deferred_capabilities": list(getattr(result031, "deferred_capabilities", ())),
        "blocked_result_hash": getattr(result031, "blocked_result_hash", None),
    }
    payload["task032_result"] = {
        "status": _status_text(getattr(result032, "status", "VALID")),
        "flow_state": _public_value(getattr(result032, "flow_state", None), decimal_strings=False),
        "blocked_result": None,
        "raw_boundary_blocked_result": None,
    }
    payload["task033_result"] = {
        "status": _status_text(getattr(result033, "status", "VALID")),
        "heat_transfer": _public_value(
            getattr(result033, "heat_transfer", None), decimal_strings=False
        ),
        "blocked_result": None,
        "raw_boundary_blocked_result": None,
    }
    payload["task034_result"] = {
        "status": _status_text(getattr(result034, "status", "VALID")),
        "pressure_drop": _public_value(
            getattr(result034, "pressure_drop", None), decimal_strings=False
        ),
        "blocked_result": None,
        "raw_boundary_blocked_result": None,
    }
    _sync_nested_identities(payload, configuration=configuration, layout=layout)
    return payload


def _task166_payload(
    authority: Task168EvaluationInputAuthority,
    configuration: ShellAndTubeConfiguration,
    layout: Any,
    shell_geometry: Any,
    baffle_geometry: Any,
    result031: Any,
    result032: Any,
    request032: Mapping[str, object],
) -> dict[str, object]:
    payload = _template_mapping(
        authority.task166_request_template,
        CandidateStage.SHELL_SIDE_BELL,
        "evaluation_input_authority.task166_request_template",
    )
    for key in (
        "task020_configuration",
        "tube_layout",
        "shell_bundle_geometry",
        "baffle_geometry",
        "shell_side_hydraulic_geometry",
        "shell_side_flow_state",
        "shell_side_flow_state_request",
    ):
        if key not in payload:
            raise _StageFailure(
                CandidateStage.SHELL_SIDE_BELL,
                BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                f"task166_request_template.{key}",
            )

    case_id = configuration.case_authority.revision_id
    config_map = cast(dict[str, object], payload["task020_configuration"])
    config_map.update(
        {
            "physical_exchanger_case_id": case_id,
            "result_hash": configuration.configuration_hash,
            "result_id": configuration.configuration_id,
            "status": "VALID",
            "construction_family": configuration.construction_family.value,
            "shell_type": "TEMA_E",
            "shell_pass_count": configuration.shell_pass_count,
        }
    )
    layout_map = cast(dict[str, object], payload["tube_layout"])
    layout_map.update(
        {
            "physical_exchanger_case_id": case_id,
            "result_hash": layout.layout_hash,
            "result_id": layout.layout_id,
            "status": "VALID",
            "layout_id": layout.layout_id,
            "layout_angle": _bell_layout_angle(layout.layout_rule_authority.pattern_family),
            "tube_outer_diameter_m": layout.tube_geometry.outer_diameter_m,
            "tube_pitch_m": layout.layout_rule_authority.pitch_m,
            "tube_count": str(layout.physical_tube_count),
        }
    )
    shell_map = cast(dict[str, object], payload["shell_bundle_geometry"])
    shell_map.update(
        {
            "physical_exchanger_case_id": case_id,
            "result_hash": shell_geometry.geometry_hash,
            "result_id": shell_geometry.geometry_id,
            "status": "VALID",
            "shell_inside_diameter_m": shell_geometry.shell_inside_diameter_m,
            "bundle_outer_diameter_m": shell_geometry.bundle_outer_envelope_diameter_m,
            "shell_to_bundle_diametral_clearance_m": (
                shell_geometry.shell_to_bundle_diametral_clearance_m
            ),
        }
    )
    baffle_map = cast(dict[str, object], payload["baffle_geometry"])
    design = baffle_geometry.design_authority
    sequence = tuple(design.spacing_sequence_m)
    baffle_map.update(
        {
            "physical_exchanger_case_id": case_id,
            "result_hash": baffle_geometry.geometry_hash,
            "result_id": baffle_geometry.geometry_id,
            "status": "VALID",
            "baffle_type": _status_text(design.baffle_type),
            "baffle_cut_fraction": design.baffle_cut_fraction,
            "baffle_count": design.baffle_count,
            "central_baffle_spacing_m": sequence[len(sequence) // 2],
            "inlet_baffle_spacing_m": sequence[0],
            "outlet_baffle_spacing_m": sequence[-1],
            "shell_to_baffle_diametral_clearance_m": design.shell_to_baffle_diametral_clearance_m,
            "tube_to_baffle_hole_diametral_clearance_m": (
                design.tube_to_baffle_hole_diametral_clearance_m
            ),
        }
    )
    hydraulic_map = cast(dict[str, object], payload["shell_side_hydraulic_geometry"])
    geometry031 = result031.geometry
    hydraulic_map.update(
        {
            "physical_exchanger_case_id": case_id,
            "result_hash": geometry031.geometry_hash,
            "result_id": geometry031.geometry_id,
            "status": "VALID",
            "central_crossflow_flow_area_m2": geometry031.central_crossflow_flow_area_m2,
        }
    )
    flow_map = cast(dict[str, object], payload["shell_side_flow_state"])
    flow = result032.flow_state
    flow_map.update(
        {
            "physical_exchanger_case_id": case_id,
            "result_hash": flow.result_hash,
            "result_id": flow.result_id,
            "status": "VALID",
            "phase": _status_text(flow.phase_region),
            "rheology": flow.rheology_model,
            "shell_side_reynolds_number": flow.shell_side_reynolds_number,
            "shell_side_prandtl_number": flow.shell_side_prandtl_number,
            "shell_side_mass_velocity_kg_m2_s": flow.shell_side_mass_velocity_kg_m2_s,
            "shell_side_mass_flow_rate_kg_s": flow.shell_side_mass_flow_rate_kg_s,
        }
    )
    flow_request = cast(dict[str, object], payload["shell_side_flow_state_request"])
    flow_property_value = flow_map.get("property_snapshot")
    if type(flow_property_value) is not dict:
        flow_property_value = flow_request.get("property_snapshot")
    if type(flow_property_value) is dict:
        flow_property = cast(dict[str, object], flow_property_value)
        for name in (
            "density_kg_m3",
            "dynamic_viscosity_pa_s",
            "specific_heat_capacity_j_kg_k",
        ):
            if name in flow_property:
                flow_map[name] = flow_property[name]
    property_snapshot = flow_request.get("property_snapshot")
    if type(property_snapshot) is not dict:
        property_snapshot = _public_value(authority.task032_property_snapshot, decimal_strings=True)
        flow_request["property_snapshot"] = property_snapshot
    mass_flow = flow_request.get("mass_flow_authority")
    if type(mass_flow) is not dict:
        mass_flow = _public_value(authority.task032_mass_flow_authority, decimal_strings=True)
        flow_request["mass_flow_authority"] = mass_flow
    if type(mass_flow) is not dict:
        raise _StageFailure(
            CandidateStage.SHELL_SIDE_BELL,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "task166_request.shell_side_flow_state_request.mass_flow_authority",
        )
    mass_flow_map = cast(dict[str, object], mass_flow)
    mass_flow_map["shell_side_mass_flow_rate_kg_s"] = flow.shell_side_mass_flow_rate_kg_s
    payload["shell_side_flow_state_request"] = flow_request
    return payload


def _task160_payload(
    authority: Task168EvaluationInputAuthority,
    configuration: ShellAndTubeConfiguration,
    candidate: CandidateSpec,
    task026: TubeSideThermalResult,
) -> dict[str, object]:
    """Bind live candidate results into the candidate's TASK-160 request.

    TASK-160 remains the owner of thermal-stream identity and applicability.
    The evaluation template supplies only structural stream data.  The
    candidate-specific configuration is always projected into the envelope;
    this is important because retaining the template's fixed-tubesheet
    envelope would let an unsupported U-tube or floating-head candidate
    produce a misleading TASK-160 success.

    When the selected family/pass-count differs from the template, the fixed
    template source identity is not retained.  A deterministic TASK-168
    configuration bridge records the selected producer configuration and its
    discrete-authority evidence.  TASK-160 then decides whether that
    candidate-specific envelope is within its own frozen applicability.
    """

    payload = _template_mapping(
        authority.task160_request_template,
        CandidateStage.THERMAL_CLOSURE,
        "evaluation_input_authority.task160_request_template",
    )

    envelope = payload.get("envelope_authority")
    if type(envelope) is not dict:
        raise _StageFailure(
            CandidateStage.THERMAL_CLOSURE,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "evaluation_input_authority.task160_request_template.envelope_authority",
            "TASK-160 envelope authority must project to a mapping",
        )
    envelope_map = cast(dict[str, object], envelope)
    selected_envelope = {
        "construction_family": configuration.construction_family.value,
        "shell_pass_count": configuration.shell_pass_count,
        "tube_pass_count": configuration.tube_pass_count,
    }
    template_envelope = {
        key: envelope_map.get(key)
        for key in ("construction_family", "shell_pass_count", "tube_pass_count")
    }
    candidate_refs = _candidate_dimension_authority_refs(
        candidate, ("CONSTRUCTION_FAMILY", "TUBE_PASS_COUNT")
    )
    configuration_ref = (
        "TASK168_TASK020_CONFIGURATION::"
        + configuration.configuration_id
        + "::"
        + configuration.configuration_hash
    )
    if template_envelope != selected_envelope:
        bridge_payload = {
            "base_envelope": template_envelope,
            "candidate_configuration_id": configuration.configuration_id,
            "candidate_configuration_hash": configuration.configuration_hash,
            "selected_envelope": selected_envelope,
            "selected_authority_refs": list(candidate_refs),
        }
        bridge_hash = task021_canonical.sha256_hex(bridge_payload)
        envelope_map.update(selected_envelope)
        if configuration.construction_family is ConstructionFamily.FIXED_TUBESHEET:
            envelope_map.update(
                {
                    "authority_source_identity": "TASK168-CANDIDATE-CONFIGURATION-BRIDGE",
                    "authority_source_version": "v1",
                    "authority_identity": "TASK168-TASK160-ENVELOPE::" + bridge_hash,
                }
            )
        else:
            envelope_map.update(
                {
                    "authority_source_identity": TASK168_TASK160_V06_ENVELOPE_SOURCE_ID,
                    "authority_source_version": TASK168_TASK160_V06_ENVELOPE_SOURCE_VERSION,
                    "authority_identity": TASK168_TASK160_V06_ENVELOPE_AUTHORITY_ID
                    + "::"
                    + bridge_hash,
                }
            )
            candidate_refs = (*candidate_refs, TASK168_TASK160_V06_ENVELOPE_EVIDENCE_REF)
    envelope_map["evidence_refs"] = _merge_evidence_refs(
        envelope_map.get("evidence_refs"), (*candidate_refs, configuration_ref)
    )
    payload["envelope_authority"] = envelope_map

    task026_result_id = getattr(task026, "result_id", None)
    task026_property_snapshot_hash = getattr(task026, "property_snapshot_hash", None)
    if (
        type(task026_result_id) is not str
        or not task026_result_id
        or type(task026_property_snapshot_hash) is not str
        or not task026_property_snapshot_hash
    ):
        raise _StageFailure(
            CandidateStage.THERMAL_CLOSURE,
            BlockerCode.TUBE_SIDE_REPLAY_FAILED,
            "task026_result",
            "TASK-026 result identity is incomplete",
        )

    adapters = payload.get("adapter_evidence")
    if type(adapters) not in (list, tuple):
        raise _StageFailure(
            CandidateStage.THERMAL_CLOSURE,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "evaluation_input_authority.task160_request_template.adapter_evidence",
        )
    adapters = cast(list[object] | tuple[object, ...], adapters)
    candidate_adapters: list[dict[str, object]] = []
    task026_adapter_count = 0
    for item in adapters:
        if type(item) is not dict:
            raise _StageFailure(
                CandidateStage.THERMAL_CLOSURE,
                BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                "evaluation_input_authority.task160_request_template.adapter_evidence",
            )
        adapter = dict(cast(dict[str, object], item))
        if adapter.get("source_task_id") == "TASK026":
            task026_adapter_count += 1
            adapter["source_result_identity"] = task026_result_id
        candidate_adapters.append(adapter)
    if task026_adapter_count != 1:
        raise _StageFailure(
            CandidateStage.THERMAL_CLOSURE,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "evaluation_input_authority.task160_request_template.adapter_evidence",
            "exactly one TASK026 adapter is required",
        )
    payload["adapter_evidence"] = candidate_adapters

    streams = payload.get("stream_records")
    if type(streams) not in (list, tuple):
        raise _StageFailure(
            CandidateStage.THERMAL_CLOSURE,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "evaluation_input_authority.task160_request_template.stream_records",
        )
    streams = cast(list[object] | tuple[object, ...], streams)
    candidate_streams: list[dict[str, object]] = []
    tube_stream_count = 0
    for item in streams:
        if type(item) is not dict:
            raise _StageFailure(
                CandidateStage.THERMAL_CLOSURE,
                BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                "evaluation_input_authority.task160_request_template.stream_records",
            )
        stream = dict(cast(dict[str, object], item))
        if stream.get("side_binding") == "TUBE_SIDE":
            tube_stream_count += 1
            snapshot = stream.get("property_snapshot")
            if type(snapshot) is not dict:
                raise _StageFailure(
                    CandidateStage.THERMAL_CLOSURE,
                    BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                    "evaluation_input_authority.task160_request_template.stream_records.property_snapshot",
                )
            snapshot_copy = dict(cast(dict[str, object], snapshot))
            snapshot_identity = snapshot_copy.get("property_snapshot_identity")
            if type(snapshot_identity) is not dict:
                raise _StageFailure(
                    CandidateStage.THERMAL_CLOSURE,
                    BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                    "evaluation_input_authority.task160_request_template.stream_records.property_snapshot.property_snapshot_identity",
                )
            identity_copy = dict(cast(dict[str, object], snapshot_identity))
            identity_copy["value"] = task026_property_snapshot_hash
            snapshot_copy["property_snapshot_identity"] = identity_copy
            stream["property_snapshot"] = snapshot_copy
        candidate_streams.append(stream)
    if tube_stream_count != 1:
        raise _StageFailure(
            CandidateStage.THERMAL_CLOSURE,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "evaluation_input_authority.task160_request_template.stream_records",
            "exactly one TUBE_SIDE stream is required",
        )
    payload["stream_records"] = candidate_streams
    return payload


def _task161_payload(
    authority: Task168EvaluationInputAuthority,
    task160: Task160Result,
) -> dict[str, object]:
    """Materialize the existing TASK-161 request from the live TASK-160 result."""

    payload = _template_mapping(
        authority.task161_request_template,
        CandidateStage.THERMAL_CLOSURE,
        "evaluation_input_authority.task161_request_template",
    )
    payload["task160_result"] = task160
    return payload


def _task162_binding(
    value: object,
    task038: Task038SuccessResult,
    task160: Task160Result,
    task161: Task161Result,
) -> object:
    if value is not None and dataclasses.is_dataclass(value):
        try:
            return replace(
                cast(Any, value),
                task160_result_hash=task160.result_hash,
                task160_result_id=str(task160.result_id),
                task161_result_hash=task161.result_hash,
                task161_result_id=str(task161.result_id),
                task038_result_hash=task038.result_hash,
                task038_result_id=task038.result_id,
            )
        except (TypeError, ValueError) as exc:
            raise _StageFailure(
                CandidateStage.THERMAL_CLOSURE,
                BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                "evaluation_input_authority.task162_binding_authority",
            ) from exc
    raise _StageFailure(
        CandidateStage.THERMAL_CLOSURE,
        BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
        "evaluation_input_authority.task162_binding_authority",
    )


def _task167_payload(
    authority: Task168EvaluationInputAuthority,
    configuration: ShellAndTubeConfiguration,
    bell: Task166Result,
    tube: TubeSideThermalResult,
) -> dict[str, object]:
    from hexagent.exchangers.shell_tube.engineering_screening import authority as task167_authority

    if authority.task167_screening_requirements is None:
        raise _StageFailure(
            CandidateStage.ENGINEERING_SCREENING,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "evaluation_input_authority.task167_screening_requirements",
        )
    if authority.task167_screening_property_snapshot is None:
        raise _StageFailure(
            CandidateStage.ENGINEERING_SCREENING,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            "evaluation_input_authority.task167_screening_property_snapshot",
        )
    return {
        "schema_version": task167_authority.REQUEST_SCHEMA_VERSION,
        "task167_version": task167_authority.TASK167_VERSION,
        "source_definition_id": task167_authority.SOURCE_DEFINITION_ID,
        "task020_configuration": configuration,
        "task166_result": bell,
        "tube_side_result": tube,
        "screening_requirements": authority.task167_screening_requirements,
        "screening_property_snapshot": authority.task167_screening_property_snapshot,
        "nozzle_geometry": authority.task167_nozzle_geometry,
        "approved_rule_pack_authority": authority.task167_approved_rule_pack_authority,
        "request_metadata": authority.task167_request_metadata,
    }


def _execute_candidate_chain(
    request: Task168Request,
    candidate: CandidateSpec,
    record: ShellGeometryRecord,
) -> tuple[_ExecutionBundle, _StageFailure | None, CandidateStage | None]:
    authority = request.evaluation_input_authority
    bundle = _ExecutionBundle()
    last_successful: CandidateStage | None = None

    def step(stage: CandidateStage, field_path: str, operation: Any) -> object:
        nonlocal last_successful
        value = _call_stage(stage, field_path, operation)
        last_successful = stage
        return value

    try:
        configuration = cast(
            ShellAndTubeConfiguration,
            step(
                CandidateStage.CONFIGURATION,
                "task020",
                lambda: _materialize_candidate_configuration(
                    request.task020_configuration,
                    candidate,
                ),
            ),
        )
        bundle.task020_configuration = configuration
        layout_outcome = step(
            CandidateStage.TUBE_LAYOUT,
            "task021",
            lambda: validate_task021(
                _task021_payload(authority, candidate, configuration),
                software_version=TASK168_IMPLEMENTATION_SOFTWARE_VERSION,
                git_commit="task168-orchestration",
            ),
        )
        bundle.task021_layout = _result_payload(
            layout_outcome,
            ("layout",),
            CandidateStage.TUBE_LAYOUT,
            "task021",
        )
        layout = bundle.task021_layout
        if type(layout) is not TubeLayout or not layout.layout_id or not layout.layout_hash:
            raise _StageFailure(
                CandidateStage.TUBE_LAYOUT,
                BlockerCode.TASK021_REPLAY_FAILED,
                "task021.layout",
            )

        geometry_outcome = step(
            CandidateStage.SHELL_BUNDLE_GEOMETRY,
            "task022",
            lambda: validate_task022(
                _task022_payload(
                    authority,
                    candidate,
                    configuration,
                    layout,
                    record,
                ),
                software_version=TASK168_IMPLEMENTATION_SOFTWARE_VERSION,
                git_commit="task168-orchestration",
            ),
        )
        bundle.task022_geometry = _result_payload(
            geometry_outcome,
            ("geometry",),
            CandidateStage.SHELL_BUNDLE_GEOMETRY,
            "task022",
        )
        native_geometry = bundle.task022_geometry

        baffle_outcome = step(
            CandidateStage.BAFFLE_GEOMETRY,
            "task024",
            lambda: validate_task024(
                _task024_payload(
                    authority,
                    candidate,
                    configuration,
                    layout,
                    native_geometry,
                )
            ),
        )
        bundle.task024_geometry = _result_payload(
            baffle_outcome,
            ("geometry",),
            CandidateStage.BAFFLE_GEOMETRY,
            "task024",
        )
        bundle.task024_result = baffle_outcome

        task025_outcome = step(
            CandidateStage.TUBE_SIDE,
            "task025",
            lambda: evaluate_task025(
                _task025_payload(
                    authority.task025_request_template,
                    candidate,
                    configuration,
                    layout,
                    CandidateStage.TUBE_SIDE,
                    "evaluation_input_authority.task025_request_template",
                )
            ),
        )
        if type(task025_outcome) is not Task025ValidResult:
            raise _StageFailure(
                CandidateStage.TUBE_SIDE,
                BlockerCode.TUBE_SIDE_REPLAY_FAILED,
                "task025.result",
                "TASK-025 did not return a valid result",
            )
        # TASK-025's public success object is itself the result (unlike the
        # wrapper-shaped validation results used by TASK-021/022/024).
        bundle.task025_result = task025_outcome

        def run_task026() -> object:
            raw_or_request = authority.task026_request
            if type(raw_or_request) is TubeSideThermalRequest:
                task026_request = raw_or_request
            else:
                projected = _public_value(raw_or_request)
                built_request = build_raw_tube_side_request_envelope(projected)
                if type(built_request) is not TubeSideThermalRequest:
                    raise _StageFailure(
                        CandidateStage.TUBE_SIDE,
                        BlockerCode.TUBE_SIDE_REPLAY_FAILED,
                        "task026_request",
                    )
                task026_request = built_request
            result = compute_tube_side_heat_transfer_coefficient(
                task026_request,
                bundle.task025_result,
            )
            if type(result) is not TubeSideThermalResult:
                raise _StageFailure(
                    CandidateStage.TUBE_SIDE,
                    BlockerCode.TUBE_SIDE_REPLAY_FAILED,
                    "task026_result",
                )
            return result

        bundle.task026_result = step(CandidateStage.TUBE_SIDE, "task026", run_task026)
        last_successful = CandidateStage.TUBE_SIDE

        def run_shell_chain() -> tuple[
            object,
            object,
            dict[str, object],
            object,
            object,
            object,
            object,
        ]:
            request031 = _task031_payload(
                authority,
                configuration,
                layout,
                bundle.task024_result,
                bundle.task024_geometry,
            )
            result031 = validate_task031(request031)
            _result_payload(result031, ("geometry",), CandidateStage.SHELL_SIDE_BELL, "task031")
            snapshot = authority.task032_property_snapshot
            if snapshot is None:
                snapshot = authority.task027_property_snapshot
            request032 = _task032_payload(
                authority,
                result031,
                configuration,
                layout,
            )
            result032 = validate_task032(request032)
            flow = _result_payload(
                result032, ("flow_state",), CandidateStage.SHELL_SIDE_BELL, "task032"
            )
            request033 = _task033_payload(
                authority,
                result032,
                request032,
                configuration,
                layout,
            )
            result033 = validate_task033(request033)
            heat = _result_payload(
                result033, ("heat_transfer",), CandidateStage.SHELL_SIDE_BELL, "task033"
            )
            request034 = _task034_payload(
                authority,
                request031,
                result031,
                result032,
                result033,
                request033,
                configuration,
                layout,
                bundle.task024_geometry,
            )
            result034 = validate_task034(request034)
            pressure = _result_payload(
                result034, ("pressure_drop",), CandidateStage.SHELL_SIDE_BELL, "task034"
            )
            request035 = _task035_payload(
                authority,
                result031,
                result032,
                result033,
                result034,
                configuration,
                layout,
            )
            result035 = validate_task035(request035)
            result035_payload = _result_payload(
                result035, ("success_result",), CandidateStage.SHELL_SIDE_BELL, "task035"
            )
            del snapshot, flow, heat, pressure
            return (
                request031,
                result031,
                request032,
                result032,
                result033,
                result034,
                result035_payload,
            )

        shell_values = step(CandidateStage.SHELL_SIDE_BELL, "task031_to_task035", run_shell_chain)
        request031, result031, request032, result032, result033, result034, result035 = cast(
            tuple[object, object, dict[str, object], object, object, object, object],
            shell_values,
        )
        bundle.task031_geometry = getattr(result031, "geometry", None)
        bundle.task032_flow_state = getattr(result032, "flow_state", None)
        bundle.task033_heat_transfer = getattr(result033, "heat_transfer", None)
        bundle.task034_pressure_drop = getattr(result034, "pressure_drop", None)
        bundle.task035_result = result035
        if bundle.task031_geometry is None or bundle.task032_flow_state is None:
            raise _StageFailure(
                CandidateStage.SHELL_SIDE_BELL,
                BlockerCode.TASK166_REPLAY_FAILED,
                "task031_to_task035",
            )

        bell_outcome = step(
            CandidateStage.SHELL_SIDE_BELL,
            "task166",
            lambda: validate_task166(
                _task166_payload(
                    authority,
                    configuration,
                    layout,
                    bundle.task022_geometry,
                    bundle.task024_geometry,
                    result031,
                    result032,
                    request032,
                )
            ),
        )
        bundle.task166_result = _result_payload(
            bell_outcome, ("valid",), CandidateStage.SHELL_SIDE_BELL, "task166"
        )
        if type(bundle.task166_result) is not Task166Result:
            raise _StageFailure(
                CandidateStage.SHELL_SIDE_BELL,
                BlockerCode.TASK166_REPLAY_FAILED,
                "task166.valid",
            )
        bell = bundle.task166_result
        if (
            task166_canonical.result_hash(bell) != bell.result_hash
            or task166_canonical.result_id(bell.result_hash) != bell.result_id
        ):
            raise _StageFailure(
                CandidateStage.SHELL_SIDE_BELL,
                BlockerCode.TASK166_REPLAY_FAILED,
                "task166.identity",
            )

        if type(authority.task037_request) is not type(None):
            result037_outcome = step(
                CandidateStage.OVERALL_RESISTANCE,
                "task037",
                lambda: evaluate_task037(
                    cast(Any, authority.task037_request),
                    layout,
                    bundle.task025_result,
                ),
            )
            bundle.task037_result = _result_payload(
                result037_outcome,
                ("success_result",),
                CandidateStage.OVERALL_RESISTANCE,
                "task037",
            )
        else:
            raise _StageFailure(
                CandidateStage.OVERALL_RESISTANCE,
                BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                "evaluation_input_authority.task037_request",
            )
        if type(
            bundle.task037_result
        ) is not Task037SuccessResult or not verify_task037_success_identity(bundle.task037_result):
            raise _StageFailure(
                CandidateStage.OVERALL_RESISTANCE,
                BlockerCode.OVERALL_RESISTANCE_REPLAY_FAILED,
                "task037.result",
            )

        def run_task038() -> object:
            binding = authority.task038_service_binding_authority
            if binding is None:
                raise _StageFailure(
                    CandidateStage.UA,
                    BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                    "evaluation_input_authority.task038_service_binding_authority",
                )
            try:
                binding = replace(
                    cast(Any, binding),
                    task026_result_hash=cast(Any, bundle.task026_result).result_hash,
                    task026_property_snapshot_hash=cast(
                        Any, bundle.task026_result
                    ).property_snapshot_hash,
                )
                binding = replace(binding, authority_hash=service_binding_hash(binding))
            except (TypeError, ValueError, AttributeError) as exc:
                raise _StageFailure(
                    CandidateStage.UA,
                    BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                    "task038_service_binding_authority",
                ) from exc
            raw = {
                "schema_version": "task038.request.v1",
                "profile_id": "hxforge.shell_tube.overall_u_ua.v1",
                "task025_result": bundle.task025_result,
                "task026_result": bundle.task026_result,
                "task035_result": bundle.task035_result,
                "task037_result": bundle.task037_result,
                "tube_side_service_binding_authority": binding,
                "evidence_refs": authority.evidence_refs,
            }
            request038 = build_raw_overall_u_ua_request(raw)
            if not hasattr(request038, "task025_result"):
                raise _StageFailure(
                    CandidateStage.UA,
                    BlockerCode.UA_REPLAY_FAILED,
                    "task038.request",
                )
            result038_outcome = evaluate_task038(cast(Any, request038))
            result038 = _result_payload(
                result038_outcome, ("success_result",), CandidateStage.UA, "task038"
            )
            if type(result038) is not Task038SuccessResult:
                raise _StageFailure(
                    CandidateStage.UA, BlockerCode.UA_REPLAY_FAILED, "task038.result"
                )
            if not verify_task038_success_identity(result038) or not verify_task038_provenance(
                result038.provenance
            ):
                raise _StageFailure(
                    CandidateStage.UA, BlockerCode.UA_REPLAY_FAILED, "task038.identity"
                )
            return result038

        bundle.task038_result = step(CandidateStage.UA, "task038", run_task038)

        def run_task162() -> tuple[Task162Result, Task162SuccessReplayEvidence]:
            if (
                authority.task160_request_template is None
                or authority.task161_request_template is None
                or authority.task162_case_authority is None
                or authority.task162_binding_authority is None
            ):
                raise _StageFailure(
                    CandidateStage.THERMAL_CLOSURE,
                    BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                    "evaluation_input_authority.task160_request_template",
                )

            task160_outcome = validate_task160(
                _task160_payload(
                    authority,
                    configuration,
                    candidate,
                    cast(TubeSideThermalResult, bundle.task026_result),
                )
            )
            task160_value = _result_payload(
                task160_outcome,
                ("valid",),
                CandidateStage.THERMAL_CLOSURE,
                "task160",
            )
            if type(task160_value) is not Task160Result:
                raise _StageFailure(
                    CandidateStage.THERMAL_CLOSURE,
                    BlockerCode.TASK162_REPLAY_FAILED,
                    "task160.result",
                )
            task161_outcome = validate_task161(_task161_payload(authority, task160_value))
            task161_value = _result_payload(
                task161_outcome,
                ("valid",),
                CandidateStage.THERMAL_CLOSURE,
                "task161",
            )
            if type(task161_value) is not Task161Result:
                raise _StageFailure(
                    CandidateStage.THERMAL_CLOSURE,
                    BlockerCode.TASK162_REPLAY_FAILED,
                    "task161.result",
                )
            binding = _task162_binding(
                authority.task162_binding_authority,
                cast(Task038SuccessResult, bundle.task038_result),
                task160_value,
                task161_value,
            )
            raw = {
                "schema_version": "task162.schema.v1",
                "task162_version": "task162.v1",
                "source_definition_id": "TASK162-SOURCE-DEFINITION-R1-ISSUE-229",
                "task160_result": task160_value,
                "task161_result": task161_value,
                "task038_result": bundle.task038_result,
                "cross_producer_binding_authority": binding,
                "case_authority": authority.task162_case_authority,
                "request_metadata": authority.task162_request_metadata,
            }
            outcome = validate_task162(raw)
            result = _result_payload(outcome, ("valid",), CandidateStage.THERMAL_CLOSURE, "task162")
            if type(result) is not Task162Result:
                raise _StageFailure(
                    CandidateStage.THERMAL_CLOSURE,
                    BlockerCode.TASK162_REPLAY_FAILED,
                    "task162.result",
                )
            task162_request = Task162Request(
                schema_version="task162.schema.v1",
                task162_version="task162.v1",
                source_definition_id="TASK162-SOURCE-DEFINITION-R1-ISSUE-229",
                task160_result=task160_value,
                task161_result=task161_value,
                task038_result=cast(Task038SuccessResult, bundle.task038_result),
                cross_producer_binding_authority=cast(
                    Task162CrossProducerBindingAuthority, binding
                ),
                case_authority=cast(Task162CaseAuthority, authority.task162_case_authority),
                request_metadata=authority.task162_request_metadata,
            )
            evidence = issue_success_replay_evidence(task162_request, result)
            if evidence is None:
                raise _StageFailure(
                    CandidateStage.THERMAL_CLOSURE,
                    BlockerCode.TASK162_REPLAY_FAILED,
                    "task162.replay_evidence",
                )
            verification = verify_task162_success(result, evidence)
            if _status_text(verification.status) != "ACCEPTED":
                raise _StageFailure(
                    CandidateStage.THERMAL_CLOSURE,
                    BlockerCode.TASK162_REPLAY_FAILED,
                    "task162.replay_evidence",
                )
            return result, evidence

        thermal, replay = cast(
            tuple[Task162Result, Task162SuccessReplayEvidence],
            step(CandidateStage.THERMAL_CLOSURE, "task162", run_task162),
        )
        bundle.task162_result = thermal
        bundle.task162_replay_evidence = replay

        def run_task029() -> object:
            if (
                authority.task027_property_snapshot is None
                or authority.task027_roughness_authority is None
                or authority.task027_constant_density_assertion is None
                or authority.task027_zero_net_elevation_assertion is None
                or authority.task027_flow_direction_assertion is None
            ):
                raise _StageFailure(
                    CandidateStage.TUBE_DP,
                    BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                    "evaluation_input_authority.task027_*",
                )
            result027 = compute_task027_friction_pressure_drop(
                task025_result=cast(Any, bundle.task025_result),
                task026_result=cast(Any, bundle.task026_result),
                property_snapshot=cast(Any, authority.task027_property_snapshot),
                constant_density_path_assertion=cast(
                    Any, authority.task027_constant_density_assertion
                ),
                zero_net_elevation_change_assertion=cast(
                    Any, authority.task027_zero_net_elevation_assertion
                ),
                flow_direction_assertion=cast(Any, authority.task027_flow_direction_assertion),
                roughness_authority=cast(Any, authority.task027_roughness_authority),
            )
            if type(result027).__name__ != "Task027SuccessResult":
                raise _StageFailure(
                    CandidateStage.TUBE_DP, BlockerCode.TUBE_SIDE_REPLAY_FAILED, "task027.result"
                )
            try:
                task028_template_value = _public_value(
                    authority.task028_request_template, decimal_strings=False
                )
            except (TypeError, ValueError, UnicodeError, ArithmeticError) as exc:
                raise _StageFailure(
                    CandidateStage.TUBE_DP,
                    BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                    "evaluation_input_authority.task028_request_template",
                    type(exc).__name__,
                ) from exc
            if type(task028_template_value) is not dict:
                raise _StageFailure(
                    CandidateStage.TUBE_DP,
                    BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                    "evaluation_input_authority.task028_request_template",
                    "a raw TASK-028 mapping is required",
                )
            task028_template = cast(dict[str, object], task028_template_value)
            task028_template["task025_valid_result"] = _public_value(
                bundle.task025_result, decimal_strings=False
            )
            task028_template["task026_success_result"] = _public_value(
                bundle.task026_result, decimal_strings=False
            )
            if authority.task027_property_snapshot is not None:
                task028_template["property_snapshot"] = _public_value(
                    authority.task027_property_snapshot, decimal_strings=False
                )
                task028_template["property_snapshot_hash"] = cast(
                    Any, bundle.task026_result
                ).property_snapshot_hash
            task028_template["constant_density_path_assertion"] = _status_text(
                authority.task027_constant_density_assertion
            )
            task028_template["zero_net_elevation_change_assertion"] = _status_text(
                authority.task027_zero_net_elevation_assertion
            )
            task028_template["flow_direction_assertion"] = _status_text(
                authority.task027_flow_direction_assertion
            )
            result028 = compute_task028_local_loss(
                raw_request=task028_template,
                task025_result=cast(Any, bundle.task025_result),
                task026_result=cast(Any, bundle.task026_result),
            )
            if type(result028).__name__ != "Task028SuccessResult":
                raise _StageFailure(
                    CandidateStage.TUBE_DP, BlockerCode.TUBE_SIDE_REPLAY_FAILED, "task028.result"
                )
            task029_template = authority.task029_request_template
            if not dataclasses.is_dataclass(task029_template):
                raise _StageFailure(
                    CandidateStage.TUBE_DP,
                    BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                    "evaluation_input_authority.task029_request_template",
                    "a typed TASK-029 request template is required",
                )
            task029_template_any = cast(Any, task029_template)
            from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.request import (
                build_task029_request,
            )

            composition = task029_template_any.composition_authority
            from ..tube_side_pressure_drop_composition.identity import (
                compute_composition_authority_hash,
                compute_member_authority_hash,
            )

            template_members = tuple(composition.member_authorities)
            template_components = tuple(
                member
                for member in template_members
                if member.producer_task is ProducerTask.TASK_028
            )
            template_friction = tuple(
                member
                for member in template_members
                if member.producer_task is ProducerTask.TASK_027
            )
            result027_any = cast(Any, result027)
            result028_any = cast(Any, result028)
            components = tuple(result028_any.component_results)
            if len(template_components) != len(components) or len(template_friction) != 1:
                raise _StageFailure(
                    CandidateStage.TUBE_DP,
                    BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
                    "evaluation_input_authority.task029_request_template.composition_authority.member_authorities",
                    "TASK-029 template must provide one member per local-loss result "
                    "and one friction member",
                )
            ordered_template_components = tuple(
                sorted(template_components, key=lambda item: item.global_path_sequence_index)
            )
            members: list[Any] = []
            for index, component in enumerate(components):
                # Component identity is produced by the live TASK-028 result;
                # the base template authorizes the ordered local-loss slots,
                # not a stale candidate-specific component identifier.
                member = ordered_template_components[index]
                updated = replace(
                    member,
                    global_path_sequence_index=index,
                    producer_component_identity=component.component_id,
                    expected_producer_component_type=_status_text(component.component_type),
                    expected_producer_authority_hash=component.authority_hash,
                    expected_upstream_reference_plane=component.upstream_reference_plane,
                    expected_downstream_reference_plane=component.downstream_reference_plane,
                    expected_multiplicity=component.multiplicity,
                    member_authority_hash="",
                )
                members.append(
                    replace(updated, member_authority_hash=compute_member_authority_hash(updated))
                )

            friction = template_friction[0]
            friction_updated = replace(
                friction,
                global_path_sequence_index=len(members),
                expected_upstream_reference_plane=result027_any.upstream_reference_plane,
                expected_downstream_reference_plane=result027_any.downstream_reference_plane,
                expected_producer_authority_hash="",
                expected_multiplicity=1,
                member_authority_hash="",
            )
            members.append(
                replace(
                    friction_updated,
                    member_authority_hash=compute_member_authority_hash(friction_updated),
                )
            )
            composition = replace(
                composition,
                member_authorities=tuple(members),
                start_reference_plane=members[0].expected_upstream_reference_plane,
                end_reference_plane=members[-1].expected_downstream_reference_plane,
                composition_authority_hash="",
            )
            composition = replace(
                composition,
                composition_authority_hash=compute_composition_authority_hash(composition),
            )
            task029_request = build_task029_request(
                profile_id=task029_template_any.profile_id,
                task027_success_result=cast(Any, result027),
                task028_success_result=cast(Any, result028),
                composition_authority=composition,
            )
            # TASK-029's raw boundary admits only its frozen four-field
            # request envelope.  A typed Task029Request also contains the
            # producer result objects, which are passed separately to the
            # public composition operation and must not leak into the raw
            # request projection as unknown fields.
            task029_raw = {
                "schema_version": task029_request.schema_version,
                "profile_id": task029_request.profile_id,
                "composition_authority": _public_value(
                    task029_request.composition_authority,
                    decimal_strings=False,
                ),
                "request_hash": task029_request.request_hash,
            }
            result029 = compute_task029_composition(
                task029_raw,
                task027_success_result=cast(Any, result027),
                task028_success_result=cast(Any, result028),
                input_evidence_refs=authority.evidence_refs,
            )
            if type(result029) is not Task029SuccessResult:
                raise _StageFailure(
                    CandidateStage.TUBE_DP, BlockerCode.TUBE_SIDE_REPLAY_FAILED, "task029.result"
                )
            return result027, result028, result029

        pressure_values = cast(
            tuple[object, object, object],
            step(CandidateStage.TUBE_DP, "task027_to_task029", run_task029),
        )
        bundle.task027_result, bundle.task028_result, bundle.task029_result = pressure_values

        screening_outcome = step(
            CandidateStage.ENGINEERING_SCREENING,
            "task167",
            lambda: validate_task167(
                _task167_payload(
                    authority,
                    configuration,
                    bundle.task166_result,
                    cast(TubeSideThermalResult, bundle.task026_result),
                )
            ),
        )
        bundle.task167_result = _result_payload(
            screening_outcome,
            ("valid",),
            CandidateStage.ENGINEERING_SCREENING,
            "task167",
        )
        if type(bundle.task167_result) is not Task167Result:
            raise _StageFailure(
                CandidateStage.ENGINEERING_SCREENING,
                BlockerCode.TASK167_REPLAY_FAILED,
                "task167.result",
            )
        screening = bundle.task167_result
        if (
            task167_canonical.result_hash(screening) != screening.result_hash
            or task167_canonical.result_id(screening.result_hash) != screening.result_id
        ):
            raise _StageFailure(
                CandidateStage.ENGINEERING_SCREENING,
                BlockerCode.TASK167_REPLAY_FAILED,
                "task167.identity",
            )
        return bundle, None, CandidateStage.ENGINEERING_SCREENING
    except _StageFailure as failure:
        return bundle, failure, last_successful


def _task_template_with_layout(
    template: object | None,
    configuration: ShellAndTubeConfiguration,
    layout: object,
    stage: CandidateStage,
    field_path: str,
) -> dict[str, object]:
    payload = _template_mapping(template, stage, field_path)
    if "task020_configuration" in payload:
        payload["task020_configuration"] = configuration
    if "configuration" in payload:
        payload["configuration"] = configuration
    if "task021_layout" in payload:
        payload["task021_layout"] = layout
    if "tube_layout" in payload:
        payload["tube_layout"] = layout
    return payload


def _task025_payload(
    template: object | None,
    candidate: CandidateSpec,
    configuration: ShellAndTubeConfiguration,
    layout: Any,
    stage: CandidateStage,
    field_path: str,
) -> dict[str, object]:
    """Materialize a candidate-owned raw TASK-025 request.

    TASK-025 intentionally keeps its length and participation authorities as
    exact typed objects.  A generic dataclass-to-mapping projection would
    destroy those producer-owned value objects (and their reference-plane
    semantics), so this boundary projects the surrounding request while
    rebuilding only the candidate-dependent authority bindings.
    """

    payload = _template_mapping(template, stage, field_path)
    source = template

    def source_field(name: str) -> object:
        if isinstance(source, Mapping):
            return source.get(name)
        return getattr(source, name, None)

    internal = source_field("internal_flow_authority")
    heat_transfer = source_field("heat_transfer_authority")
    participation = source_field("hydraulic_participation_authority")
    if type(internal) is not InternalFlowLengthAuthority:
        raise _StageFailure(
            stage,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            field_path + ".internal_flow_authority",
        )
    if type(heat_transfer) is not HeatTransferLengthAuthority:
        raise _StageFailure(
            stage,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            field_path + ".heat_transfer_authority",
        )
    if type(participation) is not Task025HydraulicParticipationAuthority:
        raise _StageFailure(
            stage,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            field_path + ".hydraulic_participation_authority",
        )

    flow_length_hash = internal_flow_authority_length_hash(
        candidate.tube_length_m,
        internal.start_plane,
        internal.end_plane,
        internal.authority_mode,
    )
    heat_length_hash = heat_transfer_authority_length_hash(
        candidate.tube_length_m,
        heat_transfer.start_plane,
        heat_transfer.end_plane,
        heat_transfer.authority_mode,
    )
    candidate_internal = replace(
        internal,
        length_m=candidate.tube_length_m,
        length_hash=flow_length_hash,
    )
    candidate_heat_transfer = replace(
        heat_transfer,
        length_m=candidate.tube_length_m,
        length_hash=heat_length_hash,
    )
    position_ids = tuple(position.position_id for position in getattr(layout, "positions", ()))
    if not position_ids:
        raise _StageFailure(
            stage,
            BlockerCode.TUBE_SIDE_REPLAY_FAILED,
            field_path + ".hydraulic_participation_authority",
            "candidate layout has no enumerated positions",
        )
    candidate_participation = replace(
        participation,
        all_layout_position_ids=position_ids,
        active_position_ids=position_ids,
        inactive_position_ids=(),
        hydraulic_authority_hash=hydraulic_authority_hash(
            task020_configuration_id=configuration.configuration_id,
            task021_layout_id=layout.layout_id,
            internal_flow_length_hash_value=flow_length_hash,
            heat_transfer_length_hash_value=heat_length_hash,
            all_layout_position_ids=position_ids,
            active_position_ids=position_ids,
            inactive_position_ids=(),
            hydraulic_authority_mode=participation.authority_mode,
            participation_evidence_refs=participation.evidence_refs,
        ),
    )
    payload.update(
        {
            "task020_configuration": configuration,
            "task021_layout": layout,
            "internal_flow_authority": candidate_internal,
            "heat_transfer_authority": candidate_heat_transfer,
            "hydraulic_participation_authority": candidate_participation,
            "flow_path_mode": source_field("flow_path_mode"),
            "hydraulic_authority_mode": source_field("hydraulic_authority_mode"),
            "evidence_refs": source_field("evidence_refs"),
        }
    )
    if type(payload["evidence_refs"]) is not tuple:
        raise _StageFailure(
            stage,
            BlockerCode.EVALUATION_AUTHORITY_REQUIRED,
            field_path + ".evidence_refs",
            "TASK-025 evidence_refs must remain an exact tuple",
        )
    return payload


def _bundle_evidence(bundle: _ExecutionBundle) -> dict[str, tuple[tuple[str, str], ...]]:
    return {
        "configuration": _configuration_evidence(bundle.task020_configuration),
        "geometry": _evidence(bundle.task022_geometry),
        "tube_layout": _evidence(bundle.task021_layout),
        "tube_side": _evidence(bundle.task026_result, result_name="tube_side"),
        "bell": _evidence(bundle.task166_result, result_name="bell"),
        "overall": _evidence(bundle.task038_result, result_name="ua"),
        "thermal": _evidence(bundle.task162_result, result_name="task162"),
        "tube_dp": _evidence(bundle.task029_result, result_name="tube_dp"),
        "shell_dp": _evidence(bundle.task166_result, result_name="shell_dp"),
        "screening": _evidence(bundle.task167_result, result_name="task167"),
    }


def _orchestrated_evaluate_candidate(
    request: Task168Request,
    candidate: CandidateSpec,
    record: ShellGeometryRecord,
) -> CandidateRecord:
    structural = _structural_blockers(candidate)
    if structural:
        return _base_record(candidate, stage=structural[0].stage, blockers=structural)
    bundle, failure, last_successful = _execute_candidate_chain(request, candidate, record)
    evidence = _bundle_evidence(bundle)
    if failure is not None:
        return _base_record(
            candidate,
            stage=failure.stage,
            blockers=(
                _blocker(
                    failure.code,
                    failure.stage,
                    failure.field_path,
                    request.evaluation_input_authority.evidence_refs,
                    failure.message,
                ),
            ),
            last_successful_stage=last_successful,
            configuration_evidence=evidence["configuration"],
            geometry_evidence=evidence["geometry"],
            tube_layout_evidence=evidence["tube_layout"],
            tube_side_evidence=evidence["tube_side"],
            bell_evidence=evidence["bell"],
            overall_u_ua_evidence=evidence["overall"],
            thermal_closure_evidence=evidence["thermal"],
            tube_dp_evidence=evidence["tube_dp"],
            shell_dp_evidence=evidence["shell_dp"],
            screening_evidence=evidence["screening"],
        )

    thermal = cast(Task162Result, bundle.task162_result)
    pressure = cast(Any, bundle.task029_result)
    bell = cast(Task166Result, bundle.task166_result)
    ua = cast(Task038SuccessResult, bundle.task038_result)
    screening = cast(Task167Result, bundle.task167_result)
    screening_status = _status_text(screening.aggregate_screening_status)
    warnings = _ordered_warnings(Task168Warning(code=_text(item)) for item in screening.warnings)
    if screening_status == "WARN" and not warnings:
        warnings = (Task168Warning("TASK167_SCREENING_WARN"),)

    constraints: list[tuple[str, str]] = []
    constraint_failures: list[Task168Blocker] = []
    requirement = request.requirement_authority
    q_method = _decimal_attr(thermal, "q_method")
    tube_dp = _decimal_attr(pressure, "modeled_total_tube_side_pressure_drop_pa")
    shell_dp = _decimal_attr(bell, "total_shell_pressure_drop")
    if q_method is None or tube_dp is None or shell_dp is None:
        return _base_record(
            candidate,
            stage=CandidateStage.CONSTRAINT_EVALUATION,
            blockers=(
                _blocker(
                    BlockerCode.CANDIDATE_STAGE_FAILED,
                    CandidateStage.CONSTRAINT_EVALUATION,
                    "producer_metrics",
                ),
            ),
            last_successful_stage=CandidateStage.ENGINEERING_SCREENING,
            configuration_evidence=evidence["configuration"],
            geometry_evidence=evidence["geometry"],
            tube_layout_evidence=evidence["tube_layout"],
            tube_side_evidence=evidence["tube_side"],
            bell_evidence=evidence["bell"],
            overall_u_ua_evidence=evidence["overall"],
            thermal_closure_evidence=evidence["thermal"],
            tube_dp_evidence=evidence["tube_dp"],
            shell_dp_evidence=evidence["shell_dp"],
            screening_evidence=evidence["screening"],
        )
    for name, actual, limit in (
        ("required_duty_w", q_method, requirement.required_duty_w),
        ("max_tube_dp_pa", tube_dp, requirement.max_tube_dp_pa),
        ("max_shell_dp_pa", shell_dp, requirement.max_shell_dp_pa),
    ):
        if limit is None:
            continue
        passed = actual >= limit if name == "required_duty_w" else actual <= limit
        constraints.append((name, "PASS" if passed else "BLOCKED"))
        if not passed:
            constraint_failures.append(
                _blocker(
                    BlockerCode.HARD_CONSTRAINT_UNSATISFIED,
                    CandidateStage.CONSTRAINT_EVALUATION,
                    name,
                    requirement.evidence_refs,
                )
            )
    metrics = tuple(
        (key, _text(value))
        for key, value in (
            ("physical_tube_count", getattr(bundle.task021_layout, "physical_tube_count", "")),
            ("tube_hole_count", getattr(bundle.task021_layout, "tube_hole_count", "")),
            ("modeled_ua_w_k", ua.modeled_ua_w_k),
            ("q_method_w", thermal.q_method),
            ("q_hot_w", thermal.q_hot),
            ("q_cold_w", thermal.q_cold),
            ("shell_dp_pa", bell.total_shell_pressure_drop),
            ("tube_dp_pa", tube_dp),
            ("task167_status", screening_status),
        )
    )
    common: dict[str, Any] = {
        "configuration_evidence": evidence["configuration"],
        "geometry_evidence": evidence["geometry"],
        "tube_layout_evidence": evidence["tube_layout"],
        "tube_side_evidence": evidence["tube_side"],
        "bell_evidence": evidence["bell"],
        "overall_u_ua_evidence": evidence["overall"],
        "thermal_closure_evidence": evidence["thermal"],
        "tube_dp_evidence": evidence["tube_dp"],
        "shell_dp_evidence": evidence["shell_dp"],
        "screening_evidence": evidence["screening"],
        "constraint_evaluations": tuple(constraints),
        "metrics": metrics,
        "warnings": warnings,
    }
    if constraint_failures:
        return _base_record(
            candidate,
            stage=CandidateStage.CONSTRAINT_EVALUATION,
            blockers=constraint_failures,
            last_successful_stage=CandidateStage.ENGINEERING_SCREENING,
            **common,
        )
    status = (
        CandidateStatus.WARN if screening_status == "WARN" or warnings else CandidateStatus.PASS
    )
    return _base_record(
        candidate,
        stage=CandidateStage.COMPLETE,
        last_successful_stage=CandidateStage.COMPLETE,
        disposition=CandidateDisposition.EVALUATED,
        status=status,
        **common,
    )


def _build_valid_batch(
    request: Task168Request,
    request_hash_value: str,
    authorities: tuple[DiscreteCandidateSetAuthority, ...],
    records: tuple[CandidateRecord, ...],
    theoretical_count: int,
) -> Task168ValidationResult:
    space_hash = candidate_space_hash(request, authorities)
    space_id = candidate_space_id(space_hash)
    pass_count = sum(item.status is CandidateStatus.PASS for item in records)
    warn_count = sum(item.status is CandidateStatus.WARN for item in records)
    blocked_count = sum(item.status is CandidateStatus.BLOCKED for item in records)
    warnings = _ordered_warnings(item for record in records for item in record.warnings)
    applicability = Task168Applicability(
        status=ApplicabilityStatus.APPLICABLE,
        checks=(
            ("CANDIDATE_SPACE_AUTHORITY_ACCEPTED", "PASS"),
            ("ENUMERATION_COMPLETE", "PASS"),
            ("ALL_CANDIDATES_DISPOSITIONED", "PASS"),
            ("NO_RANKING_OR_OPTIMIZATION", "PASS"),
        ),
    )
    completeness = Task168Completeness(
        required_fields=TASK168_COMPLETENESS_FIELDS,
        present_fields=TASK168_COMPLETENESS_FIELDS,
        status=CompletenessStatus.COMPLETE,
    )
    semantic_inputs = (
        ("request_hash", request_hash_value),
        ("candidate_space_hash", space_hash),
        ("requirement_authority_hash", requirement_authority_hash(request.requirement_authority)),
        ("shell_catalog_hash", request.shell_geometry_catalog.catalog_hash),
        ("candidate_count", str(len(records))),
    )
    empty_graph = ProvenanceGraph(
        nodes=(), edges=(), graph_hash="", self_edge_count=0, cycle_count=0
    )
    provisional = Task168BatchResult(
        schema_version=TASK168_RESULT_SCHEMA_VERSION,
        task168_version=TASK168_VERSION,
        implementation_software_version=TASK168_IMPLEMENTATION_SOFTWARE_VERSION,
        source_definition_id=request.source_definition_id,
        request_hash=request_hash_value,
        candidate_space_id=space_id,
        candidate_space_hash=space_hash,
        total_theoretical_combinations=theoretical_count,
        total_enumerated_candidates=len(records),
        pass_count=pass_count,
        warn_count=warn_count,
        blocked_count=blocked_count,
        candidate_records=records,
        warnings=warnings,
        blockers=(),
        applicability=applicability,
        completeness=completeness,
        provenance_semantic_inputs=semantic_inputs,
        provenance=empty_graph,
        result_hash="",
        result_id="",
    )
    digest = batch_result_hash(provisional)
    identifier = result_id(digest)
    graph = build_batch_provenance(
        request,
        request_hash=request_hash_value,
        candidate_space_hash=space_hash,
        records=records,
        result_id=identifier,
        result_hash=digest,
    )
    if not verify_provenance_graph(graph):
        return _typed_blocked(
            request_hash_value,
            (_blocker(BlockerCode.PROVENANCE_INVALID, CandidateStage.PROVENANCE),),
        )
    result = replace(provisional, provenance=graph, result_hash=digest, result_id=identifier)
    if (
        batch_result_hash(result) != result.result_hash
        or result_id(result.result_hash) != result.result_id
    ):
        return _typed_blocked(
            request_hash_value,
            (_blocker(BlockerCode.IDENTITY_REPLAY_FAILED, CandidateStage.IDENTITY),),
        )
    return Task168ValidationResult(status=ValidationStatus.VALID, valid=result)


def validate_request(raw: object) -> Task168ValidationResult:
    """Admit, enumerate, evaluate and classify one deterministic candidate space."""

    try:
        projection = project_raw(raw)
        raw_hash = raw_projection_hash_from_projection(projection)
    except RawProjectionFailure as failure:
        return _raw_blocked("", failure)
    request = _parse_request(raw)
    if request is None:
        return _typed_blocked(
            raw_hash, (_blocker(BlockerCode.INVALID_REQUEST_TYPE, CandidateStage.TYPED_VALIDATION),)
        )
    typed_failures = _validate_typed_request(request)
    try:
        request_hash_value = request_hash(request)
    except (TypeError, ValueError, UnicodeError, ArithmeticError):
        return _typed_blocked(
            raw_hash,
            (_blocker(BlockerCode.INVALID_REQUEST_SCHEMA, CandidateStage.TYPED_VALIDATION),),
        )
    if typed_failures:
        return _typed_blocked(request_hash_value, typed_failures)

    authorities = _authority_map(request)
    dimensions = tuple(
        _sort_values(authorities[role].values)
        for role in DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    theoretical_count = len(request.shell_geometry_catalog.records)
    for values in dimensions:
        theoretical_count *= len(values)
    if theoretical_count > MAX_RAW_COMBINATION_COUNT:
        return _typed_blocked(
            request_hash_value,
            (_blocker(BlockerCode.RESOURCE_BOUND_EXCEEDED, CandidateStage.CANDIDATE_AUTHORITY),),
        )
    if theoretical_count > MAX_MATERIALIZED_CANDIDATE_COUNT:
        return _typed_blocked(
            request_hash_value,
            (_blocker(BlockerCode.RESOURCE_BOUND_EXCEEDED, CandidateStage.CANDIDATE_AUTHORITY),),
        )
    records: list[CandidateRecord] = []
    for combination in product(request.shell_geometry_catalog.records, *dimensions):
        record = cast(ShellGeometryRecord, combination[0])
        values = tuple(combination[1:])
        candidate = _candidate(request, authorities, record, values)
        records.append(_orchestrated_evaluate_candidate(request, candidate, record))
    return _build_valid_batch(
        request,
        request_hash_value,
        request.discrete_candidate_set_authorities,
        tuple(records),
        theoretical_count,
    )


__all__ = ["validate_request"]
