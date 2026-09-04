"""TASK160 raw ingress, projection, and strict-model admission."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import fields
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, cast

from .canonical import raw_blocked_hash, raw_blocked_result_id, raw_request_projection_hash
from .errors import BlockerCode, make_blocker, sort_blockers
from .models import (
    TASK160_IMPLEMENTATION_SOFTWARE_VERSION,
    TASK160_SCHEMA_VERSION,
    TASK160_VERSION,
    ConstructionFamily,
    FailureStage,
    PropertyEvaluationBasis,
    PropertyEvaluationContext,
    PropertyEvaluationQueryType,
    PropertySnapshotIdentity,
    PropertySnapshotIdentityScheme,
    RatingStreamInput,
    RawProjectionKind,
    RawProjectionNode,
    SideBinding,
    Task160AdapterEvidence,
    Task160EnvelopeAuthority,
    Task160PhaseAssertion,
    Task160PropertySnapshot,
    Task160ProvenanceInputs,
    Task160RawAdapterEvidence,
    Task160RawBoundaryBlockedResult,
    Task160RawEnvelopeAuthority,
    Task160RawPropertyEvaluationContext,
    Task160RawPropertySnapshotIdentity,
    Task160RawPropertySnapshotInput,
    Task160RawProvenance,
    Task160RawRequest,
    Task160RawRequestProjection,
    Task160RawStreamInput,
    Task160Request,
)

RAW_RECORD_FIELDS: dict[str, tuple[str, ...]] = {
    "Task160RawRequest": (
        "schema_version",
        "task160_version",
        "implementation_software_version",
        "stream_records",
        "envelope_authority",
        "adapter_evidence",
        "deferred_capabilities",
        "provenance",
    ),
    "Task160RawStreamInput": (
        "stream_id",
        "side_binding",
        "fluid_or_service_identity",
        "phase_assertion",
        "inlet_temperature_K",
        "inlet_pressure_Pa_absolute",
        "mass_flow_kg_s",
        "property_snapshot",
        "provenance",
    ),
    "Task160RawPropertySnapshotInput": (
        "specific_heat_J_kg_K",
        "property_source_identity",
        "property_source_version",
        "property_snapshot_identity",
        "property_evaluation_context",
    ),
    "Task160RawPropertySnapshotIdentity": (
        "scheme",
        "value",
    ),
    "Task160RawPropertyEvaluationContext": (
        "evaluation_basis",
        "query_type",
        "evaluation_temperature_K",
        "evaluation_pressure_Pa_absolute",
        "context_identity",
    ),
    "Task160RawEnvelopeAuthority": (
        "construction_family",
        "shell_pass_count",
        "tube_pass_count",
        "authority_source_identity",
        "authority_source_version",
        "authority_identity",
        "evidence_refs",
    ),
    "Task160RawAdapterEvidence": (
        "adapter_id",
        "source_task_id",
        "source_result_identity",
        "admitted_fields",
        "rejected_fields",
        "source_evidence_refs",
        "evidence_hash",
    ),
    "Task160RawProvenance": (
        "producer_identity",
        "upstream_identity_hashes",
        "source_evidence_refs",
        "adapter_evidence_refs",
    ),
}

ENUM_FIELDS = {
    "side_binding",
    "phase_assertion",
    "construction_family",
    "evaluation_basis",
    "query_type",
    "scheme",
}
NUMERIC_FIELDS = {
    "inlet_temperature_K",
    "inlet_pressure_Pa_absolute",
    "mass_flow_kg_s",
    "specific_heat_J_kg_K",
    "evaluation_temperature_K",
    "evaluation_pressure_Pa_absolute",
    "shell_pass_count",
    "tube_pass_count",
}
SET_LIKE_FIELDS = {
    "source_evidence_refs",
    "upstream_identity_hashes",
    "adapter_evidence_refs",
    "deferred_capabilities",
    "evidence_refs",
    "producer_identity",
}


class RawIngressStructuralError(TypeError):
    """The value is outside the explicitly supported raw ingress grammar."""


def _mapping_value(value: object, key: str, default: object = None) -> object:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _reject_unknown_mapping_keys(
    value: object,
    allowed: tuple[str, ...],
    record_name: str,
) -> None:
    if not isinstance(value, Mapping):
        return
    unknown = tuple(key for key in value if type(key) is not str or key not in allowed)
    if unknown:
        raise RawIngressStructuralError(
            f"{record_name} contains fields outside the TASK160 raw grammar"
        )


def _sequence(value: object, name: str) -> tuple[object, ...] | None:
    if value is None:
        return None
    if type(value) is list:
        return tuple(cast(list[object], value))
    if type(value) is tuple:
        return cast(tuple[object, ...], value)
    if type(value) not in (list, tuple):
        raise RawIngressStructuralError(f"{name} must be a list or tuple")
    raise AssertionError("unreachable sequence type")


def _raw_value(value: object, *, field_name: str = "") -> object:
    """Validate the raw grammar without applying engineering semantics."""
    if value is None or type(value) is str or type(value) is int or isinstance(value, Decimal):
        if isinstance(value, Decimal) or type(value) is int or type(value) is str:
            return value
        return None
    if type(value) is bool:
        raise RawIngressStructuralError(f"bool is not a TASK160 raw value at {field_name}")
    if type(value) is float:
        raise RawIngressStructuralError(f"float is not a TASK160 raw value at {field_name}")
    if type(value) in (list, tuple):
        sequence = cast(Sequence[object], value)
        return tuple(_raw_value(item, field_name=field_name) for item in sequence)
    if isinstance(value, Mapping):
        return {_raw_key(key): _raw_value(item, field_name=str(key)) for key, item in value.items()}
    if isinstance(
        value,
        (
            Task160RawRequest,
            Task160RawStreamInput,
            Task160RawPropertySnapshotInput,
            Task160RawPropertySnapshotIdentity,
            Task160RawPropertyEvaluationContext,
            Task160RawEnvelopeAuthority,
            Task160RawAdapterEvidence,
            Task160RawProvenance,
        ),
    ):
        return {
            item.name: _raw_value(getattr(value, item.name), field_name=item.name)
            for item in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    raise RawIngressStructuralError(f"unsupported raw value type {type(value).__name__}")


def _raw_key(value: object) -> str:
    if type(value) is not str:
        raise RawIngressStructuralError("raw record keys must be strings")
    return value


def _projection_scalar(value: object, field_name: str) -> RawProjectionNode:
    if value is None:
        return RawProjectionNode(field_name, RawProjectionKind.NONE, None, ())
    if type(value) is bool or type(value) is float:
        raise RawIngressStructuralError(f"unsupported scalar type at {field_name}")
    if isinstance(value, Decimal):
        if value.is_finite():
            return RawProjectionNode(field_name, RawProjectionKind.DECIMAL, str(value), ())
        return RawProjectionNode(
            field_name, RawProjectionKind.INVALID_NUMERIC_LITERAL, str(value), ()
        )
    if type(value) is int:
        return RawProjectionNode(field_name, RawProjectionKind.INTEGER, str(value), ())
    if type(value) is str:
        if field_name in NUMERIC_FIELDS:
            try:
                parsed = Decimal(value)
            except InvalidOperation:
                return RawProjectionNode(
                    field_name, RawProjectionKind.INVALID_NUMERIC_LITERAL, value, ()
                )
            if not parsed.is_finite():
                return RawProjectionNode(
                    field_name, RawProjectionKind.INVALID_NUMERIC_LITERAL, value, ()
                )
        kind = (
            RawProjectionKind.ENUM_LITERAL
            if field_name in ENUM_FIELDS
            else RawProjectionKind.STRING
        )
        return RawProjectionNode(field_name, kind, value, ())
    if isinstance(value, Enum):
        return RawProjectionNode(
            field_name,
            RawProjectionKind.ENUM_LITERAL,
            str(value.value),
            (),
        )
    raise RawIngressStructuralError(f"unsupported scalar type at {field_name}")


def _projection_record(field_name: str, record_name: str, value: object) -> RawProjectionNode:
    if value is None:
        return _projection_scalar(None, field_name)
    if not isinstance(
        value,
        (
            Mapping,
            Task160RawRequest,
            Task160RawStreamInput,
            Task160RawPropertySnapshotInput,
            Task160RawPropertyEvaluationContext,
            Task160RawPropertySnapshotIdentity,
            Task160RawEnvelopeAuthority,
            Task160RawAdapterEvidence,
            Task160RawProvenance,
        ),
    ):
        raise RawIngressStructuralError(f"{field_name} must be a raw record")
    _reject_unknown_mapping_keys(value, RAW_RECORD_FIELDS[record_name], record_name)
    children = tuple(
        _projection_value(child_name, _mapping_value(value, child_name), child_name)
        for child_name in RAW_RECORD_FIELDS[record_name]
    )
    return RawProjectionNode(field_name, RawProjectionKind.RECORD, None, children)


def _projection_sequence(
    field_name: str, value: object, *, record_name: str | None = None
) -> RawProjectionNode:
    if value is None:
        return _projection_scalar(None, field_name)
    items = _sequence(value, field_name)
    if items is None:
        return _projection_scalar(None, field_name)
    set_like = field_name in SET_LIKE_FIELDS
    if set_like and all(type(item) is str for item in items) and len(items) == len(set(items)):
        string_items = cast(tuple[str, ...], items)
        items = tuple(sorted(string_items))
    children: list[RawProjectionNode] = []
    for index, item in enumerate(items):
        child_name = f"item-{index:06d}"
        if record_name is not None and isinstance(
            item,
            (
                Mapping,
                Task160RawRequest,
                Task160RawStreamInput,
                Task160RawPropertySnapshotInput,
                Task160RawPropertySnapshotIdentity,
                Task160RawPropertyEvaluationContext,
                Task160RawEnvelopeAuthority,
                Task160RawAdapterEvidence,
                Task160RawProvenance,
            ),
        ):
            children.append(_projection_record(child_name, record_name, item))
        else:
            children.append(_projection_value(child_name, item, field_name))
    return RawProjectionNode(field_name, RawProjectionKind.SEQUENCE, None, tuple(children))


def _projection_value(field_name: str, value: object, parent_field: str = "") -> RawProjectionNode:
    if field_name == "stream_records":
        return _projection_sequence(field_name, value, record_name="Task160RawStreamInput")
    if field_name == "adapter_evidence":
        return _projection_sequence(field_name, value, record_name="Task160RawAdapterEvidence")
    if field_name == "property_snapshot":
        if isinstance(
            value,
            (
                Mapping,
                Task160RawPropertySnapshotInput,
            ),
        ):
            return _projection_record(field_name, "Task160RawPropertySnapshotInput", value)
        return _projection_scalar(value, field_name)
    if field_name == "property_snapshot_identity":
        if type(value) is str:
            # A direct string is not a valid identity record, but it is a
            # representable semantic error and must remain hashable so B015
            # is emitted by the authority validator rather than escaping at
            # the raw boundary.
            return _projection_scalar(value, field_name)
        return _projection_record(field_name, "Task160RawPropertySnapshotIdentity", value)
    if field_name == "property_evaluation_context":
        if isinstance(value, (Mapping, Task160RawPropertyEvaluationContext)):
            return _projection_record(field_name, "Task160RawPropertyEvaluationContext", value)
        return _projection_scalar(value, field_name)
    if field_name == "envelope_authority":
        if isinstance(value, (Mapping, Task160RawEnvelopeAuthority)):
            return _projection_record(field_name, "Task160RawEnvelopeAuthority", value)
        return _projection_scalar(value, field_name)
    if field_name == "provenance":
        if isinstance(value, (Mapping, Task160RawProvenance)):
            return _projection_record(field_name, "Task160RawProvenance", value)
        return _projection_scalar(value, field_name)
    if field_name in {
        "admitted_fields",
        "rejected_fields",
        "source_evidence_refs",
        "upstream_identity_hashes",
        "adapter_evidence_refs",
        "deferred_capabilities",
        "evidence_refs",
        "producer_identity",
    }:
        return _projection_sequence(field_name, value)
    return _projection_scalar(value, field_name or parent_field)


def coerce_raw_request(value: Task160RawRequest | Mapping[str, object]) -> Task160RawRequest:
    if isinstance(value, Task160RawRequest):
        return value
    if not isinstance(value, Mapping):
        raise RawIngressStructuralError("request must be Task160RawRequest or mapping")
    _reject_unknown_mapping_keys(value, RAW_RECORD_FIELDS["Task160RawRequest"], "Task160RawRequest")
    stream_items = _sequence(value.get("stream_records"), "stream_records")
    streams = (
        None
        if stream_items is None
        else tuple(
            item
            if isinstance(item, Task160RawStreamInput)
            else Task160RawStreamInput(
                stream_id=_mapping_value(item, "stream_id"),
                side_binding=_mapping_value(item, "side_binding"),
                fluid_or_service_identity=_mapping_value(item, "fluid_or_service_identity"),
                phase_assertion=_mapping_value(item, "phase_assertion"),
                inlet_temperature_K=_mapping_value(item, "inlet_temperature_K"),
                inlet_pressure_Pa_absolute=_mapping_value(item, "inlet_pressure_Pa_absolute"),
                mass_flow_kg_s=_mapping_value(item, "mass_flow_kg_s"),
                property_snapshot=(
                    _coerce_raw_snapshot(_mapping_value(item, "property_snapshot"))
                    if _mapping_value(item, "property_snapshot") is not None
                    else None
                ),
                provenance=(
                    _coerce_raw_provenance(_mapping_value(item, "provenance"))
                    if _mapping_value(item, "provenance") is not None
                    else None
                ),
            )
            if isinstance(item, Mapping)
            else item
            for item in stream_items
        )
    )
    adapter_items = _sequence(value.get("adapter_evidence"), "adapter_evidence")
    adapters = (
        None
        if adapter_items is None
        else tuple(
            item if isinstance(item, Task160RawAdapterEvidence) else _coerce_raw_adapter(item)
            for item in adapter_items
        )
    )
    envelope = _mapping_value(value, "envelope_authority")
    provenance = _mapping_value(value, "provenance")
    return Task160RawRequest(
        schema_version=value.get("schema_version"),
        task160_version=value.get("task160_version"),
        implementation_software_version=value.get("implementation_software_version"),
        stream_records=streams,
        envelope_authority=(
            envelope
            if isinstance(envelope, Task160RawEnvelopeAuthority)
            else _coerce_raw_envelope(envelope)
            if envelope is not None
            else None
        ),
        adapter_evidence=adapters,
        deferred_capabilities=value.get("deferred_capabilities"),
        provenance=(
            provenance
            if isinstance(provenance, Task160RawProvenance)
            else _coerce_raw_provenance(provenance)
            if provenance is not None
            else None
        ),
    )


def _coerce_raw_snapshot(value: object) -> Task160RawPropertySnapshotInput:
    if isinstance(value, Task160RawPropertySnapshotInput):
        return value
    if not isinstance(value, Mapping):
        return value  # type: ignore[return-value]
    _reject_unknown_mapping_keys(
        value,
        RAW_RECORD_FIELDS["Task160RawPropertySnapshotInput"],
        "Task160RawPropertySnapshotInput",
    )
    return Task160RawPropertySnapshotInput(
        specific_heat_J_kg_K=_mapping_value(value, "specific_heat_J_kg_K"),
        property_source_identity=_mapping_value(value, "property_source_identity"),
        property_source_version=_mapping_value(value, "property_source_version"),
        property_snapshot_identity=_coerce_raw_snapshot_identity(
            _mapping_value(value, "property_snapshot_identity")
        )
        if _mapping_value(value, "property_snapshot_identity") is not None
        else None,
        property_evaluation_context=(
            _coerce_raw_context(_mapping_value(value, "property_evaluation_context"))
            if _mapping_value(value, "property_evaluation_context") is not None
            else None
        ),
    )


def _coerce_raw_snapshot_identity(value: object) -> Task160RawPropertySnapshotIdentity | object:
    if isinstance(value, Task160RawPropertySnapshotIdentity):
        return value
    if isinstance(value, Mapping):
        _reject_unknown_mapping_keys(
            value,
            RAW_RECORD_FIELDS["Task160RawPropertySnapshotIdentity"],
            "Task160RawPropertySnapshotIdentity",
        )
        return Task160RawPropertySnapshotIdentity(
            scheme=value.get("scheme"),
            value=value.get("value"),
        )
    return value


def _coerce_raw_context(value: object) -> Task160RawPropertyEvaluationContext:
    if isinstance(value, Task160RawPropertyEvaluationContext):
        return value
    if not isinstance(value, Mapping):
        return value  # type: ignore[return-value]
    _reject_unknown_mapping_keys(
        value,
        RAW_RECORD_FIELDS["Task160RawPropertyEvaluationContext"],
        "Task160RawPropertyEvaluationContext",
    )
    return Task160RawPropertyEvaluationContext(
        evaluation_basis=_mapping_value(value, "evaluation_basis"),
        query_type=_mapping_value(value, "query_type"),
        evaluation_temperature_K=_mapping_value(value, "evaluation_temperature_K"),
        evaluation_pressure_Pa_absolute=_mapping_value(value, "evaluation_pressure_Pa_absolute"),
        context_identity=_mapping_value(value, "context_identity"),
    )


def _coerce_raw_provenance(value: object) -> Task160RawProvenance:
    if isinstance(value, Task160RawProvenance):
        return value
    if not isinstance(value, Mapping):
        return value  # type: ignore[return-value]
    _reject_unknown_mapping_keys(
        value, RAW_RECORD_FIELDS["Task160RawProvenance"], "Task160RawProvenance"
    )
    return Task160RawProvenance(
        producer_identity=_mapping_value(value, "producer_identity"),
        upstream_identity_hashes=_mapping_value(value, "upstream_identity_hashes"),
        source_evidence_refs=_mapping_value(value, "source_evidence_refs"),
        adapter_evidence_refs=_mapping_value(value, "adapter_evidence_refs"),
    )


def _coerce_raw_envelope(value: object) -> Task160RawEnvelopeAuthority:
    if isinstance(value, Task160RawEnvelopeAuthority):
        return value
    if not isinstance(value, Mapping):
        return value  # type: ignore[return-value]
    _reject_unknown_mapping_keys(
        value,
        RAW_RECORD_FIELDS["Task160RawEnvelopeAuthority"],
        "Task160RawEnvelopeAuthority",
    )
    return Task160RawEnvelopeAuthority(
        construction_family=_mapping_value(value, "construction_family"),
        shell_pass_count=_mapping_value(value, "shell_pass_count"),
        tube_pass_count=_mapping_value(value, "tube_pass_count"),
        authority_source_identity=_mapping_value(value, "authority_source_identity"),
        authority_source_version=_mapping_value(value, "authority_source_version"),
        authority_identity=_mapping_value(value, "authority_identity"),
        evidence_refs=_mapping_value(value, "evidence_refs"),
    )


def _coerce_raw_adapter(value: object) -> Task160RawAdapterEvidence:
    if not isinstance(value, Mapping):
        return value  # type: ignore[return-value]
    _reject_unknown_mapping_keys(
        value, RAW_RECORD_FIELDS["Task160RawAdapterEvidence"], "Task160RawAdapterEvidence"
    )
    return Task160RawAdapterEvidence(
        adapter_id=_mapping_value(value, "adapter_id"),
        source_task_id=_mapping_value(value, "source_task_id"),
        source_result_identity=_mapping_value(value, "source_result_identity"),
        admitted_fields=_mapping_value(value, "admitted_fields"),
        rejected_fields=_mapping_value(value, "rejected_fields"),
        source_evidence_refs=_mapping_value(value, "source_evidence_refs"),
        evidence_hash=_mapping_value(value, "evidence_hash"),
    )


def project_raw_request(
    value: Task160RawRequest | Mapping[str, object],
) -> Task160RawRequestProjection:
    raw = coerce_raw_request(value)
    # Run the grammar walk before building a deterministic tree.  This is
    # where bool-before-int and float rejection are deliberately enforced.
    _raw_value(raw)
    children = tuple(
        _projection_value(name, getattr(raw, name), name)
        for name in RAW_RECORD_FIELDS["Task160RawRequest"]
    )
    return Task160RawRequestProjection(
        schema_version="task160.raw-projection.v1",
        root=RawProjectionNode("request", RawProjectionKind.RECORD, None, children),
    )


def _raw_tuple(
    value: object, name: str, blockers: list[Any], *, required: bool = True
) -> tuple[object, ...] | None:
    if value is None:
        if required:
            blockers.append(
                make_blocker(BlockerCode.B018, stage=FailureStage.RAW_BOUNDARY, field_path=name)
            )
        return None
    if type(value) not in (list, tuple):
        blockers.append(
            make_blocker(BlockerCode.B018, stage=FailureStage.RAW_BOUNDARY, field_path=name)
        )
        return None
    values: tuple[object, ...] = tuple(cast(Sequence[object], value))
    if len(values) != len(set(map(repr, values))):
        blockers.append(
            make_blocker(BlockerCode.B018, stage=FailureStage.RAW_BOUNDARY, field_path=name)
        )
    return values


def _to_decimal(
    value: object,
    name: str,
    blockers: list[Any],
    *,
    positive: bool = False,
    invalid_code: BlockerCode | None = None,
) -> Decimal | None:
    code_for_invalid = invalid_code
    if value is None or value == "":
        if code_for_invalid is None:
            if "temperature" in name:
                code_for_invalid = BlockerCode.B009
            elif "cp" in name or "specific_heat" in name:
                code_for_invalid = BlockerCode.B012
            else:
                code_for_invalid = BlockerCode.B011
        code = code_for_invalid
        blockers.append(make_blocker(code, stage=FailureStage.RAW_BOUNDARY, field_path=name))
        return None
    if type(value) is bool or type(value) is float:
        blockers.append(
            make_blocker(
                code_for_invalid
                or (BlockerCode.B009 if "temperature" in name else BlockerCode.B011),
                stage=FailureStage.RAW_BOUNDARY,
                field_path=name,
            )
        )
        return None
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(value)  # type: ignore[arg-type]
    except (InvalidOperation, ValueError, TypeError):
        parsed = None
    if parsed is None or not parsed.is_finite():
        code = code_for_invalid or (
            BlockerCode.B009
            if "temperature" in name
            else BlockerCode.B012
            if "cp" in name or "specific_heat" in name
            else BlockerCode.B011
        )
        blockers.append(make_blocker(code, stage=FailureStage.RAW_BOUNDARY, field_path=name))
        return None
    digits = len(parsed.as_tuple().digits)
    if digits > 79 or parsed.adjusted() < -499000 or parsed.adjusted() > 499000:
        code = code_for_invalid or (
            BlockerCode.B012 if "cp" in name or "specific_heat" in name else BlockerCode.B011
        )
        blockers.append(make_blocker(code, stage=FailureStage.RAW_BOUNDARY, field_path=name))
        return None
    if positive and parsed <= Decimal(0):
        code = code_for_invalid or (
            BlockerCode.B012
            if "cp" in name or "specific_heat" in name
            else BlockerCode.B009
            if "temperature" in name
            else BlockerCode.B011
        )
        blockers.append(make_blocker(code, stage=FailureStage.RAW_BOUNDARY, field_path=name))
        return None
    return parsed


def _to_required_string(
    value: object, code: BlockerCode, name: str, blockers: list[Any]
) -> str | None:
    if type(value) is str and value:
        return value
    blockers.append(make_blocker(code, stage=FailureStage.RAW_BOUNDARY, field_path=name))
    return None


def _to_strings(
    value: object,
    name: str,
    blockers: list[Any],
    *,
    required: bool = True,
    sort_values: bool = True,
    nonempty: bool = False,
) -> tuple[str, ...] | None:
    if value is None:
        if required:
            blockers.append(
                make_blocker(BlockerCode.B018, stage=FailureStage.RAW_BOUNDARY, field_path=name)
            )
        return None
    values: Sequence[object]
    if type(value) is list:
        values = cast(list[object], value)
    elif type(value) is tuple:
        values = cast(tuple[object, ...], value)
    else:
        blockers.append(
            make_blocker(BlockerCode.B018, stage=FailureStage.RAW_BOUNDARY, field_path=name)
        )
        return None
    if any(type(item) is not str or not item for item in values):
        blockers.append(
            make_blocker(BlockerCode.B018, stage=FailureStage.RAW_BOUNDARY, field_path=name)
        )
        return None
    result: tuple[str, ...] = tuple(cast(Sequence[str], values))
    if nonempty and not result:
        blockers.append(
            make_blocker(BlockerCode.B018, stage=FailureStage.RAW_BOUNDARY, field_path=name)
        )
        return None
    if len(result) != len(set(result)):
        blockers.append(
            make_blocker(BlockerCode.B018, stage=FailureStage.RAW_BOUNDARY, field_path=name)
        )
        return None
    return tuple(sorted(result)) if sort_values else result


def _identity(value: object, blockers: list[Any], path: str) -> PropertySnapshotIdentity | None:
    if isinstance(value, PropertySnapshotIdentity):
        return value
    if isinstance(value, str):
        blockers.append(
            make_blocker(BlockerCode.B015, stage=FailureStage.RAW_BOUNDARY, field_path=path)
        )
        return None
    scheme_value = _mapping_value(value, "scheme")
    raw_value = _mapping_value(value, "value")
    if type(raw_value) is not str:
        blockers.append(
            make_blocker(BlockerCode.B015, stage=FailureStage.RAW_BOUNDARY, field_path=path)
        )
        return None
    if scheme_value == PropertySnapshotIdentityScheme.SHA256_HEX or scheme_value == "SHA256_HEX":
        try:
            return PropertySnapshotIdentity(PropertySnapshotIdentityScheme.SHA256_HEX, raw_value)
        except ValueError:
            blockers.append(
                make_blocker(BlockerCode.B015, stage=FailureStage.RAW_BOUNDARY, field_path=path)
            )
            return None
    if (
        scheme_value == PropertySnapshotIdentityScheme.OPAQUE_REPRODUCIBLE
        or scheme_value == "OPAQUE_REPRODUCIBLE"
    ):
        try:
            return PropertySnapshotIdentity(
                PropertySnapshotIdentityScheme.OPAQUE_REPRODUCIBLE, raw_value
            )
        except ValueError:
            blockers.append(
                make_blocker(BlockerCode.B015, stage=FailureStage.RAW_BOUNDARY, field_path=path)
            )
            return None
    blockers.append(
        make_blocker(BlockerCode.B015, stage=FailureStage.RAW_BOUNDARY, field_path=path)
    )
    return None


def _build_context(
    value: object, blockers: list[Any], path: str
) -> PropertyEvaluationContext | None:
    if isinstance(value, PropertyEvaluationContext):
        return value
    if value is None:
        blockers.append(
            make_blocker(BlockerCode.B016, stage=FailureStage.RAW_BOUNDARY, field_path=path)
        )
        return None
    basis_value = _mapping_value(value, "evaluation_basis")
    query_value = _mapping_value(value, "query_type")
    if not isinstance(basis_value, str) or not isinstance(query_value, str):
        blockers.append(
            make_blocker(BlockerCode.B016, stage=FailureStage.RAW_BOUNDARY, field_path=path)
        )
        return None
    try:
        basis = PropertyEvaluationBasis(basis_value)
        query = PropertyEvaluationQueryType(query_value)
    except (ValueError, TypeError):
        blockers.append(
            make_blocker(BlockerCode.B016, stage=FailureStage.RAW_BOUNDARY, field_path=path)
        )
        return None
    temp = _to_decimal(
        _mapping_value(value, "evaluation_temperature_K"),
        path + ".evaluation_temperature_K",
        blockers,
        positive=True,
        invalid_code=BlockerCode.B016,
    )
    pressure_raw = _mapping_value(value, "evaluation_pressure_Pa_absolute")
    identity = _to_required_string(
        _mapping_value(value, "context_identity"),
        BlockerCode.B016,
        path + ".context_identity",
        blockers,
    )
    if temp is None or identity is None:
        return None
    if query is PropertyEvaluationQueryType.TEMPERATURE_ONLY:
        if pressure_raw is not None:
            blockers.append(
                make_blocker(BlockerCode.B016, stage=FailureStage.RAW_BOUNDARY, field_path=path)
            )
            return None
        pressure = None
    else:
        pressure = _to_decimal(
            pressure_raw,
            path + ".evaluation_pressure_Pa_absolute",
            blockers,
            positive=True,
            invalid_code=BlockerCode.B017,
        )
        if pressure is None:
            return None
    try:
        return PropertyEvaluationContext(basis, query, temp, pressure, identity)
    except ValueError:
        blockers.append(
            make_blocker(BlockerCode.B016, stage=FailureStage.RAW_BOUNDARY, field_path=path)
        )
        return None


def _build_snapshot(
    value: object, blockers: list[Any], path: str
) -> Task160PropertySnapshot | None:
    if value is None:
        blockers.append(
            make_blocker(BlockerCode.B015, stage=FailureStage.RAW_BOUNDARY, field_path=path)
        )
        return None
    cp = _to_decimal(
        _mapping_value(value, "specific_heat_J_kg_K"),
        path + ".specific_heat_J_kg_K",
        blockers,
        positive=True,
    )
    source = _to_required_string(
        _mapping_value(value, "property_source_identity"),
        BlockerCode.B013,
        path + ".property_source_identity",
        blockers,
    )
    version = _to_required_string(
        _mapping_value(value, "property_source_version"),
        BlockerCode.B014,
        path + ".property_source_version",
        blockers,
    )
    identity = _identity(
        _mapping_value(value, "property_snapshot_identity"),
        blockers,
        path + ".property_snapshot_identity",
    )
    context = _build_context(
        _mapping_value(value, "property_evaluation_context"),
        blockers,
        path + ".property_evaluation_context",
    )
    if cp is None or source is None or version is None or identity is None or context is None:
        return None
    try:
        return Task160PropertySnapshot(cp, source, version, identity, context)
    except ValueError:
        blockers.append(
            make_blocker(BlockerCode.B015, stage=FailureStage.RAW_BOUNDARY, field_path=path)
        )
        return None


def _build_provenance(
    value: object, blockers: list[Any], path: str
) -> Task160ProvenanceInputs | None:
    if value is None:
        blockers.append(
            make_blocker(BlockerCode.B018, stage=FailureStage.RAW_BOUNDARY, field_path=path)
        )
        return None
    producer = _to_strings(
        _mapping_value(value, "producer_identity"),
        path + ".producer_identity",
        blockers,
        required=True,
        nonempty=True,
    )
    upstream = _to_strings(
        _mapping_value(value, "upstream_identity_hashes"),
        path + ".upstream_identity_hashes",
        blockers,
        required=True,
        nonempty=True,
    )
    source_refs = _to_strings(
        _mapping_value(value, "source_evidence_refs"),
        path + ".source_evidence_refs",
        blockers,
        required=True,
        nonempty=True,
    )
    adapter_refs = _to_strings(
        _mapping_value(value, "adapter_evidence_refs"),
        path + ".adapter_evidence_refs",
        blockers,
        required=True,
        nonempty=True,
    )
    if upstream is not None:
        for item in upstream:
            if len(item) != 64 or any(char not in "0123456789abcdef" for char in item):
                blockers.append(
                    make_blocker(
                        BlockerCode.B027,
                        stage=FailureStage.RAW_BOUNDARY,
                        field_path=path + ".upstream_identity_hashes",
                    )
                )
                break
    if producer is None or upstream is None or source_refs is None or adapter_refs is None:
        return None
    try:
        return Task160ProvenanceInputs(producer, upstream, source_refs, adapter_refs)
    except ValueError:
        blockers.append(
            make_blocker(BlockerCode.B018, stage=FailureStage.RAW_BOUNDARY, field_path=path)
        )
        return None


def _build_adapter(value: object, blockers: list[Any], path: str) -> Task160AdapterEvidence | None:
    if value is None:
        blockers.append(
            make_blocker(BlockerCode.B025, stage=FailureStage.RAW_BOUNDARY, field_path=path)
        )
        return None
    adapter_id = _to_required_string(
        _mapping_value(value, "adapter_id"), BlockerCode.B025, path + ".adapter_id", blockers
    )
    source_task = _to_required_string(
        _mapping_value(value, "source_task_id"),
        BlockerCode.B025,
        path + ".source_task_id",
        blockers,
    )
    source_result = _mapping_value(value, "source_result_identity")
    if source_result is not None and (type(source_result) is not str or not source_result):
        blockers.append(
            make_blocker(
                BlockerCode.B025,
                stage=FailureStage.RAW_BOUNDARY,
                field_path=path + ".source_result_identity",
            )
        )
        source_result = None
    admitted = _to_strings(
        _mapping_value(value, "admitted_fields"),
        path + ".admitted_fields",
        blockers,
        sort_values=False,
        nonempty=True,
    )
    rejected = _to_strings(
        _mapping_value(value, "rejected_fields"),
        path + ".rejected_fields",
        blockers,
        sort_values=False,
        nonempty=True,
    )
    refs = _to_strings(
        _mapping_value(value, "source_evidence_refs"),
        path + ".source_evidence_refs",
        blockers,
        nonempty=True,
    )
    evidence_hash = _mapping_value(value, "evidence_hash")
    if (
        type(evidence_hash) is not str
        or len(evidence_hash) != 64
        or any(c not in "0123456789abcdef" for c in evidence_hash)
    ):
        blockers.append(
            make_blocker(
                BlockerCode.B025,
                stage=FailureStage.RAW_BOUNDARY,
                field_path=path + ".evidence_hash",
            )
        )
        evidence_hash = None
    if (
        adapter_id is None
        or source_task is None
        or admitted is None
        or rejected is None
        or refs is None
        or evidence_hash is None
    ):
        return None
    from .adapters import (
        TASK026_ADMITTED_FIELDS,
        TASK026_REJECTED_FIELDS,
        TASK032_ADMITTED_FIELDS,
        TASK032_REJECTED_FIELDS,
    )

    expected_vocabulary = {
        "TASK026": (TASK026_ADMITTED_FIELDS, TASK026_REJECTED_FIELDS),
        "TASK032": (TASK032_ADMITTED_FIELDS, TASK032_REJECTED_FIELDS),
    }.get(source_task)
    if expected_vocabulary is not None and (admitted, rejected) != expected_vocabulary:
        blockers.append(
            make_blocker(BlockerCode.B019, stage=FailureStage.RAW_BOUNDARY, field_path=path)
        )
        return None
    try:
        return Task160AdapterEvidence(
            adapter_id, source_task, source_result, admitted, rejected, refs, evidence_hash
        )
    except ValueError:
        blockers.append(
            make_blocker(BlockerCode.B025, stage=FailureStage.RAW_BOUNDARY, field_path=path)
        )
        return None


def _build_envelope(value: object, blockers: list[Any]) -> Task160EnvelopeAuthority | None:
    if value is None:
        blockers.append(
            make_blocker(
                BlockerCode.B021, stage=FailureStage.RAW_BOUNDARY, field_path="envelope_authority"
            )
        )
        return None
    family_raw = _mapping_value(value, "construction_family")
    if not isinstance(family_raw, str):
        blockers.append(
            make_blocker(
                BlockerCode.B022,
                stage=FailureStage.RAW_BOUNDARY,
                field_path="envelope_authority.construction_family",
            )
        )
        return None
    try:
        family = ConstructionFamily(family_raw)
    except (TypeError, ValueError):
        blockers.append(
            make_blocker(
                BlockerCode.B022,
                stage=FailureStage.RAW_BOUNDARY,
                field_path="envelope_authority.construction_family",
            )
        )
        return None
    shell = _mapping_value(value, "shell_pass_count")
    tube = _mapping_value(value, "tube_pass_count")
    if type(shell) is not int or type(tube) is not int:
        blockers.append(
            make_blocker(
                BlockerCode.B021, stage=FailureStage.RAW_BOUNDARY, field_path="envelope_authority"
            )
        )
        return None
    source = _to_required_string(
        _mapping_value(value, "authority_source_identity"),
        BlockerCode.B021,
        "envelope_authority.authority_source_identity",
        blockers,
    )
    version = _to_required_string(
        _mapping_value(value, "authority_source_version"),
        BlockerCode.B021,
        "envelope_authority.authority_source_version",
        blockers,
    )
    identity = _to_required_string(
        _mapping_value(value, "authority_identity"),
        BlockerCode.B021,
        "envelope_authority.authority_identity",
        blockers,
    )
    refs = _to_strings(
        _mapping_value(value, "evidence_refs"),
        "envelope_authority.evidence_refs",
        blockers,
        nonempty=True,
    )
    if family is not ConstructionFamily.FIXED_TUBESHEET or shell != 1 or tube != 1:
        blockers.append(
            make_blocker(
                BlockerCode.B022, stage=FailureStage.RAW_BOUNDARY, field_path="envelope_authority"
            )
        )
        return None
    if source is None or version is None or identity is None or not refs:
        return None
    try:
        return Task160EnvelopeAuthority(family, shell, tube, source, version, identity, refs)
    except ValueError:
        blockers.append(
            make_blocker(
                BlockerCode.B021, stage=FailureStage.RAW_BOUNDARY, field_path="envelope_authority"
            )
        )
        return None


def build_strict_request(
    raw: Task160RawRequest | Mapping[str, object],
) -> tuple[Task160Request | None, tuple[Any, ...]]:
    request = coerce_raw_request(raw)
    blockers: list[Any] = []
    if request.schema_version not in (TASK160_SCHEMA_VERSION, None):
        blockers.append(
            make_blocker(
                BlockerCode.B023, stage=FailureStage.RAW_BOUNDARY, field_path="schema_version"
            )
        )
    if request.task160_version not in (TASK160_VERSION, None):
        blockers.append(
            make_blocker(
                BlockerCode.B023, stage=FailureStage.RAW_BOUNDARY, field_path="task160_version"
            )
        )
    schema_version = request.schema_version or TASK160_SCHEMA_VERSION
    task_version = request.task160_version or TASK160_VERSION
    software_version = (
        request.implementation_software_version or TASK160_IMPLEMENTATION_SOFTWARE_VERSION
    )

    stream_values = request.stream_records
    if stream_values is None or type(stream_values) not in (tuple, list) or len(stream_values) != 2:
        blockers.append(
            make_blocker(
                BlockerCode.B001, stage=FailureStage.RAW_BOUNDARY, field_path="stream_records"
            )
        )
        stream_values = ()
    strict_streams: list[RatingStreamInput] = []
    seen_sides: list[SideBinding] = []
    for index, raw_stream in enumerate(stream_values):
        path = f"stream_records[{index}]"
        side_raw = _mapping_value(raw_stream, "side_binding")
        if not isinstance(side_raw, str):
            blockers.append(
                make_blocker(
                    BlockerCode.B004,
                    stage=FailureStage.RAW_BOUNDARY,
                    field_path=path + ".side_binding",
                )
            )
            side = None
        else:
            try:
                side = SideBinding(side_raw)
            except (TypeError, ValueError):
                blockers.append(
                    make_blocker(
                        BlockerCode.B004,
                        stage=FailureStage.RAW_BOUNDARY,
                        field_path=path + ".side_binding",
                    )
                )
                side = None
        if side is not None:
            if side is SideBinding.TUBE_SIDE and side in seen_sides:
                blockers.append(
                    make_blocker(
                        BlockerCode.B002,
                        stage=FailureStage.RAW_BOUNDARY,
                        field_path=path + ".side_binding",
                    )
                )
            if side is SideBinding.SHELL_SIDE and side in seen_sides:
                blockers.append(
                    make_blocker(
                        BlockerCode.B003,
                        stage=FailureStage.RAW_BOUNDARY,
                        field_path=path + ".side_binding",
                    )
                )
            seen_sides.append(side)
        stream_id = _to_required_string(
            _mapping_value(raw_stream, "stream_id"), BlockerCode.B005, path + ".stream_id", blockers
        )
        fluid = _to_required_string(
            _mapping_value(raw_stream, "fluid_or_service_identity"),
            BlockerCode.B006,
            path + ".fluid_or_service_identity",
            blockers,
        )
        phase_raw = _mapping_value(raw_stream, "phase_assertion")
        if not isinstance(phase_raw, str):
            blockers.append(
                make_blocker(
                    BlockerCode.B007 if phase_raw is None else BlockerCode.B008,
                    stage=FailureStage.RAW_BOUNDARY,
                    field_path=path + ".phase_assertion",
                    details=(("value", str(phase_raw)),),
                )
            )
            phase = None
        else:
            try:
                phase = Task160PhaseAssertion(phase_raw)
            except (TypeError, ValueError):
                blockers.append(
                    make_blocker(
                        BlockerCode.B007 if phase_raw is None else BlockerCode.B008,
                        stage=FailureStage.RAW_BOUNDARY,
                        field_path=path + ".phase_assertion",
                        details=(("value", str(phase_raw)),),
                    )
                )
                phase = None
        temperature = _to_decimal(
            _mapping_value(raw_stream, "inlet_temperature_K"),
            path + ".inlet_temperature_K",
            blockers,
            positive=True,
        )
        pressure_raw = _mapping_value(raw_stream, "inlet_pressure_Pa_absolute")
        pressure = (
            None
            if pressure_raw is None
            else _to_decimal(
                pressure_raw, path + ".inlet_pressure_Pa_absolute", blockers, positive=True
            )
        )
        mass = _to_decimal(
            _mapping_value(raw_stream, "mass_flow_kg_s"),
            path + ".mass_flow_kg_s",
            blockers,
            positive=True,
        )
        snapshot = _build_snapshot(
            _mapping_value(raw_stream, "property_snapshot"), blockers, path + ".property_snapshot"
        )
        provenance = _build_provenance(
            _mapping_value(raw_stream, "provenance"), blockers, path + ".provenance"
        )
        if (
            phase is not None
            and temperature is not None
            and mass is not None
            and snapshot is not None
            and provenance is not None
            and stream_id is not None
            and fluid is not None
            and side is not None
        ):
            if phase.value not in {"SINGLE_PHASE_LIQUID", "SINGLE_PHASE_GAS"}:
                blockers.append(
                    make_blocker(
                        BlockerCode.B008,
                        stage=FailureStage.RAW_BOUNDARY,
                        field_path=path + ".phase_assertion",
                    )
                )
            if (
                snapshot.property_evaluation_context.query_type
                is PropertyEvaluationQueryType.TEMPERATURE_AND_PRESSURE
                and pressure is None
            ):
                blockers.append(
                    make_blocker(
                        BlockerCode.B017,
                        stage=FailureStage.RAW_BOUNDARY,
                        field_path=path + ".inlet_pressure_Pa_absolute",
                    )
                )
            else:
                try:
                    strict_streams.append(
                        RatingStreamInput(
                            stream_id,
                            side,
                            fluid,
                            phase,
                            temperature,
                            pressure,
                            mass,
                            snapshot,
                            provenance,
                        )
                    )
                except ValueError:
                    blockers.append(
                        make_blocker(
                            BlockerCode.B009, stage=FailureStage.RAW_BOUNDARY, field_path=path
                        )
                    )

    envelope = _build_envelope(request.envelope_authority, blockers)
    adapter_values = request.adapter_evidence
    if adapter_values is None or type(adapter_values) not in (tuple, list) or not adapter_values:
        blockers.append(
            make_blocker(
                BlockerCode.B025, stage=FailureStage.RAW_BOUNDARY, field_path="adapter_evidence"
            )
        )
        strict_adapters: list[Task160AdapterEvidence] = []
    else:
        strict_adapters = [
            item
            for index, item in (
                (index, _build_adapter(raw_item, blockers, f"adapter_evidence[{index}]"))
                for index, raw_item in enumerate(adapter_values)
            )
            if item is not None
        ]
    deferred = _to_strings(request.deferred_capabilities, "deferred_capabilities", blockers)
    aggregate_provenance = _build_provenance(request.provenance, blockers, "provenance")
    if deferred is None:
        deferred = ()
    if (
        envelope is not None
        and len(strict_streams) == 2
        and aggregate_provenance is not None
        and len(strict_adapters) == len(adapter_values or ())
    ):
        try:
            strict = Task160Request(
                schema_version=schema_version,
                task160_version=task_version,
                implementation_software_version=software_version,
                stream_records=(strict_streams[0], strict_streams[1]),
                envelope_authority=envelope,
                adapter_evidence=tuple(strict_adapters),
                deferred_capabilities=deferred,
                provenance_inputs=aggregate_provenance,
            )
        except ValueError:
            strict = None
            blockers.append(
                make_blocker(
                    BlockerCode.B018, stage=FailureStage.RAW_BOUNDARY, field_path="request"
                )
            )
    else:
        strict = None
    return strict, sort_blockers(blockers)


def _raw_deferred_capabilities(raw: Task160RawRequest) -> tuple[str, ...]:
    """Return only canonicalizable deferred capabilities for a raw artifact."""
    values = raw.deferred_capabilities
    if type(values) not in (list, tuple):
        return ()
    if any(type(item) is not str or not item for item in values):
        return ()
    result = tuple(values)
    if len(result) != len(set(result)):
        return ()
    return tuple(sorted(result))


def make_raw_boundary_blocked_result(
    raw: Task160RawRequest | Mapping[str, object],
    blockers: Sequence[Any],
    *,
    schema_version: str = TASK160_SCHEMA_VERSION,
    task160_version: str = TASK160_VERSION,
    implementation_software_version: str = TASK160_IMPLEMENTATION_SOFTWARE_VERSION,
) -> Task160RawBoundaryBlockedResult:
    projection = project_raw_request(raw)
    ordered = sort_blockers(blockers)
    projection_hash = raw_request_projection_hash(projection)
    deferred = _raw_deferred_capabilities(coerce_raw_request(raw))
    artifact_hash = raw_blocked_hash(
        schema_version=schema_version,
        task160_version=task160_version,
        implementation_software_version=implementation_software_version,
        failure_stage=FailureStage.RAW_BOUNDARY,
        raw_request_projection_hash=projection_hash,
        blockers=ordered,
        deferred_capabilities=deferred,
    )
    return Task160RawBoundaryBlockedResult(
        schema_version=schema_version,
        task160_version=task160_version,
        implementation_software_version=implementation_software_version,
        failure_stage=FailureStage.RAW_BOUNDARY,
        raw_request_projection=projection,
        raw_request_projection_hash=projection_hash,
        blockers=ordered,
        warnings=(),
        deferred_capabilities=deferred,
        blocked_result_hash=artifact_hash,
        blocked_result_id=raw_blocked_result_id(artifact_hash),
    )


__all__ = [
    "RAW_RECORD_FIELDS",
    "RawIngressStructuralError",
    "build_strict_request",
    "coerce_raw_request",
    "make_raw_boundary_blocked_result",
    "project_raw_request",
]
