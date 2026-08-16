"""TASK-027 F01 production boundary supplemental tests (8 frozen TEST_IDs)."""

from __future__ import annotations

import sys
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import patch

from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    FRICTION_FACTOR_QUANTUM,
    IMPLEMENTATION_SOFTWARE_VERSION,
    KIND_ENUM,
    KIND_STRING,
    KIND_TUPLE,
    PRESSURE_DROP_QUANTUM,
    ROUGHNESS_SCHEMA_VERSION,
    TASK027_BLOCKED_RESULT_SCHEMA_VERSION,
    TASK027_REQUEST_SCHEMA_VERSION,
    TASK027_SUCCESS_RESULT_SCHEMA_VERSION,
    AssertionState,
    BlockerCode,
    FlowDirectionAssertion,
    RoughnessMode,
    SmoothRoughnessAuthority,
    Task027BlockedResult,
    Task027SuccessResult,
    classify_reynolds,
    compute_blocked_result_hash,
    compute_laminar_friction_factor,
    compute_pressure_drop,
    compute_request_hash,
    compute_result_hash,
    compute_task027_friction_pressure_drop,
    compute_turbulent_friction_factor_safe,
    derive_result_id,
)
from hexagent.exchangers.shell_tube.tube_side.provenance import FrozenProvenance

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "release_demo"))


def _make_smooth_roughness_authority() -> SmoothRoughnessAuthority:
    from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
        _encode_tuple,
        frame_record,
        sha256_hex,
    )

    auth_template = SmoothRoughnessAuthority(
        schema_version=ROUGHNESS_SCHEMA_VERSION,
        authority_id="roughness-smooth-001",
        roughness_mode=RoughnessMode.EXPLICIT_SMOOTH_PIPE_ASSERTION,
        source_type="EXPLICIT_PROJECT_ASSUMPTION",
        source_id="assumption-smooth-001",
        source_version="2026-01",
        source_location="TASK-027 selection contract",
        permission_status="PASS",
        evidence_refs=("ref:task027-selection-r1",),
        authority_hash="placeholder",
    )
    fields = [
        ("schema_version", KIND_STRING, auth_template.schema_version.encode("utf-8")),
        ("authority_id", KIND_STRING, auth_template.authority_id.encode("utf-8")),
        ("roughness_mode", KIND_ENUM, auth_template.roughness_mode.value.encode("ascii")),
        ("source_type", KIND_ENUM, auth_template.source_type.encode("ascii")),
        ("source_id", KIND_STRING, auth_template.source_id.encode("utf-8")),
        ("source_version", KIND_STRING, auth_template.source_version.encode("utf-8")),
        ("source_location", KIND_STRING, auth_template.source_location.encode("utf-8")),
        ("permission_status", KIND_ENUM, auth_template.permission_status.encode("ascii")),
        ("evidence_refs", KIND_TUPLE, _encode_tuple(auth_template.evidence_refs)),
    ]
    authority_hash = sha256_hex(frame_record(ROUGHNESS_SCHEMA_VERSION, fields))
    return SmoothRoughnessAuthority(
        schema_version=auth_template.schema_version,
        authority_id=auth_template.authority_id,
        roughness_mode=auth_template.roughness_mode,
        source_type=auth_template.source_type,
        source_id=auth_template.source_id,
        source_version=auth_template.source_version,
        source_location=auth_template.source_location,
        permission_status=auth_template.permission_status,
        evidence_refs=auth_template.evidence_refs,
        authority_hash=authority_hash,
    )


def _produce_release_demo_upstream() -> tuple[Any, Any, Any]:
    """Produce actual TASK-025/TASK-026 outputs via v0.1 release-demo authority."""
    from v0_1_task020_to_task026 import (  # noqa: E402
        _build_t020_request,
        _build_t021_request,
        _build_t026_request,
        _stage_t025_valid,
    )

    from hexagent.exchangers.shell_tube import validate_request as t020_validate
    from hexagent.exchangers.shell_tube.tube_layout import validate_request as t021_validate
    from hexagent.exchangers.shell_tube.tube_side_thermal import (
        compute_tube_side_heat_transfer_coefficient,
    )

    t020_res = t020_validate(_build_t020_request())
    config = t020_res.configuration
    t021_payload = _build_t021_request(config)
    t021_res = t021_validate(
        t021_payload,
        software_version="v0.1.0-demo",
        git_commit="b11a7d46ac6a726c2bbdff85166c78e6753289a0",
    )
    layout = t021_res.layout
    prev_out_id = layout.layout_hash  # type: ignore[union-attr]
    _t025_record, _t025_in_id, _t025_out_id, t025_typed = _stage_t025_valid(
        layout, config, prev_out_id
    )
    req = _build_t026_request()
    t026_typed = compute_tube_side_heat_transfer_coefficient(req, t025_typed)
    return t025_typed, t026_typed, req.property_snapshot


