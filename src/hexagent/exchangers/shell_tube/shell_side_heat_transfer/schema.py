"""Closed decoder for the TASK-033 five-field public request boundary."""

from __future__ import annotations

from typing import Any

from .blocker_registry import BlockerCode, make_blocker
from .models import (
    FLOW_STATE_EVIDENCE_FIELDS,
    PROFILE_ID,
    REQUEST_EVIDENCE_FIELDS,
    REQUEST_FIELDS,
    REQUEST_SCHEMA_VERSION,
    ShellSideHeatTransferRequest,
    Task032AcceptedFlowStateEvidence,
    Task032AcceptedRequestEvidence,
)


class SchemaFailure(Exception):
    def __init__(self, *, stage: str, blockers: tuple[Any, ...]) -> None:
        super().__init__(stage)
        self.stage = stage
        self.blockers = blockers


def _dict(value: Any) -> bool:
    return type(value) is dict


def _strings(value: Any) -> bool:
    return (
        type(value) is list
        and bool(value)
        and all(type(item) is str and bool(item) for item in value)
    )


def _closed(value: Any, fields: tuple[str, ...], path: str, blockers: list[Any]) -> bool:
    if not _dict(value):
        blockers.append(
            make_blocker(BlockerCode.SSHT_RAW_TYPE_INVALID, stage="S01", field_path=path)
        )
        return False
    expected = set(fields)
    for key in value:
        if type(key) is not str or key not in expected:
            blockers.append(
                make_blocker(BlockerCode.SSHT_UNKNOWN_FIELD, stage="S01", field_path=path)
            )
    for field in fields:
        if field not in value:
            blockers.append(
                make_blocker(
                    BlockerCode.SSHT_RAW_TYPE_INVALID, stage="S01", field_path=f"{path}.{field}"
                )
            )
    return not blockers


def parse_request(raw_request: Any) -> ShellSideHeatTransferRequest:
    if type(raw_request) is not dict:
        raise SchemaFailure(
            stage="S00",
            blockers=(
                make_blocker(BlockerCode.SSHT_RAW_TYPE_INVALID, stage="S00", field_path=None),
            ),
        )
    blockers: list[Any] = []
    if not _closed(raw_request, REQUEST_FIELDS, "request", blockers):
        raise SchemaFailure(stage="S01", blockers=tuple(blockers))
    if raw_request["schema_version"] != REQUEST_SCHEMA_VERSION:
        blockers.append(
            make_blocker(
                BlockerCode.SSHT_SCHEMA_VERSION_UNSUPPORTED,
                stage="S01",
                field_path="schema_version",
            )
        )
    if raw_request["profile_id"] != PROFILE_ID:
        blockers.append(
            make_blocker(
                BlockerCode.SSHT_PROFILE_ID_UNSUPPORTED, stage="S01", field_path="profile_id"
            )
        )
    if not _strings(raw_request["evidence_refs"]) or len(set(raw_request["evidence_refs"])) != len(
        raw_request["evidence_refs"]
    ):
        blockers.append(
            make_blocker(
                BlockerCode.SSHT_EVIDENCE_REFS_INVALID, stage="S01", field_path="evidence_refs"
            )
        )
    if blockers:
        raise SchemaFailure(stage="S01", blockers=tuple(blockers))

    raw_flow = raw_request["task032_flow_state"]
    raw_evidence = raw_request["task032_request_evidence"]
    if not _dict(raw_flow):
        raise SchemaFailure(
            stage="S02",
            blockers=(
                make_blocker(
                    BlockerCode.SSHT_TASK032_FLOW_STATE_INVALID,
                    stage="S02",
                    field_path="task032_flow_state",
                ),
            ),
        )
    if not _dict(raw_evidence):
        raise SchemaFailure(
            stage="S02",
            blockers=(
                make_blocker(
                    BlockerCode.SSHT_TASK032_REQUEST_EVIDENCE_INVALID,
                    stage="S02",
                    field_path="task032_request_evidence",
                ),
            ),
        )
    nested_blockers: list[Any] = []
    if not _closed(raw_flow, FLOW_STATE_EVIDENCE_FIELDS, "task032_flow_state", nested_blockers):
        nested_blockers.append(
            make_blocker(
                BlockerCode.SSHT_TASK032_FLOW_STATE_INVALID,
                stage="S02",
                field_path="task032_flow_state",
            )
        )
    if not _closed(
        raw_evidence, REQUEST_EVIDENCE_FIELDS, "task032_request_evidence", nested_blockers
    ):
        nested_blockers.append(
            make_blocker(
                BlockerCode.SSHT_TASK032_REQUEST_EVIDENCE_INVALID,
                stage="S02",
                field_path="task032_request_evidence",
            )
        )
    for name in ("task031_result", "property_snapshot", "mass_flow_authority"):
        if name in raw_evidence and not _dict(raw_evidence[name]):
            nested_blockers.append(
                make_blocker(
                    BlockerCode.SSHT_TASK032_REQUEST_EVIDENCE_INVALID,
                    stage="S02",
                    field_path=f"task032_request_evidence.{name}",
                )
            )
    evidence_refs = raw_evidence.get("evidence_refs")
    if not _strings(evidence_refs):
        nested_blockers.append(
            make_blocker(
                BlockerCode.SSHT_EVIDENCE_REFS_INVALID,
                stage="S02",
                field_path="task032_request_evidence.evidence_refs",
            )
        )
    if nested_blockers:
        raise SchemaFailure(stage="S02", blockers=tuple(nested_blockers))

    flow = Task032AcceptedFlowStateEvidence(
        **{field: raw_flow[field] for field in FLOW_STATE_EVIDENCE_FIELDS}
    )
    evidence = Task032AcceptedRequestEvidence(
        schema_version=raw_evidence["schema_version"],
        profile_id=raw_evidence["profile_id"],
        task031_result=dict(raw_evidence["task031_result"]),
        property_snapshot_hash=raw_evidence["property_snapshot_hash"],
        property_snapshot=dict(raw_evidence["property_snapshot"]),
        mass_flow_authority=dict(raw_evidence["mass_flow_authority"]),
        evidence_refs=tuple(sorted(raw_evidence["evidence_refs"])),
    )
    return ShellSideHeatTransferRequest(
        schema_version=raw_request["schema_version"],
        profile_id=raw_request["profile_id"],
        task032_flow_state=flow,
        task032_request_evidence=evidence,
        evidence_refs=tuple(sorted(raw_request["evidence_refs"])),
    )


__all__ = ["SchemaFailure", "parse_request"]
