"""Freeze and replay the native TASK173 completion-request identity.

The runtime request intentionally contains the frozen native Task168Request
dataclass.  Its complete identity preimage is recorded through TASK168's
repository projection and canonical byte helper, not through Pydantic JSON
serialization of the runtime object.

Run with ``--freeze`` once to create the evidence envelope, then run without
arguments to replay it.  The default replay mode is read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from decimal import Decimal
from importlib import import_module
from itertools import product
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_json_bytes, canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    candidate_space_hash as task168_candidate_space_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    canonical_bytes as task168_canonical_bytes,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    discrete_authority_hash,
    evaluation_input_authority_hash,
    shell_catalog_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    request_hash as task168_request_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    request_projection as task168_request_projection,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    requirement_authority_hash as task168_requirement_authority_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    DiscreteDimensionRole,
    Task168Request,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing import (
    SizingRequirementAuthority,
    Task173SizingRequest,
    sizing_request_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing import service as sizing_service
from hexagent.exchangers.shell_tube.task173_integrated_sizing.service import (
    recompute_sizing_requirement_hash,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT))

_attempt_3_sizing_request = import_module(
    "tests.exchangers.shell_tube.test_task173_integrated_sizing"
)._attempt_3_sizing_request


EVIDENCE_PATH = Path(__file__).with_name("TASK-173-v0.7-full-sizing-completion-request-r1.json")
R4_SPACE_ID = "V07-T173-SIZING-IMPLEMENTATION-VALIDATION-CANDIDATE-SPACE-R4"
R4_POLICY_HASH = "2db2372815fbc7295fde129508def1ef794aa55b44a1226c1188312e63e0a887"
R4_LEDGER_HASH = "aeac45600d17c811b4e873e4d3bf3a3085a1741ad1888837641b993cfa19980c"
HISTORICAL_R4_VALIDATION_SPACE_HASH = (
    "dd78fe36ceaa2b7e49d7c7264e07c3ba02a286114876b982f7a1b74cf91b9c01"
)
HISTORICAL_R4_SIZING_REQUEST_HASH = (
    "0d1964be99e5445605c602b20f4befeef0e16442128b21f55e615d14fc6b6f2b"
)
R4_BAFFLE_CUT_HASH = "ca0c7ada4f744390418d6a133df13a3c4b75a176ba3fab56b447a459a749e4d7"
R4_TASK168_SPACE_HASH = "aeb350ec6759c388122fd9a00c5d8cc962768ddcc46162e6af3bff38c11b74ea"
R2A_AUTHORITY_ID = "V07-T173-CELL-ROOT-PROVIDER-QUANTIZATION-ENCLOSURE-R2A"
R2A_AUTHORITY_HASH = "25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e"
EXPECTED_CANDIDATES = (
    (
        Decimal("0.215"),
        "adeab5b1-a339-5eb3-aa66-011ffe49bac0",
        "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767",
    ),
    (
        Decimal("0.220"),
        "e152cca9-fd5d-59ca-9b46-1df574eee841",
        "53e0d9af366a51c915a9a369a74f7563560359dc2b562e413f4674dcb520c489",
    ),
)


def _completion_evidence_refs() -> tuple[str, ...]:
    return (
        f"HISTORICAL_R4_VALIDATION_SPACE_HASH::{HISTORICAL_R4_VALIDATION_SPACE_HASH}",
        f"HISTORICAL_R4_SIZING_REQUEST_HASH::{HISTORICAL_R4_SIZING_REQUEST_HASH}",
        f"TASK168_CANDIDATE_SPACE_HASH::{R4_TASK168_SPACE_HASH}",
        f"R4_BAFFLE_CUT_AUTHORITY_HASH::{R4_BAFFLE_CUT_HASH}",
        f"STRUCTURAL_QUALIFICATION_POLICY_HASH::{R4_POLICY_HASH}",
        f"STRUCTURAL_QUALIFICATION_LEDGER_HASH::{R4_LEDGER_HASH}",
        f"REVIEWED_R2A_AUTHORITY_HASH::{R2A_AUTHORITY_HASH}",
        "IMPLEMENTATION_VALIDATION_COMPLETION_ONLY_NOT_GOLDEN_NOT_RELEASE_AUTHORITY",
    )


def _completion_provenance_refs() -> tuple[str, ...]:
    return (
        "OWNER_DIRECTION:NEW_COMPLETION_REQUEST_IDENTITY_FROM_EXACT_R4_TASK168_CANDIDATE_SPACE",
        "HISTORICAL_R4_OUTER_REQUEST_PREIMAGE_UNAVAILABLE_DO_NOT_CLAIM_REPLAY",
        "R4_CANDIDATE_SELECTION_UNCHANGED",
        "R2A_REVIEWED_AUTHORITY_REQUIRED_FOR_CANDIDATE_RATING",
    )


def _reconstruct_task168_request() -> tuple[Task168Request, dict[str, Any]]:
    base_request = _attempt_3_sizing_request()
    request = base_request.task168_candidate_request
    authorities = list(request.discrete_candidate_set_authorities)
    for index, authority in enumerate(authorities):
        if authority.dimension_role is not DiscreteDimensionRole.BAFFLE_CUT:
            continue
        changed = replace(
            authority,
            authority_id=f"{R4_SPACE_ID}:BAFFLE_CUT",
            authority_version="R4",
            source_id=R4_SPACE_ID,
            source_revision=("FROZEN_AFTER_STRUCTURAL_QUALIFICATION_BEFORE_PUBLIC_EXECUTION"),
            values=(Decimal("0.215"), Decimal("0.220")),
            evidence_refs=(
                f"STRUCTURAL_QUALIFICATION_POLICY_HASH::{R4_POLICY_HASH}",
                f"STRUCTURAL_QUALIFICATION_LEDGER_HASH::{R4_LEDGER_HASH}",
                "IMPLEMENTATION_VALIDATION_ONLY_NOT_GOLDEN_NOT_RELEASE_NOT_BUSINESS_REQUIREMENT",
            ),
            provenance_refs=(
                "OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET",
                "FIXTURE_CONSTRUCTION_ONLY_NO_PERFORMANCE_SELECTION",
            ),
            canonical_hash="",
        )
        authorities[index] = replace(changed, canonical_hash=discrete_authority_hash(changed))
    request = replace(request, discrete_candidate_set_authorities=tuple(authorities))

    baffle_cut_authority = next(
        item for item in authorities if item.dimension_role is DiscreteDimensionRole.BAFFLE_CUT
    )
    baffle_cut_hash = discrete_authority_hash(baffle_cut_authority)
    space_hash = task168_candidate_space_hash(request, tuple(authorities))
    if baffle_cut_hash != R4_BAFFLE_CUT_HASH or space_hash != R4_TASK168_SPACE_HASH:
        raise AssertionError(
            "BLOCKED_R4_NATIVE_CANDIDATE_SPACE_RECONSTRUCTION_MISMATCH: "
            f"baffle={baffle_cut_hash}; space={space_hash}"
        )

    authority_map = task168._authority_map(request)
    dimensions = tuple(
        task168._sort_values(authority_map[role].values)
        for role in task168.DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    candidates = tuple(
        sorted(
            (
                task168._candidate(request, authority_map, combination[0], combination[1:])
                for combination in product(request.shell_geometry_catalog.records, *dimensions)
            ),
            key=lambda item: item.baffle_cut_fraction,
        )
    )
    actual_candidates = tuple(
        (item.baffle_cut_fraction, item.candidate_id, item.candidate_hash) for item in candidates
    )
    if actual_candidates != EXPECTED_CANDIDATES:
        raise AssertionError(f"R4 candidate identity mismatch: {actual_candidates!r}")

    nested_hashes = {
        "task168_requirement_authority_hash": task168_requirement_authority_hash(
            request.requirement_authority
        ),
        "shell_catalog_hash": shell_catalog_hash(request.shell_geometry_catalog),
        "evaluation_input_authority_hash": evaluation_input_authority_hash(
            request.evaluation_input_authority
        ),
    }
    if request.shell_geometry_catalog.catalog_hash != nested_hashes["shell_catalog_hash"]:
        raise AssertionError("shell catalog hash does not replay")
    if (
        request.evaluation_input_authority.canonical_hash
        != nested_hashes["evaluation_input_authority_hash"]
    ):
        raise AssertionError("Task168 evaluation-input authority hash does not replay")
    if (
        request.requirement_authority.canonical_hash
        != nested_hashes["task168_requirement_authority_hash"]
    ):
        raise AssertionError("Task168 requirement authority hash does not replay")
    discrete_hashes = {
        item.dimension_role.value: discrete_authority_hash(item)
        for item in sorted(authorities, key=lambda item: item.dimension_role.value)
    }
    if any(
        item.canonical_hash != discrete_hashes[item.dimension_role.value] for item in authorities
    ):
        raise AssertionError("one or more discrete-authority hashes do not replay")

    return request, {
        "baffle_cut_hash": baffle_cut_hash,
        "candidate_space_hash": space_hash,
        "candidates": candidates,
        "discrete_authority_hashes": discrete_hashes,
        **nested_hashes,
    }


def _build_request_and_projection() -> tuple[Task173SizingRequest, dict[str, Any]]:
    base = _attempt_3_sizing_request()
    task168_request, task168_facts = _reconstruct_task168_request()
    authorities = tuple(task168_request.discrete_candidate_set_authorities)
    authority_bindings = tuple(
        sorted(
            ((item.authority_id, discrete_authority_hash(item)) for item in authorities),
            key=lambda item: item[0].encode("utf-8", "strict"),
        )
    )

    requirement_data = {
        "requirement_id": "TASK173-SIZING-IMPLEMENTATION-COMPLETION-R1",
        "authority_version": "R1",
        "source_class": "OWNER_APPROVED_PROJECT_DEFINED_IMPLEMENTATION_VALIDATION",
        "source_id": "V07-T173-SIZING-IMPLEMENTATION-COMPLETION-REQUEST-R1",
        "source_revision": "FROZEN_AFTER_R2A_REVIEW_BEFORE_COMPLETION_PUBLIC_EXECUTION",
        "approval_status": "APPROVED",
        "evidence_refs": _completion_evidence_refs(),
        "provenance_refs": _completion_provenance_refs(),
        "required_duty_w": Decimal("10000"),
        "max_tube_dp_pa": Decimal("1200"),
        "max_shell_dp_pa": Decimal("1200"),
        "allowed_construction_families": ("FIXED_TUBESHEET",),
        "required_screening_policy_id": "V07-T173-SIZING-MANDATORY-SCREENING-R1",
        "discrete_candidate_authority_ids_and_hashes": authority_bindings,
    }
    requirement_json_projection = {
        **requirement_data,
        "evidence_refs": list(requirement_data["evidence_refs"]),
        "provenance_refs": list(requirement_data["provenance_refs"]),
        "required_duty_w": "10000",
        "max_tube_dp_pa": "1200",
        "max_shell_dp_pa": "1200",
        "allowed_construction_families": ["FIXED_TUBESHEET"],
        "discrete_candidate_authority_ids_and_hashes": [list(item) for item in authority_bindings],
    }
    requirement_hash = canonical_sha256(requirement_json_projection)
    requirement = SizingRequirementAuthority(
        **requirement_data,
        canonical_hash=requirement_hash,
    )
    if recompute_sizing_requirement_hash(requirement) != requirement_hash:
        raise AssertionError("completion requirement authority hash does not replay")

    metadata = (
        ("authority_use", "IMPLEMENTATION_VALIDATION_COMPLETION_ONLY"),
        ("golden", "false"),
        ("release_authority", "false"),
        ("historical_r4_validation_space_authority_id", R4_SPACE_ID),
        ("historical_r4_validation_space_authority_hash", HISTORICAL_R4_VALIDATION_SPACE_HASH),
        ("historical_r4_sizing_request_hash", HISTORICAL_R4_SIZING_REQUEST_HASH),
        ("historical_r4_request_preimage_status", "UNAVAILABLE_HASH_ONLY_DO_NOT_CLAIM_REPLAY"),
        ("task168_candidate_space_hash", R4_TASK168_SPACE_HASH),
        ("reviewed_r2a_authority_id", R2A_AUTHORITY_ID),
        ("reviewed_r2a_authority_hash", R2A_AUTHORITY_HASH),
        ("candidate_space_frozen_before_completion_execution", "true"),
    )
    request = Task173SizingRequest(
        authority_package_id=base.authority_package_id,
        authority_package_hash=base.authority_package_hash,
        sizing_scope_projection_hash=base.sizing_scope_projection_hash,
        service_authority=base.service_authority,
        requirement_authority=requirement,
        task168_candidate_request=task168_request,
        ranking_policy_id=base.ranking_policy_id,
        ranking_policy_hash=base.ranking_policy_hash,
        request_metadata=metadata,
    )
    if type(request) is not Task173SizingRequest:
        raise AssertionError("completion request must be exact Task173SizingRequest")
    if type(request.task168_candidate_request) is not Task168Request:
        raise AssertionError("completion request must retain native Task168Request")
    validated = Task173SizingRequest.model_validate(request, strict=True)
    if type(validated) is not Task173SizingRequest:
        raise AssertionError("strict native validation returned the wrong model type")
    if type(validated.task168_candidate_request) is not Task168Request:
        raise AssertionError("strict native validation lost native Task168Request")

    task168_projection = task168_request_projection(task168_request)
    task168_bytes = task168_canonical_bytes(task168_projection)
    native_task168_hash = task168_request_hash(task168_request)
    native_candidate_space_hash = task168_candidate_space_hash(
        task168_request, tuple(task168_request.discrete_candidate_set_authorities)
    )
    request_digest = sizing_request_hash(request)
    sizing_identity_projection = {
        "schema_version": request.schema_version,
        "authority_package_id": request.authority_package_id,
        "authority_package_hash": request.authority_package_hash,
        "sizing_scope_projection_hash": request.sizing_scope_projection_hash,
        "service_authority": request.service_authority.model_dump(mode="json"),
        "requirement_authority": request.requirement_authority.model_dump(mode="json"),
        "task168_request_hash": native_task168_hash,
        "shell_catalog_id": task168_request.shell_geometry_catalog.catalog_id,
        "shell_catalog_hash": task168_facts["shell_catalog_hash"],
        "discrete_candidate_authority_hashes": [
            [item.dimension_role.value, discrete_authority_hash(item)]
            for item in sorted(
                task168_request.discrete_candidate_set_authorities,
                key=lambda item: item.dimension_role.value,
            )
        ],
        "candidate_space_hash": native_candidate_space_hash,
        "candidate_authority_hashes": {
            "task171": sizing_service._TASK171_AUTHORITY_HASH,
            "task172": sizing_service._TASK172_AUTHORITY_HASH,
            "task174": sizing_service._TASK174_AUTHORITY_HASH,
            "candidate_rating": sizing_service._TASK173_RATING_AUTHORITY_HASH,
            "jmu_transfer": sizing_service._JMU_TRANSFER_HASH,
            "bell_event_transfer": sizing_service._BELL_TRANSFER_HASH,
            "pressure_coupling_transfer": sizing_service._PRESSURE_TRANSFER_HASH,
            "task174_project_transfer": sizing_service._TASK174_TRANSFER_HASH,
        },
        "ranking_policy_id": request.ranking_policy_id,
        "ranking_policy_hash": request.ranking_policy_hash,
        "request_metadata": [list(item) for item in request.request_metadata],
    }
    sizing_identity_bytes = canonical_json_bytes(sizing_identity_projection)
    if canonical_sha256(sizing_identity_projection) != request_digest:
        raise AssertionError("frozen sizing identity projection differs from production hash")
    if task168_facts["candidate_space_hash"] != native_candidate_space_hash:
        raise AssertionError("native candidate-space replay mismatch")
    if task168_facts["baffle_cut_hash"] != R4_BAFFLE_CUT_HASH:
        raise AssertionError("R4 baffle-cut authority replay mismatch")

    task168_projection_json = json.loads(task168_bytes.decode("utf-8"))
    audit_projection = {
        "schema_version": request.schema_version,
        "authority_package_id": request.authority_package_id,
        "authority_package_hash": request.authority_package_hash,
        "sizing_scope_projection_hash": request.sizing_scope_projection_hash,
        "service_authority": request.service_authority.model_dump(mode="json"),
        "requirement_authority": request.requirement_authority.model_dump(mode="json"),
        "task168_canonical_request_projection": task168_projection_json,
        "ranking_policy_id": request.ranking_policy_id,
        "ranking_policy_hash": request.ranking_policy_hash,
        "request_metadata": [list(item) for item in request.request_metadata],
    }
    facts: dict[str, Any] = {
        **task168_facts,
        "completion_requirement_authority_hash": requirement_hash,
        "completion_sizing_request_hash": request_digest,
        "task168_request_hash": native_task168_hash,
        "task168_request_projection": task168_projection_json,
        "task168_request_canonical_json_utf8": task168_bytes.decode("utf-8"),
        "task168_request_canonical_json_sha256": hashlib.sha256(task168_bytes).hexdigest(),
        "sizing_identity_projection": sizing_identity_projection,
        "sizing_identity_canonical_json_utf8": sizing_identity_bytes.decode("utf-8"),
        "native_request_audit_projection": audit_projection,
    }
    return request, facts


def _make_evidence(facts: dict[str, Any]) -> dict[str, Any]:
    candidate_a, candidate_b = facts["candidates"]
    return {
        "schema_version": "task173.full-sizing-completion-request-evidence.v2",
        "runtime_request_validation_mode": "STRICT_NATIVE_PYTHON",
        "strict_native_python_validation": "PASS",
        "json_model_roundtrip_required": False,
        "json_model_roundtrip_not_applicable_reason": (
            "Task168Request is a native frozen dataclass with Python-only nested values; "
            "canonical identity is defined by repository projection/hash functions"
        ),
        "production_serialization_code_changed": False,
        "completion_requirement_authority_hash": facts["completion_requirement_authority_hash"],
        "completion_sizing_request_hash": facts["completion_sizing_request_hash"],
        "task168_request_hash": facts["task168_request_hash"],
        "task168_request_canonical_json_sha256": facts["task168_request_canonical_json_sha256"],
        "task168_candidate_space_hash": facts["candidate_space_hash"],
        "r4_baffle_cut_authority_hash": facts["baffle_cut_hash"],
        "task168_requirement_authority_hash": facts["task168_requirement_authority_hash"],
        "shell_catalog_hash": facts["shell_catalog_hash"],
        "evaluation_input_authority_hash": facts["evaluation_input_authority_hash"],
        "discrete_authority_hashes": facts["discrete_authority_hashes"],
        "candidate_A": {
            "cut": str(candidate_a.baffle_cut_fraction),
            "id": candidate_a.candidate_id,
            "hash": candidate_a.candidate_hash,
        },
        "candidate_B": {
            "cut": str(candidate_b.baffle_cut_fraction),
            "id": candidate_b.candidate_id,
            "hash": candidate_b.candidate_hash,
        },
        "TASK168_REQUEST_CANONICAL_JSON_UTF8": facts["task168_request_canonical_json_utf8"],
        "SIZING_IDENTITY_PROJECTION": facts["sizing_identity_projection"],
        "SIZING_IDENTITY_CANONICAL_JSON_UTF8": facts["sizing_identity_canonical_json_utf8"],
        "native_request_audit_projection": facts["native_request_audit_projection"],
        "historical_r4_validation_space_hash": HISTORICAL_R4_VALIDATION_SPACE_HASH,
        "historical_r4_request_hash": HISTORICAL_R4_SIZING_REQUEST_HASH,
        "historical_r4_request_preimage_status": ("UNAVAILABLE_HASH_ONLY_NOT_EXECUTION_IDENTITY"),
    }


def _replay(evidence: dict[str, Any]) -> None:
    request, facts = _build_request_and_projection()
    expected = _make_evidence(facts)
    if evidence != expected:
        raise AssertionError("committed request evidence differs from native reconstruction")
    committed_task168_bytes = evidence["TASK168_REQUEST_CANONICAL_JSON_UTF8"].encode("utf-8")
    regenerated_task168_bytes = facts["task168_request_canonical_json_utf8"].encode("utf-8")
    if regenerated_task168_bytes != committed_task168_bytes:
        raise AssertionError("Task168 canonical preimage bytes differ")
    committed_sizing_bytes = evidence["SIZING_IDENTITY_CANONICAL_JSON_UTF8"].encode("utf-8")
    regenerated_sizing_bytes = facts["sizing_identity_canonical_json_utf8"].encode("utf-8")
    if regenerated_sizing_bytes != committed_sizing_bytes:
        raise AssertionError("Sizing identity canonical preimage bytes differ")
    if task168_request_hash(request.task168_candidate_request) != evidence["task168_request_hash"]:
        raise AssertionError("Task168 request hash mismatch")
    if sizing_request_hash(request) != evidence["completion_sizing_request_hash"]:
        raise AssertionError("completion request hash mismatch")

    print("STRICT_NATIVE_PYTHON_REQUEST_VALIDATION=PASS")
    print("R4_BAFFLE_CUT_AUTHORITY_REPLAY=PASS")
    print("TASK168_REQUEST_CANONICAL_PREIMAGE_REPLAY=PASS")
    print("TASK168_REQUEST_HASH_REPLAY=PASS")
    print("R4_NATIVE_TASK168_CANDIDATE_SPACE_REPLAY=PASS")
    print("R4_NATIVE_CANDIDATE_IDENTITIES_REPLAY=PASS")
    print("COMPLETION_REQUIREMENT_HASH_REPLAY=PASS")
    print("SIZING_IDENTITY_CANONICAL_PREIMAGE_REPLAY=PASS")
    print("COMPLETION_SIZING_REQUEST_HASH_REPLAY=PASS")
    print("ALL_COMPLETION_REQUEST_REPLAY_PASS=true")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--freeze",
        action="store_true",
        help="write the deterministic request evidence envelope, then replay it",
    )
    args = parser.parse_args()
    if args.freeze:
        _, facts = _build_request_and_projection()
        evidence = _make_evidence(facts)
        EVIDENCE_PATH.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    loaded = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    _replay(loaded)


if __name__ == "__main__":
    main()
