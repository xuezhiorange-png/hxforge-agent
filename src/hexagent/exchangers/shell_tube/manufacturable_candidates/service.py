"""TASK-168 deterministic candidate generation and producer orchestration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from itertools import product
from typing import Any, cast

from hexagent.exchangers.shell_tube.baffle_geometry.models import BaffleGeometry
from hexagent.exchangers.shell_tube.bell_delaware import canonical as task166_canonical
from hexagent.exchangers.shell_tube.bell_delaware.models import Task166Result
from hexagent.exchangers.shell_tube.engineering_screening import canonical as task167_canonical
from hexagent.exchangers.shell_tube.engineering_screening.models import Task167Result
from hexagent.exchangers.shell_tube.models import ConstructionFamily, ShellAndTubeConfiguration
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
    Task038SuccessResult,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.provenance import (
    verify_provenance as verify_task038_provenance,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.validation import (
    verify_task038_success_identity,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.models import (
    Task037SuccessResult,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.validation import (
    verify_task037_success_identity,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure.models import (
    Task162Result,
    Task162SuccessReplayEvidence,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure.service import (
    verify_task162_success,
)
from hexagent.exchangers.shell_tube.tube_layout.canonical import layout_id as task021_layout_id
from hexagent.exchangers.shell_tube.tube_layout.models import TubeLayout
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029SuccessResult,
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
    Task168CandidateEvaluationContext,
    Task168Completeness,
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
        contexts = raw["candidate_evaluations"]
        metadata = raw["request_metadata"]
        if type(authorities) is list:
            authorities = tuple(authorities)
        if type(contexts) is list:
            contexts = tuple(contexts)
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
            candidate_evaluations=contexts,
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

    contexts = request.candidate_evaluations
    if type(contexts) is not tuple or any(
        type(item) is not Task168CandidateEvaluationContext for item in contexts
    ):
        failures.append(
            _blocker(
                BlockerCode.INVALID_REQUEST_SCHEMA,
                CandidateStage.TYPED_VALIDATION,
                "candidate_evaluations",
            )
        )
    elif len({item.candidate_id for item in contexts}) != len(contexts):
        failures.append(
            _blocker(
                BlockerCode.INVALID_REQUEST_SCHEMA,
                CandidateStage.TYPED_VALIDATION,
                "candidate_evaluations.candidate_id",
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
    )
    digest = candidate_hash(candidate)
    return replace(candidate, candidate_hash=digest, candidate_id=candidate_id(digest))


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


def _context_blockers(
    request: Task168Request,
    candidate: CandidateSpec,
    context: Task168CandidateEvaluationContext,
) -> tuple[Task168Blocker, ...]:
    """Replay each producer boundary in frozen stage order."""

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
        layout.task020_configuration_id != request.task020_configuration.configuration_id
        or layout.task020_configuration_hash != request.task020_configuration.configuration_hash
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


def _evaluate_candidate(
    request: Task168Request,
    candidate: CandidateSpec,
    context_by_id: dict[str, Task168CandidateEvaluationContext],
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
                    "candidate_evaluations",
                ),
            ),
        )
    failures = _context_blockers(request, candidate, context)
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
    context_by_id = {item.candidate_id: item for item in request.candidate_evaluations}
    for combination in product(request.shell_geometry_catalog.records, *dimensions):
        record = cast(ShellGeometryRecord, combination[0])
        values = tuple(combination[1:])
        candidate = _candidate(request, authorities, record, values)
        records.append(_evaluate_candidate(request, candidate, context_by_id))
    return _build_valid_batch(
        request,
        request_hash_value,
        request.discrete_candidate_set_authorities,
        tuple(records),
        theoretical_count,
    )


__all__ = ["validate_request"]
