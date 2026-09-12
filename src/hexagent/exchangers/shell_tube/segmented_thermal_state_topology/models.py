"""Explicit immutable structural inputs; no implicit mesh or producer defaults."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class Side(StrEnum):
    TUBE = "TUBE"
    SHELL = "SHELL"


class Role(StrEnum):
    HOT = "HOT"
    COLD = "COLD"


class Location(StrEnum):
    UPSTREAM_FACE = "UPSTREAM_FACE"
    DOWNSTREAM_FACE = "DOWNSTREAM_FACE"
    CELL_MEAN = "CELL_MEAN"
    COMPARTMENT_MIXED = "COMPARTMENT_MIXED"
    WALL_INNER_SURFACE = "WALL_INNER_SURFACE"
    WALL_OUTER_SURFACE = "WALL_OUTER_SURFACE"


class EventRole(StrEnum):
    CENTRAL_CROSSFLOW = "CENTRAL_CROSSFLOW"
    WINDOW = "WINDOW"
    INLET_END_ZONE = "INLET_END_ZONE"
    OUTLET_END_ZONE = "OUTLET_END_ZONE"
    BAFFLE = "BAFFLE"
    LEAKAGE_GEOMETRY = "LEAKAGE_GEOMETRY"
    BYPASS_GEOMETRY = "BYPASS_GEOMETRY"
    TUBE_ROW_OR_CROSSED_ROW = "TUBE_ROW_OR_CROSSED_ROW"


class Binding(Model):
    authority_id: str
    revision: str
    evidence_refs: tuple[str, ...]
    source_hash: str


class Interval(Model):
    physical_segment_id: str
    start_m: str
    end_m: str
    inside_area_m2: str
    outside_area_m2: str


class Path(Model):
    flow_path_id: str
    stream_id: str
    side: Side
    role: Role
    inlet_face_id: str
    outlet_face_id: str
    physical_inlet_m: str
    physical_outlet_m: str
    tube_position_ids: tuple[str, ...]


class Cell(Model):
    numerical_cell_id: str
    physical_segment_id: str
    flow_path_id: str
    upstream_face_id: str
    downstream_face_id: str
    physical_upstream_m: str
    physical_downstream_m: str
    travel_start_m: str
    travel_end_m: str


class Wall(Model):
    wall_interface_id: str
    physical_segment_id: str
    hot_cell_id: str
    cold_cell_id: str
    start_m: str
    end_m: str
    inside_area_m2: str
    outside_area_m2: str


class Event(Model):
    physical_event_id: str
    physical_compartment_id: str
    role: EventRole
    native_geometry_id: str
    native_geometry_hash: str
    start_m: str
    end_m: str
    # Explicit native selectors; interpreted against geometry, never mesh.
    baffle_indices: tuple[int, ...]
    position_ids: tuple[str, ...]
    multiplicity: int
    physical_segment_ids: tuple[str, ...]
    authority: Binding
    producer_status: Literal["UNRESOLVED"]
    source_relation_role: Literal["STRUCTURAL_REFERENCE_ONLY"]


class State(Model):
    state_id: str
    location: Location
    owner_id: str
    flow_path_id: str
    authority: Binding
    producer_status: Literal["UNRESOLVED"]


class Edge(Model):
    source: str
    target: str


class Definition(Model):
    profile_id: str
    authority_ids: tuple[str, ...]
    review_receipt_id: str
    steady_state: bool
    single_phase: bool
    newtonian: bool
    flow_arrangement: str
    tube_path: str
    mapping_authority: Binding
    mesh_authority: Binding
    intervals: tuple[Interval, ...]
    paths: tuple[Path, ...]
    cells: tuple[Cell, ...]
    walls: tuple[Wall, ...]
    events: tuple[Event, ...]
    states: tuple[State, ...]
    provenance_edges: tuple[Edge, ...]


class NativeIdentity(Model):
    configuration_id: str
    configuration_hash: str
    layout_id: str
    layout_hash: str
    bundle_id: str
    bundle_hash: str
    baffle_id: str
    baffle_hash: str
    area_result_id: str
    area_result_hash: str


class FaceObservation(Model):
    face_id: str
    enthalpy_j_kg: str
    mass_flow_kg_s: str
    authority: Binding


class HeatObservation(Model):
    wall_interface_id: str
    heat_rate_w: str
    authority: Binding


class Bookkeeping(Model):
    faces: tuple[FaceObservation, ...]
    heat_events: tuple[HeatObservation, ...]


class Residual(Model):
    cell_id: str
    energy_residual_w: str
    mass_residual_kg_s: str


class Result(Model):
    topology_definition: Definition | None
    bookkeeping_observations: Bookkeeping | None
    warnings: tuple[str, ...]
    status: Literal["VALIDATED", "BLOCKED"]
    blocker_code: str | None
    blocker_field: str | None
    topology_id: str | None
    result_hash: str | None
    mesh_identity: str | None
    physical_ownership_hash: str | None
    native_identity: NativeIdentity | None
    provenance_edges: tuple[Edge, ...]
    residuals: tuple[Residual, ...]
    global_energy_residual_w: str | None
    bookkeeping_status: Literal["NOT_REQUESTED", "COMPUTED_NOT_ASSESSED", "UNAVAILABLE"]
    # No convergence flag or recommendation is present.
