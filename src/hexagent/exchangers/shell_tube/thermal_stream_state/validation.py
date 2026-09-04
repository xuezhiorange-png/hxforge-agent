"""TASK160 strict validation, role resolution, and applicability ledgers."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from decimal import Decimal

from .errors import BlockerCode, make_blocker, sort_blockers
from .models import (
    ApplicabilityCheck,
    ApplicabilityCheckId,
    ApplicabilityLedger,
    ApplicabilityStatus,
    CapacityRatedStream,
    CompletenessCheck,
    CompletenessCheckId,
    CompletenessLedger,
    CompletenessStatus,
    FailureStage,
    RoleResolvedRatingStream,
    SideBinding,
    Task160Blocker,
    Task160Request,
    ThermalRole,
    ValidatedRatingStreamState,
)


def validate_base_streams(request: Task160Request) -> tuple[ValidatedRatingStreamState, ...]:
    """Construct validated stream-state wrappers after raw admission."""
    records = request.stream_records
    if not isinstance(records, tuple) or len(records) != 2:
        raise ValueError("exactly two stream records are required")
    return tuple(ValidatedRatingStreamState(item) for item in records)


def resolve_thermal_roles(
    *states: ValidatedRatingStreamState,
) -> tuple[RoleResolvedRatingStream, ...]:
    """Resolve roles from only validated inlet temperatures.

    The input is intentionally the pre-role ``ValidatedRatingStreamState``;
    a role-populated result is never required to resolve its own role.
    """
    if len(states) != 2 or any(not isinstance(item, ValidatedRatingStreamState) for item in states):
        raise ValueError("role resolution requires exactly two validated stream states")
    first, second = states
    if first.inlet_temperature_K == second.inlet_temperature_K:
        raise ValueError(BlockerCode.B010.value)
    if first.inlet_temperature_K > second.inlet_temperature_K:
        roles = (ThermalRole.HOT, ThermalRole.COLD)
    else:
        roles = (ThermalRole.COLD, ThermalRole.HOT)
    return tuple(
        RoleResolvedRatingStream(state, role) for state, role in zip(states, roles, strict=True)
    )


def make_applicability_ledger(
    request: Task160Request,
    states: Sequence[ValidatedRatingStreamState],
) -> ApplicabilityLedger:
    """Build the complete ordered A01-A11 applicability evidence ledger."""
    records = request.stream_records
    blockers: list[Task160Blocker] = []
    checks: list[ApplicabilityCheck] = []

    def add(
        check_id: ApplicabilityCheckId,
        passed: bool,
        refs: tuple[str, ...],
        details: tuple[tuple[str, str], ...],
        failed: Iterable[Task160Blocker] = (),
    ) -> None:
        local = tuple(failed)
        checks.append(
            ApplicabilityCheck(check_id, passed, tuple(item.code for item in local), refs, details)
        )
        blockers.extend(local)

    add(
        ApplicabilityCheckId.A01_TWO_STREAMS,
        len(records) == 2,
        ("stream-records-0001",),
        (("stream_count", str(len(records))),),
        ()
        if len(records) == 2
        else (
            make_blocker(
                BlockerCode.B001, stage=FailureStage.APPLICABILITY, field_path="stream_records"
            ),
        ),
    )
    tube_count = sum(
        getattr(item, "side_binding", None) is SideBinding.TUBE_SIDE for item in records
    )
    shell_count = sum(
        getattr(item, "side_binding", None) is SideBinding.SHELL_SIDE for item in records
    )
    add(
        ApplicabilityCheckId.A02_EXACTLY_ONE_TUBE_SIDE,
        tube_count == 1,
        tuple(item.stream_id for item in records if hasattr(item, "stream_id")),
        (("tube_side_count", str(tube_count)),),
        ()
        if tube_count == 1
        else (
            make_blocker(
                BlockerCode.B002 if tube_count > 1 else BlockerCode.B004,
                stage=FailureStage.APPLICABILITY,
                field_path="side_binding",
            ),
        ),
    )
    add(
        ApplicabilityCheckId.A03_EXACTLY_ONE_SHELL_SIDE,
        shell_count == 1,
        tuple(item.stream_id for item in records if hasattr(item, "stream_id")),
        (("shell_side_count", str(shell_count)),),
        ()
        if shell_count == 1
        else (
            make_blocker(
                BlockerCode.B003 if shell_count > 1 else BlockerCode.B004,
                stage=FailureStage.APPLICABILITY,
                field_path="side_binding",
            ),
        ),
    )
    phases = tuple(item.input.phase_assertion.value for item in states)
    add(
        ApplicabilityCheckId.A04_SINGLE_PHASE_AUTHORITY,
        len(phases) == 2,
        tuple(f"phase-{item.stream_id.removeprefix('stream-')}" for item in states),
        (("phase_values", ",".join(phases)),),
    )
    snapshots = tuple(item.input.property_snapshot for item in states)
    snapshot_refs = tuple(
        "task026-property-snapshot-0001"
        if item.side_binding is SideBinding.TUBE_SIDE
        else "task032-property-snapshot-0001"
        for item in states
    )
    add(
        ApplicabilityCheckId.A05_CONSTANT_PROPERTY_SNAPSHOT,
        len(snapshots) == 2,
        snapshot_refs,
        (("property_model", "RATING_LEVEL_FIXED_SNAPSHOT"),),
    )
    envelope = request.envelope_authority
    envelope_ok = (
        envelope.construction_family.value == "FIXED_TUBESHEET"
        and envelope.shell_pass_count == 1
        and envelope.tube_pass_count == 1
        and bool(envelope.authority_identity)
        and bool(envelope.evidence_refs)
    )
    add(
        ApplicabilityCheckId.A06_FIXED_GEOMETRY_V05_ENVELOPE,
        envelope_ok,
        tuple(envelope.evidence_refs),
        (("envelope", "fixed-tubesheet-1x1"),),
        ()
        if envelope_ok
        else (
            make_blocker(
                BlockerCode.B022, stage=FailureStage.APPLICABILITY, field_path="envelope_authority"
            ),
        ),
    )
    inlet_ok = all(
        item.input.inlet_temperature_K.is_finite() and item.input.inlet_temperature_K > 0
        for item in states
    )
    add(
        ApplicabilityCheckId.A07_FINITE_VALID_INLET_STATE,
        inlet_ok,
        tuple(item.input.stream_id for item in states),
        (("finite_inlet_state", str(inlet_ok).lower()),),
        ()
        if inlet_ok
        else (
            make_blocker(
                BlockerCode.B009, stage=FailureStage.APPLICABILITY, field_path="inlet_temperature_K"
            ),
        ),
    )
    flow_ok = all(
        item.input.mass_flow_kg_s.is_finite() and item.input.mass_flow_kg_s > 0 for item in states
    )
    add(
        ApplicabilityCheckId.A08_POSITIVE_MASS_FLOW,
        flow_ok,
        tuple(item.input.stream_id for item in states),
        (("mass_flow_positive", str(flow_ok).lower()),),
        ()
        if flow_ok
        else (
            make_blocker(
                BlockerCode.B011, stage=FailureStage.APPLICABILITY, field_path="mass_flow_kg_s"
            ),
        ),
    )
    cp_ok = all(
        item.input.property_snapshot.specific_heat_J_kg_K.is_finite()
        and item.input.property_snapshot.specific_heat_J_kg_K > 0
        for item in states
    )
    add(
        ApplicabilityCheckId.A09_POSITIVE_CP,
        cp_ok,
        snapshot_refs,
        (("cp_positive", str(cp_ok).lower()),),
        ()
        if cp_ok
        else (
            make_blocker(
                BlockerCode.B012,
                stage=FailureStage.APPLICABILITY,
                field_path="specific_heat_J_kg_K",
            ),
        ),
    )
    property_ok = all(
        bool(item.input.property_snapshot.property_source_identity)
        and bool(item.input.property_snapshot.property_source_version)
        and bool(item.input.property_snapshot.property_snapshot_identity.value)
        and bool(item.input.property_snapshot.property_evaluation_context.context_identity)
        for item in states
    )
    add(
        ApplicabilityCheckId.A10_APPROVED_PROPERTY_AUTHORITY,
        property_ok,
        ("task026-property-snapshot-0001", "task032-mass-flow-authority-0001"),
        (("approved_property_authority", str(property_ok).lower()),),
        ()
        if property_ok
        else (
            make_blocker(
                BlockerCode.B013, stage=FailureStage.APPLICABILITY, field_path="property_snapshot"
            ),
        ),
    )
    provenance_ok = bool(request.provenance_inputs) and all(
        bool(item.input.provenance_inputs.source_evidence_refs) for item in states
    )
    add(
        ApplicabilityCheckId.A11_COMPLETE_PROVENANCE,
        provenance_ok,
        (
            "envelope-authority-0001",
            "task026-property-snapshot-0001",
            "task032-mass-flow-authority-0001",
        )
        if provenance_ok
        else (),
        (("provenance_complete", str(provenance_ok).lower()),),
        ()
        if provenance_ok
        else (
            make_blocker(
                BlockerCode.B018, stage=FailureStage.APPLICABILITY, field_path="provenance"
            ),
        ),
    )
    ordered = sort_blockers(blockers)
    return ApplicabilityLedger(
        status=ApplicabilityStatus.APPLICABLE
        if not ordered and all(item.passed for item in checks)
        else ApplicabilityStatus.NOT_APPLICABLE,
        checks=tuple(checks),
        blockers=ordered,
    )


def make_completeness_ledger(
    request: Task160Request,
    rated_streams: Sequence[CapacityRatedStream],
    *,
    c_dot_hot_W_K: Decimal,
    c_dot_cold_W_K: Decimal,
    applicability: ApplicabilityLedger,
    identity_inputs_ready: bool,
) -> CompletenessLedger:
    """Build C01-C16 after Cdot and pre-result identity inputs exist."""
    records = tuple(rated_streams)
    blockers: list[Task160Blocker] = []
    checks: list[CompletenessCheck] = []
    stream_ids = tuple(item.stream_id for item in records)
    phase_refs = tuple(f"phase-{item.stream_id.removeprefix('stream-')}" for item in records)
    snapshot_refs = tuple(
        "task026-property-snapshot-0001"
        if item.side_binding is SideBinding.TUBE_SIDE
        else "task032-property-snapshot-0001"
        for item in records
    )

    def add(
        check_id: CompletenessCheckId,
        passed: bool,
        refs: tuple[str, ...],
        details: tuple[tuple[str, str], ...],
        failed: Iterable[Task160Blocker] = (),
    ) -> None:
        local = tuple(failed)
        checks.append(
            CompletenessCheck(check_id, passed, tuple(item.code for item in local), refs, details)
        )
        blockers.extend(local)

    add(
        CompletenessCheckId.C01_STREAM_RECORD_COUNT,
        len(records) == 2,
        stream_ids,
        (("stream_record_count", str(len(records))),),
        ()
        if len(records) == 2
        else (
            make_blocker(
                BlockerCode.B030, stage=FailureStage.COMPLETENESS, field_path="stream_records"
            ),
        ),
    )
    tube_count = sum(item.side_binding is SideBinding.TUBE_SIDE for item in records)
    shell_count = sum(item.side_binding is SideBinding.SHELL_SIDE for item in records)
    add(
        CompletenessCheckId.C02_SIDE_BINDINGS,
        tube_count == 1 and shell_count == 1,
        stream_ids,
        (("side_bindings", "TUBE_SIDE,SHELL_SIDE"),),
        ()
        if tube_count == 1 and shell_count == 1
        else (
            make_blocker(
                BlockerCode.B030, stage=FailureStage.COMPLETENESS, field_path="side_binding"
            ),
        ),
    )
    add(
        CompletenessCheckId.C03_STREAM_IDENTITIES,
        len(set(stream_ids)) == 2 and all(stream_ids),
        stream_ids,
        (("stream_identities", str(len(set(stream_ids)))),),
    )
    add(
        CompletenessCheckId.C04_FLUID_SERVICE_IDENTITIES,
        all(item.input_state.input.fluid_or_service_identity for item in records),
        stream_ids,
        (("fluid_service_identities", str(len(records))),),
    )
    add(
        CompletenessCheckId.C05_PHASE_ASSERTIONS,
        all(item.input_state.input.phase_assertion for item in records),
        phase_refs,
        (("phase_authorities", str(len(records))),),
    )
    add(
        CompletenessCheckId.C06_RATING_INLET_TEMPERATURES,
        all(item.input_state.input.inlet_temperature_K for item in records),
        stream_ids,
        (("rating_inlet_temperatures", str(len(records))),),
    )
    add(
        CompletenessCheckId.C07_MASS_FLOW_AUTHORITIES,
        all(item.input_state.input.mass_flow_kg_s > 0 for item in records),
        ("task026-explicit-tube-input-0001", "task032-mass-flow-authority-0001"),
        (("mass_flow_authorities", str(len(records))),),
    )
    add(
        CompletenessCheckId.C08_CP_AUTHORITIES,
        all(item.input_state.input.property_snapshot.specific_heat_J_kg_K > 0 for item in records),
        snapshot_refs,
        (("cp_authorities", str(len(records))),),
    )
    add(
        CompletenessCheckId.C09_HEAT_CAPACITY_RATES,
        c_dot_hot_W_K > 0 and c_dot_cold_W_K > 0,
        ("c-dot-hot-0001", "c-dot-cold-0001"),
        (("heat_capacity_rates", str(len(records))),),
        ()
        if c_dot_hot_W_K > 0 and c_dot_cold_W_K > 0
        else (
            make_blocker(
                BlockerCode.B029,
                stage=FailureStage.COMPLETENESS,
                field_path="heat_capacity_rate_W_K",
            ),
        ),
    )
    add(
        CompletenessCheckId.C10_CONDITIONAL_PRESSURE_CONTEXTS,
        all(
            item.input_state.input.property_snapshot.property_evaluation_context.query_type.value
            == "TEMPERATURE_ONLY"
            or (
                item.input_state.input.property_snapshot.property_evaluation_context.evaluation_pressure_Pa_absolute
                is not None
            )
            for item in records
        ),
        tuple(
            item.input_state.input.property_snapshot.property_evaluation_context.context_identity
            for item in records
        ),
        (("conditional_pressure", "recorded-contexts"),),
    )
    add(
        CompletenessCheckId.C11_PROPERTY_SOURCE_IDENTITIES,
        all(item.input_state.input.property_snapshot.property_source_identity for item in records),
        snapshot_refs,
        (("property_source_identities", str(len(records))),),
    )
    add(
        CompletenessCheckId.C12_PROPERTY_SOURCE_VERSIONS,
        all(item.input_state.input.property_snapshot.property_source_version for item in records),
        snapshot_refs,
        (("property_source_versions", str(len(records))),),
    )
    add(
        CompletenessCheckId.C13_PROPERTY_SNAPSHOT_IDENTITIES,
        all(
            item.input_state.input.property_snapshot.property_snapshot_identity.value
            for item in records
        ),
        snapshot_refs,
        (("property_snapshot_identities", str(len(records))),),
    )
    add(
        CompletenessCheckId.C14_PROPERTY_EVALUATION_CONTEXTS,
        all(
            item.input_state.input.property_snapshot.property_evaluation_context.context_identity
            for item in records
        ),
        tuple(
            item.input_state.input.property_snapshot.property_evaluation_context.context_identity
            for item in records
        ),
        (("property_evaluation_contexts", str(len(records))),),
    )
    prov = getattr(request, "provenance_inputs", None)
    prov_ok = bool(
        prov
        and prov.producer_identity
        and prov.upstream_identity_hashes
        and prov.source_evidence_refs
        and prov.adapter_evidence_refs
    )
    add(
        CompletenessCheckId.C15_PROVENANCE,
        prov_ok,
        ("task026-property-snapshot-0001", "task032-mass-flow-authority-0001") if prov_ok else (),
        (("provenance", "complete"),),
    )
    add(
        CompletenessCheckId.C16_DETERMINISTIC_NON_COMPLETENESS_IDENTITY_INPUT_READINESS,
        identity_inputs_ready,
        ("pre-result-identity-inputs",),
        (),
    )
    ordered = sort_blockers(blockers)
    return CompletenessLedger(
        status=CompletenessStatus.COMPLETE
        if not ordered and all(item.passed for item in checks)
        else CompletenessStatus.INCOMPLETE,
        checks=tuple(checks),
        blockers=ordered,
    )


__all__ = [
    "make_applicability_ledger",
    "make_completeness_ledger",
    "resolve_thermal_roles",
    "validate_base_streams",
]
