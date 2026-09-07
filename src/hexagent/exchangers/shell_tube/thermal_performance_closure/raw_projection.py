"""Total, bounded raw ingress projection for TASK162."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, cast
from uuid import UUID

from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority.models import (
    Task161Provenance,
    Task161Result,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
    Task038Provenance,
    Task038SuccessResult,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.models import (
    Task160Provenance,
    Task160Result,
)

from .canonical import TASK162_COMPATIBILITY_DIMENSION_ORDER, raw_projection_node_bytes
from .models import (
    TASK162_RAW_MAX_DEPTH,
    TASK162_RAW_MAX_NODES,
    TASK162_RAW_MAX_SCALAR_BYTES,
    TASK162_RAW_PROJECTION_SCHEMA_VERSION,
    Task162CaseAuthority,
    Task162CrossProducerBindingAuthority,
    Task162RawProjectionKind,
    Task162RawProjectionNode,
    Task162RawRequestProjection,
)

LIMIT_MARKER_FIELD_NAME = "__TASK162_LIMIT_MARKER__"
LIMIT_MARKER_REASONS = (
    "DEPTH_LIMIT_EXCEEDED",
    "NODE_LIMIT_EXCEEDED",
    "SCALAR_BYTE_LIMIT_EXCEEDED",
    "UNICODE_ENCODING_FAILURE",
    "TYPE_IDENTITY_UNAVAILABLE",
)

_RAW_FIELDS = (
    "schema_version",
    "task162_version",
    "source_definition_id",
    "task160_result",
    "task161_result",
    "task038_result",
    "cross_producer_binding_authority",
    "case_authority",
    "request_metadata",
)


class _ProjectionBuilder:
    def __init__(self) -> None:
        self.normal_nodes = 0
        self.unsupported_object_seen = False
        self.marker_reasons: set[str] = set()

    def marker(self, reason: str) -> Task162RawProjectionNode:
        self.marker_reasons.add(reason)
        return Task162RawProjectionNode(
            field_name=LIMIT_MARKER_FIELD_NAME,
            kind=Task162RawProjectionKind.LIMIT_MARKER,
            type_identity=None,
            scalar_payload=reason,
            children=(),
        )

    @staticmethod
    def _text_bytes(value: str) -> tuple[bytes | None, str | None]:
        """Count strict UTF-8 incrementally and stop at limit plus one."""

        total = 0
        for character in value:
            try:
                encoded = character.encode("utf-8", "strict")
            except UnicodeError:
                return None, "UNICODE_ENCODING_FAILURE"
            total += len(encoded)
            if total >= TASK162_RAW_MAX_SCALAR_BYTES + 1:
                return None, "SCALAR_BYTE_LIMIT_EXCEEDED"
        return value.encode("utf-8", "strict"), None

    @staticmethod
    def _sort_text(value: str) -> tuple[int, bytes]:
        """Return a bounded deterministic ordering key for textual slots."""

        encoded_prefix = bytearray()
        for character in value:
            try:
                encoded = character.encode("utf-8", "strict")
            except UnicodeError:
                return (1, b"")
            encoded_prefix.extend(encoded)
            if len(encoded_prefix) >= TASK162_RAW_MAX_SCALAR_BYTES + 1:
                return (2, bytes(encoded_prefix))
        return (0, bytes(encoded_prefix))

    def _normal(
        self,
        field_name: str,
        kind: Task162RawProjectionKind,
        *,
        type_identity: str | None = None,
        scalar_payload: str | None = None,
        children: tuple[Task162RawProjectionNode, ...] = (),
        depth: int,
    ) -> Task162RawProjectionNode:
        marker = self._reserve(
            field_name,
            kind,
            type_identity=type_identity,
            scalar_payload=scalar_payload,
            depth=depth,
        )
        if marker is not None:
            return marker
        return Task162RawProjectionNode(
            field_name=field_name,
            kind=kind,
            type_identity=type_identity,
            scalar_payload=scalar_payload,
            children=children,
        )

    def _reserve(
        self,
        field_name: str,
        kind: Task162RawProjectionKind,
        *,
        type_identity: str | None = None,
        scalar_payload: str | None = None,
        depth: int,
    ) -> Task162RawProjectionNode | None:
        """Reserve a normal node before expanding its descendants."""

        if depth > TASK162_RAW_MAX_DEPTH:
            return self.marker("DEPTH_LIMIT_EXCEEDED")
        if self.normal_nodes >= TASK162_RAW_MAX_NODES:
            return self.marker("NODE_LIMIT_EXCEEDED")

        _, field_reason = self._text_bytes(field_name)
        if field_reason is not None:
            return self.marker(field_reason)
        if type_identity is not None:
            _, type_reason = self._text_bytes(type_identity)
            if type_reason is not None:
                return self.marker(type_reason)
        if scalar_payload is not None:
            _, scalar_reason = self._text_bytes(scalar_payload)
            if scalar_reason is not None:
                return self.marker(scalar_reason)

        self.normal_nodes += 1
        return None

    def _safe_type_identity(self, value: object) -> tuple[str | None, str | None]:
        try:
            python_type = type(value)
            module = type.__getattribute__(python_type, "__module__")
            qualname = type.__getattribute__(python_type, "__qualname__")
        except BaseException:
            return None, "TYPE_IDENTITY_UNAVAILABLE"
        if type(module) is not str or type(qualname) is not str:
            return None, "TYPE_IDENTITY_UNAVAILABLE"
        return module + "." + qualname, None

    @staticmethod
    def _safe_uuid_text(value: object) -> object:
        if type(value) is UUID:
            return str(value).lower()
        return value

    @staticmethod
    def _safe_provenance_hash(value: object, provenance_type: type[object]) -> object:
        provenance = cast(Any, value).provenance  # callers pass exact upstream result types
        if type(provenance) is provenance_type:
            return cast(Any, provenance).provenance_hash
        return provenance

    def _canonical_record_children(
        self, children: tuple[Task162RawProjectionNode, ...]
    ) -> tuple[Task162RawProjectionNode, ...]:
        """Apply the complete record key, including the projected-node tie-breaker."""

        return tuple(
            sorted(
                children,
                key=lambda item: (
                    self._sort_text(item.field_name),
                    raw_projection_node_bytes(item),
                ),
            )
        )

    def _scalar(self, field_name: str, value: object, depth: int) -> Task162RawProjectionNode:
        if value is None:
            return self._normal(field_name, Task162RawProjectionKind.NONE, depth=depth)
        if type(value) is bool:
            return self._normal(
                field_name,
                Task162RawProjectionKind.BOOLEAN,
                scalar_payload="true" if value else "false",
                depth=depth,
            )
        if type(value) is int:
            try:
                scalar_payload = str(value)
            except (ValueError, OverflowError):
                return self.marker("SCALAR_BYTE_LIMIT_EXCEEDED")
            return self._normal(
                field_name,
                Task162RawProjectionKind.INTEGER,
                scalar_payload=scalar_payload,
                depth=depth,
            )
        if type(value) is Decimal:
            try:
                scalar_payload = str(value)
            except (ValueError, OverflowError):
                return self.marker("SCALAR_BYTE_LIMIT_EXCEEDED")
            return self._normal(
                field_name,
                Task162RawProjectionKind.DECIMAL,
                scalar_payload=scalar_payload,
                depth=depth,
            )
        if type(value) is str:
            return self._normal(
                field_name,
                Task162RawProjectionKind.STRING,
                scalar_payload=value,
                depth=depth,
            )
        if isinstance(value, Enum):
            try:
                literal = value.value
            except BaseException:
                return self.marker("TYPE_IDENTITY_UNAVAILABLE")
            if type(literal) is not str:
                return self.marker("TYPE_IDENTITY_UNAVAILABLE")
            return self._normal(
                field_name,
                Task162RawProjectionKind.ENUM_LITERAL,
                scalar_payload=literal,
                depth=depth,
            )
        return self.node(field_name, value, depth)

    def _identity_children(
        self, values: tuple[tuple[str, object], ...], depth: int
    ) -> tuple[Task162RawProjectionNode, ...]:
        return tuple(self._scalar(name, value, depth + 1) for name, value in values)

    def _identity_node(
        self,
        field_name: str,
        kind: Task162RawProjectionKind,
        values: tuple[tuple[str, object], ...],
        depth: int,
    ) -> Task162RawProjectionNode:
        marker = self._reserve(field_name, kind, depth=depth)
        if marker is not None:
            return marker
        return Task162RawProjectionNode(
            field_name=field_name,
            kind=kind,
            type_identity=None,
            scalar_payload=None,
            children=self._identity_children(values, depth),
        )

    def _binding_node(
        self, field_name: str, value: Task162CrossProducerBindingAuthority, depth: int
    ) -> Task162RawProjectionNode:
        marker = self._reserve(
            field_name, Task162RawProjectionKind.CROSS_PRODUCER_BINDING_IDENTITY, depth=depth
        )
        if marker is not None:
            return marker
        dimension_order = {
            dimension: index
            for index, dimension in enumerate(TASK162_COMPATIBILITY_DIMENSION_ORDER)
        }
        compatibility = sorted(
            value.compatibility_evidence,
            key=lambda item: (
                dimension_order.get(item.dimension, len(dimension_order)),
                item.dimension.value,
            ),
        )
        values: tuple[tuple[str, object], ...] = (
            ("binding_authority_id", value.binding_authority_id),
            ("task160_result_hash", value.task160_result_hash),
            ("task160_result_id", value.task160_result_id),
            ("task161_result_hash", value.task161_result_hash),
            ("task161_result_id", value.task161_result_id),
            ("task038_result_hash", value.task038_result_hash),
            ("task038_result_id", value.task038_result_id),
            ("physical_exchanger_case_id", value.physical_exchanger_case_id),
            ("binding_status", value.binding_status),
            ("evidence_refs", tuple(sorted(value.evidence_refs, key=self._sort_text))),
        )
        children = self._identity_children(values, depth)
        compatibility_marker = self._reserve(
            "compatibility_evidence",
            Task162RawProjectionKind.SEQUENCE,
            depth=depth + 1,
        )
        if compatibility_marker is not None:
            children += (compatibility_marker,)
        else:
            compatibility_children: list[Task162RawProjectionNode] = []
            for index, item in enumerate(compatibility):
                record_name = f"compatibility-{index:02d}"
                record_marker = self._reserve(
                    record_name, Task162RawProjectionKind.RECORD, depth=depth + 1
                )
                if record_marker is not None:
                    compatibility_children.append(record_marker)
                    continue
                evidence = tuple(sorted(item.evidence_refs, key=self._sort_text))
                record = (
                    ("dimension", item.dimension),
                    ("status", item.status),
                    ("evidence_refs", tuple(evidence)),
                    ("failure_code_or_none", item.failure_code_or_none),
                )
                compatibility_children.append(
                    Task162RawProjectionNode(
                        field_name=record_name,
                        kind=Task162RawProjectionKind.RECORD,
                        type_identity=None,
                        scalar_payload=None,
                        children=self._binding_record_children(record, depth + 2),
                    )
                )
            children += (
                Task162RawProjectionNode(
                    field_name="compatibility_evidence",
                    kind=Task162RawProjectionKind.SEQUENCE,
                    type_identity=None,
                    scalar_payload=None,
                    children=tuple(compatibility_children),
                ),
            )
        return Task162RawProjectionNode(
            field_name=field_name,
            kind=Task162RawProjectionKind.CROSS_PRODUCER_BINDING_IDENTITY,
            type_identity=None,
            scalar_payload=None,
            children=children,
        )

    def _binding_record_children(
        self, values: tuple[tuple[str, object], ...], depth: int
    ) -> tuple[Task162RawProjectionNode, ...]:
        output: list[Task162RawProjectionNode] = []
        for name, value in values:
            if name == "evidence_refs":
                refs = value if type(value) is tuple else ()
                marker = self._reserve(name, Task162RawProjectionKind.SEQUENCE, depth=depth)
                if marker is not None:
                    output.append(marker)
                else:
                    output.append(
                        Task162RawProjectionNode(
                            field_name=name,
                            kind=Task162RawProjectionKind.SEQUENCE,
                            type_identity=None,
                            scalar_payload=None,
                            children=tuple(
                                self._scalar(f"item-{index:06d}", item, depth + 1)
                                for index, item in enumerate(refs)
                            ),
                        )
                    )
            else:
                output.append(self._scalar(name, value, depth))
        return tuple(output)

    def _case_node(
        self, field_name: str, value: Task162CaseAuthority, depth: int
    ) -> Task162RawProjectionNode:
        marker = self._reserve(
            field_name, Task162RawProjectionKind.CASE_AUTHORITY_IDENTITY, depth=depth
        )
        if marker is not None:
            return marker
        values: tuple[tuple[str, object], ...] = (
            ("case_authority_id", value.case_authority_id),
            ("shell_type", value.shell_type),
            ("overall_flow_orientation", value.overall_flow_orientation),
            ("baffle_count", value.baffle_count),
            ("physical_sthe_tube_side_mixing", value.physical_sthe_tube_side_mixing),
            ("physical_sthe_shell_side_mixing_model", value.physical_sthe_shell_side_mixing_model),
            ("steady_state", value.steady_state),
            ("ambient_heat_loss_assumption", value.ambient_heat_loss_assumption),
            ("internal_source_sink_assumption", value.internal_source_sink_assumption),
            ("constant_wall_material_property", value.constant_wall_material_property),
            ("constant_heat_transfer_coefficient", value.constant_heat_transfer_coefficient),
            ("axial_heat_transfer_assumption", value.axial_heat_transfer_assumption),
            ("leakage_model_assumption", value.leakage_model_assumption),
            ("bypass_model_assumption", value.bypass_model_assumption),
            ("evidence_refs", tuple(sorted(value.evidence_refs, key=self._sort_text))),
        )
        children: list[Task162RawProjectionNode] = []
        for name, item in values:
            if name == "evidence_refs":
                refs = cast(tuple[str, ...], item)
                sequence_marker = self._reserve(
                    name, Task162RawProjectionKind.SEQUENCE, depth=depth + 1
                )
                if sequence_marker is not None:
                    children.append(sequence_marker)
                else:
                    children.append(
                        Task162RawProjectionNode(
                            field_name=name,
                            kind=Task162RawProjectionKind.SEQUENCE,
                            type_identity=None,
                            scalar_payload=None,
                            children=tuple(
                                self._scalar(f"item-{index:06d}", ref, depth + 2)
                                for index, ref in enumerate(refs)
                            ),
                        )
                    )
            else:
                children.append(self._scalar(name, item, depth + 1))
        return Task162RawProjectionNode(
            field_name=field_name,
            kind=Task162RawProjectionKind.CASE_AUTHORITY_IDENTITY,
            type_identity=None,
            scalar_payload=None,
            children=tuple(children),
        )

    def _unsupported_mapping_key_node(
        self, key: object, value: object, depth: int
    ) -> Task162RawProjectionNode:
        field_name = "__TASK162_UNSUPPORTED_KEY__"
        marker = self._reserve(field_name, Task162RawProjectionKind.RECORD, depth=depth)
        if marker is not None:
            return marker
        return Task162RawProjectionNode(
            field_name=field_name,
            kind=Task162RawProjectionKind.RECORD,
            type_identity=None,
            scalar_payload=None,
            children=(
                self._scalar("key", key, depth + 1),
                self._scalar("value", value, depth + 1),
            ),
        )

    def _mapping_children(
        self, value: dict[object, object], depth: int
    ) -> tuple[Task162RawProjectionNode, ...]:
        children: list[Task162RawProjectionNode] = []
        for key, item in value.items():
            if type(key) is str:
                children.append(self._scalar(key, item, depth + 1))
            else:
                children.append(self._unsupported_mapping_key_node(key, item, depth + 1))
        return self._canonical_record_children(tuple(children))

    def node(self, field_name: str, value: object, depth: int) -> Task162RawProjectionNode:
        if type(value) is Task160Result:
            return self._identity_node(
                field_name,
                Task162RawProjectionKind.TASK160_RESULT_IDENTITY,
                (
                    ("schema_version", value.schema_version),
                    ("task160_version", value.task160_version),
                    ("request_hash", value.request_hash),
                    ("result_hash", value.result_hash),
                    ("result_id", self._safe_uuid_text(value.result_id)),
                    (
                        "provenance_hash",
                        self._safe_provenance_hash(value, Task160Provenance),
                    ),
                ),
                depth,
            )
        if type(value) is Task161Result:
            return self._identity_node(
                field_name,
                Task162RawProjectionKind.TASK161_RESULT_IDENTITY,
                (
                    ("schema_version", value.schema_version),
                    ("task161_version", value.task161_version),
                    ("source_definition_id", value.source_definition_id),
                    ("request_hash", value.request_hash),
                    ("result_hash", value.result_hash),
                    ("result_id", self._safe_uuid_text(value.result_id)),
                    (
                        "provenance_hash",
                        self._safe_provenance_hash(value, Task161Provenance),
                    ),
                ),
                depth,
            )
        if type(value) is Task038SuccessResult:
            return self._identity_node(
                field_name,
                Task162RawProjectionKind.TASK038_RESULT_IDENTITY,
                (
                    ("schema_version", value.schema_version),
                    ("task038_version", value.task038_version),
                    ("profile_id", value.profile_id),
                    ("request_hash", value.request_hash),
                    ("result_hash", value.result_hash),
                    ("result_id", self._safe_uuid_text(value.result_id)),
                    (
                        "provenance_hash",
                        self._safe_provenance_hash(value, Task038Provenance),
                    ),
                ),
                depth,
            )
        if type(value) is Task162CrossProducerBindingAuthority:
            return self._binding_node(field_name, value, depth)
        if type(value) is Task162CaseAuthority:
            return self._case_node(field_name, value, depth)
        if type(value) is tuple or type(value) is list:
            marker = self._reserve(field_name, Task162RawProjectionKind.SEQUENCE, depth=depth)
            if marker is not None:
                return marker
            children = tuple(
                self._scalar(f"item-{index:06d}", item, depth + 1)
                for index, item in enumerate(value)
            )
            return Task162RawProjectionNode(
                field_name=field_name,
                kind=Task162RawProjectionKind.SEQUENCE,
                type_identity=None,
                scalar_payload=None,
                children=children,
            )
        if type(value) is dict:
            marker = self._reserve(field_name, Task162RawProjectionKind.RECORD, depth=depth)
            if marker is not None:
                return marker
            children = self._mapping_children(value, depth)
            return Task162RawProjectionNode(
                field_name=field_name,
                kind=Task162RawProjectionKind.RECORD,
                type_identity=None,
                scalar_payload=None,
                children=children,
            )

        type_identity, reason = self._safe_type_identity(value)
        if reason is not None or type_identity is None:
            return self.marker("TYPE_IDENTITY_UNAVAILABLE")
        self.unsupported_object_seen = True
        return self._normal(
            field_name,
            Task162RawProjectionKind.UNSUPPORTED_OBJECT,
            type_identity=type_identity,
            depth=depth,
        )

    def project(self, raw: object) -> Task162RawRequestProjection:
        if type(raw) is dict:
            marker = self._reserve("root", Task162RawProjectionKind.RECORD, depth=0)
            if marker is not None:
                root = marker
            else:
                children = self._mapping_children(raw, 0)
                root = Task162RawProjectionNode(
                    field_name="root",
                    kind=Task162RawProjectionKind.RECORD,
                    type_identity=None,
                    scalar_payload=None,
                    children=children,
                )
        else:
            root = self._scalar("root", raw, 0)
        return Task162RawRequestProjection(
            schema_version=TASK162_RAW_PROJECTION_SCHEMA_VERSION,
            root=root,
        )


@dataclass(frozen=True, slots=True)
class RawProjectionOutcome:
    projection: Task162RawRequestProjection
    reasons: tuple[str, ...]
    unsupported_object_present: bool


def project_raw_request_with_diagnostics(raw: object) -> RawProjectionOutcome:
    """Return a projection and diagnostics; this function never raises."""

    builder = _ProjectionBuilder()
    try:
        projection = builder.project(raw)
    except BaseException:
        projection = Task162RawRequestProjection(
            schema_version=TASK162_RAW_PROJECTION_SCHEMA_VERSION,
            root=Task162RawProjectionNode(
                field_name=LIMIT_MARKER_FIELD_NAME,
                kind=Task162RawProjectionKind.LIMIT_MARKER,
                type_identity=None,
                scalar_payload="TYPE_IDENTITY_UNAVAILABLE",
                children=(),
            ),
        )
        return RawProjectionOutcome(
            projection=projection,
            reasons=("TYPE_IDENTITY_UNAVAILABLE",),
            unsupported_object_present=True,
        )
    unsupported = builder.unsupported_object_seen or bool(builder.marker_reasons)
    return RawProjectionOutcome(
        projection=projection,
        reasons=tuple(sorted(builder.marker_reasons)),
        unsupported_object_present=unsupported,
    )


def project_raw_request(raw: object) -> Task162RawRequestProjection:
    return project_raw_request_with_diagnostics(raw).projection


def iter_projection_nodes(value: Task162RawProjectionNode) -> Iterator[Task162RawProjectionNode]:
    yield value
    for child in value.children:
        yield from iter_projection_nodes(child)


__all__ = [
    "LIMIT_MARKER_FIELD_NAME",
    "LIMIT_MARKER_REASONS",
    "RawProjectionOutcome",
    "project_raw_request",
    "project_raw_request_with_diagnostics",
    "iter_projection_nodes",
]
