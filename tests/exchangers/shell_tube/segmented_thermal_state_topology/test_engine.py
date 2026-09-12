"""Explicit synthetic mesh fixtures; NOT_PRODUCTION_NUMERICAL_AUTHORITY.

Native geometry/area validators run for real. No rated outputs/Golden oracle.
"""

from dataclasses import replace
from decimal import localcontext
from fractions import Fraction

import pytest

from hexagent.exchangers.shell_tube import validate_request as config_validate
from hexagent.exchangers.shell_tube.baffle_geometry import validate_request as baffle_validate
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.engineering import (
    compute_outer_to_inner_area_ratio,
)
from hexagent.exchangers.shell_tube.segmented_thermal_state_topology import validate_request
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
    Bookkeeping,
    Cell,
    Definition,
    Edge,
    Event,
    EventRole,
    FaceObservation,
    HeatObservation,
    Interval,
    Location,
    NativeIdentity,
    Path,
    Role,
    Side,
    State,
    Wall,
)
from hexagent.exchangers.shell_tube.tube_layout import validate_request as layout_validate
from hexagent.exchangers.shell_tube.tube_side.scheduler import evaluate_task025
from hexagent.release_demo.v0_4 import task039
from tests.exchangers.shell_tube.baffle_geometry import _builders as b
from tests.exchangers.shell_tube.baffle_geometry.test_validation import _raw_from_request


def authority(source_hash="a" * 64):
    return Binding(
        authority_id="TEST_FIXTURE_ONLY",
        revision="1",
        evidence_refs=("NOT_PRODUCTION_NUMERICAL_AUTHORITY",),
        source_hash=source_hash,
    )


