"""Pristine and transparent-observer replays for frozen TASK173 candidates.

Each invocation runs one candidate Rating request in one fresh Python process.
The result projection is persisted immediately after the Rating call returns,
before result-hash or frozen-ledger comparisons are performed.
"""

from __future__ import annotations

import argparse
import dataclasses
import enum
import json
import math
import os
import platform
import runpy
import subprocess
import sys
from collections.abc import Mapping
from decimal import Decimal, getcontext
from importlib import metadata
from pathlib import Path
from typing import Any

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from hexagent.canonical_json import canonical_sha256  # noqa: E402
from hexagent.exchangers.shell_tube.manufacturable_candidates import (  # noqa: E402
    service as task168,
)
from hexagent.exchangers.shell_tube.task172_local_runtime.service import (  # noqa: E402
    recompute_task172_request_hash,
    recompute_task172_result_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import (  # noqa: E402
    candidate_rating_request_hash,
    validate_candidate_rating,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as rating  # noqa: E402
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (  # noqa: E402
    Task173BlockedResult,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing import service as sizing  # noqa: E402
from hexagent.exchangers.shell_tube.task173_integrated_sizing.candidate_materialization import (  # noqa: E402
    materialize_candidate_task171,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (  # noqa: E402
    Task174NativeOutputs,
    Task174SuccessResult,
)

EXPECTED = {
    "A": {
        "candidate_id": "adeab5b1-a339-5eb3-aa66-011ffe49bac0",
        "candidate_hash": "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767",
        "request_hash": "1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7",
        "result_hash": "acf8fd832d345a3fbc6e6fed218187ee3c98367955b3a060e01b246d42adbfbb",
    },
    "B": {
        "candidate_id": "e152cca9-fd5d-59ca-9b46-1df574eee841",
        "candidate_hash": "53e0d9af366a51c915a9a369a74f7563560359dc2b562e413f4674dcb520c489",
        "request_hash": "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8",
        "result_hash": "737ed569590d1464f990566599281a2eb3d2d31d51bddf2fa472984c5a04203f",
    },
}
PREVIOUS_LOCAL_A_RESULT_HASH = "1ddde455a88fdb5ab4b17c821a78395d3c624cefb215b578a4e2a1da07d3df85"


def _audit_json(value: Any) -> Any:
    """Make a lossless-for-review JSON view of native values without hashing it."""
    if isinstance(value, enum.Enum):
        return _audit_json(value.value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, BaseModel):
        return _audit_json(value.model_dump(mode="python"))
    if type(value).__name__ == "ReferencePlanePair" and type(value).__module__.endswith(
        "owned_enums"
    ):
        return {
            "start": _audit_json(value.start),
            "end": _audit_json(value.end),
            "kind": value.kind,
        }
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _audit_json(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): _audit_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_audit_json(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(
        f"no diagnostic JSON projection for {type(value).__module__}.{type(value).__qualname__}"
    )


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _ambient_context() -> dict[str, Any]:
    context = getcontext()
    traps = {signal.__name__: bool(enabled) for signal, enabled in context.traps.items()}
    flags = {signal.__name__: bool(enabled) for signal, enabled in context.flags.items()}
    try:
        import CoolProp.CoolProp as cp

        provider = {
            "provider": "CoolProp",
            "backend": "HEOS::Water",
            "version": cp.get_global_param_string("version"),
            "git_revision": cp.get_global_param_string("gitrevision"),
            "reference_state": "DEF",
        }
    except Exception as exc:  # diagnostic only; never alters the Rating call
        provider = {"capture_error": f"{type(exc).__name__}: {exc}"}
    try:
        coolprop_package_version = metadata.version("CoolProp")
    except metadata.PackageNotFoundError:
        coolprop_package_version = None
    return {
        "git_head": _git("rev-parse", "HEAD"),
        "git_tree": _git("rev-parse", "HEAD^{tree}"),
        "python_version": platform.python_version(),
        "decimal_context": {
            "prec": context.prec,
            "rounding": context.rounding,
            "Emax": context.Emax,
            "Emin": context.Emin,
            "clamp": context.clamp,
            "capitals": context.capitals,
            "traps": traps,
            "flags": flags,
        },
        "environment": {
            name: os.environ.get(name) for name in ("PYTHONHASHSEED", "TZ", "LC_ALL", "LANG")
        },
        "coolprop_package_version": coolprop_package_version,
        "production_provider_identity": provider,
        "runtime_module_files": {
            "rating": str(Path(rating.__file__).resolve()),
            "task168": str(Path(task168.__file__).resolve()),
            "sizing": str(Path(sizing.__file__).resolve()),
        },
    }


def _build_native_rating_request(candidate_letter: str) -> tuple[Any, dict[str, Any]]:
    replay_path = (
        ROOT / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-completion-request-r1-replay.py"
    )
    replay = runpy.run_path(str(replay_path), run_name="task173_completion_request_replay")
    sizing_request, facts = replay["_build_request_and_projection"]()
    expected = EXPECTED[candidate_letter]
    candidate = next(
        item for item in facts["candidates"] if item.candidate_id == expected["candidate_id"]
    )
    if candidate.candidate_hash != expected["candidate_hash"]:
        raise RuntimeError("frozen candidate identity mismatch before diagnostic Rating")

    candidate_request = sizing_request.task168_candidate_request
    shell_record = next(
        item
        for item in candidate_request.shell_geometry_catalog.records
        if item.geometry_id == candidate.shell_geometry_id
    )
    bundle, stage_failure, _ = task168._execute_candidate_chain(
        candidate_request,
        candidate,
        shell_record,
        include_legacy_task162=False,
        include_legacy_task168_rating_dependencies=False,
        preserve_baffle_orientation_sequence=True,
    )
    if stage_failure is not None:
        raise RuntimeError(f"candidate-native upstream chain blocked: {stage_failure!r}")

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
    task174 = sizing.validate_task174_candidate(
        task174_request,
        Task174NativeOutputs(
            task029=bundle.task029_result,
            task034=None,
            task166=bundle.task166_result,
        ),
    )
    if type(task174) is not Task174SuccessResult:
        raise RuntimeError(f"candidate-native TASK174 blocked: {task174!r}")
    if task174.result_hash != sizing.recompute_task174_result_hash(task174):
        raise RuntimeError("candidate-native TASK174 result hash failed replay")

    rating_request = sizing._candidate_rating_request(
        candidate,
        facts["candidate_space_hash"],
        bundle,
        topology,
        task174,
        facts["completion_sizing_request_hash"],
    )
    request_hash = candidate_rating_request_hash(rating_request)
    if request_hash != expected["request_hash"]:
        raise RuntimeError(
            f"candidate Rating request identity mismatch: {request_hash} != "
            f"{expected['request_hash']}"
        )
    return rating_request, {
        "candidate_id": candidate.candidate_id,
        "candidate_hash": candidate.candidate_hash,
        "candidate_space_hash": facts["candidate_space_hash"],
        "completion_sizing_request_hash": facts["completion_sizing_request_hash"],
        "candidate_rating_request_hash": request_hash,
        "candidate_rating_request_projection": _audit_json(rating_request),
        "native_upstream_identities": {
            "TASK020": bundle.task020_configuration.configuration_hash,
            "TASK021": bundle.task021_layout.layout_hash,
            "TASK022": bundle.task022_geometry.geometry_hash,
            "TASK024": bundle.task024_geometry.geometry_hash,
            "TASK025": bundle.task025_result.result_hash,
            "TASK029": bundle.task029_result.result_hash,
            "TASK031": bundle.task031_geometry.geometry_hash,
            "TASK166": bundle.task166_result.result_hash,
            "TASK171": topology.result_hash,
            "TASK174": task174.result_hash,
        },
    }


def _trial_projection(trial: Any) -> dict[str, Any]:
    evaluation = trial.evaluation
    result = evaluation.task172_result if evaluation is not None else None
    request = evaluation.task172_request if evaluation is not None else None
    return {
        "classification": trial.classification,
        "q_w": repr(trial.q_w),
        "q_hex": trial.q_w.hex(),
        "residual_w": str(trial.residual) if trial.residual is not None else None,
        "task172_request_hash": (
            recompute_task172_request_hash(request) if request is not None else None
        ),
        "task172_request_projection": _audit_json(request) if request is not None else None,
        "task172_result_request_hash": getattr(result, "request_hash", None),
        "task172_result_hash": getattr(result, "result_hash", None),
        "task172_result_id": getattr(result, "result_id", None),
        "task172_result_projection": (
            result.model_dump(mode="json") if result is not None else None
        ),
    }


def _q_checks(arguments: dict[str, Any]) -> dict[str, bool]:
    context = arguments["context"]
    control = arguments["control"]
    support = arguments["support"]
    left, right = arguments["left"], arguments["right"]
    trials = arguments["trials"]
    if (
        left.evaluation is None
        or right.evaluation is None
        or left.residual is None
        or right.residual is None
    ):
        return {f"Q{i}": False for i in range(1, 16)}
    le, re = left.evaluation, right.evaluation
    lr, rr = le.task172_result, re.task172_result
    lq, rq = le.task172_request, re.task172_request
    if type(lr) is not rating.Task172LocalResult or type(rr) is not rating.Task172LocalResult:
        return {f"Q{i}": False for i in range(1, 16)}
    if (
        type(lq) is not rating.CandidateTask172LocalRequest
        or type(rq) is not rating.CandidateTask172LocalRequest
    ):
        return {f"Q{i}": False for i in range(1, 16)}
    state_pairs = (
        (le.tube_downstream, re.tube_downstream),
        (le.shell_next_physical, re.shell_next_physical),
        (le.tube_local, re.tube_local),
        (le.shell_local, re.shell_local),
    )

    def property_identity(state: Any) -> bool:
        snapshot = state.snapshot
        return (
            rating.T_MIN_K <= rating._d(state.native.temperature_k) <= rating.T_MAX_K
            and rating._d(state.native.pressure_pa) == rating.REFERENCE_PRESSURE_PA
            and state.native.phase is rating.PhaseRegion.LIQUID
            and state.native.provenance.fluid_identifier == "HEOS::Water"
            and snapshot.phase == "liquid"
            and snapshot.backend == "HEOS::Water"
            and snapshot.provider == "CoolProp"
            and snapshot.provider_version == "8.0.0"
            and snapshot.provider_git_revision == "ae81610e7d23efc57f9d051c8e70a4d66e87537f"
            and snapshot.reference_state == "DEF"
            and snapshot.query_type == "PH"
        )

    coordinates: list[bool] = []
    no_interiors: list[bool] = []
    for left_state, right_state in state_pairs:
        left_input = rating._provider_input_enthalpy(left_state)
        right_input = rating._provider_input_enthalpy(right_state)
        if left_input is None or right_input is None:
            coordinates.append(False)
            no_interiors.append(False)
            continue
        lf, rf = float(left_input), float(right_input)
        low, high = sorted((lf, rf))
        coordinates.append(rating._binary64_adjacent(lf, rf))
        no_interiors.append(low == high or math.nextafter(low, high) == high)

    from hexagent.exchangers.shell_tube.tube_side_thermal import FlowRegime
    from hexagent.exchangers.shell_tube.tube_side_thermal.nusselt_selector import (
        check_pr_envelope,
        select_regime,
    )

    lre, lpr = lr.tube_reynolds_number, lr.tube_prandtl_number_bulk
    rre, rpr = rr.tube_reynolds_number, rr.tube_prandtl_number_bulk
    lreg, lcorr, lversion = select_regime(lre, lpr)
    rreg, rcorr, rversion = select_regime(rre, rpr)
    lc, rc = lq.candidate_binding, rq.candidate_binding
    q: dict[str, bool] = {
        "Q1": lr.status == rr.status == "VALIDATED" and not lr.blockers and not rr.blockers,
        "Q2": left.residual < 0 < right.residual,
        "Q3": abs(left.residual) > Decimal("1e-6") and abs(right.residual) > Decimal("1e-6"),
        "Q4": not any(item.classification == "TASK172_NUMERICAL_HOLE" for item in trials.values()),
        "Q5": not any(item.classification == "HARD_BLOCKER" for item in trials.values()),
        "Q6": all(property_identity(state) for pair in state_pairs for state in pair),
        "Q7": left.q_w < right.q_w and math.nextafter(left.q_w, right.q_w) == right.q_w,
        "Q8": all(coordinates),
        "Q9": all(no_interiors),
        "Q10": lr.property_profile_id
        == rr.property_profile_id
        == lq.property_profile_id
        == rq.property_profile_id
        and lr.property_profile_canonical_hash == rr.property_profile_canonical_hash
        and all(
            a.snapshot.configuration_fingerprint == b.snapshot.configuration_fingerprint
            for a, b in state_pairs
        ),
        "Q11": lr.tube_correlation_id == rr.tube_correlation_id
        and lr.tube_correlation_version == rr.tube_correlation_version
        and lr.shell_correlation_id
        == rr.shell_correlation_id
        == "TASK166_BELL_DELAWARE_WITH_REVIEWED_LOCAL_JMU"
        and lr.shell_jmu_model_authority_canonical_hash
        == rr.shell_jmu_model_authority_canonical_hash,
        "Q12": lre > Decimal("3000")
        and lre < Decimal("5000000")
        and rre > Decimal("3000")
        and rre < Decimal("5000000")
        and lreg is rreg is FlowRegime.TURBULENT
        and check_pr_envelope(lreg, lpr)
        and check_pr_envelope(rreg, rpr)
        and lcorr == rcorr == lr.tube_correlation_id
        and lversion == rversion == lr.tube_correlation_version,
        "Q13": lr.case_id == rr.case_id == context.request.candidate_id
        and lr.case_revision_id == rr.case_revision_id
        and lr.task171_result_hash == rr.task171_result_hash == context.task171_result_hash
        and lq.case_id == rq.case_id == context.request.candidate_id
        and lq.case_revision_id == rq.case_revision_id == context.request.candidate_id
        and lq.topology.task171_result_hash
        == rq.topology.task171_result_hash
        == context.task171_result_hash
        and lq.topology.topology_id == rq.topology.topology_id == context.topology_id
        and lq.topology.mesh_identity == rq.topology.mesh_identity == context.mesh_identity
        and lq.topology.physical_ownership_hash
        == rq.topology.physical_ownership_hash
        == context.physical_ownership_hash
        and lr.topology_id == rr.topology_id == context.topology_id
        and lr.physical_support_id == rr.physical_support_id == support.physical_segment_id
        and lq.support.physical_segment_id
        == rq.support.physical_segment_id
        == support.physical_segment_id
        and lq.support.mesh_level_identity
        == rq.support.mesh_level_identity
        == support.mesh_level_identity
        == rating._candidate_mesh_identity(context, control.mesh_subdivisions)
        and lr.physical_segment_id == rr.physical_segment_id
        and lr.tube_cell_id == rr.tube_cell_id == support.tube_cell_id
        and lr.shell_cell_id == rr.shell_cell_id == support.shell_cell_id
        and lr.wall_interface_id == rr.wall_interface_id == support.wall_interface_id
        and lq.support.wall_interface_id
        == rq.support.wall_interface_id
        == support.wall_interface_id,
        "Q14": lr.numerical_profile_id == rr.numerical_profile_id
        and lr.r94_model_profile_canonical_hash == rr.r94_model_profile_canonical_hash
        and lr.r98_overlay_canonical_hash == rr.r98_overlay_canonical_hash
        and lr.selected_thermal_role_variant == rr.selected_thermal_role_variant
        and lr.property_profile_canonical_hash == rr.property_profile_canonical_hash,
        "Q15": recompute_task172_request_hash(lq) == lr.request_hash
        and recompute_task172_request_hash(rq) == rr.request_hash
        and recompute_task172_result_hash(lr) == lr.result_hash
        and recompute_task172_result_hash(rr) == rr.result_hash
        and le.q_w == Decimal(str(left.q_w))
        and re.q_w == Decimal(str(right.q_w))
        and lc.candidate_id == rc.candidate_id == context.request.candidate_id
        and lc.candidate_hash == rc.candidate_hash == context.request.candidate_hash
        and lc.authority_package_id
        == rc.authority_package_id
        == context.request.authority_package_id
        and lc.authority_package_hash
        == rc.authority_package_hash
        == context.request.authority_package_hash
        and lc.task166_result.result_hash
        == rc.task166_result.result_hash
        == context.request.task166_result.result_hash
        and lc.task171_result.result_hash
        == rc.task171_result.result_hash
        == context.task171_result_hash,
    }
    return q


def _observer_record(arguments: dict[str, Any], event: Any) -> dict[str, Any]:
    left, right = arguments["left"], arguments["right"]
    left_eval, right_eval = left.evaluation, right.evaluation
    coordinate_records = []
    if left_eval is not None and right_eval is not None:
        for name, left_state, right_state in (
            ("tube_downstream_h", left_eval.tube_downstream, right_eval.tube_downstream),
            ("shell_next_face_h", left_eval.shell_next_physical, right_eval.shell_next_physical),
            ("tube_midpoint_h", left_eval.tube_local, right_eval.tube_local),
            ("shell_midpoint_h", left_eval.shell_local, right_eval.shell_local),
        ):
            left_text = rating._provider_input_enthalpy(left_state)
            right_text = rating._provider_input_enthalpy(right_state)
            if left_text is None or right_text is None:
                coordinate_records.append(
                    {"name": name, "left_decimal": left_text, "right_decimal": right_text}
                )
                continue
            lf, rf = float(left_text), float(right_text)
            low, high = sorted((lf, rf))
            coordinate_records.append(
                {
                    "name": name,
                    "left_decimal": left_text,
                    "right_decimal": right_text,
                    "left_hex": lf.hex(),
                    "right_hex": rf.hex(),
                    "identical": lf == rf,
                    "adjacent": rating._binary64_adjacent(lf, rf),
                    "nextafter": math.nextafter(low, high) if low != high else low,
                    "no_representable_value_between": low == high
                    or math.nextafter(low, high) == high,
                }
            )
    record: dict[str, Any] = {
        "candidate_id": arguments["context"].request.candidate_id,
        "candidate_hash": arguments["context"].request.candidate_hash,
        "mesh_subdivisions": arguments["control"].mesh_subdivisions,
        "outer_iteration": arguments["control"].outer_iteration,
        "shooting_enthalpy_j_kg": str(arguments["control"].shooting_enthalpy),
        "transient_mode": arguments["control"].mode,
        "physical_support_id": arguments["support"].physical_segment_id,
        "left": _trial_projection(left),
        "right": _trial_projection(right),
        "provider_coordinates": coordinate_records,
        "production_return": "EVENT" if event is not None else "NONE",
        "event": event,
    }
    if left_eval is not None and right_eval is not None:
        left_result, right_result = left_eval.task172_result, right_eval.task172_result
        left_request, right_request = left_eval.task172_request, right_eval.task172_request
        context = arguments["context"]
        control = arguments["control"]
        support = arguments["support"]
        record["endpoint_property_context"] = {
            "left": {
                "fluid": left_eval.tube_local.native.provenance.fluid_identifier,
                "phase": left_eval.tube_local.native.phase.value,
                "backend": left_eval.tube_local.snapshot.backend,
                "provider": left_eval.tube_local.snapshot.provider,
                "provider_version": left_eval.tube_local.snapshot.provider_version,
                "provider_git_revision": left_eval.tube_local.snapshot.provider_git_revision,
                "reference_state": left_eval.tube_local.snapshot.reference_state,
                "configuration_fingerprint": (
                    left_eval.tube_local.snapshot.configuration_fingerprint
                ),
                "tube_re": str(left_result.tube_reynolds_number),
                "tube_pr": str(left_result.tube_prandtl_number_bulk),
                "tube_correlation_id": left_result.tube_correlation_id,
                "tube_correlation_version": left_result.tube_correlation_version,
                "candidate_id": left_request.candidate_binding.candidate_id,
                "candidate_hash": left_request.candidate_binding.candidate_hash,
                "task171_hash": left_request.topology.task171_result_hash,
                "support_id": left_request.support.physical_segment_id,
                "wall_interface_id": left_request.support.wall_interface_id,
            },
            "right": {
                "fluid": right_eval.tube_local.native.provenance.fluid_identifier,
                "phase": right_eval.tube_local.native.phase.value,
                "backend": right_eval.tube_local.snapshot.backend,
                "provider": right_eval.tube_local.snapshot.provider,
                "provider_version": right_eval.tube_local.snapshot.provider_version,
                "provider_git_revision": right_eval.tube_local.snapshot.provider_git_revision,
                "reference_state": right_eval.tube_local.snapshot.reference_state,
                "configuration_fingerprint": (
                    right_eval.tube_local.snapshot.configuration_fingerprint
                ),
                "tube_re": str(right_result.tube_reynolds_number),
                "tube_pr": str(right_result.tube_prandtl_number_bulk),
                "tube_correlation_id": right_result.tube_correlation_id,
                "tube_correlation_version": right_result.tube_correlation_version,
                "candidate_id": right_request.candidate_binding.candidate_id,
                "candidate_hash": right_request.candidate_binding.candidate_hash,
                "task171_hash": right_request.topology.task171_result_hash,
                "support_id": right_request.support.physical_segment_id,
                "wall_interface_id": right_request.support.wall_interface_id,
            },
            "context_candidate_id": context.request.candidate_id,
            "context_candidate_hash": context.request.candidate_hash,
            "context_task171_hash": context.task171_result_hash,
            "context_topology_id": context.topology_id,
            "context_mesh_identity": context.mesh_identity,
            "context_physical_ownership_hash": context.physical_ownership_hash,
            "expected_candidate_mesh_identity": rating._candidate_mesh_identity(
                context, control.mesh_subdivisions
            ),
            "support_id": support.physical_segment_id,
            "support_mesh_level_identity": support.mesh_level_identity,
            "support_tube_cell_id": support.tube_cell_id,
            "support_shell_cell_id": support.shell_cell_id,
            "support_wall_interface_id": support.wall_interface_id,
        }
        record["Q13_components"] = {
            "result_case_ids_match_candidate": left_result.case_id
            == right_result.case_id
            == context.request.candidate_id,
            "result_case_revision_ids_match": left_result.case_revision_id
            == right_result.case_revision_id,
            "result_task171_hashes_match_context": left_result.task171_result_hash
            == right_result.task171_result_hash
            == context.task171_result_hash,
            "request_case_ids_match_candidate": left_request.case_id
            == right_request.case_id
            == context.request.candidate_id,
            "request_case_revision_ids_match_candidate": left_request.case_revision_id
            == right_request.case_revision_id
            == context.request.candidate_id,
            "request_topology_task171_hashes_match_context": (
                left_request.topology.task171_result_hash
            )
            == right_request.topology.task171_result_hash
            == context.task171_result_hash,
            "request_topology_ids_match_context": left_request.topology.topology_id
            == right_request.topology.topology_id
            == context.topology_id,
            "request_mesh_identities_match_context": left_request.topology.mesh_identity
            == right_request.topology.mesh_identity
            == context.mesh_identity,
            "request_physical_ownership_hashes_match_context": (
                left_request.topology.physical_ownership_hash
            )
            == right_request.topology.physical_ownership_hash
            == context.physical_ownership_hash,
            "result_topology_ids_match_context": left_result.topology_id
            == right_result.topology_id
            == context.topology_id,
            "result_physical_support_matches": left_result.physical_support_id
            == right_result.physical_support_id
            == support.physical_segment_id,
            "request_physical_support_matches": left_request.support.physical_segment_id
            == right_request.support.physical_segment_id
            == support.physical_segment_id,
            "request_mesh_level_identity_matches_candidate_mesh": (
                left_request.support.mesh_level_identity
            )
            == right_request.support.mesh_level_identity
            == support.mesh_level_identity
            == rating._candidate_mesh_identity(context, control.mesh_subdivisions),
            "result_physical_segments_match": left_result.physical_segment_id
            == right_result.physical_segment_id,
            "result_tube_cell_ids_match_support": left_result.tube_cell_id
            == right_result.tube_cell_id
            == support.tube_cell_id,
            "result_shell_cell_ids_match_support": left_result.shell_cell_id
            == right_result.shell_cell_id
            == support.shell_cell_id,
            "result_wall_interfaces_match_support": left_result.wall_interface_id
            == right_result.wall_interface_id
            == support.wall_interface_id,
            "request_wall_interfaces_match_support": left_request.support.wall_interface_id
            == right_request.support.wall_interface_id
            == support.wall_interface_id,
        }
    if event is None:
        record["Q1_Q15"] = _q_checks(arguments)
        false_qs = [name for name, passes in record["Q1_Q15"].items() if not passes]
        record["first_false_q"] = false_qs[0] if false_qs else None
        record["all_false_qs"] = false_qs
        record["r2a_eligibility"] = (
            "NOT_ELIGIBLE" if false_qs else "FULLY_ELIGIBLE_BUT_NOT_TRIGGERED"
        )
    else:
        record["Q1_Q15"] = event.get("Q1_Q15")
        record["first_false_q"] = None
        record["all_false_qs"] = []
        record["r2a_eligibility"] = "ELIGIBLE_AND_TRIGGERED"
    return record


def _result_identity(projection: dict[str, Any]) -> str:
    return canonical_sha256(
        {
            "schema_version": projection["schema_version"],
            "status": projection["status"],
            "failure_code": projection["failure_code"],
            "failed_mesh_subdivisions": projection["failed_mesh_subdivisions"],
            "request_hash": projection["request_hash"],
            "diagnostics": projection["diagnostics"],
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=("A", "B"), required=True)
    parser.add_argument("--mode", choices=("pristine", "observer"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata-output", type=Path, required=True)
    parser.add_argument("--observer-output", type=Path)
    args = parser.parse_args()

    request, request_facts = _build_native_rating_request(args.candidate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    request_path = args.output.with_name(args.output.stem + "-request.json")
    request_path.write_text(
        json.dumps(request_facts, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    before = _ambient_context()
    events: list[dict[str, Any]] = []
    monkey_patch_count = 0
    observer_installed = False
    if args.mode == "observer":
        original = rating._candidate_provider_enclosure_event

        def observing_wrapper(**kwargs: Any) -> Any:
            event = original(**kwargs)
            try:
                events.append(_observer_record(kwargs, event))
            except Exception as exc:  # instrumentation errors are recorded, not propagated
                events.append({"observer_capture_error": f"{type(exc).__name__}: {exc}"})
            return event

        rating._candidate_provider_enclosure_event = observing_wrapper
        monkey_patch_count = 1
        observer_installed = True
    try:
        outcome = validate_candidate_rating(request)
    finally:
        if observer_installed:
            rating._candidate_provider_enclosure_event = original

    # Persist the complete returned model before computing or comparing any hash.
    result_projection = outcome.model_dump(mode="json")
    args.output.write_text(
        json.dumps(result_projection, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    after = _ambient_context()
    if args.observer_output is not None:
        args.observer_output.write_text(
            json.dumps(events, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    digest = _result_identity(result_projection) if "failure_code" in result_projection else None
    expected = EXPECTED[args.candidate]
    metadata_projection = {
        "candidate": args.candidate,
        "mode": args.mode,
        "candidate_rating_request_hash": request_facts["candidate_rating_request_hash"],
        "expected_request_hash": expected["request_hash"],
        "request_projection_path": str(request_path),
        "result_preimage_path": str(args.output),
        "observer_events_path": str(args.observer_output) if args.observer_output else None,
        "monkey_patch_count": monkey_patch_count,
        "observer_installed": observer_installed,
        "blocked_result_type": type(outcome) is Task173BlockedResult,
        "recomputed_result_hash": digest,
        "returned_result_hash": result_projection.get("result_hash"),
        "returned_result_id": result_projection.get("result_id"),
        "expected_public_sizing_result_hash": expected["result_hash"],
        "previous_local_a_result_hash": PREVIOUS_LOCAL_A_RESULT_HASH
        if args.candidate == "A"
        else None,
        "ambient_before": before,
        "ambient_after": after,
        "native_upstream_identities": request_facts["native_upstream_identities"],
        "full_candidate_rating_request_projection": request_facts[
            "candidate_rating_request_projection"
        ],
        "full_blocked_result_projection": result_projection,
        "observer_events": events,
    }
    args.metadata_output.write_text(
        json.dumps(metadata_projection, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"CANDIDATE={args.candidate}")
    print(f"MODE={args.mode}")
    print(f"CANDIDATE_RATING_REQUEST_HASH={request_facts['candidate_rating_request_hash']}")
    print(f"MONKEY_PATCH_COUNT={monkey_patch_count}")
    print(f"OBSERVER_INSTALLED={str(observer_installed).lower()}")
    print(f"RESULT_TYPE={type(outcome).__name__}")
    print(f"RECOMPUTED_RESULT_HASH={digest}")
    print(f"RETURNED_RESULT_HASH={result_projection.get('result_hash')}")
    print(f"EXPECTED_RESULT_HASH={expected['result_hash']}")
    print(f"RESULT_PREIMAGE_PERSISTED={args.output.exists()}")
    if args.observer_output is not None:
        print(f"OBSERVER_EVENT_COUNT={len(events)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
