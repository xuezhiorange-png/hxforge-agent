"""Production v0.7 Sizing orchestration over native candidate producers."""

from __future__ import annotations

import enum
import itertools
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Any, Final, Literal, cast

from pydantic import ValidationError

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.bell_delaware.models import (
    Task166BlockedResult,
    Task166Result,
)
from hexagent.exchangers.shell_tube.engineering_screening.models import Task167Result
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    candidate_space_hash as task168_candidate_space_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    discrete_authority_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    request_hash as task168_request_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    DIMENSION_ORDER,
    CandidateSpec,
    CandidateStage,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import (
    CandidateRatingRequest,
    CandidateRatingSuccessResult,
    Task173BlockedResult,
    candidate_rating_request_hash,
    candidate_rating_result_hash,
    validate_candidate_rating,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.candidate_materialization import (
    materialize_candidate_task171,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
    RANKING_POLICY_HASH,
    RANKING_POLICY_ID,
    SIZING_PACKAGE_HASH,
    SIZING_PACKAGE_ID,
    CandidateLedgerEntry,
    RankingTraceEntry,
    SizingRequirementAuthority,
    Task173SizingBlockedResult,
    Task173SizingOutcome,
    Task173SizingRequest,
    Task173SizingSuccessResult,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    BellEventRegionAllocation,
    CandidatePhysicalAbsenceProof,
    CandidateTask174Request,
    HydraulicComponentBinding,
    PhysicalEventBinding,
    PressurePropertyBinding,
    Task174BlockedResult,
    Task174NativeOutputs,
    Task174SuccessResult,
    recompute_task174_result_hash,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    validate_candidate_request as validate_task174_candidate,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029BlockedResult,
    Task029RawBoundaryBlockedResult,
    Task029SuccessResult,
)

_TASK171_AUTHORITY_HASH: Final = "bf014e7ca44eb5f9a3a2abec7c41f44b39a2590e7efaf31d77c70c892bcd1a9e"
_TASK172_AUTHORITY_HASH: Final = "fc7afcc9c51ed5920e3258b2a5683f1274d45df6c7d7e624be29614f97691483"
_TASK174_AUTHORITY_HASH: Final = "4d0f83b8ab1777ba6516dfc607c7accc814ef8a521d26c25c8cf0adc1b264023"
_TASK173_RATING_AUTHORITY_HASH: Final = (
    "a5536ba8e93dcf9a94f26a8c5274672494dd53b9391a9dad60553067967f49aa"
)
_JMU_TRANSFER_HASH: Final = "6d716f541c44aeaa6911efe5919ed2f1474f4af93a4c06fcb01a672c56d234cc"
_BELL_TRANSFER_HASH: Final = "28c89b6c58fef6050f9a0f5d33b80ce686f875a4ba9350e254d43ff699dccc58"
_PRESSURE_TRANSFER_HASH: Final = "7506d4217d27123cdec1a5d46813445a1a8b500ef24af39e10b7598ba163ce19"
_TASK174_TRANSFER_HASH: Final = "893a6c1644a940b27fbad85ef4d4fc402a7999971dc5e2ed3603fada0398b857"
_TUBE_COMPONENT_TYPES = (
    "ENTRANCE",
    "EXIT",
    "CHANNEL_HEAD",
    "NOZZLE",
    "CONTRACTION",
    "EXPANSION",
)
_BELL_ROLE: dict[
    str,
    tuple[Literal["ADDITIVE_PRESSURE_REGION", "CORRECTION_OR_GEOMETRY_SUPPORT"], str],
] = {
    "CENTRAL_CROSSFLOW": ("ADDITIVE_PRESSURE_REGION", "BELL_CENTRAL_CROSSFLOW_REGION"),
    "WINDOW": ("ADDITIVE_PRESSURE_REGION", "BELL_WINDOW_REGION"),
    "INLET_END_ZONE": ("ADDITIVE_PRESSURE_REGION", "BELL_INLET_END_ZONE"),
    "OUTLET_END_ZONE": ("ADDITIVE_PRESSURE_REGION", "BELL_OUTLET_END_ZONE"),
    "BAFFLE": ("CORRECTION_OR_GEOMETRY_SUPPORT", "BAFFLE_GEOMETRY_SUPPORT"),
    "LEAKAGE_GEOMETRY": (
        "CORRECTION_OR_GEOMETRY_SUPPORT",
        "RL_LEAKAGE_CORRECTION_SUPPORT",
    ),
    "BYPASS_GEOMETRY": ("CORRECTION_OR_GEOMETRY_SUPPORT", "RB_BYPASS_CORRECTION_SUPPORT"),
    "TUBE_ROW_OR_CROSSED_ROW": (
        "CORRECTION_OR_GEOMETRY_SUPPORT",
        "CROSS_FLOW_ROW_COUNT_SUPPORT",
    ),
}


def sizing_requirement_projection(authority: SizingRequirementAuthority) -> dict[str, object]:
    return authority.model_dump(mode="json", exclude={"canonical_hash"})


def recompute_sizing_requirement_hash(authority: SizingRequirementAuthority) -> str:
    return canonical_sha256(sizing_requirement_projection(authority))


def sizing_request_hash(request: Task173SizingRequest) -> str:
    task168_request = request.task168_candidate_request
    authorities = tuple(task168_request.discrete_candidate_set_authorities)
    return canonical_sha256(
        {
            "schema_version": request.schema_version,
            "authority_package_id": request.authority_package_id,
            "authority_package_hash": request.authority_package_hash,
            "sizing_scope_projection_hash": request.sizing_scope_projection_hash,
            "service_authority": request.service_authority.model_dump(mode="json"),
            "requirement_authority": request.requirement_authority.model_dump(mode="json"),
            "task168_request_hash": task168_request_hash(task168_request),
            "shell_catalog_id": task168_request.shell_geometry_catalog.catalog_id,
            "shell_catalog_hash": task168_request.shell_geometry_catalog.catalog_hash,
            "discrete_candidate_authority_hashes": [
                [item.dimension_role.value, discrete_authority_hash(item)]
                for item in sorted(authorities, key=lambda item: item.dimension_role.value)
            ],
            "candidate_space_hash": task168_candidate_space_hash(task168_request, authorities),
            "candidate_authority_hashes": {
                "task171": _TASK171_AUTHORITY_HASH,
                "task172": _TASK172_AUTHORITY_HASH,
                "task174": _TASK174_AUTHORITY_HASH,
                "candidate_rating": _TASK173_RATING_AUTHORITY_HASH,
                "jmu_transfer": _JMU_TRANSFER_HASH,
                "bell_event_transfer": _BELL_TRANSFER_HASH,
                "pressure_coupling_transfer": _PRESSURE_TRANSFER_HASH,
                "task174_project_transfer": _TASK174_TRANSFER_HASH,
            },
            "ranking_policy_id": request.ranking_policy_id,
            "ranking_policy_hash": request.ranking_policy_hash,
            "request_metadata": [list(item) for item in request.request_metadata],
        }
    )


def sizing_result_projection(result: Task173SizingSuccessResult) -> dict[str, object]:
    return result.model_dump(mode="json", exclude={"result_hash", "result_id"})


def recompute_sizing_result_hash(result: Task173SizingSuccessResult) -> str:
    if type(result) is not Task173SizingSuccessResult:
        raise TypeError("Sizing result hash replay requires exact success result")
    return canonical_sha256(sizing_result_projection(result))


def _blocked(
    code: str, stage: str, request_hash: str | None, details: tuple[str, ...]
) -> Task173SizingBlockedResult:
    projection = {
        "schema_version": "task173.sizing-blocked.v1",
        "status": "BLOCKED",
        "failure_stage": stage,
        "failure_code": code,
        "request_hash": request_hash,
        "blockers": list(details),
    }
    digest = canonical_sha256(projection)
    return Task173SizingBlockedResult(
        status="BLOCKED",
        failure_stage=stage,
        failure_code=code,
        request_hash=request_hash,
        blockers=details,
        result_hash=digest,
        result_id=f"urn:hxforge:task173-sizing:blocked:{digest}",
    )


def _primitive(value: object) -> object:
    if isinstance(value, enum.Enum):
        return value.value
    if type(value) is Decimal:
        return str(value)
    if type(value) in (str, int, bool) or value is None:
        return value
    return str(value)


def _selected_dimensions(candidate: CandidateSpec) -> tuple[tuple[str, str], ...]:
    return tuple(
        (name, str(_primitive(getattr(candidate, field))))
        for name, field in (
            ("CONSTRUCTION_FAMILY", "construction_family"),
            ("SHELL_GEOMETRY_ID", "shell_geometry_id"),
            ("TUBE_OUTER_DIAMETER", "tube_outer_diameter_m"),
            ("TUBE_WALL_THICKNESS", "tube_wall_thickness_m"),
            ("TUBE_LENGTH", "tube_length_m"),
            ("TUBE_PITCH", "tube_pitch_m"),
            ("TUBE_LAYOUT", "tube_layout"),
            ("TUBE_PASS_COUNT", "tube_pass_count"),
            ("BAFFLE_TYPE", "baffle_type"),
            ("BAFFLE_CUT", "baffle_cut_fraction"),
            ("BAFFLE_SPACING", "baffle_spacing_m"),
            ("BAFFLE_COUNT", "baffle_count"),
        )
    )


def _dimension_hashes(candidate: CandidateSpec) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (
                (item.dimension_role.value, item.canonical_hash)
                for item in candidate.dimension_authority_bindings
            ),
            key=lambda pair: pair[0].encode("utf-8"),
        )
    )