def fixture(*, split=False, hot_tube=True, invalid_physical_cuts=None):
    c = config_validate(task039._build_task020_request()).configuration
    layout = layout_validate(
        task039._build_task021_request(c, pattern_family="TRIANGULAR"),
        software_version="TASK171_TEST",
        git_commit="TEST_FIXTURE_ONLY",
    ).layout
    bundle = b.make_shell_bundle_geometry(c, layout)
    br = _raw_from_request(
        replace(
            b.make_geometry_request(position_count=1, spacing_value_m="0.97"),
            configuration=c,
            tube_layout=layout,
            shell_bundle_geometry=bundle,
        )
    )
    g = baffle_validate(br).geometry
    assert g is not None
    ar = task039._build_task025_request(layout, c)
    area = evaluate_task025(ar)
    ni = NativeIdentity(
        configuration_id=c.configuration_id,
        configuration_hash=c.configuration_hash,
        layout_id=layout.layout_id,
        layout_hash=layout.layout_hash,
        bundle_id=bundle.geometry_id,
        bundle_hash=bundle.geometry_hash,
        baffle_id=g.geometry_id,
        baffle_hash=g.geometry_hash,
        area_result_id=area.result_id,
        area_result_hash=area.result_hash,
    )
    inside = number(str(area.internal_heat_transfer_surface_area_m2))
    outside = inside * number(
        str(
            compute_outer_to_inner_area_ratio(
                area.hydraulic_diameter_m, __import__("decimal").Decimal(g.tube_outer_diameter_m)
            )
        )
    )
    cuts = sorted(
        {
            number(g.axial_span.axial_start_coordinate_m),
            *(number(p.center_coordinate_m) for p in g.baffle_planes),
            number(g.axial_span.axial_end_coordinate_m),
        }
    )
    if invalid_physical_cuts is not None:
        # Negative fixtures only: never an admitted physical/numerical policy.
        cuts = invalid_physical_cuts
    span = cuts[-1] - cuts[0]
    intervals = tuple(
        Interval(
            physical_segment_id=f"i{k}",
            start_m=decimal_text(a),
            end_m=decimal_text(z),
            inside_area_m2=decimal_text(inside * (z - a) / span),
            outside_area_m2=decimal_text(outside * (z - a) / span),
        )
        for k, (a, z) in enumerate(zip(cuts, cuts[1:], strict=False))
    )
    paths = tuple(
        Path(
            flow_path_id=side.value,
            stream_id=side.value + "-fluid",
            side=side,
            role=Role.HOT if (side == Side.TUBE) == hot_tube else Role.COLD,
            inlet_face_id=side.value + "f0",
            outlet_face_id=side.value + "out",
            physical_inlet_m="0" if side == Side.TUBE else "4.85",
            physical_outlet_m="4.85" if side == Side.TUBE else "0",
            tube_position_ids=tuple(p.position_id for p in layout.positions)
            if side == Side.TUBE
            else (),
        )
        for side in Side
    )
    cells = []
    for p in paths:
        ordered = list(intervals) if p.side == Side.TUBE else list(reversed(intervals))
        pieces = []
        for i in ordered:
            a, z = number(i.start_m), number(i.end_m)
            pc = [(a, (a + z) / 2), ((a + z) / 2, z)] if split and p.side == Side.TUBE else [(a, z)]
            if p.side == Side.SHELL:
                pc = [(z, a) for a, z in reversed(pc)]
            pieces.extend((i, a, z) for a, z in pc)
        travel = Fraction()
        for k, (i, a, z) in enumerate(pieces):
            cells.append(
                Cell(
                    numerical_cell_id=f"{p.side.value}c{k}",
                    physical_segment_id=i.physical_segment_id,
                    flow_path_id=p.flow_path_id,
                    upstream_face_id=f"{p.side.value}f{k}",
                    downstream_face_id=p.outlet_face_id
                    if k == len(pieces) - 1
                    else f"{p.side.value}f{k + 1}",
                    physical_upstream_m=decimal_text(a),
                    physical_downstream_m=decimal_text(z),
                    travel_start_m=decimal_text(travel),
                    travel_end_m=decimal_text(travel + abs(z - a)),
                )
            )
            travel += abs(z - a)
    walls = []
    for tc in [x for x in cells if x.flow_path_id == "TUBE"]:
        for sc in [x for x in cells if x.flow_path_id == "SHELL"]:
            a = max(
                min(number(tc.physical_upstream_m), number(tc.physical_downstream_m)),
                min(number(sc.physical_upstream_m), number(sc.physical_downstream_m)),
            )
            z = min(
                max(number(tc.physical_upstream_m), number(tc.physical_downstream_m)),
                max(number(sc.physical_upstream_m), number(sc.physical_downstream_m)),
            )
            if a < z:
                # Explicit fixture intersection/area allocation; not a production mesh policy.
                ratio = (z - a) / Fraction("4.85")
                walls.append(
                    Wall(
                        wall_interface_id=f"w{len(walls)}",
                        physical_segment_id=tc.physical_segment_id,
                        hot_cell_id=tc.numerical_cell_id if hot_tube else sc.numerical_cell_id,
                        cold_cell_id=sc.numerical_cell_id if hot_tube else tc.numerical_cell_id,
                        start_m=decimal_text(a),
                        end_m=decimal_text(z),
                        inside_area_m2=decimal_text(inside * ratio),
                        outside_area_m2=decimal_text(outside * ratio),
                    )
                )
    events = []

    def event(role, indices, a, z):
        events.append(
            Event(
                physical_event_id=f"e{len(events)}",
                physical_compartment_id=f"comp{len(events)}",
                role=role,
                native_geometry_id=g.geometry_id,
                native_geometry_hash=g.geometry_hash,
                start_m=str(a),
                end_m=str(z),
                baffle_indices=indices,
                position_ids=tuple(p.position_id for p in layout.positions)
                if role == EventRole.TUBE_ROW_OR_CROSSED_ROW
                else (),
                multiplicity=1,
                physical_segment_ids=tuple(
                    i.physical_segment_id
                    for i in intervals
                    if number(i.start_m) <= number(str(z)) and number(i.end_m) >= number(str(a))
                ),
                authority=authority(g.geometry_hash),
                producer_status="UNRESOLVED",
                source_relation_role="STRUCTURAL_REFERENCE_ONLY",
            )
        )

    for p in g.baffle_planes:
        for role in [EventRole.BAFFLE, EventRole.WINDOW, EventRole.LEAKAGE_GEOMETRY]:
            event(role, (p.baffle_index,), p.center_coordinate_m, p.center_coordinate_m)
    for a, z in zip(g.baffle_planes, g.baffle_planes[1:], strict=False):
        event(
            EventRole.CENTRAL_CROSSFLOW,
            (a.baffle_index, z.baffle_index),
            a.center_coordinate_m,
            z.center_coordinate_m,
        )
    event(EventRole.OUTLET_END_ZONE, (), "0", g.baffle_planes[0].center_coordinate_m)
    event(EventRole.INLET_END_ZONE, (), g.baffle_planes[-1].center_coordinate_m, "4.85")
    event(EventRole.BYPASS_GEOMETRY, (), "0", "4.85")
    event(EventRole.TUBE_ROW_OR_CROSSED_ROW, (), "0", "4.85")
    states = tuple(
        State(
            state_id="s" + c.numerical_cell_id,
            location=Location.CELL_MEAN,
            owner_id=c.numerical_cell_id,
            flow_path_id=c.flow_path_id,
            authority=authority(),
            producer_status="UNRESOLVED",
        )
        for c in cells
    )
    d = Definition(
        profile_id=PROFILE_ID,
        authority_ids=AUTHORITY_IDS,
        review_receipt_id=REVIEW_RECEIPT_ID,
        steady_state=True,
        single_phase=True,
        newtonian=True,
        flow_arrangement="COUNTERCURRENT",
        tube_path="STRAIGHT_THROUGH",
        mapping_authority=authority(g.geometry_hash),
        mesh_authority=authority(g.geometry_hash),
        intervals=intervals,
        paths=paths,
        cells=tuple(cells),
        walls=tuple(walls),
        events=tuple(events),
        states=states,
        provenance_edges=(),
    )
    return dict(
        definition=d, baffle_request=br, area_request=ar, native_identity=ni, bookkeeping=None
    )


