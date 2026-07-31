"""TASK-026 frozen provenance.

R8 implementation. The 5-field FrozenProvenance (R6-R7 §17.1) carries
exactly five fields:

  task_id
  design_contract_path
  implementation_software_version
  input_evidence_refs (KIND_TUPLE of 6 frozen refs)
  upstream_identity_hashes (KIND_TUPLE)

input_evidence_refs is the 6-element frozen tuple per R6-R7 §17.2:
[A2, T1-R2, H1-R1, Issue body, Repository BASE_SHA, R6-R7 design
contract]. The upstream_identity_hashes tuple is rebuilt at S15
from the actual upstream result/blocked envelope (R6-R7 §7 Runtime
Provenance / R8 brief §7).
"""

from __future__ import annotations

from dataclasses import dataclass

# R6-R7 §17.2 — six input evidence references (verbatim).
INPUT_EVIDENCE_REFS_V1: tuple[str, ...] = (
    "e152c803452972989ec7bfe4d5045e0dcd24eff6a6102d40cfc90b46d3b42efa",  # A2 manifest
    "b763b1a4768c596523f51d6dbc1a3d8df04c20f4c28c8007fcc19212c1a1970f",  # T1-R2 addendum
    "f9dbe86b89d3b88a0679adf108aee93468e57344178ebefae54a9e5907656a68",  # H1-R1 addendum
    "11a542048d666cd2022ca7f965462d558e128fd73f7b94d867ee087718cd9102",  # Issue source body
    "e924fb1d9fe263fbe11a5cb512201751734dde5d",  # Repository BASE_SHA
    "238786b68250832ba083a56f0d6ba35dffa627a237b5fead80a6ee322de69f58",  # R6-R7 design contract
)

INPUT_EVIDENCE_REF_COUNT: int = 6

# R6-R7 §17.1 — exactly 5 fields.
PROVENANCE_FIELDS: tuple[str, ...] = (
    "task_id",
    "design_contract_path",
    "implementation_software_version",
    "input_evidence_refs",
    "upstream_identity_hashes",
)

PROVENANCE_NAMESPACE: str = "task026.provenance.v1"

# R6-R7 §9.7.2 — kind tags.
PROVENANCE_KIND_TAGS: tuple[bytes, ...] = (
    # KIND_STRING, KIND_STRING, KIND_STRING, KIND_TUPLE, KIND_TUPLE
    b"STRING",
    b"STRING",
    b"STRING",
    b"TUPLE",
    b"TUPLE",
)


@dataclass(frozen=True)
class FrozenProvenance:
    """R6-R7 §17.1 — 5-field frozen provenance value object.

    input_evidence_refs is always the 6-tuple from INPUT_EVIDENCE_REFS_V1.
    upstream_identity_hashes is rebuilt at S15 from the actual upstream.
    """

    task_id: str
    design_contract_path: str
    implementation_software_version: str
    input_evidence_refs: tuple[str, ...]
    upstream_identity_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not self.task_id:
            raise ValueError("task_id must be non-empty str")
        if not isinstance(self.design_contract_path, str) or not self.design_contract_path:
            raise ValueError("design_contract_path must be non-empty str")
        if (
            not isinstance(self.implementation_software_version, str)
            or not self.implementation_software_version
        ):
            raise ValueError("implementation_software_version must be non-empty str")
        if not isinstance(self.input_evidence_refs, tuple):
            raise ValueError("input_evidence_refs must be tuple")
        if len(self.input_evidence_refs) != INPUT_EVIDENCE_REF_COUNT:
            raise ValueError(
                f"input_evidence_refs must have exactly {INPUT_EVIDENCE_REF_COUNT} entries; "
                f"got {len(self.input_evidence_refs)}"
            )
        for ref in self.input_evidence_refs:
            if not isinstance(ref, str) or not ref:
                raise ValueError("input_evidence_refs entries must be non-empty str")
        # Verify frozen 6-tuple identity.
        if self.input_evidence_refs != INPUT_EVIDENCE_REFS_V1:
            raise ValueError("input_evidence_refs must be the frozen 6-tuple from R6-R7 §17.2")
        if not isinstance(self.upstream_identity_hashes, tuple):
            raise ValueError("upstream_identity_hashes must be tuple")
        if len(self.upstream_identity_hashes) == 0:
            raise ValueError("upstream_identity_hashes must be non-empty")
        for h in self.upstream_identity_hashes:
            if not isinstance(h, str) or len(h) != 64:
                raise ValueError("upstream_identity_hashes entries must be 64-hex str")
            if any(c not in "0123456789abcdef" for c in h):
                raise ValueError("upstream_identity_hashes must be lowercase hex")


def field_count() -> int:
    return 5


__all__ = [
    "INPUT_EVIDENCE_REFS_V1",
    "INPUT_EVIDENCE_REF_COUNT",
    "PROVENANCE_FIELDS",
    "PROVENANCE_NAMESPACE",
    "PROVENANCE_KIND_TAGS",
    "FrozenProvenance",
    "field_count",
]