def _candidate_provenance(
    candidate: CandidateSpec, identities: tuple[tuple[str, str], ...], rating_hash: str | None
) -> tuple[str, tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]:
    nodes = [("requirement", "requirement-authority"), ("candidate", candidate.candidate_hash)]
    nodes.extend((name, digest) for name, digest in identities)
    if rating_hash is not None:
        nodes.append(("candidate-rating", rating_hash))
    edges = [("requirement", "candidate")]
    upstream_names = [
        name
        for name, _ in identities
        if name
        in {
            "TASK020",
            "TASK021",
            "TASK022",
            "TASK024",
            "TASK025",
            "TASK171",
            "TASK029",
            "TASK166",
            "TASK174",
        }
    ]
    previous = "candidate"
    for name in upstream_names:
        edges.append((previous, name))
        previous = name
    if rating_hash is not None:
        edges.append((previous, "candidate-rating"))
        edges.append(("candidate-rating", "constraints"))
    digest = canonical_sha256({"nodes": nodes, "edges": edges})
    return digest, tuple(nodes), tuple(edges)


def _candidate_request_for_task174(
    candidate: CandidateSpec, bundle: Any, topology: Any
) -> CandidateTask174Request:
    configuration = bundle.task020_configuration
    layout = bundle.task021_layout
    shell_geometry = bundle.task022_geometry
    baffle_geometry = bundle.task024_geometry
    area = bundle.task025_result
    bell: Task166Result = bundle.task166_result
    definition = topology.topology_definition
    if definition is None:
        raise ValueError("candidate TASK171 Definition missing")
    physical_events = tuple(
        PhysicalEventBinding(
            physical_event_id=item.physical_event_id,
            physical_compartment_id=item.physical_compartment_id,
            event_role=item.role.value,
            native_geometry_id=item.native_geometry_id,
            native_geometry_hash=item.native_geometry_hash,
            physical_segment_ids=item.physical_segment_ids,
            multiplicity=item.multiplicity,
        )
        for item in definition.events
    )
    allocations = tuple(
        BellEventRegionAllocation(
            physical_event_id=item.physical_event_id,
            allocation_role=_BELL_ROLE[item.event_role][0],
            bell_region_or_support_role=_BELL_ROLE[item.event_role][1],
            task166_result_hash=bell.result_hash,
            evidence_refs=(f"TASK171::{topology.result_hash}", f"TASK166::{bell.result_hash}"),
        )
        for item in physical_events
    )
    task028 = bundle.task028_result
    components = tuple(task028.component_results)
    modeled = tuple(
        HydraulicComponentBinding(
            component_type=item.component_type.value,
            component_id=item.component_id,
            task028_result_hash=task028.result_hash,
            component_authority_id="TASK028_NATIVE_COMPONENT_AUTHORITY",
            component_authority_hash=item.authority_hash,
            upstream_reference_plane=item.upstream_reference_plane,
            downstream_reference_plane=item.downstream_reference_plane,
            multiplicity=item.multiplicity,
        )
        for item in components
    )
    modeled_types = {item.component_type for item in modeled}
    exclusions = []
    for component_type in _TUBE_COMPONENT_TYPES:
        if component_type in modeled_types:
            continue
        proof_projection = {
            "candidate_id": candidate.candidate_id,
            "candidate_hash": candidate.candidate_hash,
            "task020_configuration_id": configuration.configuration_id,
            "task020_configuration_hash": configuration.configuration_hash,
            "task021_layout_id": layout.layout_id,
            "task021_layout_hash": layout.layout_hash,
            "task022_geometry_id": shell_geometry.geometry_id,
            "task022_geometry_hash": shell_geometry.geometry_hash,
            "task024_geometry_id": baffle_geometry.geometry_id,
            "task024_geometry_hash": baffle_geometry.geometry_hash,
            "component_type": component_type,
            "upstream_reference_plane": f"CANDIDATE_{component_type}_UPSTREAM_BOUNDARY",
            "downstream_reference_plane": f"CANDIDATE_{component_type}_DOWNSTREAM_BOUNDARY",
            "structural_reason": (
                "Candidate-native fixed-tubesheet single straight-through tube path "
                "contains no such separate modeled component."
            ),
            "exclusion_authority_id": "V07-T173-SIZING-TASK174-CANDIDATE-PROJECT-TRANSFER-R1",
            "exclusion_authority_hash": _TASK174_TRANSFER_HASH,
            "evidence_ref": ";".join(
                (
                    f"TASK020::{configuration.configuration_hash}",
                    f"TASK021::{layout.layout_hash}",
                    f"TASK022::{shell_geometry.geometry_hash}",
                    f"TASK024::{baffle_geometry.geometry_hash}",
                )
            ),
        }
        exclusions.append(
            CandidatePhysicalAbsenceProof(
                **proof_projection,
                canonical_hash=canonical_sha256(proof_projection),
            )
        )
    task026 = bundle.task026_result
    task032 = bundle.task032_flow_state
    return CandidateTask174Request(
        candidate_id=candidate.candidate_id,
        candidate_hash=candidate.candidate_hash,
        authority_package_id=SIZING_PACKAGE_ID,
        authority_package_hash=SIZING_PACKAGE_HASH,
        task174_candidate_authority_hash=_TASK174_AUTHORITY_HASH,
        task174_project_transfer_authority_hash=_TASK174_TRANSFER_HASH,
        bell_event_transfer_authority_hash=_BELL_TRANSFER_HASH,
        pressure_coupling_authority_hash=_PRESSURE_TRANSFER_HASH,
        task020_configuration_id=configuration.configuration_id,
        task020_configuration_hash=configuration.configuration_hash,
        task021_layout_id=layout.layout_id,
        task021_layout_hash=layout.layout_hash,
        task022_geometry_id=shell_geometry.geometry_id,
        task022_geometry_hash=shell_geometry.geometry_hash,
        task024_geometry_id=baffle_geometry.geometry_id,
        task024_geometry_hash=baffle_geometry.geometry_hash,
        task025_result_id=area.result_id,
        task025_result_hash=area.result_hash,
        task025_hydraulic_authority_hash=area.hydraulic_authority_hash,
        task171_topology_id=topology.topology_id,
        task171_result_hash=topology.result_hash,
        mesh_identity=topology.mesh_identity,
        physical_ownership_hash=topology.physical_ownership_hash,
        task166_result_id=bell.result_id,
        task166_result_hash=bell.result_hash,
        tube_component_bindings=modeled,
        physical_absence_proofs=tuple(exclusions),
        physical_events=physical_events,
        bell_event_region_allocations=allocations,
        pressure_property_bindings=(
            PressurePropertyBinding(
                location_id=f"{candidate.candidate_id}:TUBE:REFERENCE_PRESSURE",
                side="TUBE",
                pressure_pa=Decimal("101325"),
                property_snapshot_hash=task026.property_snapshot_hash,
            ),
            PressurePropertyBinding(
                location_id=f"{candidate.candidate_id}:SHELL:REFERENCE_PRESSURE",
                side="SHELL",
                pressure_pa=Decimal("101325"),
                property_snapshot_hash=task032.property_snapshot_hash,
            ),
        ),
    )


