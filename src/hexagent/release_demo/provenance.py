"""The frozen seven-node, six-edge TASK036 provenance projection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .canonical import provenance_hash
from .schema import (
    PROFILE_ID,
    PROVENANCE_EDGES,
    PROVENANCE_FIELDS,
    PROVENANCE_NODES,
)


def _value(record: Mapping[str, Any], field: str, default: Any = None) -> Any:
    return record.get(field, default)


def _producer_edge(
    producer_task: str,
    consumer_task: str,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "producer_task": producer_task,
        "consumer_task": consumer_task,
        "producer_request_hash": _value(result, "request_hash"),
        "producer_result_hash": _value(result, "result_hash"),
        "producer_result_id": _value(result, "result_id"),
        "producer_status": _value(result, "status", "VALID"),
    }


def _result_projection(envelope: Mapping[str, Any], payload_key: str) -> dict[str, Any]:
    payload = envelope.get(payload_key)
    if not isinstance(payload, Mapping):
        return {"status": envelope.get("status", "BLOCKED")}
    result = dict(payload)
    result["status"] = envelope.get("status", "VALID")
    return result


def build_provenance(
    *,
    task031_result: Mapping[str, Any],
    task032_result: Mapping[str, Any],
    task033_result: Mapping[str, Any],
    task034_result: Mapping[str, Any],
    task035_result: Mapping[str, Any],
    demo_id: str,
    release_evidence_ledger_hash: str,
    artifact_manifest_digest: str,
    acceptance_checklist_digest: str,
    source_commit: str,
    source_tree: str,
) -> dict[str, Any]:
    """Build provenance without inventing an identity for release evidence."""

    t031 = _result_projection(task031_result, "geometry")
    t032 = _result_projection(task032_result, "flow_state")
    t033 = _result_projection(task033_result, "heat_transfer")
    t034 = _result_projection(task034_result, "pressure_drop")
    t035 = _result_projection(task035_result, "success_result")

    edges = [
        _producer_edge("TASK031", "TASK032", t031),
        _producer_edge("TASK032", "TASK033", t032),
        _producer_edge("TASK033", "TASK034", t033),
        _producer_edge("TASK034", "TASK035", t034),
        _producer_edge("TASK035", "TASK036_RELEASE_EVIDENCE", t035),
        {
            "producer_task": "TASK036_RELEASE_EVIDENCE",
            "consumer_task": "TASK036_ACCEPTANCE_RESULT",
            "producer_evidence_hash": release_evidence_ledger_hash,
            "producer_status": "VALID",
        },
    ]
    record: dict[str, Any] = {
        "schema_version": "task036.provenance.v1",
        "task_id": "TASK036",
        "profile_id": PROFILE_ID,
        "demo_id": demo_id,
        "task031_request_hash": _value(t031, "request_hash"),
        "task031_geometry_id": _value(t031, "geometry_id"),
        "task031_geometry_hash": _value(t031, "geometry_hash"),
        "task032_request_hash": _value(t032, "request_hash"),
        "task032_result_hash": _value(t032, "result_hash"),
        "task032_result_id": _value(t032, "result_id"),
        "task033_request_hash": _value(t033, "request_hash"),
        "task033_result_hash": _value(t033, "result_hash"),
        "task033_result_id": _value(t033, "result_id"),
        "task034_request_hash": _value(t034, "request_hash"),
        "task034_result_hash": _value(t034, "result_hash"),
        "task034_result_id": _value(t034, "result_id"),
        "task035_request_hash": _value(t035, "request_hash"),
        "task035_result_hash": _value(t035, "result_hash"),
        "task035_result_id": _value(t035, "result_id"),
        "producer_edges": edges,
        "release_evidence_ledger_hash": release_evidence_ledger_hash,
        "artifact_manifest_digest": artifact_manifest_digest,
        "acceptance_checklist_digest": acceptance_checklist_digest,
        "source_commit": source_commit,
        "source_tree": source_tree,
        "provenance_hash": "",
    }
    record["provenance_hash"] = provenance_hash(record)
    return record


def provenance_edge_shape_is_valid(record: Mapping[str, Any]) -> bool:
    edges = record.get("producer_edges")
    if type(edges) is not list or len(edges) != len(PROVENANCE_EDGES):
        return False
    for index, (producer, consumer) in enumerate(PROVENANCE_EDGES):
        edge = edges[index]
        if type(edge) is not dict:
            return False
        if edge.get("producer_task") != producer or edge.get("consumer_task") != consumer:
            return False
        if producer == "TASK036_RELEASE_EVIDENCE":
            if set(edge) != {
                "producer_task",
                "consumer_task",
                "producer_evidence_hash",
                "producer_status",
            }:
                return False
            if not edge.get("producer_evidence_hash"):
                return False
        elif set(edge) != {
            "producer_task",
            "consumer_task",
            "producer_request_hash",
            "producer_result_hash",
            "producer_result_id",
            "producer_status",
        }:
            return False
    return True


def verify_provenance(record: Mapping[str, Any]) -> bool:
    return (
        tuple(record) == PROVENANCE_FIELDS
        and provenance_edge_shape_is_valid(record)
        and record.get("provenance_hash") == provenance_hash(record)
        and all(left != right for left, right in PROVENANCE_EDGES)
        and tuple(PROVENANCE_NODES)
        == (
            "TASK031",
            "TASK032",
            "TASK033",
            "TASK034",
            "TASK035",
            "TASK036_RELEASE_EVIDENCE",
            "TASK036_ACCEPTANCE_RESULT",
        )
    )


__all__ = ["build_provenance", "provenance_edge_shape_is_valid", "verify_provenance"]