@pytest.mark.parametrize(
    "split,hot_tube",
    [
        (False, True),
        (True, True),
        (True, False),
        (False, False),
    ],
)
def test_valid_explicit_topology(split, hot_tube):
    r = validate_request(fixture(split=split, hot_tube=hot_tube))
    assert r.status == "VALIDATED", r
    assert r.bookkeeping_status == "NOT_REQUESTED"


def test_mesh_split_preserves_hardware():
    a = validate_request(fixture())
    z = validate_request(fixture(split=True))
    assert a.status == z.status == "VALIDATED"
    assert a.native_identity == z.native_identity
    assert a.physical_ownership_hash == z.physical_ownership_hash
    assert a.mesh_identity != z.mesh_identity
    assert a.topology_definition.events == z.topology_definition.events
    assert a.topology_definition.intervals == z.topology_definition.intervals


def native_cuts(request):
    g = baffle_validate(request["baffle_request"]).geometry
    return sorted(
        {
            number(g.axial_span.axial_start_coordinate_m),
            *(number(p.center_coordinate_m) for p in g.baffle_planes),
            number(g.axial_span.axial_end_coordinate_m),
        }
    )


def test_positive_intervals_exactly_follow_native_boundaries():
    request = fixture()
    d = request["definition"]
    actual = {number(i.start_m) for i in d.intervals} | {number(i.end_m) for i in d.intervals}
    assert actual == set(native_cuts(request))
    assert validate_request(request).status == "VALIDATED"


@pytest.mark.parametrize("kind", ["missing_one", "whole_span", "old_midpoint", "extra_mesh_cut"])
def test_physical_boundaries_must_be_native(kind):
    cuts = native_cuts(fixture())
    if kind == "missing_one":
        cuts = cuts[:1] + cuts[2:]
    elif kind == "whole_span":
        cuts = [cuts[0], cuts[-1]]
    elif kind == "old_midpoint":
        cuts = [cuts[0], (cuts[0] + cuts[-1]) / 2, cuts[-1]]
    else:
        cuts = sorted(cuts + [(cuts[0] + cuts[1]) / 2])
    # Internally consistent cells/events/areas cannot excuse missing native cuts.
    request = fixture(invalid_physical_cuts=cuts)
    result = validate_request(request)
    assert result.status == "BLOCKED"
    assert result.blocker_code == "INVALID_PHYSICAL_MAPPING"
    assert result.blocker_field in {"missing_native_event_boundary", "unbound_physical_boundary"}
    assert result.topology_definition is None


def test_mesh_merge_cannot_cross_baffle_window_boundary():
    request = fixture()
    d = request["definition"]
    a, b = d.cells[:2]
    merged = a.model_copy(
        update={
            "downstream_face_id": b.downstream_face_id,
            "physical_downstream_m": b.physical_downstream_m,
            "travel_end_m": b.travel_end_m,
        }
    )
    request["definition"] = d.model_copy(update={"cells": (merged,) + d.cells[2:]})
    result = validate_request(request)
    assert result.status == "BLOCKED"
    assert result.blocker_code == "INVALID_MESH_MAPPING"
    assert result.blocker_field == "cell_partition"