def _candidate_rating_request(
    candidate: CandidateSpec,
    candidate_space_hash: str,
    bundle: Any,
    topology: Any,
    task174: Task174SuccessResult,
    request_hash: str,
) -> CandidateRatingRequest:
    return CandidateRatingRequest(
        candidate_id=candidate.candidate_id,
        candidate_hash=candidate.candidate_hash,
        selected_dimensions=_selected_dimensions(candidate),
        dimension_authority_hashes=_dimension_hashes(candidate),
        candidate_space_hash=candidate_space_hash,
        task020_configuration_id=bundle.task020_configuration.configuration_id,
        task020_configuration_hash=bundle.task020_configuration.configuration_hash,
        task021_layout_id=bundle.task021_layout.layout_id,
        task021_layout_hash=bundle.task021_layout.layout_hash,
        task022_geometry_id=bundle.task022_geometry.geometry_id,
        task022_geometry_hash=bundle.task022_geometry.geometry_hash,
        task024_geometry_id=bundle.task024_geometry.geometry_id,
        task024_geometry_hash=bundle.task024_geometry.geometry_hash,
        task025_result=bundle.task025_result,
        task031_geometry=bundle.task031_geometry,
        task166_result=bundle.task166_result,
        task029_result=bundle.task029_result,
        task171_result=topology,
        task174_result=task174,
        request_metadata=(
            ("candidate_rating_scope", "V07_SIZING"),
            ("sizing_request_hash", request_hash),
        ),
    )


