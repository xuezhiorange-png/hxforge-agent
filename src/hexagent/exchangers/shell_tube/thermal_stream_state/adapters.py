"""Task026 evidence and Task032 shell mass-flow admission adapters."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import Any

from hexagent.exchangers.shell_tube.shell_side_flow_state.models import ShellSideMassFlowAuthority

from .errors import BlockerCode, make_blocker
from .models import (
    FailureStage,
    PropertySnapshotIdentityScheme,
    SideBinding,
    Task160RawAdapterEvidence,
    Task160RawPropertySnapshotInput,
    Task160RawStreamInput,
)

TASK026_ADMITTED_FIELDS: tuple[str, ...] = (
    "property_snapshot_identity",
    "property_source_identity",
    "property_source_version",
    "source_result_identity",
)
TASK026_REJECTED_FIELDS: tuple[str, ...] = (
    "fluid_or_service_identity",
    "inlet_pressure_Pa_absolute",
    "inlet_temperature_K",
    "mass_flow_kg_s",
    "phase_assertion",
    "property_evaluation_context",
    "side_binding",
    "specific_heat_J_kg_K",
    "stream_id",
)
TASK032_ADMITTED_FIELDS: tuple[str, ...] = (
    "fluid_or_service_identity",
    "mass_flow_kg_s",
    "side_binding",
    "stream_id",
)
TASK032_REJECTED_FIELDS: tuple[str, ...] = (
    "inlet_pressure_Pa_absolute",
    "inlet_temperature_K",
    "phase_assertion",
    "property_evaluation_context",
    "property_source_identity",
    "property_source_version",
    "property_snapshot_identity",
    "specific_heat_J_kg_K",
)


@dataclass(frozen=True)
class Task032ShellAdmissionInput:
    mass_flow_authority: ShellSideMassFlowAuthority
    explicit_rating_input: Task160RawStreamInput
    approved_property_snapshot: Task160RawPropertySnapshotInput


@dataclass(frozen=True)
class AdapterAdmissionBlocked:
    blocker: Any


def _identity_parts(snapshot: Task160RawPropertySnapshotInput) -> tuple[object, object]:
    value = snapshot.property_snapshot_identity
    if isinstance(value, dict):
        return value.get("scheme"), value.get("value")
    return getattr(value, "scheme", None), getattr(value, "value", value)


def _decimal_value(value: object) -> Decimal | None:
    if isinstance(value, Decimal):
        return value
    if type(value) is int and not isinstance(value, bool):
        return Decimal(value)
    if type(value) is str:
        try:
            return Decimal(value)
        except InvalidOperation:
            return None
    return None


def admit_task032_shell_mass_flow(
    raw_stream_input: Task160RawStreamInput,
    approved_property_snapshot: Task160RawPropertySnapshotInput,
    mass_flow_authority: ShellSideMassFlowAuthority,
) -> Task160RawStreamInput | AdapterAdmissionBlocked:
    """Admit only the fields whose semantics are frozen by TASK032.

    This function consumes a value object already produced by TASK032.  It
    never executes TASK032, calls a property provider, derives flow, or
    interprets bulk state as rating state.
    """
    if not isinstance(mass_flow_authority, ShellSideMassFlowAuthority):
        raise TypeError("mass_flow_authority must be ShellSideMassFlowAuthority")
    if not isinstance(raw_stream_input, Task160RawStreamInput):
        raise TypeError("raw_stream_input must be Task160RawStreamInput")
    if not isinstance(approved_property_snapshot, Task160RawPropertySnapshotInput):
        raise TypeError("approved_property_snapshot must be Task160RawPropertySnapshotInput")

    identity_scheme, identity_value = _identity_parts(approved_property_snapshot)
    if identity_scheme not in (PropertySnapshotIdentityScheme.SHA256_HEX, "SHA256_HEX"):
        return AdapterAdmissionBlocked(
            make_blocker(
                BlockerCode.B026,
                stage=FailureStage.RAW_BOUNDARY,
                field_path="property_snapshot_identity",
            )
        )
    if (
        type(identity_value) is not str
        or mass_flow_authority.property_snapshot_hash != identity_value
    ):
        return AdapterAdmissionBlocked(
            make_blocker(
                BlockerCode.B026,
                stage=FailureStage.RAW_BOUNDARY,
                field_path="property_snapshot_identity",
            )
        )

    conflicts: list[str] = []
    if raw_stream_input.stream_id not in (None, "", mass_flow_authority.shell_side_stream_id):
        conflicts.append("stream_id")
    if raw_stream_input.fluid_or_service_identity not in (
        None,
        "",
        mass_flow_authority.shell_side_fluid_id,
    ):
        conflicts.append("fluid_or_service_identity")
    if raw_stream_input.side_binding not in (None, "", SideBinding.SHELL_SIDE, "SHELL_SIDE"):
        conflicts.append("side_binding")
    explicit_mass = _decimal_value(raw_stream_input.mass_flow_kg_s)
    authority_mass = _decimal_value(mass_flow_authority.mass_flow_rate_kg_s)
    if raw_stream_input.mass_flow_kg_s not in (None, "") and (
        explicit_mass is None or authority_mass is None or explicit_mass != authority_mass
    ):
        conflicts.append("mass_flow_kg_s")
    if conflicts:
        return AdapterAdmissionBlocked(
            make_blocker(
                BlockerCode.B020,
                stage=FailureStage.RAW_BOUNDARY,
                field_path=conflicts[0],
                details=(("conflicting_fields", ",".join(sorted(conflicts))),),
            )
        )

    # Only the four admitted fields are filled.  Rating T/P, phase, Cp,
    # property context and property identity remain untouched.
    return replace(
        raw_stream_input,
        stream_id=mass_flow_authority.shell_side_stream_id,
        fluid_or_service_identity=mass_flow_authority.shell_side_fluid_id,
        side_binding=SideBinding.SHELL_SIDE,
        mass_flow_kg_s=mass_flow_authority.mass_flow_rate_kg_s,
    )


def build_task026_evidence(
    task026_result: object,
    property_snapshot: object,
    *,
    evidence_hash: str,
    source_evidence_refs: tuple[str, ...],
) -> Task160RawAdapterEvidence:
    """Record Task026 evidence without admitting incompatible rating fields."""
    source_result_identity = getattr(task026_result, "result_id", None)
    source_task = "TASK026"
    source_identity = getattr(property_snapshot, "property_snapshot_hash", None)
    if source_identity is None:
        source_identity = getattr(property_snapshot, "property_snapshot_identity", None)
    _ = source_identity  # evidence is deliberately not used as rating state
    return Task160RawAdapterEvidence(
        adapter_id="TASK026_TUBE_EVIDENCE_ONLY_ADAPTER_V1",
        source_task_id=source_task,
        source_result_identity=source_result_identity,
        admitted_fields=TASK026_ADMITTED_FIELDS,
        rejected_fields=TASK026_REJECTED_FIELDS,
        source_evidence_refs=source_evidence_refs,
        evidence_hash=evidence_hash,
    )


__all__ = [
    "AdapterAdmissionBlocked",
    "TASK026_ADMITTED_FIELDS",
    "TASK026_REJECTED_FIELDS",
    "TASK032_ADMITTED_FIELDS",
    "TASK032_REJECTED_FIELDS",
    "Task032ShellAdmissionInput",
    "admit_task032_shell_mass_flow",
    "build_task026_evidence",
]
