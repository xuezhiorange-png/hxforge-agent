"""Total, bounded, side-effect-free TASK164 raw ingress projection."""

from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal
from enum import Enum
from typing import Any, cast
from uuid import UUID

from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority.models import (
    Task161Result,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
    Task038SuccessResult,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure.models import (
    Task162Result,
    Task162SuccessReplayEvidence,
)
from hexagent.exchangers.shell_tube.thermal_rating_composition.models import (
    Task163Request,
    Task163ValidationResult,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.models import Task160Result

from .canonical import (
    task038_result_identity_bytes,
    task160_result_identity_bytes,
    task161_result_identity_bytes,
    task162_result_identity_bytes,
    task162_success_replay_evidence_identity_bytes,
    task163_request_projection_bytes,
    task163_validation_projection_bytes,
)
from .models import (
    TASK164_RAW_MAX_DEPTH,
    TASK164_RAW_MAX_NODES,
    TASK164_RAW_MAX_SCALAR_BYTES,
    TASK164_RAW_PROJECTION_SCHEMA_VERSION,
    TASK164_RAW_TEXT_BYTE_COUNT_LIMIT_PLUS_ONE,
    Task164AcceptanceCategory,
    Task164AcceptanceCategoryRecord,
    Task164AcceptanceCategoryStatus,
    Task164AcceptanceLedger,
    Task164AcceptanceLedgerStatus,
    Task164Applicability,
    Task164ApplicabilityCheck,
    Task164ApplicabilityRecord,
    Task164ApplicabilityStatus,
    Task164ArtifactRecord,
    Task164Blocker,
    Task164CaseBinding,
    Task164ClaimMatchStatus,
    Task164CommandIdentity,
    Task164Completeness,
    Task164CompletenessItem,
    Task164CompletenessStatus,
    Task164ConstructionFamily,
    Task164DeterminismEvidence,
    Task164DualRuntimeObservation,
    Task164EvidenceAuthority,
    Task164EvidencePackage,
    Task164EvidencePackageClaim,
    Task164EvidencePayload,
    Task164EvidencePayloadKind,
    Task164EvidenceStatus,
    Task164FailureCode,
    Task164FailureStage,
    Task164ForbiddenCapabilityToken,
    Task164MediaKind,
    Task164MethodAuthority,
    Task164PackageArtifactId,
    Task164PairingKey,
    Task164ParityStatus,
    Task164ParitySurface,
    Task164PostResultArtifactId,
    Task164PreResultIdentityInputs,
    Task164Provenance,
    Task164ProvenanceSemanticInputs,
    Task164PythonParityClaim,
    Task164PythonVersion,
    Task164RatingOutputAuthority,
    Task164RawProjectionKind,
    Task164RawProjectionNode,
    Task164RawRequestProjection,
    Task164RepeatRunClaim,
    Task164RepeatRunObservation,
    Task164RepeatRunSurface,
    Task164Request,
    Task164Result,
    Task164RunnerIdentity,
    Task164RuntimeObservation,
    Task164ScenarioClaim,
    Task164ScenarioClass,
    Task164ScenarioId,
    Task164ScenarioInputAuthority,
    Task164ScenarioObservation,
    Task164ScenarioOutcome,
    Task164ScenarioRecord,
    Task164ScenarioSetup,
    Task164ScopeFenceEvidence,
    Task164ScopeStatus,
    Task164SurfaceHashRecord,
    Task164TamperTarget,
    Task164Task163Branch,
    Task164Task163Evidence,
    Task164Task163ReplayEvidence,
    Task164TerminalCapability,
    Task164TerminalCapabilityId,
    Task164TypedBlockedResult,
    Task164ValidationBranch,
)


@dataclass(frozen=True, slots=True)
class RawProjectionOutcome:
    projection: Task164RawRequestProjection
    reasons: tuple[Task164FailureCode, ...]


_TRUSTED_ENUM_TYPES: frozenset[type[Enum]] = frozenset(
    {
        type(member)
        for enum_type in (
            Task164FailureCode,
            Task164FailureStage,
            Task164ValidationBranch,
            Task164Task163Branch,
            Task164ScenarioClass,
            Task164ScenarioOutcome,
            Task164TamperTarget,
            Task164ScenarioInputAuthority,
            Task164ScenarioId,
            Task164EvidenceAuthority,
            Task164EvidenceStatus,
            Task164AcceptanceCategoryStatus,
            Task164AcceptanceLedgerStatus,
            Task164ApplicabilityStatus,
            Task164CompletenessStatus,
            Task164ScopeStatus,
            Task164ClaimMatchStatus,
            Task164ParityStatus,
            Task164PythonVersion,
            Task164RunnerIdentity,
            Task164CommandIdentity,
            Task164PairingKey,
            Task164ConstructionFamily,
            Task164CaseBinding,
            Task164MethodAuthority,
            Task164RatingOutputAuthority,
            Task164TerminalCapabilityId,
            Task164ApplicabilityCheck,
            Task164RepeatRunSurface,
            Task164ParitySurface,
            Task164EvidencePayloadKind,
            Task164AcceptanceCategory,
            Task164PackageArtifactId,
            Task164PostResultArtifactId,
            Task164CompletenessItem,
            Task164MediaKind,
            Task164ForbiddenCapabilityToken,
        )
        for member in enum_type
    }
)


def _safe_type_identity(value: object) -> str | None:
    """Read only built-in type metadata; never inspect the value itself."""

    try:
        python_type = type(value)
        module = type.__getattribute__(python_type, "__module__")
        qualname = type.__getattribute__(python_type, "__qualname__")
        if type(module) is not str or type(qualname) is not str:
            return None
        module.encode("utf-8", "strict")
        qualname.encode("utf-8", "strict")
        return module + "." + qualname
    except BaseException:
        return None


class _Walker:
    def __init__(self) -> None:
        self.nodes = 0
        self.reasons: list[Task164FailureCode] = []

    def _remember(self, code: Task164FailureCode) -> None:
        if code not in self.reasons:
            self.reasons.append(code)

    def _marker(self, code: Task164FailureCode) -> Task164RawProjectionNode:
        self._remember(code)
        return Task164RawProjectionNode(
            field_name="__TASK164_LIMIT_MARKER__",
            kind=Task164RawProjectionKind.LIMIT_MARKER,
            type_identity=None,
            scalar_payload=code.value,
            children=(),
        )

    def _bounded_text(self, value: str) -> tuple[bytes | None, Task164FailureCode | None]:
        if type(value) is not str:
            return None, Task164FailureCode.UNSUPPORTED_RAW_VALUE
        # Incremental encoding is deliberate: an oversized value is never
        # materialized as one large UTF-8 buffer.
        try:
            encoder = "utf-8"
            count = 0
            chunks: list[bytes] = []
            for char in value:
                encoded = char.encode(encoder, "strict")
                count += len(encoded)
                if count >= TASK164_RAW_TEXT_BYTE_COUNT_LIMIT_PLUS_ONE:
                    return None, Task164FailureCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED
                chunks.append(encoded)
            return b"".join(chunks), None
        except UnicodeEncodeError:
            return None, Task164FailureCode.RAW_UNICODE_ENCODING_FAILURE
        except BaseException:
            return None, Task164FailureCode.UNSUPPORTED_RAW_VALUE

    def _field_name_ok(self, field_name: str) -> Task164RawProjectionNode | None:
        encoded, failure = self._bounded_text(field_name)
        if failure is not None:
            return self._marker(failure)
        if encoded is None:
            return self._marker(Task164FailureCode.UNSUPPORTED_RAW_VALUE)
        return None

    def _new_node(
        self,
        field_name: str,
        kind: Task164RawProjectionKind,
        type_identity: str | None,
        scalar_payload: str | None,
        children: tuple[Task164RawProjectionNode, ...],
        depth: int,
    ) -> Task164RawProjectionNode:
        field_failure = self._field_name_ok(field_name)
        if field_failure is not None:
            return field_failure
        if depth > TASK164_RAW_MAX_DEPTH:
            return self._marker(Task164FailureCode.RAW_DEPTH_LIMIT_EXCEEDED)
        if self.nodes >= TASK164_RAW_MAX_NODES:
            return self._marker(Task164FailureCode.RAW_NODE_LIMIT_EXCEEDED)
        self.nodes += 1
        try:
            return Task164RawProjectionNode(
                field_name=field_name,
                kind=kind,
                type_identity=type_identity,
                scalar_payload=scalar_payload,
                children=children,
            )
        except BaseException:
            return self._marker(Task164FailureCode.UNSUPPORTED_RAW_VALUE)

    def _text_scalar(
        self,
        field_name: str,
        value: str,
        kind: Task164RawProjectionKind,
        depth: int,
        *,
        type_identity: str | None = None,
    ) -> Task164RawProjectionNode:
        _, failure = self._bounded_text(value)
        if failure is not None:
            return self._marker(failure)
        return self._new_node(field_name, kind, type_identity, value, (), depth)

    def _special_identity(
        self,
        field_name: str,
        label: str,
        payload: bytes,
        depth: int,
    ) -> Task164RawProjectionNode:
        digest = __import__("hashlib").sha256(payload).hexdigest()
        return self._new_node(
            field_name,
            Task164RawProjectionKind.RECORD,
            label,
            digest,
            (),
            depth,
        )

    def _known_dataclass_fields(
        self,
        value: object,
        field_name: str,
        depth: int,
        label: str,
    ) -> Task164RawProjectionNode:
        children: list[Task164RawProjectionNode] = []
        try:
            for item in fields(cast(Any, value)):
                child = self.walk(item.name, getattr(value, item.name), depth + 1)
                children.append(child)
        except BaseException:
            return self._marker(Task164FailureCode.UNSUPPORTED_RAW_VALUE)
        return self._new_node(
            field_name,
            Task164RawProjectionKind.RECORD,
            label,
            None,
            tuple(children),
            depth,
        )

    def _known_object(
        self,
        value: object,
        field_name: str,
        depth: int,
    ) -> Task164RawProjectionNode | None:
        exact = type(value)
        try:
            if exact is Task160Result:
                return self._special_identity(
                    field_name, "Task160Result", task160_result_identity_bytes(value), depth
                )
            if exact is Task161Result:
                return self._special_identity(
                    field_name, "Task161Result", task161_result_identity_bytes(value), depth
                )
            if exact is Task038SuccessResult:
                return self._special_identity(
                    field_name, "Task038SuccessResult", task038_result_identity_bytes(value), depth
                )
            if exact is Task162Result:
                return self._special_identity(
                    field_name, "Task162Result", task162_result_identity_bytes(value), depth
                )
            if exact is Task162SuccessReplayEvidence:
                return self._special_identity(
                    field_name,
                    "Task162SuccessReplayEvidence",
                    task162_success_replay_evidence_identity_bytes(value),
                    depth,
                )
            if exact is Task163Request:
                return self._special_identity(
                    field_name, "Task163Request", task163_request_projection_bytes(value), depth
                )
            if exact is Task163ValidationResult:
                return self._special_identity(
                    field_name,
                    "Task163ValidationResult",
                    task163_validation_projection_bytes(cast(Task163ValidationResult, value)),
                    depth,
                )
            if exact in {
                Task164Request,
                Task164ScenarioClaim,
                Task164ScenarioSetup,
                Task164RepeatRunClaim,
                Task164PythonParityClaim,
                Task164EvidencePackageClaim,
                Task164SurfaceHashRecord,
                Task164Task163ReplayEvidence,
                Task164ScenarioObservation,
                Task164ScenarioRecord,
                Task164AcceptanceCategoryRecord,
                Task164AcceptanceLedger,
                Task164EvidencePackage,
                Task164EvidencePayload,
                Task164ArtifactRecord,
                Task164TerminalCapability,
                Task164Task163Evidence,
                Task164DeterminismEvidence,
                Task164RepeatRunObservation,
                Task164DualRuntimeObservation,
                Task164RuntimeObservation,
                Task164ScopeFenceEvidence,
                Task164Applicability,
                Task164ApplicabilityRecord,
                Task164Completeness,
                Task164ProvenanceSemanticInputs,
                Task164Provenance,
                Task164TypedBlockedResult,
                Task164Result,
                Task164PreResultIdentityInputs,
                Task164Blocker,
            }:
                return self._known_dataclass_fields(value, field_name, depth, exact.__name__)
        except BaseException:
            return self._marker(Task164FailureCode.UNSUPPORTED_RAW_VALUE)
        return None

    def _sort_dict_items(self, value: dict[object, object]) -> list[tuple[object, object]]:
        def key(item: tuple[object, object]) -> tuple[int, bytes, str]:
            candidate = item[0]
            if type(candidate) is str:
                encoded, failure = self._bounded_text(candidate)
                if failure is None and encoded is not None:
                    return 0, encoded, ""
                self._remember(failure or Task164FailureCode.UNSUPPORTED_RAW_VALUE)
                return 1, b"", ""
            identity = _safe_type_identity(candidate) or ""
            return 2, identity.encode("utf-8", "strict"), ""

        return sorted(value.items(), key=key)

    def walk(self, field_name: str, value: object, depth: int) -> Task164RawProjectionNode:
        try:
            special = self._known_object(value, field_name, depth)
            if special is not None:
                return special
            if depth > TASK164_RAW_MAX_DEPTH:
                return self._marker(Task164FailureCode.RAW_DEPTH_LIMIT_EXCEEDED)
            if self.nodes >= TASK164_RAW_MAX_NODES:
                return self._marker(Task164FailureCode.RAW_NODE_LIMIT_EXCEEDED)
            if type(value) is None.__class__:
                return self._new_node(
                    field_name, Task164RawProjectionKind.NONE, None, None, (), depth
                )
            if type(value) is bool:
                return self._new_node(
                    field_name,
                    Task164RawProjectionKind.BOOL,
                    None,
                    "true" if value else "false",
                    (),
                    depth,
                )
            if type(value) is int:
                return self._new_node(
                    field_name, Task164RawProjectionKind.INT, None, str(value), (), depth
                )
            if type(value) is str:
                return self._text_scalar(field_name, value, Task164RawProjectionKind.STRING, depth)
            if type(value) is bytes:
                if len(value) > TASK164_RAW_MAX_SCALAR_BYTES:
                    return self._marker(Task164FailureCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED)
                return self._new_node(
                    field_name, Task164RawProjectionKind.BYTES, None, value.hex(), (), depth
                )
            if type(value) is Decimal:
                if not value.is_finite():
                    return self._marker(Task164FailureCode.UNSUPPORTED_RAW_VALUE)
                return self._text_scalar(
                    field_name, str(value), Task164RawProjectionKind.DECIMAL, depth
                )
            if type(value) is UUID:
                return self._text_scalar(
                    field_name, str(value).lower(), Task164RawProjectionKind.STRING, depth
                )
            if type(value) in _TRUSTED_ENUM_TYPES:
                enum_value = cast(Enum, value).value
                if type(enum_value) is not str:
                    return self._marker(Task164FailureCode.UNSUPPORTED_RAW_VALUE)
                return self._text_scalar(
                    field_name, enum_value, Task164RawProjectionKind.ENUM, depth
                )
            if type(value) is dict:
                children = tuple(
                    self.walk(key if type(key) is str else "<non-string-key>", item, depth + 1)
                    for key, item in self._sort_dict_items(value)
                )
                return self._new_node(
                    field_name, Task164RawProjectionKind.RECORD, "dict", None, children, depth
                )
            if type(value) in (tuple, list):
                sequence = cast(tuple[object, ...] | list[object], value)
                children = tuple(self.walk("item", item, depth + 1) for item in sequence)
                return self._new_node(
                    field_name,
                    Task164RawProjectionKind.SEQUENCE,
                    type(value).__name__,
                    None,
                    children,
                    depth,
                )
            # Calling this helper is the only identity inspection permitted for
            # an unsupported object.  Its result is intentionally not emitted
            # as an authority-bearing value.
            _safe_type_identity(value)
            return self._marker(Task164FailureCode.UNSUPPORTED_RAW_VALUE)
        except UnicodeEncodeError:
            return self._marker(Task164FailureCode.RAW_UNICODE_ENCODING_FAILURE)
        except BaseException:
            return self._marker(Task164FailureCode.UNSUPPORTED_RAW_VALUE)


def _minimal_projection() -> Task164RawRequestProjection:
    return Task164RawRequestProjection(
        schema_version=TASK164_RAW_PROJECTION_SCHEMA_VERSION,
        root=Task164RawProjectionNode(
            field_name="__TASK164_LIMIT_MARKER__",
            kind=Task164RawProjectionKind.LIMIT_MARKER,
            type_identity=None,
            scalar_payload=Task164FailureCode.UNSUPPORTED_RAW_VALUE.value,
            children=(),
        ),
    )


def project_raw_request_with_diagnostics(raw: object) -> RawProjectionOutcome:
    walker = _Walker()
    try:
        if type(raw) is not dict:
            walker._remember(Task164FailureCode.INVALID_REQUEST_TYPE)
            root = Task164RawProjectionNode(
                field_name="__TASK164_LIMIT_MARKER__",
                kind=Task164RawProjectionKind.LIMIT_MARKER,
                type_identity=None,
                scalar_payload=Task164FailureCode.UNSUPPORTED_RAW_VALUE.value,
                children=(),
            )
        else:
            root = walker.walk("root", raw, 0)
        projection = Task164RawRequestProjection(
            schema_version=TASK164_RAW_PROJECTION_SCHEMA_VERSION,
            root=root,
        )
        return RawProjectionOutcome(projection=projection, reasons=tuple(walker.reasons))
    except BaseException:
        return RawProjectionOutcome(
            projection=_minimal_projection(),
            reasons=(Task164FailureCode.UNSUPPORTED_RAW_VALUE,),
        )


def project_raw_request(raw: object) -> Task164RawRequestProjection:
    return project_raw_request_with_diagnostics(raw).projection


__all__ = [
    "RawProjectionOutcome",
    "project_raw_request",
    "project_raw_request_with_diagnostics",
]