def _native_identities(
    bundle: Any, topology: Any | None, task174: Any | None
) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for name, value in (
        ("TASK020", bundle.task020_configuration),
        ("TASK021", bundle.task021_layout),
        ("TASK022", bundle.task022_geometry),
        ("TASK024", bundle.task024_geometry),
        ("TASK025", bundle.task025_result),
        ("TASK031", bundle.task031_geometry),
        ("TASK032", bundle.task032_flow_state),
        ("TASK029", bundle.task029_result),
        ("TASK166", bundle.task166_result),
    ):
        if value is None:
            continue
        digest = (
            getattr(value, "result_hash", None)
            or getattr(value, "geometry_hash", None)
            or getattr(value, "layout_hash", None)
            or getattr(value, "configuration_hash", None)
        )
        if type(digest) is str:
            pairs.append((name, digest))
    if topology is not None and topology.result_hash:
        pairs.append(("TASK171", topology.result_hash))
    if task174 is not None and getattr(task174, "result_hash", None):
        pairs.append(("TASK174", task174.result_hash))
    return tuple(pairs)


def _candidate_blocked_entry(
    candidate: CandidateSpec,
    stage: str,
    code: str,
    identities: tuple[tuple[str, str], ...] = (),
    rating_request_hash: str | None = None,
    rating_result_hash: str | None = None,
    rating_result_id: str | None = None,
) -> CandidateLedgerEntry:
    provenance_hash, _, _ = _candidate_provenance(candidate, identities, rating_result_hash)
    return CandidateLedgerEntry(
        candidate_id=candidate.candidate_id,
        candidate_hash=candidate.candidate_hash,
        selected_dimensions=_selected_dimensions(candidate),
        dimension_authority_hashes=_dimension_hashes(candidate),
        disposition="BLOCKED",
        stage=stage,
        status="BLOCKED",
        native_identities=identities,
        candidate_rating_request_hash=rating_request_hash,
        candidate_rating_result_hash=rating_result_hash,
        candidate_rating_result_id=rating_result_id,
        warnings=(),
        blockers=(code,),
        provenance_hash=provenance_hash,
    )