def test_canonical_order_and_decimal_context():
    f = fixture(split=True)
    a = validate_request(f)
    d = f["definition"]
    f["definition"] = d.model_copy(
        update={
            k: tuple(reversed(getattr(d, k)))
            for k in ["paths", "cells", "intervals", "walls", "events", "states", "authority_ids"]
        }
    )
    with localcontext() as ctx:
        ctx.prec = 6
        z = validate_request(f)
    assert a == z


@pytest.mark.parametrize(
    "field,value",
    [
        ("steady_state", False),
        ("single_phase", False),
        ("newtonian", False),
        ("flow_arrangement", "COCURRENT"),
        ("tube_path", "RETURN"),
        ("profile_id", "TAMPERED"),
        ("review_receipt_id", "SELF_APPROVED"),
    ],
)
def test_admission_rejected(field, value):
    f = fixture()
    f["definition"] = f["definition"].model_copy(update={field: value})
    assert validate_request(f).status == "BLOCKED"


@pytest.mark.parametrize(
    "kind",
    [
        "cycle",
        "orphan",
        "branch",
        "duplicate_inlet",
        "duplicate_outlet",
        "reverse",
        "cross_stream",
        "straddle",
        "gap",
        "zero",
        "unknown_interval",
    ],
)
def test_connectivity_rejected(kind):
    f = fixture(split=True)
    d = f["definition"]
    cells = list(d.cells)
    c = cells[0]
    updates = {
        "cycle": {"upstream_face_id": c.downstream_face_id},
        "orphan": {"flow_path_id": "other"},
        "branch": {"downstream_face_id": c.upstream_face_id},
        "duplicate_inlet": {"upstream_face_id": "TUBEf1"},
        "duplicate_outlet": {"downstream_face_id": "TUBEout"},
        "reverse": {"physical_downstream_m": "-1"},
        "cross_stream": {"upstream_face_id": "SHELLf0"},
        "straddle": {"physical_downstream_m": "5"},
        "gap": {"physical_upstream_m": "0.1"},
        "zero": {"physical_downstream_m": "0"},
        "unknown_interval": {"physical_segment_id": "other"},
    }[kind]
    cells[0] = c.model_copy(update=updates)
    f["definition"] = d.model_copy(update={"cells": tuple(cells)})
    assert validate_request(f).status == "BLOCKED"


@pytest.mark.parametrize("role", [EventRole.BAFFLE, EventRole.WINDOW, EventRole.INLET_END_ZONE])
def test_mesh_cannot_create_event(role):
    f = fixture()
    d = f["definition"]
    e = next(e for e in d.events if e.role == role)
    f["definition"] = d.model_copy(
        update={"events": d.events + (e.model_copy(update={"physical_event_id": "new"}),)}
    )
    assert validate_request(f).blocker_code == "DUPLICATE_PHYSICAL_EVENT"


@pytest.mark.parametrize("field", ["inside_area_m2", "outside_area_m2"])
def test_area_mismatch(field):
    f = fixture()
    d = f["definition"]
    f["definition"] = d.model_copy(update={"walls": (d.walls[0].model_copy(update={field: "0"}),)})
    assert validate_request(f).blocker_code == "INVALID_AREA_OWNERSHIP"


def test_native_hash_tamper():
    f = fixture()
    f["native_identity"] = f["native_identity"].model_copy(update={"layout_hash": "0" * 64})
    assert validate_request(f).blocker_code == "UPSTREAM_IDENTITY_MISMATCH"


def test_provenance_cycle():
    f = fixture()
    f["definition"] = f["definition"].model_copy(
        update={"provenance_edges": (Edge(source="a", target="b"), Edge(source="b", target="a"))}
    )
    assert validate_request(f).blocker_code == "PROVENANCE_INVALID"


def test_unlocated_state():
    f = fixture()
    d = f["definition"]
    f["definition"] = d.model_copy(
        update={"states": (d.states[0].model_copy(update={"owner_id": "missing"}),)}
    )
    assert validate_request(f).blocker_code == "UNLOCATED_STATE"


