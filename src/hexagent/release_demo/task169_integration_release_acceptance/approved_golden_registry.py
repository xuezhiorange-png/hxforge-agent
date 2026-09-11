"""Immutable TASK-169 Golden authority registered by independent review.

The registry is deliberately separate from the executable fixture builder.
Observed replay values become release expectations only when they are bound to
the recorded independent-review evidence below.  A caller cannot approve a
new identity by supplying matching ``review_status`` fields alone.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from .models import GoldenCaseId

APPROVED_GOLDEN_REVIEW_AUTHORITY: Final[str] = "TASK169_INDEPENDENT_GOLDEN_REVIEW"
APPROVED_GOLDEN_REVIEW_HEAD: Final[str] = "40c8188eca8f0430c54277a3b86873012942ed10"
APPROVED_GOLDEN_REVIEW_STATUS: Final[str] = "APPROVED"
APPROVED_GOLDEN_IDENTITY_STATUS: Final[str] = "APPROVED"
APPROVED_GOLDEN_TOLERANCE_CLASS: Final[str] = "TASK165_V06_FROZEN"
APPROVED_GOLDEN_RANKING_POLICY_HASH: Final[str] = (
    "142d58764a886a658bc24d1734b2be900843baa62c28dba849926b10a1f2fdc8"
)


@dataclass(frozen=True, slots=True)
class ApprovedGoldenAuthority:
    """The identity and review binding required for one approved Golden."""

    golden_id: GoldenCaseId
    source_id: str
    source_location: str
    source_class: str
    redistribution_status: str
    task168_request_hash: str
    task168_result_hash: str
    task168_result_id: str
    task168_result_status: str
    ranking_policy_hash: str
    task169_result_hash: str
    task169_result_id: str
    tolerance_class: str
    provenance_source_hash: str
    reviewer_evidence_refs: tuple[str, ...]
    review_status: str
    approved_by: str
    approval_evidence: tuple[str, ...]
    expected_identity_status: str
    negative_class: str | None = None
    expected_blocker_code: str | None = None
    expected_blocker_owner: str | None = None
    no_recommendation_required: bool = False


_REVIEW_REFS = (
    APPROVED_GOLDEN_REVIEW_AUTHORITY,
    "TASK169_REVIEW_HEAD_40C8188",
)


def _entry(
    golden_id: GoldenCaseId,
    *,
    task168_request_hash: str,
    task168_result_hash: str,
    task168_result_id: str,
    task169_result_hash: str,
    task169_result_id: str,
    provenance_source_hash: str,
    decision_ref: str,
    source_suffix: str,
    negative_class: str | None = None,
    expected_blocker_code: str | None = None,
    expected_blocker_owner: str | None = None,
    no_recommendation_required: bool = False,
) -> ApprovedGoldenAuthority:
    return ApprovedGoldenAuthority(
        golden_id=golden_id,
        source_id="TASK169-GOLDEN-AUTHORITY-" + source_suffix,
        source_location=(
            "docs/tasks/TASK-169-v06-golden-authority-proposal.json::goldens["
            + golden_id.value
            + "]"
        ),
        source_class="INDEPENDENTLY_REVIEWED_GOLDEN_AUTHORITY",
        redistribution_status="METADATA_ONLY_NO_PROTECTED_PAYLOAD",
        task168_request_hash=task168_request_hash,
        task168_result_hash=task168_result_hash,
        task168_result_id=task168_result_id,
        task168_result_status="VALID",
        ranking_policy_hash=APPROVED_GOLDEN_RANKING_POLICY_HASH,
        task169_result_hash=task169_result_hash,
        task169_result_id=task169_result_id,
        tolerance_class=APPROVED_GOLDEN_TOLERANCE_CLASS,
        provenance_source_hash=provenance_source_hash,
        reviewer_evidence_refs=_REVIEW_REFS,
        review_status=APPROVED_GOLDEN_REVIEW_STATUS,
        approved_by=APPROVED_GOLDEN_REVIEW_AUTHORITY,
        approval_evidence=tuple(
            sorted(
                (decision_ref, APPROVED_GOLDEN_REVIEW_HEAD),
                key=lambda item: item.encode("utf-8"),
            )
        ),
        expected_identity_status=APPROVED_GOLDEN_IDENTITY_STATUS,
        negative_class=negative_class,
        expected_blocker_code=expected_blocker_code,
        expected_blocker_owner=expected_blocker_owner,
        no_recommendation_required=no_recommendation_required,
    )


APPROVED_GOLDEN_REGISTRY: Final[Mapping[GoldenCaseId, ApprovedGoldenAuthority]] = MappingProxyType(
    {
        GoldenCaseId.V06_G01: _entry(
            GoldenCaseId.V06_G01,
            task168_request_hash="b4e959204e09f784b9c698b97170357d68310218077c41dd6363390083a36ea2",
            task168_result_hash="48f74fa55a69033f7af13777f0098293f325138e2bc61d46cb50ce2557c16562",
            task168_result_id="3455efc1-e4ad-5571-aab7-4612780b82b8",
            task169_result_hash="625b4fd3694504c3757e11758c7aaa6f4e4b6bdf6eb7143f9a4c19862b5f3717",
            task169_result_id="7e736888-2736-5da8-8887-582daadb288e",
            provenance_source_hash="ebc4923a59db2598b36c003a82a954be24d7aeda1994e846baa365ef93662687",
            decision_ref="TASK169_REVIEW_G01_APPROVE",
            source_suffix="V06-G01",
        ),
        GoldenCaseId.V06_G02: _entry(
            GoldenCaseId.V06_G02,
            task168_request_hash="f99f9d37b535201c2952b6652e6c84c912ac2d3ad9428362ffcb397d6fea80fb",
            task168_result_hash="5abf3df51b532d8ceb14cecfb5f30b1234dc79b2e4efed077255806ea3896cf0",
            task168_result_id="05f20f03-a486-51cc-b47d-c61e6e3b02a9",
            task169_result_hash="1e1f3e9155e2cdf8fb7ebbc28a11afd199c54d43d4575f12ff19023b0fd68637",
            task169_result_id="a2fd6ad6-08c2-5d8d-b9d7-6768483ed464",
            provenance_source_hash="895bd8e1ee5fecccfccc29a422b17574dedf4c7140435b544e8c35a78dc0edba",
            decision_ref="TASK169_REVIEW_G02_APPROVE_FOR_FIXTURE_SCOPE",
            source_suffix="V06-G02",
        ),
        GoldenCaseId.V06_G03: _entry(
            GoldenCaseId.V06_G03,
            task168_request_hash="81dcec220d87ec412789fa83d5d1d6d56a5ff23cffaf7a0f7bb55d06ce31f210",
            task168_result_hash="3b763508f555bb5053a2050fc7477edd43ddf9553a6b3fd9381bb3390c229777",
            task168_result_id="ee016f4d-542d-5e0b-a95c-e90fcad7497f",
            task169_result_hash="e79b4f254f03f53c51c06f557cb3e7558ae379c4e7b729fa31fa759a99db5a24",
            task169_result_id="d6361e86-e089-5e75-8789-f5679d8b344f",
            provenance_source_hash="9558a0b9114792465487dffde9e3f790cfefab5d13bbcf8e32e9d0cdda6b1ad6",
            decision_ref="TASK169_REVIEW_G03_APPROVE",
            source_suffix="V06-G03",
        ),
        GoldenCaseId.V06_G04: _entry(
            GoldenCaseId.V06_G04,
            task168_request_hash="ffb7dc72a82395a8493e636897a2a9430b9a4c9c78e79c84d0f5f6273a9fd6a9",
            task168_result_hash="c7cb67c9c6a7fc7af3f5ba1f30639d18e3b3c010f566756c97e306d3fcb93a87",
            task168_result_id="0333664d-a67b-5aeb-b520-f77bb8fa7ebc",
            task169_result_hash="901dcb049c8a833d987ea1de03e2ad177ba7f9966d4fbe38b9ce0f60ad536d6a",
            task169_result_id="55abcd89-fab4-5b29-88ea-60d0ef077b83",
            provenance_source_hash="5ff42057afe366e2c135929be44a18ccbc1ef2ac6ce31ab616516317c06a27b5",
            decision_ref="TASK169_REVIEW_G04_APPROVE",
            source_suffix="V06-G04",
        ),
        GoldenCaseId.V06_G05: _entry(
            GoldenCaseId.V06_G05,
            task168_request_hash="59a131b1034a8d8a24228c279a9d4222b21b3d93c3860c06b79974f8a6541995",
            task168_result_hash="a0521d00137833f0bd3763c440e0684fa993ba36917b824951a43a234ef3a17e",
            task168_result_id="1cf76875-a201-5a14-a9c7-960912156a1d",
            task169_result_hash="b2f86665b182deab959af4eb1e0617a7939341d67b5eb81c2b94aa9a0a66c197",
            task169_result_id="4019e286-8f41-5d94-a996-f825aa39094b",
            provenance_source_hash="5396c03e3219577edc840db46395c30fb02a270b0b942dcd92df3e221c1416ba",
            decision_ref="TASK169_REVIEW_G05_APPROVE_AFTER_FROZEN_NEGATIVE_CORRECTION",
            source_suffix="V06-G05",
            negative_class="MISSING_REQUIRED_SOURCE_OR_LICENSE_AUTHORITY",
            expected_blocker_code="EVALUATION_AUTHORITY_REQUIRED",
            expected_blocker_owner="TASK166",
            no_recommendation_required=True,
        ),
    }
)

APPROVED_GOLDEN_AUTHORITY_IDS: Final[frozenset[GoldenCaseId]] = frozenset(APPROVED_GOLDEN_REGISTRY)


def approved_golden_authority(golden_id: GoldenCaseId) -> ApprovedGoldenAuthority | None:
    """Return the immutable reviewed authority for ``golden_id`` if present."""

    return APPROVED_GOLDEN_REGISTRY.get(golden_id)


__all__ = [
    "APPROVED_GOLDEN_AUTHORITY_IDS",
    "APPROVED_GOLDEN_IDENTITY_STATUS",
    "APPROVED_GOLDEN_RANKING_POLICY_HASH",
    "APPROVED_GOLDEN_REGISTRY",
    "APPROVED_GOLDEN_REVIEW_AUTHORITY",
    "APPROVED_GOLDEN_REVIEW_HEAD",
    "APPROVED_GOLDEN_REVIEW_STATUS",
    "APPROVED_GOLDEN_TOLERANCE_CLASS",
    "ApprovedGoldenAuthority",
    "approved_golden_authority",
]