def _make_success_result(
    request: Task173SizingRequest,
    request_hash: str,
    space_hash: str,
    entries: list[CandidateLedgerEntry],
) -> Task173SizingSuccessResult:
    recommendable = [
        item
        for item in entries
        if item.disposition == "EVALUATED"
        and item.stage == CandidateStage.COMPLETE.value
        and item.status in ("PASS", "WARN")
        and not item.blockers
    ]
    ranking = sorted(
        recommendable,
        key=lambda item: (
            cast(Decimal, item.ranking_score),
            item.candidate_hash.encode("utf-8"),
        ),
    )
    trace_entries: list[RankingTraceEntry] = []
    for index, item in enumerate(ranking):
        with localcontext() as context:
            context.prec = 50
            context.rounding = ROUND_HALF_EVEN
            normalized_objective = cast(Decimal, item.shell_dp_pa) / Decimal(100)
        warn_penalty = Decimal(10) if item.status == "WARN" else Decimal(0)
        trace_entries.append(
            RankingTraceEntry(
                candidate_id=item.candidate_id,
                candidate_hash=item.candidate_hash,
                source_status=cast(Literal["PASS", "WARN"], item.status),
                objective_metric="shell_dp_pa",
                objective_value=cast(Decimal, item.shell_dp_pa),
                normalized_objective=normalized_objective,
                warn_penalty=warn_penalty,
                composite_score=cast(Decimal, item.ranking_score),
                rank=index + 1,
                reason_codes=(
                    "MINIMIZE_SHELL_DP_PA",
                    "WARN_PENALTY_APPLIED" if item.status == "WARN" else "NO_WARN_PENALTY",
                    "CANDIDATE_HASH_ASC_UTF8_TIE_BREAK",
                ),
            )
        )
    ranking_trace = tuple(trace_entries)
    ranked_top_n = ranking[:3]
    ranked_ids = tuple(item.candidate_id for item in ranked_top_n)
    recommended = ranked_ids[0] if ranked_ids else None
    alternatives = ranked_ids[1:]
    ranks = {item.candidate_id: index + 1 for index, item in enumerate(ranking)}
    entries = [item.model_copy(update={"rank": ranks.get(item.candidate_id)}) for item in entries]
    pass_count = sum(item.status == "PASS" for item in entries)
    warn_count = sum(item.status == "WARN" for item in entries)
    blocked_count = sum(item.status == "BLOCKED" for item in entries)
    excluded = tuple(
        (item.candidate_id, item.blockers) for item in entries if item.status == "BLOCKED"
    )
    graph_nodes: dict[str, str] = {
        "request": request_hash,
        "requirement": request.requirement_authority.canonical_hash,
        "candidate-space": space_hash,
        "ranking-policy": request.ranking_policy_hash,
        "sizing-result": "RESULT_PROJECTION_BOUND_BY_CANONICAL_RESULT_HASH",
    }
    graph_edges: set[tuple[str, str]] = {
        ("request", "candidate-space"),
        ("request", "requirement"),
        ("request", "ranking-policy"),
        ("candidate-space", "ranking-policy"),
    }
    for item in entries:
        candidate_node = f"candidate:{item.candidate_id}"
        graph_nodes[candidate_node] = item.candidate_hash
        graph_edges.add(("candidate-space", candidate_node))
        native_nodes: dict[str, str] = {}
        for name, digest in item.native_identities:
            key = f"candidate:{item.candidate_id}:{name}"
            native_nodes[name] = key
            graph_nodes[key] = digest
            graph_edges.add((candidate_node, key))
        dependencies = (
            ("TASK020", "TASK021"),
            ("TASK021", "TASK022"),
            ("TASK022", "TASK024"),
            ("TASK024", "TASK025"),
            ("TASK025", "TASK029"),
            ("TASK024", "TASK031"),
            ("TASK031", "TASK032"),
            ("TASK032", "TASK166"),
        )
        for source, target in dependencies:
            if source in native_nodes and target in native_nodes:
                graph_edges.add((native_nodes[source], native_nodes[target]))
        for source in ("TASK020", "TASK021", "TASK022", "TASK024", "TASK025"):
            if source in native_nodes and "TASK171" in native_nodes:
                graph_edges.add((native_nodes[source], native_nodes["TASK171"]))
        for source in ("TASK171", "TASK029", "TASK166"):
            if source in native_nodes and "TASK174" in native_nodes:
                graph_edges.add((native_nodes[source], native_nodes["TASK174"]))
        rating_node = f"candidate:{item.candidate_id}:TASK173_RATING"
        if item.candidate_rating_result_hash is not None:
            graph_nodes[rating_node] = item.candidate_rating_result_hash
            for source in ("TASK171", "TASK174"):
                if source in native_nodes:
                    graph_edges.add((native_nodes[source], rating_node))
        terminal_node = f"candidate:{item.candidate_id}:disposition"
        graph_nodes[terminal_node] = canonical_sha256(
            {
                "status": item.status,
                "stage": item.stage,
                "constraints": [
                    item.duty_constraint,
                    item.tube_dp_constraint,
                    item.shell_dp_constraint,
                ],
                "warnings": list(item.warnings),
                "blockers": list(item.blockers),
                "provenance_hash": item.provenance_hash,
            }
        )
        graph_edges.add(
            (rating_node if item.candidate_rating_result_hash else candidate_node, terminal_node)
        )
        if item.status in ("PASS", "WARN") and item.disposition == "EVALUATED":
            graph_edges.add((terminal_node, "ranking-policy"))
    selection_projection = {
        "ranked_candidate_ids": list(item.candidate_id for item in ranking),
        "recommended_candidate_id": recommended,
        "alternative_candidate_ids": list(alternatives),
        "excluded_candidate_ids": [item[0] for item in excluded],
    }
    graph_nodes["sizing-selection"] = canonical_sha256(selection_projection)
    graph_edges.add(("ranking-policy", "sizing-selection"))
    graph_edges.add(("sizing-selection", "sizing-result"))
    graph_nodes_tuple = tuple(sorted(graph_nodes.items(), key=lambda item: item[0].encode("utf-8")))
    graph_edges_tuple = tuple(
        sorted(graph_edges, key=lambda item: (item[0].encode("utf-8"), item[1].encode("utf-8")))
    )
    node_ids = set(graph_nodes)
    if any(
        source == target or source not in node_ids or target not in node_ids
        for source, target in graph_edges_tuple
    ):
        raise ValueError("Sizing provenance graph contains an invalid/self edge")
    adjacency: dict[str, list[str]] = {node: [] for node in node_ids}
    for source, target in graph_edges_tuple:
        adjacency[source].append(target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return False
        if node in visited:
            return True
        visiting.add(node)
        if not all(visit(child) for child in adjacency[node]):
            return False
        visiting.remove(node)
        visited.add(node)
        return True

    if not all(visit(node) for node in node_ids):
        raise ValueError("Sizing provenance graph contains a cycle")
    selection: Literal["RECOMMENDATION_AVAILABLE", "NO_RECOMMENDABLE_CANDIDATE"] = (
        "RECOMMENDATION_AVAILABLE" if recommended is not None else "NO_RECOMMENDABLE_CANDIDATE"
    )
    provisional = Task173SizingSuccessResult(
        status="VALIDATED",
        selection_status=selection,
        request_hash=request_hash,
        candidate_space_hash=space_hash,
        candidate_records=tuple(entries),
        candidate_count=len(entries),
        pass_count=pass_count,
        warn_count=warn_count,
        blocked_count=blocked_count,
        recommendable_count=len(recommendable),
        excluded_count=len(excluded),
        ranked_candidate_ids=ranked_ids,
        ranking_trace=ranking_trace,
        recommended_candidate_id=recommended,
        alternative_candidate_ids=alternatives,
        exclusion_reason_codes=excluded,
        ranking_policy_id=request.ranking_policy_id,
        ranking_policy_hash=request.ranking_policy_hash,
        provenance_nodes=graph_nodes_tuple,
        provenance_edges=graph_edges_tuple,
        provenance_cycle_count=0,
        provenance_self_edge_count=0,
        orphan_recommendation=False,
        stale_reference_binding=False,
        result_hash="0" * 64,
        result_id="pending",
    )
    digest = recompute_sizing_result_hash(provisional)
    return provisional.model_copy(
        update={"result_hash": digest, "result_id": f"urn:hxforge:task173-sizing:{digest}"}
    )


def validate_sizing_request(
    raw_request: Task173SizingRequest | dict[str, Any],
) -> Task173SizingOutcome:
    """Enumerate and fully evaluate all authorized Sizing candidates."""
    request: Task173SizingRequest | None = None
    digest: str | None = None
    try:
        if type(raw_request) is Task173SizingRequest:
            request = raw_request
        elif type(raw_request) is dict:
            request = Task173SizingRequest.model_validate(raw_request, strict=True)
        else:
            return _blocked(
                "INVALID_SIZING_REQUEST_TYPE",
                "REQUEST",
                None,
                ("strict task173.sizing-request.v1 required",),
            )
        digest = sizing_request_hash(request)
        if (
            request.authority_package_id != SIZING_PACKAGE_ID
            or request.authority_package_hash != SIZING_PACKAGE_HASH
        ):
            return _blocked(
                "SIZING_AUTHORITY_PACKAGE_MISMATCH",
                "AUTHORITY",
                digest,
                ("reviewed R2 package binding required",),
            )
        if (
            request.ranking_policy_id != RANKING_POLICY_ID
            or request.ranking_policy_hash != RANKING_POLICY_HASH
        ):
            return _blocked(
                "SIZING_RANKING_POLICY_MISMATCH",
                "AUTHORITY",
                digest,
                ("reviewed v0.7 ranking policy required",),
            )
        task168_request = request.task168_candidate_request
        if request.requirement_authority.allowed_construction_families != ("FIXED_TUBESHEET",):
            return _blocked(
                "SIZING_REQUIREMENT_SCOPE_MISMATCH",
                "AUTHORITY",
                digest,
                ("allowed construction family must be exactly FIXED_TUBESHEET",),
            )
        actual_discrete_authorities = tuple(
            sorted(
                (
                    (item.authority_id, discrete_authority_hash(item))
                    for item in task168_request.discrete_candidate_set_authorities
                ),
                key=lambda item: item[0].encode("utf-8"),
            )
        )
        required_discrete_authorities = tuple(
            sorted(
                request.requirement_authority.discrete_candidate_authority_ids_and_hashes,
                key=lambda item: item[0].encode("utf-8"),
            )
        )
        if actual_discrete_authorities != required_discrete_authorities:
            return _blocked(
                "SIZING_DISCRETE_AUTHORITY_BINDING_MISMATCH",
                "AUTHORITY",
                digest,
                ("requirement and candidate-space discrete authority identities differ",),
            )
        if task168_request.task020_configuration.component_tokens.shell != "E":
            return _blocked(
                "UNSUPPORTED_SIZING_SHELL_FAMILY",
                "CANDIDATE_AUTHORITY",
                digest,
                ("only E shell is authorized",),
            )
        if task168_request.task020_configuration.shell_pass_count != 1:
            return _blocked(
                "UNSUPPORTED_SIZING_SHELL_PASS_COUNT",
                "CANDIDATE_AUTHORITY",
                digest,
                ("only one shell pass is authorized",),
            )
        if len(task168_request.shell_geometry_catalog.records) > 32 or any(
            len(item.values) > 32 for item in task168_request.discrete_candidate_set_authorities
        ):
            return _blocked(
                "SIZING_RESOURCE_BOUND_EXCEEDED",
                "CANDIDATE_AUTHORITY",
                digest,
                ("MAX_VALUES_PER_ROLE=32; no truncation",),
            )
        typed_failures = task168._validate_typed_request(task168_request)
        if typed_failures:
            return _blocked(
                "TASK168_CANDIDATE_SPACE_AUTHORITY_INVALID",
                "CANDIDATE_AUTHORITY",
                digest,
                tuple(item.code for item in typed_failures),
            )
        discrete = tuple(task168_request.discrete_candidate_set_authorities)
        authorities = task168._authority_map(task168_request)
        dimensions = tuple(
            task168._sort_values(authorities[role].values)
            for role in DIMENSION_ORDER
            if role != "SHELL_GEOMETRY_ID"
        )
        if len(task168_request.shell_geometry_catalog.records) > 32:
            return _blocked(
                "SIZING_RESOURCE_BOUND_EXCEEDED",
                "CANDIDATE_AUTHORITY",
                digest,
                ("MAX_VALUES_PER_ROLE=32 for SHELL_GEOMETRY_ID",),
            )
        candidate_count = len(task168_request.shell_geometry_catalog.records)
        for values in dimensions:
            if len(values) > 32:
                return _blocked(
                    "SIZING_RESOURCE_BOUND_EXCEEDED",
                    "CANDIDATE_AUTHORITY",
                    digest,
                    ("MAX_VALUES_PER_ROLE=32",),
                )
            candidate_count *= len(values)
        if candidate_count > 4096:
            return _blocked(
                "SIZING_RESOURCE_BOUND_EXCEEDED",
                "CANDIDATE_AUTHORITY",
                digest,
                ("MAX_CARTESIAN_COMBINATIONS=4096; no truncation",),
            )
        space_hash = task168_candidate_space_hash(task168_request, discrete)
        entries: list[CandidateLedgerEntry] = []
        for combination in itertools.product(
            task168_request.shell_geometry_catalog.records, *dimensions
        ):
            shell_record = combination[0]
            candidate = task168._candidate(
                task168_request, authorities, shell_record, tuple(combination[1:])
            )
            unsupported = []
            if candidate.construction_family.value != "FIXED_TUBESHEET":
                unsupported.append("UNSUPPORTED_V07_SIZING_TOPOLOGY:CONSTRUCTION_FAMILY")
            if candidate.tube_pass_count != 1:
                unsupported.append("UNSUPPORTED_V07_SIZING_TOPOLOGY:TUBE_PASS_COUNT")
            if task168_request.task020_configuration.shell_pass_count != 1:
                unsupported.append("UNSUPPORTED_V07_SIZING_TOPOLOGY:SHELL_PASS_COUNT")
            if unsupported:
                entries.append(
                    _candidate_blocked_entry(candidate, "CANDIDATE_AUTHORITY", unsupported[0])
                )
                continue
            structural = task168._structural_blockers(candidate)
            if structural:
                entries.append(
                    _candidate_blocked_entry(
                        candidate, structural[0].stage.value, structural[0].code
                    )
                )
                continue
            bundle, stage_failure, last_success = task168._execute_candidate_chain(
                task168_request,
                candidate,
                shell_record,
                include_legacy_task162=False,
                include_legacy_task168_rating_dependencies=False,
                preserve_baffle_orientation_sequence=True,
            )
            identities = _native_identities(bundle, None, None)
            if stage_failure is not None:
                entries.append(
                    _candidate_blocked_entry(
                        candidate, stage_failure.stage.value, stage_failure.code, identities
                    )
                )
                continue
            try:
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
            except Exception as exc:
                entries.append(
                    _candidate_blocked_entry(
                        candidate,
                        "TASK171",
                        "BLOCKED_CANDIDATE_TASK171_MATERIALIZATION:" + type(exc).__name__,
                        identities,
                    )
                )
                continue
            identities = _native_identities(bundle, topology, None)
            try:
                task174_request = _candidate_request_for_task174(candidate, bundle, topology)
                task174 = validate_task174_candidate(
                    task174_request,
                    Task174NativeOutputs(
                        task029=cast(
                            Task029SuccessResult
                            | Task029BlockedResult
                            | Task029RawBoundaryBlockedResult
                            | None,
                            bundle.task029_result,
                        ),
                        task034=None,
                        task166=cast(
                            Task166Result | Task166BlockedResult | None,
                            bundle.task166_result,
                        ),
                    ),
                )
            except Exception as exc:
                entries.append(
                    _candidate_blocked_entry(
                        candidate,
                        "TASK174",
                        "BLOCKED_CANDIDATE_TASK174_REQUEST:" + type(exc).__name__,
                        identities,
                    )
                )
                continue
            if type(task174) is not Task174SuccessResult:
                blocked_task174 = cast(Task174BlockedResult, task174)
                blocker_codes = tuple(item.code for item in blocked_task174.blockers)
                entries.append(
                    _candidate_blocked_entry(
                        candidate,
                        "TASK174",
                        ";".join(blocker_codes) or "BLOCKED_TASK174",
                        identities,
                    )
                )
                continue
            if task174.result_hash != recompute_task174_result_hash(task174):
                entries.append(
                    _candidate_blocked_entry(
                        candidate, "TASK174", "BLOCKED_TASK174_IDENTITY_REPLAY", identities
                    )
                )
                continue
            identities = _native_identities(bundle, topology, task174)
            rating_request = _candidate_rating_request(
                candidate, space_hash, bundle, topology, task174, digest
            )
            rating_request_hash = candidate_rating_request_hash(rating_request)
            rating_outcome = validate_candidate_rating(rating_request)
            if type(rating_outcome) is not CandidateRatingSuccessResult:
                if rating_outcome.request_hash != rating_request_hash:
                    entries.append(
                        _candidate_blocked_entry(
                            candidate,
                            "TASK173_CANDIDATE_RATING",
                            "BLOCKED_CANDIDATE_RATING_REQUEST_IDENTITY_REPLAY",
                            identities,
                            rating_request_hash,
                            rating_outcome.result_hash,
                            rating_outcome.result_id,
                        )
                    )
                    continue
                entries.append(
                    _candidate_blocked_entry(
                        candidate,
                        "TASK173_CANDIDATE_RATING",
                        cast(Task173BlockedResult, rating_outcome).failure_code,
                        identities,
                        rating_request_hash,
                        rating_outcome.result_hash,
                        rating_outcome.result_id,
                    )
                )
                continue
            if (
                rating_outcome.candidate_id != candidate.candidate_id
                or rating_outcome.candidate_hash != candidate.candidate_hash
                or rating_outcome.authority_package_id != SIZING_PACKAGE_ID
                or rating_outcome.authority_package_hash != SIZING_PACKAGE_HASH
                or rating_outcome.request_hash != rating_request_hash
                or rating_outcome.result_hash != candidate_rating_result_hash(rating_outcome)
                or rating_outcome.result_id != f"urn:hxforge:task173:{rating_outcome.result_hash}"
            ):
                entries.append(
                    _candidate_blocked_entry(
                        candidate,
                        "TASK173_CANDIDATE_RATING",
                        "BLOCKED_CANDIDATE_RATING_IDENTITY_REPLAY",
                        identities,
                        rating_request_hash,
                    )
                )
                continue
            rated_duty = rating_outcome.total_duty_w
            tube_dp = task174.modeled_total_tube_side_pressure_drop_pa
            shell_dp = task174.bell_total_shell_pressure_drop_pa
            duty_pass = rated_duty >= request.requirement_authority.required_duty_w
            tube_pass = tube_dp <= request.requirement_authority.max_tube_dp_pa
            shell_pass = shell_dp <= request.requirement_authority.max_shell_dp_pa
            blockers = tuple(
                code
                for code, passed in (
                    ("DUTY_BELOW_REQUIRED", duty_pass),
                    ("TUBE_DP_ABOVE_MAXIMUM", tube_pass),
                    ("SHELL_DP_ABOVE_MAXIMUM", shell_pass),
                )
                if not passed
            )
            warnings = tuple(
                sorted(
                    set(
                        tuple(cast(Task167Result, bundle.task167_result).warnings)
                        + (
                            ("FIV_NUMERIC_LIMIT_AUTHORITY_MISSING",)
                            if task174.fiv_numeric_limit_authority_missing
                            else ()
                        )
                    ),
                    key=lambda item: item.encode("utf-8"),
                )
            )
            status: Literal["PASS", "WARN", "BLOCKED"] = (
                "BLOCKED" if blockers else "WARN" if warnings else "PASS"
            )
            score: Decimal | None = None
            if status in ("PASS", "WARN"):
                with localcontext() as context:
                    context.prec = 50
                    context.rounding = ROUND_HALF_EVEN
                    score = shell_dp / Decimal(100)
                    if status == "WARN":
                        score += Decimal(10)
            provenance_hash, _, _ = _candidate_provenance(
                candidate, identities, rating_outcome.result_hash
            )
            entries.append(
                CandidateLedgerEntry(
                    candidate_id=candidate.candidate_id,
                    candidate_hash=candidate.candidate_hash,
                    selected_dimensions=_selected_dimensions(candidate),
                    dimension_authority_hashes=_dimension_hashes(candidate),
                    disposition="BLOCKED" if blockers else "EVALUATED",
                    stage="CONSTRAINT_EVALUATION" if blockers else CandidateStage.COMPLETE.value,
                    status=status,
                    native_identities=identities,
                    candidate_rating_request_hash=rating_request_hash,
                    candidate_rating_result_hash=rating_outcome.result_hash,
                    candidate_rating_result_id=rating_outcome.result_id,
                    accepted_mesh_identity=rating_outcome.accepted_mesh_result_hash,
                    accepted_subdivisions_per_interval=rating_outcome.accepted_subdivisions_per_interval,
                    headroom_subdivisions_per_interval=rating_outcome.headroom_subdivisions_per_interval,
                    rated_duty_w=rated_duty,
                    tube_dp_pa=tube_dp,
                    shell_dp_pa=shell_dp,
                    duty_constraint="PASS" if duty_pass else "BLOCKED",
                    tube_dp_constraint="PASS" if tube_pass else "BLOCKED",
                    shell_dp_constraint="PASS" if shell_pass else "BLOCKED",
                    ranking_score=score,
                    warnings=warnings,
                    blockers=blockers,
                    provenance_hash=provenance_hash,
                )
            )
        result = _make_success_result(request, digest, space_hash, entries)
        if (
            result.result_hash != recompute_sizing_result_hash(result)
            or result.result_id != f"urn:hxforge:task173-sizing:{result.result_hash}"
        ):
            return _blocked(
                "BLOCKED_SIZING_RESULT_IDENTITY_REPLAY",
                "IDENTITY",
                digest,
                ("canonical sizing result hash or ID does not replay",),
            )
        return result
    except ValidationError:
        return _blocked(
            "INVALID_SIZING_REQUEST_SCHEMA",
            "REQUEST",
            digest,
            ("strict task173.sizing-request.v1 boundary rejected input",),
        )
    except Exception as exc:
        return _blocked(
            "BLOCKED_SIZING_RUNTIME_FAILURE", "RUNTIME", digest, (type(exc).__name__, str(exc))
        )


__all__ = [
    "recompute_sizing_requirement_hash",
    "recompute_sizing_result_hash",
    "sizing_request_hash",
    "validate_sizing_request",
]
