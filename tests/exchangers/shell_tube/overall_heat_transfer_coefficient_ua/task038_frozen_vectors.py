"""R4 static TASK-038 identity and engineering oracle vectors."""

from __future__ import annotations

from decimal import Decimal

from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
    BlockerEntry,
    EngineeringSourceIdentity,
    LedgerRow,
    ProducerIdentityEnvelope,
    Task038Provenance,
    Task038Request,
    Task038SuccessResult,
    ThermalResistanceLedgerRow,
    TubeSideServiceBindingAuthority,
    WarningEntry,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.schema import (
    APPLICABILITY_ROWS,
    COMPLETENESS_ROWS,
    DEFERRED_CAPABILITIES,
    ENGINEERING_SOURCE_S01_CLASS,
    ENGINEERING_SOURCE_S01_ID,
    ENGINEERING_SOURCE_S01_LOCATIONS,
    ENGINEERING_SOURCE_S01_PERMISSION,
    ENGINEERING_SOURCE_S01_VERSION,
    ENGINEERING_SOURCE_S02_CLASS,
    ENGINEERING_SOURCE_S02_ID,
    ENGINEERING_SOURCE_S02_LOCATIONS,
    ENGINEERING_SOURCE_S02_PERMISSION,
    ENGINEERING_SOURCE_S02_VERSION,
    IMPLEMENTATION_SOFTWARE_VERSION,
    OVERALL_U_REFERENCE_SURFACE,
    PROFILE_ID,
    REQUEST_SCHEMA_VERSION,
    SUCCESS_RESULT_HASH_A,
    SUCCESS_RESULT_HASH_B,
    SUCCESS_RESULT_SCHEMA_VERSION,
    TASK038_VERSION,
    TUBE_SIDE_FILM_REFERENCE_SURFACE,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    DEFERRED_CAPABILITIES_V1,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.blocker_registry import (
    BlockerEntry as Task026BlockerEntry,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.raw_projection import (
    FrozenRawProjection as Task026FrozenRawProjection,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import (
    RawBoundaryBlockedResult as Task026RawBoundaryBlockedResult,
)

RESULT_ID_A: str = "f169b858-8221-569f-b841-dbfab7179d84"
RESULT_ID_B: str = "b60eb764-ee80-57bc-99e3-df3a52c8be6b"


def _h(pair: str) -> str:
    """Return a synthetic lowercase SHA-256 literal used by the fixture."""

    return pair * 32


TASK025_RESULT_HASH = _h("25")
TASK025_RESULT_ID = "25000000-0000-5000-8000-000000000025"
TASK025_HYDRAULIC_AUTHORITY_HASH = _h("b5")
TASK026_RESULT_HASH = _h("26")
TASK026_RESULT_ID = "26000000-0000-5000-8000-000000000026"
TASK026_PROPERTY_SNAPSHOT_HASH = _h("a6")
TASK035_RESULT_HASH = _h("35")
TASK035_RESULT_ID = "35000000-0000-5000-8000-000000000035"
TASK037_RESULT_HASH = _h("37")
TASK037_RESULT_ID = "37000000-0000-5000-8000-000000000037"
TASK021_LAYOUT_HASH = _h("21")
TASK021_LAYOUT_ID = "TASK021-LAYOUT-FIXTURE-001"
TASK020_CONFIGURATION_HASH = _h("20")
TASK020_CONFIGURATION_ID = "TASK020-CONFIG-FIXTURE-001"
TASK037_SURFACE_TRANSFORM_AUTHORITY_HASH = _h("d7")
TASK037_INSIDE_FOULING_AUTHORITY_HASH = _h("f1")
TASK037_OUTSIDE_FOULING_AUTHORITY_HASH = _h("f2")
TASK037_PRODUCER_AREA_PRECISION_POLICY_HASH = _h("e5")

SERVICE_BINDING_AUTHORITY_HASH = "d8c23d9944d9090d77050d6c10dedccf612b5da39e3d0111437222ec265a71fe"
SERVICE_BINDING_ID = "TSBA-038-FIXTURE-001"
TUBE_SIDE_FLUID_SERVICE_ID = "TUBE-WATER-001"
SHELL_SIDE_FLUID_SERVICE_ID = "SHELL-WATER-001"

REQUEST_HASH_A = "3b5076d5cc1004d1a24d2dbc72677bc3e22b18c256a98214d8e2640c5348cffd"
REQUEST_HASH_B = "eae2ffae128e1e7e078de067005b1afa8c926c9c57cc84c3c3d8c676fc0f03b6"
PROVENANCE_HASH_A = "2fc1206f9343057cd28a113e43fced24ae5eead088bbc798c2c7e3a37e9f7086"
PROVENANCE_HASH_B = "f4e9c105a0586adc9807d0a6e753ae0ea3c6ff6e00001ecf44d16d45a46bfc90"
SUCCESS_CANONICAL_BYTES_A = 12382
SUCCESS_CANONICAL_BYTES_B = 12384
PROVENANCE_PREIMAGE_BYTES_A = 3936
PROVENANCE_PREIMAGE_BYTES_B = 3938
PROVENANCE_FULL_BYTES_A = 4037
PROVENANCE_FULL_BYTES_B = 4039
REQUEST_CANONICAL_BYTES_A = 2184
REQUEST_CANONICAL_BYTES_B = 2186

RAW_FIXTURE_CANONICAL_BYTES = 1390
RAW_FIXTURE_SHA256 = "0b1b69c93361f01ff6ccee9aecf7724ddbca27844c3f0539cd998aaa29ed1433"

GV01_GAMMA = Decimal("1.2")
GV01_H_I = Decimal("1000")
GV01_H_O = Decimal("800")
GV01_R_FI_I = Decimal("0.0002")
GV01_R_W_O = Decimal("0.0001")
GV01_R_FO_O = Decimal("0.0003")
GV01_A_I_PUB = Decimal("10.0000000000")
GV01_R01 = Decimal("0.0012")
GV01_R02 = Decimal("0.00024")
GV01_R03 = Decimal("0.0001")
GV01_R04 = Decimal("0.0003")
GV01_R05 = Decimal("0.00125")
GV01_R_TOTAL = Decimal("0.00309")
GV01_PUBLIC_U = Decimal("323.624595469")
GV01_PUBLIC_A_O = Decimal("12.0000000000")
GV01_PUBLIC_UA = Decimal("3883.495145628")

CANONICAL_CODEC_PROBES = (
    (
        "none",
        "000000044e4f4e450000000000000000",
        "35374d759a6cd2beccaeb7c1df8481e04bdd7c5fe4623f2dc3a5fadd21436f30",
    ),
    (
        "bool_true",
        "00000009424f4f4c5f545255450000000000000000",
        "2564db23695c4ada3ee24ef7d87258ed0768aed19290e21ac31cd9a05b655244",
    ),
    (
        "bool_false",
        "0000000a424f4f4c5f46414c53450000000000000000",
        "ac2b752131e8e0e7d65e7abbfb2d891b117c338e614c3a95d1687ce7a66d18d1",
    ),
    (
        "int",
        "00000003494e5400000000000000022d37",
        "62625783247ebd2e82e4c8a97db55d9acdf5ea2a8b0e4d035bcc02c0b5dd1ab7",
    ),
    (
        "string_utf8",
        "00000006535452494e47000000000000000368c3a9",
        "8e724023965e37d9da339f3138e0c9990ec98c33c18486c29e351a1b2e5dc6e0",
    ),
    (
        "decimal",
        "00000007444543494d414c000000000000000531452d3130",
        "fe0d44869edf7c326df7ddbcdcd7dd4d6d1aa18e8d7404f21617acc442aca67b",
    ),
    (
        "enum",
        "00000004454e554d0000000000000012494e4e45525f545542455f53555246414345",
        "839cc8b26d8bcaa7634cf841cd676c00b10a70e1a4788ab83b5aa3c39a9e543e",
    ),
    (
        "tuple_utf8",
        "000000055455504c45000000000000000f00000002000000016100000002c3a9",
        "c0483d5b1aca90dab8f3661d9dd380fc8865041d4653695a78a17ed30c7312e5",
    ),
    (
        "record",
        "0000000870726f62652e7631000000010000000576616c756500000006535452494e47000000000000000176",
        "bcdecd4e08ef1da598ce45a508ad417293d6bd3b377294e1a9ce2a45b7dc22be",
    ),
    (
        "nested_record",
        "000000065245434f5244000000000000002d000000096e65737465642e7631000000010000000576616c756500000006535452494e47000000000000000176",
        "c6ba22b5181e95aed772c0f4d5c378bf3c3011024a7851fcd3537eecc0f8b402",
    ),
)


def service_binding_fixture() -> TubeSideServiceBindingAuthority:
    return TubeSideServiceBindingAuthority(
        authority_id=SERVICE_BINDING_ID,
        tube_side_fluid_service_id=TUBE_SIDE_FLUID_SERVICE_ID,
        task026_result_hash=TASK026_RESULT_HASH,
        task026_property_snapshot_hash=TASK026_PROPERTY_SNAPSHOT_HASH,
        source_id="EB-T038-TUBE-SERVICE-001",
        source_version="v1",
        source_location="CASE-001/TUBE-SERVICE",
        source_class="APPROVED_ENGINEERING_BASIS",
        permission_status="INTERNAL_USE_AUTHORIZED",
        approval_status="APPROVED",
        evidence_refs=("ER-BIND-001",),
        authority_hash=SERVICE_BINDING_AUTHORITY_HASH,
    )


def source_identities() -> tuple[EngineeringSourceIdentity, ...]:
    return (
        EngineeringSourceIdentity(
            ENGINEERING_SOURCE_S01_ID,
            ENGINEERING_SOURCE_S01_VERSION,
            ENGINEERING_SOURCE_S01_CLASS,
            ENGINEERING_SOURCE_S01_LOCATIONS,
            ENGINEERING_SOURCE_S01_PERMISSION,
        ),
        EngineeringSourceIdentity(
            ENGINEERING_SOURCE_S02_ID,
            ENGINEERING_SOURCE_S02_VERSION,
            ENGINEERING_SOURCE_S02_CLASS,
            ENGINEERING_SOURCE_S02_LOCATIONS,
            ENGINEERING_SOURCE_S02_PERMISSION,
        ),
    )


def producer_envelopes() -> tuple[ProducerIdentityEnvelope, ...]:
    return (
        ProducerIdentityEnvelope(
            "TASK025", "SUCCESS", TASK025_RESULT_ID, TASK025_RESULT_HASH, TASK025_RESULT_HASH
        ),
        ProducerIdentityEnvelope(
            "TASK026", "SUCCESS", TASK026_RESULT_ID, TASK026_RESULT_HASH, TASK026_RESULT_HASH
        ),
        ProducerIdentityEnvelope(
            "TASK035", "SUCCESS", TASK035_RESULT_ID, TASK035_RESULT_HASH, TASK035_RESULT_HASH
        ),
        ProducerIdentityEnvelope(
            "TASK037", "SUCCESS", TASK037_RESULT_ID, TASK037_RESULT_HASH, TASK037_RESULT_HASH
        ),
    )


def request_fixture(refs: tuple[str, ...] = ("ER-T038-001", "ER-T038-002")) -> Task038Request:
    task025, task026, task035, task037 = producer_envelopes()
    return Task038Request(
        schema_version=REQUEST_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        task025_result=task025,
        task026_result=task026,
        task035_result=task035,
        task037_result=task037,
        tube_side_service_binding_authority=service_binding_fixture(),
        evidence_refs=refs,
    )


def provenance_fixture(request_hash: str, terminal_hash: str) -> Task038Provenance:
    return Task038Provenance(
        task_id="TASK038",
        source_definition_issue=211,
        source_definition_revision="R1_FROZEN",
        design_issue=212,
        design_revision="R4_FINAL_FROZEN",
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        base_main_sha="9a6ca44726357b683590b51d2d727002ca756d2e",
        base_main_tree="e57ee630365b87ffff70b93d89e070de55461374",
        baseline_repair_governance_comment_id="5472639060",
        request_hash=request_hash,
        task025_result_hash=TASK025_RESULT_HASH,
        task025_result_id=TASK025_RESULT_ID,
        task025_hydraulic_authority_hash=TASK025_HYDRAULIC_AUTHORITY_HASH,
        task026_result_hash=TASK026_RESULT_HASH,
        task026_result_id=TASK026_RESULT_ID,
        task026_property_snapshot_hash=TASK026_PROPERTY_SNAPSHOT_HASH,
        task035_result_hash=TASK035_RESULT_HASH,
        task035_result_id=TASK035_RESULT_ID,
        task035_shell_side_fluid_id=SHELL_SIDE_FLUID_SERVICE_ID,
        task037_result_hash=TASK037_RESULT_HASH,
        task037_result_id=TASK037_RESULT_ID,
        task037_surface_transform_authority_hash=TASK037_SURFACE_TRANSFORM_AUTHORITY_HASH,
        task037_inside_fouling_authority_hash=TASK037_INSIDE_FOULING_AUTHORITY_HASH,
        task037_outside_fouling_authority_hash=TASK037_OUTSIDE_FOULING_AUTHORITY_HASH,
        task037_task025_area_quantum_m2=Decimal("1E-10"),
        task037_task025_area_rounding_mode="ROUND_HALF_EVEN",
        task037_producer_area_precision_policy_id=(
            "task037.task025-public-area-authority.accept-positive-v1"
        ),
        task037_producer_area_precision_policy_hash=TASK037_PRODUCER_AREA_PRECISION_POLICY_HASH,
        task037_producer_precision_limitation_disclosed=True,
        task037_producer_precision_threshold_defined=False,
        tube_side_service_binding_authority_hash=SERVICE_BINDING_AUTHORITY_HASH,
        engineering_source_identity_hashes=(
            "5e939001be060fcd044121b442e9b0cbbea078f869bfa8e83d688bf4c8b5f024",
            "8f53a07ab56efebbaee392e79772c09d60ba49500f1045f65b36181d97d68da3",
        ),
        cross_producer_compatibility_hash=(
            "17365c90eea8747711d93d5ffdc760905f4ec1731bd84bb971e4084012d9ec8d"
        ),
        resistance_composition_authority_hash=(
            "24e272673e1434b5157d121d72d8bc7705a93136a46138eeffc181a0ef3ae39c"
        ),
        outer_area_projection_authority_hash=(
            "ef19ab57c6a052e6d2c211f164ea68eb52b8a00fa7bd02b091a9a932d4d65645"
        ),
        ua_composition_authority_hash=(
            "4d32cdbcfaa1c29ae1f6335f02749c1093e0b51c947b2806b8b5b0b7752635e1"
        ),
        overall_u_reference_surface=OVERALL_U_REFERENCE_SURFACE,
        modeled_overall_heat_transfer_coefficient_w_m2_k=Decimal("323.624595469"),
        outer_tube_surface_effective_area_m2=Decimal("12.0000000000"),
        modeled_ua_w_k=Decimal("3883.495145628"),
        evidence_refs=("ER-T038-001", "ER-T038-002")
        if request_hash == REQUEST_HASH_A
        else ("ER-T038-001", "ER-T038-REQ-B"),
        deferred_capabilities=DEFERRED_CAPABILITIES,
        provenance_hash=terminal_hash,
    )


def resistance_rows() -> tuple[ThermalResistanceLedgerRow, ...]:
    status = "PRESENT_APPLICABLE_COMPATIBLE"
    return (
        ThermalResistanceLedgerRow(
            "R01_TUBE_SIDE_FILM_OUTER_REFERENCE",
            "TASK026",
            "TASK026.tube_side_heat_transfer_coefficient_w_m2_k",
            TUBE_SIDE_FILM_REFERENCE_SURFACE,
            OVERALL_U_REFERENCE_SURFACE,
            TASK037_SURFACE_TRANSFORM_AUTHORITY_HASH,
            Decimal("0.0012"),
            status,
        ),
        ThermalResistanceLedgerRow(
            "R02_INSIDE_FOULING_OUTER_REFERENCE",
            "TASK037",
            "TASK037.inside_fouling_authority.fouling_resistance_m2_k_w",
            TUBE_SIDE_FILM_REFERENCE_SURFACE,
            OVERALL_U_REFERENCE_SURFACE,
            TASK037_SURFACE_TRANSFORM_AUTHORITY_HASH,
            Decimal("0.00024"),
            status,
        ),
        ThermalResistanceLedgerRow(
            "R03_TUBE_WALL_CONDUCTION_OUTER_REFERENCE",
            "TASK037",
            "TASK037.wall_resistance_outer_surface_m2_k_w",
            OVERALL_U_REFERENCE_SURFACE,
            OVERALL_U_REFERENCE_SURFACE,
            None,
            Decimal("0.0001"),
            status,
        ),
        ThermalResistanceLedgerRow(
            "R04_OUTSIDE_FOULING_OUTER_REFERENCE",
            "TASK037",
            "TASK037.outside_fouling_authority.fouling_resistance_m2_k_w",
            OVERALL_U_REFERENCE_SURFACE,
            OVERALL_U_REFERENCE_SURFACE,
            None,
            Decimal("0.0003"),
            status,
        ),
        ThermalResistanceLedgerRow(
            "R05_SHELL_SIDE_FILM_OUTER_REFERENCE",
            "TASK035",
            "TASK035.modeled_shell_side_heat_transfer_coefficient_w_m2_k",
            OVERALL_U_REFERENCE_SURFACE,
            OVERALL_U_REFERENCE_SURFACE,
            None,
            Decimal("0.00125"),
            status,
        ),
    )


def result_fixture(request_hash: str, provenance: Task038Provenance) -> Task038SuccessResult:
    return Task038SuccessResult(
        schema_version=SUCCESS_RESULT_SCHEMA_VERSION,
        task038_version=TASK038_VERSION,
        profile_id=PROFILE_ID,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        request_hash=request_hash,
        overall_u_reference_surface=OVERALL_U_REFERENCE_SURFACE,
        full_thermal_resistance_composition_ledger=resistance_rows(),
        modeled_overall_heat_transfer_coefficient_w_m2_k=Decimal("323.624595469"),
        outer_tube_surface_effective_area_m2=Decimal("12.0000000000"),
        modeled_ua_w_k=Decimal("3883.495145628"),
        applicability_ledger=tuple(LedgerRow(row_id, "PASS") for row_id in APPLICABILITY_ROWS),
        completeness_ledger=tuple(LedgerRow(row_id, "PASS") for row_id in COMPLETENESS_ROWS),
        warnings=tuple(),
        blockers=tuple(),
        deferred_capabilities=DEFERRED_CAPABILITIES,
        provenance=provenance,
        result_hash=(
            SUCCESS_RESULT_HASH_A if request_hash == REQUEST_HASH_A else SUCCESS_RESULT_HASH_B
        ),
        result_id=(RESULT_ID_A if request_hash == REQUEST_HASH_A else RESULT_ID_B),
    )


def task026_raw_fixture() -> Task026RawBoundaryBlockedResult:
    """Construct the real Task026 raw-boundary model for replay tests."""

    return Task026RawBoundaryBlockedResult(
        raw_request_projection=Task026FrozenRawProjection("RAW_PROJECTION", ""),
        blockers=(
            Task026BlockerEntry(
                "BL_RAW_INPUT_BOUNDARY_MALFORMED",
                "hard",
                "S00",
                ("str",),
                "raw input must be a built-in dict; got {actual_type}",
            ),
        ),
        warnings=(),
        deferred_capabilities=DEFERRED_CAPABILITIES_V1,
        schema_version="task026-r7.schema.v1",
        implementation_software_version="task026-local-impl-r8",
    )


def task038_blocker() -> BlockerEntry:
    return BlockerEntry(
        "BL_REQUEST_SCHEMA_INVALID",
        "S01_REQUEST_AND_AUTHORITY_SCHEMA",
        "request",
        "request_schema_invalid",
        (("reason", "invalid"),),
    )


def task038_warning() -> WarningEntry:
    return WarningEntry("WARN_TASK039_FORWARD_CONSUMER_DEFERRED", None, "deferred")


__all__ = [name for name in globals() if not name.startswith("_")]
