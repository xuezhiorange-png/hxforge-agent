"""Raw-ingress and immutable TASK160 model coverage."""

from __future__ import annotations

from dataclasses import fields
from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.thermal_stream_state.errors import BlockerCode
from hexagent.exchangers.shell_tube.thermal_stream_state.ingress import (
    RawIngressStructuralError,
    project_raw_request,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.models import (
    PropertyEvaluationBasis,
    PropertyEvaluationContext,
    PropertyEvaluationQueryType,
    PropertySnapshotIdentity,
    PropertySnapshotIdentityScheme,
    RawProjectionKind,
    Task160RawPropertySnapshotIdentity,
    Task160RawRequest,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.service import validate_request


def _hash(letter: str) -> str:
    return letter * 64


def make_r607_raw(**overrides: object) -> dict[str, object]:
    """Build the literal R607 request; callers may replace top-level keys."""
    tube_snapshot = {
        "specific_heat_J_kg_K": "4180",
        "property_source_identity": "CoolProp-6.6",
        "property_source_version": "6.6.0",
        "property_snapshot_identity": {"scheme": "SHA256_HEX", "value": _hash("a")},
        "property_evaluation_context": {
            "evaluation_basis": "RECORDED_PROPERTY_SNAPSHOT",
            "query_type": "TEMPERATURE_ONLY",
            "evaluation_temperature_K": "390.15",
            "evaluation_pressure_Pa_absolute": None,
            "context_identity": "ctx-tube-390.15",
        },
    }
    shell_snapshot = {
        "specific_heat_J_kg_K": "3500",
        "property_source_identity": "CoolProp-6.6",
        "property_source_version": "6.6.0",
        "property_snapshot_identity": {"scheme": "SHA256_HEX", "value": _hash("a")},
        "property_evaluation_context": {
            "evaluation_basis": "RECORDED_PROPERTY_SNAPSHOT",
            "query_type": "TEMPERATURE_AND_PRESSURE",
            "evaluation_temperature_K": "300.15",
            "evaluation_pressure_Pa_absolute": "101325",
            "context_identity": "ctx-shell-300.15-101325",
        },
    }
    raw: dict[str, object] = {
        "schema_version": "task160.schema.v1",
        "task160_version": "task160.v1",
        "implementation_software_version": "task160.local-implementation.v1",
        "stream_records": [
            {
                "stream_id": "stream-tube-A",
                "side_binding": "TUBE_SIDE",
                "fluid_or_service_identity": "water",
                "phase_assertion": "SINGLE_PHASE_LIQUID",
                "inlet_temperature_K": "390.15",
                "inlet_pressure_Pa_absolute": None,
                "mass_flow_kg_s": "2.5",
                "property_snapshot": tube_snapshot,
                "provenance": {
                    "producer_identity": ["TASK026"],
                    "upstream_identity_hashes": [_hash("b")],
                    "source_evidence_refs": ["task026-property-snapshot-0001"],
                    "adapter_evidence_refs": [_hash("e")],
                },
            },
            {
                "stream_id": "stream-shell-B",
                "side_binding": "SHELL_SIDE",
                "fluid_or_service_identity": "glycol",
                "phase_assertion": "SINGLE_PHASE_LIQUID",
                "inlet_temperature_K": "300.15",
                "inlet_pressure_Pa_absolute": "101325",
                "mass_flow_kg_s": "1.25",
                "property_snapshot": shell_snapshot,
                "provenance": {
                    "producer_identity": ["TASK032"],
                    "upstream_identity_hashes": [_hash("c")],
                    "source_evidence_refs": ["task032-mass-flow-authority-0001"],
                    "adapter_evidence_refs": [_hash("f")],
                },
            },
        ],
        "envelope_authority": {
            "construction_family": "FIXED_TUBESHEET",
            "shell_pass_count": 1,
            "tube_pass_count": 1,
            "authority_source_identity": "HXForge-v0.5-envelope",
            "authority_source_version": "v0.5",
            "authority_identity": "env-160-fixed-tubesheet-1x1",
            "evidence_refs": ["envelope-authority-0001"],
        },
        "adapter_evidence": [
            {
                "adapter_id": "TASK026_TUBE_EVIDENCE_ONLY_ADAPTER_V1",
                "source_task_id": "TASK026",
                "source_result_identity": "task026-result-0001",
                "admitted_fields": [
                    "property_snapshot_identity",
                    "property_source_identity",
                    "property_source_version",
                    "source_result_identity",
                ],
                "rejected_fields": [
                    "fluid_or_service_identity",
                    "inlet_pressure_Pa_absolute",
                    "inlet_temperature_K",
                    "mass_flow_kg_s",
                    "phase_assertion",
                    "property_evaluation_context",
                    "side_binding",
                    "specific_heat_J_kg_K",
                    "stream_id",
                ],
                "source_evidence_refs": ["task026-evidence-0001"],
                "evidence_hash": _hash("e"),
            },
            {
                "adapter_id": "TASK032_SHELL_MASS_FLOW_AUTHORITY_ADAPTER_V1",
                "source_task_id": "TASK032",
                "source_result_identity": None,
                "admitted_fields": [
                    "fluid_or_service_identity",
                    "mass_flow_kg_s",
                    "side_binding",
                    "stream_id",
                ],
                "rejected_fields": [
                    "inlet_pressure_Pa_absolute",
                    "inlet_temperature_K",
                    "phase_assertion",
                    "property_evaluation_context",
                    "property_source_identity",
                    "property_source_version",
                    "property_snapshot_identity",
                    "specific_heat_J_kg_K",
                ],
                "source_evidence_refs": ["task032-adapter-evidence-0001"],
                "evidence_hash": _hash("f"),
            },
        ],
        "deferred_capabilities": [
            "TASK161_PERFORMANCE_METHOD",
            "TASK162_THERMAL_CLOSURE",
            "TASK163_COMPOSITION",
        ],
        "provenance": {
            "producer_identity": ["TASK026", "TASK032"],
            "upstream_identity_hashes": [_hash("b"), _hash("c")],
            "source_evidence_refs": [
                "envelope-authority-0001",
                "task026-evidence-0001",
                "task026-property-snapshot-0001",
                "task032-adapter-evidence-0001",
                "task032-mass-flow-authority-0001",
            ],
            "adapter_evidence_refs": [_hash("e"), _hash("f")],
        },
    }
    raw.update(overrides)
    return raw


def _blocker_codes(raw: object) -> tuple[str, ...]:
    return tuple(item.code for item in validate_request(raw).blockers)


def test_raw_models_are_frozen_and_allow_missing_authority() -> None:
    assert all(field.default is None for field in fields(Task160RawRequest))
    assert Task160RawPropertySnapshotIdentity() == Task160RawPropertySnapshotIdentity()
    with pytest.raises((AttributeError, TypeError)):
        Task160RawRequest().stream_records = ()  # type: ignore[misc]


def test_raw_projection_has_typed_nested_tree() -> None:
    projection = project_raw_request(make_r607_raw())
    assert projection.schema_version == "task160.raw-projection.v1"
    assert projection.root.kind is RawProjectionKind.RECORD
    stream_records = projection.root.children[3]
    assert stream_records.kind is RawProjectionKind.SEQUENCE
    assert stream_records.children[0].field_name == "item-000000"
    snapshot = stream_records.children[0].children[7]
    identity = snapshot.children[3]
    assert identity.kind is RawProjectionKind.RECORD
    assert tuple(item.field_name for item in identity.children) == ("scheme", "value")


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("stream_id", "B005"),
        ("fluid_or_service_identity", "B006"),
        ("phase_assertion", "B007"),
        ("inlet_temperature_K", "B009"),
        ("mass_flow_kg_s", "B011"),
    ],
)
def test_raw_missing_stream_authority_is_reachable(field: str, code: str) -> None:
    raw = make_r607_raw()
    stream = dict(raw["stream_records"][0])  # type: ignore[index]
    stream[field] = None
    raw["stream_records"] = [stream, raw["stream_records"][1]]  # type: ignore[index]
    assert code in _blocker_codes(raw)