def test_enthalpy_residual_not_numerical_acceptance():
    f = fixture()
    d = f["definition"]
    values = {}
    for path in d.paths:
        cells = sorted(
            (c for c in d.cells if c.flow_path_id == path.flow_path_id),
            key=lambda c: number(c.travel_start_m),
        )
        faces = [c.upstream_face_id for c in cells] + [cells[-1].downstream_face_id]
        for i, face in enumerate(faces):
            delta = Fraction(10 * i, len(cells))
            values[face] = decimal_text(20 - delta if path.role == Role.HOT else delta)
    f["bookkeeping"] = Bookkeeping(
        faces=tuple(
            FaceObservation(face_id=k, enthalpy_j_kg=v, mass_flow_kg_s="2", authority=authority())
            for k, v in values.items()
        ),
        heat_events=tuple(
            HeatObservation(
                wall_interface_id=w.wall_interface_id,
                heat_rate_w=decimal_text(Fraction(20, len(d.walls))),
                authority=authority(),
            )
            for w in d.walls
        ),
    )
    r = validate_request(f)
    assert r.status == "VALIDATED", r
    assert {x.energy_residual_w for x in r.residuals} == {"0"}
    assert r.bookkeeping_status == "COMPUTED_NOT_ASSESSED"
    f["bookkeeping"] = f["bookkeeping"].model_copy(
        update={
            "heat_events": tuple(
                HeatObservation(
                    wall_interface_id=w.wall_interface_id,
                    heat_rate_w="-1",
                    authority=authority(),
                )
                for w in d.walls
            )
        }
    )
    r = validate_request(f)
    assert {x.energy_residual_w for x in r.residuals} == {
        decimal_text(Fraction(20, len(d.walls)) + 1)
    }
    assert r.status == "VALIDATED"  # Structural status only, not energy acceptance.


@pytest.mark.parametrize("raw", [None, {}, [], 42])
def test_invalid_raw(raw):
    assert validate_request(raw).status == "BLOCKED"


@pytest.mark.parametrize("family", ["U_TUBE", "FLOATING_HEAD"])
def test_native_family_rejected(family):
    from hexagent.exchangers.shell_tube.models import ConstructionFamily

    f = fixture()
    f["baffle_request"]["configuration"] = replace(
        f["baffle_request"]["configuration"], construction_family=ConstructionFamily(family)
    )
    assert validate_request(f).status == "BLOCKED"


@pytest.mark.parametrize("field", ["tube_pass_count", "shell_pass_count"])
def test_additional_pass_rejected(field):
    f = fixture()
    f["baffle_request"]["configuration"] = replace(
        f["baffle_request"]["configuration"], **{field: 2}
    )
    assert validate_request(f).status == "BLOCKED"


def test_non_e_shell_rejected():
    f = fixture()
    c = f["baffle_request"]["configuration"]
    f["baffle_request"]["configuration"] = replace(
        c, component_tokens=replace(c.component_tokens, shell="F")
    )
    assert validate_request(f).status == "BLOCKED"


def test_event_removed_or_hash_tampered():
    f = fixture()
    d = f["definition"]
    f["definition"] = d.model_copy(update={"events": d.events[1:]})
    assert validate_request(f).status == "BLOCKED"
    f["definition"] = d.model_copy(
        update={
            "events": (d.events[0].model_copy(update={"native_geometry_hash": "0" * 64}),)
            + d.events[1:]
        }
    )
    assert validate_request(f).status == "BLOCKED"


def test_no_hooks_or_unbounded_mesh():
    class Poison:
        def __repr__(self):
            raise AssertionError("repr called")

        def __str__(self):
            raise AssertionError("str called")

        def __hash__(self):
            raise AssertionError("hash called")

    f = fixture()
    d = f["definition"]
    f["definition"] = d.model_copy(update={"profile_id": Poison()})
    assert validate_request(f).status == "BLOCKED"
    f["definition"] = d.model_copy(update={"cells": d.cells * 4097})
    assert validate_request(f).status == "BLOCKED"


def test_state_location_and_mixed_producer_closed():
    f = fixture()
    d = f["definition"]
    s = d.states[0]
    f["definition"] = d.model_copy(
        update={"states": (s.model_copy(update={"location": "UNKNOWN"}),)}
    )
    assert validate_request(f).status == "BLOCKED"
    f["definition"] = d.model_copy(
        update={
            "states": (
                s.model_copy(
                    update={
                        "location": Location.COMPARTMENT_MIXED,
                        "owner_id": d.events[0].physical_compartment_id,
                    }
                ),
            )
        }
    )
    r = validate_request(f)
    assert r.status == "VALIDATED"
    assert r.topology_definition.states[0].producer_status == "UNRESOLVED"
    f["definition"] = f["definition"].model_copy(
        update={
            "states": (
                f["definition"].states[0].model_copy(update={"producer_status": "COMPUTED"}),
            )
        }
    )
    assert validate_request(f).status == "BLOCKED"


