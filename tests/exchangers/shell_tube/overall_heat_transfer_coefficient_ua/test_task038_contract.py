"""Independent contract tests for the frozen TASK-038 R4 boundary."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua import (
    build_raw_overall_u_ua_request,
    canonical,
    compute_overall_heat_transfer_coefficient_and_ua,
    evaluate_task038,
    schema,
    verify_task038_success_identity,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.authority import (
    build_cross_producer_projection,
    cross_producer_hash,
    validate_cross_producer_joins,
    validate_engineering_source,
    validate_service_binding,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.canonical import (
    cross_producer_compatibility_hash,
    engineering_source_identity_hash,
    outer_area_projection_hash,
    producer_envelope_hash,
    provenance_bytes,
    provenance_hash,
    request_bytes,
    request_hash,
    resistance_composition_hash,
    result_id_from_hash,
    service_binding_bytes,
    service_binding_hash,
    success_result_bytes,
    success_result_hash,
    thermal_resistance_ledger_row_hash,
    ua_composition_hash,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.decimal_math import (
    compose_resistances,
    public_outer_area,
    public_u,
    public_ua,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.engineering import (
    build_thermal_resistance_ledger,
    compute_outer_area,
    compute_resistance_composition,
    compute_ua,
    gv01,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
    Task038Provenance,
    Task038RawBoundaryBlockedResult,
    Task038Request,
    Task038SuccessResult,
    Task038TypedBlockedResult,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.producer_replay import (
    producer_identity_envelope,
    replay_task025,
    replay_task026,
    replay_task035,
    replay_task037,
    task026_raw_replay_hash,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.raw_projection import (
    FrozenRawProjection,
    project_raw_value,
)
from tests.exchangers.shell_tube.overall_heat_transfer_coefficient_ua import (
    task038_frozen_vectors as vectors,
)


def _request(refs: tuple[str, ...] = ("ER-T038-001", "ER-T038-002")) -> Task038Request:
    return vectors.request_fixture(refs)


def _provenance(refs: tuple[str, ...] = ("ER-T038-001", "ER-T038-002")) -> Task038Provenance:
    request_value = (
        vectors.REQUEST_HASH_A if refs == ("ER-T038-001", "ER-T038-002") else vectors.REQUEST_HASH_B
    )
    terminal = (
        vectors.PROVENANCE_HASH_A
        if request_value == vectors.REQUEST_HASH_A
        else vectors.PROVENANCE_HASH_B
    )
    return vectors.provenance_fixture(request_value, terminal)


def _unchecked_replace(value: Any, **changes: Any) -> Any:
    """Build adversarial dataclass values without invoking constructor guards."""

    clone = object.__new__(type(value))
    for field_name in value.__dataclass_fields__:
        object.__setattr__(clone, field_name, changes.get(field_name, getattr(value, field_name)))
    return clone


def _rehash_tampered_result(
    result: Task038SuccessResult,
    *,
    provenance_changes: dict[str, Any] | None = None,
    **changes: Any,
) -> Task038SuccessResult:
    provenance = result.provenance
    if provenance_changes:
        provenance = _unchecked_replace(provenance, **provenance_changes)
        provenance = _unchecked_replace(provenance, provenance_hash=provenance_hash(provenance))
    candidate = _unchecked_replace(result, provenance=provenance, **changes)
    digest = success_result_hash(candidate)
    return _unchecked_replace(
        candidate,
        result_hash=digest,
        result_id=result_id_from_hash(digest),
    )


def _tampered_rehashed_result(case: str) -> Task038SuccessResult:
    result = vectors.result_fixture(
        vectors.REQUEST_HASH_A,
        vectors.provenance_fixture(vectors.REQUEST_HASH_A, vectors.PROVENANCE_HASH_A),
    )
    thermal = result.full_thermal_resistance_composition_ledger
    applicability = result.applicability_ledger
    completeness = result.completeness_ledger
    if case == "T01":
        return _rehash_tampered_result(
            result,
            overall_u_reference_surface="INNER_TUBE_SURFACE",
            provenance_changes={"overall_u_reference_surface": "INNER_TUBE_SURFACE"},
        )
    if case == "T02":
        return _rehash_tampered_result(
            result,
            full_thermal_resistance_composition_ledger=(
                replace(thermal[0], term_id="R99_TAMPERED"),
                *thermal[1:],
            ),
        )
    if case == "T03":
        return _rehash_tampered_result(
            result,
            full_thermal_resistance_composition_ledger=tuple(reversed(thermal)),
        )
    if case == "T04":
        return _rehash_tampered_result(
            result,
            full_thermal_resistance_composition_ledger=(
                replace(thermal[0], producer_owner="TASK038"),
                *thermal[1:],
            ),
        )
    if case == "T05":
        return _rehash_tampered_result(
            result,
            full_thermal_resistance_composition_ledger=(
                replace(thermal[0], native_reference_surface="OUTER_TUBE_SURFACE"),
                *thermal[1:],
            ),
        )
    if case == "T06":
        return _rehash_tampered_result(
            result,
            full_thermal_resistance_composition_ledger=(
                replace(thermal[0], composed_reference_surface="INNER_TUBE_SURFACE"),
                *thermal[1:],
            ),
        )
    if case == "T07":
        return _rehash_tampered_result(
            result,
            full_thermal_resistance_composition_ledger=(
                replace(thermal[0], transformation_authority_hash_or_none=None),
                *thermal[1:],
            ),
        )
    if case == "T08":
        return _rehash_tampered_result(
            result,
            full_thermal_resistance_composition_ledger=(
                replace(thermal[0], status="PRESENT_APPLICABLE_INCOMPATIBLE"),
                *thermal[1:],
            ),
        )
    if case == "T09":
        return _rehash_tampered_result(
            result,
            applicability_ledger=(
                replace(applicability[0], row_id="A99_TAMPERED"),
                *applicability[1:],
            ),
        )
    if case == "T10":
        return _rehash_tampered_result(
            result,
            applicability_ledger=tuple(reversed(applicability)),
        )
    if case == "T11":
        return _rehash_tampered_result(
            result,
            applicability_ledger=(replace(applicability[0], status="FAIL"), *applicability[1:]),
        )
    if case == "T12":
        return _rehash_tampered_result(
            result,
            completeness_ledger=(
                replace(completeness[0], row_id="C99_TAMPERED"),
                *completeness[1:],
            ),
        )
    if case == "T13":
        return _rehash_tampered_result(
            result,
            completeness_ledger=tuple(reversed(completeness)),
        )
    if case == "T14":
        return _rehash_tampered_result(
            result,
            completeness_ledger=(replace(completeness[0], status="FAIL"), *completeness[1:]),
        )
    if case == "T15":
        return _rehash_tampered_result(result, warnings=(vectors.task038_warning(),))
    if case == "T16":
        return _rehash_tampered_result(result, blockers=(vectors.task038_blocker(),))
    if case == "T17":
        return _rehash_tampered_result(
            result, deferred_capabilities=tuple(reversed(result.deferred_capabilities))
        )
    if case == "T18":
        return _rehash_tampered_result(
            result, provenance_changes={"design_revision": "R3_FINAL_FROZEN"}
        )
    if case == "T19":
        return _rehash_tampered_result(
            result,
            provenance_changes={
                "base_main_sha": "0" * 64,
                "base_main_tree": "1" * 64,
                "baseline_repair_governance_comment_id": "5472639061",
            },
        )
    if case == "T20":
        return _rehash_tampered_result(
            result, modeled_overall_heat_transfer_coefficient_w_m2_k=Decimal("1")
        )
    if case == "T21":
        return _rehash_tampered_result(result, outer_tube_surface_effective_area_m2=Decimal("1"))
    if case == "T22":
        return _rehash_tampered_result(result, modeled_ua_w_k=Decimal("1"))
    raise AssertionError(f"unknown tamper case: {case}")


def _cross_projection() -> dict[str, object]:
    return {
        "task025_result_hash": vectors.TASK025_RESULT_HASH,
        "task026_result_hash": vectors.TASK026_RESULT_HASH,
        "task035_result_hash": vectors.TASK035_RESULT_HASH,
        "task037_result_hash": vectors.TASK037_RESULT_HASH,
        "tube_side_service_binding_authority_hash": vectors.SERVICE_BINDING_AUTHORITY_HASH,
        "task025_hydraulic_authority_hash": vectors.TASK025_HYDRAULIC_AUTHORITY_HASH,
        "task021_layout_id": vectors.TASK021_LAYOUT_ID,
        "task021_layout_hash": vectors.TASK021_LAYOUT_HASH,
        "task020_configuration_id": vectors.TASK020_CONFIGURATION_ID,
        "task020_configuration_hash": vectors.TASK020_CONFIGURATION_HASH,
        "task026_property_snapshot_hash": vectors.TASK026_PROPERTY_SNAPSHOT_HASH,
        "task035_shell_side_fluid_id": vectors.SHELL_SIDE_FLUID_SERVICE_ID,
        "task037_inside_fouling_fluid_service_id": vectors.TUBE_SIDE_FLUID_SERVICE_ID,
        "task037_outside_fouling_fluid_service_id": vectors.SHELL_SIDE_FLUID_SERVICE_ID,
        "tube_side_film_reference_surface": "INNER_TUBE_SURFACE",
        "shell_side_film_reference_surface": "OUTER_TUBE_SURFACE",
        "overall_u_reference_surface": "OUTER_TUBE_SURFACE",
    }


def _resistance_projection() -> dict[str, object]:
    return {
        "cross_producer_compatibility_hash": (
            "17365c90eea8747711d93d5ffdc760905f4ec1731bd84bb971e4084012d9ec8d"
        ),
        "engineering_source_identity_hashes": (
            "5e939001be060fcd044121b442e9b0cbbea078f869bfa8e83d688bf4c8b5f024",
            "8f53a07ab56efebbaee392e79772c09d60ba49500f1045f65b36181d97d68da3",
        ),
        "overall_u_reference_surface": "OUTER_TUBE_SURFACE",
        "outer_to_inner_area_ratio": Decimal("1.2"),
        "tube_side_heat_transfer_coefficient_w_m2_k": Decimal("1000"),
        "shell_side_heat_transfer_coefficient_w_m2_k": Decimal("800"),
        "inside_fouling_resistance_inner_surface_m2_k_w": Decimal("0.0002"),
        "wall_resistance_outer_surface_m2_k_w": Decimal("0.0001"),
        "outside_fouling_resistance_outer_surface_m2_k_w": Decimal("0.0003"),
        "overall_u_quantum_w_m2_k": Decimal("1E-9"),
        "rounding_mode": "ROUND_HALF_EVEN",
    }


def _area_projection() -> dict[str, object]:
    return {
        "task025_result_hash": vectors.TASK025_RESULT_HASH,
        "task025_internal_heat_transfer_surface_area_m2": vectors.GV01_A_I_PUB,
        "task037_result_hash": vectors.TASK037_RESULT_HASH,
        "task037_surface_transform_authority_hash": (
            vectors.TASK037_SURFACE_TRANSFORM_AUTHORITY_HASH
        ),
        "outer_to_inner_area_ratio": vectors.GV01_GAMMA,
        "task025_area_quantum_m2": Decimal("1E-10"),
        "task025_area_rounding_mode": "ROUND_HALF_EVEN",
        "producer_area_precision_policy_id": (
            "task037.task025-public-area-authority.accept-positive-v1"
        ),
        "producer_area_precision_policy_hash": vectors.TASK037_PRODUCER_AREA_PRECISION_POLICY_HASH,
        "producer_precision_limitation_disclosed": True,
        "producer_precision_threshold_defined": False,
        "outer_area_quantum_m2": Decimal("1E-10"),
        "rounding_mode": "ROUND_HALF_EVEN",
    }


def _ua_projection() -> dict[str, object]:
    return {
        "resistance_composition_authority_hash": (
            "24e272673e1434b5157d121d72d8bc7705a93136a46138eeffc181a0ef3ae39c"
        ),
        "outer_area_projection_authority_hash": (
            "ef19ab57c6a052e6d2c211f164ea68eb52b8a00fa7bd02b091a9a932d4d65645"
        ),
        "modeled_overall_heat_transfer_coefficient_w_m2_k": vectors.GV01_PUBLIC_U,
        "outer_tube_surface_effective_area_m2": vectors.GV01_PUBLIC_A_O,
        "ua_quantum_w_k": Decimal("1E-9"),
        "rounding_mode": "ROUND_HALF_EVEN",
    }


def _valid_join_objects() -> tuple[Any, Any, Any, Any]:
    task021 = SimpleNamespace(
        identity_id=vectors.TASK021_LAYOUT_ID,
        identity_hash=vectors.TASK021_LAYOUT_HASH,
    )
    task020 = SimpleNamespace(
        identity_id=vectors.TASK020_CONFIGURATION_ID,
        identity_hash=vectors.TASK020_CONFIGURATION_HASH,
    )
    task025 = SimpleNamespace(
        task021_identity=task021,
        task020_identity=task020,
        layout_hash=vectors.TASK021_LAYOUT_HASH,
        hydraulic_authority_hash=vectors.TASK025_HYDRAULIC_AUTHORITY_HASH,
        result_hash=vectors.TASK025_RESULT_HASH,
        result_id=vectors.TASK025_RESULT_ID,
    )
    task026 = SimpleNamespace(
        upstream_geometry_hash=vectors.TASK025_HYDRAULIC_AUTHORITY_HASH,
        result_hash=vectors.TASK026_RESULT_HASH,
        property_snapshot_hash=vectors.TASK026_PROPERTY_SNAPSHOT_HASH,
    )
    task035 = SimpleNamespace(
        task021_layout_id=vectors.TASK021_LAYOUT_ID,
        task021_layout_hash=vectors.TASK021_LAYOUT_HASH,
        task020_configuration_id=vectors.TASK020_CONFIGURATION_ID,
        task020_configuration_hash=vectors.TASK020_CONFIGURATION_HASH,
        heat_transfer_surface="OUTER_TUBE_SURFACE",
        shell_side_fluid_id=vectors.SHELL_SIDE_FLUID_SERVICE_ID,
        result_hash=vectors.TASK035_RESULT_HASH,
    )
    task037 = SimpleNamespace(
        task021_identity=task021,
        task025_identity=SimpleNamespace(
            identity_hash=vectors.TASK025_RESULT_HASH,
            identity_id=vectors.TASK025_RESULT_ID,
        ),
        task025_hydraulic_authority_hash=vectors.TASK025_HYDRAULIC_AUTHORITY_HASH,
        overall_u_reference_surface="OUTER_TUBE_SURFACE",
        tube_side_film_reference_surface="INNER_TUBE_SURFACE",
        inside_fouling_authority=SimpleNamespace(
            fluid_service_id=vectors.TUBE_SIDE_FLUID_SERVICE_ID,
        ),
        outside_fouling_authority=SimpleNamespace(
            fluid_service_id=vectors.SHELL_SIDE_FLUID_SERVICE_ID,
        ),
        result_hash=vectors.TASK037_RESULT_HASH,
    )
    return task025, task026, task035, task037


def test_I01_exact_request_field_inventory() -> None:
    assert schema.REQUEST_FIELDS == (
        "schema_version",
        "profile_id",
        "task025_result",
        "task026_result",
        "task035_result",
        "task037_result",
        "tube_side_service_binding_authority",
        "evidence_refs",
    )
    assert schema.REQUEST_FIELD_COUNT == 8


def test_I02_request_canonical_variant_a() -> None:
    request = _request()
    assert len(request_bytes(request)) == vectors.REQUEST_CANONICAL_BYTES_A
    assert request_hash(request) == vectors.REQUEST_HASH_A


def test_I03_request_canonical_variant_b() -> None:
    request = _request(("ER-T038-001", "ER-T038-REQ-B"))
    assert len(request_bytes(request)) == vectors.REQUEST_CANONICAL_BYTES_B
    assert request_hash(request) == vectors.REQUEST_HASH_B


def test_I04_all_direct_producer_envelopes_are_explicit() -> None:
    envelopes = vectors.producer_envelopes()
    assert tuple(item.producer_task_id for item in envelopes) == (
        "TASK025",
        "TASK026",
        "TASK035",
        "TASK037",
    )
    assert all(item.branch == "SUCCESS" for item in envelopes)


def test_I05_service_binding_is_approved_and_replays() -> None:
    binding = vectors.service_binding_fixture()
    assert validate_service_binding(binding) == (True, "PASS")
    assert service_binding_hash(binding) == vectors.SERVICE_BINDING_AUTHORITY_HASH
    assert len(service_binding_bytes(binding)) == 770


def test_I06_task026_raw_boundary_replay_uses_producer_contract() -> None:
    raw = vectors.task026_raw_fixture()
    assert task026_raw_replay_hash(raw) == vectors.RAW_FIXTURE_SHA256
    assert len(raw.blockers) == 1
    assert raw.blockers[0].payload == ("str",)


def test_I07_task026_raw_projection_is_single_frame_child() -> None:
    raw = vectors.task026_raw_fixture()
    assert raw.raw_request_projection.canonical_bytes_hex == ""
    assert task026_raw_replay_hash(raw) == vectors.RAW_FIXTURE_SHA256
    assert (
        task026_raw_replay_hash(replace(raw, warnings=("changed",))) != vectors.RAW_FIXTURE_SHA256
    )


def test_I08_producer_replay_dispatch_is_fail_closed_for_unknown_value() -> None:
    for replay in (replay_task025, replay_task026, replay_task035, replay_task037):
        outcome = replay(object())
        assert outcome[0] is False


def test_I09_cross_producer_parent_count_is_exact() -> None:
    assert len(schema.CROSS_PRODUCER_COMPATIBILITY_FIELDS) == 17
    assert tuple(_cross_projection()) == schema.CROSS_PRODUCER_COMPATIBILITY_FIELDS


def test_I10_cross_producer_hash_is_frozen() -> None:
    projection = _cross_projection()
    expected = "17365c90eea8747711d93d5ffdc760905f4ec1731bd84bb971e4084012d9ec8d"
    assert cross_producer_compatibility_hash(projection) == expected
    assert (
        cross_producer_hash(*_valid_join_objects(), vectors.service_binding_fixture()) == expected
    )


def test_I11_j01_to_j17_valid_join() -> None:
    assert validate_cross_producer_joins(
        *_valid_join_objects(), vectors.service_binding_fixture()
    ) == (True, "PASS")


@pytest.mark.parametrize(
    "field",
    (
        "hydraulic_authority_hash",
        "task025_hydraulic_authority_hash",
        "task021_identity",
        "overall_u_reference_surface",
        "tube_side_film_reference_surface",
    ),
)
def test_I12_to_I16_cross_join_tamper_blocks(field: str) -> None:
    task025, task026, task035, task037 = _valid_join_objects()
    if field == "hydraulic_authority_hash":
        task026.upstream_geometry_hash = "0" * 64
    elif field == "task025_hydraulic_authority_hash":
        task037.task025_hydraulic_authority_hash = "0" * 64
    elif field == "task021_identity":
        task037.task021_identity = SimpleNamespace(identity_id="wrong", identity_hash="0" * 64)
    elif field == "overall_u_reference_surface":
        setattr(task037, field, "INNER_TUBE_SURFACE")
    else:
        setattr(task037, field, "OUTER_TUBE_SURFACE")
    assert (
        validate_cross_producer_joins(
            task025, task026, task035, task037, vectors.service_binding_fixture()
        )[0]
        is False
    )


def test_I17_cross_projection_uses_distinct_service_and_stream_fields() -> None:
    task025, task026, task035, task037 = _valid_join_objects()
    projection = build_cross_producer_projection(
        task025, task026, task035, task037, vectors.service_binding_fixture()
    )
    assert (
        projection["task026_property_snapshot_hash"]
        != projection["task025_hydraulic_authority_hash"]
    )
    assert (
        projection["task037_inside_fouling_fluid_service_id"] == vectors.TUBE_SIDE_FLUID_SERVICE_ID
    )


def test_I18_engineering_source_identity_is_typed_and_hashed() -> None:
    sources = vectors.source_identities()
    assert all(validate_engineering_source(source)[0] for source in sources)
    assert tuple(len(engineering_source_identity_hash(source)) for source in sources) == (64, 64)


def test_I19_five_term_resistance_composition() -> None:
    output = compute_resistance_composition(
        gamma=vectors.GV01_GAMMA,
        h_i=vectors.GV01_H_I,
        h_o=vectors.GV01_H_O,
        inside_fouling=vectors.GV01_R_FI_I,
        wall_resistance=vectors.GV01_R_W_O,
        outside_fouling=vectors.GV01_R_FO_O,
    )
    assert (output.r01, output.r02, output.r03, output.r04, output.r05) == (
        vectors.GV01_R01,
        vectors.GV01_R02,
        vectors.GV01_R03,
        vectors.GV01_R04,
        vectors.GV01_R05,
    )
    assert output.total == vectors.GV01_R_TOTAL


def test_I20_resistance_composition_does_not_downquantize_terms() -> None:
    terms = compose_resistances(
        Decimal("1.23456789"),
        Decimal("987.654321"),
        Decimal("876.543219"),
        Decimal("0.000123456789"),
        Decimal("0.000000987654"),
        Decimal("0.000234567891"),
    )
    assert terms[0].as_tuple().exponent == -242


def test_I21_overall_u_public_quantization() -> None:
    resistance, _, _ = gv01()
    assert resistance.overall_u == vectors.GV01_PUBLIC_U
    assert public_u(resistance.overall_u_raw) == vectors.GV01_PUBLIC_U


def test_I22_outer_area_uses_published_inner_area() -> None:
    area = compute_outer_area(
        published_inner_area=vectors.GV01_A_I_PUB,
        gamma=vectors.GV01_GAMMA,
    )
    assert area.raw_outer_area == Decimal("12.00000000000")
    assert area.outer_area == vectors.GV01_PUBLIC_A_O
    assert public_outer_area(area.raw_outer_area) == vectors.GV01_PUBLIC_A_O


def test_I23_ua_uses_public_u_and_public_area() -> None:
    _, _, ua = gv01()
    assert ua.ua == vectors.GV01_PUBLIC_UA
    assert (
        compute_ua(
            public_overall_u=vectors.GV01_PUBLIC_U,
            public_outer_area_value=vectors.GV01_PUBLIC_A_O,
        ).ua
        == vectors.GV01_PUBLIC_UA
    )
    assert public_ua(Decimal("3883.4951456275")) == vectors.GV01_PUBLIC_UA


def test_I24_resistance_authority_hash_is_exact() -> None:
    assert resistance_composition_hash(_resistance_projection()) == (
        "24e272673e1434b5157d121d72d8bc7705a93136a46138eeffc181a0ef3ae39c"
    )


def test_I25_outer_area_authority_hash_is_exact() -> None:
    assert outer_area_projection_hash(_area_projection()) == (
        "ef19ab57c6a052e6d2c211f164ea68eb52b8a00fa7bd02b091a9a932d4d65645"
    )


def test_I26_ua_authority_hash_is_exact() -> None:
    assert ua_composition_hash(_ua_projection()) == (
        "4d32cdbcfaa1c29ae1f6335f02749c1093e0b51c947b2806b8b5b0b7752635e1"
    )


def test_I27_thermal_ledger_has_exact_five_rows() -> None:
    ledger = build_thermal_resistance_ledger(
        task026_transform_hash=vectors.TASK037_SURFACE_TRANSFORM_AUTHORITY_HASH,
        task037_transform_hash=vectors.TASK037_SURFACE_TRANSFORM_AUTHORITY_HASH,
        r01=vectors.GV01_R01,
        r02=vectors.GV01_R02,
        r03=vectors.GV01_R03,
        r04=vectors.GV01_R04,
        r05=vectors.GV01_R05,
    )
    assert tuple(row.term_id for row in ledger) == schema.THERMAL_RESISTANCE_TERM_IDS
    assert all(row.status == "PRESENT_APPLICABLE_COMPATIBLE" for row in ledger)


def test_I28_thermal_ledger_row_identity_is_stable() -> None:
    ledger = build_thermal_resistance_ledger(
        task026_transform_hash=vectors.TASK037_SURFACE_TRANSFORM_AUTHORITY_HASH,
        task037_transform_hash=vectors.TASK037_SURFACE_TRANSFORM_AUTHORITY_HASH,
        r01=vectors.GV01_R01,
        r02=vectors.GV01_R02,
        r03=vectors.GV01_R03,
        r04=vectors.GV01_R04,
        r05=vectors.GV01_R05,
    )
    assert len({thermal_resistance_ledger_row_hash(row) for row in ledger}) == 5


def test_I29_applicability_ledger_order_is_frozen() -> None:
    assert len(schema.APPLICABILITY_ROWS) == 20
    assert schema.APPLICABILITY_ROWS[0] == "A01_TASK025_RESULT_VALID"
    assert schema.APPLICABILITY_ROWS[-1] == "A20_UA_NUMERIC_DOMAIN_VALID"


def test_I30_completeness_ledger_order_is_frozen() -> None:
    assert schema.COMPLETENESS_ROWS == (
        "C01_ALL_DIRECT_PRODUCER_IDENTITIES_COMPLETE",
        "C02_CROSS_PRODUCER_COMPATIBILITY_COMPLETE",
        "C03_RUNTIME_SERVICE_BINDING_COMPLETE",
        "C04_FULL_THERMAL_RESISTANCE_LEDGER_COMPLETE",
        "C05_OVERALL_U_COMPLETE",
        "C06_OUTER_REFERENCE_AREA_COMPLETE",
        "C07_UA_COMPLETE",
        "C08_PROVENANCE_COMPLETE",
        "C09_TASK039_FORWARD_CONSUMER_CONTRACT_COMPLETE",
    )


def test_I31_success_result_requires_complete_ledgers_and_no_partial() -> None:
    result = vectors.result_fixture(
        vectors.REQUEST_HASH_A,
        vectors.provenance_fixture(vectors.REQUEST_HASH_A, vectors.PROVENANCE_HASH_A),
    )
    assert len(result.full_thermal_resistance_composition_ledger) == 5
    assert len(result.applicability_ledger) == 20
    assert len(result.completeness_ledger) == 9
    assert result.warnings == ()
    assert result.blockers == ()


def test_I32_raw_boundary_factory_rejects_non_dict() -> None:
    outcome = build_raw_overall_u_ua_request("not a dict")
    assert isinstance(outcome, Task038RawBoundaryBlockedResult)
    assert outcome.blockers[0].code == "BL_RAW_INPUT_BOUNDARY_MALFORMED"


def test_I33_raw_boundary_factory_requires_exact_fields() -> None:
    outcome = build_raw_overall_u_ua_request({"schema_version": schema.REQUEST_SCHEMA_VERSION})
    assert isinstance(outcome, Task038RawBoundaryBlockedResult)


def test_I34_typed_compute_rejects_untyped_producers() -> None:
    outcome = compute_overall_heat_transfer_coefficient_and_ua(_request())
    assert outcome.__class__.__name__ == "Task038TypedBlockedResult"


def test_I35_evaluate_is_fail_closed() -> None:
    outcome = evaluate_task038(_request())
    assert outcome.status == "BLOCKED"
    assert outcome.success_result is None
    assert outcome.blocked_result is not None


def test_I36_blocker_and_warning_vocabulary_is_closed() -> None:
    assert schema.BLOCKER_ENTRY_NAMESPACE == "task038.blocker-entry.v1"
    assert schema.WARNING_ENTRY_NAMESPACE == "task038.warning-entry.v1"
    assert vectors.task038_blocker().code == "BL_REQUEST_SCHEMA_INVALID"
    assert vectors.task038_warning().code == "WARN_TASK039_FORWARD_CONSUMER_DEFERRED"


def test_I37_typed_blocked_result_hash_excludes_self() -> None:
    blocked = Task038TypedBlockedResult(
        schema_version=schema.TYPED_BLOCKED_RESULT_SCHEMA_VERSION,
        task038_version=schema.TASK038_VERSION,
        implementation_software_version=schema.IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage="S01_REQUEST_AND_AUTHORITY_SCHEMA",
        request_hash=vectors.REQUEST_HASH_A,
        producer_result_identities=vectors.producer_envelopes(),
        blockers=(vectors.task038_blocker(),),
        warnings=(),
        deferred_capabilities=schema.DEFERRED_CAPABILITIES,
        provenance_or_none=None,
        blocked_result_hash="0" * 64,
    )
    from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.canonical import (
        typed_blocked_result_hash,
    )

    assert typed_blocked_result_hash(blocked) != blocked.blocked_result_hash


def test_I38_raw_boundary_result_hash_excludes_self() -> None:
    outcome = build_raw_overall_u_ua_request("not a dict")
    assert isinstance(outcome, Task038RawBoundaryBlockedResult)
    from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.canonical import (
        raw_boundary_blocked_result_hash,
    )

    assert raw_boundary_blocked_result_hash(outcome) == outcome.blocked_result_hash


def test_I39_raw_projection_is_not_reinterpreted() -> None:
    child = b"already canonical"
    assert project_raw_value(child) is child
    assert FrozenRawProjection("RAW_PROJECTION", child.hex()).child_bytes == child


def test_I40_provenance_prehash_and_full_bytes_are_frozen() -> None:
    provenance = _provenance()
    assert (
        len(canonical.provenance_preimage_bytes(provenance)) == vectors.PROVENANCE_PREIMAGE_BYTES_A
    )
    assert len(provenance_bytes(provenance)) == vectors.PROVENANCE_FULL_BYTES_A
    assert provenance_hash(provenance) == vectors.PROVENANCE_HASH_A


def test_I41_provenance_variant_changes_only_declared_request_branch() -> None:
    provenance_a = _provenance()
    provenance_b = _provenance(("ER-T038-001", "ER-T038-REQ-B"))
    assert (
        len(canonical.provenance_preimage_bytes(provenance_b))
        == vectors.PROVENANCE_PREIMAGE_BYTES_B
    )
    assert len(provenance_bytes(provenance_b)) == vectors.PROVENANCE_FULL_BYTES_B
    assert provenance_hash(provenance_b) == vectors.PROVENANCE_HASH_B
    assert provenance_hash(provenance_a) != provenance_hash(provenance_b)


def test_I42_success_result_variant_a_oracle() -> None:
    result = vectors.result_fixture(
        vectors.REQUEST_HASH_A,
        vectors.provenance_fixture(vectors.REQUEST_HASH_A, vectors.PROVENANCE_HASH_A),
    )
    assert len(success_result_bytes(result)) == vectors.SUCCESS_CANONICAL_BYTES_A
    assert success_result_hash(result) == schema.SUCCESS_RESULT_HASH_A
    assert result_id_from_hash(result.result_hash) == schema.RESULT_ID_A


def test_I43_success_result_variant_b_oracle() -> None:
    result = vectors.result_fixture(
        vectors.REQUEST_HASH_B,
        vectors.provenance_fixture(vectors.REQUEST_HASH_B, vectors.PROVENANCE_HASH_B),
    )
    assert len(success_result_bytes(result)) == vectors.SUCCESS_CANONICAL_BYTES_B
    assert success_result_hash(result) == schema.SUCCESS_RESULT_HASH_B
    assert result_id_from_hash(result.result_hash) == schema.RESULT_ID_B


def test_I44_uuid5_result_identity_is_deterministic() -> None:
    assert result_id_from_hash(schema.SUCCESS_RESULT_HASH_A) == vectors.RESULT_ID_A
    assert result_id_from_hash(schema.SUCCESS_RESULT_HASH_B) == vectors.RESULT_ID_B
    assert result_id_from_hash(schema.SUCCESS_RESULT_HASH_A) != result_id_from_hash(
        schema.SUCCESS_RESULT_HASH_B
    )


def test_I45_success_identity_verifier_accepts_frozen_result() -> None:
    result = vectors.result_fixture(
        vectors.REQUEST_HASH_A,
        vectors.provenance_fixture(vectors.REQUEST_HASH_A, vectors.PROVENANCE_HASH_A),
    )
    assert verify_task038_success_identity(result) is True


def test_I46_success_identity_verifier_rejects_hash_tamper() -> None:
    result = vectors.result_fixture(
        vectors.REQUEST_HASH_A,
        vectors.provenance_fixture(vectors.REQUEST_HASH_A, vectors.PROVENANCE_HASH_A),
    )
    tampered = replace(result, result_hash="0" * 64)
    assert verify_task038_success_identity(tampered) is False


@pytest.mark.parametrize("case", tuple(f"T{index:02d}" for index in range(1, 23)))
def test_R1_T01_to_T22_rehashed_semantic_tampering_is_rejected(case: str) -> None:
    tampered = _tampered_rehashed_result(case)
    assert success_result_hash(tampered) == tampered.result_hash
    assert result_id_from_hash(tampered.result_hash) == tampered.result_id
    assert verify_task038_success_identity(tampered) is False


def test_R1_original_rehashed_semantic_exploit_is_rejected() -> None:
    result = vectors.result_fixture(
        vectors.REQUEST_HASH_A,
        vectors.provenance_fixture(vectors.REQUEST_HASH_A, vectors.PROVENANCE_HASH_A),
    )
    tampered = _rehash_tampered_result(
        result,
        full_thermal_resistance_composition_ledger=(
            replace(
                result.full_thermal_resistance_composition_ledger[0],
                value_m2_k_w=Decimal("-1"),
            ),
            *result.full_thermal_resistance_composition_ledger[1:],
        ),
    )
    assert success_result_hash(tampered) == tampered.result_hash
    assert result_id_from_hash(tampered.result_hash) == tampered.result_id
    assert verify_task038_success_identity(tampered) is False


def test_I47_result_hash_has_no_self_reference() -> None:
    result = vectors.result_fixture(
        vectors.REQUEST_HASH_A,
        vectors.provenance_fixture(vectors.REQUEST_HASH_A, vectors.PROVENANCE_HASH_A),
    )
    assert result.result_hash not in success_result_bytes(result).decode("latin1")


def test_I48_gv01_engineering_oracle_is_exact() -> None:
    resistance, area, ua = gv01()
    assert resistance.total == vectors.GV01_R_TOTAL
    assert resistance.overall_u == vectors.GV01_PUBLIC_U
    assert area.outer_area == vectors.GV01_PUBLIC_A_O
    assert ua.ua == vectors.GV01_PUBLIC_UA


def test_I49_decimal_policy_is_frozen() -> None:
    assert schema.ROUNDING_MODE == "ROUND_HALF_EVEN"
    assert schema.TASK038_OVERALL_U_QUANTUM_W_M2_K == "1E-9"
    assert schema.TASK038_OUTER_AREA_QUANTUM_M2 == "1E-10"
    assert schema.TASK038_UA_QUANTUM_W_K == "1E-9"
    assert schema.WORKING_DECIMAL_PRECISION == 200


def test_I50_no_float_engineering_inputs_are_admitted() -> None:
    with pytest.raises(ValueError):
        compute_resistance_composition(
            gamma=1.2,  # type: ignore[arg-type]
            h_i=vectors.GV01_H_I,
            h_o=vectors.GV01_H_O,
            inside_fouling=vectors.GV01_R_FI_I,
            wall_resistance=vectors.GV01_R_W_O,
            outside_fouling=vectors.GV01_R_FO_O,
        )


def test_I51_public_producer_envelope_hash_is_stable() -> None:
    envelope = vectors.producer_envelopes()[0]
    assert producer_envelope_hash(envelope) == producer_envelope_hash(envelope)
    assert len(producer_envelope_hash(envelope)) == 64
    with pytest.raises(ValueError):
        producer_identity_envelope(object())


def test_I52_task039_is_deferred_only() -> None:
    assert "C09_TASK039_FORWARD_CONSUMER_CONTRACT_COMPLETE" in schema.COMPLETENESS_ROWS
    assert "TASK039" not in schema.TASK_ID
    assert "LMTD" in schema.DEFERRED_CAPABILITIES


def test_I53_runtime_stage_order_is_forward_only() -> None:
    assert len(schema.STAGE_ORDER) == 20
    assert schema.STAGE_RANKS[schema.STAGE_ORDER[0]] == 0
    assert schema.STAGE_RANKS[schema.STAGE_ORDER[-1]] == 19
    ranks = tuple(schema.STAGE_RANKS.values())
    assert all(left < right for left, right in zip(ranks, ranks[1:], strict=False))


def test_I54_runtime_provenance_binds_frozen_authorities() -> None:
    provenance = _provenance()
    assert provenance.task_id == "TASK038"
    assert provenance.source_definition_issue == 211
    assert provenance.design_issue == 212
    assert provenance.design_revision == "R4_FINAL_FROZEN"
    assert provenance.base_main_sha == schema.BASE_MAIN_SHA
    assert provenance.base_main_tree == schema.BASE_MAIN_TREE


def test_I55_public_api_does_not_expose_partial_result_branch() -> None:
    result = vectors.result_fixture(
        vectors.REQUEST_HASH_A,
        vectors.provenance_fixture(vectors.REQUEST_HASH_A, vectors.PROVENANCE_HASH_A),
    )
    assert isinstance(result, Task038SuccessResult)
    assert not hasattr(result, "partial_overall_u")
    assert not hasattr(result, "partial_ua")
