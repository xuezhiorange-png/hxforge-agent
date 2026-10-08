"""Replay frozen inputs for TASK173 supplemental functional acceptance R2.

This script reconstructs identities and candidate projections only. It does not
execute TASK020+ producer chains, Candidate Rating, or public Sizing.
"""

from __future__ import annotations

import json
import runpy
from decimal import Decimal
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    candidate_space_id,
    discrete_authority_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    request_hash as task168_request_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import Task168Request
from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
    SizingRequirementAuthority,
    Task173SizingRequest,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.service import (
    recompute_sizing_requirement_hash,
    sizing_request_hash,
)

ROOT = Path.cwd()
EVIDENCE_PATH = Path("docs/tasks/evidence/TASK-173-v0.7-supplemental-functional-acceptance-r2.json")
R2_QUALIFICATION_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-qualification.py"
)


def _reconstruct() -> tuple[dict[str, Any], Task173SizingRequest]:
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    source_record = dict(evidence["source_record"])
    recorded_source_hash = source_record.pop("canonical_hash")
    assert canonical_sha256(source_record) == recorded_source_hash

    r2 = runpy.run_path(str(ROOT / R2_QUALIFICATION_PATH), run_name="task173_r2_readonly")
    base_request, task168_request, candidate_space_hash = r2["_r4_or_rebound_request"]("H1")
    expected = evidence["candidate_space"]
    assert candidate_space_hash == expected["task168_candidate_space_hash"]
    assert candidate_space_id(candidate_space_hash) == expected["candidate_space_id"]
    assert (
        task168_request_hash(task168_request) == evidence["sizing_request"]["task168_request_hash"]
    )

    authority_bindings = tuple(
        sorted(
            (
                (item.authority_id, discrete_authority_hash(item))
                for item in task168_request.discrete_candidate_set_authorities
            ),
            key=lambda item: item[0].encode("utf-8", "strict"),
        )
    )
    recorded_requirement = dict(evidence["requirement_authority"])
    requirement_data = {
        key: value for key, value in recorded_requirement.items() if key != "canonical_hash"
    }
    requirement_data["required_duty_w"] = Decimal(recorded_requirement["required_duty_w"])
    requirement_data["max_tube_dp_pa"] = Decimal(recorded_requirement["max_tube_dp_pa"])
    requirement_data["max_shell_dp_pa"] = Decimal(recorded_requirement["max_shell_dp_pa"])
    requirement_data["evidence_refs"] = tuple(requirement_data["evidence_refs"])
    requirement_data["provenance_refs"] = tuple(requirement_data["provenance_refs"])
    requirement_data["allowed_construction_families"] = tuple(
        requirement_data["allowed_construction_families"]
    )
    requirement_data["discrete_candidate_authority_ids_and_hashes"] = tuple(
        tuple(item) for item in requirement_data["discrete_candidate_authority_ids_and_hashes"]
    )
    assert requirement_data["discrete_candidate_authority_ids_and_hashes"] == authority_bindings
    requirement_data["canonical_hash"] = recorded_requirement["canonical_hash"]
    requirement = SizingRequirementAuthority(**requirement_data)
    assert recompute_sizing_requirement_hash(requirement) == recorded_requirement["canonical_hash"]

    request_metadata = tuple(tuple(item) for item in evidence["sizing_request"]["request_metadata"])
    request = Task173SizingRequest(
        authority_package_id=base_request.authority_package_id,
        authority_package_hash=base_request.authority_package_hash,
        sizing_scope_projection_hash=base_request.sizing_scope_projection_hash,
        service_authority=base_request.service_authority,
        requirement_authority=requirement,
        task168_candidate_request=task168_request,
        ranking_policy_id=base_request.ranking_policy_id,
        ranking_policy_hash=base_request.ranking_policy_hash,
        request_metadata=request_metadata,
    )
    assert type(request) is Task173SizingRequest
    assert type(request.task168_candidate_request) is Task168Request
    validated = Task173SizingRequest.model_validate(request, strict=True)
    assert type(validated) is Task173SizingRequest
    assert type(validated.task168_candidate_request) is Task168Request
    return evidence, validated


def main() -> None:
    evidence, request = _reconstruct()
    task168_request = request.task168_candidate_request
    candidate_space = evidence["candidate_space"]
    r2 = runpy.run_path(str(ROOT / R2_QUALIFICATION_PATH), run_name="task173_r2_candidate_identity")
    expected_cases = r2["EXPECTED_CASES"]
    authority_map = task168._authority_map(task168_request)
    rows = []
    for ordinal, label in enumerate(("H1", "H2", "H3"), start=1):
        cut = Decimal(expected_cases[label][0])
        selected = tuple(
            cut if role == "BAFFLE_CUT" else task168._sort_values(authority_map[role].values)[0]
            for role in task168.DIMENSION_ORDER
            if role != "SHELL_GEOMETRY_ID"
        )
        candidate = task168._candidate(
            task168_request,
            authority_map,
            task168_request.shell_geometry_catalog.records[0],
            selected,
        )
        expected_candidate = candidate_space["candidates"][ordinal - 1]
        assert expected_candidate["prior_label"] == label
        assert candidate.candidate_id == expected_candidate["candidate_id"]
        assert candidate.candidate_hash == expected_candidate["candidate_hash"]
        assert not task168._structural_blockers(candidate)
        rows.append((candidate.candidate_id, candidate.candidate_hash))

    assert len(rows) == candidate_space["candidate_count"] == 3
    assert (
        recompute_sizing_requirement_hash(request.requirement_authority)
        == evidence["requirement_authority"]["canonical_hash"]
    )
    assert sizing_request_hash(request) == evidence["sizing_request"]["sizing_request_hash"]
    assert candidate_space["task168_candidate_space_hash"] == (
        "480e3249300d4b4a0668815cd18ebb7ed6fb5cf507c073449c9a509526eea668"
    )

    print("SUPPLEMENTAL_SOURCE_HASH_REPLAY=PASS")
    print("CANDIDATE_SPACE_HASH_REPLAY=PASS")
    print("TASK168_REQUEST_HASH_REPLAY=PASS")
    print("CANDIDATE_IDENTITIES_REPLAY=PASS")
    print("REQUIREMENT_AUTHORITY_HASH_REPLAY=PASS")
    print("STRICT_NATIVE_SIZING_REQUEST_VALIDATION=PASS")
    print("SIZING_REQUEST_HASH_REPLAY=PASS")
    print("RATING_OR_SIZING_EXECUTED=false")
    print("CANDIDATES=" + ",".join(f"{item[0]}:{item[1]}" for item in rows))


if __name__ == "__main__":
    main()
