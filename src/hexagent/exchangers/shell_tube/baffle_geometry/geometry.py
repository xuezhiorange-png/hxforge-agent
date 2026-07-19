"""TASK-024 Round 5 deterministic geometry foundation.

This module implements the **in-memory** decimal-only geometry foundation
that follows :func:`hexagent.exchangers.shell_tube.baffle_geometry.authority
.validate_authority_foundation`. It accepts a fully-typed
:class:`hexagent.exchangers.shell_tube.baffle_geometry.models
.BaffleGeometryRequest` whose Round-4 authority validation already passed
(or whose caller has guaranteed Round-2 through Round-8 invariants) and
returns a private :class:`_GeometryFoundationResult`. It does not
construct a public :class:`BaffleGeometry` or
:class:`BaffleGeometryValidationResult`, does not compute a public
``geometry_hash``, ``geometry_id``, ``blocked_result_hash`` or
``provenance`` (these belong to a later round). It does not read any
TASK-023 catalog, does not perform public-facing heat-balance /
hydraulic calculations, and does not depend on the
``validation``/``public`` modules.

Stages implemented (Section 9 of the TASK-024 design contract):

* Stage 9  -- Decimal lexical canonicalization and signed-domain validation.
* Stage 10 -- Count, cardinality and exact axial closure.
* Stage 11 -- Derived diameters / radii / cut height / chord offset.
* Stage 12 -- Center planes and solid intervals.
* Stage 13 -- Single-segment cut chord construction (Decimal sqrt).
* Stage 14 -- Cut-boundary classification.
* Stage 15 -- Outer-circle containment (WINDOW / CROSSFLOW_REFERENCE).
* Stage 16 -- Covered-region hole pairwise non-overlap.
* Stage 17 -- Classification completeness.
* Stage 18 -- Public quantization closure.

Stages 1 (raw schema parsing), 2 through 8 (authority validation) and
19 (final canonical result) are explicitly **deferred** to other
modules.

Pure-in-memory architecture (Section 7 of the design contract):

* No filesystem / network / database / environment / clock / locale /
  random / subprocess / dynamic-import access.
* No float geometry (Decimal only, under the frozen precision-50 /
  ROUND_HALF_EVEN local context).
* No ``dataclasses.asdict``; no runtime field discovery; no
  ``str(object)``; no JSON default fallback.
* No second canonical JSON serializer; reuses
  ``baffle_geometry.canonical.canonical_json_bytes`` and
  ``canonical_decimal_string``.
* All Round-5 message codes are sourced from
  :class:`baffle_geometry.models.BlockerCode` and
  :class:`baffle_geometry.models.WarningCode`.

The module-local result type :class:`_GeometryFoundationResult` is
**module-private** and is **not** exported through ``__all__``. No
public dataclass is added.
"""

from __future__ import annotations

import decimal
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Final, cast

from hexagent.exchangers.shell_tube.baffle_geometry import (
    canonical as _t024_canonical,
)
from hexagent.exchangers.shell_tube.baffle_geometry import (
    models as _t024,
)

# ---------------------------------------------------------------------------
# Frozen decimal context and quanta (Section 7.2).
# ---------------------------------------------------------------------------

_DECIMAL_PRECISION: Final[int] = _t024_canonical.DECIMAL_PRECISION
_COORDINATE_QUANTUM: Final[Decimal] = Decimal(_t024_canonical.COORDINATE_QUANTUM_M)
_SQUARED_COORDINATE_QUANTUM: Final[Decimal] = Decimal(_t024_canonical.SQUARED_COORDINATE_QUANTUM_M2)
_CANONICAL_ZERO: Final[Decimal] = Decimal("0")
_ONE: Final[Decimal] = Decimal("1")
_TWO: Final[Decimal] = Decimal("2")

# Stage ranks (Section 9 of the design contract).
_STAGE_9_RANK: Final[int] = 9
_STAGE_10_RANK: Final[int] = 10
_STAGE_11_RANK: Final[int] = 11
_STAGE_12_RANK: Final[int] = 12
_STAGE_13_RANK: Final[int] = 13
_STAGE_14_RANK: Final[int] = 14
_STAGE_15_RANK: Final[int] = 15
_STAGE_16_RANK: Final[int] = 16
_STAGE_17_RANK: Final[int] = 17
_STAGE_18_RANK: Final[int] = 18

# Frozen semantic region tokens (Section 18 of the brief).
_WINDOW_REGION_SEMANTICS: Final[str] = _t024.WINDOW_REGION_SEMANTICS
_BAFFLE_COVERED_REGION_SEMANTICS: Final[str] = _t024.BAFFLE_COVERED_REGION_SEMANTICS
_CROSSFLOW_REFERENCE_REGION_SEMANTICS: Final[str] = _t024.CROSSFLOW_REFERENCE_REGION_SEMANTICS

# Orientation unit vectors and chord-half-plane offsets.
_ORIENTATION_NORMAL_TOP: Final[tuple[int, int]] = (0, 1)
_ORIENTATION_NORMAL_BOTTOM: Final[tuple[int, int]] = (0, -1)
_ORIENTATION_NORMAL_RIGHT: Final[tuple[int, int]] = (1, 0)
_ORIENTATION_NORMAL_LEFT: Final[tuple[int, int]] = (-1, 0)


def _local_decimal_context() -> decimal.Context:
    """Build a fresh :class:`decimal.Context` from frozen constants.

    The context is constructed locally on every call so that no global
    context mutation can leak into or out of this module.
    """
    return decimal.Context(prec=_DECIMAL_PRECISION, rounding=decimal.ROUND_HALF_EVEN)


def _parse_decimal_field(value: str) -> Decimal:
    """Parse a finite canonical decimal string under the frozen context."""
    canonical = _t024_canonical.canonical_decimal_string(value)
    with decimal.localcontext(_local_decimal_context()):
        return Decimal(canonical)


def _quantize_coordinate(value: Decimal) -> str:
    """Quantize an unquantized Decimal coordinate to the public string."""
    with decimal.localcontext(_local_decimal_context()):
        quantized = value.quantize(_COORDINATE_QUANTUM)
    return _t024_canonical.canonical_decimal_string(quantized)


def _quantize_squared(value: Decimal) -> str:
    """Quantize an unquantized squared Decimal to the public string."""
    with decimal.localcontext(_local_decimal_context()):
        quantized = value.quantize(_SQUARED_COORDINATE_QUANTUM)
    return _t024_canonical.canonical_decimal_string(quantized)


# ---------------------------------------------------------------------------
# Module-private result types (Section 6.3 + 9).
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _CutChordFoundation:
    """Module-private cut-chord geometry result."""

    normal_x: int
    normal_y: int
    half_plane_offset_m: Decimal
    chord_half_length_m: Decimal
    endpoint_a_x_m: Decimal
    endpoint_a_y_m: Decimal
    endpoint_b_x_m: Decimal
    endpoint_b_y_m: Decimal


@dataclass(frozen=True, slots=True)
class _PlaneClassificationFoundation:
    """Module-private per-plane classification aggregation result.

    Holds the unquantized :class:`Decimal` margins and position lists
    produced by Stages 14 / 15 / 16. The public projection lives on
    :class:`_BafflePlaneFoundation`.
    """

    classifications: tuple[_t024.TubeHoleClassification, ...]
    window_position_ids: tuple[str, ...]
    crossflow_reference_position_ids: tuple[str, ...]
    outer_tangent_position_ids: tuple[str, ...]
    pairwise_tangent_position_pairs: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class _BafflePlaneFoundation:
    """Module-private per-baffle plane foundation (Section 9)."""

    baffle_index: int
    center_coordinate_m: str
    occupied_start_coordinate_m: str
    occupied_end_coordinate_m: str
    orientation: _t024.BaffleOrientation
    cut_chord: _CutChordFoundation
    window_region_semantics: str
    baffle_covered_region_semantics: str
    crossflow_reference_region_semantics: str
    classifications: _PlaneClassificationFoundation


@dataclass(frozen=True, slots=True)
class _GeometryFoundation:
    """Module-private complete geometry foundation (Section 9)."""

    usable_baffle_span_m: str
    baffle_diameter_m: str
    baffle_radius_m: str
    baffle_hole_diameter_m: str
    baffle_hole_radius_m: str
    cut_height_m: str
    chord_offset_from_center_m: str
    baffle_planes: tuple[_BafflePlaneFoundation, ...]
    position_count: int


@dataclass(frozen=True, slots=True)
class _RankedMessage:
    """Module-private record binding a message to its stage rank."""

    validation_stage_rank: int
    entry: _t024.MessageEntry