def _default_assertions() -> dict[str, AssertionState | FlowDirectionAssertion]:
    return {
        "constant_density_path_assertion": AssertionState.TRUE,
        "zero_net_elevation_change_assertion": AssertionState.TRUE,
        "flow_direction_assertion": FlowDirectionAssertion.START_TO_END,
    }


def _replay_request_hash(
    *,
    task025: Any,
    task026: Any,
    property_snapshot: Any,
    roughness: SmoothRoughnessAuthority,
    profile_id: str = "profile-001",
) -> str:
    assertions = _default_assertions()
    return compute_request_hash(
        schema_version=TASK027_REQUEST_SCHEMA_VERSION,
        profile_id=profile_id,
        task025_result_hash=task025.result_hash,
        task026_result_hash=task026.result_hash,
        property_snapshot_hash=property_snapshot.property_snapshot_hash,
        constant_density_assertion=assertions["constant_density_path_assertion"].value,
        zero_elevation_assertion=assertions["zero_net_elevation_change_assertion"].value,
        flow_direction_assertion=assertions["flow_direction_assertion"].value,
        roughness_authority_hash=roughness.authority_hash,
    )


def _replay_blocked_result_hash(result: Task027BlockedResult) -> str:
    return compute_blocked_result_hash(
        schema_version=TASK027_BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id=result.profile_id,
        request_hash=result.request_hash,
        task025_hydraulic_authority_hash=result.task025_hydraulic_authority_hash,
        task025_result_hash=result.task025_result_hash,
        task026_result_hash=result.task026_result_hash,
        property_snapshot_hash=result.property_snapshot_hash,
        raw_request_projection=result.raw_request_projection,
        raw_upstream_blocked_projection=result.raw_upstream_blocked_projection,
        warnings=result.warnings,
        blockers=result.blockers,
        deferred_capabilities=result.deferred_capabilities,
        provenance=result.provenance,
    )


class TestT027F01Pb001ActualSuccess:
    """T027_F01_PB_001_ACTUAL_SUCCESS — actual upstream replay success."""

    def test_actual_success_from_release_demo_upstream(self) -> None:
        task025, task026, property_snapshot = _produce_release_demo_upstream()
        roughness = _make_smooth_roughness_authority()
        result = compute_task027_friction_pressure_drop(
            task025_result=task025,
            task026_result=task026,
            property_snapshot=property_snapshot,
            roughness_authority=roughness,
            **_default_assertions(),
        )
        assert isinstance(result, Task027SuccessResult)
        assert result.blockers == ()
        assert result.request_hash
        assert result.result_hash
        assert result.result_id == derive_result_id(result.result_hash)
        assert result.darcy_friction_factor > Decimal(0)
        assert result.straight_tube_friction_pressure_drop_pa > Decimal(0)


