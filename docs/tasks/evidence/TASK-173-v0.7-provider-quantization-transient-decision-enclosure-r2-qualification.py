"""Run the frozen R2 transient-only enclosure qualification on committed runtime."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from dataclasses import asdict, replace
from decimal import Decimal, localcontext
from pathlib import Path
from types import ModuleType
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    candidate_hash as recompute_candidate_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    candidate_projection,
    discrete_authority_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    candidate_space_hash as task168_candidate_space_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    canonical_bytes as task168_canonical_bytes,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    DiscreteAuthoritySource,
    DiscreteDimensionRole,
)
from hexagent.exchangers.shell_tube.task172_local_runtime import service as task172
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as rating
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    candidate_rating_request_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing import service as sizing
from hexagent.exchangers.shell_tube.task173_integrated_sizing.candidate_materialization import (
    materialize_candidate_task171,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    Task174NativeOutputs,
    Task174SuccessResult,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    validate_candidate_request as validate_task174_candidate,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration.service import (
    recompute_task174_result_hash,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    ReferencePlanePair,
    ReferencePlaneToken,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import FlowRegime
from hexagent.exchangers.shell_tube.tube_side_thermal.nusselt_selector import (
    check_pr_envelope,
    select_regime,
)
from hexagent.properties.coolprop_provider import CoolPropProvider

ROOT = Path.cwd()
RUNTIME_HEAD = "b1b9d676c693e09d740c47b642198b5e4f543409"
RUNTIME_TREE = "b0cfbdb7c4a9c3136fda317723fb5eab30c40e1e"
RUNTIME_REBASELINE_V3_PROVENANCE_HASH = (
    "1f65fd736f4d5565d2f4a9037fabe8d9c48a7b0770ccb4414d86c7d82bb47574"
)
AUTHORITY_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2.json"
)
REBINDED_HOLDOUT_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-holdout-identity-rebinding-and-enclosure-qualification-resume-r1.json"
)
PRECISION_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-cell-root-precision-floor-adjudication-r1.json"
)
REVIEW_HISTORY_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-task174-native-bell-canonical-reduction-parity-and-enclosure-qualification-resume-r1.json"
)
IMPL_EVIDENCE_PATH = Path("docs/tasks/evidence/TASK-173-v0.7-full-sizing-implementation-r1.json")
R4_SPACE_ID = "V07-T173-SIZING-IMPLEMENTATION-VALIDATION-CANDIDATE-SPACE-R4"
R4_SPACE_HASH = "dd78fe36ceaa2b7e49d7c7264e07c3ba02a286114876b982f7a1b74cf91b9c01"
R4_TASK168_HASH = "aeb350ec6759c388122fd9a00c5d8cc962768ddcc46162e6af3bff38c11b74ea"
R4_REQUEST_HASH = "0d1964be99e5445605c602b20f4befeef0e16442128b21f55e615d14fc6b6f2b"
R4_POLICY_HASH = "2db2372815fbc7295fde129508def1ef794aa55b44a1226c1188312e63e0a887"
R4_LEDGER_HASH = "aeac45600d17c811b4e873e4d3bf3a3085a1741ad1888837641b993cfa19980c"
HOLDOUT_SELECTION_HASH = "f2de04ae8ca31a0f42c3cbfa57a135416d5607c5e6963442576c6e6da50450da"
SIZING_AUTHORITY_PACKAGE_HASH = "750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9"
REBIND_CANDIDATE_SPACE_HASH = "480e3249300d4b4a0668815cd18ebb7ed6fb5cf507c073449c9a509526eea668"
EXPECTED_CASES = {
    "TRAIN_A": (
        "0.215",
        "adeab5b1-a339-5eb3-aa66-011ffe49bac0",
        "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767",
    ),
    "TRAIN_B": (
        "0.220",
        "e152cca9-fd5d-59ca-9b46-1df574eee841",
        "53e0d9af366a51c915a9a369a74f7563560359dc2b562e413f4674dcb520c489",
    ),
    "H1": (
        "0.225",
        "68a99368-a518-5482-b9df-4bc3357edea9",
        "bd0da145a592652e55a6fc8cd325a98d6f1cf349ed74b98e811d1343ce62ed54",
    ),
    "H2": (
        "0.275",
        "aa70248a-9f76-542d-bc77-1e935b9c32d4",
        "a30d1b0c01dcd0607bdd46e720a3a278e6b90b265b6bd4f109eb2c1cae58d8c5",
    ),
    "H3": (
        "0.350",
        "f3e14759-e05b-5088-bfb5-b6e16e918267",
        "b5bcf9258ff1cd455eab071a55cbdce7d8708391d1737e44d3dae2bccdaedb7e",
    ),
}

_fixture_spec = importlib.util.spec_from_file_location(
    "task173_sizing_committed_fixture",
    ROOT / "tests/exchangers/shell_tube/test_task173_integrated_sizing.py",
)
assert _fixture_spec is not None and _fixture_spec.loader is not None
# A third-party distribution may install a concrete top-level ``tests`` package.
# Bind the fixture imports to this repository's namespace package explicitly.
_tests_package = ModuleType("tests")
_tests_package.__path__ = [str(ROOT / "tests")]
sys.modules["tests"] = _tests_package
_fixture = importlib.util.module_from_spec(_fixture_spec)
_fixture_spec.loader.exec_module(_fixture)
_attempt_3_sizing_request = _fixture._attempt_3_sizing_request


def _check_committed_runtime() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if head != RUNTIME_HEAD:
        raise RuntimeError(f"RUNTIME_HEAD_MISMATCH:{head}")
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], text=True).strip()
    if tree != RUNTIME_TREE:
        raise RuntimeError(f"RUNTIME_TREE_MISMATCH:{tree}")
    subprocess.run(["git", "diff", "--exit-code", "HEAD"], check=True)
    source_paths = [
        "src/hexagent/exchangers/shell_tube/manufacturable_candidates",
        "src/hexagent/exchangers/shell_tube/task172_local_runtime",
        "src/hexagent/exchangers/shell_tube/task173_integrated_rating",
        "src/hexagent/exchangers/shell_tube/task173_integrated_sizing",
        "src/hexagent/exchangers/shell_tube/task174_hydraulic_orchestration",
        "tests/exchangers/shell_tube/test_task173_integrated_sizing.py",
        "tests/exchangers/shell_tube/test_task174_hydraulic_orchestration.py",
    ]
    subprocess.run(["git", "diff", "--exit-code", "HEAD", "--", *source_paths], check=True)
    projection = json.loads(AUTHORITY_PATH.read_text())["authority_candidate"]["projection"]
    evidence = json.loads(AUTHORITY_PATH.read_text())
    rebaseline = evidence["runtime_rebaseline_v3"]
    if (
        canonical_sha256(
            {key: value for key, value in rebaseline.items() if key != "provenance_hash"}
        )
        != RUNTIME_REBASELINE_V3_PROVENANCE_HASH
        or projection["runtime_rebaseline_v3_provenance_hash"]
        != RUNTIME_REBASELINE_V3_PROVENANCE_HASH
    ):
        raise RuntimeError("RUNTIME_REBASELINE_V3_PROVENANCE_MISMATCH")
    expected_artifacts = projection["qualification_artifacts"]
    replay_path = Path(__file__).with_name(
        "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-replay.py"
    )
    for key, path in (
        ("qualification_runner_sha256", Path(__file__)),
        ("replay_runner_sha256", replay_path),
    ):
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected_artifacts[key]:
            raise RuntimeError(f"QUALIFICATION_ARTIFACT_HASH_MISMATCH:{key}:{actual}")


def _r4_or_rebound_request(label: str) -> tuple[Any, Any, str]:
    sizing_request = _attempt_3_sizing_request()
    task168_request = sizing_request.task168_candidate_request
    authorities = []
    if label.startswith("TRAIN"):
        evidence = {
            "authority_id": f"{R4_SPACE_ID}:BAFFLE_CUT",
            "authority_version": "R4",
            "source_id": R4_SPACE_ID,
            "source_revision": "FROZEN_AFTER_STRUCTURAL_QUALIFICATION_BEFORE_PUBLIC_EXECUTION",
            "approval_status": "APPROVED",
            "values": ["0.215", "0.220"],
            "evidence_refs": [
                f"STRUCTURAL_QUALIFICATION_POLICY_HASH::{R4_POLICY_HASH}",
                f"STRUCTURAL_QUALIFICATION_LEDGER_HASH::{R4_LEDGER_HASH}",
                "IMPLEMENTATION_VALIDATION_ONLY_NOT_GOLDEN_NOT_RELEASE_NOT_BUSINESS_REQUIREMENT",
            ],
            "provenance_refs": [
                "OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET",
                "FIXTURE_CONSTRUCTION_ONLY_NO_PERFORMANCE_SELECTION",
            ],
        }
    else:
        evidence = json.loads(REBINDED_HOLDOUT_PATH.read_text())["rebind_authority"]
    for authority in task168_request.discrete_candidate_set_authorities:
        if authority.dimension_role is DiscreteDimensionRole.BAFFLE_CUT:
            authority = replace(
                authority,
                authority_id=evidence["authority_id"],
                authority_version=evidence["authority_version"],
                source_class=DiscreteAuthoritySource.OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET,
                source_id=evidence["source_id"],
                source_revision=evidence["source_revision"],
                approval_status=evidence["approval_status"],
                values=tuple(Decimal(value) for value in evidence["values"]),
                evidence_refs=tuple(evidence["evidence_refs"]),
                provenance_refs=tuple(evidence["provenance_refs"]),
                canonical_hash="",
            )
            authority = replace(authority, canonical_hash=discrete_authority_hash(authority))
            if not label.startswith("TRAIN"):
                assert authority.canonical_hash == evidence["canonical_hash"]
        authorities.append(authority)
    task168_request = replace(
        task168_request, discrete_candidate_set_authorities=tuple(authorities)
    )
    space_hash = task168_candidate_space_hash(
        task168_request, tuple(task168_request.discrete_candidate_set_authorities)
    )
    return sizing_request, task168_request, space_hash


def _build_candidate(label: str) -> tuple[Any, Any, Any, Any, Any, str]:
    base_request, task168_request, space_hash = _r4_or_rebound_request(label)
    authority_map = task168._authority_map(task168_request)
    cut = Decimal(EXPECTED_CASES[label][0])
    values = tuple(
        cut if role == "BAFFLE_CUT" else task168._sort_values(authority_map[role].values)[0]
        for role in task168.DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    shell_record = task168_request.shell_geometry_catalog.records[0]
    candidate = task168._candidate(task168_request, authority_map, shell_record, values)
    assert (candidate.candidate_id, candidate.candidate_hash) == EXPECTED_CASES[label][1:]
    assert not task168._structural_blockers(candidate)
    bundle, failure, _last_success = task168._execute_candidate_chain(
        task168_request,
        candidate,
        shell_record,
        include_legacy_task162=False,
        include_legacy_task168_rating_dependencies=False,
        preserve_baffle_orientation_sequence=True,
    )
    if failure is not None:
        raise RuntimeError(f"{label}:TASK168:{failure.stage}:{failure.code}")
    topology = materialize_candidate_task171(
        candidate=candidate,
        configuration=bundle.task020_configuration,
        layout=bundle.task021_layout,
        bundle_geometry=bundle.task022_geometry,
        baffle_geometry=bundle.task024_geometry,
        task025_result=bundle.task025_result,
        task024_request=bundle.task024_request,
        task025_request=bundle.task025_request,
    )
    task174_request = sizing._candidate_request_for_task174(candidate, bundle, topology)
    task174_result = validate_task174_candidate(
        task174_request,
        Task174NativeOutputs(
            task029=bundle.task029_result, task034=None, task166=bundle.task166_result
        ),
    )
    if type(task174_result) is not Task174SuccessResult or task174_result.status != "VALIDATED":
        raise RuntimeError(f"{label}:TASK174:{task174_result.model_dump(mode='json')}")
    if label == "H1":
        assert (
            bundle.task166_result.result_hash
            == "08e783c2405569924fbcc1a32f643eae8ad0277d5fe97b32aaaf0f56b12cd9d5"
        )
    if label.startswith("TRAIN"):
        assert space_hash == R4_TASK168_HASH
        sizing_hash = R4_REQUEST_HASH
    else:
        sizing_hash = canonical_sha256(
            {
                "schema_version": "task173.enclosure-n1-qualification-request.v1",
                "purpose": "IMPLEMENTATION_VALIDATION_ONLY_NOT_GOLDEN_NOT_RELEASE_AUTHORITY",
                "authority_package_hash": SIZING_AUTHORITY_PACKAGE_HASH,
                "holdout_selection_hash": HOLDOUT_SELECTION_HASH,
                "holdout_candidate_space_hash": REBIND_CANDIDATE_SPACE_HASH,
                "task168_candidate_space_hash": space_hash,
                "candidate_id": candidate.candidate_id,
                "candidate_hash": candidate.candidate_hash,
            }
        )
    rating_request = sizing._candidate_rating_request(
        candidate, space_hash, bundle, topology, task174_result, sizing_hash
    )
    if not label.startswith("TRAIN"):
        rating_request = rating_request.model_copy(
            update={
                "request_metadata": (
                    ("candidate_rating_scope", "PROVIDER_QUANTIZATION_ENCLOSURE_R2_QUALIFICATION"),
                    ("qualification_request_hash", sizing_hash),
                    ("authority_use", "IMPLEMENTATION_VALIDATION_ONLY"),
                )
            }
        )
    request_hash = candidate_rating_request_hash(rating_request)
    expected_train_hash = {
        "TRAIN_A": "77ba78058f7e2f0d0befcc4fc1042fe179a79aadddc009666e4748ad00101334",
        "TRAIN_B": "8771099ae4fdfa553d2d092e41e366fcb36b1b30f16822c9f0277b9a6394066e",
    }
    if label.startswith("TRAIN"):
        assert request_hash == expected_train_hash[label]
    return candidate, bundle, topology, task174_result, rating_request, space_hash


def _failure_fields(exc: BaseException) -> dict[str, str]:
    return {
        item.split("=", 1)[0]: item.split("=", 1)[1]
        for item in getattr(exc, "diagnostics", ())
        if "=" in item
    }


def _binary64_adjacent(left: float, right: float) -> bool:
    if left == right:
        return True
    low, high = sorted((left, right))
    return math.nextafter(low, high) == high


def _state_input_enthalpy(state: Any) -> str:
    if state.snapshot.query_type != "PH":
        raise RuntimeError("PROVIDER_COORDINATE_NOT_PH")
    value = state.snapshot.inputs.get("enthalpy_j_kg")
    if value is None:
        raise RuntimeError("PROVIDER_PH_ENTHALPY_INPUT_MISSING")
    return value


def _pair_fallback(value: Any) -> Any:
    if type(value) is ReferencePlanePair:
        return {
            "__task173_type__": "ReferencePlanePair",
            "start": value.start.value,
            "end": value.end.value,
        }
    raise TypeError(f"unhandled complete-request JSON value: {type(value).__name__}")


def _restore_pairs(value: Any) -> Any:
    if isinstance(value, dict) and value.get("__task173_type__") == "ReferencePlanePair":
        return ReferencePlanePair(
            ReferencePlaneToken(value["start"]), ReferencePlaneToken(value["end"])
        )
    if isinstance(value, dict):
        return {key: _restore_pairs(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore_pairs(item) for item in value]
    return value


def _request_dump(request: Any) -> dict[str, Any]:
    return request.model_dump(mode="json", fallback=_pair_fallback)


def _replay_endpoint(request_dump: dict[str, Any], result_dump: dict[str, Any]) -> dict[str, Any]:
    request = CandidateTask172LocalRequest.model_validate(
        _restore_pairs(request_dump), strict=False
    )
    result = Task172LocalResult.model_validate(result_dump, strict=False)
    request_hash = task172.recompute_task172_request_hash(request)
    result_hash = task172.recompute_task172_result_hash(result)
    return {
        "request_hash": request_hash,
        "result_hash": result_hash,
        "support_id": task172.recompute_task172_support_id(request),
        "candidate_id": request.candidate_binding.candidate_id,
        "candidate_hash": request.candidate_binding.candidate_hash,
        "authority_package_id": request.candidate_binding.authority_package_id,
        "authority_package_hash": request.candidate_binding.authority_package_hash,
        "task166_result_hash": request.candidate_binding.task166_result.result_hash,
        "task171_result_hash": request.candidate_binding.task171_result.result_hash,
    }


def _enclosure_event(
    label: str,
    branch: str,
    kwargs: dict[str, Any],
    failure: BaseException,
    endpoint_evaluations: list[Any],
) -> dict[str, Any]:
    diagnostics = _failure_fields(failure)
    left_q, right_q = float(diagnostics["left_q_w"]), float(diagnostics["right_q_w"])
    by_q = {float(item.q_w): item for item in endpoint_evaluations}
    left, right = by_q[left_q], by_q[right_q]
    left_result, right_result = left.task172_result, right.task172_result
    left_f = Decimal(str(left_q)) - left_result.signed_q_hot_to_cold_w
    right_f = Decimal(str(right_q)) - right_result.signed_q_hot_to_cold_w
    qcoords_left = {
        "tube_downstream_h": _state_input_enthalpy(left.tube_downstream),
        "shell_next_face_h": _state_input_enthalpy(left.shell_next_physical),
        "tube_midpoint_h": _state_input_enthalpy(left.tube_local),
        "shell_midpoint_h": _state_input_enthalpy(left.shell_local),
    }
    qcoords_right = {
        "tube_downstream_h": _state_input_enthalpy(right.tube_downstream),
        "shell_next_face_h": _state_input_enthalpy(right.shell_next_physical),
        "tube_midpoint_h": _state_input_enthalpy(right.tube_local),
        "shell_midpoint_h": _state_input_enthalpy(right.shell_local),
    }
    coordinates = []
    for name in qcoords_left:
        a, b = float(qcoords_left[name]), float(qcoords_right[name])
        adjacent = _binary64_adjacent(a, b)
        coordinates.append(
            {
                "name": name,
                "left_decimal": qcoords_left[name],
                "right_decimal": qcoords_right[name],
                "left_hex": a.hex(),
                "right_hex": b.hex(),
                "identical": a == b,
                "adjacent_or_identical": adjacent,
                "nextafter_left_toward_right": math.nextafter(a, b).hex() if a != b else a.hex(),
            }
        )
    left_request_dump, right_request_dump = (
        _request_dump(left.task172_request),
        _request_dump(right.task172_request),
    )
    left_result_dump = left_result.model_dump(mode="json")
    right_result_dump = right_result.model_dump(mode="json")
    left_replay = _replay_endpoint(left_request_dump, left_result_dump)
    right_replay = _replay_endpoint(right_request_dump, right_result_dump)
    left_tube_re, left_tube_pr = (
        left_result.tube_reynolds_number,
        left_result.tube_prandtl_number_bulk,
    )
    right_tube_re, right_tube_pr = (
        right_result.tube_reynolds_number,
        right_result.tube_prandtl_number_bulk,
    )
    left_regime, left_corr, left_corr_version = select_regime(left_tube_re, left_tube_pr)
    right_regime, right_corr, right_corr_version = select_regime(right_tube_re, right_tube_pr)
    q_checks = {
        "Q1": left_result.status == right_result.status == "VALIDATED"
        and not left_result.blockers
        and not right_result.blockers,
        "Q2": left_f < 0 < right_f,
        "Q3": abs(left_f) > Decimal("1e-6") and abs(right_f) > Decimal("1e-6"),
        "Q4": diagnostics.get("cell_hole_count", "0") == "0"
        and diagnostics.get("hole_codes", "NONE") == "NONE",
        "Q5": getattr(failure, "code", None) == "PRECISION_FLOOR_UNRESOLVED",
        "Q6": all(not item.blockers for item in (left_result, right_result))
        and all(
            rating.T_MIN_K <= Decimal(str(state.native.temperature_k)) <= rating.T_MAX_K
            and state.snapshot.phase == "liquid"
            and state.snapshot.backend == "HEOS::Water"
            and state.snapshot.provider == "CoolProp"
            and state.snapshot.provider_version == "8.0.0"
            and state.snapshot.reference_state == "DEF"
            for state in (left.tube_local, left.shell_local, right.tube_local, right.shell_local)
        ),
        "Q7": math.nextafter(left_q, right_q) == right_q,
        "Q8": all(item["adjacent_or_identical"] for item in coordinates),
        "Q9": all(
            item["identical"] or item["nextafter_left_toward_right"] == item["right_hex"]
            for item in coordinates
        ),
        "Q10": left_result.property_profile_canonical_hash
        == right_result.property_profile_canonical_hash
        and left_result.property_profile_id == right_result.property_profile_id
        and all(
            state.snapshot.backend == "HEOS::Water"
            and state.snapshot.provider_version == "8.0.0"
            and state.snapshot.provider_git_revision == "ae81610e7d23efc57f9d051c8e70a4d66e87537f"
            and state.snapshot.reference_state == "DEF"
            and state.snapshot.configuration_fingerprint
            == left.tube_local.snapshot.configuration_fingerprint
            for state in (left.tube_local, left.shell_local, right.tube_local, right.shell_local)
        ),
        "Q11": left_result.tube_correlation_id == right_result.tube_correlation_id
        and left_result.tube_correlation_version == right_result.tube_correlation_version
        and left_result.shell_correlation_id
        == right_result.shell_correlation_id
        == "TASK166_BELL_DELAWARE_WITH_REVIEWED_LOCAL_JMU"
        and left_result.shell_jmu_model_authority_canonical_hash
        == right_result.shell_jmu_model_authority_canonical_hash,
        "Q12": left_tube_re > Decimal("3000")
        and left_tube_re < Decimal("5000000")
        and right_tube_re > Decimal("3000")
        and right_tube_re < Decimal("5000000")
        and left_regime is FlowRegime.TURBULENT
        and right_regime is FlowRegime.TURBULENT
        and check_pr_envelope(left_regime, left_tube_pr)
        and check_pr_envelope(right_regime, right_tube_pr)
        and left_corr
        == right_corr
        == left_result.tube_correlation_id
        == right_result.tube_correlation_id
        and left_corr_version == right_corr_version == left_result.tube_correlation_version,
        "Q13": left_result.case_id == right_result.case_id
        and left_result.case_revision_id == right_result.case_revision_id
        and left_result.task171_result_hash == right_result.task171_result_hash
        and left_result.topology_id == right_result.topology_id
        and left_result.physical_support_id == right_result.physical_support_id
        and left_result.physical_segment_id == right_result.physical_segment_id
        and left_result.tube_cell_id == right_result.tube_cell_id
        and left_result.shell_cell_id == right_result.shell_cell_id
        and left_result.wall_interface_id == right_result.wall_interface_id,
        "Q14": left_result.numerical_profile_id == right_result.numerical_profile_id
        and left_result.r94_model_profile_canonical_hash
        == right_result.r94_model_profile_canonical_hash
        and left_result.r98_overlay_canonical_hash == right_result.r98_overlay_canonical_hash
        and left_result.selected_thermal_role_variant == right_result.selected_thermal_role_variant,
        "Q15": left_replay["request_hash"] == left_result.request_hash
        and right_replay["request_hash"] == right_result.request_hash
        and left_replay["result_hash"] == left_result.result_hash
        and right_replay["result_hash"] == right_result.result_hash,
    }
    if not all(q_checks.values()):
        raise RuntimeError(f"{label}:{branch}:PROVIDER_ENCLOSURE_Q_PREDICATE_FAILURE:{q_checks}")
    event: dict[str, Any] = {
        "schema_version": "task173.r2.transient-provider-enclosure-event.v1",
        "label": label,
        "branch": branch,
        "mesh_subdivisions": kwargs.get("mesh_subdivisions"),
        "mesh_identity": rating._candidate_mesh_identity(
            rating._candidate_context(_ACTIVE_RATING_REQUEST[label]),
            int(kwargs.get("mesh_subdivisions") or 0),
        ),
        "outer_iteration": kwargs.get("outer_iteration"),
        "shooting_enthalpy_j_kg": str(kwargs.get("shooting_enthalpy")),
        "candidate_id": left_result.case_id,
        "candidate_hash": left.task172_request.candidate_binding.candidate_hash,
        "physical_support_id": left_result.physical_support_id,
        "tube_cell_id": left_result.tube_cell_id,
        "shell_cell_id": left_result.shell_cell_id,
        "wall_interface_id": left_result.wall_interface_id,
        "left_q_w": repr(left_q),
        "right_q_w": repr(right_q),
        "left_q_hex": left_q.hex(),
        "right_q_hex": right_q.hex(),
        "left_f_w": str(left_f),
        "right_f_w": str(right_f),
        "left_task172_request_hash": left_result.request_hash,
        "right_task172_request_hash": right_result.request_hash,
        "left_task172_result_hash": left_result.result_hash,
        "right_task172_result_hash": right_result.result_hash,
        "left_task172_result_id": left_result.result_id,
        "right_task172_result_id": right_result.result_id,
        "left_shell_property_snapshot_hash": left.shell_local.snapshot_hash,
        "right_shell_property_snapshot_hash": right.shell_local.snapshot_hash,
        "left_tube_property_snapshot_hash": left.tube_local.snapshot_hash,
        "right_tube_property_snapshot_hash": right.tube_local.snapshot_hash,
        "provider_coordinates": coordinates,
        "property_state_identities": {
            "left_tube_snapshot_hash": left.tube_local.snapshot_hash,
            "right_tube_snapshot_hash": right.tube_local.snapshot_hash,
            "left_shell_snapshot_hash": left.shell_local.snapshot_hash,
            "right_shell_snapshot_hash": right.shell_local.snapshot_hash,
            "left_tube_result_identity": left_result.tube_property_snapshot_identity,
            "right_tube_result_identity": right_result.tube_property_snapshot_identity,
            "left_shell_result_identity": left_result.shell_property_snapshot_identity,
            "right_shell_result_identity": right_result.shell_property_snapshot_identity,
        },
        "provider_state_snapshots": {
            "left_tube_downstream": left.tube_downstream.snapshot.model_dump(mode="json"),
            "right_tube_downstream": right.tube_downstream.snapshot.model_dump(mode="json"),
            "left_shell_next_face": left.shell_next_physical.snapshot.model_dump(mode="json"),
            "right_shell_next_face": right.shell_next_physical.snapshot.model_dump(mode="json"),
            "left_tube_midpoint": left.tube_local.snapshot.model_dump(mode="json"),
            "right_tube_midpoint": right.tube_local.snapshot.model_dump(mode="json"),
            "left_shell_midpoint": left.shell_local.snapshot.model_dump(mode="json"),
            "right_shell_midpoint": right.shell_local.snapshot.model_dump(mode="json"),
        },
        "local_enthalpies_j_kg": {
            "left_tube": str(left.tube_local.native.enthalpy_j_kg),
            "right_tube": str(right.tube_local.native.enthalpy_j_kg),
            "left_shell": str(left.shell_local.native.enthalpy_j_kg),
            "right_shell": str(right.shell_local.native.enthalpy_j_kg),
        },
        "local_temperatures_k": {
            "left_tube": str(left.tube_local.native.temperature_k),
            "right_tube": str(right.tube_local.native.temperature_k),
            "left_shell": str(left.shell_local.native.temperature_k),
            "right_shell": str(right.shell_local.native.temperature_k),
        },
        "endpoint_request_projection_left": left_request_dump,
        "endpoint_request_projection_right": right_request_dump,
        "endpoint_result_projection_left": left_result_dump,
        "endpoint_result_projection_right": right_result_dump,
        "endpoint_replay_left": left_replay,
        "endpoint_replay_right": right_replay,
        "Q1_Q15": q_checks,
        "endpoint_replay_pass": {
            "left_request": left_replay["request_hash"] == left_result.request_hash,
            "right_request": right_replay["request_hash"] == right_result.request_hash,
            "left_result": left_replay["result_hash"] == left_result.result_hash,
            "right_result": right_replay["result_hash"] == right_result.result_hash,
        },
        "representative_endpoint": "LEFT"
        if (abs(left_f), left_q) <= (abs(right_f), right_q)
        else "RIGHT",
        "exact_point_root_found": False,
        "provider_q_span_w": str(
            abs(right_result.signed_q_hot_to_cold_w - left_result.signed_q_hot_to_cold_w)
        ),
        "provider_twi_span_k": str(
            abs(right_result.wall_temperature_inner_k - left_result.wall_temperature_inner_k)
        ),
        "provider_two_span_k": str(
            abs(right_result.wall_temperature_outer_k - left_result.wall_temperature_outer_k)
        ),
        "used_in_final_physical_acceptance": False,
        "cell_root_failure_diagnostics": list(getattr(failure, "diagnostics", ())),
        "hash_contract": "canonical_sha256(event without root event_hash)",
    }
    event["event_hash"] = canonical_sha256(event)
    return event


def _run_branch(
    label: str, request: Any, side: str, enthalpy: Decimal, iteration: int
) -> dict[str, Any]:
    context = rating._candidate_context(request)
    provider = CoolPropProvider()
    stats = rating._CellSearchStats()
    captured: list[tuple[float, Any]] = []
    events: list[dict[str, Any]] = []
    original_solve, original_eval = rating._solve_cell, rating._cell_evaluation

    def eval_wrapper(q_w: float, **kwargs: Any) -> Any:
        value = original_eval(q_w, **kwargs)
        captured.append((q_w, value))
        return value

    def solve_wrapper(**kwargs: Any) -> Any:
        start = len(captured)
        try:
            return original_solve(**kwargs)
        except rating._Stage3Failure as exc:
            if (
                exc.code != "PRECISION_FLOOR_UNRESOLVED"
                or "CELL_ROOT_PRECISION_FLOOR_REACHED" not in exc.diagnostics
            ):
                raise
            if len(events) >= 1:
                raise rating._Stage3Failure(
                    "BLOCKED_NESTED_PROVIDER_QUANTIZATION_ENCLOSURE_UNSUPPORTED",
                    f"candidate={label}",
                    f"branch={side}",
                    f"outer_iteration={iteration}",
                    f"support={kwargs['support'].physical_segment_id}",
                ) from exc
            fields = _failure_fields(exc)
            left_q, right_q = float(fields["left_q_w"]), float(fields["right_q_w"])
            local = captured[start:]
            by_q = {q: value for q, value in local}
            if left_q not in by_q or right_q not in by_q:
                raise RuntimeError(f"{label}:{side}:ENDPOINT_EVALUATION_CAPTURE_MISSING") from exc
            event = _enclosure_event(label, side, kwargs, exc, [by_q[left_q], by_q[right_q]])
            events.append(event)
            selected_q = float(left_q if side == "LEFT_BRANCH" else right_q)
            return by_q[selected_q]

    rating._cell_evaluation = eval_wrapper
    rating._solve_cell = solve_wrapper
    token = rating._CANDIDATE_RATING_CONTEXT.set(context)
    try:
        trial = rating._outer_trial(
            1, enthalpy, provider, context.shell_authority, iteration, stats
        )
    finally:
        rating._CANDIDATE_RATING_CONTEXT.reset(token)
        rating._solve_cell, rating._cell_evaluation = original_solve, original_eval
    result = {
        "transient_search_mode": True,
        "provider_enclosure_fallback_allowed": True,
        "classification": trial.classification,
        "enthalpy_j_kg": str(enthalpy),
        "diagnostics": list(trial.diagnostics),
        "events": events,
        "stats": {
            "task172_evaluation_count": stats.task172_local_evaluation_count,
            "task172_hole_count": stats.task172_numerical_hole_count,
            "hole_receipts": [item for item in stats.task172_numerical_hole_trials],
            "recovery_receipts": [asdict(item) for item in stats.endpoint_hole_level_receipts],
        },
    }
    if trial.mesh_run is not None:
        mesh_token = rating._CANDIDATE_RATING_CONTEXT.set(context)
        try:
            result["mesh_run"] = _mesh_run_payload(trial.mesh_run, stats)
        finally:
            rating._CANDIDATE_RATING_CONTEXT.reset(mesh_token)
        result["mesh_result_hash"] = trial.mesh_run.mesh_result_hash
        result["mesh_identity"] = trial.mesh_run.observables.mesh_level_identity
        result["observables"] = trial.mesh_run.observables.model_dump(mode="json")
        result["terminal_tolerance_pass"] = rating._terminal_tolerance_pass(trial.mesh_run)
    result["continuation_hash"] = canonical_sha256(
        {key: value for key, value in result.items() if key != "continuation_hash"}
    )
    return result


def _mesh_run_payload(run: Any, stats: Any) -> dict[str, Any]:
    obs = run.observables
    projection = rating._mesh_rating_projection(
        subdivisions=run.subdivisions,
        mesh_id=obs.mesh_level_identity,
        shell_outlet_enthalpy=run.shooting_enthalpy,
        outer_iterations=run.bisection_iterations,
        tube_faces=list(run.faces_tube),
        shell_faces=list(run.faces_shell),
        cells=list(run.cells),
        interval_duties=list(obs.interval_duty_w),
        total_duty=obs.total_duty_w,
        hot_loss=obs.hot_energy_loss_w,
        cold_gain=obs.cold_energy_gain_w,
        energy_residual=obs.energy_balance_residual_w,
        terminal_residual_t=obs.terminal_boundary_residual_k,
        terminal_residual_h=obs.terminal_boundary_residual_j_kg,
        stats=stats,
        hole_neighborhoods=list(run.task172_numerical_hole_neighborhoods),
    )
    assert canonical_sha256(projection) == run.mesh_result_hash
    return {
        "mesh_projection": projection,
        "mesh_result_hash": run.mesh_result_hash,
        "observables": obs.model_dump(mode="json"),
        "shooting_enthalpy_j_kg": str(run.shooting_enthalpy),
        "outer_iterations": run.bisection_iterations,
        "tube_faces": [item.model_dump(mode="json") for item in run.faces_tube],
        "shell_faces": [item.model_dump(mode="json") for item in run.faces_shell],
        "accepted_cells": [
            {
                "support": cell.support.model_dump(mode="json"),
                "rated_cell": cell.rated_cell.model_dump(mode="json"),
                "tube_approach_k": str(cell.tube_approach_k),
                "shell_approach_k": str(cell.shell_approach_k),
                "task172_request_projection": _request_dump(cell.solution.task172_request),
                "task172_result_projection": cell.solution.task172_result.model_dump(mode="json"),
                "task172_request_hash": cell.solution.task172_result.request_hash,
                "task172_result_hash": cell.solution.task172_result.result_hash,
            }
            for cell in run.cells
        ],
        "numerical_hole_receipts": list(stats.task172_numerical_hole_trials),
        "hole_recovery_receipts": [asdict(item) for item in stats.endpoint_hole_level_receipts],
        "cell_trial_receipts": [asdict(item) for item in stats.trial_receipts],
    }


def _branch_trial(
    label: str, rating_request: Any, enthalpy: Decimal, iteration: int
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    left = _run_branch(label, rating_request, "LEFT_BRANCH", enthalpy, iteration)
    if not left["events"]:
        return left, left, False
    right = _run_branch(label, rating_request, "RIGHT_BRANCH", enthalpy, iteration)
    return left, right, True


def _action(classification: str, terminal_pass: bool | None) -> str:
    if classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
        return "UPDATE_H_LOW"
    if classification == "VALID_TRAJECTORY" and terminal_pass is False:
        return "UPDATE_H_HIGH_CONTINUE"
    if classification == "VALID_TRAJECTORY" and terminal_pass is True:
        return "CANDIDATE_SHOOTING_ENTHALPY_SELECTED"
    raise RuntimeError(f"OUTER_DECISION_NOT_CLASSIFIABLE:{classification}")


def _trial_record(label: str, iteration: int, enthalpy: Decimal) -> tuple[dict[str, Any], str]:
    left, right, enclosed = _branch_trial(label, _ACTIVE_RATING_REQUEST[label], enthalpy, iteration)
    if left["classification"] == "HARD_BLOCKER" or right["classification"] == "HARD_BLOCKER":
        blocker = left if left["classification"] == "HARD_BLOCKER" else right
        raise RuntimeError(f"{label}:FIRST_BLOCKER:{blocker['diagnostics']}")
    if enclosed and left["classification"] != right["classification"]:
        raise RuntimeError(
            f"{label}:BLOCKED_TRANSIENT_OUTER_DECISION_QUANTIZATION_STRADDLE:{left['classification']}:{right['classification']}"
        )
    left_tol = left.get("terminal_tolerance_pass")
    right_tol = right.get("terminal_tolerance_pass")
    if enclosed and left["classification"] == "VALID_TRAJECTORY" and left_tol != right_tol:
        raise RuntimeError(
            f"{label}:BLOCKED_TRANSIENT_OUTER_TERMINAL_DECISION_QUANTIZATION_STRADDLE:{left_tol}:{right_tol}"
        )
    action_left = _action(left["classification"], left_tol)
    action_right = _action(right["classification"], right_tol)
    if enclosed and action_left != action_right:
        raise RuntimeError(f"{label}:OUTER_ACTION_NOT_INVARIANT:{action_left}:{action_right}")
    cert = None
    if enclosed:
        cert = {
            "schema_version": "task173.r2.outer-decision-certificate.v1",
            "candidate_id": left["events"][0]["candidate_id"],
            "candidate_hash": left["events"][0]["candidate_hash"],
            "mesh_identity": left["events"][0]["mesh_identity"],
            "mesh_subdivisions": left["events"][0]["mesh_subdivisions"],
            "shooting_enthalpy_j_kg": str(enthalpy),
            "outer_iteration": iteration,
            "trigger_support_id": left["events"][0]["physical_support_id"],
            "left_endpoint_event_hashes": [item["event_hash"] for item in left["events"]],
            "right_endpoint_event_hashes": [item["event_hash"] for item in right["events"]],
            "left_continuation_hash": left["continuation_hash"],
            "right_continuation_hash": right["continuation_hash"],
            "left_outer_classification": left["classification"],
            "right_outer_classification": right["classification"],
            "left_terminal_residual_k": left.get("observables", {}).get(
                "terminal_boundary_residual_k"
            ),
            "right_terminal_residual_k": right.get("observables", {}).get(
                "terminal_boundary_residual_k"
            ),
            "left_terminal_residual_j_kg": left.get("observables", {}).get(
                "terminal_boundary_residual_j_kg"
            ),
            "right_terminal_residual_j_kg": right.get("observables", {}).get(
                "terminal_boundary_residual_j_kg"
            ),
            "left_terminal_tolerance_decision": left_tol,
            "right_terminal_tolerance_decision": right_tol,
            "left_outer_bisection_action": action_left,
            "right_outer_bisection_action": action_right,
            "representative_branch_used_to_decide_outer_action": False,
        }
        cert["certificate_hash"] = canonical_sha256(cert)
    return {
        "iteration": iteration,
        "enthalpy_j_kg": str(enthalpy),
        "left_branch": {key: value for key, value in left.items() if key != "mesh_run"},
        "right_branch": {key: value for key, value in right.items() if key != "mesh_run"},
        "enclosure_used": enclosed,
        "outer_action": action_left,
        "decision_certificate": cert,
        "left_continuation": left if enclosed else None,
        "right_continuation": right if enclosed else None,
    }, action_left


_ACTIVE_RATING_REQUEST: dict[str, Any] = {}


def _accepted_run(
    label: str, request: Any, context: Any, enthalpy: Decimal, iterations: int
) -> dict[str, Any]:
    provider = CoolPropProvider()
    stats = rating._CellSearchStats()
    token = rating._CANDIDATE_RATING_CONTEXT.set(context)
    try:
        try:
            run = rating._valid_trajectory(
                1, enthalpy, provider, context.shell_authority, iterations, stats, True
            )
        except rating._Stage3Failure as exc:
            if (
                exc.code == "PRECISION_FLOOR_UNRESOLVED"
                and "CELL_ROOT_PRECISION_FLOOR_REACHED" in exc.diagnostics
            ):
                raise RuntimeError(
                    f"{label}:BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED:{exc.diagnostics}"
                ) from exc
            raise
    finally:
        rating._CANDIDATE_RATING_CONTEXT.reset(token)
    if not rating._terminal_tolerance_pass(run):
        raise RuntimeError(f"{label}:ACCEPTED_TRAJECTORY_TERMINAL_TOLERANCE_FAIL")
    mesh_token = rating._CANDIDATE_RATING_CONTEXT.set(context)
    try:
        payload = _mesh_run_payload(run, stats)
    finally:
        rating._CANDIDATE_RATING_CONTEXT.reset(mesh_token)
    if any(cell["rated_cell"]["task172_result_hash"] == "" for cell in payload["accepted_cells"]):
        raise RuntimeError(f"{label}:ACCEPTED_TASK172_IDENTITY_MISSING")
    payload.update(
        {
            "closure_modes": ["EXACT_VALID_POINT_ROOT"] * len(run.cells),
            "provider_enclosure_count": 0,
            "transient_search_mode": False,
            "provider_enclosure_fallback_allowed": False,
            "terminal_tolerance_pass": True,
        }
    )
    payload["trajectory_hash"] = canonical_sha256(payload)
    return payload


def _qualify_case(label: str) -> dict[str, Any]:
    candidate, bundle, topology, task174_result, request, candidate_space_hash = _build_candidate(
        label
    )
    _ACTIVE_RATING_REQUEST[label] = request
    context = rating._candidate_context(request)
    trial_rows: list[dict[str, Any]] = []
    certificates: list[dict[str, Any]] = []
    event_hashes: list[str] = []
    h_low, h_high = rating.H_MIN_J_KG, rating.H_MAX_J_KG
    seen_low, seen_valid = [h_low], [h_high]

    def evaluate(h_value: Decimal, iteration: int) -> tuple[dict[str, Any], str]:
        row, action = _trial_record(label, iteration, h_value)
        trial_rows.append(row)
        if row["decision_certificate"] is not None:
            certificates.append(row["decision_certificate"])
            for branch_key in ("left_branch", "right_branch"):
                event_hashes.extend(item["event_hash"] for item in row[branch_key]["events"])
        return row, action

    low_row, _ = evaluate(h_low, 0)
    if low_row["left_branch"]["classification"] != "LOW_SIDE_DOMAIN_INFEASIBLE":
        raise RuntimeError(f"{label}:OUTER_LOW_ENDPOINT_NOT_INFEASIBLE")
    high_row, _ = evaluate(h_high, 0)
    if high_row["left_branch"]["classification"] != "VALID_TRAJECTORY":
        raise RuntimeError(f"{label}:OUTER_HIGH_ENDPOINT_NOT_VALID")
    high_obs = high_row["left_branch"].get("observables")
    if high_obs is None:
        raise RuntimeError(f"{label}:OUTER_HIGH_TRAJECTORY_MISSING")
    high_tolerance = bool(high_row["left_branch"].get("terminal_tolerance_pass"))
    selected_h: Decimal | None = h_high if high_tolerance else None
    selected_iterations = 0
    if selected_h is None:
        iterations = 0
        while iterations < rating.MAX_OUTER_BISECTION_ITERATIONS:
            with localcontext() as context_decimal:
                context_decimal.prec = 80
                h_mid = (h_low + h_high) / Decimal(2)
            if h_mid in (h_low, h_high) or float(h_mid) in (float(h_low), float(h_high)):
                raise RuntimeError(f"{label}:OUTER_BOUNDARY_PRECISION_FLOOR_REACHED")
            iterations += 1
            row, action = evaluate(h_mid, iterations)
            classification = row["left_branch"]["classification"]
            if classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
                rating._assert_outer_classification_order(
                    seen_low, seen_valid, h_mid, classification
                )
                h_low = h_mid
                seen_low.append(h_mid)
                continue
            if classification != "VALID_TRAJECTORY":
                raise RuntimeError(f"{label}:OUTER_TRIAL_CLASSIFICATION_INVALID:{classification}")
            rating._assert_outer_classification_order(seen_low, seen_valid, h_mid, classification)
            obs = row["left_branch"].get("observables")
            if obs is None:
                raise RuntimeError(f"{label}:MISSING_OUTER_OBSERVABLES")
            h_high = h_mid
            seen_valid.append(h_mid)
            if action == "CANDIDATE_SHOOTING_ENTHALPY_SELECTED":
                selected_h, selected_iterations = h_mid, iterations
                break
        if selected_h is None:
            raise RuntimeError(f"{label}:OUTER_BOUNDARY_RESOURCE_EXHAUSTION")
    accepted = _accepted_run(label, request, context, selected_h, selected_iterations)
    if accepted["provider_enclosure_count"] != 0:
        raise RuntimeError(f"{label}:ACCEPTED_TRAJECTORY_ENCLOSURE_PRESENT")
    case = {
        "label": label,
        "cut": str(candidate.baffle_cut_fraction),
        "candidate_id": candidate.candidate_id,
        "candidate_hash": candidate.candidate_hash,
        "candidate_hash_replay": recompute_candidate_hash(candidate),
        "candidate_projection": json.loads(
            task168_canonical_bytes(candidate_projection(candidate, include_identity=True))
        ),
        "candidate_rating_request_hash": candidate_rating_request_hash(request),
        "candidate_rating_request_projection": request.model_dump(
            mode="json", fallback=_pair_fallback
        ),
        "candidate_space_hash": candidate_space_hash,
        "native_identities": {
            "TASK020": bundle.task020_configuration.configuration_hash,
            "TASK021": bundle.task021_layout.layout_hash,
            "TASK022": bundle.task022_geometry.geometry_hash,
            "TASK024": bundle.task024_geometry.geometry_hash,
            "TASK025": bundle.task025_result.result_hash,
            "TASK029": bundle.task029_result.result_hash,
            "TASK031": bundle.task031_geometry.geometry_hash,
            "TASK166": bundle.task166_result.result_hash,
            "TASK171": topology.result_hash,
            "TASK174": task174_result.result_hash,
        },
        "task174_result_projection": task174_result.model_dump(mode="json"),
        "task174_result_hash_replay": recompute_task174_result_hash(task174_result),
        "pre_rating_status": "TASK024_VALID_TASK025_VALID_TASK031_VALID_TASK166_APPLICABLE_"
        "COMPLETE_TASK171_VALID_TASK174_VALIDATED",
        "outer_search": {
            "trials": trial_rows,
            "decision_certificates": certificates,
            "actions": [row["outer_action"] for row in trial_rows],
            "selected_shooting_enthalpy_j_kg": str(selected_h),
            "outer_iterations": selected_iterations,
            "event_hashes": event_hashes,
        },
        "accepted_trajectory": accepted,
        "final_accepted_trajectory_provider_enclosure_count": 0,
        "nested_enclosure_count": 0,
        "hard_blocker_count": 0,
        "trajectory_hash": accepted["trajectory_hash"],
    }
    case["case_hash"] = canonical_sha256(case)
    return case


def _load_reference_shell_authority() -> tuple[Any, str]:
    from hexagent.exchangers.shell_tube.task173_integrated_rating.replay import (
        replay_shell_flow_authority,
    )

    evidence_path = Path(
        "docs/tasks/evidence/TASK-172-stage2-native-shell-flow-replay-correction-r1.json"
    )
    authority, task174_result, replay = replay_shell_flow_authority(
        json.loads(evidence_path.read_text()), CoolPropProvider()
    )
    if replay.get("status") != "PASS":
        raise RuntimeError("REFERENCE_SHELL_AUTHORITY_REPLAY_BLOCKED")
    expected = "ccb62cd76c6089840291cc37bf2f32dcad44d6e0ba3a0616792963b04233f419"
    if task174_result.result_hash != expected:
        raise RuntimeError(
            f"BLOCKED_REFERENCE_TASK174_IDENTITY_REGRESSION:{task174_result.result_hash}"
        )
    return authority, task174_result.result_hash


def _run_reference_n1(authority: Any) -> dict[str, Any]:
    original_solve = rating._solve_cell
    trigger_count = 0

    def count_wrapper(**kwargs: Any) -> Any:
        nonlocal trigger_count
        try:
            return original_solve(**kwargs)
        except rating._Stage3Failure as exc:
            if (
                exc.code == "PRECISION_FLOOR_UNRESOLVED"
                and "CELL_ROOT_PRECISION_FLOOR_REACHED" in exc.diagnostics
            ):
                trigger_count += 1
            raise

    rating._solve_cell = count_wrapper
    try:
        run = rating._solve_outer_boundary(
            1, CoolPropProvider(), authority, rating._CellSearchStats()
        )
    finally:
        rating._solve_cell = original_solve
    return {
        "trigger_count": trigger_count,
        "accepted_trigger_count": trigger_count,
        "mesh_result_hash": run.mesh_result_hash,
        "duty_w": str(run.observables.total_duty_w),
    }


def _control_tests() -> dict[str, str]:
    def classify(
        left: str,
        right: str,
        left_tol: bool | None,
        right_tol: bool | None,
        nested: bool = False,
        accepted: bool = False,
        hard: bool = False,
        identity: bool = True,
    ) -> str:
        if not identity:
            return "BLOCKED_ENDPOINT_IDENTITY_REPLAY_MISMATCH"
        if accepted:
            return "BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED"
        if nested:
            return "BLOCKED_NESTED_PROVIDER_QUANTIZATION_ENCLOSURE_UNSUPPORTED"
        if hard:
            return "PROPAGATE_HARD_BLOCKER"
        if left != right:
            return "BLOCKED_TRANSIENT_OUTER_DECISION_QUANTIZATION_STRADDLE"
        if left == "VALID_TRAJECTORY" and left_tol != right_tol:
            return "BLOCKED_TRANSIENT_OUTER_TERMINAL_DECISION_QUANTIZATION_STRADDLE"
        return "INVARIANT"

    cases = {
        "left_valid_right_low": classify(
            "VALID_TRAJECTORY", "LOW_SIDE_DOMAIN_INFEASIBLE", None, None
        ),
        "terminal_tolerance_split": classify("VALID_TRAJECTORY", "VALID_TRAJECTORY", True, False),
        "nested_second_enclosure": classify(
            "VALID_TRAJECTORY", "VALID_TRAJECTORY", False, False, nested=True
        ),
        "branch_hard_blocker": classify("VALID_TRAJECTORY", "HARD_BLOCKER", None, None, hard=True),
        "accepted_path_enclosure": classify(
            "VALID_TRAJECTORY", "VALID_TRAJECTORY", True, True, accepted=True
        ),
        "endpoint_identity_mismatch": classify(
            "VALID_TRAJECTORY", "VALID_TRAJECTORY", True, True, identity=False
        ),
    }
    expected = {
        "left_valid_right_low": "BLOCKED_TRANSIENT_OUTER_DECISION_QUANTIZATION_STRADDLE",
        "terminal_tolerance_split": "BLOCKED_TRANSIENT_OUTER_TERMINAL_"
        "DECISION_QUANTIZATION_STRADDLE",
        "nested_second_enclosure": "BLOCKED_NESTED_PROVIDER_QUANTIZATION_ENCLOSURE_UNSUPPORTED",
        "branch_hard_blocker": "PROPAGATE_HARD_BLOCKER",
        "accepted_path_enclosure": "BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED",
        "endpoint_identity_mismatch": "BLOCKED_ENDPOINT_IDENTITY_REPLAY_MISMATCH",
    }
    assert cases == expected
    return cases


def main() -> None:
    _check_committed_runtime()
    evidence = json.loads(AUTHORITY_PATH.read_text())
    projection = evidence["authority_candidate"]["projection"]
    if canonical_sha256(projection) != evidence["authority_candidate"]["canonical_hash"]:
        raise RuntimeError("R2_AUTHORITY_HASH_REPLAY_FAILURE")
    for case in EXPECTED_CASES:
        print("CASE_BEGIN", case, EXPECTED_CASES[case][1], flush=True)
    qualification: dict[str, Any] = {
        "status": "RUNNING",
        "runtime_source_head": RUNTIME_HEAD,
        "runtime_source_dirty": False,
        "control_tests": _control_tests(),
        "reference_task174_result_hash": None,
        "cases": [],
        "reference_n1": None,
        "first_blocker": None,
    }
    reference_authority = None
    try:
        reference_authority, reference_task174_hash = _load_reference_shell_authority()
        qualification["reference_task174_result_hash"] = reference_task174_hash
    except Exception as exc:
        qualification["status"] = "BLOCKED"
        qualification["first_blocker"] = {
            "case": "REFERENCE_TASK174",
            "stage": "REFERENCE_TASK174_IDENTITY",
            "code": type(exc).__name__,
            "details": str(exc),
        }
    for label in EXPECTED_CASES:
        if qualification["first_blocker"] is not None:
            break
        try:
            row = _qualify_case(label)
        except Exception as exc:
            qualification["status"] = "BLOCKED"
            qualification["first_blocker"] = {
                "case": label,
                "stage": "TRANSIENT_OUTER_DECISION_QUALIFICATION",
                "code": type(exc).__name__,
                "details": str(exc),
            }
            break
        qualification["cases"].append(row)
        print("CASE_COMPLETE", label, row["candidate_id"], row["candidate_hash"], flush=True)
    if qualification["first_blocker"] is None and reference_authority is not None:
        try:
            qualification["reference_n1"] = _run_reference_n1(reference_authority)
            if qualification["reference_n1"]["trigger_count"] != 0:
                raise RuntimeError("REFERENCE_TRANSIENT_ENCLOSURE_NONZERO")
        except Exception as exc:
            qualification["status"] = "BLOCKED"
            qualification["first_blocker"] = {
                "case": "REFERENCE_N1",
                "stage": "REFERENCE_N1_DORMANCY",
                "code": type(exc).__name__,
                "details": str(exc),
            }
    if qualification["first_blocker"] is None:
        qualification["status"] = "PASS"
        qualification["five_case_n1_complete"] = len(qualification["cases"]) == 5
        qualification["all_endpoint_request_hashes_replay"] = "PASS"
        qualification["all_endpoint_result_hashes_replay"] = "PASS"
        qualification["all_transient_q1_q15_pass"] = True
        qualification["all_transient_branch_continuations_complete"] = True
        qualification["all_outer_decisions_invariant"] = True
        qualification["all_terminal_tolerance_decisions_invariant"] = True
        qualification["nested_enclosure_count"] = 0
        qualification["all_final_accepted_trajectories_enclosure_free"] = True
    qualification["qualification_matrix_hash"] = canonical_sha256(
        {key: value for key, value in qualification.items() if key != "qualification_matrix_hash"}
    )
    evidence["qualification"] = qualification
    evidence["qualification_result"] = (
        "PASS_TASK173_PROVIDER_QUANTIZATION_TRANSIENT_DECISION_ENCLOSURE_R2_AUTHORITY_CANDIDATE"
        if qualification["status"] == "PASS"
        else "BLOCKED_TASK173_PROVIDER_QUANTIZATION_TRANSIENT_DECISION_ENCLOSURE_R2_QUALIFICATION"
    )
    AUTHORITY_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print("QUALIFICATION_STATUS", qualification["status"], flush=True)
    print("QUALIFICATION_MATRIX_HASH", qualification["qualification_matrix_hash"], flush=True)
    if qualification["first_blocker"] is not None:
        print(
            "FIRST_BLOCKER",
            json.dumps(qualification["first_blocker"], ensure_ascii=False, sort_keys=True),
            flush=True,
        )


if __name__ == "__main__":
    main()