@dataclass(frozen=True, slots=True)
class _GeometryFoundationResult:
    """Module-private result of the Round-5 geometry foundation.

    Not exported. Not part of the public canonical projection. Used by
    a later ``validation.py`` to assemble a public result.
    """

    geometry: _GeometryFoundation | None
    completed_stage_rank: int
    warnings: tuple[_t024.MessageEntry, ...]
    blockers: tuple[_t024.MessageEntry, ...]


# ---------------------------------------------------------------------------
# Internal helpers -- message construction and ordering.
# ---------------------------------------------------------------------------


def _make_message(
    code: str,
    *,
    field_path: str | None,
    message_key: str,
    evidence_refs: tuple[str, ...] = (),
    details: tuple[tuple[str, str], ...] = (),
) -> _t024.MessageEntry:
    """Build a frozen :class:`MessageEntry` with literal-string projection."""
    return _t024.MessageEntry(
        code=code,
        field_path=field_path,
        message_key=message_key,
        evidence_refs=tuple(evidence_refs),
        details=tuple(details),
    )


def _rank_blocker(stage_rank: int, entry: _t024.MessageEntry) -> _RankedMessage:
    return _RankedMessage(validation_stage_rank=stage_rank, entry=entry)


def _rank_warning(stage_rank: int, entry: _t024.MessageEntry) -> _RankedMessage:
    return _RankedMessage(validation_stage_rank=stage_rank, entry=entry)


def _details_sort_key(details: tuple[tuple[str, str], ...]) -> str:
    return _t024_canonical.canonical_json_bytes([list(pair) for pair in details]).decode("ascii")


def _evidence_refs_sort_key(evidence_refs: tuple[str, ...]) -> str:
    return _t024_canonical.canonical_json_bytes(list(evidence_refs)).decode("ascii")


def _global_sort_key(ranked: _RankedMessage) -> tuple[int, str, str, str, str, str]:
    entry = ranked.entry
    details_key = _details_sort_key(entry.details)
    evidence_key = _evidence_refs_sort_key(entry.evidence_refs)
    field_path = entry.field_path if entry.field_path is not None else ""
    return (
        ranked.validation_stage_rank,
        entry.code,
        field_path,
        entry.message_key,
        details_key,
        evidence_key,
    )


def _sort_messages(
    messages: tuple[_RankedMessage, ...],
) -> tuple[_RankedMessage, ...]:
    return tuple(sorted(messages, key=_global_sort_key))


def _freeze_blockers(
    ranked: tuple[_RankedMessage, ...],
) -> tuple[_t024.MessageEntry, ...]:
    return tuple(ranked_msg.entry for ranked_msg in _sort_messages(ranked))


def _freeze_warnings(
    ranked: tuple[_RankedMessage, ...] | list[_RankedMessage],
) -> tuple[_t024.MessageEntry, ...]:
    return tuple(ranked_msg.entry for ranked_msg in _sort_messages(tuple(ranked)))


# ---------------------------------------------------------------------------
# Stage 9 -- Decimal lexical canonicalization and signed-domain validation.
# ---------------------------------------------------------------------------


def _stage9_parse(
    request: _t024.BaffleGeometryRequest,
) -> tuple[
    tuple[_RankedMessage, ...],
    dict[str, Any] | None,
]:
    """Stage 9: parse and validate every Decimal input."""
    blockers: list[_RankedMessage] = []

    authority = request.design_authority
    axial = request.axial_span
    shell_bundle_geometry = request.shell_bundle_geometry
    tube_layout = request.tube_layout

    shell_inside_diameter_raw: str | None = getattr(
        shell_bundle_geometry, "shell_inside_diameter_m", None
    )
    tube_outer_diameter_raw: str | None = None
    tube_geometry = getattr(tube_layout, "tube_geometry", None)
    if tube_geometry is not None:
        tube_outer_diameter_raw = getattr(tube_geometry, "outer_diameter_m", None)
    positions_raw: tuple[tuple[str, str, str], ...] = tuple(
        (p.position_id, p.x_m, p.y_m) for p in tube_layout.positions
    )

    if shell_inside_diameter_raw is None:
        blockers.append(
            _rank_blocker(
                _STAGE_9_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
                    field_path="shell_bundle_geometry.shell_inside_diameter_m",
                    message_key="shell_inside_diameter_missing",
                ),
            )
        )
    if tube_outer_diameter_raw is None:
        blockers.append(
            _rank_blocker(
                _STAGE_9_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
                    field_path="tube_layout.tube_geometry.outer_diameter_m",
                    message_key="tube_outer_diameter_missing",
                ),
            )
        )
    if blockers:
        return tuple(blockers), None

    parsed: dict[str, Any] = {
        "axial_start": None,
        "axial_end": None,
        "baffle_thickness": None,
        "baffle_cut_fraction": None,
        "shell_to_baffle_clearance": None,
        "tube_to_baffle_hole_clearance": None,
        "shell_inside_diameter": None,
        "tube_outer_diameter": None,
        "spacing_sequence": (),
        "positions": (),
    }

    def _parse_into(raw: str, field_path: str, blocker_code: str) -> Decimal | None:
        try:
            return _parse_decimal_field(raw)
        except ValueError:
            blockers.append(
                _rank_blocker(
                    _STAGE_9_RANK,
                    _make_message(
                        blocker_code,
                        field_path=field_path,
                        message_key="decimal_lexical_invalid",
                        details=(("raw", raw),),
                    ),
                )
            )
            return None

    axial_start = _parse_into(
        axial.axial_start_coordinate_m,
        "axial_span.axial_start_coordinate_m",
        _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
    )
    axial_end = _parse_into(
        axial.axial_end_coordinate_m,
        "axial_span.axial_end_coordinate_m",
        _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
    )
    baffle_thickness = _parse_into(
        authority.baffle_thickness_m,
        "design_authority.baffle_thickness_m",
        _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
    )
    baffle_cut_fraction = _parse_into(
        authority.baffle_cut_fraction,
        "design_authority.baffle_cut_fraction",
        _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
    )
    shell_to_baffle_clearance = _parse_into(
        authority.shell_to_baffle_diametral_clearance_m,
        "design_authority.shell_to_baffle_diametral_clearance_m",
        _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
    )
    tube_to_baffle_hole_clearance = _parse_into(
        authority.tube_to_baffle_hole_diametral_clearance_m,
        "design_authority.tube_to_baffle_hole_diametral_clearance_m",
        _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
    )
    shell_inside_diameter = _parse_into(
        cast(str, shell_inside_diameter_raw),
        "shell_bundle_geometry.shell_inside_diameter_m",
        _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
    )
    tube_outer_diameter = _parse_into(
        cast(str, tube_outer_diameter_raw),
        "tube_layout.tube_geometry.outer_diameter_m",
        _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
    )

    spacing_sequence: list[Decimal] = []
    for idx, raw in enumerate(authority.spacing_sequence_m):
        spacing_value = _parse_into(
            raw,
            f"design_authority.spacing_sequence_m[{idx}]",
            _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
        )
        if spacing_value is None:
            continue
        spacing_sequence.append(spacing_value)

    positions_parsed: list[tuple[str, Decimal, Decimal]] = []
    for position_id, x_raw, y_raw in positions_raw:
        x_value = _parse_into(
            x_raw,
            f"tube_layout.positions[position_id={position_id}].x_m",
            _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
        )
        y_value = _parse_into(
            y_raw,
            f"tube_layout.positions[position_id={position_id}].y_m",
            _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
        )
        if x_value is None or y_value is None:
            continue
        positions_parsed.append((position_id, x_value, y_value))

    # Domain rules (Section 9.8 of the design contract).
    if axial_start is not None and axial_end is not None and axial_end <= axial_start:
        blockers.append(
            _rank_blocker(
                _STAGE_9_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_AXIAL_SPAN_INVALID.value,
                    field_path="axial_span",
                    message_key="axial_end_not_strictly_above_axial_start",
                    details=(
                        (
                            "axial_start",
                            _t024_canonical.canonical_decimal_string(axial_start),
                        ),
                        (
                            "axial_end",
                            _t024_canonical.canonical_decimal_string(axial_end),
                        ),
                    ),
                ),
            )
        )

    if baffle_thickness is not None and baffle_thickness <= _CANONICAL_ZERO:
        blockers.append(
            _rank_blocker(
                _STAGE_9_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_BAFFLE_THICKNESS_INVALID.value,
                    field_path="design_authority.baffle_thickness_m",
                    message_key="baffle_thickness_non_positive",
                    details=(
                        (
                            "baffle_thickness_m",
                            _t024_canonical.canonical_decimal_string(baffle_thickness),
                        ),
                    ),
                ),
            )
        )

    for idx, value in enumerate(spacing_sequence):
        if value <= _CANONICAL_ZERO:
            blockers.append(
                _rank_blocker(
                    _STAGE_9_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_SPACING_VALUE_INVALID.value,
                        field_path=f"design_authority.spacing_sequence_m[{idx}]",
                        message_key="spacing_value_non_positive",
                        details=(
                            (
                                "spacing_value",
                                _t024_canonical.canonical_decimal_string(value),
                            ),
                        ),
                    ),
                )
            )

    if baffle_cut_fraction is not None and (
        baffle_cut_fraction <= _CANONICAL_ZERO or baffle_cut_fraction >= _ONE
    ):
        blockers.append(
            _rank_blocker(
                _STAGE_9_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_BAFFLE_CUT_INVALID.value,
                    field_path="design_authority.baffle_cut_fraction",
                    message_key="baffle_cut_fraction_out_of_open_unit_interval",
                    details=(
                        (
                            "baffle_cut_fraction",
                            _t024_canonical.canonical_decimal_string(baffle_cut_fraction),
                        ),
                    ),
                ),
            )
        )

    if shell_to_baffle_clearance is not None and shell_to_baffle_clearance < _CANONICAL_ZERO:
        blockers.append(
            _rank_blocker(
                _STAGE_9_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_SHELL_TO_BAFFLE_CLEARANCE_INVALID.value,
                    field_path="design_authority.shell_to_baffle_diametral_clearance_m",
                    message_key="shell_to_baffle_clearance_negative",
                    details=(
                        (
                            "shell_to_baffle_clearance_m",
                            _t024_canonical.canonical_decimal_string(shell_to_baffle_clearance),
                        ),
                    ),
                ),
            )
        )

    if (
        tube_to_baffle_hole_clearance is not None
        and tube_to_baffle_hole_clearance < _CANONICAL_ZERO
    ):
        blockers.append(
            _rank_blocker(
                _STAGE_9_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TUBE_TO_BAFFLE_HOLE_CLEARANCE_INVALID.value,
                    field_path="design_authority.tube_to_baffle_hole_diametral_clearance_m",
                    message_key="tube_to_baffle_hole_clearance_negative",
                    details=(
                        (
                            "tube_to_baffle_hole_clearance_m",
                            _t024_canonical.canonical_decimal_string(tube_to_baffle_hole_clearance),
                        ),
                    ),
                ),
            )
        )

    if shell_inside_diameter is not None and shell_inside_diameter <= _CANONICAL_ZERO:
        blockers.append(
            _rank_blocker(
                _STAGE_9_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
                    field_path="shell_bundle_geometry.shell_inside_diameter_m",
                    message_key="shell_inside_diameter_non_positive",
                    details=(
                        (
                            "shell_inside_diameter_m",
                            _t024_canonical.canonical_decimal_string(shell_inside_diameter),
                        ),
                    ),
                ),
            )
        )

    if tube_outer_diameter is not None and tube_outer_diameter <= _CANONICAL_ZERO:
        blockers.append(
            _rank_blocker(
                _STAGE_9_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value,
                    field_path="tube_layout.tube_geometry.outer_diameter_m",
                    message_key="tube_outer_diameter_non_positive",
                    details=(
                        (
                            "tube_outer_diameter_m",
                            _t024_canonical.canonical_decimal_string(tube_outer_diameter),
                        ),
                    ),
                ),
            )
        )

    if blockers:
        return tuple(blockers), None

    parsed["axial_start"] = axial_start
    parsed["axial_end"] = axial_end
    parsed["baffle_thickness"] = baffle_thickness
    parsed["baffle_cut_fraction"] = baffle_cut_fraction
    parsed["shell_to_baffle_clearance"] = shell_to_baffle_clearance
    parsed["tube_to_baffle_hole_clearance"] = tube_to_baffle_hole_clearance
    parsed["shell_inside_diameter"] = shell_inside_diameter
    parsed["tube_outer_diameter"] = tube_outer_diameter
    parsed["spacing_sequence"] = tuple(spacing_sequence)
    parsed["positions"] = tuple(positions_parsed)
    return tuple(blockers), parsed