def test_connectivity_semantics_changes_identity():
    f = fixture()
    a = validate_request(f)
    d = f["definition"]
    # Relabeling a physical port changes graph identity; presentation sorting does not.
    f["definition"] = d.model_copy(
        update={
            "paths": tuple(
                p.model_copy(update={"inlet_face_id": "new-inlet"}) if p.side == Side.TUBE else p
                for p in d.paths
            ),
            "cells": tuple(
                c.model_copy(update={"upstream_face_id": "new-inlet"})
                if c.upstream_face_id == "TUBEf0"
                else c
                for c in d.cells
            ),
        }
    )
    z = validate_request(f)
    assert z.status == "VALIDATED"
    assert a.topology_id != z.topology_id


def test_canonical_decimal_lexical_equivalence():
    f = fixture()
    a = validate_request(f)
    d = f["definition"]
    f["definition"] = d.model_copy(
        update={
            "intervals": (d.intervals[0].model_copy(update={"start_m": "0.0000"}),)
            + d.intervals[1:]
        }
    )
    assert validate_request(f) == a


def test_duplicate_heat_and_missing_observation_fail_closed():
    f = fixture()
    w = f["definition"].walls[0]
    q = HeatObservation(
        wall_interface_id=w.wall_interface_id, heat_rate_w="1", authority=authority()
    )
    f["bookkeeping"] = Bookkeeping(faces=(), heat_events=(q, q))
    assert validate_request(f).status == "BLOCKED"


def test_required_provenance_and_no_cycle():
    from hexagent.exchangers.shell_tube.segmented_thermal_state_topology.provenance import (
        verify_edges,
    )

    r = validate_request(fixture(split=True))
    assert verify_edges(r.provenance_edges) == r.provenance_edges
    sources = {e.source for e in r.provenance_edges}
    assert all("authority:" + a in sources for a in AUTHORITY_IDS)
    assert all(
        any(s.startswith(k + ":") for s in sources)
        for k in ["walls", "paths", "states", "events", "intervals"]
    )
    assert all(e.source != e.target for e in r.provenance_edges)


def test_canonical_snapshot_can_be_replayed():
    request = fixture(split=True)
    first = validate_request(request)
    assert first.status == "VALIDATED"
    request["definition"] = first.topology_definition
    assert validate_request(request) == first


def test_duplicate_native_row_reference_rejected():
    request = fixture()
    d = request["definition"]
    request["definition"] = d.model_copy(
        update={
            "events": tuple(
                e.model_copy(update={"position_ids": e.position_ids + e.position_ids})
                if e.role == EventRole.TUBE_ROW_OR_CROSSED_ROW
                else e
                for e in d.events
            )
        }
    )
    assert validate_request(request).status == "BLOCKED"


def test_shared_internal_enthalpy_flux_cancels_with_different_meshes():
    request = fixture(split=True)
    d = request["definition"]
    observations = []
    for path in d.paths:
        cells = sorted(
            (c for c in d.cells if c.flow_path_id == path.flow_path_id),
            key=lambda c: number(c.travel_start_m),
        )
        faces = [c.upstream_face_id for c in cells] + [cells[-1].downstream_face_id]
        for i, face in enumerate(faces):
            delta = Fraction(2 * i, len(cells))
            enthalpy = 200 - delta if path.role == Role.HOT else 100 + delta
            observations.append(
                FaceObservation(
                    face_id=face,
                    enthalpy_j_kg=decimal_text(enthalpy),
                    mass_flow_kg_s="1",
                    authority=authority(),
                )
            )
    request["bookkeeping"] = Bookkeeping(
        faces=tuple(observations),
        heat_events=tuple(
            HeatObservation(
                wall_interface_id=w.wall_interface_id,
                heat_rate_w=decimal_text(Fraction(2, len(d.walls))),
                authority=authority(),
            )
            for w in d.walls
        ),
    )
    result = validate_request(request)
    assert result.status == "VALIDATED"
    assert result.global_energy_residual_w == "0"
    assert all(r.energy_residual_w == "0" for r in result.residuals)
    assert result.bookkeeping_status == "COMPUTED_NOT_ASSESSED"
    assert result.bookkeeping_observations is not None
    assert any(e.source.startswith("bookkeeping:") for e in result.provenance_edges)