class TestT027F01Pb002UpstreamIdentityMismatchReachable:
    """T027_F01_PB_002_UPSTREAM_IDENTITY_MISMATCH_REACHABLE."""

    def test_upstream_identity_mismatch_from_production_entry(self) -> None:
        task025, task026, property_snapshot = _produce_release_demo_upstream()
        roughness = _make_smooth_roughness_authority()
        mismatched_task026 = replace(
            task026,
            upstream_geometry_hash="f" * 64,
        )
        result = compute_task027_friction_pressure_drop(
            task025_result=task025,
            task026_result=mismatched_task026,
            property_snapshot=property_snapshot,
            roughness_authority=roughness,
            **_default_assertions(),
        )
        assert isinstance(result, Task027BlockedResult)
        codes = [b.code for b in result.blockers]
        assert BlockerCode.BL_T027_UPSTREAM_IDENTITY_MISMATCH in codes
        assert any(b.field_path == ("upstream_geometry_hash",) for b in result.blockers)

        expected_request_hash = _replay_request_hash(
            task025=task025,
            task026=mismatched_task026,
            property_snapshot=property_snapshot,
            roughness=roughness,
        )
        assert result.request_hash == expected_request_hash
        assert result.task025_hydraulic_authority_hash == task025.hydraulic_authority_hash
        assert result.task025_result_hash == task025.result_hash
        assert result.task026_result_hash == mismatched_task026.result_hash
        assert result.property_snapshot_hash == property_snapshot.property_snapshot_hash
        assert isinstance(result.provenance, FrozenProvenance)
        assert result.provenance.upstream_identity_hashes == (
            task025.hydraulic_authority_hash,
            task025.result_hash,
            mismatched_task026.result_hash,
            property_snapshot.property_snapshot_hash,
        )
        replayed_blocked_hash = _replay_blocked_result_hash(result)
        assert result.result_hash == replayed_blocked_hash
        assert result.result_id == derive_result_id(result.result_hash)


class TestT027F01Pb003PropertySnapshotMismatchReachable:
    """T027_F01_PB_003_PROPERTY_SNAPSHOT_MISMATCH_REACHABLE."""

    def test_property_snapshot_mismatch_from_production_entry(self) -> None:
        task025, task026, property_snapshot = _produce_release_demo_upstream()
        roughness = _make_smooth_roughness_authority()
        mismatched_property_snapshot = replace(
            property_snapshot,
            property_snapshot_hash="a" * 64,
        )
        result = compute_task027_friction_pressure_drop(
            task025_result=task025,
            task026_result=task026,
            property_snapshot=mismatched_property_snapshot,
            roughness_authority=roughness,
            **_default_assertions(),
        )
        assert isinstance(result, Task027BlockedResult)
        codes = [b.code for b in result.blockers]
        assert BlockerCode.BL_T027_PROPERTY_SNAPSHOT_HASH_MISMATCH in codes
        assert any(b.field_path == ("property_snapshot_hash",) for b in result.blockers)

        expected_request_hash = _replay_request_hash(
            task025=task025,
            task026=task026,
            property_snapshot=mismatched_property_snapshot,
            roughness=roughness,
        )
        assert result.request_hash == expected_request_hash
        assert result.task025_result_hash == task025.result_hash
        assert result.task026_result_hash == task026.result_hash
        assert result.property_snapshot_hash == mismatched_property_snapshot.property_snapshot_hash
        assert isinstance(result.provenance, FrozenProvenance)
        assert result.provenance.upstream_identity_hashes == (
            task025.hydraulic_authority_hash,
            task025.result_hash,
            task026.result_hash,
            mismatched_property_snapshot.property_snapshot_hash,
        )
        replayed_blocked_hash = _replay_blocked_result_hash(result)
        assert result.result_hash == replayed_blocked_hash
        assert result.result_id == derive_result_id(result.result_hash)


class TestT027F01Pb004ReferencePlaneAndLengthBinding:
    """T027_F01_PB_004_REFERENCE_PLANE_AND_LENGTH_BINDING."""

    def test_reference_planes_and_length_bind_task025_internal_flow_authority(self) -> None:
        task025, task026, property_snapshot = _produce_release_demo_upstream()
        result = compute_task027_friction_pressure_drop(
            task025_result=task025,
            task026_result=task026,
            property_snapshot=property_snapshot,
            roughness_authority=_make_smooth_roughness_authority(),
            **_default_assertions(),
        )
        assert isinstance(result, Task027SuccessResult)
        ifa = task025.internal_flow_authority
        assert result.friction_length_m == ifa.length_m
        assert result.upstream_reference_plane == ifa.start_plane.start.value
        assert result.downstream_reference_plane == ifa.end_plane.end.value