# ---------------------------------------------------------------------------
# Stage 10 -- Count, cardinality and exact axial closure.
# ---------------------------------------------------------------------------


def _stage10_validate(
    request: _t024.BaffleGeometryRequest,
    parsed: dict[str, Any],
) -> tuple[
    tuple[_RankedMessage, ...],
    int | None,
    tuple[Decimal, ...] | None,
]:
    """Stage 10: count / cardinality / exact closure validation."""
    blockers: list[_RankedMessage] = []

    authority = request.design_authority
    baffle_count_raw = authority.baffle_count
    baffle_count: int | None = None
    if type(baffle_count_raw) is not int or isinstance(baffle_count_raw, bool):
        blockers.append(
            _rank_blocker(
                _STAGE_10_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_BAFFLE_COUNT_INVALID.value,
                    field_path="design_authority.baffle_count",
                    message_key="baffle_count_not_strict_int",
                    details=(("actual_type", type(baffle_count_raw).__name__),),
                ),
            )
        )
    elif baffle_count_raw < 1:
        blockers.append(
            _rank_blocker(
                _STAGE_10_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_BAFFLE_COUNT_INVALID.value,
                    field_path="design_authority.baffle_count",
                    message_key="baffle_count_below_one",
                    details=(("baffle_count", str(baffle_count_raw)),),
                ),
            )
        )
    else:
        baffle_count = baffle_count_raw

    spacing: tuple[Decimal, ...] = parsed["spacing_sequence"]
    expected_spacing_length = (baffle_count + 1) if baffle_count is not None else None
    if expected_spacing_length is not None and len(spacing) != expected_spacing_length:
        blockers.append(
            _rank_blocker(
                _STAGE_10_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_SPACING_SEQUENCE_CARDINALITY_MISMATCH.value,
                    field_path="design_authority.spacing_sequence_m",
                    message_key="spacing_sequence_cardinality_mismatch",
                    details=(
                        ("expected_length", str(expected_spacing_length)),
                        ("actual_length", str(len(spacing))),
                    ),
                ),
            )
        )

    orientation: tuple[_t024.BaffleOrientation, ...] = tuple(authority.orientation_sequence)
    expected_orientation_length = baffle_count if baffle_count is not None else None
    if expected_orientation_length is not None and len(orientation) != expected_orientation_length:
        blockers.append(
            _rank_blocker(
                _STAGE_10_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_ORIENTATION_SEQUENCE_CARDINALITY_MISMATCH.value,
                    field_path="design_authority.orientation_sequence",
                    message_key="orientation_sequence_cardinality_mismatch",
                    details=(
                        ("expected_length", str(expected_orientation_length)),
                        ("actual_length", str(len(orientation))),
                    ),
                ),
            )
        )

    axial_start: Decimal = parsed["axial_start"]
    axial_end: Decimal = parsed["axial_end"]
    with decimal.localcontext(_local_decimal_context()):
        usable_span = axial_end - axial_start
        spacing_sum: Decimal = sum(spacing, _CANONICAL_ZERO)
        if spacing_sum != usable_span:
            blockers.append(
                _rank_blocker(
                    _STAGE_10_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_SPACING_SEQUENCE_SPAN_MISMATCH.value,
                        field_path="design_authority.spacing_sequence_m",
                        message_key="spacing_sequence_span_mismatch",
                        details=(
                            (
                                "spacing_sum",
                                _t024_canonical.canonical_decimal_string(spacing_sum),
                            ),
                            (
                                "usable_span",
                                _t024_canonical.canonical_decimal_string(usable_span),
                            ),
                        ),
                    ),
                )
            )

    if blockers or baffle_count is None:
        return tuple(blockers), None, None

    # Compute the center-plane coordinates (z_i) under the frozen context.
    with decimal.localcontext(_local_decimal_context()):
        center_planes: list[Decimal] = []
        first = axial_start + spacing[0]
        center_planes.append(first)
        for i in range(1, baffle_count):
            center_planes.append(center_planes[-1] + spacing[i])

    return tuple(blockers), baffle_count, tuple(center_planes)


# ---------------------------------------------------------------------------
# Stage 11 -- Derived diameters / radii / cut height / chord offset.
# ---------------------------------------------------------------------------


