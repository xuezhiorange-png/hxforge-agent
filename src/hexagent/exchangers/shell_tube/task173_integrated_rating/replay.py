"""Exact native replay of the reviewed Stage-2 shell-flow authority chain."""

from __future__ import annotations

import copy
import json
from dataclasses import fields, is_dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.bell_delaware import validate_request as task166_validate
from hexagent.exchangers.shell_tube.bell_delaware.canonical import result_hash as task166_hash
from hexagent.exchangers.shell_tube.bell_delaware.canonical import result_id as task166_id
from hexagent.exchangers.shell_tube.shell_side_flow_state import (
    validate_request as task032_validate,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    validate_request as task031_validate,
)
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    ShellFlowAuthority,
    Task172LocalRequest,
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.task172_local_runtime.service import (
    recompute_task172_request_hash,
    recompute_task172_result_hash,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration.models import (
    Task174SuccessResult,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration.service import (
    recompute_task174_result_hash,
)
from hexagent.properties.coolprop_provider import CoolPropProvider

EXPECTED_STAGE2_EVIDENCE_HASH = "3ed4da6385097e1ee57196c5946d37943d073d4506e35149ef57ad9183cdd100"
EXPECTED_SHARED_NATIVE_PAYLOAD_HASH = (
    "a769116b0deb0fdddb0ee455a3d8a344eb702171633ab43bf03ebba466565dd1"
)
EXPECTED_TASK031_GEOMETRY_ID = "82b051f6-d8f6-5bbb-b46f-76609b9f8cca"
EXPECTED_TASK031_GEOMETRY_HASH = "1dc32d501ee1ba283e4d2bb5eab2f2f5ffc81e464fd6f254ff13b02ceb01519e"
EXPECTED_TASK031_REQUEST_HASH = "688c13a7d9022338fba1787be6a0a0867bd3e37e1bac2528fcae101cb66adb58"
EXPECTED_TASK032_RESULT_ID = "8a43b528-acca-5388-8f82-cd85e53b820e"
EXPECTED_TASK032_RESULT_HASH = "58e47124f94d14ece0f1c93a0bb5510b7dda52bfbc60b9f650fbf72c1eb232d2"
EXPECTED_TASK032_REQUEST_HASH = "942c339c85a585d51be5a6431b17ae3f4064d2ae9d6166a51cdf4651e444e13e"
EXPECTED_TASK166_RESULT_ID = "ad4745b7-fa18-519f-99c2-e76b12bb23dc"
EXPECTED_TASK166_RESULT_HASH = "a42aee19a2fbb77d1666e4b7170b86e3a9e036f992ef8030a9c2ecf1928c151d"
EXPECTED_TASK166_REQUEST_HASH = "1083b8fbaef93ef2370b63364b3fd9e40f2ba0e98d2c8dd1b852f2da158967c2"
EXPECTED_TASK172_RESULT_HASH = "14feaec9190e5e00be79f638db8e5e572adf83788a628b56b4ba1d9b20036e63"
EXPECTED_TASK174_RESULT_ID = (
    "urn:hxforge:task174:ccb62cd76c6089840291cc37bf2f32dcad44d6e0ba3a0616792963b04233f419"
)
EXPECTED_TASK174_RESULT_HASH = "ccb62cd76c6089840291cc37bf2f32dcad44d6e0ba3a0616792963b04233f419"
SUPERSEDED_EFFECTIVE_IDENTITIES = frozenset(
    {
        "3b639d0523b799f92bdf59ebee415dc263dac5164ab816cb5fb7df5b3ed37cb7",
        "ed3c9b1d-b303-5b50-9faf-ba1a1fd927df",
        "59cfd30e3cf7d4a199744824c26daf61a85f668daad20b8a5c5861755ff5e50e",
        "e8ce04e6e48120ff8d655c16a4aa07a1ddd32f8bc22afbc1bb750291a35dae0e",
    }
)


class NativeReplayError(ValueError):
    """Raised when accepted native upstream identities cannot be replayed."""


def public_projection(value: Any) -> Any:
    """Serialize native objects without reprs or process-specific identities."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value):
        return {
            field.name: public_projection(getattr(value, field.name)) for field in fields(value)
        }
    if isinstance(value, dict):
        return {str(key): public_projection(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [public_projection(item) for item in value]
    return value


def _replay_one(payload: dict[str, Any]) -> tuple[Any, Any, Any, dict[str, Any]]:
    task031_request = copy.deepcopy(payload["TASK031_request"])
    task032_request = copy.deepcopy(payload["TASK032_request"])
    task166_request = copy.deepcopy(payload["TASK166_request"])
    task031 = task031_validate(task031_request)
    task032 = task032_validate(task032_request)
    task166 = task166_validate(task166_request)
    if (
        task031.status.value != "VALID"
        or task031.geometry is None
        or task032.status.value != "VALID"
        or task032.flow_state is None
        or task166.status.value != "VALID"
        or task166.valid is None
    ):
        raise NativeReplayError(
            "BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: native producer blocked"
        )

    geometry = task031.geometry
    flow_state = task032.flow_state
    result = task166.valid
    if (
        geometry.geometry_id != EXPECTED_TASK031_GEOMETRY_ID
        or geometry.geometry_hash != EXPECTED_TASK031_GEOMETRY_HASH
        or geometry.request_hash != EXPECTED_TASK031_REQUEST_HASH
        or flow_state.result_id != EXPECTED_TASK032_RESULT_ID
        or flow_state.result_hash != EXPECTED_TASK032_RESULT_HASH
        or flow_state.request_hash != EXPECTED_TASK032_REQUEST_HASH
        or result.result_id != EXPECTED_TASK166_RESULT_ID
        or result.result_hash != EXPECTED_TASK166_RESULT_HASH
        or result.request_hash != EXPECTED_TASK166_REQUEST_HASH
        or result.result_hash != task166_hash(result)
        or result.result_id != task166_id(result.result_hash)
    ):
        raise NativeReplayError("BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: identity")

    if (
        payload.get("TASK031_native_result") != public_projection(geometry)
        or payload.get("TASK032_native_result") != public_projection(flow_state)
        or payload.get("TASK166_native_result") != public_projection(result)
    ):
        raise NativeReplayError(
            "BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: persisted native result projection"
        )

    # TASK166 has its own narrower public projection of TASK032's native flow
    # state. Compare every overlapping producer field, then verify the two
    # TASK166-only context fields against their accepted case semantics.
    embedded_flow = task166_request.get("shell_side_flow_state")
    replayed_flow = public_projection(flow_state)
    if type(embedded_flow) is not dict or any(
        embedded_flow.get(key) != value
        for key, value in replayed_flow.items()
        if key in embedded_flow
    ):
        raise NativeReplayError(
            "BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: TASK032 to TASK166 field binding"
        )
    if (
        embedded_flow.get("status") != "VALID"
        or embedded_flow.get("physical_exchanger_case_id") != flow_state.shell_side_case_id
        or not set(embedded_flow).issubset(
            set(replayed_flow) | {"status", "physical_exchanger_case_id"}
        )
    ):
        raise NativeReplayError(
            "BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: TASK166 flow projection shape"
        )
    request_flow = task166_request.get("shell_side_flow_state_request")
    if type(request_flow) is not dict:
        raise NativeReplayError(
            "BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: TASK032 request binding"
        )
    if (
        request_flow.get("task031_geometry_id") != geometry.geometry_id
        or request_flow.get("task031_geometry_hash") != geometry.geometry_hash
        or request_flow.get("task032_request_hash") != flow_state.request_hash
        or request_flow.get("task032_result_hash") != flow_state.result_hash
        or request_flow.get("task032_result_id") != flow_state.result_id
        or request_flow.get("property_snapshot") != task032_request.get("property_snapshot")
        or request_flow.get("mass_flow_authority") != task032_request.get("mass_flow_authority")
    ):
        raise NativeReplayError(
            "BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: TASK032 input projection"
        )

    projection = {
        "TASK031_request": task031_request,
        "TASK031_result": public_projection(geometry),
        "TASK032_request": task032_request,
        "TASK032_result": public_projection(flow_state),
        "TASK166_request": task166_request,
        "TASK166_result": public_projection(result),
    }
    return geometry, flow_state, result, projection


def replay_shell_flow_authority(
    evidence: dict[str, Any], provider: CoolPropProvider | None = None
) -> tuple[ShellFlowAuthority, Task174SuccessResult, dict[str, Any]]:
    """Replay two independent native chains and build the accepted authorities."""
    if type(evidence) is not dict or canonical_sha256(evidence) != EXPECTED_STAGE2_EVIDENCE_HASH:
        raise NativeReplayError("BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: evidence hash")
    payload = evidence.get("shared_native_payload")
    if type(payload) is not dict:
        raise NativeReplayError("BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: missing native payload")
    payload_without_hash = {
        key: value for key, value in payload.items() if key != "shared_payload_sha256"
    }
    if (
        payload.get("shared_payload_sha256") != EXPECTED_SHARED_NATIVE_PAYLOAD_HASH
        or canonical_sha256(payload_without_hash) != EXPECTED_SHARED_NATIVE_PAYLOAD_HASH
    ):
        raise NativeReplayError("BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: payload hash")

    chain_a = _replay_one(payload)
    chain_b = _replay_one(payload)
    if chain_a[3] != chain_b[3]:
        raise NativeReplayError(
            "BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: independent run divergence"
        )
    geometry, flow_state, task166_result, _ = chain_a
    shell_authority = ShellFlowAuthority(
        task031_geometry=geometry,
        task166_result=task166_result,
    )

    # Deserialize the accepted Stage-2 reference TASK172 request from its full
    # native payload, then substitute only the independently replayed typed
    # ShellFlowAuthority object. No test helper or summary-to-native promotion.
    raw_task172_request = payload.get("TASK172_request")
    if type(raw_task172_request) is not dict:
        raise NativeReplayError(
            "BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: missing TASK172 request"
        )
    encoded_request = json.dumps(raw_task172_request, separators=(",", ":"), ensure_ascii=False)
    task172_request = Task172LocalRequest.model_validate_json(encoded_request, strict=True)
    if (
        task172_request.shell_flow_authority.task031_geometry.geometry_hash
        != geometry.geometry_hash
        or task172_request.shell_flow_authority.task166_result.result_hash
        != task166_result.result_hash
    ):
        raise NativeReplayError("BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: TASK172 binding")
    task172_request = task172_request.model_copy(update={"shell_flow_authority": shell_authority})
    raw_task172_result = payload.get("TASK172_native_result")
    if type(raw_task172_result) is not dict:
        raise NativeReplayError(
            "BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: missing TASK172 result payload"
        )
    encoded_result = json.dumps(raw_task172_result, separators=(",", ":"), ensure_ascii=False)
    task172_result = Task172LocalResult.model_validate_json(encoded_result, strict=True)
    if (
        recompute_task172_request_hash(task172_request) != task172_result.request_hash
        or task172_result.result_hash != EXPECTED_TASK172_RESULT_HASH
        or recompute_task172_result_hash(task172_result) != EXPECTED_TASK172_RESULT_HASH
    ):
        raise NativeReplayError(
            "BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: TASK172 payload identity"
        )

    corrected_raw = evidence.get("corrected_downstream_native_results", {}).get("task174_result")
    if type(corrected_raw) is not dict:
        raise NativeReplayError("BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: missing TASK174 result")
    task174_fields = dict(corrected_raw)
    for name, value in tuple(task174_fields.items()):
        if name.endswith("_pa") and isinstance(value, str):
            task174_fields[name] = Decimal(value)
    task174 = Task174SuccessResult.model_validate(task174_fields, strict=True)
    task174_hash = recompute_task174_result_hash(task174)
    if (
        task174_hash != EXPECTED_TASK174_RESULT_HASH
        or task174.result_hash != task174_hash
        or task174.result_id != EXPECTED_TASK174_RESULT_ID
        or task174.task166_result_hash != EXPECTED_TASK166_RESULT_HASH
        or task174.task166_result_id != task166_result.result_id
        or task174.status != "VALIDATED"
        or task174.modeled_total_tube_side_pressure_drop_pa != Decimal("436.958")
        or task174.bell_total_shell_pressure_drop_pa
        != Decimal("695.60879452416523317091096372842532069004685992373")
        or task174.tube_outlet_pressure_pa != Decimal("100888.042")
        or task174.shell_outlet_pressure_pa
        != Decimal("100629.39120547583476682908903627157467930995314008")
    ):
        raise NativeReplayError(
            "BLOCKED_NATIVE_SHELL_FLOW_REPLAY_MISMATCH: corrected TASK174 binding"
        )

    replay = {
        "status": "PASS",
        "bundle_canonical_hash": EXPECTED_STAGE2_EVIDENCE_HASH,
        "shared_native_payload_sha256": EXPECTED_SHARED_NATIVE_PAYLOAD_HASH,
        "task031_geometry_id": geometry.geometry_id,
        "task031_geometry_hash": geometry.geometry_hash,
        "task031_request_hash": geometry.request_hash,
        "task032_result_id": flow_state.result_id,
        "task032_result_hash": flow_state.result_hash,
        "task032_request_hash": flow_state.request_hash,
        "task166_result_id": task166_result.result_id,
        "task166_result_hash": task166_result.result_hash,
        "task166_request_hash": task166_result.request_hash,
        "task172_reference_result_hash": task172_result.result_hash,
        "task172_reference_result_payload_identity_validated": True,
        "task172_reference_producer_reinvoked_during_shell_replay": False,
        "task174_result_id": task174.result_id,
        "task174_result_hash": task174.result_hash,
        "run_a": chain_a[3],
        "run_b": chain_b[3],
        "same_native_payload": True,
        "same_native_identities_and_outputs": True,
        "test_fixture_used_as_authority": False,
    }
    return shell_authority, task174, replay


__all__ = [
    "EXPECTED_STAGE2_EVIDENCE_HASH",
    "EXPECTED_SHARED_NATIVE_PAYLOAD_HASH",
    "EXPECTED_TASK031_GEOMETRY_HASH",
    "EXPECTED_TASK032_RESULT_HASH",
    "EXPECTED_TASK166_RESULT_HASH",
    "EXPECTED_TASK174_RESULT_HASH",
    "NativeReplayError",
    "SUPERSEDED_EFFECTIVE_IDENTITIES",
    "public_projection",
    "replay_shell_flow_authority",
]
