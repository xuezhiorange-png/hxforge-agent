"""Producer-backed tests for TASK-167 preliminary engineering screening."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, getcontext, localcontext
from functools import cache

import pytest

from hexagent.exchangers.shell_tube import validate_request as validate_task020
from hexagent.exchangers.shell_tube.bell_delaware import (
    validate_request as validate_task166,
)
from hexagent.exchangers.shell_tube.bell_delaware.models import ValidationStatus as Task166Status
from hexagent.exchangers.shell_tube.engineering_screening import authority, validate_request
from hexagent.exchangers.shell_tube.engineering_screening.canonical import (
    request_hash,
    result_hash,
    result_id,
)
from hexagent.exchangers.shell_tube.engineering_screening.errors import (
    BlockerCode,
    FailureStage,
)
from hexagent.exchangers.shell_tube.engineering_screening.models import (
    FoulingTendency,
    NozzleGeometryAuthority,
    ScreeningPropertySnapshot,
    ScreeningRequirements,
    ScreenStatus,
    Task167Request,
    ValidationStatus,
)
from hexagent.exchangers.shell_tube.engineering_screening.raw_projection import (
    RawProjectionFailure,
    project_raw,
    raw_projection_hash,
)
from hexagent.exchangers.shell_tube.models import ConstructionFamily
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    compute_tube_side_heat_transfer_coefficient,
)
from tests.exchangers.shell_tube.test_task166_bell_delaware import _request as task166_request
from tests.exchangers.shell_tube.tube_side_thermal.test_python311_python312_byte_identical import (
    Task025ValidResult,
)
from tests.exchangers.shell_tube.tube_side_thermal.test_python311_python312_byte_identical import (
    _build_request as task026_request,
)


def _task020_raw(construction_family: str = "FIXED_TUBESHEET") -> dict[str, object]:
    return {
        "schema_version": "task020.configuration-request.v1",
        "case_authority": {
            "revision_id": "rev-167",
            "payload_hash": "a" * 64,
            "domain_snapshot_hash": "b" * 64,
            "status": "committed",
        },
        "equipment_family": "SHELL_AND_TUBE",
        "authority_mode": "INTERNAL_GENERIC",
        "construction_family": construction_family,
        "orientation": "HORIZONTAL",
        "shell_pass_count": 1,
        "tube_pass_count": 1,
        "front_head_token": "FRONT",
        "shell_token": "SHELL",
        "rear_head_token": "REAR",
        "standard_system_id": None,
        "requested_rule_pack_identity": None,
        "evidence_refs": [],
    }


@cache
def _configuration(construction_family: str = "FIXED_TUBESHEET"):
    outcome = validate_task020(_task020_raw(construction_family))
    assert outcome.configuration is not None, outcome.blockers
    return outcome.configuration


@cache
def _task166_result():
    outcome = validate_task166(task166_request())
    assert outcome.status is Task166Status.VALID
    assert outcome.valid is not None
    return outcome.valid


@cache
def _tube_result():
    request = task026_request()
    result = compute_tube_side_heat_transfer_coefficient(
        request,
        Task025ValidResult(Decimal("0.01"), Decimal("0.01")),
    )
    assert hasattr(result, "result_hash")
    return result


def _requirements(**overrides: object) -> ScreeningRequirements:
    values: dict[str, object] = {
        "requirement_id": "requirement-167",
        "source_id": "project-screening-source",
        "source_version": "v1",
        "evidence_ref": "project-evidence-167",
        "snapshot_hash": "project-snapshot-hash",
    }
    values.update(overrides)
    return ScreeningRequirements(**values)


def _snapshot(**overrides: object) -> ScreeningPropertySnapshot:
    values: dict[str, object] = {
        "snapshot_id": "properties-167",
        "source_id": "screening-property-source",
        "source_version": "v1",
        "evidence_ref": "property-evidence-167",
        "snapshot_hash": "property-snapshot-hash",
        "fluid_density_kg_m3": Decimal("1000"),
        "shell_bulk_velocity_m_s": Decimal("1.0"),
        "shell_crossflow_velocity_m_s": Decimal("1.2"),
        "tube_free_span_m": Decimal("1.0"),
        "tube_mass_per_length_kg_m": Decimal("2.0"),
        "young_modulus_pa": Decimal("2e11"),
        "damping_ratio": Decimal("0.01"),
        "coefficient_thermal_expansion_per_k": Decimal("1e-5"),
        "reference_temperature_k": Decimal("300"),
        "effective_shell_temperature_k": Decimal("310"),
        "effective_tube_temperature_k": Decimal("305"),
        "effective_length_m": Decimal("1.0"),
        "added_mass_kg_m": Decimal("1.0"),
        "natural_frequency_hz": Decimal("10"),
    }
    values.update(overrides)
    return ScreeningPropertySnapshot(**values)


@cache
def _request(construction_family: str = "FIXED_TUBESHEET") -> Task167Request:
    return Task167Request(
        schema_version=authority.REQUEST_SCHEMA_VERSION,
        task167_version=authority.TASK167_VERSION,
        source_definition_id=authority.SOURCE_DEFINITION_ID,
        task020_configuration=_configuration(construction_family),
        task166_result=_task166_result(),
        tube_side_result=_tube_result(),
        screening_requirements=_requirements(),
        screening_property_snapshot=_snapshot(),
        request_metadata=(("zeta", "1"), ("alpha", "2")),
    )


def _valid(request: Task167Request | None = None):
    outcome = validate_request(request or _request())
    assert outcome.status is ValidationStatus.VALID, outcome
    assert outcome.valid is not None
    return outcome.valid


def _blockers(outcome: object) -> tuple[object, ...]:
    branch = getattr(outcome, "typed_blocked", None) or getattr(
        outcome, "raw_boundary_blocked", None
    )
    return () if branch is None else branch.blockers


def _codes(outcome: object) -> set[BlockerCode]:
    return {item.code for item in _blockers(outcome)}


def test_valid_path_uses_real_upstream_results_and_is_complete() -> None:
    result = _valid()
    assert result.configuration_evidence[0][1] == _configuration().configuration_id
    assert result.task166_evidence == (
        ("result_hash", _task166_result().result_hash),
        ("result_id", _task166_result().result_id),
    )
    assert result.tube_side_evidence == (
        ("result_hash", _tube_result().result_hash),
        ("result_id", _tube_result().result_id),
    )
    assert result.aggregate_screening_status is ScreenStatus.WARN
    assert result.applicability is not None
    assert result.applicability.status == "APPLICABLE"
    assert len(result.applicability.checks) == len(authority.TASK167_APPLICABILITY_CHECKS)
    assert result.completeness is not None
    assert result.completeness.status == "COMPLETE"
    assert result.completeness.required_fields == authority.TASK167_COMPLETENESS_FIELDS
    assert result.provenance is not None
    assert result.provenance.self_edge_count == 0
    assert result.provenance.cycle_count == 0


def test_only_public_business_api_is_validate_request() -> None:
    import hexagent.exchangers.shell_tube.engineering_screening as package

    assert package.__all__ == ("validate_request",)


@pytest.mark.parametrize(
    ("attribute", "code"),
    [
        ("task166_result", BlockerCode.TASK166_IDENTITY_REPLAY_FAILED),
        ("tube_side_result", BlockerCode.TUBE_SIDE_IDENTITY_REPLAY_FAILED),
    ],
)
def test_upstream_identity_tampering_is_replayed_and_blocked(
    attribute: str, code: BlockerCode
) -> None:
    original = getattr(_request(), attribute)
    tampered = replace(original, result_hash="0" * 64)
    outcome = validate_request(replace(_request(), **{attribute: tampered}))
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert code in _codes(outcome)


def test_same_upstream_replay_stage_accumulates_blockers() -> None:
    task166 = replace(_task166_result(), result_hash="0" * 64)
    tube = replace(_tube_result(), result_hash="1" * 64)
    outcome = validate_request(replace(_request(), task166_result=task166, tube_side_result=tube))
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    codes = _codes(outcome)
    assert BlockerCode.TASK166_IDENTITY_REPLAY_FAILED in codes
    assert BlockerCode.TUBE_SIDE_IDENTITY_REPLAY_FAILED in codes


def test_task020_identity_tampering_is_blocked_before_screening() -> None:
    configuration = replace(_configuration(), configuration_hash="0" * 64)
    outcome = validate_request(replace(_request(), task020_configuration=configuration))
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.TASK020_AUTHORITY_INVALID in _codes(outcome)


def test_task166_blocker_or_non_applicable_result_is_rejected() -> None:
    task166 = replace(_task166_result(), applicability=None)
    outcome = validate_request(replace(_request(), task166_result=task166))
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.TASK166_NOT_APPLICABLE in _codes(outcome)


def test_raw_unsupported_object_is_raw_boundary_blocked_without_repr() -> None:
    class Explosive:
        def __repr__(self) -> str:
            raise AssertionError("repr must not run")

        def __str__(self) -> str:
            raise AssertionError("str must not run")

    outcome = validate_request(Explosive())
    assert outcome.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.UNSUPPORTED_RAW_VALUE in _codes(outcome)


def test_raw_unicode_surrogate_is_total_and_blocked() -> None:
    outcome = validate_request({"bad": "\ud800"})
    assert outcome.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.RAW_UNICODE_ENCODING_FAILURE in _codes(outcome)


def test_raw_limits_are_bounded() -> None:
    nested: object = 0
    for _ in range(authority.RAW_MAX_DEPTH + 1):
        nested = (nested,)
    with pytest.raises(RawProjectionFailure) as depth:
        project_raw(nested)
    assert depth.value.code is BlockerCode.RAW_DEPTH_LIMIT_EXCEEDED

    with pytest.raises(RawProjectionFailure) as nodes:
        project_raw(tuple(range(authority.RAW_MAX_NODES + 1)))
    assert nodes.value.code is BlockerCode.RAW_NODE_LIMIT_EXCEEDED

    with pytest.raises(RawProjectionFailure) as scalar:
        project_raw("x" * (authority.RAW_MAX_SCALAR_BYTES + 1))
    assert scalar.value.code is BlockerCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED


def test_request_metadata_order_is_nonsemantic_for_raw_and_typed_identity() -> None:
    first = _request()
    second = replace(first, request_metadata=tuple(reversed(first.request_metadata)))
    assert raw_projection_hash(first) == raw_projection_hash(second)
    assert request_hash(first) == request_hash(second)
    first_result = _valid(first)
    second_result = _valid(second)
    assert first_result.result_hash == second_result.result_hash
    assert first_result.result_id == second_result.result_id


def test_duplicate_metadata_is_rejected() -> None:
    request = replace(_request(), request_metadata=(("same", "1"), ("same", "2")))
    outcome = validate_request(request)
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.INVALID_REQUEST_SCHEMA in _codes(outcome)


def test_raw_mapping_insertion_order_is_nonsemantic() -> None:
    one = {"b": 2, "a": 1}
    two = {"a": 1, "b": 2}
    assert project_raw(one) == project_raw(two)


def test_nozzle_is_optional_but_computed_when_authority_exists() -> None:
    snapshot = _snapshot(
        nozzle_mass_flow_rate_kg_s=Decimal("2"),
        nozzle_density_kg_m3=Decimal("1000"),
    )
    nozzle = NozzleGeometryAuthority(
        authority_id="nozzle-167",
        source_id="nozzle-source",
        source_version="v1",
        evidence_ref="nozzle-evidence",
        snapshot_hash="nozzle-snapshot",
        flow_area_m2=Decimal("0.01"),
    )
    result = _valid(
        replace(_request(), screening_property_snapshot=snapshot, nozzle_geometry=nozzle)
    )
    nozzle_screen = next(
        item for item in result.velocity_screens if item.screen_id == "NOZZLE_VELOCITY"
    )
    assert ("nozzle_velocity_m_s", "0.2") in nozzle_screen.diagnostic_values


def test_required_nozzle_without_geometry_blocks() -> None:
    requirements = _requirements(nozzle_velocity_screen_required=True)
    outcome = validate_request(replace(_request(), screening_requirements=requirements))
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.NOZZLE_GEOMETRY_NOT_AVAILABLE in _codes(outcome)


def test_shell_velocity_requires_authoritative_snapshot_value() -> None:
    snapshot = _snapshot(shell_bulk_velocity_m_s=None, shell_crossflow_velocity_m_s=None)
    outcome = validate_request(replace(_request(), screening_property_snapshot=snapshot))
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.SHELL_VELOCITY_NOT_COMPUTABLE in _codes(outcome)


def test_generic_screen_never_claims_standard_compliance() -> None:
    result = _valid()
    screens = result.velocity_screens + (
        result.erosion_screen,
        result.fouling_cleanability_screen,
        result.thermal_expansion_screen,
        result.construction_family_suitability_screen,
    )
    assert all(item is not None and item.standard_claim is False for item in screens)
    assert result.fiv_screen is not None
    assert result.fiv_screen.numeric_limit_not_guessed is True
    assert result.fiv_screen.critical_velocity_m_s is None


@pytest.mark.parametrize(
    "construction_family",
    ["FIXED_TUBESHEET", "U_TUBE", "FLOATING_HEAD"],
)
def test_all_construction_families_have_preliminary_screen_semantics(
    construction_family: str,
) -> None:
    result = _valid(_request(construction_family))
    assert result.construction_family_suitability_screen is not None
    assert result.construction_family_suitability_screen.standard_claim is False


def test_fixed_tubesheet_shell_cleaning_requirement_blocks() -> None:
    requirements = _requirements(shell_side_mechanical_cleaning_required=True)
    outcome = validate_request(replace(_request(), screening_requirements=requirements))
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.CLEANABILITY_REQUIREMENT_UNSATISFIED in _codes(outcome)


def test_fixed_tubesheet_fouling_without_hard_requirement_warns() -> None:
    requirements = _requirements(shell_side_fouling_tendency=FoulingTendency.HIGH)
    result = _valid(replace(_request(), screening_requirements=requirements))
    assert result.fouling_cleanability_screen is not None
    assert result.fouling_cleanability_screen.status is ScreenStatus.WARN


def test_u_tube_tube_cleaning_limit_is_retained() -> None:
    requirements = _requirements(tube_side_mechanical_cleaning_required=True)
    result = _valid(
        replace(
            _request("U_TUBE"),
            screening_requirements=requirements,
        )
    )
    assert result.fouling_cleanability_screen is not None
    assert (
        "tube_side_bend_limitation",
        "TRUE",
    ) in result.fouling_cleanability_screen.diagnostic_values


def test_floating_head_is_broad_and_not_specific_subtype_compliance() -> None:
    requirements = _requirements(removable_bundle_required=True)
    result = _valid(
        replace(
            _request("FLOATING_HEAD"),
            screening_requirements=requirements,
        )
    )
    assert result.construction_family_suitability_screen is not None
    assert result.construction_family_suitability_screen.standard_claim is False


def test_fixed_tubesheet_expansion_is_warning_without_allowable() -> None:
    result = _valid()
    assert result.thermal_expansion_screen is not None
    assert result.thermal_expansion_screen.status is ScreenStatus.WARN
    assert any(
        name == "differential_free_expansion_m"
        for name, _value in result.thermal_expansion_screen.diagnostic_values
    )


@pytest.mark.parametrize("construction_family", ["U_TUBE", "FLOATING_HEAD"])
def test_expansion_accommodation_is_structural_preliminary_diagnostic(
    construction_family: str,
) -> None:
    result = _valid(_request(construction_family))
    assert result.thermal_expansion_screen is not None
    assert result.thermal_expansion_screen.status is ScreenStatus.PASS


def test_missing_expansion_inputs_warn_without_anonymous_threshold() -> None:
    result = _valid(
        replace(
            _request(),
            screening_property_snapshot=_snapshot(
                coefficient_thermal_expansion_per_k=None,
                effective_length_m=None,
            ),
        )
    )
    assert result.thermal_expansion_screen is not None
    assert result.thermal_expansion_screen.status is ScreenStatus.WARN
    assert result.thermal_expansion_screen.limit_values == ()


def test_negative_physical_property_is_typed_blocked() -> None:
    outcome = validate_request(
        replace(
            _request(),
            screening_property_snapshot=_snapshot(tube_free_span_m=Decimal("-1")),
        )
    )
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.SCREENING_PROPERTY_AUTHORITY_INVALID in _codes(outcome)


def test_fiv_exposes_diagnostics_but_no_guessed_critical_limit() -> None:
    result = _valid()
    assert result.fiv_screen is not None
    fiv = result.fiv_screen
    assert fiv.crossflow_velocity_m_s == Decimal("1.2")
    assert fiv.tube_mass_per_length_kg_m == Decimal("2.0")
    assert fiv.effective_mass_kg_m == Decimal("3.0")
    assert fiv.reduced_velocity is not None
    assert fiv.mass_damping_parameter is not None
    assert fiv.critical_velocity_m_s is None
    assert fiv.status.value == "WARN"


def test_fiv_invalid_optional_damping_does_not_emit_numeric_limit() -> None:
    outcome = validate_request(
        replace(_request(), screening_property_snapshot=_snapshot(damping_ratio=Decimal("-0.1")))
    )
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.SCREENING_PROPERTY_AUTHORITY_INVALID in _codes(outcome)


def test_approved_rule_pack_without_authority_fails_closed() -> None:
    configuration = _configuration()
    # The existing TASK-020 model is trusted and cannot be changed to an
    # approved binding without a real evaluated rule-pack object.  This test
    # asserts TASK-167 does not silently downgrade the missing authority.
    approved = replace(
        configuration,
        authority_mode=type(configuration.authority_mode)("APPROVED_RULE_PACK"),
    )
    outcome = validate_request(replace(_request(), task020_configuration=approved))
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.RULE_PACK_REQUIRED in _codes(
        outcome
    ) or BlockerCode.TASK020_AUTHORITY_INVALID in _codes(outcome)


def test_decimal_context_does_not_change_result_identity() -> None:
    first = _valid()
    ambient = getcontext()
    original_precision = ambient.prec
    try:
        ambient.prec = 7
        second = _valid()
    finally:
        ambient.prec = original_precision
    assert first.result_hash == second.result_hash
    assert first.result_id == second.result_id


def test_canonical_decimal_lexical_forms_remain_distinct() -> None:
    left = replace(_request(), request_metadata=(("decimal", "1.20"),))
    right = replace(_request(), request_metadata=(("decimal", "1.2"),))
    assert request_hash(left) != request_hash(right)


def test_result_hash_and_id_replay_without_final_graph_cycle() -> None:
    result = _valid()
    assert result_hash(result) == result.result_hash
    assert result_id(result.result_hash) == result.result_id
    assert result.provenance is not None
    assert result.provenance.graph_hash
    assert result.provenance.self_edge_count == 0
    assert result.provenance.cycle_count == 0
    assert all(edge.source_node_id != edge.target_node_id for edge in result.provenance.edges)


def test_task166_and_task026_authorities_remain_separate() -> None:
    result = _valid()
    assert result.task166_evidence[0][1] != result.tube_side_evidence[0][1]
    assert _configuration().construction_family is ConstructionFamily.FIXED_TUBESHEET


def test_no_lmtd_or_f_factor_surface_is_present() -> None:
    result = _valid()
    result_names = {field for field in result.__dataclass_fields__}
    assert "lmtd" not in result_names
    assert "f_factor" not in result_names
    assert "lmtD" not in result_names


def test_raw_projection_has_no_user_object_state_or_address() -> None:
    class Meta(type):
        def __getattribute__(cls, name: str):
            if name in {"__repr__", "__str__", "__hash__"}:
                raise AssertionError("user hook must not run")
            return super().__getattribute__(name)

    class Hostile(metaclass=Meta):
        pass

    with pytest.raises(RawProjectionFailure) as failure:
        project_raw(Hostile())
    assert failure.value.code is BlockerCode.UNSUPPORTED_RAW_VALUE


def test_blocked_identity_is_deterministic() -> None:
    first = validate_request({"unsupported": object()})
    second = validate_request({"unsupported": object()})
    assert first.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert second.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert first.raw_boundary_blocked is not None
    assert second.raw_boundary_blocked is not None
    assert first.raw_boundary_blocked.result_hash == second.raw_boundary_blocked.result_hash
    assert first.raw_boundary_blocked.result_id == second.raw_boundary_blocked.result_id


def test_failure_stage_is_preserved_for_screening_blocker() -> None:
    outcome = validate_request(
        replace(
            _request(),
            screening_property_snapshot=_snapshot(
                shell_bulk_velocity_m_s=None,
                shell_crossflow_velocity_m_s=None,
            ),
        )
    )
    assert outcome.typed_blocked is not None
    blocker = outcome.typed_blocked.blockers[0]
    assert blocker.code is BlockerCode.SHELL_VELOCITY_NOT_COMPUTABLE
    assert blocker.stage is FailureStage.SCREENING


def test_task167_request_raw_projection_is_bounded_and_deterministic() -> None:
    one = project_raw(_request())
    two = project_raw(_request())
    assert one == two


def test_source_definition_and_deferred_capabilities_are_bound() -> None:
    result = _valid()
    assert result.source_definition_id == authority.SOURCE_DEFINITION_ID
    assert "TASK168_CANDIDATE_GENERATION_NOT_COMPUTABLE" in result.deferred_capabilities
    assert "TASK169_RANKING_AND_RELEASE_ACCEPTANCE_NOT_COMPUTABLE" in result.deferred_capabilities


def test_task166_result_has_not_been_recomputed_by_task167() -> None:
    result = _valid()
    assert result.task166_evidence[0][1] == _task166_result().result_hash
    assert result.task166_evidence[1][1] == _task166_result().result_id


def test_typed_request_schema_rejects_raw_replacement_values() -> None:
    raw = {
        "schema_version": authority.REQUEST_SCHEMA_VERSION,
        "task167_version": authority.TASK167_VERSION,
        "source_definition_id": authority.SOURCE_DEFINITION_ID,
        "task020_configuration": _configuration(),
        "task166_result": _task166_result(),
        "tube_side_result": _tube_result(),
        "screening_requirements": _requirements(),
        "screening_property_snapshot": _snapshot(),
        "ua": Decimal("1"),
    }
    outcome = validate_request(raw)
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.INVALID_REQUEST_SCHEMA in _codes(outcome)


def test_raw_projection_hash_changes_when_semantic_scalar_changes() -> None:
    first = replace(_request(), request_metadata=(("mode", "one"),))
    second = replace(_request(), request_metadata=(("mode", "two"),))
    assert raw_projection_hash(first) != raw_projection_hash(second)


def test_screen_warning_order_is_stable() -> None:
    first = _valid()
    second = _valid()
    assert first.warnings == second.warnings
    assert first.provenance_semantic_inputs == second.provenance_semantic_inputs


def test_no_optional_nozzle_false_value_is_emitted() -> None:
    result = _valid()
    nozzle = next(item for item in result.velocity_screens if item.screen_id == "NOZZLE_VELOCITY")
    assert nozzle.status is ScreenStatus.WARN
    assert nozzle.diagnostic_values == ()
    assert nozzle.reason_code == "NOZZLE_VELOCITY_NOT_EVALUATED"


def test_thermal_expansion_diagnostic_is_decimal_lexical_output() -> None:
    result = _valid()
    assert result.thermal_expansion_screen is not None
    differential = dict(result.thermal_expansion_screen.diagnostic_values)[
        "differential_free_expansion_m"
    ]
    assert differential == "0.000050"


def test_fiv_ambient_decimal_context_does_not_change_diagnostics() -> None:
    first = _valid().fiv_screen
    with localcontext() as context:
        context.prec = 8
        second = _valid().fiv_screen
    assert first == second