def _stage11_derive(
    parsed: dict[str, Any],
) -> tuple[
    tuple[_RankedMessage, ...],
    dict[str, Decimal] | None,
]:
    """Stage 11: derived diameters / radii / cut geometry."""
    blockers: list[_RankedMessage] = []

    shell_inside_diameter: Decimal = parsed["shell_inside_diameter"]
    tube_outer_diameter: Decimal = parsed["tube_outer_diameter"]
    shell_to_baffle_clearance: Decimal = parsed["shell_to_baffle_clearance"]
    tube_to_baffle_hole_clearance: Decimal = parsed["tube_to_baffle_hole_clearance"]
    baffle_cut_fraction: Decimal = parsed["baffle_cut_fraction"]

    with decimal.localcontext(_local_decimal_context()):
        baffle_diameter = shell_inside_diameter - shell_to_baffle_clearance
        baffle_hole_diameter = tube_outer_diameter + tube_to_baffle_hole_clearance
        baffle_radius = baffle_diameter / _TWO
        baffle_hole_radius = baffle_hole_diameter / _TWO
        physical_tube_radius = tube_outer_diameter / _TWO
        cut_height = baffle_cut_fraction * baffle_diameter
        chord_offset_from_center = baffle_radius - cut_height

    if baffle_diameter <= _CANONICAL_ZERO:
        blockers.append(
            _rank_blocker(
                _STAGE_11_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_BAFFLE_DIAMETER_INVALID.value,
                    field_path="baffle_diameter_m",
                    message_key="baffle_diameter_non_positive",
                    details=(
                        (
                            "baffle_diameter_m",
                            _t024_canonical.canonical_decimal_string(baffle_diameter),
                        ),
                    ),
                ),
            )
        )

    if baffle_hole_diameter < tube_outer_diameter:
        blockers.append(
            _rank_blocker(
                _STAGE_11_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_BAFFLE_HOLE_DIAMETER_INVALID.value,
                    field_path="baffle_hole_diameter_m",
                    message_key="baffle_hole_diameter_below_tube_outer_diameter",
                    details=(
                        (
                            "baffle_hole_diameter_m",
                            _t024_canonical.canonical_decimal_string(baffle_hole_diameter),
                        ),
                        (
                            "tube_outer_diameter_m",
                            _t024_canonical.canonical_decimal_string(tube_outer_diameter),
                        ),
                    ),
                ),
            )
        )

    if blockers:
        return tuple(blockers), None

    derived: dict[str, Decimal] = {
        "baffle_diameter": baffle_diameter,
        "baffle_hole_diameter": baffle_hole_diameter,
        "baffle_radius": baffle_radius,
        "baffle_hole_radius": baffle_hole_radius,
        "physical_tube_radius": physical_tube_radius,
        "cut_height": cut_height,
        "chord_offset_from_center": chord_offset_from_center,
    }
    return tuple(blockers), derived


# ---------------------------------------------------------------------------
# Stage 12 -- Center planes and solid intervals.
# ---------------------------------------------------------------------------


def _stage12_solids(
    request: _t024.BaffleGeometryRequest,
    parsed: dict[str, Any],
    baffle_count: int,
    center_planes: tuple[Decimal, ...],
) -> tuple[
    tuple[_RankedMessage, ...],
    tuple[_RankedMessage, ...],
    tuple[tuple[Decimal, Decimal, Decimal], ...] | None,
]:
    """Stage 12: solid intervals and aggregate tangency warning."""
    blockers: list[_RankedMessage] = []
    warnings: list[_RankedMessage] = []

    axial_start: Decimal = parsed["axial_start"]
    axial_end: Decimal = parsed["axial_end"]
    baffle_thickness: Decimal = parsed["baffle_thickness"]

    intervals: list[tuple[Decimal, Decimal, Decimal]] = []
    with decimal.localcontext(_local_decimal_context()):
        half_thickness = baffle_thickness / _TWO
        for z_i in center_planes:
            occupied_start = z_i - half_thickness
            occupied_end = z_i + half_thickness
            intervals.append((z_i, occupied_start, occupied_end))

        first_occupied_start = intervals[0][1]
        last_occupied_end = intervals[-1][2]

        if first_occupied_start < axial_start:
            blockers.append(
                _rank_blocker(
                    _STAGE_12_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_BAFFLE_THICKNESS_OUTSIDE_ACTIVE_SPAN.value,
                        field_path="baffle_planes[0].occupied_start_coordinate_m",
                        message_key="first_baffle_occupied_start_below_axial_start",
                        details=(
                            (
                                "first_occupied_start_m",
                                _t024_canonical.canonical_decimal_string(first_occupied_start),
                            ),
                            (
                                "axial_start_m",
                                _t024_canonical.canonical_decimal_string(axial_start),
                            ),
                        ),
                    ),
                )
            )

        if last_occupied_end > axial_end:
            blockers.append(
                _rank_blocker(
                    _STAGE_12_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_BAFFLE_THICKNESS_OUTSIDE_ACTIVE_SPAN.value,
                        field_path=f"baffle_planes[{baffle_count - 1}].occupied_end_coordinate_m",
                        message_key="last_baffle_occupied_end_above_axial_end",
                        details=(
                            (
                                "last_occupied_end_m",
                                _t024_canonical.canonical_decimal_string(last_occupied_end),
                            ),
                            (
                                "axial_end_m",
                                _t024_canonical.canonical_decimal_string(axial_end),
                            ),
                        ),
                    ),
                )
            )

        boundary_contacts: list[str] = []
        adjacent_pairs: list[tuple[int, int]] = []

        if first_occupied_start == axial_start:
            boundary_contacts.append("FIRST_BAFFLE_START")
        if last_occupied_end == axial_end:
            boundary_contacts.append("LAST_BAFFLE_END")

        for i in range(baffle_count - 1):
            current_end = intervals[i][2]
            next_start = intervals[i + 1][1]
            if current_end > next_start:
                blockers.append(
                    _rank_blocker(
                        _STAGE_12_RANK,
                        _make_message(
                            _t024.BlockerCode.BFG_BAFFLE_SOLIDS_OVERLAP.value,
                            field_path=f"baffle_planes[{i}].occupied_end_coordinate_m",
                            message_key="adjacent_baffle_solids_overlap",
                            details=(
                                ("lower_index", str(i)),
                                ("upper_index", str(i + 1)),
                                (
                                    "lower_occupied_end_m",
                                    _t024_canonical.canonical_decimal_string(current_end),
                                ),
                                (
                                    "upper_occupied_start_m",
                                    _t024_canonical.canonical_decimal_string(next_start),
                                ),
                            ),
                        ),
                    )
                )
            elif current_end == next_start:
                adjacent_pairs.append((i, i + 1))

    if blockers:
        return tuple(blockers), tuple(warnings), None

    if boundary_contacts or adjacent_pairs:
        warnings.append(
            _rank_warning(
                _STAGE_12_RANK,
                _make_message(
                    _t024.WarningCode.BFG_BAFFLE_SOLID_TANGENCY_NOT_MANUFACTURING_ADEQUACY.value,
                    field_path="baffle_planes",
                    message_key="baffle_solid_tangency_not_manufacturing_adequacy",
                    evidence_refs=request.evidence_refs,
                    details=(
                        (
                            "active_span_boundary_contacts",
                            "|".join(boundary_contacts),
                        ),
                        (
                            "adjacent_baffle_index_pairs",
                            "|".join(f"({lower},{higher})" for (lower, higher) in adjacent_pairs),
                        ),
                    ),
                ),
            )
        )

    return tuple(blockers), tuple(warnings), tuple(intervals)


# ---------------------------------------------------------------------------
# Stage 13 -- Single-segment cut chord construction (Decimal sqrt).
# ---------------------------------------------------------------------------


def _orientation_unit(orientation: _t024.BaffleOrientation) -> tuple[int, int]:
    if orientation is _t024.BaffleOrientation.TOP:
        return _ORIENTATION_NORMAL_TOP
    if orientation is _t024.BaffleOrientation.BOTTOM:
        return _ORIENTATION_NORMAL_BOTTOM
    if orientation is _t024.BaffleOrientation.RIGHT:
        return _ORIENTATION_NORMAL_RIGHT
    if orientation is _t024.BaffleOrientation.LEFT:
        return _ORIENTATION_NORMAL_LEFT
    raise ValueError("unreachable orientation enum")


