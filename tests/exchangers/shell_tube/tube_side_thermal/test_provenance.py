"""TASK-026 provenance tests (T1-R2 numbered_inventory items 34-35).

Frozen test reference set (T1-R2):
  34. test_provenance_shape_and_six_input_evidence_refs
  35. test_upstream_identity_hashes_has_single_frozen_runtime_source

T1-R2 module allocation: 2 tests in this module.
"""

from __future__ import annotations

import pytest

from hexagent.exchangers.shell_tube.tube_side_thermal import (
    INPUT_EVIDENCE_REF_COUNT,
    INPUT_EVIDENCE_REFS_V1,
    PROVENANCE_FIELDS,
    FrozenProvenance,
)


def test_provenance_shape_and_six_input_evidence_refs() -> None:
    """T1-R2 34 — Provenance shape: 5 fields, 6 input_evidence_refs."""
    # 5-field shape
    assert len(PROVENANCE_FIELDS) == 5
    assert PROVENANCE_FIELDS == (
        "task_id",
        "design_contract_path",
        "implementation_software_version",
        "input_evidence_refs",
        "upstream_identity_hashes",
    )
    # 6 input_evidence_refs frozen
    assert len(INPUT_EVIDENCE_REFS_V1) == 6
    assert INPUT_EVIDENCE_REF_COUNT == 6
    # Last 3 are deployment-shape: A2, T1-R2, H1-R1
    assert INPUT_EVIDENCE_REFS_V1[0] == "e152c803452972989ec7bfe4d5045e0dcd24eff6a6102d40cfc90b46d3b42efa"
    assert INPUT_EVIDENCE_REFS_V1[1] == "b763b1a4768c596523f51d6dbc1a3d8df04c20f4c28c8007fcc19212c1a1970f"
    assert INPUT_EVIDENCE_REFS_V1[2] == "f9dbe86b89d3b88a0679adf108aee93468e57344178ebefae54a9e5907656a68"
    # Construct a valid provenance.
    p = FrozenProvenance(
        task_id="TASK-026",
        design_contract_path="/tmp/TASK-026-DESIGN-CONTRACT-DRAFT-R6-R7.md",
        implementation_software_version="task026-local-impl-r8",
        input_evidence_refs=INPUT_EVIDENCE_REFS_V1,
        upstream_identity_hashes=("a" * 64,),
    )
    assert p.input_evidence_refs == INPUT_EVIDENCE_REFS_V1
    assert p.upstream_identity_hashes == ("a" * 64,)


def test_upstream_identity_hashes_has_single_frozen_runtime_source() -> None:
    """T1-R2 35 — upstream_identity_hashes is rebuilt at S15 from actual upstream."""
    # Must be non-empty tuple of 64-hex strings.
    with pytest.raises(ValueError):
        FrozenProvenance(
            task_id="TASK-026",
            design_contract_path="/tmp/X",
            implementation_software_version="x",
            input_evidence_refs=INPUT_EVIDENCE_REFS_V1,
            upstream_identity_hashes=(),  # empty
        )
    p = FrozenProvenance(
        task_id="TASK-026",
        design_contract_path="/tmp/X",
        implementation_software_version="x",
        input_evidence_refs=INPUT_EVIDENCE_REFS_V1,
        upstream_identity_hashes=("a" * 64,),
    )
    assert len(p.upstream_identity_hashes) == 1
    assert p.upstream_identity_hashes[0] == "a" * 64