class TestT027F01Pb005ProvenanceActualUpstreamIdentities:
    """T027_F01_PB_005_PROVENANCE_ACTUAL_UPSTREAM_IDENTITIES."""

    def test_provenance_upstream_identity_hashes_from_actual_producer_objects(self) -> None:
        task025, task026, property_snapshot = _produce_release_demo_upstream()
        result = compute_task027_friction_pressure_drop(
            task025_result=task025,
            task026_result=task026,
            property_snapshot=property_snapshot,
            roughness_authority=_make_smooth_roughness_authority(),
            **_default_assertions(),
        )
        assert isinstance(result, Task027SuccessResult)
        assert isinstance(result.provenance, FrozenProvenance)
        assert result.provenance.task_id == "TASK-027"
        assert (
            result.provenance.design_contract_path
            == "github-issue:xuezhiorange-png/hxforge-agent#168"
        )
        assert result.provenance.implementation_software_version == IMPLEMENTATION_SOFTWARE_VERSION
        assert result.provenance.upstream_identity_hashes == (
            task025.hydraulic_authority_hash,
            task025.result_hash,
            task026.result_hash,
            property_snapshot.property_snapshot_hash,
        )
        assert (
            "github-issue:xuezhiorange-png/hxforge-agent#167"
            in result.provenance.input_evidence_refs
        )


class TestT027F01Pb006NoPartialResultOnBlock:
    """T027_F01_PB_006_NO_PARTIAL_RESULT_ON_BLOCK."""

    @staticmethod
    def _assert_blocked_without_partial_result(result: Task027BlockedResult) -> None:
        assert result.blockers
        assert not hasattr(result, "darcy_friction_factor")
        assert not hasattr(result, "straight_tube_friction_pressure_drop_pa")
        assert result.request_hash is not None
        assert result.task025_hydraulic_authority_hash is not None
        assert result.task025_result_hash is not None
        assert result.task026_result_hash is not None
        assert result.property_snapshot_hash is not None
        assert isinstance(result.provenance, FrozenProvenance)

    def test_upstream_identity_mismatch_has_no_partial_result(self) -> None:
        task025, task026, property_snapshot = _produce_release_demo_upstream()
        result = compute_task027_friction_pressure_drop(
            task025_result=task025,
            task026_result=replace(task026, upstream_geometry_hash="e" * 64),
            property_snapshot=property_snapshot,
            roughness_authority=_make_smooth_roughness_authority(),
            **_default_assertions(),
        )
        assert isinstance(result, Task027BlockedResult)
        self._assert_blocked_without_partial_result(result)

    def test_property_snapshot_mismatch_has_no_partial_result(self) -> None:
        task025, task026, property_snapshot = _produce_release_demo_upstream()
        result = compute_task027_friction_pressure_drop(
            task025_result=task025,
            task026_result=task026,
            property_snapshot=replace(property_snapshot, property_snapshot_hash="d" * 64),
            roughness_authority=_make_smooth_roughness_authority(),
            **_default_assertions(),
        )
        assert isinstance(result, Task027BlockedResult)
        self._assert_blocked_without_partial_result(result)

    def test_roughness_authority_hash_mismatch_has_no_partial_result(self) -> None:
        task025, task026, property_snapshot = _produce_release_demo_upstream()
        roughness = _make_smooth_roughness_authority()
        tampered_roughness = replace(roughness, authority_hash="b" * 64)
        result = compute_task027_friction_pressure_drop(
            task025_result=task025,
            task026_result=task026,
            property_snapshot=property_snapshot,
            roughness_authority=tampered_roughness,
            **_default_assertions(),
        )
        assert isinstance(result, Task027BlockedResult)
        codes = [b.code for b in result.blockers]
        assert BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_HASH_MISMATCH in codes
        self._assert_blocked_without_partial_result(result)