def _stage13_chord(
    derived: dict[str, Decimal],
    orientation: _t024.BaffleOrientation,
) -> tuple[tuple[_RankedMessage, ...], _CutChordFoundation | None]:
    """Stage 13: build the cut chord for one baffle."""
    blockers: list[_RankedMessage] = []

    baffle_radius: Decimal = derived["baffle_radius"]
    chord_offset: Decimal = derived["chord_offset_from_center"]
    normal = _orientation_unit(orientation)
    normal_x, normal_y = normal

    with decimal.localcontext(_local_decimal_context()):
        try:
            chord_half_length_squared = baffle_radius * baffle_radius - chord_offset * chord_offset
            if chord_half_length_squared < _CANONICAL_ZERO:
                blockers.append(
                    _rank_blocker(
                        _STAGE_13_RANK,
                        _make_message(
                            _t024.BlockerCode.BFG_CHORD_CALCULATION_FAILED.value,
                            field_path="cut_chord.chord_half_length_m",
                            message_key="chord_half_length_squared_negative",
                            details=(
                                (
                                    "chord_half_length_squared_m2",
                                    _t024_canonical.canonical_decimal_string(
                                        chord_half_length_squared
                                    ),
                                ),
                            ),
                        ),
                    )
                )
                return tuple(blockers), None
            chord_half_length = chord_half_length_squared.sqrt()
        except decimal.InvalidOperation:  # pragma: no cover - guarded
            blockers.append(
                _rank_blocker(
                    _STAGE_13_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_CHORD_CALCULATION_FAILED.value,
                        field_path="cut_chord.chord_half_length_m",
                        message_key="decimal_sqrt_failed",
                    ),
                )
            )
            return tuple(blockers), None

        if normal_x == 0:
            endpoint_a_x = -chord_half_length
            endpoint_b_x = chord_half_length
            endpoint_a_y = chord_offset * Decimal(normal_y)
            endpoint_b_y = endpoint_a_y
        else:
            endpoint_a_y = -chord_half_length
            endpoint_b_y = chord_half_length
            endpoint_a_x = chord_offset * Decimal(normal_x)
            endpoint_b_x = endpoint_a_x

    chord = _CutChordFoundation(
        normal_x=normal_x,
        normal_y=normal_y,
        half_plane_offset_m=chord_offset,
        chord_half_length_m=chord_half_length,
        endpoint_a_x_m=endpoint_a_x,
        endpoint_a_y_m=endpoint_a_y,
        endpoint_b_x_m=endpoint_b_x,
        endpoint_b_y_m=endpoint_b_y,
    )
    return tuple(blockers), chord


# ---------------------------------------------------------------------------
# Stage 14 + 15 + 16 -- per-plane classification and containment.
# ---------------------------------------------------------------------------


def _classify_position_against_chord(
    *,
    position_id: str,
    x_m: Decimal,
    y_m: Decimal,
    chord: _CutChordFoundation,
    baffle_hole_radius: Decimal,
    physical_tube_radius: Decimal,
) -> tuple[
    _t024.TubeRegionClassification | None,
    Decimal,
    Decimal,
    tuple[_RankedMessage, ...],
]:
    """Stage 14: classify a single position relative to one baffle chord.

    Returns ``(classification_or_none, signed_window_distance,
    cut_boundary_margin, blockers)``. ``classification_or_none`` is
    ``None`` iff any Stage-14 blocker was produced.
    """
    blockers: list[_RankedMessage] = []
    with decimal.localcontext(_local_decimal_context()):
        signed_window_distance = (
            Decimal(chord.normal_x) * x_m
            + Decimal(chord.normal_y) * y_m
            - chord.half_plane_offset_m
        )
        cut_boundary_margin = signed_window_distance - baffle_hole_radius

        if cut_boundary_margin > _CANONICAL_ZERO:
            classification: _t024.TubeRegionClassification = _t024.TubeRegionClassification.WINDOW
        elif cut_boundary_margin < -baffle_hole_radius:
            classification = _t024.TubeRegionClassification.CROSSFLOW_REFERENCE
        elif cut_boundary_margin == _CANONICAL_ZERO:
            classification = _t024.TubeRegionClassification.CROSSFLOW_REFERENCE
            blockers.append(
                _rank_blocker(
                    _STAGE_14_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_BAFFLE_HOLE_DISK_TANGENT_TO_CUT_BOUNDARY.value,
                        field_path=f"tube_hole_classifications[position_id={position_id}]",
                        message_key="baffle_hole_disk_tangent_to_cut_boundary_positive_side",
                        details=(
                            ("position_id", position_id),
                            (
                                "cut_boundary_margin_m",
                                _t024_canonical.canonical_decimal_string(cut_boundary_margin),
                            ),
                        ),
                    ),
                )
            )
            return None, signed_window_distance, cut_boundary_margin, tuple(blockers)
        elif cut_boundary_margin == -baffle_hole_radius:
            classification = _t024.TubeRegionClassification.CROSSFLOW_REFERENCE
            blockers.append(
                _rank_blocker(
                    _STAGE_14_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_BAFFLE_HOLE_DISK_TANGENT_TO_CUT_BOUNDARY.value,
                        field_path=f"tube_hole_classifications[position_id={position_id}]",
                        message_key="baffle_hole_disk_tangent_to_cut_boundary_negative_side",
                        details=(
                            ("position_id", position_id),
                            (
                                "cut_boundary_margin_m",
                                _t024_canonical.canonical_decimal_string(cut_boundary_margin),
                            ),
                        ),
                    ),
                )
            )
            return None, signed_window_distance, cut_boundary_margin, tuple(blockers)
        else:
            classification = _t024.TubeRegionClassification.CROSSFLOW_REFERENCE
            blockers.append(
                _rank_blocker(
                    _STAGE_14_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_BAFFLE_HOLE_DISK_INTERSECTS_CUT_BOUNDARY.value,
                        field_path=f"tube_hole_classifications[position_id={position_id}]",
                        message_key="baffle_hole_disk_intersects_cut_boundary",
                        details=(
                            ("position_id", position_id),
                            (
                                "cut_boundary_margin_m",
                                _t024_canonical.canonical_decimal_string(cut_boundary_margin),
                            ),
                        ),
                    ),
                )
            )
            return None, signed_window_distance, cut_boundary_margin, tuple(blockers)

    return classification, signed_window_distance, cut_boundary_margin, tuple(blockers)


def _outer_containment_check(
    *,
    position_id: str,
    x_m: Decimal,
    y_m: Decimal,
    baffle_hole_radius: Decimal,
    baffle_radius: Decimal,
) -> tuple[bool, Decimal]:
    """Stage 15: outer-circle containment check for one WINDOW or CROSSFLOW
    classification.

    Returns ``(inside_ok, outer_boundary_margin_squared)``. ``inside_ok``
    is ``True`` iff ``d^2 < (R - r_h)^2`` (strictly inside) or
    ``d^2 == (R - r_h)^2`` (exact outer tangency accepted as
    inside-acceptable). All arithmetic is in the unquantized
    precision-50 ``ROUND_HALF_EVEN`` context.
    """
    with decimal.localcontext(_local_decimal_context()):
        d_squared = x_m * x_m + y_m * y_m
        available_radius = baffle_radius - baffle_hole_radius
        available_squared = available_radius * available_radius
        outer_margin_squared = available_squared - d_squared
        return d_squared <= available_squared, outer_margin_squared


def _covered_pair_overlap_check(
    *,
    lower_position_id: str,
    lower_x: Decimal,
    lower_y: Decimal,
    higher_position_id: str,
    higher_x: Decimal,
    higher_y: Decimal,
    baffle_hole_radius: Decimal,
) -> tuple[bool, Decimal]:
    """Stage 16: covered-hole pairwise non-overlap check.

    Returns ``(separable, d2_ij)``. ``separable`` is ``True`` iff the
    center-to-center squared distance is ``>= (2 * r_h)^2``.
    """
    with decimal.localcontext(_local_decimal_context()):
        dx = lower_x - higher_x
        dy = lower_y - higher_y
        d_squared = dx * dx + dy * dy
        minimum_center_distance = _TWO * baffle_hole_radius
        minimum_center_distance_squared = minimum_center_distance * minimum_center_distance
        return d_squared >= minimum_center_distance_squared, d_squared


