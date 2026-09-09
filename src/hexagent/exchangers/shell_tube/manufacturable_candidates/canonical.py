"""TASK-168 identity projections on the repository canonical framework.

The shared TASK-021 canonical JSON helper remains the serialization primitive.
This module only defines TASK-168 domains and stable projections; it does not
reimplement any upstream engineering calculation or canonical algorithm.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import uuid
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.tube_layout.canonical import canonical_json
from hexagent.exchangers.shell_tube.tube_side.owned_enums import ReferencePlanePair

from .models import (
    CandidateRecord,
    CandidateSpec,
    DiscreteCandidateSetAuthority,
    ProvenanceGraph,
    Task168BatchResult,
    Task168EvaluationInputAuthority,
    Task168Request,
    Task168RequirementAuthority,
)

REQUEST_HASH_DOMAIN = "task168.manufacturable-candidates.request.v1"
CANDIDATE_SPACE_HASH_DOMAIN = "task168.manufacturable-candidates.space.v1"
CANDIDATE_HASH_DOMAIN = "task168.manufacturable-candidates.candidate.v1"
RESULT_HASH_DOMAIN = "task168.manufacturable-candidates.result.v1"
TYPED_BLOCKED_HASH_DOMAIN = "task168.manufacturable-candidates.typed-blocked.v1"
RAW_BLOCKED_HASH_DOMAIN = "task168.manufacturable-candidates.raw-boundary-blocked.v1"
PROVENANCE_HASH_DOMAIN = "task168.manufacturable-candidates.provenance.v1"

RESULT_ID_NAMESPACE = uuid.UUID("a1680000-0000-5000-8000-000000000168")
RESULT_ID_PREFIX = "task168-manufacturable-candidates-result-v1::"
TYPED_BLOCKED_ID_NAMESPACE = uuid.UUID("a1680000-0000-5000-8000-000000000169")
TYPED_BLOCKED_ID_PREFIX = "task168-manufacturable-candidates-typed-blocked-v1::"
RAW_BLOCKED_ID_NAMESPACE = uuid.UUID("a1680000-0000-5000-8000-00000000016a")
RAW_BLOCKED_ID_PREFIX = "task168-manufacturable-candidates-raw-blocked-v1::"
CANDIDATE_ID_NAMESPACE = uuid.UUID("a1680000-0000-5000-8000-00000000016b")
CANDIDATE_ID_PREFIX = "task168-manufacturable-candidate-v1::"
CANDIDATE_SPACE_ID_NAMESPACE = uuid.UUID("a1680000-0000-5000-8000-00000000016c")
CANDIDATE_SPACE_ID_PREFIX = "task168-manufacturable-candidate-space-v1::"


def _primitive(value: Any) -> Any:
    """Reduce trusted model fragments without admitting binary floats."""

    if value is None or type(value) is bool or type(value) is int or type(value) is str:
        return value
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("non-finite Decimal is not canonical")
        return str(value)
    if isinstance(value, enum.Enum):
        return _primitive(value.value)
    if isinstance(value, uuid.UUID):
        return str(value).lower()
    if type(value) is ReferencePlanePair:
        return {
            "kind": value.kind,
            "start": _primitive(value.start),
            "end": _primitive(value.end),
        }
    if isinstance(value, BaseModel):
        return _primitive(value.model_dump(mode="python"))
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _primitive(getattr(value, item.name)) for item in dataclasses.fields(value)
        }
    if isinstance(value, Mapping):
        pairs: list[tuple[bytes, str, Any]] = []
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("canonical mapping keys must be exact str")
            pairs.append((key.encode("utf-8", "strict"), key, _primitive(item)))
        return {key: item for _, key, item in sorted(pairs, key=lambda pair: pair[0])}
    if isinstance(value, (tuple, list)):
        return [_primitive(item) for item in value]
    raise ValueError(f"unsupported canonical value {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    """Use the repository TASK-021 canonical JSON framing boundary."""

    return canonical_json(_primitive(value)).encode("utf-8")


def sha256_domain_hex(domain: str, value: Any) -> str:
    return hashlib.sha256(canonical_bytes((domain, value))).hexdigest()


def _sorted_pairs(value: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            value,
            key=lambda pair: (
                pair[0].encode("utf-8", "strict"),
                pair[1].encode("utf-8", "strict"),
            ),
        )
    )


def discrete_authority_projection(value: DiscreteCandidateSetAuthority) -> dict[str, Any]:
    def value_key(item: Any) -> tuple[int, Any]:
        if type(item) is Decimal:
            return (0, item)
        if type(item) is int and type(item) is not bool:
            return (1, item)
        if isinstance(item, enum.Enum):
            raw = item.value
            return (2, raw.encode("utf-8") if type(raw) is str else str(raw).encode("utf-8"))
        if type(item) is str:
            return (3, item.encode("utf-8", "strict"))
        return (4, type(item).__qualname__.encode("utf-8"))

    return {
        "authority_id": value.authority_id,
        "authority_version": value.authority_version,
        "dimension_role": value.dimension_role,
        "source_class": value.source_class,
        "source_id": value.source_id,
        "source_revision": value.source_revision,
        "approval_status": value.approval_status,
        "values": tuple(sorted(value.values, key=value_key)),
        "evidence_refs": value.evidence_refs,
        "provenance_refs": value.provenance_refs,
    }


def discrete_authority_hash(value: DiscreteCandidateSetAuthority) -> str:
    return canonical_sha256(_primitive(discrete_authority_projection(value)))


def requirement_authority_projection(value: Task168RequirementAuthority) -> dict[str, Any]:
    return {
        "requirement_id": value.requirement_id,
        "authority_version": value.authority_version,
        "source_class": value.source_class,
        "source_id": value.source_id,
        "approval_status": value.approval_status,
        "allowed_construction_families": value.allowed_construction_families,
        "required_duty_w": value.required_duty_w,
        "max_tube_dp_pa": value.max_tube_dp_pa,
        "max_shell_dp_pa": value.max_shell_dp_pa,
        "evidence_refs": value.evidence_refs,
        "provenance_refs": value.provenance_refs,
    }


def requirement_authority_hash(value: Task168RequirementAuthority) -> str:
    return canonical_sha256(_primitive(requirement_authority_projection(value)))


def evaluation_input_authority_projection(
    value: Task168EvaluationInputAuthority,
) -> dict[str, Any]:
    """Project explicit base inputs, excluding the supplied replay hash."""

    return {
        field.name: getattr(value, field.name)
        for field in dataclasses.fields(value)
        if field.name != "canonical_hash"
    }


def evaluation_input_authority_hash(value: Task168EvaluationInputAuthority) -> str:
    return sha256_domain_hex(
        "task168.manufacturable-candidates.evaluation-input-authority.v1",
        evaluation_input_authority_projection(value),
    )


def _source_binding_projection(binding: Any) -> dict[str, Any]:
    return {
        "source_id": binding.source_id,
        "source_type": binding.source_type,
        "source_revision": binding.source_revision,
        "source_location": binding.source_location,
        "evidence_ref": binding.evidence_ref,
        "approved_by": binding.approved_by,
        "approved_at": binding.approved_at,
    }


def shell_record_hash(record: Any) -> str:
    payload = {
        "schema_version": record.schema_version,
        "geometry_id": record.geometry_id,
        "geometry_type": record.geometry_type,
        "profile_id": record.profile_id,
        "revision": record.revision,
        "approval_state": record.approval_state,
        "shell_inside_diameter_m": record.shell_inside_diameter_m,
        "source_class": record.source_class,
        "license_evidence": record.license_evidence,
        "source_binding": _source_binding_projection(record.source_binding),
        "permission_evidence_refs": record.permission_evidence_refs,
        "provenance_edge_ids": record.provenance_edge_ids,
        "evidence_refs": record.evidence_refs,
    }
    return canonical_sha256(_primitive(payload))


def shell_catalog_hash(catalog: Any) -> str:
    records = tuple(
        sorted(
            catalog.records, key=lambda item: (item.geometry_id, item.revision, item.record_hash)
        )
    )
    payload = {
        "schema_version": catalog.schema_version,
        "catalog_id": catalog.catalog_id,
        "catalog_version": catalog.catalog_version,
        "profile_id": catalog.profile_id,
        "authority": catalog.authority,
        "source_revision": catalog.source_revision,
        "effective_at": catalog.effective_at,
        "evidence_bundle_hash": catalog.evidence_bundle_hash,
        "record_hashes": tuple(item.record_hash for item in records),
    }
    return canonical_sha256(_primitive(payload))


def configuration_projection(configuration: Any) -> dict[str, Any]:
    binding = configuration.authority_binding
    return {
        "schema_version": configuration.schema_version,
        "configuration_id": configuration.configuration_id,
        "configuration_hash": configuration.configuration_hash,
        "equipment_family": configuration.equipment_family,
        "authority_mode": configuration.authority_mode,
        "construction_family": configuration.construction_family,
        "orientation": configuration.orientation,
        "shell_pass_count": configuration.shell_pass_count,
        "tube_pass_count": configuration.tube_pass_count,
        "case_revision_id": configuration.case_authority.revision_id,
        "case_payload_hash": configuration.case_authority.payload_hash,
        "binding_authority_mode": binding.authority_mode,
        "standard_system_id": binding.standard_system_id,
    }


def request_projection(request: Task168Request) -> dict[str, Any]:
    return {
        "schema_version": request.schema_version,
        "task168_version": request.task168_version,
        "source_definition_id": request.source_definition_id,
        "task020_configuration": configuration_projection(request.task020_configuration),
        "requirement_authority": requirement_authority_projection(request.requirement_authority),
        "shell_catalog": {
            "catalog_id": request.shell_geometry_catalog.catalog_id,
            "catalog_version": request.shell_geometry_catalog.catalog_version,
            "catalog_hash": request.shell_geometry_catalog.catalog_hash,
            "record_hashes": tuple(
                item.record_hash for item in request.shell_geometry_catalog.records
            ),
        },
        "discrete_authorities": tuple(
            discrete_authority_projection(item)
            for item in sorted(
                request.discrete_candidate_set_authorities,
                key=lambda item: item.dimension_role.value,
            )
        ),
        "evaluation_input_authority": evaluation_input_authority_projection(
            request.evaluation_input_authority
        ),
        "request_metadata": _sorted_pairs(request.request_metadata),
    }


def request_hash(request: Task168Request) -> str:
    return sha256_domain_hex(REQUEST_HASH_DOMAIN, request_projection(request))


def candidate_space_projection(
    request: Task168Request,
    authorities: tuple[DiscreteCandidateSetAuthority, ...],
) -> dict[str, Any]:
    return {
        "source_definition_id": request.source_definition_id,
        "configuration": configuration_projection(request.task020_configuration),
        "requirement_authority_hash": requirement_authority_hash(request.requirement_authority),
        "shell_catalog_id": request.shell_geometry_catalog.catalog_id,
        "shell_catalog_version": request.shell_geometry_catalog.catalog_version,
        "shell_catalog_hash": request.shell_geometry_catalog.catalog_hash,
        "discrete_authority_hashes": tuple(
            (item.dimension_role.value, discrete_authority_hash(item))
            for item in sorted(authorities, key=lambda item: item.dimension_role.value)
        ),
    }


def candidate_space_hash(
    request: Task168Request, authorities: tuple[DiscreteCandidateSetAuthority, ...]
) -> str:
    return sha256_domain_hex(
        CANDIDATE_SPACE_HASH_DOMAIN, candidate_space_projection(request, authorities)
    )


def candidate_space_id(space_hash: str) -> str:
    return str(uuid.uuid5(CANDIDATE_SPACE_ID_NAMESPACE, CANDIDATE_SPACE_ID_PREFIX + space_hash))


def candidate_projection(
    candidate: CandidateSpec, *, include_identity: bool = False
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "case_authority_id": candidate.case_authority_id,
        "construction_family": candidate.construction_family,
        "shell_geometry_id": candidate.shell_geometry_id,
        "shell_record_hash": candidate.shell_record_hash,
        "shell_inside_diameter_m": candidate.shell_inside_diameter_m,
        "tube_outer_diameter_m": candidate.tube_outer_diameter_m,
        "tube_wall_thickness_m": candidate.tube_wall_thickness_m,
        "tube_length_m": candidate.tube_length_m,
        "tube_pitch_m": candidate.tube_pitch_m,
        "tube_layout": candidate.tube_layout,
        "tube_pass_count": candidate.tube_pass_count,
        "baffle_type": candidate.baffle_type,
        "baffle_cut_fraction": candidate.baffle_cut_fraction,
        "baffle_spacing_m": candidate.baffle_spacing_m,
        "baffle_count": candidate.baffle_count,
        "authority_bindings": candidate.authority_bindings,
        # Keep the complete selected-member authority trace in candidate
        # identity.  The compact legacy bindings above remain for the
        # existing catalog-facing surface; they are not sufficient to prove
        # which source-bound member authorized a candidate dimension.
        "dimension_authority_bindings": candidate.dimension_authority_bindings,
    }
    if include_identity:
        payload["candidate_hash"] = candidate.candidate_hash
        payload["candidate_id"] = candidate.candidate_id
    return payload


def candidate_hash(candidate: CandidateSpec) -> str:
    return sha256_domain_hex(CANDIDATE_HASH_DOMAIN, candidate_projection(candidate))


def candidate_id(candidate_hash_value: str) -> str:
    return str(uuid.uuid5(CANDIDATE_ID_NAMESPACE, CANDIDATE_ID_PREFIX + candidate_hash_value))


def _blocker_projection(value: Any) -> dict[str, Any]:
    return {
        "code": value.code,
        "stage": value.stage,
        "field_path": value.field_path,
        "message": value.message,
        "evidence_refs": value.evidence_refs,
    }


def _warning_projection(value: Any) -> dict[str, Any]:
    return {"code": value.code, "evidence_refs": value.evidence_refs}


def candidate_record_projection(value: CandidateRecord) -> dict[str, Any]:
    return {
        "candidate_id": value.candidate_id,
        "candidate_hash": value.candidate_hash,
        "candidate": candidate_projection(value.candidate, include_identity=True),
        "disposition": value.disposition,
        "status": value.status,
        "stage": value.stage,
        "last_successful_stage": value.last_successful_stage,
        "configuration_evidence": value.configuration_evidence,
        "geometry_evidence": value.geometry_evidence,
        "tube_layout_evidence": value.tube_layout_evidence,
        "tube_side_evidence": value.tube_side_evidence,
        "bell_evidence": value.bell_evidence,
        "overall_u_ua_evidence": value.overall_u_ua_evidence,
        "thermal_closure_evidence": value.thermal_closure_evidence,
        "tube_dp_evidence": value.tube_dp_evidence,
        "shell_dp_evidence": value.shell_dp_evidence,
        "screening_evidence": value.screening_evidence,
        "constraint_evaluations": value.constraint_evaluations,
        "metrics": value.metrics,
        "warnings": tuple(_warning_projection(item) for item in value.warnings),
        "blockers": tuple(_blocker_projection(item) for item in value.blockers),
    }


def batch_preimage(value: Task168BatchResult) -> dict[str, Any]:
    return {
        "schema_version": value.schema_version,
        "task168_version": value.task168_version,
        "implementation_software_version": value.implementation_software_version,
        "source_definition_id": value.source_definition_id,
        "request_hash": value.request_hash,
        "candidate_space_id": value.candidate_space_id,
        "candidate_space_hash": value.candidate_space_hash,
        "total_theoretical_combinations": value.total_theoretical_combinations,
        "total_enumerated_candidates": value.total_enumerated_candidates,
        "pass_count": value.pass_count,
        "warn_count": value.warn_count,
        "blocked_count": value.blocked_count,
        "candidate_records": tuple(
            candidate_record_projection(item) for item in value.candidate_records
        ),
        "warnings": tuple(_warning_projection(item) for item in value.warnings),
        "blockers": tuple(_blocker_projection(item) for item in value.blockers),
        "applicability": value.applicability,
        "completeness": value.completeness,
        "provenance_semantic_inputs": value.provenance_semantic_inputs,
    }


def batch_result_hash(value: Task168BatchResult) -> str:
    return sha256_domain_hex(RESULT_HASH_DOMAIN, batch_preimage(value))


def result_id(result_hash_value: str) -> str:
    return str(uuid.uuid5(RESULT_ID_NAMESPACE, RESULT_ID_PREFIX + result_hash_value))


def typed_blocked_projection(value: Any) -> dict[str, Any]:
    return {
        "schema_version": value.schema_version,
        "task168_version": value.task168_version,
        "implementation_software_version": value.implementation_software_version,
        "request_hash": value.request_hash,
        "blockers": tuple(_blocker_projection(item) for item in value.blockers),
        "warnings": tuple(_warning_projection(item) for item in value.warnings),
    }


def typed_blocked_hash(value: Any) -> str:
    return sha256_domain_hex(TYPED_BLOCKED_HASH_DOMAIN, typed_blocked_projection(value))


def typed_blocked_id(hash_value: str) -> str:
    return str(uuid.uuid5(TYPED_BLOCKED_ID_NAMESPACE, TYPED_BLOCKED_ID_PREFIX + hash_value))


def raw_blocked_projection(value: Any) -> dict[str, Any]:
    return {
        "schema_version": value.schema_version,
        "task168_version": value.task168_version,
        "implementation_software_version": value.implementation_software_version,
        "raw_request_projection_hash": value.raw_request_projection_hash,
        "blockers": tuple(_blocker_projection(item) for item in value.blockers),
        "warnings": tuple(_warning_projection(item) for item in value.warnings),
    }


def raw_blocked_hash(value: Any) -> str:
    return sha256_domain_hex(RAW_BLOCKED_HASH_DOMAIN, raw_blocked_projection(value))


def raw_blocked_id(hash_value: str) -> str:
    return str(uuid.uuid5(RAW_BLOCKED_ID_NAMESPACE, RAW_BLOCKED_ID_PREFIX + hash_value))


def provenance_graph_hash(value: ProvenanceGraph) -> str:
    return sha256_domain_hex(
        PROVENANCE_HASH_DOMAIN,
        {
            "nodes": value.nodes,
            "edges": value.edges,
            "self_edge_count": value.self_edge_count,
            "cycle_count": value.cycle_count,
        },
    )


__all__ = [
    "CANDIDATE_HASH_DOMAIN",
    "CANDIDATE_ID_NAMESPACE",
    "CANDIDATE_SPACE_HASH_DOMAIN",
    "PROVENANCE_HASH_DOMAIN",
    "RAW_BLOCKED_HASH_DOMAIN",
    "RAW_BLOCKED_ID_NAMESPACE",
    "REQUEST_HASH_DOMAIN",
    "RESULT_HASH_DOMAIN",
    "RESULT_ID_NAMESPACE",
    "TYPED_BLOCKED_HASH_DOMAIN",
    "TYPED_BLOCKED_ID_NAMESPACE",
    "batch_preimage",
    "batch_result_hash",
    "candidate_hash",
    "candidate_id",
    "candidate_projection",
    "candidate_record_projection",
    "candidate_space_hash",
    "candidate_space_id",
    "canonical_bytes",
    "configuration_projection",
    "discrete_authority_hash",
    "discrete_authority_projection",
    "evaluation_input_authority_hash",
    "evaluation_input_authority_projection",
    "provenance_graph_hash",
    "raw_blocked_hash",
    "raw_blocked_id",
    "raw_blocked_projection",
    "request_hash",
    "request_projection",
    "requirement_authority_hash",
    "requirement_authority_projection",
    "result_id",
    "sha256_domain_hex",
    "shell_catalog_hash",
    "shell_record_hash",
    "typed_blocked_hash",
    "typed_blocked_id",
    "typed_blocked_projection",
]
