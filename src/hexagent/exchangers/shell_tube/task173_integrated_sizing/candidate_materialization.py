"""Candidate-native TASK171 topology materialization for TASK173 Sizing."""

from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Any

from hexagent.exchangers.shell_tube.manufacturable_candidates.models import CandidateSpec
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.engineering import (
    compute_outer_to_inner_area_ratio,
)
from hexagent.exchangers.shell_tube.segmented_thermal_state_topology.authority import (
    AUTHORITY_IDS,
    PROFILE_ID,
    REVIEW_RECEIPT_ID,
)
from hexagent.exchangers.shell_tube.segmented_thermal_state_topology.canonical import (
    decimal_text,
    number,
)
from hexagent.exchangers.shell_tube.segmented_thermal_state_topology.models import (
    Binding,
    Cell,
    Definition,
    Event,
    EventRole,
    Interval,
    Location,
    NativeIdentity,
    Path,
    Role,
    Side,
    State,
    Wall,
)
from hexagent.exchangers.shell_tube.segmented_thermal_state_topology.service import (
    validate_request as validate_task171,
)


def _binding(source_hash: str, authority_id: str, evidence: str) -> Binding:
    return Binding(
        authority_id=authority_id,
        revision="R2-CANDIDATE-NATIVE",
        evidence_refs=(evidence,),
        source_hash=source_hash,
    )


