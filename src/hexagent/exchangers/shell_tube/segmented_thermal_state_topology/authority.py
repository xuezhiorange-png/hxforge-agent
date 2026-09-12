"""Reviewed TASK170 R5 interface authority; no numerical engineering presets."""

from hexagent.canonical_json import canonical_sha256

PROFILE_ID = "V07-T171-STRAIGHT-COUNTERCURRENT-ENTRY-R4-V1"
VERSION = "task171.v1"
REVIEW_RECEIPT_ID = "TASK170-R4-INDEPENDENT-ENTRY-REVIEW-R5"
REVIEWED_DOCUMENT_SHA256 = "ecf01cb2b019a7b43a4dd6241890893fb4238a0a11dec4a1c4e91d780c9e08ca"
AUTHORITY_IDS = (
    "V07-T171-TOPOLOGY-R4-V1",
    "V07-T171-CELL-COMPARTMENT-R4-V1",
    "V07-T171-CONSERVATION-R4-V1",
)
DEFERRED_TOPOLOGIES = (
    "U_TUBE",
    "FLOATING_HEAD",
    "ADDITIONAL_PASSES",
    "BRANCHED_PATHS",
    "REVERSING_PATHS",
    "COCURRENT",
    "NON_E_SHELL",
    "ALTERNATE_BAFFLES",
    "TWO_PHASE",
    "TRANSIENT",
)
PREDECESSORS = ("TASK020", "TASK021", "TASK022", "TASK024", "TASK025_AREA")
AUTHORITY_PROFILE_HASH = canonical_sha256(
    {
        "profile_id": PROFILE_ID,
        "version": VERSION,
        "review_receipt_id": REVIEW_RECEIPT_ID,
        "reviewed_document_sha256": REVIEWED_DOCUMENT_SHA256,
        "authority_ids": list(AUTHORITY_IDS),
        "deferred_topologies": list(DEFERRED_TOPOLOGIES),
        "predecessors": list(PREDECESSORS),
    }
)
# Admission resource bounds, NOT mesh-selection or numerical-accuracy policy.
MAX_RECORDS = 4096
MAX_SCALAR_LENGTH = 512