def _process_one_baffle(
    request: _t024.BaffleGeometryRequest,
    *,
    baffle_index: int,
    orientation: _t024.BaffleOrientation,
    derived: dict[str, Decimal],
    parsed_positions: tuple[tuple[str, Decimal, Decimal], ...],
) -> tuple[
    tuple[_RankedMessage, ...],
    tuple[_RankedMessage, ...],
    _BafflePlaneFoundation | None,
    int,
]:
    """Process a single baffle through Stages 13 / 14 / 15 / 16.

    Returns ``(blockers, warnings, plane_or_none, last_completed_stage_rank)``.

    The ``last_completed_stage_rank`` is an **explicit tracker**: it starts
    at 12 (the last fully completed stage before the per-baffle loop
    started) and is only advanced *after* a per-baffle stage finishes
    without producing a blocker. When a blocker fires inside this
    function, the tracker is frozen at the last per-baffle stage that
    fully completed, and that frozen value is returned. Callers MUST
    NOT recompute it from blocker rank.
    """
    blockers: list[_RankedMessage] = []
    warnings: list[_RankedMessage] = []

    # Explicit per-baffle tracker. Advances 12 -> 13 -> 14 -> 15 -> 16
    # only after the corresponding stage fully completes. Frozen when
    # the first blocker fires; the frozen value is returned as the 4th
    # tuple element so the orchestrator never has to derive the last
    # completed stage from blocker metadata.
    per_baffle_completed: int = _STAGE_12_RANK

    chord_blockers, chord = _stage13_chord(derived, orientation)
    if chord_blockers or chord is None:
        blockers.extend(chord_blockers)
        return (
            tuple(blockers),
            tuple(warnings),
            None,
            per_baffle_completed,
        )
    per_baffle_completed = _STAGE_13_RANK

    baffle_radius = derived["baffle_radius"]
    baffle_hole_radius = derived["baffle_hole_radius"]
    physical_tube_radius = derived["physical_tube_radius"]

    classifications: list[_t024.TubeHoleClassification] = []
    window_ids: list[str] = []
    crossflow_ids: list[str] = []
    outer_tangent_ids: list[str] = []

    # Stage 14 + 15: per-position sweep. The explicit tracker
    # advances 13 -> 14 after Stage 14 succeeds for the current
    # position, and 14 -> 15 after Stage 15 succeeds for the current
    # position. To preserve the original "collect all blockers"
    # semantics, blockers from Stage 14 and Stage 15 do not early-
    # return; they ``continue`` so the loop can visit every position.
    # The tracker is **frozen at its value at the first blocker** and
    # must not advance past that point on subsequent blocker
    # positions, so that the returned tracker value reflects the
    # earliest stage at which any blocker fired.
    per_position_state: dict[str, tuple[_t024.TubeRegionClassification, Decimal, Decimal]] = {}
    sorted_positions = sorted(parsed_positions, key=lambda item: item[0])

    # Freeze flag: once any blocker has fired, do not advance the
    # explicit tracker past the value it had at the first blocker.
    tracker_frozen: bool = False
    # Saved value at the first blocker (when tracker_frozen was
    # set). All subsequent blocker positions leave the tracker at
    # this saved value.
    frozen_tracker: int = _STAGE_13_RANK

    for position_id, x_m, y_m in sorted_positions:
        (
            classification,
            signed_window_distance,
            cut_boundary_margin,
            pos_blockers,
        ) = _classify_position_against_chord(
            position_id=position_id,
            x_m=x_m,
            y_m=y_m,
            chord=chord,
            baffle_hole_radius=baffle_hole_radius,
            physical_tube_radius=physical_tube_radius,
        )
        if pos_blockers:
            blockers.extend(pos_blockers)
            if not tracker_frozen:
                frozen_tracker = per_baffle_completed
                tracker_frozen = True
            continue
        if tracker_frozen:
            # Tracker frozen by an earlier blocker; do not advance.
            continue
        if classification is None:
            # Stage 14 emitted no classification for this position
            # (degenerate case). The tracker stays at 13.
            continue

        # Stage 14 succeeded for this position: advance the explicit
        # tracker to 14 before Stage 15 runs.
        per_baffle_completed = _STAGE_14_RANK

        # Stage 15: outer containment.
        inside_ok, outer_margin_squared = _outer_containment_check(
            position_id=position_id,
            x_m=x_m,
            y_m=y_m,
            baffle_hole_radius=baffle_hole_radius,
            baffle_radius=baffle_radius,
        )
        if not inside_ok:
            blockers.append(
                _rank_blocker(
                    _STAGE_15_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_BAFFLE_HOLE_OUTSIDE_BAFFLE_DISK.value,
                        field_path=f"tube_hole_classifications[position_id={position_id}]",
                        message_key="baffle_hole_outside_baffle_disk",
                        details=(
                            ("position_id", position_id),
                            (
                                "outer_boundary_margin_squared_m2",
                                _t024_canonical.canonical_decimal_string(outer_margin_squared),
                            ),
                        ),
                    ),
                )
            )
            if not tracker_frozen:
                frozen_tracker = per_baffle_completed
                tracker_frozen = True
            continue

        is_outer_tangent = outer_margin_squared == _CANONICAL_ZERO

        audit = _t024.PhysicalTubeDiskAudit(
            physical_tube_radius_m=_t024_canonical.canonical_decimal_string(physical_tube_radius),
            signed_window_distance_m=_t024_canonical.canonical_decimal_string(
                signed_window_distance
            ),
            cut_boundary_margin_m=_t024_canonical.canonical_decimal_string(cut_boundary_margin),
            classification=classification,
        )

        classifications.append(
            _t024.TubeHoleClassification(
                position_id=position_id,
                center_x_m=_t024_canonical.canonical_decimal_string(x_m),
                center_y_m=_t024_canonical.canonical_decimal_string(y_m),
                physical_tube_radius_m=_t024_canonical.canonical_decimal_string(
                    physical_tube_radius
                ),
                baffle_hole_radius_m=_t024_canonical.canonical_decimal_string(baffle_hole_radius),
                signed_window_distance_m=_t024_canonical.canonical_decimal_string(
                    signed_window_distance
                ),
                cut_boundary_margin_m=_t024_canonical.canonical_decimal_string(cut_boundary_margin),
                classification=classification,
                outer_boundary_margin_squared_m2=_t024_canonical.canonical_decimal_string(
                    outer_margin_squared
                ),
                physical_tube_disk_audit=audit,
            )
        )

        if is_outer_tangent:
            outer_tangent_ids.append(position_id)

        if classification is _t024.TubeRegionClassification.WINDOW:
            window_ids.append(position_id)
        else:
            crossflow_ids.append(position_id)

        per_position_state[position_id] = (
            classification,
            x_m,
            y_m,
        )

        # Stage 15 succeeded for this position. Advance the explicit
        # tracker to 15.
        per_baffle_completed = _STAGE_15_RANK

    if blockers:
        # Per-baffle Stages 14 + 15 produced blockers. The explicit
        # tracker was frozen at the value it had at the first blocker;
        # the frozen value reflects the earliest stage at which any
        # blocker fired. We MUST NOT recompute it from blocker ranks.
        return (
            tuple(blockers),
            tuple(warnings),
            None,
            frozen_tracker,
        )

    # Stage 16: covered-region (CROSSFLOW_REFERENCE) pairwise overlap.
    crossflow_sorted = sorted(crossflow_ids)
    pairwise_tangent_pairs: list[tuple[str, str]] = []
    overlap_blockers: list[_RankedMessage] = []
    tangency_warnings: list[_RankedMessage] = []

    for i in range(len(crossflow_sorted)):
        for j in range(i + 1, len(crossflow_sorted)):
            lower_id = crossflow_sorted[i]
            higher_id = crossflow_sorted[j]
            _, lower_x, lower_y = per_position_state[lower_id]
            _, higher_x, higher_y = per_position_state[higher_id]
            separable, _d2 = _covered_pair_overlap_check(
                lower_position_id=lower_id,
                lower_x=lower_x,
                lower_y=lower_y,
                higher_position_id=higher_id,
                higher_x=higher_x,
                higher_y=higher_y,
                baffle_hole_radius=baffle_hole_radius,
            )
            if not separable:
                overlap_blockers.append(
                    _rank_blocker(
                        _STAGE_16_RANK,
                        _make_message(
                            _t024.BlockerCode.BFG_BAFFLE_HOLE_DISKS_OVERLAP.value,
                            field_path="pairwise_tangent_position_pairs",
                            message_key="baffle_hole_disks_overlap",
                            details=(
                                ("lower_position_id", lower_id),
                                ("higher_position_id", higher_id),
                            ),
                        ),
                    )
                )
            else:
                # Tangency case: re-check exact equality under Decimal.
                with decimal.localcontext(_local_decimal_context()):
                    dx = lower_x - higher_x
                    dy = lower_y - higher_y
                    d2 = dx * dx + dy * dy
                    minimum_center_distance = _TWO * baffle_hole_radius
                    minimum_squared = minimum_center_distance * minimum_center_distance
                if d2 == minimum_squared:
                    pairwise_tangent_pairs.append((lower_id, higher_id))

    if overlap_blockers:
        blockers.extend(overlap_blockers)

    if pairwise_tangent_pairs:
        tangency_warnings.append(
            _rank_warning(
                _STAGE_16_RANK,
                _make_message(
                    _t024.WarningCode.BFG_BAFFLE_HOLE_PAIR_TANGENCY_NOT_MANUFACTURING_ADEQUACY.value,
                    field_path="pairwise_tangent_position_pairs",
                    message_key="baffle_hole_pair_tangency_not_manufacturing_adequacy",
                    evidence_refs=request.evidence_refs,
                    details=(
                        (
                            "contacts",
                            "|".join(
                                f"({baffle_index},{lower_id},{higher_id})"
                                for lower_id, higher_id in sorted(pairwise_tangent_pairs)
                            ),
                        ),
                    ),
                ),
            )
        )

    if outer_tangent_ids:
        tangency_warnings.append(
            _rank_warning(
                _STAGE_15_RANK,
                _make_message(
                    _t024.WarningCode.BFG_BAFFLE_HOLE_OUTER_TANGENCY_NOT_MANUFACTURING_ADEQUACY.value,
                    field_path="tube_hole_classifications[*].outer_boundary_margin_squared_m2",
                    message_key="baffle_hole_outer_tangency_not_manufacturing_adequacy",
                    evidence_refs=request.evidence_refs,
                    details=(
                        (
                            "contacts",
                            "|".join(
                                f"({baffle_index},{pid})" for pid in sorted(outer_tangent_ids)
                            ),
                        ),
                    ),
                ),
            )
        )

    warnings.extend(tangency_warnings)

    if blockers:
        # Stage 16 produced blockers; the explicit tracker stays at 15
        # (the value it had after Stages 14 + 15 succeeded).
        return (
            tuple(blockers),
            tuple(warnings),
            None,
            per_baffle_completed,
        )

    # All four per-baffle stages completed without blockers. Advance
    # the explicit tracker to 16.
    per_baffle_completed = _STAGE_16_RANK

    classifications_tuple = tuple(classifications)
    classification_foundation = _PlaneClassificationFoundation(
        classifications=classifications_tuple,
        window_position_ids=tuple(window_ids),
        crossflow_reference_position_ids=tuple(crossflow_ids),
        outer_tangent_position_ids=tuple(outer_tangent_ids),
        pairwise_tangent_position_pairs=tuple(pairwise_tangent_pairs),
    )
    # Note: center / occupied coordinates are filled in by the orchestrator
    # from the Stage-12 intervals. We pass empty strings here as placeholders
    # for the per-baffle foundation.
    plane = _BafflePlaneFoundation(
        baffle_index=baffle_index,
        center_coordinate_m="0",
        occupied_start_coordinate_m="0",
        occupied_end_coordinate_m="0",
        orientation=orientation,
        cut_chord=chord,
        window_region_semantics=_WINDOW_REGION_SEMANTICS,
        baffle_covered_region_semantics=_BAFFLE_COVERED_REGION_SEMANTICS,
        crossflow_reference_region_semantics=_CROSSFLOW_REFERENCE_REGION_SEMANTICS,
        classifications=classification_foundation,
    )
    return (
        tuple(blockers),
        tuple(warnings),
        plane,
        per_baffle_completed,
    )