def materialize_candidate_task171(
    *,
    candidate: CandidateSpec,
    configuration: Any,
    layout: Any,
    bundle_geometry: Any,
    baffle_geometry: Any,
    task025_result: Any,
    task024_request: object,
    task025_request: object,
) -> Any:
    """Rebuild and validate a TASK171 Definition from candidate-native outputs."""
    span_start = number(baffle_geometry.axial_span.axial_start_coordinate_m)
    span_end = number(baffle_geometry.axial_span.axial_end_coordinate_m)
    boundaries = sorted(
        {span_start, span_end}
        | {number(item.center_coordinate_m) for item in baffle_geometry.baffle_planes}
    )
    if len(boundaries) < 4 or boundaries[0] != span_start or boundaries[-1] != span_end:
        raise ValueError("candidate TASK024 did not provide the reviewed native baffle boundaries")

    total_inside = Decimal(task025_result.internal_heat_transfer_surface_area_m2)
    ratio = compute_outer_to_inner_area_ratio(
        task025_result.hydraulic_diameter_m,
        Decimal(baffle_geometry.tube_outer_diameter_m),
    )
    total_outside = total_inside * ratio
    total_span = span_end - span_start
    intervals: list[Interval] = []
    inside_used = Decimal(0)
    outside_used = Decimal(0)
    interval_count = len(boundaries) - 1
    for index, (left, right) in enumerate(zip(boundaries, boundaries[1:], strict=False)):
        if right <= left:
            raise ValueError("candidate TASK024 physical intervals must have positive length")
        if index == interval_count - 1:
            inside_area = total_inside - inside_used
            outside_area = total_outside - outside_used
        else:
            with localcontext() as context:
                context.prec = 80
                fraction = Decimal(decimal_text(right - left)) / Decimal(decimal_text(total_span))
                inside_area = total_inside * fraction
                outside_area = total_outside * fraction
            inside_used += inside_area
            outside_used += outside_area
        intervals.append(
            Interval(
                physical_segment_id=f"urn:hxforge:task171:candidate:{candidate.candidate_hash}:support:{index}",
                start_m=decimal_text(left),
                end_m=decimal_text(right),
                inside_area_m2=str(inside_area),
                outside_area_m2=str(outside_area),
            )
        )

    active_positions = tuple(layout_position.position_id for layout_position in layout.positions)
    tube_path_id = f"urn:hxforge:task171:candidate:{candidate.candidate_hash}:path:TUBE"
    shell_path_id = f"urn:hxforge:task171:candidate:{candidate.candidate_hash}:path:SHELL"
    paths = (
        Path(
            flow_path_id=tube_path_id,
            stream_id=f"candidate:{candidate.candidate_hash}:TUBE-WATER",
            side=Side.TUBE,
            role=Role.HOT,
            inlet_face_id=f"candidate:{candidate.candidate_hash}:TUBE:face:0",
            outlet_face_id=f"candidate:{candidate.candidate_hash}:TUBE:face:{interval_count}",
            physical_inlet_m=decimal_text(span_start),
            physical_outlet_m=decimal_text(span_end),
            tube_position_ids=active_positions,
        ),
        Path(
            flow_path_id=shell_path_id,
            stream_id=f"candidate:{candidate.candidate_hash}:SHELL-WATER",
            side=Side.SHELL,
            role=Role.COLD,
            inlet_face_id=f"candidate:{candidate.candidate_hash}:SHELL:face:0",
            outlet_face_id=f"candidate:{candidate.candidate_hash}:SHELL:face:{interval_count}",
            physical_inlet_m=decimal_text(span_end),
            physical_outlet_m=decimal_text(span_start),
            tube_position_ids=(),
        ),
    )
    cells: list[Cell] = []
    tube_cell_by_segment: dict[str, str] = {}
    shell_cell_by_segment: dict[str, str] = {}
    tube_travel = Decimal(0)
    shell_travel = Decimal(0)
    ordered_shell_intervals = tuple(reversed(intervals))
    for side, path, ordered in (
        (Side.TUBE, paths[0], tuple(intervals)),
        (Side.SHELL, paths[1], ordered_shell_intervals),
    ):
        travel = Decimal(0)
        for index, interval in enumerate(ordered):
            low, high = Decimal(interval.start_m), Decimal(interval.end_m)
            upstream, downstream = (low, high) if side is Side.TUBE else (high, low)
            face_index = index
            cell_id = f"candidate:{candidate.candidate_hash}:{side.value}:cell:{index}"
            upstream_face = (
                path.inlet_face_id
                if face_index == 0
                else f"candidate:{candidate.candidate_hash}:{side.value}:face:{face_index}"
            )
            downstream_face = (
                path.outlet_face_id
                if face_index == interval_count - 1
                else f"candidate:{candidate.candidate_hash}:{side.value}:face:{face_index + 1}"
            )
            cells.append(
                Cell(
                    numerical_cell_id=cell_id,
                    physical_segment_id=interval.physical_segment_id,
                    flow_path_id=path.flow_path_id,
                    upstream_face_id=upstream_face,
                    downstream_face_id=downstream_face,
                    physical_upstream_m=decimal_text(number(str(upstream))),
                    physical_downstream_m=decimal_text(number(str(downstream))),
                    travel_start_m=str(travel),
                    travel_end_m=str(travel + abs(downstream - upstream)),
                )
            )
            travel += abs(downstream - upstream)
            if side is Side.TUBE:
                tube_cell_by_segment[interval.physical_segment_id] = cell_id
            else:
                shell_cell_by_segment[interval.physical_segment_id] = cell_id
        if side is Side.TUBE:
            tube_travel = travel
        else:
            shell_travel = travel
    expected_travel = Decimal(decimal_text(span_end - span_start))
    if tube_travel != expected_travel or shell_travel != expected_travel:
        raise ValueError("candidate TASK171 flow paths do not cover the native axial span")

    walls = tuple(
        Wall(
            wall_interface_id=f"candidate:{candidate.candidate_hash}:wall:{index}",
            physical_segment_id=interval.physical_segment_id,
            hot_cell_id=tube_cell_by_segment[interval.physical_segment_id],
            cold_cell_id=shell_cell_by_segment[interval.physical_segment_id],
            start_m=interval.start_m,
            end_m=interval.end_m,
            inside_area_m2=interval.inside_area_m2,
            outside_area_m2=interval.outside_area_m2,
        )
        for index, interval in enumerate(intervals)
    )

    events: list[Event] = []
    event_index = 0

    def append_event(
        role: EventRole, baffle_indices: tuple[int, ...], left: Any, right: Any
    ) -> None:
        nonlocal event_index
        start = number(str(left))
        end = number(str(right))
        incidences = tuple(
            interval.physical_segment_id
            for interval in intervals
            if number(interval.start_m) <= end and number(interval.end_m) >= start
        )
        event_id = f"candidate:{candidate.candidate_hash}:event:{event_index}:{role.value}"
        events.append(
            Event(
                physical_event_id=event_id,
                physical_compartment_id=f"candidate:{candidate.candidate_hash}:compartment:{event_index}",
                role=role,
                native_geometry_id=baffle_geometry.geometry_id,
                native_geometry_hash=baffle_geometry.geometry_hash,
                start_m=decimal_text(start),
                end_m=decimal_text(end),
                baffle_indices=baffle_indices,
                position_ids=active_positions if role is EventRole.TUBE_ROW_OR_CROSSED_ROW else (),
                multiplicity=1,
                physical_segment_ids=incidences,
                authority=_binding(
                    baffle_geometry.geometry_hash,
                    "V07-T173-SIZING-TASK171-CANDIDATE-BINDING-R1",
                    f"TASK024::{baffle_geometry.geometry_id}::{baffle_geometry.geometry_hash}",
                ),
                producer_status="UNRESOLVED",
                source_relation_role="STRUCTURAL_REFERENCE_ONLY",
            )
        )
        event_index += 1

    planes = tuple(
        sorted(baffle_geometry.baffle_planes, key=lambda item: number(item.center_coordinate_m))
    )
    for plane in planes:
        for role in (EventRole.BAFFLE, EventRole.WINDOW, EventRole.LEAKAGE_GEOMETRY):
            append_event(
                role, (plane.baffle_index,), plane.center_coordinate_m, plane.center_coordinate_m
            )
    for left, right in zip(planes, planes[1:], strict=False):
        append_event(
            EventRole.CENTRAL_CROSSFLOW,
            (left.baffle_index, right.baffle_index),
            left.center_coordinate_m,
            right.center_coordinate_m,
        )
    append_event(
        EventRole.INLET_END_ZONE, (), planes[-1].center_coordinate_m, decimal_text(span_end)
    )
    append_event(
        EventRole.OUTLET_END_ZONE, (), decimal_text(span_start), planes[0].center_coordinate_m
    )
    append_event(EventRole.BYPASS_GEOMETRY, (), decimal_text(span_start), decimal_text(span_end))
    append_event(
        EventRole.TUBE_ROW_OR_CROSSED_ROW,
        (),
        decimal_text(span_start),
        decimal_text(span_end),
    )
    states = tuple(
        State(
            state_id=f"candidate:{candidate.candidate_hash}:state:{cell.numerical_cell_id}",
            location=Location.CELL_MEAN,
            owner_id=cell.numerical_cell_id,
            flow_path_id=cell.flow_path_id,
            authority=_binding(
                baffle_geometry.geometry_hash,
                "V07-T173-SIZING-TASK171-CANDIDATE-BINDING-R1",
                f"TASK024::{baffle_geometry.geometry_id}::{baffle_geometry.geometry_hash}",
            ),
            producer_status="UNRESOLVED",
        )
        for cell in cells
    )
    definition = Definition(
        profile_id=PROFILE_ID,
        authority_ids=AUTHORITY_IDS,
        review_receipt_id=REVIEW_RECEIPT_ID,
        steady_state=True,
        single_phase=True,
        newtonian=True,
        flow_arrangement="COUNTERCURRENT",
        tube_path="STRAIGHT_THROUGH",
        mapping_authority=_binding(
            baffle_geometry.geometry_hash,
            "V07-T173-SIZING-TASK171-CANDIDATE-BINDING-R1",
            f"TASK024::{baffle_geometry.geometry_id}::{baffle_geometry.geometry_hash}",
        ),
        mesh_authority=_binding(
            baffle_geometry.geometry_hash,
            "V07-T173-SIZING-TASK171-CANDIDATE-BINDING-R1",
            f"TASK024::{baffle_geometry.geometry_id}::{baffle_geometry.geometry_hash}",
        ),
        intervals=tuple(intervals),
        paths=paths,
        cells=tuple(cells),
        walls=walls,
        events=tuple(events),
        states=states,
        provenance_edges=(),
    )
    native = NativeIdentity(
        configuration_id=configuration.configuration_id,
        configuration_hash=configuration.configuration_hash,
        layout_id=layout.layout_id,
        layout_hash=layout.layout_hash,
        bundle_id=bundle_geometry.geometry_id,
        bundle_hash=bundle_geometry.geometry_hash,
        baffle_id=baffle_geometry.geometry_id,
        baffle_hash=baffle_geometry.geometry_hash,
        area_result_id=task025_result.result_id,
        area_result_hash=task025_result.result_hash,
    )
    result = validate_task171(
        {
            "definition": definition,
            "baffle_request": task024_request,
            "area_request": task025_request,
            "native_identity": native,
            "bookkeeping": None,
        }
    )
    if result.status != "VALIDATED":
        raise ValueError(f"candidate TASK171 blocked: {result.blocker_code}:{result.blocker_field}")
    if result.topology_definition is None or result.native_identity != native:
        raise ValueError("candidate TASK171 returned incomplete native identity")
    return result