class TestT027F01Pb007ExistingEngineeringPrimitivesReused:
    """T027_F01_PB_007_EXISTING_ENGINEERING_PRIMITIVES_REUSED."""

    def test_production_entry_delegates_to_existing_primitives(self) -> None:
        task025, task026, property_snapshot = _produce_release_demo_upstream()
        roughness = _make_smooth_roughness_authority()
        with (
            patch(
                "hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop.compute_laminar_friction_factor",
                wraps=compute_laminar_friction_factor,
            ) as laminar_mock,
            patch(
                "hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop.compute_turbulent_friction_factor_safe",
                wraps=compute_turbulent_friction_factor_safe,
            ) as turbulent_mock,
            patch(
                "hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop.compute_pressure_drop",
                wraps=compute_pressure_drop,
            ) as pressure_mock,
            patch(
                "hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop.compute_request_hash",
                wraps=compute_request_hash,
            ) as request_hash_mock,
            patch(
                "hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop.compute_result_hash",
                wraps=compute_result_hash,
            ) as result_hash_mock,
        ):
            result = compute_task027_friction_pressure_drop(
                task025_result=task025,
                task026_result=task026,
                property_snapshot=property_snapshot,
                roughness_authority=roughness,
                **_default_assertions(),
            )
        assert isinstance(result, Task027SuccessResult)
        regime = classify_reynolds(task026.reynolds_number)
        if regime == "laminar":
            assert laminar_mock.called
            assert not turbulent_mock.called
        else:
            assert turbulent_mock.called
        assert pressure_mock.called
        assert request_hash_mock.called
        assert result_hash_mock.called


class TestT027F01Pb008FrozenQuantizationAndIdentityReplay:
    """T027_F01_PB_008_FROZEN_QUANTIZATION_AND_IDENTITY_REPLAY."""

    def test_frozen_quanta_request_hash_result_hash_and_result_id_replay(self) -> None:
        task025, task026, property_snapshot = _produce_release_demo_upstream()
        roughness = _make_smooth_roughness_authority()
        result = compute_task027_friction_pressure_drop(
            task025_result=task025,
            task026_result=task026,
            property_snapshot=property_snapshot,
            roughness_authority=roughness,
            **_default_assertions(),
        )
        assert isinstance(result, Task027SuccessResult)

        reynolds = task026.reynolds_number
        regime = classify_reynolds(reynolds)
        if regime == "laminar":
            f_raw = compute_laminar_friction_factor(reynolds)
        else:
            f_raw, blockers = compute_turbulent_friction_factor_safe(reynolds, Decimal(0))
            assert not blockers
            assert f_raw is not None
        expected_f = f_raw.quantize(FRICTION_FACTOR_QUANTUM)
        assert result.darcy_friction_factor == expected_f

        friction_length_m = task025.internal_flow_authority.length_m
        dp_raw = compute_pressure_drop(
            darcy_friction_factor=expected_f,
            friction_length_m=friction_length_m,
            hydraulic_diameter_m=task025.hydraulic_diameter_m,
            density_kg_m3=property_snapshot.density_kg_m3,
            bulk_velocity_m_s=task026.bulk_velocity_m_s,
        )
        expected_dp = dp_raw.quantize(PRESSURE_DROP_QUANTUM)
        assert result.straight_tube_friction_pressure_drop_pa == expected_dp

        expected_request_hash = compute_request_hash(
            schema_version=TASK027_REQUEST_SCHEMA_VERSION,
            profile_id="profile-001",
            task025_result_hash=task025.result_hash,
            task026_result_hash=task026.result_hash,
            property_snapshot_hash=property_snapshot.property_snapshot_hash,
            constant_density_assertion=AssertionState.TRUE.value,
            zero_elevation_assertion=AssertionState.TRUE.value,
            flow_direction_assertion=FlowDirectionAssertion.START_TO_END.value,
            roughness_authority_hash=roughness.authority_hash,
        )
        assert result.request_hash == expected_request_hash

        expected_result_hash = compute_result_hash(
            schema_version=TASK027_SUCCESS_RESULT_SCHEMA_VERSION,
            profile_id="profile-001",
            request_hash=expected_request_hash,
            darcy_friction_factor=str(expected_f),
            friction_length_m=str(friction_length_m),
            upstream_reference_plane=task025.internal_flow_authority.start_plane.start.value,
            downstream_reference_plane=task025.internal_flow_authority.end_plane.end.value,
            straight_tube_friction_pressure_drop_pa=str(expected_dp),
            task025_hydraulic_authority_hash=task025.hydraulic_authority_hash,
            task025_result_hash=task025.result_hash,
            task026_result_hash=task026.result_hash,
            property_snapshot_hash=property_snapshot.property_snapshot_hash,
        )
        assert result.result_hash == expected_result_hash
        assert result.result_id == derive_result_id(expected_result_hash)
