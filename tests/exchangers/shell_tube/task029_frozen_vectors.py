"""TASK-029 frozen external oracle vector fixtures.

I15: external acceptance authority only. Expected hashes, UUIDs, and canonical
expectations are hard-coded literals from Design Contract R5 §16. This module
must never import or invoke the system under test (SUT).
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Final

# ---------------------------------------------------------------------------
# Oracle vector expected values (external authority — do not recompute)
# ---------------------------------------------------------------------------

ORACLE_VECTOR_COUNT: Final[int] = 8

VECTOR_01_M000_HASH_INPUT_LEN: Final[int] = 798
VECTOR_01_M000_HASH: Final[str] = "9fdd83ffcaed0e03cc2178023a1b2dd084bfe85a8f9396c9cf2f41059009868e"

VECTOR_02_M001_HASH_INPUT_LEN: Final[int] = 767
VECTOR_02_M001_HASH: Final[str] = "e590c0a0f9a60c8088da7c8e8d8220cd274dc703da3c3daedd65de88a05c0929"

VECTOR_03_COMPOSITION_HASH_INPUT_LEN: Final[int] = 6840
VECTOR_03_COMPOSITION_HASH: Final[str] = (
    "71b540bfe29373cd6056f8cf3f9098fe9d126c82b06856e158fc844a357c7553"
)
VECTOR_03_CALLER_MEMBER_ORDER_PERMUTATION_HASH: Final[str] = VECTOR_03_COMPOSITION_HASH

VECTOR_04_REQUEST_HASH_INPUT_LEN: Final[int] = 881
VECTOR_04_REQUEST_HASH: Final[str] = (
    "23f0d73c8e5c3dd531570723c09c2ea57b1a059213c0445c91690d5ee5c4167c"
)

VECTOR_05_LEDGER_HASH_INPUT_LEN: Final[int] = 7567
VECTOR_05_LEDGER_HASH: Final[str] = (
    "9fa0fc68a33ec81e551b0fa79557f62e3b4fdb6eb461a1d43b4cc8514f9c949c"
)

VECTOR_06_SUCCESS_HASH_INPUT_LEN: Final[int] = 10505
VECTOR_06_SUCCESS_RESULT_HASH: Final[str] = (
    "1fa5ef8a46de30132e4540be87b1b38f6098ce65aa60fb301eb85480309690d4"
)
VECTOR_06_SUCCESS_RESULT_ID: Final[str] = "eeaad53c-5843-52d4-9a7e-3e0c4511976f"
VECTOR_06_MODELED_TOTAL: Final[Decimal] = Decimal("351.504")

VECTOR_07_TYPED_BLOCKED_HASH_INPUT_LEN: Final[int] = 22660
VECTOR_07_TYPED_BLOCKED_RESULT_HASH: Final[str] = (
    "264c9e50a528a77cae05ccd00d2e1e31029c347eb694be431bd646c9b94ed5f1"
)
VECTOR_07_TYPED_BLOCKED_RESULT_ID: Final[str] = "3ea9058b-f2c2-5e7d-a0ef-451b83d2a5bb"

VECTOR_08_RAW_BOUNDARY_CANONICAL_LEN: Final[int] = 21849
VECTOR_08_RAW_BOUNDARY_CANONICAL_SHA256: Final[str] = (
    "5a2f17fcd7b93132007647cd6271b18e8aef7f4cf976ea950c81fceb8b0b87d5"
)

VALID_RAW_REQUEST_CANONICAL_LEN: Final[int] = 10276
VALID_RAW_REQUEST_CANONICAL_SHA256: Final[str] = (
    "fb47b48015c0af1b838efcaafa51c6dc759295370fe7fd73b8ad6cda63fe1dcd"
)

UNKNOWN_RAW_REQUEST_CANONICAL_LEN: Final[int] = 10347
UNKNOWN_RAW_REQUEST_CANONICAL_SHA256: Final[str] = (
    "251aeca74385642f788d827b3e836a90c0a30ae974d1f5ca0bb5381257fa7f4e"
)

# ---------------------------------------------------------------------------
# Common synthetic oracle inputs (§16.1)
#
# THESE_ARE_OPAQUE_SYNTHETIC_ORACLE_INPUTS
# NOT_PRODUCTION_REPLAY_EXPECTATIONS
# ---------------------------------------------------------------------------

PROFILE_ID: Final[str] = "profile-001"

TASK025_HYDRAULIC_AUTHORITY_HASH: Final[str] = (
    "2525252525252525252525252525252525252525252525252525252525252525"
)
TASK025_RESULT_HASH: Final[str] = "1515151515151515151515151515151515151515151515151515151515151515"
TASK026_RESULT_HASH: Final[str] = "2626262626262626262626262626262626262626262626262626262626262626"
TASK027_RESULT_HASH: Final[str] = "2727272727272727272727272727272727272727272727272727272727272727"
TASK028_RESULT_HASH: Final[str] = "2828282828282828282828282828282828282828282828282828282828282828"
PROPERTY_SNAPSHOT_HASH: Final[str] = (
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
)
PROPERTY_SNAPSHOT_HASH_MISMATCH: Final[str] = (
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
)
TASK028_COMPONENT_AUTHORITY_HASH: Final[str] = (
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
)

TASK029_REQUEST_SCHEMA_VERSION: Final[str] = "task029.request.v1"
MEMBER_AUTHORITY_SCHEMA_VERSION: Final[str] = "task029.pressure-path-member-authority.v1"
EXCLUSION_AUTHORITY_SCHEMA_VERSION: Final[str] = "task029.pressure-path-exclusion-authority.v1"
COMPOSITION_AUTHORITY_SCHEMA_VERSION: Final[str] = "task029.pressure-path-composition-authority.v1"
LEDGER_MEMBER_EVIDENCE_SCHEMA_VERSION: Final[str] = "task029.ledger-member-evidence.v1"
LEDGER_EXCLUSION_EVIDENCE_SCHEMA_VERSION: Final[str] = "task029.ledger-exclusion-evidence.v1"
COMPLETENESS_LEDGER_SCHEMA_VERSION: Final[str] = "task029.completeness-ledger.v1"
PROVENANCE_SCHEMA_VERSION: Final[str] = "task029.provenance.v1"
IMPLEMENTATION_SOFTWARE_VERSION: Final[str] = "0.2.0-dev"
TASK029_DESIGN_CONTRACT_PATH: Final[str] = (
    "docs/tasks/TASK-029-shell-and-tube-tube-side-modeled-total-pressure-drop-composition.md"
)

INPUT_EVIDENCE_REFS: Final[tuple[str, ...]] = (
    "github-issue:xuezhiorange-png/hxforge-agent#167",
    "github-issue:xuezhiorange-png/hxforge-agent#173",
    "git-commit:6dd4bfa81a330fb36eec4cb262664184657279d4",
)

# Frozen §15.6 / §10.6 upstream synthetic oracle tuple order.
SYNTHETIC_UPSTREAM_IDENTITY_HASHES: Final[tuple[str, ...]] = (
    TASK027_RESULT_HASH,
    TASK028_RESULT_HASH,
    TASK025_HYDRAULIC_AUTHORITY_HASH,
    TASK025_RESULT_HASH,
    TASK026_RESULT_HASH,
    PROPERTY_SNAPSHOT_HASH,
    VECTOR_03_COMPOSITION_HASH,
)

# ---------------------------------------------------------------------------
# Member authority fixtures (pure literals)
# ---------------------------------------------------------------------------

M000_MEMBER_AUTHORITY_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": MEMBER_AUTHORITY_SCHEMA_VERSION,
    "member_id": "M000",
    "global_path_sequence_index": 0,
    "producer_task": "TASK-028",
    "producer_member_kind": "LOCAL_MINOR_LOSS",
    "producer_component_identity": "ENTRANCE-001",
    "expected_producer_component_type": "ENTRANCE",
    "expected_producer_authority_hash": TASK028_COMPONENT_AUTHORITY_HASH,
    "expected_upstream_reference_plane": "P0",
    "expected_downstream_reference_plane": "P1",
    "expected_multiplicity": 1,
    "geometry_evidence_refs": ("geom:entrance-001",),
    "member_authority_hash": VECTOR_01_M000_HASH,
}

M001_MEMBER_AUTHORITY_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": MEMBER_AUTHORITY_SCHEMA_VERSION,
    "member_id": "M001",
    "global_path_sequence_index": 1,
    "producer_task": "TASK-027",
    "producer_member_kind": "DISTRIBUTED_FRICTION",
    "producer_component_identity": "STRAIGHT_TUBE_FRICTION",
    "expected_producer_component_type": "STRAIGHT_TUBE_FRICTION",
    "expected_producer_authority_hash": "",
    "expected_upstream_reference_plane": "P1",
    "expected_downstream_reference_plane": "P2",
    "expected_multiplicity": 1,
    "geometry_evidence_refs": ("geom:straight-tube-001",),
    "member_authority_hash": VECTOR_02_M001_HASH,
}

# ---------------------------------------------------------------------------
# Exclusion authority fixtures X000–X008 (pure literals)
# ---------------------------------------------------------------------------

EXCLUSION_X000_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": EXCLUSION_AUTHORITY_SCHEMA_VERSION,
    "exclusion_id": "X000",
    "excluded_item_identity": "PASS_PARTITION",
    "exclusion_reason": "V0_2_OUT_OF_SCOPE",
    "evidence_refs": ("scope:issue-167:PASS_PARTITION",),
    "exclusion_authority_hash": (
        "bee97445787a8691d612f1e499974d5d98bf796daf8eb85ee6a305e1c1db66f5"
    ),
}

EXCLUSION_X001_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": EXCLUSION_AUTHORITY_SCHEMA_VERSION,
    "exclusion_id": "X001",
    "excluded_item_identity": "RETURN_HEADER",
    "exclusion_reason": "V0_2_OUT_OF_SCOPE",
    "evidence_refs": ("scope:issue-167:RETURN_HEADER",),
    "exclusion_authority_hash": (
        "074222c90396856d5bdfefbdac658cdb88fdd6c6613c8c46d48c77d56c9273b3"
    ),
}

EXCLUSION_X002_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": EXCLUSION_AUTHORITY_SCHEMA_VERSION,
    "exclusion_id": "X002",
    "excluded_item_identity": "RETURN_BEND",
    "exclusion_reason": "V0_2_OUT_OF_SCOPE",
    "evidence_refs": ("scope:issue-167:RETURN_BEND",),
    "exclusion_authority_hash": (
        "c735b960365ea7fbfa10ec2f274f33a0d5d3ae0b70f2fcee6947bd1178f45b50"
    ),
}

EXCLUSION_X003_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": EXCLUSION_AUTHORITY_SCHEMA_VERSION,
    "exclusion_id": "X003",
    "excluded_item_identity": "U_BEND",
    "exclusion_reason": "V0_2_OUT_OF_SCOPE",
    "evidence_refs": ("scope:issue-167:U_BEND",),
    "exclusion_authority_hash": (
        "6d7a3dbeea4baab43c6323abc4a58c5c49aaf32751c9498baf526ed4a39a1d74"
    ),
}

EXCLUSION_X004_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": EXCLUSION_AUTHORITY_SCHEMA_VERSION,
    "exclusion_id": "X004",
    "excluded_item_identity": "EXIT",
    "exclusion_reason": "PHYSICALLY_ABSENT",
    "evidence_refs": ("geom:absent:EXIT",),
    "exclusion_authority_hash": (
        "2ca5491f5202b4149c38dab27b94d312c1b33445885936a039d156166f248111"
    ),
}

EXCLUSION_X005_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": EXCLUSION_AUTHORITY_SCHEMA_VERSION,
    "exclusion_id": "X005",
    "excluded_item_identity": "CHANNEL_HEAD",
    "exclusion_reason": "PHYSICALLY_ABSENT",
    "evidence_refs": ("geom:absent:CHANNEL_HEAD",),
    "exclusion_authority_hash": (
        "30a352a0e866803ec771040a337fc3f130c2e4548da898387c2fc49973146b54"
    ),
}

EXCLUSION_X006_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": EXCLUSION_AUTHORITY_SCHEMA_VERSION,
    "exclusion_id": "X006",
    "excluded_item_identity": "NOZZLE",
    "exclusion_reason": "PHYSICALLY_ABSENT",
    "evidence_refs": ("geom:absent:NOZZLE",),
    "exclusion_authority_hash": (
        "154f6afc091f29b57f6d5a28b72c523b8f49aedee9465c587c62e728bc261d78"
    ),
}

EXCLUSION_X007_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": EXCLUSION_AUTHORITY_SCHEMA_VERSION,
    "exclusion_id": "X007",
    "excluded_item_identity": "CONTRACTION",
    "exclusion_reason": "PHYSICALLY_ABSENT",
    "evidence_refs": ("geom:absent:CONTRACTION",),
    "exclusion_authority_hash": (
        "a05b3f97c842dc20a20124e2430fe7d7b9741c44d64ea62d1c4beff9b82321df"
    ),
}

EXCLUSION_X008_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": EXCLUSION_AUTHORITY_SCHEMA_VERSION,
    "exclusion_id": "X008",
    "excluded_item_identity": "EXPANSION",
    "exclusion_reason": "PHYSICALLY_ABSENT",
    "evidence_refs": ("geom:absent:EXPANSION",),
    "exclusion_authority_hash": (
        "27716ef6ae1b93b878d07cece5c8aeb1bc32bdd30e0872fa01bb8b977d271b66"
    ),
}

EXCLUSION_AUTHORITY_FIXTURES: Final[tuple[Mapping[str, Any], ...]] = (
    EXCLUSION_X000_FIXTURE,
    EXCLUSION_X001_FIXTURE,
    EXCLUSION_X002_FIXTURE,
    EXCLUSION_X003_FIXTURE,
    EXCLUSION_X004_FIXTURE,
    EXCLUSION_X005_FIXTURE,
    EXCLUSION_X006_FIXTURE,
    EXCLUSION_X007_FIXTURE,
    EXCLUSION_X008_FIXTURE,
)

# ---------------------------------------------------------------------------
# Composition fixture
# ---------------------------------------------------------------------------

COMPOSITION_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": COMPOSITION_AUTHORITY_SCHEMA_VERSION,
    "modeled_path_id": "tube-side-path-001",
    "flow_direction_assertion": "START_TO_END",
    "start_reference_plane": "P0",
    "end_reference_plane": "P2",
    "member_authorities": (
        M000_MEMBER_AUTHORITY_FIXTURE,
        M001_MEMBER_AUTHORITY_FIXTURE,
    ),
    "exclusion_authorities": EXCLUSION_AUTHORITY_FIXTURES,
    "geometry_evidence_refs": ("geom:path-001",),
    "composition_authority_hash": VECTOR_03_COMPOSITION_HASH,
}

# ---------------------------------------------------------------------------
# Ledger member / exclusion evidence fixtures (synthetic oracle ledger)
# ---------------------------------------------------------------------------

LEDGER_MEMBER_M000_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": LEDGER_MEMBER_EVIDENCE_SCHEMA_VERSION,
    "member_id": "M000",
    "global_path_sequence_index": 0,
    "producer_task": "TASK-028",
    "producer_result_hash": TASK028_RESULT_HASH,
    "producer_member_kind": "LOCAL_MINOR_LOSS",
    "producer_component_identity": "ENTRANCE-001",
    "producer_component_type": "ENTRANCE",
    "producer_authority_hash": TASK028_COMPONENT_AUTHORITY_HASH,
    "upstream_reference_plane": "P0",
    "downstream_reference_plane": "P1",
    "expected_multiplicity": 1,
    "observed_multiplicity": 1,
    "pressure_contribution_pa": Decimal("101.504"),
    "composition_member_authority_hash": VECTOR_01_M000_HASH,
    "member_status": "VERIFIED",
}

LEDGER_MEMBER_M001_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": LEDGER_MEMBER_EVIDENCE_SCHEMA_VERSION,
    "member_id": "M001",
    "global_path_sequence_index": 1,
    "producer_task": "TASK-027",
    "producer_result_hash": TASK027_RESULT_HASH,
    "producer_member_kind": "DISTRIBUTED_FRICTION",
    "producer_component_identity": "STRAIGHT_TUBE_FRICTION",
    "producer_component_type": "STRAIGHT_TUBE_FRICTION",
    "producer_authority_hash": "",
    "upstream_reference_plane": "P1",
    "downstream_reference_plane": "P2",
    "expected_multiplicity": 1,
    "observed_multiplicity": 1,
    "pressure_contribution_pa": Decimal("250.000"),
    "composition_member_authority_hash": VECTOR_02_M001_HASH,
    "member_status": "VERIFIED",
}

LEDGER_MEMBER_FIXTURES: Final[tuple[Mapping[str, Any], ...]] = (
    LEDGER_MEMBER_M000_FIXTURE,
    LEDGER_MEMBER_M001_FIXTURE,
)

LEDGER_EXCLUSION_FIXTURES: Final[tuple[Mapping[str, Any], ...]] = tuple(
    {
        "schema_version": LEDGER_EXCLUSION_EVIDENCE_SCHEMA_VERSION,
        "exclusion_id": exclusion["exclusion_id"],
        "excluded_item_identity": exclusion["excluded_item_identity"],
        "exclusion_reason": exclusion["exclusion_reason"],
        "evidence_refs": exclusion["evidence_refs"],
        "exclusion_authority_hash": exclusion["exclusion_authority_hash"],
        "exclusion_status": "VERIFIED_EXCLUSION",
    }
    for exclusion in EXCLUSION_AUTHORITY_FIXTURES
)

LEDGER_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": COMPLETENESS_LEDGER_SCHEMA_VERSION,
    "modeled_path_id": "tube-side-path-001",
    "modeled_start_reference_plane": "P0",
    "modeled_end_reference_plane": "P2",
    "expected_member_count": 2,
    "observed_member_count": 2,
    "ordered_member_evidence": LEDGER_MEMBER_FIXTURES,
    "ordered_exclusion_evidence": LEDGER_EXCLUSION_FIXTURES,
    "path_continuity_status": "CONTIGUOUS_EXACT_REFERENCE_PLANE_CHAIN",
    "identity_compatibility_status": "MATCHED",
    "completeness_status": "COMPLETE_WITHIN_EXPLICIT_MODELED_BOUNDARY",
    "ledger_hash": VECTOR_05_LEDGER_HASH,
}

# ---------------------------------------------------------------------------
# Success provenance fixture
# ---------------------------------------------------------------------------

SUCCESS_PROVENANCE_FIXTURE: Final[Mapping[str, Any]] = {
    "schema_version": PROVENANCE_SCHEMA_VERSION,
    "task_id": "TASK-029",
    "design_contract_path": TASK029_DESIGN_CONTRACT_PATH,
    "implementation_software_version": IMPLEMENTATION_SOFTWARE_VERSION,
    "input_evidence_refs": INPUT_EVIDENCE_REFS,
    "upstream_identity_hashes": SYNTHETIC_UPSTREAM_IDENTITY_HASHES,
}

# ---------------------------------------------------------------------------
# Typed blocked fixture (VECTOR_07 upstream identity mismatch)
# ---------------------------------------------------------------------------

TYPED_BLOCKED_FIXTURE: Final[Mapping[str, Any]] = {
    "profile_id": PROFILE_ID,
    "request_hash": VECTOR_04_REQUEST_HASH,
    "composition_authority_hash": VECTOR_03_COMPOSITION_HASH,
    "task027_result_hash": TASK027_RESULT_HASH,
    "task028_result_hash": TASK028_RESULT_HASH,
    "task025_hydraulic_authority_hash": TASK025_HYDRAULIC_AUTHORITY_HASH,
    "task025_result_hash": TASK025_RESULT_HASH,
    "task026_result_hash": TASK026_RESULT_HASH,
    "property_snapshot_hash": PROPERTY_SNAPSHOT_HASH_MISMATCH,
    "blocker_code": "BL_T029_UPSTREAM_IDENTITY_MISMATCH",
    "blocker_field_path": "task028_success_result.property_snapshot_hash",
    "expected_result_hash": VECTOR_07_TYPED_BLOCKED_RESULT_HASH,
    "expected_result_id": VECTOR_07_TYPED_BLOCKED_RESULT_ID,
}

# ---------------------------------------------------------------------------
# Raw request fixtures (frozen insertion order)
# ---------------------------------------------------------------------------

_VALID_RAW_REQUEST_BODY: Final[dict[str, Any]] = {
    "schema_version": TASK029_REQUEST_SCHEMA_VERSION,
    "profile_id": PROFILE_ID,
    "composition_authority": COMPOSITION_FIXTURE,
    "request_hash": VECTOR_04_REQUEST_HASH,
}

VALID_RAW_REQUEST: Final[Mapping[str, Any]] = _VALID_RAW_REQUEST_BODY

UNKNOWN_FIELD_RAW_REQUEST: Final[Mapping[str, Any]] = {
    **_VALID_RAW_REQUEST_BODY,
    "unexpected": "x",
}


def copy_valid_raw_request_fixture() -> dict[str, Any]:
    """Return a deep copy of the frozen valid raw request fixture."""
    return copy.deepcopy(_VALID_RAW_REQUEST_BODY)


def copy_unknown_field_raw_request_fixture() -> dict[str, Any]:
    """Return a deep copy of the frozen unknown-field raw request fixture."""
    return copy.deepcopy(dict(UNKNOWN_FIELD_RAW_REQUEST))


__all__ = [
    "COMPOSITION_AUTHORITY_SCHEMA_VERSION",
    "COMPOSITION_FIXTURE",
    "COMPLETENESS_LEDGER_SCHEMA_VERSION",
    "EXCLUSION_AUTHORITY_FIXTURES",
    "EXCLUSION_AUTHORITY_SCHEMA_VERSION",
    "EXCLUSION_X000_FIXTURE",
    "EXCLUSION_X001_FIXTURE",
    "EXCLUSION_X002_FIXTURE",
    "EXCLUSION_X003_FIXTURE",
    "EXCLUSION_X004_FIXTURE",
    "EXCLUSION_X005_FIXTURE",
    "EXCLUSION_X006_FIXTURE",
    "EXCLUSION_X007_FIXTURE",
    "EXCLUSION_X008_FIXTURE",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "INPUT_EVIDENCE_REFS",
    "LEDGER_EXCLUSION_EVIDENCE_SCHEMA_VERSION",
    "LEDGER_EXCLUSION_FIXTURES",
    "LEDGER_FIXTURE",
    "LEDGER_MEMBER_EVIDENCE_SCHEMA_VERSION",
    "LEDGER_MEMBER_FIXTURES",
    "LEDGER_MEMBER_M000_FIXTURE",
    "LEDGER_MEMBER_M001_FIXTURE",
    "M000_MEMBER_AUTHORITY_FIXTURE",
    "M001_MEMBER_AUTHORITY_FIXTURE",
    "MEMBER_AUTHORITY_SCHEMA_VERSION",
    "ORACLE_VECTOR_COUNT",
    "PROFILE_ID",
    "PROPERTY_SNAPSHOT_HASH",
    "PROPERTY_SNAPSHOT_HASH_MISMATCH",
    "PROVENANCE_SCHEMA_VERSION",
    "SUCCESS_PROVENANCE_FIXTURE",
    "SYNTHETIC_UPSTREAM_IDENTITY_HASHES",
    "TASK025_HYDRAULIC_AUTHORITY_HASH",
    "TASK025_RESULT_HASH",
    "TASK026_RESULT_HASH",
    "TASK027_RESULT_HASH",
    "TASK028_COMPONENT_AUTHORITY_HASH",
    "TASK028_RESULT_HASH",
    "TASK029_DESIGN_CONTRACT_PATH",
    "TASK029_REQUEST_SCHEMA_VERSION",
    "TYPED_BLOCKED_FIXTURE",
    "UNKNOWN_FIELD_RAW_REQUEST",
    "UNKNOWN_RAW_REQUEST_CANONICAL_LEN",
    "UNKNOWN_RAW_REQUEST_CANONICAL_SHA256",
    "VALID_RAW_REQUEST",
    "VALID_RAW_REQUEST_CANONICAL_LEN",
    "VALID_RAW_REQUEST_CANONICAL_SHA256",
    "VECTOR_01_M000_HASH",
    "VECTOR_01_M000_HASH_INPUT_LEN",
    "VECTOR_02_M001_HASH",
    "VECTOR_02_M001_HASH_INPUT_LEN",
    "VECTOR_03_CALLER_MEMBER_ORDER_PERMUTATION_HASH",
    "VECTOR_03_COMPOSITION_HASH",
    "VECTOR_03_COMPOSITION_HASH_INPUT_LEN",
    "VECTOR_04_REQUEST_HASH",
    "VECTOR_04_REQUEST_HASH_INPUT_LEN",
    "VECTOR_05_LEDGER_HASH",
    "VECTOR_05_LEDGER_HASH_INPUT_LEN",
    "VECTOR_06_MODELED_TOTAL",
    "VECTOR_06_SUCCESS_HASH_INPUT_LEN",
    "VECTOR_06_SUCCESS_RESULT_HASH",
    "VECTOR_06_SUCCESS_RESULT_ID",
    "VECTOR_07_TYPED_BLOCKED_HASH_INPUT_LEN",
    "VECTOR_07_TYPED_BLOCKED_RESULT_HASH",
    "VECTOR_07_TYPED_BLOCKED_RESULT_ID",
    "VECTOR_08_RAW_BOUNDARY_CANONICAL_LEN",
    "VECTOR_08_RAW_BOUNDARY_CANONICAL_SHA256",
    "copy_unknown_field_raw_request_fixture",
    "copy_valid_raw_request_fixture",
]
