"""Total, bounded TASK163 raw ingress projection."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import cast

from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority.models import (
    CatalogApplicability,
    CatalogBindingState,
    CatalogCompleteness,
    Task161FailureStage,
    Task161Result,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
    Task038SuccessResult,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure.models import (
    Task162AmbientHeatLossAssumption,
    Task162AxialHeatTransferAssumption,
    Task162BindingStatus,
    Task162BypassAssumption,
    Task162CaseAuthority,
    Task162CompatibilityDimension,
    Task162CompatibilityStatus,
    Task162CrossProducerBindingAuthority,
    Task162FlowOrientation,
    Task162HeatTransferCoefficientAssumption,
    Task162InternalSourceSinkAssumption,
    Task162LeakageAssumption,
    Task162Result,
    Task162ShellSideMixingModel,
    Task162ShellType,
    Task162SuccessReplayEvidence,
    Task162TubeSideMixing,
    Task162ValidationStatus,
    Task162WallPropertyAssumption,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.models import Task160Result

from .canonical import (
    task038_result_identity_projection,
    task160_result_identity_projection,
    task161_result_identity_projection,
    task162_result_identity_projection,
    task162_success_replay_evidence_identity_projection,
)
from .models import (
    TASK163_RAW_MAX_DEPTH,
    TASK163_RAW_MAX_NODES,
    TASK163_RAW_PROJECTION_SCHEMA_VERSION,
    TASK163_RAW_TEXT_BYTE_COUNT_LIMIT_PLUS_ONE,
    TASK163_SCHEMA_VERSION,
    TASK163_SOURCE_DEFINITION_ID,
    TASK163_VERSION,
    Task163FailureCode,
    Task163FailureStage,
    Task163RawProjectionKind,
    Task163RawProjectionNode,
    Task163RawRequestProjection,
)


@dataclass(frozen=True, slots=True)
class RawProjectionOutcome:
    projection: Task163RawRequestProjection
    reasons: tuple[Task163FailureCode, ...]


_TRUSTED_ENUM_TYPES: frozenset[type[Enum]] = frozenset(
    cast(type[Enum], enum_type)
    for enum_type in (
        CatalogApplicability,
        CatalogBindingState,
        CatalogCompleteness,
        Task162AmbientHeatLossAssumption,
        Task162AxialHeatTransferAssumption,
        Task162BindingStatus,
        Task162BypassAssumption,
        Task162CompatibilityDimension,
        Task162CompatibilityStatus,
        Task162FlowOrientation,
        Task162HeatTransferCoefficientAssumption,
        Task162InternalSourceSinkAssumption,
        Task162LeakageAssumption,
        Task162ShellSideMixingModel,
        Task162ShellType,
        Task161FailureStage,
        Task162ValidationStatus,
        Task162TubeSideMixing,
        Task162WallPropertyAssumption,
    )
)


def _trusted_enum_types() -> frozenset[type[Enum]]:
    # Importing the Task163 enum classes here avoids a circular import at
    # module initialization and, importantly, permits exact-type checks only.
    from .models import (
        Task163ApplicabilityCheckName,
        Task163ApplicabilityStatus,
        Task163CheckStatus,
        Task163CompletenessField,
        Task163CompletenessStatus,
        Task163DeferredCapability,
        Task163DeferredStatus,
        Task163FailureCode,
        Task163RawProjectionKind,
    )

    return _TRUSTED_ENUM_TYPES | frozenset(
        {
            Task163ApplicabilityCheckName,
            Task163ApplicabilityStatus,
            Task163CheckStatus,
            Task163CompletenessField,
            Task163CompletenessStatus,
            Task163DeferredCapability,
            Task163DeferredStatus,
            Task163FailureCode,
            Task163FailureStage,
            Task163RawProjectionKind,
        }
    )


class _Walker:
    def __init__(self) -> None:
        self.nodes = 0
        self.reasons: list[Task163FailureCode] = []

    def _reason(self, value: Task163FailureCode) -> None:
        if value not in self.reasons:
            self.reasons.append(value)

    def _marker(self, reason: Task163FailureCode) -> Task163RawProjectionNode:
        self._reason(reason)
        token = reason.value
        return Task163RawProjectionNode(
            field_name="__TASK163_LIMIT_MARKER__",
            kind=Task163RawProjectionKind.LIMIT_MARKER,
            type_identity=None,
            scalar_payload=token,
            children=(),
        )

    @staticmethod
    def _text_failure(value: str) -> Task163FailureCode | None:
        byte_count = 0
        try:
            for character in value:
                byte_count += len(character.encode("utf-8", "strict"))
                if byte_count >= TASK163_RAW_TEXT_BYTE_COUNT_LIMIT_PLUS_ONE:
                    return Task163FailureCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED
        except UnicodeError:
            return Task163FailureCode.RAW_UNICODE_ENCODING_FAILURE
        return None

    @staticmethod
    def _text_sort_key(value: str) -> tuple[int, bytes | tuple[int, ...]]:
        try:
            return 0, value.encode("utf-8", "strict")
        except UnicodeError:
            return 1, tuple(ord(character) for character in value)

    def _text(self, field_name: str, value: str) -> Task163RawProjectionNode:
        return self._normal(field_name, Task163RawProjectionKind.STRING, scalar=value)

    def _normal(
        self,
        field_name: str,
        kind: Task163RawProjectionKind,
        *,
        scalar: str | None = None,
        children: tuple[Task163RawProjectionNode, ...] = (),
    ) -> Task163RawProjectionNode:
        if type(field_name) is not str:
            return self._marker(Task163FailureCode.RAW_UNICODE_ENCODING_FAILURE)
        field_failure = self._text_failure(field_name)
        if field_failure is not None:
            return self._marker(field_failure)
        if scalar is not None:
            scalar_failure = self._text_failure(scalar)
            if scalar_failure is not None:
                return self._marker(scalar_failure)
        if self.nodes >= TASK163_RAW_MAX_NODES:
            return self._marker(Task163FailureCode.RAW_NODE_LIMIT_EXCEEDED)
        self.nodes += 1
        return Task163RawProjectionNode(
            field_name=field_name,
            kind=kind,
            type_identity=None,
            scalar_payload=scalar,
            children=children,
        )

    def _scalar(self, field_name: str, value: object) -> Task163RawProjectionNode | None:
        if value is None:
            return self._normal(field_name, Task163RawProjectionKind.NONE)
        if type(value) is bool:
            return self._normal(
                field_name,
                Task163RawProjectionKind.BOOLEAN,
                scalar="true" if value else "false",
            )
        if type(value) is int:
            return self._normal(field_name, Task163RawProjectionKind.INTEGER, scalar=str(value))
        if type(value) is Decimal:
            if not value.is_finite():
                self._reason(Task163FailureCode.UNSUPPORTED_RAW_VALUE)
                return self._marker(Task163FailureCode.UNSUPPORTED_RAW_VALUE)
            return self._normal(field_name, Task163RawProjectionKind.DECIMAL, scalar=str(value))
        if type(value) is str:
            return self._text(field_name, value)
        enum_types = _trusted_enum_types()
        if type(value) in enum_types:
            enum_value = cast(Enum, value).value
            if type(enum_value) is not str:
                return self._marker(Task163FailureCode.UNSUPPORTED_RAW_VALUE)
            return self._normal(
                field_name,
                Task163RawProjectionKind.ENUM_LITERAL,
                scalar=enum_value,
            )
        return None

    def _identity(
        self,
        field_name: str,
        kind: Task163RawProjectionKind,
        value: object,
        fields: tuple[str, ...],
        values: tuple[str, ...],
    ) -> Task163RawProjectionNode:
        children = tuple(self._text(name, item) for name, item in zip(fields, values, strict=True))
        return self._normal(field_name, kind, children=children)

    def _task160(self, field_name: str, value: Task160Result) -> Task163RawProjectionNode:
        identity = task160_result_identity_projection(value)
        return self._identity(
            field_name,
            Task163RawProjectionKind.TASK160_RESULT_IDENTITY,
            value,
            (
                "schema_version",
                "task160_version",
                "request_hash",
                "result_hash",
                "result_id",
                "provenance_hash",
            ),
            (
                identity.schema_version,
                identity.task160_version,
                identity.request_hash,
                identity.result_hash,
                identity.result_id,
                identity.provenance_hash,
            ),
        )

    def _task161(self, field_name: str, value: object) -> Task163RawProjectionNode:
        identity = task161_result_identity_projection(value)
        return self._identity(
            field_name,
            Task163RawProjectionKind.TASK161_RESULT_IDENTITY,
            value,
            (
                "schema_version",
                "task161_version",
                "source_definition_id",
                "request_hash",
                "result_hash",
                "result_id",
                "provenance_hash",
            ),
            (
                identity.schema_version,
                identity.task161_version,
                identity.source_definition_id,
                identity.request_hash,
                identity.result_hash,
                identity.result_id,
                identity.provenance_hash,
            ),
        )

    def _task038(self, field_name: str, value: object) -> Task163RawProjectionNode:
        identity = task038_result_identity_projection(value)
        return self._identity(
            field_name,
            Task163RawProjectionKind.TASK038_RESULT_IDENTITY,
            value,
            (
                "schema_version",
                "task038_version",
                "profile_id",
                "request_hash",
                "result_hash",
                "result_id",
                "provenance_hash",
            ),
            (
                identity.schema_version,
                identity.task038_version,
                identity.profile_id,
                identity.request_hash,
                identity.result_hash,
                identity.result_id,
                identity.provenance_hash,
            ),
        )

    def _task162(self, field_name: str, value: Task162Result) -> Task163RawProjectionNode:
        identity = task162_result_identity_projection(value)
        return self._identity(
            field_name,
            Task163RawProjectionKind.TASK162_RESULT_IDENTITY,
            value,
            (
                "schema_version",
                "task162_version",
                "implementation_software_version",
                "source_definition_id",
                "request_hash",
                "result_hash",
                "result_id",
                "provenance_hash",
            ),
            (
                identity.schema_version,
                identity.task162_version,
                identity.implementation_software_version,
                identity.source_definition_id,
                identity.request_hash,
                identity.result_hash,
                identity.result_id,
                identity.provenance_hash,
            ),
        )

    def _case(self, field_name: str, value: Task162CaseAuthority) -> Task163RawProjectionNode:
        fields = (
            "case_authority_id",
            "shell_type",
            "overall_flow_orientation",
            "baffle_count",
            "physical_sthe_tube_side_mixing",
            "physical_sthe_shell_side_mixing_model",
            "steady_state",
            "ambient_heat_loss_assumption",
            "internal_source_sink_assumption",
            "constant_wall_material_property",
            "constant_heat_transfer_coefficient",
            "axial_heat_transfer_assumption",
            "leakage_model_assumption",
            "bypass_model_assumption",
            "evidence_refs",
        )
        child_nodes: list[Task163RawProjectionNode] = []
        for name in fields:
            item = getattr(value, name)
            if name == "evidence_refs":
                ordered_refs = tuple(sorted(item, key=self._text_sort_key))
                child_nodes.append(self._sequence(name, ordered_refs, 1))
            else:
                child_nodes.append(self._project(name, item, 1))
        return self._normal(
            field_name,
            Task163RawProjectionKind.CASE_AUTHORITY_IDENTITY,
            children=tuple(child_nodes),
        )

    def _binding(
        self, field_name: str, value: Task162CrossProducerBindingAuthority
    ) -> Task163RawProjectionNode:
        fields = (
            "binding_authority_id",
            "task160_result_hash",
            "task160_result_id",
            "task161_result_hash",
            "task161_result_id",
            "task038_result_hash",
            "task038_result_id",
            "physical_exchanger_case_id",
            "binding_status",
            "evidence_refs",
        )
        children: list[Task163RawProjectionNode] = []
        for name in fields:
            item = getattr(value, name)
            if name == "evidence_refs":
                item = tuple(sorted(item, key=self._text_sort_key))
            children.append(self._project(name, item, 1))

        dimension_order = {
            dimension: index for index, dimension in enumerate(Task162CompatibilityDimension)
        }
        compatibility = sorted(
            value.compatibility_evidence,
            key=lambda item: dimension_order[item.dimension],
        )
        compatibility_children: list[Task163RawProjectionNode] = []
        for index, item in enumerate(compatibility):
            record_children = (
                self._project("dimension", item.dimension, 2),
                self._project("status", item.status, 2),
                self._project(
                    "evidence_refs",
                    tuple(sorted(item.evidence_refs, key=self._text_sort_key)),
                    2,
                ),
                self._project("failure_code_or_none", item.failure_code_or_none, 2),
            )
            compatibility_children.append(
                self._normal(
                    f"compatibility-{index:02d}",
                    Task163RawProjectionKind.RECORD,
                    children=record_children,
                )
            )
        children.append(
            self._normal(
                "compatibility_evidence",
                Task163RawProjectionKind.SEQUENCE,
                children=tuple(compatibility_children),
            )
        )
        return self._normal(
            field_name,
            Task163RawProjectionKind.RECORD,
            children=tuple(children),
        )

    def _replay_evidence(
        self, field_name: str, value: Task162SuccessReplayEvidence
    ) -> Task163RawProjectionNode:
        identity = task162_success_replay_evidence_identity_projection(value)
        children: list[Task163RawProjectionNode] = []
        for name in (
            "evidence_schema_version",
            "task162_schema_version",
            "task162_version",
            "task162_implementation_software_version",
            "task162_source_definition_id",
            "task162_result_hash",
            "task162_result_id",
        ):
            children.append(self._text(name, getattr(identity, name)))
        children.append(self._task160("original_task160_result", value.original_task160_result))
        children.append(self._task161("original_task161_result", value.original_task161_result))
        children.append(
            self._task038("original_task038_success_result", value.original_task038_success_result)
        )
        children.append(self._case("original_case_authority", value.original_case_authority))
        children.append(
            self._metadata_sequence(
                "original_task162_request_metadata", identity.original_task162_request_metadata, 1
            )
        )
        return self._normal(
            field_name,
            Task163RawProjectionKind.TASK162_REPLAY_EVIDENCE_IDENTITY,
            children=tuple(children),
        )

    def _metadata_sequence(
        self, field_name: str, value: object, depth: int
    ) -> Task163RawProjectionNode:
        if type(value) is not tuple:
            return self._marker(Task163FailureCode.INVALID_REQUEST_SCHEMA)
        items: list[Task163RawProjectionNode] = []
        valid_items: list[tuple[str, str]] = []
        invalid_items = 0
        for item in value:
            if (
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not str
                or type(item[1]) is not str
            ):
                invalid_items += 1
                continue
            valid_items.append((item[0], item[1]))
        for _ in range(invalid_items):
            items.append(self._marker(Task163FailureCode.INVALID_REQUEST_SCHEMA))
        valid_items.sort(
            key=lambda item: (self._text_sort_key(item[0]), self._text_sort_key(item[1]))
        )
        for index, (item_key, item_value) in enumerate(valid_items, start=invalid_items):
            key = self._text("key", item_key)
            val = self._text("value", item_value)
            items.append(
                self._normal(
                    f"item-{index:06d}", Task163RawProjectionKind.RECORD, children=(key, val)
                )
            )
        return self._normal(field_name, Task163RawProjectionKind.SEQUENCE, children=tuple(items))

    def _sequence(self, field_name: str, value: object, depth: int) -> Task163RawProjectionNode:
        if depth > TASK163_RAW_MAX_DEPTH:
            return self._marker(Task163FailureCode.RAW_DEPTH_LIMIT_EXCEEDED)
        if type(value) not in (tuple, list):
            return self._marker(Task163FailureCode.INVALID_REQUEST_SCHEMA)
        sequence_value = cast(tuple[object, ...] | list[object], value)
        children = tuple(
            self._project(f"item-{index:06d}", item, depth + 1)
            for index, item in enumerate(sequence_value)
        )
        return self._normal(field_name, Task163RawProjectionKind.SEQUENCE, children=children)

    def _mapping(self, field_name: str, value: object, depth: int) -> Task163RawProjectionNode:
        if depth > TASK163_RAW_MAX_DEPTH:
            return self._marker(Task163FailureCode.RAW_DEPTH_LIMIT_EXCEEDED)
        if type(value) is not dict:
            return self._marker(Task163FailureCode.INVALID_REQUEST_SCHEMA)
        children: list[Task163RawProjectionNode] = []
        for key, item in value.items():
            if type(key) is not str:
                if depth == 0:
                    self._reason(Task163FailureCode.INVALID_REQUEST_SCHEMA)
                    children.append(
                        self._normal(
                            "__TASK163_INVALID_FIELD__",
                            Task163RawProjectionKind.UNSUPPORTED_OBJECT,
                        )
                    )
                else:
                    children.append(self._marker(Task163FailureCode.UNSUPPORTED_RAW_VALUE))
            else:
                children.append(self._project(key, item, depth + 1))
        return self._normal(field_name, Task163RawProjectionKind.RECORD, children=tuple(children))

    def _validate_root_schema(self, value: dict[object, object]) -> None:
        expected = (
            "request_metadata",
            "schema_version",
            "source_definition_id",
            "task162_result",
            "task162_success_replay_evidence",
            "task163_version",
        )
        keys = tuple(value.keys())
        invalid_schema = any(type(key) is not str for key in keys)
        if not invalid_schema:
            invalid_schema = tuple(sorted(cast(tuple[str, ...], keys))) != expected
        if invalid_schema:
            self._reason(Task163FailureCode.INVALID_REQUEST_SCHEMA)

        schema = value.get("schema_version")
        if type(schema) is not str or schema != TASK163_SCHEMA_VERSION:
            self._reason(Task163FailureCode.INVALID_REQUEST_SCHEMA)

        version = value.get("task163_version")
        if type(version) is not str:
            self._reason(Task163FailureCode.INVALID_REQUEST_SCHEMA)
        elif version != TASK163_VERSION:
            self._reason(Task163FailureCode.UNSUPPORTED_TASK163_VERSION)

        source_definition_id = value.get("source_definition_id")
        if type(source_definition_id) is not str:
            self._reason(Task163FailureCode.INVALID_REQUEST_SCHEMA)
        elif source_definition_id != TASK163_SOURCE_DEFINITION_ID:
            self._reason(Task163FailureCode.SOURCE_DEFINITION_ID_MISMATCH)

    def _invalid_top_level(self, value: object) -> Task163RawProjectionNode:
        type_identity: str | None = None
        try:
            python_type = type(value)
            module = type.__getattribute__(python_type, "__module__")
            qualname = type.__getattribute__(python_type, "__qualname__")
            if type(module) is str and type(qualname) is str:
                candidate = module + "." + qualname
                if self._text_failure(candidate) is None:
                    type_identity = candidate
        except BaseException:
            type_identity = None
        if self.nodes >= TASK163_RAW_MAX_NODES:
            return self._marker(Task163FailureCode.RAW_NODE_LIMIT_EXCEEDED)
        self.nodes += 1
        return Task163RawProjectionNode(
            field_name="root",
            kind=Task163RawProjectionKind.UNSUPPORTED_OBJECT,
            type_identity=type_identity,
            scalar_payload=None,
            children=(),
        )

    def _unsupported(self, field_name: str, value: object) -> Task163RawProjectionNode:
        self._reason(Task163FailureCode.UNSUPPORTED_RAW_VALUE)
        field_failure = self._text_failure(field_name)
        if field_failure is not None:
            return self._marker(field_failure)
        try:
            python_type = type(value)
            module = type.__getattribute__(python_type, "__module__")
            qualname = type.__getattribute__(python_type, "__qualname__")
            if type(module) is not str or type(qualname) is not str:
                raise ValueError("invalid type metadata")
            identity = f"{module}.{qualname}"
            failure = self._text_failure(identity)
            if failure is not None:
                return self._marker(failure)
        except BaseException:
            return self._marker(Task163FailureCode.UNSUPPORTED_RAW_VALUE)
        if self.nodes >= TASK163_RAW_MAX_NODES:
            return self._marker(Task163FailureCode.RAW_NODE_LIMIT_EXCEEDED)
        self.nodes += 1
        return Task163RawProjectionNode(
            field_name=field_name,
            kind=Task163RawProjectionKind.UNSUPPORTED_OBJECT,
            type_identity=identity,
            scalar_payload=None,
            children=(),
        )

    def _project(self, field_name: str, value: object, depth: int) -> Task163RawProjectionNode:
        if depth > TASK163_RAW_MAX_DEPTH:
            return self._marker(Task163FailureCode.RAW_DEPTH_LIMIT_EXCEEDED)
        scalar = self._scalar(field_name, value)
        if scalar is not None:
            return scalar
        try:
            if type(value) is Task160Result:
                return self._task160(field_name, value)
            if type(value) is Task162Result:
                return self._task162(field_name, value)
            if type(value) is Task162SuccessReplayEvidence:
                return self._replay_evidence(field_name, value)
            if type(value) is Task038SuccessResult:
                return self._task038(field_name, value)
            if type(value) is Task161Result:
                return self._task161(field_name, value)
            if type(value) is Task162CrossProducerBindingAuthority:
                return self._binding(field_name, value)
            if type(value) is Task162CaseAuthority:
                return self._case(field_name, value)
            if type(value) is dict:
                return self._mapping(field_name, value, depth)
            if type(value) in (tuple, list):
                return self._sequence(field_name, value, depth)
            return self._unsupported(field_name, value)
        except BaseException:
            return self._marker(Task163FailureCode.UNSUPPORTED_RAW_VALUE)

    def project(self, raw: object) -> RawProjectionOutcome:
        if type(raw) is not dict:
            self._reason(Task163FailureCode.INVALID_REQUEST_TYPE)
            root = self._invalid_top_level(raw)
        else:
            self._validate_root_schema(raw)
            root = self._mapping("root", raw, 0)
        return RawProjectionOutcome(
            projection=Task163RawRequestProjection(
                schema_version=TASK163_RAW_PROJECTION_SCHEMA_VERSION,
                root=root,
            ),
            reasons=tuple(self.reasons),
        )


def project_raw_request_with_diagnostics(raw: object) -> RawProjectionOutcome:
    try:
        return _Walker().project(raw)
    except BaseException:
        marker = Task163RawProjectionNode(
            field_name="__TASK163_LIMIT_MARKER__",
            kind=Task163RawProjectionKind.LIMIT_MARKER,
            type_identity=None,
            scalar_payload=Task163FailureCode.UNSUPPORTED_RAW_VALUE.value,
            children=(),
        )
        return RawProjectionOutcome(
            projection=Task163RawRequestProjection(
                schema_version=TASK163_RAW_PROJECTION_SCHEMA_VERSION,
                root=marker,
            ),
            reasons=(Task163FailureCode.UNSUPPORTED_RAW_VALUE,),
        )


def project_raw_request(raw: object) -> Task163RawRequestProjection:
    return project_raw_request_with_diagnostics(raw).projection


__all__ = [
    "RawProjectionOutcome",
    "project_raw_request",
    "project_raw_request_with_diagnostics",
]
