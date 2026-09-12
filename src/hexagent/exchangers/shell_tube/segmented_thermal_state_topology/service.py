"""TASK171 structural validator and exact enthalpy bookkeeping, not a solver."""

from fractions import Fraction
from typing import Any, TypeVar, cast

from pydantic import ValidationError

from hexagent.canonical_json import canonical_json_bytes, canonical_sha256

from . import models as model_types
from .authority import (
    AUTHORITY_IDS,
    AUTHORITY_PROFILE_HASH,
    MAX_RECORDS,
    PROFILE_ID,
    REVIEW_RECEIPT_ID,
    VERSION,
)
from .canonical import decimal_text, identity, number, projection
from .errors import Code, Failure
from .models import (
    Binding,
    Bookkeeping,
    Definition,
    Edge,
    EventRole,
    Location,
    Model,
    NativeIdentity,
    Residual,
    Result,
    Role,
    Side,
)
from .native import replay
from .provenance import verify_edges

T = TypeVar("T", bound=Model)


def safe_model(value: object) -> None:
    """Reject model_construct poisoning without calling user repr/coercion hooks."""
    allowed = {
        v for v in vars(model_types).values() if isinstance(v, type) and issubclass(v, Model)
    }
    enums = {Role, Side, Location, EventRole}
    nodes = 0

    def walk(item: object, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        require(
            nodes <= MAX_RECORDS * 64 and depth <= 16, Code.RAW_BOUNDARY_INVALID, "resource_bound"
        )
        kind = type(item)
        if kind in allowed:
            for child in object.__getattribute__(item, "__dict__").values():
                walk(child, depth + 1)
        elif kind is tuple:
            require(
                len(cast(tuple[object, ...], item)) <= MAX_RECORDS,
                Code.RAW_BOUNDARY_INVALID,
                "record_bound",
            )
            for child in cast(tuple[object, ...], item):
                walk(child, depth + 1)
        elif kind in enums or item is None or kind is bool:
            return
        elif kind is str:
            require(len(cast(str, item)) <= 512, Code.RAW_BOUNDARY_INVALID, "string_bound")
        elif kind is int:
            require(abs(cast(int, item)) <= MAX_RECORDS, Code.RAW_BOUNDARY_INVALID, "count_bound")
        else:
            raise Failure(Code.RAW_BOUNDARY_INVALID, "unknown_object")

    walk(value, 0)


def require(ok: bool, code: Code, field: str) -> None:
    if not ok:
        raise Failure(code, field)


def index(items: tuple[T, ...], field: str, code: Code) -> dict[str, T]:
    require(0 < len(items) <= MAX_RECORDS, code, field)
    result = {getattr(item, field): item for item in items}
    require(len(result) == len(items), code, field)
    require(all(type(k) is str and k and len(k) <= 512 for k in result), code, field)
    return result


def binding(value: Binding) -> None:
    require(
        bool(value.authority_id and value.revision and value.evidence_refs),
        Code.TOPOLOGY_AUTHORITY_INCOMPLETE,
        "binding",
    )
    require(
        len(value.source_hash) == 64 and all(c in "0123456789abcdef" for c in value.source_hash),
        Code.TOPOLOGY_AUTHORITY_INCOMPLETE,
        "binding.source_hash",
    )
    require(
        len(set(value.evidence_refs)) == len(value.evidence_refs) and all(value.evidence_refs),
        Code.TOPOLOGY_AUTHORITY_INCOMPLETE,
        "binding.evidence_refs",
    )
    # Source-bound project definition, not a reviewed numerical preset.


def partition(
    parts: list[tuple[Fraction, Fraction]], start: Fraction, end: Fraction, code: Code, field: str
) -> None:
    cursor = start
    for left, right in sorted(parts):
        require(left == cursor and right > left, code, field)
        cursor = right
    require(cursor == end and bool(parts), code, field)


def _validate(
    d: Definition, g: Any, active_positions: tuple[str, ...], inside: Fraction, outside: Fraction
) -> None:
    require(
        d.profile_id == PROFILE_ID
        and set(d.authority_ids) == set(AUTHORITY_IDS)
        and len(d.authority_ids) == 3
        and d.review_receipt_id == REVIEW_RECEIPT_ID,
        Code.TOPOLOGY_AUTHORITY_INCOMPLETE,
        "profile",
    )
    require(
        d.steady_state
        and d.single_phase
        and d.newtonian
        and d.flow_arrangement == "COUNTERCURRENT"
        and d.tube_path == "STRAIGHT_THROUGH",
        Code.UNSUPPORTED_TOPOLOGY,
        "envelope",
    )
    binding(d.mapping_authority)
    binding(d.mesh_authority)
    require(
        d.mapping_authority.source_hash == g.geometry_hash
        and d.mesh_authority.source_hash == g.geometry_hash,
        Code.TOPOLOGY_AUTHORITY_INCOMPLETE,
        "mapping_geometry_binding",
    )
    verify_edges(d.provenance_edges)
    intervals = index(d.intervals, "physical_segment_id", Code.INVALID_PHYSICAL_MAPPING)
    paths = index(d.paths, "flow_path_id", Code.INVALID_CONNECTIVITY)
    cells = index(d.cells, "numerical_cell_id", Code.INVALID_MESH_MAPPING)
    walls = index(d.walls, "wall_interface_id", Code.INVALID_AREA_OWNERSHIP)
    events = index(d.events, "physical_event_id", Code.DUPLICATE_PHYSICAL_EVENT)
    states = index(d.states, "state_id", Code.UNLOCATED_STATE)
    start = number(g.axial_span.axial_start_coordinate_m)
    end = number(g.axial_span.axial_end_coordinate_m)
    partition(
        [(number(i.start_m), number(i.end_m)) for i in intervals.values()],
        start,
        end,
        Code.INVALID_PHYSICAL_MAPPING,
        "intervals",
    )
    require(
        sum((number(i.inside_area_m2) for i in intervals.values()), Fraction()) == inside
        and sum((number(i.outside_area_m2) for i in intervals.values()), Fraction()) == outside,
        Code.INVALID_AREA_OWNERSHIP,
        "native_area_totals",
    )
    require(
        len(paths) == 2
        and {p.side for p in paths.values()} == {Side.TUBE, Side.SHELL}
        and {p.role for p in paths.values()} == {Role.HOT, Role.COLD}
        and len({p.stream_id for p in paths.values()}) == 2,
        Code.INVALID_CONNECTIVITY,
        "side_assignment",
    )
    require(
        {number(p.physical_inlet_m) for p in paths.values()} == {start, end},
        Code.INVALID_CONNECTIVITY,
        "countercurrent_inlets",
    )
    face_paths: dict[str, str] = {}
    for p in paths.values():
        require(
            bool(p.stream_id and p.inlet_face_id and p.outlet_face_id),
            Code.INVALID_CONNECTIVITY,
            "empty_port_or_stream",
        )
        a, b = number(p.physical_inlet_m), number(p.physical_outlet_m)
        require({a, b} == {start, end} and a != b, Code.INVALID_CONNECTIVITY, "physical_ports")
        require(p.inlet_face_id != p.outlet_face_id, Code.INVALID_CONNECTIVITY, "ports")
        if p.side == Side.TUBE:
            require(
                len(p.tube_position_ids) == len(set(p.tube_position_ids))
                and set(p.tube_position_ids) == set(active_positions),
                Code.INVALID_PHYSICAL_MAPPING,
                "parallel_tube_membership",
            )
        else:
            require(not p.tube_position_ids, Code.INVALID_PHYSICAL_MAPPING, "shell_membership")
        pcs = [c for c in cells.values() if c.flow_path_id == p.flow_path_id]
        require(bool(pcs), Code.INVALID_CONNECTIVITY, "orphan_path")
        upstream = {c.upstream_face_id: c for c in pcs}
        downstream = {c.downstream_face_id: c for c in pcs}
        require(
            len(upstream) == len(pcs) and len(downstream) == len(pcs),
            Code.INVALID_CONNECTIVITY,
            "branch_or_duplicate_port",
        )
        require(
            set(upstream) - set(downstream) == {p.inlet_face_id}
            and set(downstream) - set(upstream) == {p.outlet_face_id},
            Code.INVALID_CONNECTIVITY,
            "inlet_outlet_count",
        )
        seen: set[str] = set()
        face, coordinate, travel = p.inlet_face_id, a, Fraction()
        while face != p.outlet_face_id:
            require(face in upstream, Code.INVALID_CONNECTIVITY, "disconnected")
            c = upstream[face]
            require(c.numerical_cell_id not in seen, Code.INVALID_CONNECTIVITY, "cycle")
            seen.add(c.numerical_cell_id)
            x, y = number(c.physical_upstream_m), number(c.physical_downstream_m)
            require(
                x == coordinate and (y - x) * (b - a) > 0,
                Code.INVALID_CONNECTIVITY,
                "reversal_or_face_coordinate",
            )
            require(
                number(c.travel_start_m) == travel
                and number(c.travel_end_m) - travel == abs(y - x),
                Code.INVALID_CONNECTIVITY,
                "travel_coordinate",
            )
            coordinate, travel, face = y, number(c.travel_end_m), c.downstream_face_id
        require(
            len(seen) == len(pcs) and coordinate == b, Code.INVALID_CONNECTIVITY, "orphan_or_cycle"
        )
        for f in set(upstream) | set(downstream):
            require(f not in face_paths, Code.INVALID_CONNECTIVITY, "cross_stream_mass_face")
            face_paths[f] = p.flow_path_id
        for i in intervals.values():
            partition(
                [
                    (
                        min(number(c.physical_upstream_m), number(c.physical_downstream_m)),
                        max(number(c.physical_upstream_m), number(c.physical_downstream_m)),
                    )
                    for c in pcs
                    if c.physical_segment_id == i.physical_segment_id
                ],
                number(i.start_m),
                number(i.end_m),
                Code.INVALID_MESH_MAPPING,
                "cell_partition",
            )
    require(
        all(c.flow_path_id in paths and c.physical_segment_id in intervals for c in cells.values()),
        Code.INVALID_MESH_MAPPING,
        "cell_membership",
    )
    for w in walls.values():
        require(
            w.hot_cell_id in cells
            and w.cold_cell_id in cells
            and w.physical_segment_id in intervals,
            Code.INVALID_AREA_OWNERSHIP,
            "wall_membership",
        )
        hot, cold = cells[w.hot_cell_id], cells[w.cold_cell_id]
        require(
            paths[hot.flow_path_id].role == Role.HOT and paths[cold.flow_path_id].role == Role.COLD,
            Code.INVALID_AREA_OWNERSHIP,
            "wall_roles",
        )
        require(
            hot.physical_segment_id == cold.physical_segment_id == w.physical_segment_id,
            Code.INVALID_AREA_OWNERSHIP,
            "wall_interval",
        )
        left, right = number(w.start_m), number(w.end_m)
        for c in (hot, cold):
            bounds = sorted((number(c.physical_upstream_m), number(c.physical_downstream_m)))
            require(
                bounds[0] <= left < right <= bounds[1], Code.INVALID_AREA_OWNERSHIP, "wall_support"
            )
        require(
            number(w.inside_area_m2) > 0 and number(w.outside_area_m2) > 0,
            Code.INVALID_AREA_OWNERSHIP,
            "positive_area",
        )
    for c in cells.values():
        bounds = sorted((number(c.physical_upstream_m), number(c.physical_downstream_m)))
        partition(
            [
                (number(w.start_m), number(w.end_m))
                for w in walls.values()
                if c.numerical_cell_id in (w.hot_cell_id, w.cold_cell_id)
            ],
            bounds[0],
            bounds[1],
            Code.INVALID_AREA_OWNERSHIP,
            "wall_cell_coverage",
        )
    for i in intervals.values():
        owned = [w for w in walls.values() if w.physical_segment_id == i.physical_segment_id]
        require(
            sum((number(w.inside_area_m2) for w in owned), Fraction()) == number(i.inside_area_m2)
            and sum((number(w.outside_area_m2) for w in owned), Fraction())
            == number(i.outside_area_m2),
            Code.INVALID_AREA_OWNERSHIP,
            "interval_area",
        )
    # Exact source-role structural occurrences. No local Bell state or equation.
    planes = {p.baffle_index: number(p.center_coordinate_m) for p in g.baffle_planes}
    ordered = sorted(planes, key=lambda k: planes[k])
    expected: dict[tuple[EventRole, tuple[int, ...]], tuple[Fraction, Fraction, int]] = {}
    for k in ordered:
        for role in (EventRole.BAFFLE, EventRole.WINDOW, EventRole.LEAKAGE_GEOMETRY):
            expected[role, (k,)] = (planes[k], planes[k], 1)
    for a, b in zip(ordered, ordered[1:], strict=False):
        expected[EventRole.CENTRAL_CROSSFLOW, (a, b)] = (planes[a], planes[b], 1)
    require(len(ordered) >= 2, Code.UNSUPPORTED_TOPOLOGY, "Bell_baffle_count")
    low_end = (start, planes[ordered[0]], 1)
    high_end = (planes[ordered[-1]], end, 1)
    shell_path = next(p for p in paths.values() if p.side == Side.SHELL)
    inlet_low = number(shell_path.physical_inlet_m) == start
    expected[EventRole.INLET_END_ZONE, ()] = low_end if inlet_low else high_end
    expected[EventRole.OUTLET_END_ZONE, ()] = high_end if inlet_low else low_end
    expected[EventRole.BYPASS_GEOMETRY, ()] = (start, end, 1)
    expected[EventRole.TUBE_ROW_OR_CROSSED_ROW, ()] = (start, end, 1)
    keys: set[tuple[EventRole, tuple[int, ...]]] = set()
    for e in events.values():
        binding(e.authority)
        key = e.role, tuple(sorted(e.baffle_indices))
        require(
            key in expected and key not in keys, Code.DUPLICATE_PHYSICAL_EVENT, "native_occurrence"
        )
        keys.add(key)
        require(
            (number(e.start_m), number(e.end_m), e.multiplicity) == expected[key],
            Code.INVALID_PHYSICAL_MAPPING,
            "event_native_support",
        )
        require(
            e.native_geometry_id == g.geometry_id
            and e.native_geometry_hash == g.geometry_hash
            and e.authority.source_hash == g.geometry_hash,
            Code.UPSTREAM_IDENTITY_MISMATCH,
            "event_geometry",
        )
        require(bool(e.physical_compartment_id), Code.INVALID_PHYSICAL_MAPPING, "compartment")
        supports = {
            i.physical_segment_id
            for i in intervals.values()
            if number(i.start_m) <= number(e.end_m) and number(i.end_m) >= number(e.start_m)
        }
        require(
            set(e.physical_segment_ids) == supports
            and len(e.physical_segment_ids) == len(supports),
            Code.INVALID_PHYSICAL_MAPPING,
            "event_incidence",
        )
        require(
            len(e.position_ids) == len(set(e.position_ids))
            and set(e.position_ids)
            == (set(active_positions) if e.role == EventRole.TUBE_ROW_OR_CROSSED_ROW else set()),
            Code.INVALID_PHYSICAL_MAPPING,
            "row_geometry_membership",
        )
    require(keys == set(expected), Code.INVALID_PHYSICAL_MAPPING, "missing_event")
    # Row membership is a reference slot; active tube count is NOT a Bell row count.
    for s in states.values():
        binding(s.authority)
        require(s.flow_path_id in paths, Code.UNLOCATED_STATE, "state_path")
        if s.location in (Location.UPSTREAM_FACE, Location.DOWNSTREAM_FACE):
            require(
                face_paths.get(s.owner_id) == s.flow_path_id, Code.UNLOCATED_STATE, "face_owner"
            )
            candidates = [c for c in cells.values() if c.flow_path_id == s.flow_path_id]
            valid_faces = {
                c.upstream_face_id if s.location == Location.UPSTREAM_FACE else c.downstream_face_id
                for c in candidates
            }
            require(s.owner_id in valid_faces, Code.UNLOCATED_STATE, "face_direction")
        elif s.location == Location.CELL_MEAN:
            require(
                s.owner_id in cells and cells[s.owner_id].flow_path_id == s.flow_path_id,
                Code.UNLOCATED_STATE,
                "cell_owner",
            )
        elif s.location == Location.COMPARTMENT_MIXED:
            require(
                s.owner_id in {e.physical_compartment_id for e in events.values()},
                Code.UNLOCATED_STATE,
                "compartment_owner",
            )
        else:
            require(s.owner_id in walls, Code.UNLOCATED_STATE, "wall_owner")
            require(
                paths[s.flow_path_id].side
                == (Side.TUBE if s.location == Location.WALL_INNER_SURFACE else Side.SHELL),
                Code.UNLOCATED_STATE,
                "wall_surface_side",
            )


def _bookkeeping(d: Definition, b: Bookkeeping | None) -> tuple[Residual, ...]:
    if b is None:
        return ()
    faces = index(b.faces, "face_id", Code.CONSERVATION_INPUT_INCOMPLETE)
    heats = index(b.heat_events, "wall_interface_id", Code.CONSERVATION_INPUT_INCOMPLETE)
    require(
        set(faces) == {f for c in d.cells for f in (c.upstream_face_id, c.downstream_face_id)}
        and set(heats) == {w.wall_interface_id for w in d.walls},
        Code.CONSERVATION_INPUT_INCOMPLETE,
        "observation_coverage",
    )
    for obs in b.faces:
        binding(obs.authority)
    for heat in b.heat_events:
        binding(heat.authority)
    paths = {p.flow_path_id: p for p in d.paths}
    residuals = []
    for c in d.cells:
        up, down = faces[c.upstream_face_id], faces[c.downstream_face_id]
        m, n = number(up.mass_flow_kg_s), number(down.mass_flow_kg_s)
        require(m > 0 and n > 0 and m == n, Code.CONSERVATION_INPUT_INCOMPLETE, "steady_mass_flow")
        hot = paths[c.flow_path_id].role == Role.HOT
        flux = m * number(up.enthalpy_j_kg) - n * number(down.enthalpy_j_kg)
        q = sum(
            (
                number(heats[w.wall_interface_id].heat_rate_w)
                for w in d.walls
                if c.numerical_cell_id in (w.hot_cell_id, w.cold_cell_id)
            ),
            Fraction(),
        )
        residuals.append(
            Residual(
                cell_id=c.numerical_cell_id,
                energy_residual_w=decimal_text((flux if hot else -flux) - q),
                mass_residual_kg_s=decimal_text(m - n),
            )
        )
    return tuple(sorted(residuals, key=lambda x: x.cell_id))


def validate_request(raw: object) -> Result:
    """Validate explicit typed definition + native producer requests; fail closed."""
    try:
        require(type(raw) is dict, Code.RAW_BOUNDARY_INVALID, "request")
        request: Any = raw
        require(all(type(k) is str for k in request), Code.RAW_BOUNDARY_INVALID, "keys")
        require(
            set(request)
            == {"definition", "baffle_request", "area_request", "native_identity", "bookkeeping"},
            Code.RAW_BOUNDARY_INVALID,
            "fields",
        )
        require(
            type(request["definition"]) is Definition
            and type(request["native_identity"]) is NativeIdentity,
            Code.RAW_BOUNDARY_INVALID,
            "typed_inputs",
        )
        safe_model(request["definition"])
        safe_model(request["native_identity"])
        d = Definition.model_validate(request["definition"].model_dump())
        native = NativeIdentity.model_validate(request["native_identity"].model_dump())
        book = request["bookkeeping"]
        require(book is None or type(book) is Bookkeeping, Code.RAW_BOUNDARY_INVALID, "bookkeeping")
        if book is not None:
            safe_model(book)
            book = Bookkeeping.model_validate(book.model_dump())
        g, area, ratio = replay(request["baffle_request"], request["area_request"], native)
        inside = number(str(area.internal_heat_transfer_surface_area_m2))
        _validate(d, g, area.active_position_ids, inside, inside * number(ratio))
        residuals = _bookkeeping(d, book)
        roles = {p.flow_path_id: p.role for p in d.paths}
        cell_roles = {c.numerical_cell_id: roles[c.flow_path_id] for c in d.cells}
        global_residual = (
            None
            if book is None
            else decimal_text(
                sum(
                    (
                        number(r.energy_residual_w)
                        * (1 if cell_roles[r.cell_id] == Role.HOT else -1)
                        for r in residuals
                    ),
                    Fraction(),
                )
            )
        )
        native_payload = projection(native)
        physical = canonical_sha256(
            {
                "native": native_payload,
                "intervals": [
                    projection(i) for i in sorted(d.intervals, key=lambda i: i.physical_segment_id)
                ],
                "events": [
                    projection(e) for e in sorted(d.events, key=lambda e: e.physical_event_id)
                ],
                "mapping_authority": projection(d.mapping_authority),
            }
        )
        mesh = canonical_sha256(
            {
                "cells": projection(d)["cells"],
                "mesh_authority": projection(d.mesh_authority),
                "physical": physical,
            }
        )
        h = canonical_sha256(
            {
                "version": VERSION,
                "authority_profile_hash": AUTHORITY_PROFILE_HASH,
                "definition": projection(d),
                "native": native_payload,
                "bookkeeping": None if book is None else projection(book),
                "residuals": [projection(r) for r in residuals],
                "global_energy_residual_w": global_residual,
            }
        )
        tid = "urn:hxforge:task171:" + h
        # Caller edges are audit evidence; required producer/result edges cannot be omitted.
        edges = list(d.provenance_edges)
        inputs = (
            list(AUTHORITY_IDS)
            + [REVIEW_RECEIPT_ID, AUTHORITY_PROFILE_HASH]
            + list(native_payload.values())
            + [physical, mesh, identity(d.mapping_authority), identity(d.mesh_authority)]
        )
        for value in sorted(set(inputs)):
            edges.append(Edge(source="authority:" + value, target="run:" + h))
        for key in ("walls", "paths", "states", "events", "intervals"):
            digest = canonical_sha256({key: projection(d)[key]})
            edges.append(Edge(source=key + ":" + digest, target="run:" + h))
        if book is not None:
            edges.append(Edge(source="bookkeeping:" + identity(book), target="run:" + h))
        edges.append(Edge(source="run:" + h, target=tid))
        return Result(
            topology_definition=Definition.model_validate_json(canonical_json_bytes(projection(d))),
            bookkeeping_observations=(
                None
                if book is None
                else Bookkeeping.model_validate_json(canonical_json_bytes(projection(book)))
            ),
            warnings=(),
            status="VALIDATED",
            blocker_code=None,
            blocker_field=None,
            topology_id=tid,
            result_hash=h,
            mesh_identity=mesh,
            physical_ownership_hash=physical,
            native_identity=native,
            provenance_edges=verify_edges(tuple(edges)),
            residuals=residuals,
            global_energy_residual_w=global_residual,
            bookkeeping_status="NOT_REQUESTED" if book is None else "COMPUTED_NOT_ASSESSED",
        )
    except Failure as exc:
        code, field = exc.code.value, exc.field
    except (
        ValidationError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        ArithmeticError,
        RecursionError,
    ):
        code, field = Code.RAW_BOUNDARY_INVALID.value, "request"
    return Result(
        topology_definition=None,
        bookkeeping_observations=None,
        warnings=(),
        status="BLOCKED",
        blocker_code=code,
        blocker_field=field,
        topology_id=None,
        result_hash=None,
        mesh_identity=None,
        physical_ownership_hash=None,
        native_identity=None,
        provenance_edges=(),
        residuals=(),
        global_energy_residual_w=None,
        bookkeeping_status="UNAVAILABLE",
    )