def test_raw_missing_snapshot_authority_is_reachable() -> None:
    raw = make_r607_raw()
    stream = dict(raw["stream_records"][0])  # type: ignore[index]
    stream["property_snapshot"] = None
    raw["stream_records"] = [stream, raw["stream_records"][1]]  # type: ignore[index]
    assert BlockerCode.B015.value in _blocker_codes(raw)


def test_bool_and_float_are_structural_raw_errors() -> None:
    raw = make_r607_raw()
    stream = dict(raw["stream_records"][0])  # type: ignore[index]
    stream["inlet_temperature_K"] = 1.0
    raw["stream_records"] = [stream, raw["stream_records"][1]]  # type: ignore[index]
    with pytest.raises(RawIngressStructuralError):
        project_raw_request(raw)

    stream["inlet_temperature_K"] = True
    raw["stream_records"] = [stream, raw["stream_records"][1]]  # type: ignore[index]
    with pytest.raises(RawIngressStructuralError):
        project_raw_request(raw)


@pytest.mark.parametrize(
    "literal", ["NaN", "-NaN", "sNaN", "Infinity", "-Infinity", "not-a-number"]
)
def test_raw_nonfinite_or_invalid_numeric_strings_are_projectable(literal: str) -> None:
    raw = make_r607_raw()
    stream = dict(raw["stream_records"][0])  # type: ignore[index]
    stream["inlet_temperature_K"] = literal
    raw["stream_records"] = [stream, raw["stream_records"][1]]  # type: ignore[index]
    projection = project_raw_request(raw)
    node = projection.root.children[3].children[0].children[4]
    assert node.kind is RawProjectionKind.INVALID_NUMERIC_LITERAL
    assert node.scalar_payload == literal


def test_property_context_has_closed_semantics() -> None:
    context = PropertyEvaluationContext(
        evaluation_basis=PropertyEvaluationBasis.RECORDED_PROPERTY_SNAPSHOT,
        query_type=PropertyEvaluationQueryType.TEMPERATURE_ONLY,
        evaluation_temperature_K=Decimal("300.15"),
        evaluation_pressure_Pa_absolute=None,
        context_identity="ctx",
    )
    assert context.evaluation_pressure_Pa_absolute is None
    with pytest.raises(ValueError):
        PropertyEvaluationContext(
            context.evaluation_basis,
            PropertyEvaluationQueryType.TEMPERATURE_ONLY,
            context.evaluation_temperature_K,
            Decimal("1"),
            context.context_identity,
        )


def test_snapshot_identity_scheme_is_part_of_value_object() -> None:
    sha = PropertySnapshotIdentity(PropertySnapshotIdentityScheme.SHA256_HEX, _hash("a"))
    opaque = PropertySnapshotIdentity(PropertySnapshotIdentityScheme.OPAQUE_REPRODUCIBLE, "same")
    assert sha != opaque
