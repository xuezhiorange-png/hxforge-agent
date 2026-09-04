"""Task026/Task032 adapter-boundary tests for TASK160."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

from hexagent.exchangers.shell_tube.shell_side_flow_state.models import ShellSideMassFlowAuthority
from hexagent.exchangers.shell_tube.thermal_stream_state.adapters import (
    TASK026_ADMITTED_FIELDS,
    TASK026_REJECTED_FIELDS,
    TASK032_ADMITTED_FIELDS,
    TASK032_REJECTED_FIELDS,
    AdapterAdmissionBlocked,
    admit_task032_shell_mass_flow,
    build_task026_evidence,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.errors import BlockerCode
from hexagent.exchangers.shell_tube.thermal_stream_state.ingress import coerce_raw_request
from hexagent.exchangers.shell_tube.thermal_stream_state.models import (
    PropertySnapshotIdentityScheme,
    SideBinding,
    Task160RawPropertySnapshotIdentity,
    Task160RawPropertySnapshotInput,
    Task160RawStreamInput,
)


def _authority(snapshot_hash: str = "a" * 64) -> ShellSideMassFlowAuthority:
    return ShellSideMassFlowAuthority(
        schema_version="task032.shell-side-flow-state.v1",
        authority_profile_id="profile-032",
        shell_side_case_id="case-032",
        shell_side_stream_id="stream-shell-B",
        shell_side_fluid_id="glycol",
        rheology_model="NEWTONIAN",
        task020_configuration_id="config-020",
        task020_configuration_hash="b" * 64,
        task031_geometry_id="geometry-031",
        task031_geometry_hash="c" * 64,
        property_snapshot_hash=snapshot_hash,
        property_state_role="BULK_SHELL_SIDE_STATE",
        mass_flow_rate_kg_s=Decimal("1.25"),
        mass_flow_sign_convention="POSITIVE_ALONG_DECLARED_SHELL_SIDE_FLOW_DIRECTION",
        authority_source_id="TASK032",
        authority_source_version="v1",
        evidence_refs=("task032-mass-flow-authority-0001",),
        authority_hash="d" * 64,
    )


def _raw_stream() -> Task160RawStreamInput:
    return Task160RawStreamInput(
        stream_id=None,
        side_binding=None,
        fluid_or_service_identity=None,
        phase_assertion=None,
        inlet_temperature_K=None,
        inlet_pressure_Pa_absolute=None,
        mass_flow_kg_s=None,
        property_snapshot=None,
        provenance=None,
    )


def _snapshot(identity: object = None) -> Task160RawPropertySnapshotInput:
    return Task160RawPropertySnapshotInput(
        property_snapshot_identity=identity
        if identity is not None
        else Task160RawPropertySnapshotIdentity(
            PropertySnapshotIdentityScheme.SHA256_HEX, "a" * 64
        ),
    )


def test_task032_admits_only_the_frozen_mass_flow_fields() -> None:
    admitted = admit_task032_shell_mass_flow(_raw_stream(), _snapshot(), _authority())
    assert isinstance(admitted, Task160RawStreamInput)
    assert admitted.stream_id == "stream-shell-B"
    assert admitted.fluid_or_service_identity == "glycol"
    assert admitted.side_binding is SideBinding.SHELL_SIDE
    assert admitted.mass_flow_kg_s == Decimal("1.25")
    assert admitted.inlet_temperature_K is None
    assert admitted.inlet_pressure_Pa_absolute is None
    assert admitted.phase_assertion is None
    assert admitted.property_snapshot is None


def test_task032_explicit_conflict_fails_closed() -> None:
    raw = replace(_raw_stream(), stream_id="other-stream")
    blocked = admit_task032_shell_mass_flow(raw, _snapshot(), _authority())
    assert isinstance(blocked, AdapterAdmissionBlocked)
    assert blocked.blocker.code == BlockerCode.B020.value


def test_task032_opaque_snapshot_identity_cannot_auto_cross_bind() -> None:
    identity = Task160RawPropertySnapshotIdentity(
        PropertySnapshotIdentityScheme.OPAQUE_REPRODUCIBLE,
        "authority-snapshot-1",
    )
    blocked = admit_task032_shell_mass_flow(_raw_stream(), _snapshot(identity), _authority())
    assert isinstance(blocked, AdapterAdmissionBlocked)
    assert blocked.blocker.code == BlockerCode.B026.value


def test_task032_cross_binding_requires_exact_bare_sha256_value() -> None:
    blocked = admit_task032_shell_mass_flow(_raw_stream(), _snapshot("not-the-hash"), _authority())
    assert isinstance(blocked, AdapterAdmissionBlocked)
    assert blocked.blocker.code == BlockerCode.B026.value


def test_task026_evidence_is_explicitly_non_authoritative_for_rating_state() -> None:
    evidence = build_task026_evidence(
        SimpleNamespace(result_id="task026-result-0001"),
        SimpleNamespace(property_snapshot_hash="a" * 64),
        evidence_hash="e" * 64,
        source_evidence_refs=("task026-evidence-0001",),
    )
    assert evidence.source_task_id == "TASK026"
    assert evidence.admitted_fields == TASK026_ADMITTED_FIELDS
    assert evidence.rejected_fields == TASK026_REJECTED_FIELDS
    assert "mass_flow_kg_s" in evidence.rejected_fields
    assert "inlet_temperature_K" in evidence.rejected_fields
    assert "property_snapshot_identity" in evidence.admitted_fields


def test_task032_evidence_vocabulary_is_closed() -> None:
    raw = coerce_raw_request({"adapter_evidence": None})
    assert raw.adapter_evidence is None
    assert TASK032_ADMITTED_FIELDS == (
        "fluid_or_service_identity",
        "mass_flow_kg_s",
        "side_binding",
        "stream_id",
    )
    assert TASK032_REJECTED_FIELDS == (
        "inlet_pressure_Pa_absolute",
        "inlet_temperature_K",
        "phase_assertion",
        "property_evaluation_context",
        "property_source_identity",
        "property_source_version",
        "property_snapshot_identity",
        "specific_heat_J_kg_K",
    )
