"""Production R2A producer replay fixture from Task173 captured precision-floor evidence."""

# ruff: noqa: E501

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.r2a_contract import (
    R2A_AUTHORITY_ID,
)

PRECISION_FLOOR_EVIDENCE_REL = (
    "docs/tasks/evidence/"
    "TASK-173-v0.7-full-sizing-candidate-rating-precision-floor-diagnostic-r2.json"
)


def _restore_candidate_json_values(value: Any) -> Any:
    from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
        ReferencePlanePair,
        ReferencePlaneToken,
    )

    if isinstance(value, dict) and value.get("__task173_type__") == "ReferencePlanePair":
        return ReferencePlanePair(
            ReferencePlaneToken(value["start"]), ReferencePlaneToken(value["end"])
        )
    if (
        isinstance(value, dict)
        and set(value) == {"kind", "start", "end"}
        and value["kind"] in {"internal_flow", "heat_transfer"}
    ):
        return ReferencePlanePair(
            ReferencePlaneToken(value["start"]), ReferencePlaneToken(value["end"])
        )
    if isinstance(value, dict):
        return {key: _restore_candidate_json_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore_candidate_json_values(item) for item in value]
    return value


def load_precision_floor_capture(root: Path) -> dict[str, Any]:
    path = root / PRECISION_FLOOR_EVIDENCE_REL
    evidence = json.loads(path.read_text(encoding="utf-8"))
    return evidence["candidate_b"]["precision_floor"]["observer_event"]


def _full_endpoint(
    captured: dict[str, Any], side: Literal["left", "right"]
) -> tuple[CandidateTask172LocalRequest, Task172LocalResult]:
    endpoint = captured[side]
    request = CandidateTask172LocalRequest.model_validate(
        _restore_candidate_json_values(endpoint["task172_request_projection"]),
        strict=False,
    )
    result = Task172LocalResult.model_validate(endpoint["task172_result_projection"], strict=False)
    return request, result


def build_captured_candidate_b_producer_arguments(root: Path) -> dict[str, Any]:
    captured = load_precision_floor_capture(root)
    left_request, left_result = _full_endpoint(captured, "left")
    right_request, right_result = _full_endpoint(captured, "right")
    property_context = captured["endpoint_property_context"]
    fingerprint = property_context["left"]["configuration_fingerprint"]

    def state(coordinate: dict[str, Any], side: Literal["left", "right"]) -> Any:
        return SimpleNamespace(
            native=SimpleNamespace(
                temperature_k=299.0,
                pressure_pa=101325.0,
                phase=t173.PhaseRegion.LIQUID,
                provenance=SimpleNamespace(fluid_identifier="HEOS::Water"),
            ),
            snapshot=SimpleNamespace(
                query_type="PH",
                inputs={"enthalpy_j_kg": coordinate[f"{side}_decimal"]},
                phase="liquid",
                backend="HEOS::Water",
                provider="CoolProp",
                provider_version="8.0.0",
                provider_git_revision="ae81610e7d23efc57f9d051c8e70a4d66e87537f",
                reference_state="DEF",
                configuration_fingerprint=fingerprint,
            ),
        )

    coordinates = {item["name"]: item for item in captured["provider_coordinates"]}

    def evaluation(
        request: CandidateTask172LocalRequest,
        result: Task172LocalResult,
        side: Literal["left", "right"],
        q_w: float,
    ) -> Any:
        return t173._CellEvaluation(
            q_w=Decimal(str(q_w)),
            tube_downstream=state(coordinates["tube_downstream_h"], side),
            shell_next_physical=state(coordinates["shell_next_face_h"], side),
            tube_local=state(coordinates["tube_midpoint_h"], side),
            shell_local=state(coordinates["shell_midpoint_h"], side),
            task172_request=request,
            task172_result=result,
        )

    left_q = float.fromhex(captured["left"]["q_hex"])
    right_q = float.fromhex(captured["right"]["q_hex"])
    left = t173._CellTrial(
        q_w=left_q,
        classification="VALID_CELL_EVALUATION",
        evaluation=evaluation(left_request, left_result, "left", left_q),
        residual=Decimal(captured["left"]["residual_w"]),
    )
    right = t173._CellTrial(
        q_w=right_q,
        classification="VALID_CELL_EVALUATION",
        evaluation=evaluation(right_request, right_result, "right", right_q),
        residual=Decimal(captured["right"]["residual_w"]),
    )
    context = SimpleNamespace(
        request=SimpleNamespace(
            candidate_id=captured["candidate_id"],
            candidate_hash=captured["candidate_hash"],
            authority_package_id=left_request.candidate_binding.authority_package_id,
            authority_package_hash=left_request.candidate_binding.authority_package_hash,
            task166_result=left_request.candidate_binding.task166_result,
        ),
        task171_result_hash=property_context["context_task171_hash"],
        topology_id=property_context["context_topology_id"],
        mesh_identity=left_request.topology.mesh_identity,
        physical_ownership_hash=property_context["context_physical_ownership_hash"],
    )
    control = t173._CandidateTransientControl(
        mode="DETECT",
        mesh_subdivisions=captured["mesh_subdivisions"],
        outer_iteration=captured["outer_iteration"],
        shooting_enthalpy=Decimal("107000"),
    )
    return {
        "context": context,
        "control": control,
        "support": left_request.support,
        "left": left,
        "right": right,
        "trials": {left.q_w: left, right.q_w: right},
        "captured": captured,
        "left_request": left_request,
        "right_request": right_request,
        "producer_authority_id": R2A_AUTHORITY_ID,
        "provider_identity": {
            "provider": "CoolProp",
            "provider_version": "8.0.0",
            "provider_git_revision": "ae81610e7d23efc57f9d051c8e70a4d66e87537f",
        },
        "evidence_rel": PRECISION_FLOOR_EVIDENCE_REL,
    }


def emit_production_r2a_event(root: Path) -> dict[str, Any]:
    args = build_captured_candidate_b_producer_arguments(root)
    event = t173._candidate_provider_enclosure_event(
        context=args["context"],
        control=args["control"],
        support=args["support"],
        left=args["left"],
        right=args["right"],
        trials=args["trials"],
    )
    if event is None:
        raise RuntimeError("CAPTURED_FIXTURE_DID_NOT_EMIT_R2A_EVENT")
    return event