# ---------------------------------------------------------------------------
# Stage 17 -- Classification completeness.
# ---------------------------------------------------------------------------


def _stage17_completeness(
    parsed_positions: tuple[tuple[str, Decimal, Decimal], ...],
    planes: tuple[_BafflePlaneFoundation, ...],
) -> tuple[tuple[_RankedMessage, ...], tuple[str, ...]]:
    """Stage 17: every position_id must be classified exactly once per plane.

    The check is **per plane**. Each upstream ``position_id`` must appear
    exactly once in ``plane.classifications.classifications``. Position
    IDs that are missing from a plane, duplicated within a plane, or
    extra to the upstream set collectively trigger
    :attr:`BFG_POSITION_CLASSIFICATION_INCOMPLETE`.

    Returns ``(blockers, all_classified_position_ids)``. The returned
    tuple is the deterministic lexical-order union of classified IDs
    from ``planes``.
    """
    blockers: list[_RankedMessage] = []
    upstream_ids = tuple(sorted(pid for pid, _, _ in parsed_positions))
    upstream_id_set = set(upstream_ids)
    classified_ids: list[str] = []

    for plane_index, plane in enumerate(planes):
        plane_classified_ids = [cls.position_id for cls in plane.classifications.classifications]
        plane_set = set(plane_classified_ids)
        missing = sorted(upstream_id_set - plane_set)
        extras = sorted(plane_set - upstream_id_set)
        # duplicate detection
        seen: set[str] = set()
        duplicates: list[str] = []
        for pid in plane_classified_ids:
            if pid in seen and pid not in duplicates:
                duplicates.append(pid)
            seen.add(pid)
        if missing or extras or duplicates:
            details = []
            if missing:
                details.append(("plane_index", str(plane_index)))
                details.append(("missing_position_ids", "|".join(missing)))
            if extras:
                details.append(("plane_index", str(plane_index)))
                details.append(("extra_position_ids", "|".join(extras)))
            if duplicates:
                details.append(("plane_index", str(plane_index)))
                details.append(("duplicate_position_ids", "|".join(sorted(set(duplicates)))))
            blockers.append(
                _rank_blocker(
                    _STAGE_17_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_POSITION_CLASSIFICATION_INCOMPLETE.value,
                        field_path=f"baffle_planes[{plane_index}].tube_hole_classifications",
                        message_key="position_classification_incomplete",
                        details=tuple(details),
                    ),
                )
            )
        classified_ids.extend(plane_classified_ids)

    return tuple(blockers), tuple(sorted(set(classified_ids)))


# ---------------------------------------------------------------------------
# Stage 18 -- Public quantization closure.
# ---------------------------------------------------------------------------


def _stage18_quantization(
    planes: tuple[_BafflePlaneFoundation, ...],
    intervals: tuple[tuple[Decimal, Decimal, Decimal], ...],
    parsed: dict[str, Any],
    derived: dict[str, Decimal],
    usable_span: Decimal,
    requested_quantization_collision: bool,
) -> tuple[tuple[_RankedMessage, ...], tuple[_BafflePlaneFoundation, ...]]:
    """Stage 18: public quantization closure.

    Verifies that after public-string quantization:

    * contract-positive derived values quantize to ``> 0``,
    * public center coordinates are strictly increasing and distinct,
    * public occupied intervals remain ``start <= center <= end``,
    * positive unquantized gaps are allowed to quantize to public zero
      (no tangency warning emitted by Stage 18).

    Returns ``(blockers, planes_with_public_coordinates)``.
    """
    blockers: list[_RankedMessage] = []

    # Validate public quantization of contract-positive values.
    def _must_be_positive(public: str, label: str) -> None:
        try:
            parsed_value = _parse_decimal_field(public)
        except ValueError:
            blockers.append(
                _rank_blocker(
                    _STAGE_18_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION.value,
                        field_path=label,
                        message_key="public_decimal_lexical_invalid_after_quantization",
                        details=(("field", label),),
                    ),
                )
            )
            return
        if parsed_value <= _CANONICAL_ZERO:
            blockers.append(
                _rank_blocker(
                    _STAGE_18_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION.value,
                        field_path=label,
                        message_key="positive_unquantized_derived_value_quantizes_to_public_zero",
                        details=(
                            ("field", label),
                            ("public", public),
                        ),
                    ),
                )
            )

    _must_be_positive(_quantize_coordinate(derived["baffle_diameter"]), "baffle_diameter_m")
    _must_be_positive(_quantize_coordinate(derived["baffle_radius"]), "baffle_radius_m")
    _must_be_positive(
        _quantize_coordinate(derived["baffle_hole_diameter"]), "baffle_hole_diameter_m"
    )
    _must_be_positive(_quantize_coordinate(derived["baffle_hole_radius"]), "baffle_hole_radius_m")
    _must_be_positive(_quantize_coordinate(usable_span), "usable_baffle_span_m")

    public_centers: list[str] = []
    for z_i, _occ_start, _occ_end in intervals:
        public_centers.append(_quantize_coordinate(z_i))

    # Strictly increasing + distinct.
    prev: str | None = None
    for center in public_centers:
        if prev is not None and not (center > prev):
            blockers.append(
                _rank_blocker(
                    _STAGE_18_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION.value,
                        field_path="baffle_planes[*].center_coordinate_m",
                        message_key="public_center_ordering_collapses",
                        details=(
                            ("previous", prev if prev is not None else ""),
                            ("current", center),
                        ),
                    ),
                )
            )
            break
        prev = center

    # occupied_start <= center <= occupied_end and not collapsed.
    for (_z_i, occ_start, occ_end), center_pub in zip(intervals, public_centers, strict=True):
        occ_start_pub = _quantize_coordinate(occ_start)
        occ_end_pub = _quantize_coordinate(occ_end)
        if occ_start_pub > center_pub or center_pub > occ_end_pub:
            blockers.append(
                _rank_blocker(
                    _STAGE_18_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION.value,
                        field_path="baffle_planes[*].occupied_interval",
                        message_key="public_occupied_interval_out_of_order",
                        details=(
                            ("center", center_pub),
                            ("occupied_start", occ_start_pub),
                            ("occupied_end", occ_end_pub),
                        ),
                    ),
                )
            )
        if occ_start_pub == occ_end_pub:
            blockers.append(
                _rank_blocker(
                    _STAGE_18_RANK,
                    _make_message(
                        _t024.BlockerCode.BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION.value,
                        field_path="baffle_planes[*].occupied_interval",
                        message_key="public_occupied_interval_collapses_to_zero_width",
                        details=(
                            ("occupied_start", occ_start_pub),
                            ("occupied_end", occ_end_pub),
                        ),
                    ),
                )
            )

    if blockers:
        return tuple(blockers), planes

    # Patch planes with public-coordinate strings.
    new_planes: list[_BafflePlaneFoundation] = []
    for plane, (z_i, occ_start, occ_end) in zip(planes, intervals, strict=True):
        new_plane = _BafflePlaneFoundation(
            baffle_index=plane.baffle_index,
            center_coordinate_m=_quantize_coordinate(z_i),
            occupied_start_coordinate_m=_quantize_coordinate(occ_start),
            occupied_end_coordinate_m=_quantize_coordinate(occ_end),
            orientation=plane.orientation,
            cut_chord=plane.cut_chord,
            window_region_semantics=plane.window_region_semantics,
            baffle_covered_region_semantics=plane.baffle_covered_region_semantics,
            crossflow_reference_region_semantics=plane.crossflow_reference_region_semantics,
            classifications=plane.classifications,
        )
        new_planes.append(new_plane)
    return tuple(blockers), tuple(new_planes)


# ---------------------------------------------------------------------------
# Top-level orchestration entry point.
# ---------------------------------------------------------------------------


def compute_geometry_foundation(
    request: _t024.BaffleGeometryRequest,
) -> _GeometryFoundationResult:
    """Compute the Round-5 geometry foundation for ``request``.

    Module-private entry point. Returns a :class:`_GeometryFoundationResult`
    whose ``geometry`` field is ``None`` iff any blocker was produced.

    Caller-visible warning / blocker codes follow the design contract.
    """
    warnings: list[_RankedMessage] = []
    completed_stage_rank = 0

    stage9_blockers, parsed = _stage9_parse(request)
    if stage9_blockers or parsed is None:
        return _GeometryFoundationResult(
            geometry=None,
            completed_stage_rank=completed_stage_rank,
            warnings=_freeze_warnings(()),
            blockers=_freeze_blockers(stage9_blockers),
        )
    completed_stage_rank = _STAGE_9_RANK

    stage10_blockers, baffle_count, center_planes = _stage10_validate(request, parsed)
    if stage10_blockers or baffle_count is None or center_planes is None:
        return _GeometryFoundationResult(
            geometry=None,
            completed_stage_rank=completed_stage_rank,
            warnings=_freeze_warnings(()),
            blockers=_freeze_blockers(stage10_blockers),
        )
    completed_stage_rank = _STAGE_10_RANK

    stage11_blockers, derived = _stage11_derive(parsed)
    if stage11_blockers or derived is None:
        return _GeometryFoundationResult(
            geometry=None,
            completed_stage_rank=completed_stage_rank,
            warnings=_freeze_warnings(()),
            blockers=_freeze_blockers(stage11_blockers),
        )
    completed_stage_rank = _STAGE_11_RANK

    stage12_blockers, stage12_warnings, intervals = _stage12_solids(
        request, parsed, baffle_count, center_planes
    )
    warnings.extend(stage12_warnings)
    if stage12_blockers or intervals is None:
        return _GeometryFoundationResult(
            geometry=None,
            completed_stage_rank=completed_stage_rank,
            warnings=_freeze_warnings(warnings),
            blockers=_freeze_blockers(stage12_blockers),
        )
    completed_stage_rank = _STAGE_12_RANK

    # Per-baffle Stages 13 / 14 / 15 / 16.
    planes: list[_BafflePlaneFoundation] = []
    orientations = tuple(request.design_authority.orientation_sequence)
    for baffle_index in range(baffle_count):
        (
            per_baffle_blockers,
            per_baffle_warnings,
            plane,
            per_baffle_completed_stage_rank,
        ) = _process_one_baffle(
            request,
            baffle_index=baffle_index,
            orientation=orientations[baffle_index],
            derived=derived,
            parsed_positions=parsed["positions"],
        )
        warnings.extend(per_baffle_warnings)
        if per_baffle_blockers or plane is None:
            # ``completed_stage_rank`` carries the rank of the last
            # fully-completed validation stage. The per-baffle loop
            # (Stages 13-16) returns its last-completed rank as an
            # **explicit tracker** value from ``_process_one_baffle``;
            # callers MUST NOT recompute it from blocker metadata.
            # Defensive fallback: if the loop returned ``plane is None``
            # without blockers, the orchestrator's own explicit tracker
            # (which still holds the Stage 12 rank from earlier) is the
            # authoritative last-completed value.
            if per_baffle_blockers:
                last_completed_rank = per_baffle_completed_stage_rank
            else:
                last_completed_rank = completed_stage_rank
            return _GeometryFoundationResult(
                geometry=None,
                completed_stage_rank=last_completed_rank,
                warnings=_freeze_warnings(warnings),
                blockers=_freeze_blockers(tuple(per_baffle_blockers)),
            )

        # Patch the per-plane center / occupied coordinates with the
        # current interval triple so the downstream stages can reuse them.
        z_i, occ_start, occ_end = intervals[baffle_index]
        plane_with_coords = _BafflePlaneFoundation(
            baffle_index=plane.baffle_index,
            center_coordinate_m=_quantize_coordinate(z_i),
            occupied_start_coordinate_m=_quantize_coordinate(occ_start),
            occupied_end_coordinate_m=_quantize_coordinate(occ_end),
            orientation=plane.orientation,
            cut_chord=plane.cut_chord,
            window_region_semantics=plane.window_region_semantics,
            baffle_covered_region_semantics=plane.baffle_covered_region_semantics,
            crossflow_reference_region_semantics=plane.crossflow_reference_region_semantics,
            classifications=plane.classifications,
        )
        planes.append(plane_with_coords)
    completed_stage_rank = _STAGE_16_RANK

    # Stage 17.
    stage17_blockers, _ = _stage17_completeness(parsed["positions"], tuple(planes))
    if stage17_blockers:
        return _GeometryFoundationResult(
            geometry=None,
            completed_stage_rank=completed_stage_rank,
            warnings=_freeze_warnings(warnings),
            blockers=_freeze_blockers(stage17_blockers),
        )
    completed_stage_rank = _STAGE_17_RANK

    # Stage 18.
    usable_span = parsed["axial_end"] - parsed["axial_start"]
    stage18_blockers, planes_quantized = _stage18_quantization(
        tuple(planes),
        intervals,
        parsed,
        derived,
        usable_span,
        requested_quantization_collision=False,
    )
    planes = list(planes_quantized)
    if stage18_blockers:
        return _GeometryFoundationResult(
            geometry=None,
            completed_stage_rank=completed_stage_rank,
            warnings=_freeze_warnings(warnings),
            blockers=_freeze_blockers(stage18_blockers),
        )
    completed_stage_rank = _STAGE_18_RANK

    geometry_foundation = _GeometryFoundation(
        usable_baffle_span_m=_quantize_coordinate(usable_span),
        baffle_diameter_m=_quantize_coordinate(derived["baffle_diameter"]),
        baffle_radius_m=_quantize_coordinate(derived["baffle_radius"]),
        baffle_hole_diameter_m=_quantize_coordinate(derived["baffle_hole_diameter"]),
        baffle_hole_radius_m=_quantize_coordinate(derived["baffle_hole_radius"]),
        cut_height_m=_quantize_coordinate(derived["cut_height"]),
        chord_offset_from_center_m=_quantize_coordinate(derived["chord_offset_from_center"]),
        baffle_planes=tuple(planes),
        position_count=len(parsed["positions"]),
    )
    return _GeometryFoundationResult(
        geometry=geometry_foundation,
        completed_stage_rank=completed_stage_rank,
        warnings=_freeze_warnings(warnings),
        blockers=_freeze_blockers(()),
    )


__all__ = [
    "compute_geometry_foundation",
]
