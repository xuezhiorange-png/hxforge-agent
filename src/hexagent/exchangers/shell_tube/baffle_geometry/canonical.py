"""TASK-024 canonical foundation module.

Implements:
- Decimal lexical canonicalization (Section 7.1, 7.2, 7.3).
- Canonical JSON encoder (Section 7.4, 7.5).
- Raw blocked projection v3 (Section 7.6).

All public surface area of this module is the deterministic infrastructure
frozen by the TASK-024 design contract. It performs no engineering
calculation; it only normalizes, projects, and serializes values.

Rules honored everywhere:

- Exact identity dispatch via ``type(value)`` (no isinstance, no
  dataclasses.is_dataclass, no runtime introspection).
- Static recognized-type tables for enums and dataclasses (Section 7.6.2).
- Decimal arithmetic only under a local context built from the frozen
  precision / rounding constants (Section 7.2); no global context
  pollution.
- Canonical JSON keys are sorted lexicographically (Section 7.4).
- Compact UTF-8 JSON output; no whitespace bytes.
- Reference cycles in exact built-in containers collapse to the diagnostic
  token ``{"raw_type":"cyclic_graph"}`` (Section 7.6.3).
- Insertion / iteration / randomization / locale / pid do not influence
  any result.
- ``sys.set_int_max_str_digits`` is never read or written; arbitrary
  magnitude ints go through ``int.__format__(value, "x")`` directly
  (Section 7.6.1).
- Unsupported objects project to ``{"raw_type":"unsupported_object"}``
  and no user-defined method is called (Section 7.6.2.4).

The Round 3 scope declares which functions are public for this round and
which are internal-only. Anything outside the round-3 scope (Section 14
hash assembly, Section 9 geometry, Section 12 warning emission, etc.) is
explicitly deferred to later rounds.
"""

from __future__ import annotations

import datetime
import decimal
import hashlib
import json
import uuid
from decimal import Decimal
from enum import Enum
from typing import Any, Final, NoReturn, TypeAlias

# Frozen decimal context (Section 7.2).
_DECIMAL_PRECISION: Final[int] = 50
_DECIMAL_ROUNDING: Final[str] = decimal.ROUND_HALF_EVEN
_COORDINATE_QUANTUM_M: Final[str] = "0.000000000001"
_SQUARED_COORDINATE_QUANTUM_M2: Final[str] = "0.000000000000000000000001"
_CANONICAL_ZERO: Final[str] = "0"
_RAW_BLOCKED_PROJECTION_VERSION: Final[str] = "task024.raw-blocked-projection.v3"


# ---------------------------------------------------------------------------
# Canonical projection type aliases (Section 7.6, raw blocked projection v3).
#
# These aliases describe the closed tagged-projection space. They are used
# only for mypy narrowing; runtime values are plain dict/list/tuple/str/int
# instances produced by ``_raw_value_projection``. The contracts require
# exact identity dispatch (no isinstance) and no user-code execution, so
# these aliases are non-exhaustive intent documentation; the runtime
# projection never returns unknown shapes.
# ---------------------------------------------------------------------------

ProjectionScalar: TypeAlias = dict[str, Any]
MappingEntry: TypeAlias = dict[str, Any]
Container: TypeAlias = list[MappingEntry]
RawValueProjection: TypeAlias = Any


# ---------------------------------------------------------------------------
# Recognized enum and dataclass table type signatures (Section 7.6.2).
# ---------------------------------------------------------------------------

_EnumMemberPair: TypeAlias = tuple[Enum, str]
_EnumTableEntry: TypeAlias = tuple[str, type[Enum], tuple[_EnumMemberPair, ...]]
_DataclassTableEntry: TypeAlias = tuple[str, type, tuple[str, ...]]


def _local_decimal_context() -> decimal.Context:
    """Build a fresh ``decimal.Context`` from the frozen contract tokens.

    The context is intentionally constructed locally on every call so that
    no global context mutation can leak into or out of this module.
    """
    return decimal.Context(prec=_DECIMAL_PRECISION, rounding=_DECIMAL_ROUNDING)


def canonical_decimal_string(value: Any) -> str:
    """Return a canonical finite decimal string for ``value``.

    - ``value`` must be an exact ``Decimal`` or a finite decimal-lexical
      string.
    - No exponent notation, no leading ``+``, no surrounding whitespace.
    - Negative zero normalizes to ``"0"``.
    - NaN and Infinity are forbidden and raise ``ValueError``.
    """
    if isinstance(value, Decimal):
        d = value
    elif isinstance(value, str):
        if value != value.strip():
            raise ValueError("canonical_decimal_string forbids surrounding whitespace")
        if value.startswith("+"):
            raise ValueError("canonical_decimal_string forbids leading plus")
        if "e" in value or "E" in value:
            raise ValueError("canonical_decimal_string forbids exponent notation")
        d = Decimal(value)
    else:
        raise ValueError(
            "canonical_decimal_string requires exact Decimal or finite "
            "decimal-lexical string; got type " + type(value).__name__
        )

    if d.is_nan():
        raise ValueError("canonical_decimal_string forbids NaN")
    if d.is_infinite():
        raise ValueError("canonical_decimal_string forbids Infinity")

    ctx = _local_decimal_context()
    with decimal.localcontext(ctx):
        if not d.is_finite():
            raise ValueError("canonical_decimal_string forbids special values")
        sign, digits, exponent = d.as_tuple()
        if not isinstance(exponent, int):
            raise ValueError("canonical_decimal_string refuses non-integer exponent")
        int_d = int("".join(str(x) for x in digits)) if digits else 0
        sign_prefix = "-" if sign else ""
        if int_d == 0:
            return _CANONICAL_ZERO
        if exponent >= 0:
            body = str(int_d) + ("0" * int(exponent))
            return sign_prefix + body
        s_digs = str(int_d)
        abs_exp = -exponent
        if len(s_digs) > abs_exp:
            pos = len(s_digs) + exponent
            return sign_prefix + s_digs[:pos] + "." + s_digs[pos:]
        if len(s_digs) == abs_exp:
            return sign_prefix + "0." + s_digs
        pad = "0." + ("0" * (abs_exp - len(s_digs))) + s_digs
        return sign_prefix + pad


# ---------------------------------------------------------------------------
# Recognized enum and dataclass tables (Section 7.6.2.1 -- CLOSED tables).
# ---------------------------------------------------------------------------


def _build_recognized_enum_table() -> tuple[_EnumTableEntry, ...]:
    """Build the static recognized-enum table (Section 7.6.2.2).

    The returned tuple is ordered by owning-task ascending then enum type
    token ascending. Each entry is a tuple of::

        (enum_type_token: str, python_type: type,
         ordered_member_pairs: tuple of (enum_member: Enum, member_token: str))
    """
    from hexagent.exchangers.shell_tube import models as _m_t020
    from hexagent.exchangers.shell_tube.baffle_geometry import models as _m_t024
    from hexagent.exchangers.shell_tube.shell_bundle_geometry import models as _m_t022
    from hexagent.exchangers.shell_tube.tube_layout import models as _m_t021

    entries: list[_EnumTableEntry] = []

    def _add(token: str, py_type: type[Enum], members: tuple[str, ...]) -> None:
        ordered: tuple[_EnumMemberPair, ...] = tuple((getattr(py_type, n), n) for n in members)
        entries.append((token, py_type, ordered))

    _add("task020:AuthorityMode", _m_t020.AuthorityMode, ("INTERNAL_GENERIC", "APPROVED_RULE_PACK"))
    _add(
        "task020:CaseRevisionStatus",
        _m_t020.CaseRevisionStatus,
        ("COMMITTED", "SUPERSEDED", "ARCHIVED"),
    )
    _add(
        "task020:ConstructionFamily",
        _m_t020.ConstructionFamily,
        ("FIXED_TUBESHEET", "U_TUBE", "FLOATING_HEAD"),
    )
    _add("task020:EquipmentFamily", _m_t020.EquipmentFamily, ("SHELL_AND_TUBE",))
    _add("task020:Orientation", _m_t020.Orientation, ("HORIZONTAL", "VERTICAL", "UNSPECIFIED"))
    _add(
        "task020:StandardClaimStatus",
        _m_t020.StandardClaimStatus,
        ("NO_STANDARD_CLAIM", "RULE_PACK_VALIDATED"),
    )

    _add("task021:AuthorityMode", _m_t021.AuthorityMode, ("INTERNAL_GENERIC", "APPROVED_RULE_PACK"))
    _add("task021:AxisOrientation", _m_t021.AxisOrientation, ("PRIMARY_AXIS_X", "PRIMARY_AXIS_Y"))
    _add(
        "task021:ExclusionZoneType", _m_t021.ExclusionZoneType, ("AXIS_ALIGNED_RECTANGLE", "CIRCLE")
    )
    _add(
        "task021:OriginMode",
        _m_t021.OriginMode,
        ("CENTER_ON_LATTICE_POINT", "CENTER_ON_PRIMITIVE_CELL"),
    )
    _add("task021:PatternFamily", _m_t021.PatternFamily, ("SQUARE", "TRIANGULAR"))

    _add(
        "task022:RuleAuthorityMode",
        _m_t022.RuleAuthorityMode,
        ("INTERNAL_GENERIC", "APPROVED_RULE_PACK"),
    )
    _add(
        "task022:ShellInsideDiameterAuthorityMode",
        _m_t022.ShellInsideDiameterAuthorityMode,
        ("CALLER_SUPPLIED_EXPLICIT", "APPROVED_CATALOG_SNAPSHOT"),
    )

    _add("task024:BaffleOrientation", _m_t024.BaffleOrientation, ("TOP", "BOTTOM", "LEFT", "RIGHT"))
    _add("task024:BaffleType", _m_t024.BaffleType, ("SINGLE_SEGMENTAL",))
    _add(
        "task024:TubeRegionClassification",
        _m_t024.TubeRegionClassification,
        ("WINDOW", "CROSSFLOW_REFERENCE"),
    )
    _add("task024:ValidationStatus", _m_t024.ValidationStatus, ("VALID", "BLOCKED"))

    return tuple(entries)


def _build_recognized_dataclass_table() -> tuple[_DataclassTableEntry, ...]:
    """Build the static recognized-dataclass table (Section 7.6.2.3).

    Returns a tuple of::

        (dataclass_type_token: str, python_type: type,
         literal_field_name_tuple: tuple of str)
    """
    from hexagent.exchangers.shell_tube import models as _m_t020
    from hexagent.exchangers.shell_tube.baffle_geometry import models as _m_t024
    from hexagent.exchangers.shell_tube.shell_bundle_geometry import models as _m_t022
    from hexagent.exchangers.shell_tube.tube_layout import models as _m_t021

    entries: list[_DataclassTableEntry] = []

    def _add(token: str, py_type: type, fields: tuple[str, ...]) -> None:
        entries.append((token, py_type, tuple(fields)))

    _add(
        "task020:CaseRevisionAuthority",
        _m_t020.CaseRevisionAuthority,
        ("revision_id", "payload_hash", "domain_snapshot_hash", "revision_status"),
    )
    _add("task020:ComponentTokens", _m_t020.ComponentTokens, ("front_head", "shell", "rear_head"))
    _add(
        "task020:ConfigurationAuthorityBinding",
        _m_t020.ConfigurationAuthorityBinding,
        (
            "authority_mode",
            "standard_system_id",
            "case_authority",
            "evaluated_rule_pack_authority",
            "case_authority_evidence_refs",
        ),
    )
    _add(
        "task020:ErrorEntry",
        _m_t020.ErrorEntry,
        ("code", "field_path", "message_key", "evidence_refs", "details"),
    )
    _add(
        "task020:EvaluatedRulePackAuthority",
        _m_t020.EvaluatedRulePackAuthority,
        (
            "rule_pack_id",
            "rule_pack_version",
            "rule_pack_canonical_hash",
            "validation_status",
            "selected_rule_authorities",
        ),
    )
    _add(
        "task020:SelectedRuleAuthority",
        _m_t020.SelectedRuleAuthority,
        (
            "rule_id",
            "rule_version",
            "rule_artifact_canonical_hash",
            "source_class",
            "license_evidence",
            "approval_status",
            "provenance_edge_ids",
            "evidence_refs",
        ),
    )
    _add(
        "task020:ShellAndTubeConfiguration",
        _m_t020.ShellAndTubeConfiguration,
        (
            "schema_version",
            "configuration_id",
            "configuration_hash",
            "equipment_family",
            "authority_mode",
            "standard_claim_status",
            "construction_family",
            "orientation",
            "shell_pass_count",
            "tube_pass_count",
            "component_tokens",
            "authority_binding",
            "case_authority",
            "warnings",
            "blockers",
            "deferred_capabilities",
        ),
    )

    _add(
        "task021:ApprovedTubeGeometrySnapshot",
        _m_t021.ApprovedTubeGeometrySnapshot,
        (
            "geometry_id",
            "geometry_type",
            "revision",
            "approval_state",
            "outer_diameter_m",
            "inner_diameter_m",
            "wall_thickness_m",
            "record_hash",
            "snapshot_hash",
            "source_binding",
        ),
    )
    _add(
        "task021:CircularTubeCenterEnvelope",
        _m_t021.CircularTubeCenterEnvelope,
        ("schema_version", "tube_center_envelope_diameter_m", "evidence_refs"),
    )
    _add(
        "task021:ExclusionAudit",
        _m_t021.ExclusionAudit,
        ("zone_id", "rejected_position_count", "reason_code", "evidence_refs"),
    )
    _add(
        "task021:ExclusionZone",
        _m_t021.ExclusionZone,
        (
            "zone_id",
            "zone_type",
            "center_x_m",
            "center_y_m",
            "clearance_m",
            "reason_code",
            "evidence_refs",
            "width_m",
            "height_m",
            "radius_m",
        ),
    )
    _add(
        "task021:LayoutRuleAuthoritySnapshot",
        _m_t021.LayoutRuleAuthoritySnapshot,
        (
            "profile_id",
            "authority_mode",
            "rule_id",
            "rule_version",
            "rule_artifact_canonical_hash",
            "source_class",
            "license_evidence",
            "approval_status",
            "provenance_edge_ids",
            "evidence_refs",
            "rule_pack_identity",
            "pattern_family",
            "pitch_m",
            "edge_clearance_m",
            "allowed_origin_modes",
            "allowed_axis_orientations",
            "allowed_exclusion_zone_types",
            "maximum_candidate_positions",
            "snapshot_hash",
        ),
    )
    _add(
        "task021:MessageEntry",
        _m_t021.MessageEntry,
        ("code", "field_path", "message_key", "evidence_refs", "details"),
    )
    _add(
        "task021:RulePackIdentitySnapshot",
        _m_t021.RulePackIdentitySnapshot,
        ("rule_pack_id", "rule_pack_version", "rule_pack_canonical_hash"),
    )
    _add(
        "task021:SourceBindingSnapshot",
        _m_t021.SourceBindingSnapshot,
        (
            "source_id",
            "source_type",
            "source_revision",
            "source_location",
            "evidence_ref",
            "approved_by",
            "approved_at",
        ),
    )
    _add(
        "task021:TubeLayout",
        _m_t021.TubeLayout,
        (
            "schema_version",
            "layout_id",
            "layout_hash",
            "request_hash",
            "task020_configuration_id",
            "task020_configuration_hash",
            "case_authority",
            "construction_family",
            "equipment_orientation",
            "shell_pass_count",
            "tube_pass_count",
            "tube_geometry",
            "layout_rule_authority",
            "placement_envelope",
            "origin_mode",
            "axis_orientation",
            "exclusion_zones",
            "positions",
            "tube_hole_count",
            "physical_tube_count",
            "boundary_rejection_count",
            "exclusion_rejection_count",
            "exclusion_audit",
            "warnings",
            "blockers",
            "deferred_capabilities",
            "provenance",
        ),
    )
    _add("task021:TubePosition", _m_t021.TubePosition, ("position_id", "u", "v", "x_m", "y_m"))

    _add(
        "task022:ApprovedShellGeometrySnapshot",
        _m_t022.ApprovedShellGeometrySnapshot,
        (
            "schema_version",
            "geometry_id",
            "geometry_type",
            "revision",
            "approval_state",
            "shell_inside_diameter_m",
            "record_hash",
            "source_binding",
            "snapshot_hash",
        ),
    )
    _add(
        "task022:CallerSuppliedShellInsideDiameter",
        _m_t022.CallerSuppliedShellInsideDiameter,
        ("schema_version", "shell_inside_diameter_m", "evidence_refs", "authority_hash"),
    )
    _add(
        "task022:MessageEntry",
        _m_t022.MessageEntry,
        ("code", "field_path", "message_key", "evidence_refs", "details"),
    )
    _add(
        "task022:RulePackIdentitySnapshot",
        _m_t022.RulePackIdentitySnapshot,
        ("rule_pack_id", "rule_pack_version", "rule_pack_canonical_hash"),
    )
    _add(
        "task022:ShellBundleGeometry",
        _m_t022.ShellBundleGeometry,
        (
            "schema_version",
            "geometry_id",
            "geometry_hash",
            "request_hash",
            "task020_configuration_id",
            "task020_configuration_hash",
            "task021_layout_id",
            "task021_layout_hash",
            "construction_family",
            "equipment_orientation",
            "shell_pass_count",
            "tube_pass_count",
            "tube_geometry_snapshot_hash",
            "geometry_rule_authority",
            "shell_authority_mode",
            "caller_supplied_shell",
            "approved_shell_geometry",
            "shell_inside_diameter_m",
            "shell_radius_m",
            "bare_tube_bundle_radius_m",
            "bare_tube_bundle_diameter_m",
            "bundle_peripheral_allowance_m",
            "bundle_outer_envelope_radius_m",
            "bundle_outer_envelope_diameter_m",
            "shell_to_bundle_radial_clearance_m",
            "shell_to_bundle_diametral_clearance_m",
            "required_minimum_radial_clearance_m",
            "radial_clearance_margin_m",
            "limiting_position_ids",
            "position_count",
            "warnings",
            "blockers",
            "deferred_capabilities",
            "provenance",
        ),
    )
    _add(
        "task022:ShellBundleGeometryRuleAuthoritySnapshot",
        _m_t022.ShellBundleGeometryRuleAuthoritySnapshot,
        (
            "schema_version",
            "profile_id",
            "authority_mode",
            "rule_id",
            "rule_version",
            "rule_artifact_canonical_hash",
            "source_class",
            "license_evidence",
            "approval_status",
            "provenance_edge_ids",
            "evidence_refs",
            "rule_pack_identity",
            "allowed_shell_authority_modes",
            "minimum_bundle_peripheral_allowance_m",
            "minimum_radial_clearance_m",
            "maximum_position_count",
            "snapshot_hash",
        ),
    )
    _add(
        "task022:SourceBindingSnapshot",
        _m_t022.SourceBindingSnapshot,
        (
            "source_id",
            "source_type",
            "source_revision",
            "source_location",
            "evidence_ref",
            "approved_by",
            "approved_at",
        ),
    )

    _add(
        "task024:BaffleGeometry",
        _m_t024.BaffleGeometry,
        (
            "schema_version",
            "geometry_id",
            "geometry_hash",
            "request_hash",
            "task020_configuration_id",
            "task020_configuration_hash",
            "task021_layout_id",
            "task021_layout_hash",
            "task022_geometry_id",
            "task022_geometry_hash",
            "construction_family",
            "equipment_orientation",
            "shell_pass_count",
            "tube_pass_count",
            "shell_inside_diameter_m",
            "tube_outer_diameter_m",
            "axial_span",
            "design_authority",
            "usable_baffle_span_m",
            "baffle_diameter_m",
            "baffle_radius_m",
            "baffle_hole_diameter_m",
            "baffle_hole_radius_m",
            "cut_height_m",
            "chord_offset_from_center_m",
            "baffle_planes",
            "position_count",
            "warnings",
            "blockers",
            "deferred_capabilities",
            "provenance",
        ),
    )
    _add(
        "task024:BaffleGeometryRequest",
        _m_t024.BaffleGeometryRequest,
        (
            "schema_version",
            "configuration",
            "tube_layout",
            "shell_bundle_geometry",
            "axial_span",
            "design_authority",
            "evidence_refs",
        ),
    )
    _add(
        "task024:BaffleGeometryValidationResult",
        _m_t024.BaffleGeometryValidationResult,
        (
            "status",
            "geometry",
            "warnings",
            "blockers",
            "deferred_capabilities",
            "blocked_result_hash",
        ),
    )
    _add(
        "task024:BafflePlaneGeometry",
        _m_t024.BafflePlaneGeometry,
        (
            "baffle_index",
            "center_coordinate_m",
            "occupied_start_coordinate_m",
            "occupied_end_coordinate_m",
            "orientation",
            "cut_chord",
            "window_region_semantics",
            "baffle_covered_region_semantics",
            "crossflow_reference_region_semantics",
            "tube_hole_classifications",
            "window_position_ids",
            "crossflow_reference_position_ids",
            "outer_tangent_position_ids",
            "pairwise_tangent_position_pairs",
            "classification_audit_hash",
        ),
    )
    _add(
        "task024:CallerSuppliedBaffleAxialSpan",
        _m_t024.CallerSuppliedBaffleAxialSpan,
        (
            "schema_version",
            "axial_start_coordinate_m",
            "axial_end_coordinate_m",
            "evidence_refs",
            "authority_hash",
        ),
    )
    _add(
        "task024:CallerSuppliedBaffleDesignAuthority",
        _m_t024.CallerSuppliedBaffleDesignAuthority,
        (
            "schema_version",
            "baffle_type",
            "baffle_count",
            "baffle_thickness_m",
            "spacing_sequence_m",
            "baffle_cut_fraction",
            "orientation_sequence",
            "shell_to_baffle_diametral_clearance_m",
            "tube_to_baffle_hole_diametral_clearance_m",
            "evidence_refs",
            "authority_hash",
        ),
    )
    _add(
        "task024:CutChordGeometry",
        _m_t024.CutChordGeometry,
        (
            "normal_x",
            "normal_y",
            "half_plane_offset_m",
            "chord_half_length_m",
            "endpoint_a_x_m",
            "endpoint_a_y_m",
            "endpoint_b_x_m",
            "endpoint_b_y_m",
        ),
    )
    _add(
        "task024:MessageEntry",
        _m_t024.MessageEntry,
        ("code", "field_path", "message_key", "evidence_refs", "details"),
    )
    _add(
        "task024:PhysicalTubeDiskAudit",
        _m_t024.PhysicalTubeDiskAudit,
        (
            "physical_tube_radius_m",
            "signed_window_distance_m",
            "cut_boundary_margin_m",
            "classification",
        ),
    )
    _add(
        "task024:TubeHoleClassification",
        _m_t024.TubeHoleClassification,
        (
            "position_id",
            "center_x_m",
            "center_y_m",
            "physical_tube_radius_m",
            "baffle_hole_radius_m",
            "signed_window_distance_m",
            "cut_boundary_margin_m",
            "classification",
            "outer_boundary_margin_squared_m2",
            "physical_tube_disk_audit",
        ),
    )

    return tuple(entries)


STATIC_RECOGNIZED_ENUMS: Final[tuple[_EnumTableEntry, ...]] = _build_recognized_enum_table()
STATIC_RECOGNIZED_DATACLASSES: Final[tuple[_DataclassTableEntry, ...]] = (
    _build_recognized_dataclass_table()
)


# ---------------------------------------------------------------------------
# Canonical JSON encoder (Section 7.4).
# ---------------------------------------------------------------------------
def _canonical_json_bytes(value: Any) -> bytes:
    """Encode any value into compact UTF-8 deterministic JSON bytes.

    The input domain is the closed canonical value domain: ``None``, exact
    ``bool``, exact ``int`` of arbitrary magnitude, exact ``str``, exact
    ``Decimal`` already projected, lists, and string-keyed dicts whose
    keys sort lexicographically. ``float``, live ``Decimal``, ``bytes``,
    ``set``, ``datetime``, locale or process metadata and arbitrary
    objects are forbidden here and raise ``TypeError``.
    """
    if type(value) is float:
        raise TypeError("canonical_json_bytes forbids float")
    if isinstance(value, Decimal):
        raise TypeError("canonical_json_bytes forbids live Decimal")
    if type(value) is bytes:
        raise TypeError("canonical_json_bytes forbids bytes")
    if type(value) is set or type(value) is frozenset:
        raise TypeError("canonical_json_bytes forbids set/frozenset")
    if isinstance(value, datetime.datetime):
        raise TypeError("canonical_json_bytes forbids datetime")
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=_json_default_forbidden,
    ).encode("utf-8")


def _json_default_forbidden(_value: Any) -> NoReturn:  # pragma: no cover - never reached
    raise TypeError("canonical_json_bytes forbids non-canonical default value")


# ---------------------------------------------------------------------------
# Raw blocked projection v3 (Section 7.6).
# ---------------------------------------------------------------------------
_INT_ZERO_BYTES: Final[bytes] = b"0"


def _exact_int_projection(value: int) -> dict[str, Any]:
    if value == 0:
        return {"raw_type": "int", "sign": 0, "magnitude_hex": _INT_ZERO_BYTES.decode("ascii")}
    if value > 0:
        return {
            "raw_type": "int",
            "sign": 0,
            "magnitude_hex": int.__format__(value, "x"),
        }
    return {
        "raw_type": "int",
        "sign": 1,
        "magnitude_hex": int.__format__(-value, "x"),
    }


def _exact_str_projection(value: str) -> dict[str, Any]:
    return {
        "raw_type": "str",
        "code_points": [f"{ord(c):04x}" for c in value],
    }


def _exact_float_projection(value: float) -> dict[str, Any]:
    if value != value:
        token: str = "nan"
    elif value == float("inf"):
        token = "+infinity"
    elif value == float("-inf"):
        token = "-infinity"
    else:
        token = float.hex(value)
    return {"raw_type": "float", "value": token}


def _exact_decimal_projection(value: Decimal) -> dict[str, Any]:
    try:
        sign, digits, exponent = value.as_tuple()
    except Exception:
        return {"raw_type": "decimal_projection_unavailable"}

    if value.is_nan() or value.is_infinite():
        return {"raw_type": "decimal_projection_unavailable"}

    if isinstance(exponent, str):
        if exponent == "F":
            token: str = "F"
        elif exponent == "n":
            token = "n"
        elif exponent == "N":
            token = "N"
        else:
            return {"raw_type": "decimal_projection_unavailable"}
        exponent_obj: dict[str, Any] = {"kind": "special", "token": token}
    else:
        if exponent == 0:
            exponent_obj = {
                "kind": "integer",
                "sign": 0,
                "magnitude_hex": _INT_ZERO_BYTES.decode("ascii"),
            }
        elif exponent > 0:
            exponent_obj = {
                "kind": "integer",
                "sign": 0,
                "magnitude_hex": int.__format__(exponent, "x"),
            }
        else:
            exponent_obj = {
                "kind": "integer",
                "sign": 1,
                "magnitude_hex": int.__format__(-exponent, "x"),
            }

    return {
        "raw_type": "decimal",
        "sign": int(sign),
        "digits": [int(d) for d in digits],
        "exponent": exponent_obj,
    }


def _cyclic_safe_graph_traversal(value: Any, seen: frozenset[int]) -> bool:
    """Pre-scan exact supported containers / recognized dataclass trees
    for cycles. Returns ``True`` if any cycle exists in the traversed
    graph.

    The traversal is restricted to:
    - exact ``list``, ``tuple``, ``dict``, ``set``, ``frozenset``;
    - ``str``, ``bytes``, exact scalars;
    - instances whose ``type(value) is`` in the recognized-dataclass table.

    All other objects appear opaque to the traversal but do not cause
    them to be entered.
    """
    seen_id = id(value)
    if seen_id in seen:
        return True
    new_seen: frozenset[int] = seen | frozenset({seen_id})
    value_type = type(value)
    if value_type is list or value_type is tuple:
        return any(_cyclic_safe_graph_traversal(item, new_seen) for item in value)
    if value_type is dict:
        for k, v in value.items():
            if _cyclic_safe_graph_traversal(k, new_seen):
                return True
            if _cyclic_safe_graph_traversal(v, new_seen):
                return True
        return False
    if value_type is set or value_type is frozenset:
        return any(_cyclic_safe_graph_traversal(item, new_seen) for item in value)
    if (
        value_type is bytes
        or value_type is str
        or value_type is int
        or value_type is bool
        or value_type is float
        or value_type is Decimal
    ):
        return False
    if value_type is type(None):
        return False
    for entry in STATIC_RECOGNIZED_DATACLASSES:
        _, py_type, fields = entry
        if value_type is py_type:
            for name in fields:
                if _cyclic_safe_graph_traversal(object.__getattribute__(value, name), new_seen):
                    return True
            return False
    return False


def _raw_value_projection(value: Any, _seen: frozenset[int] | None = None) -> dict[str, Any]:
    """Total raw-value projection (Section 7.6).

    Uses only exact identity ``type(value)`` comparisons and never
    inspects runtime type metadata, user-defined methods, ``vars`` or
    ``object.__dict__``. ``bytes``, ``str`` and ``bool`` subclasses are
    rejected and collapsed to ``{"raw_type":"unsupported_object"}``.
    Reference cycles in exact built-in containers collapse to
    ``{"raw_type":"cyclic_graph"}``.
    """
    if _seen is None:
        if _cyclic_safe_graph_traversal(value, frozenset()):
            return {"raw_type": "cyclic_graph"}
        _seen = frozenset[int]()

    if value is None:
        return {"raw_type": "null"}

    value_type = type(value)

    if value_type is bool:
        return {"raw_type": "bool", "value": bool(value)}

    if value_type is int:
        return _exact_int_projection(int(value))

    if value_type is str:
        return _exact_str_projection(str(value))

    if value_type is float:
        return _exact_float_projection(float(value))

    if value_type is Decimal:
        return _exact_decimal_projection(value)

    if value_type is bytes:
        return {"raw_type": "bytes", "hex": bytes.hex(bytes(value))}

    if value_type is list:
        seen_id = id(value)
        if seen_id in _seen:
            return {"raw_type": "cyclic_graph"}
        list_seen: frozenset[int] = _seen | frozenset({seen_id})
        return {"raw_type": "list", "items": [_raw_value_projection(v, list_seen) for v in value]}

    if value_type is tuple:
        seen_id = id(value)
        if seen_id in _seen:
            return {"raw_type": "cyclic_graph"}
        tuple_seen: frozenset[int] = _seen | frozenset({seen_id})
        return {"raw_type": "tuple", "items": [_raw_value_projection(v, tuple_seen) for v in value]}

    if value_type is dict:
        seen_id = id(value)
        if seen_id in _seen:
            return {"raw_type": "cyclic_graph"}
        dict_seen: frozenset[int] = _seen | frozenset({seen_id})
        entries: list[dict[str, Any]] = [
            {
                "key": _raw_value_projection(k, dict_seen),
                "value": _raw_value_projection(v, dict_seen),
            }
            for k, v in value.items()
        ]
        entries.sort(
            key=lambda e: (_canonical_json_bytes(e["key"]), _canonical_json_bytes(e["value"]))
        )
        return {"raw_type": "mapping", "entries": entries}

    if value_type is set:
        seen_id = id(value)
        if seen_id in _seen:
            return {"raw_type": "cyclic_graph"}
        set_seen: frozenset[int] = _seen | frozenset({seen_id})
        items: list[dict[str, Any]] = [_raw_value_projection(v, set_seen) for v in value]
        items.sort(key=_canonical_json_bytes)
        return {"raw_type": "set", "items": items}

    if value_type is frozenset:
        seen_id = id(value)
        if seen_id in _seen:
            return {"raw_type": "cyclic_graph"}
        fset_seen: frozenset[int] = _seen | frozenset({seen_id})
        fset_items: list[dict[str, Any]] = [_raw_value_projection(v, fset_seen) for v in value]
        fset_items.sort(key=_canonical_json_bytes)
        return {"raw_type": "frozenset", "items": fset_items}

    if isinstance(value, Enum):
        for entry in STATIC_RECOGNIZED_ENUMS:
            enum_token, py_type, members = entry
            if value_type is py_type:
                for member_obj, member_token in members:
                    if value is member_obj:
                        return {
                            "raw_type": "enum",
                            "enum_type_token": enum_token,
                            "member_token": member_token,
                        }
                return {"raw_type": "recognized_enum_unavailable", "enum_type_token": enum_token}
        return {"raw_type": "unsupported_object"}

    dc_entry: _DataclassTableEntry
    for dc_entry in STATIC_RECOGNIZED_DATACLASSES:
        _, py_type, fields = dc_entry
        if value_type is py_type:
            seen_id = id(value)
            if seen_id in _seen:
                return {"raw_type": "cyclic_graph"}
            dc_seen: frozenset[int] = _seen | frozenset({seen_id})
            projected_fields: list[dict[str, Any]] = []
            try:
                for name in fields:
                    projected_fields.append(
                        {
                            "name": name,
                            "value": _raw_value_projection(
                                object.__getattribute__(value, name), dc_seen
                            ),
                        }
                    )
            except Exception:
                return {
                    "raw_type": "recognized_dataclass_unavailable",
                    "dataclass_type_token": dc_entry[0],
                }
            return {
                "raw_type": "dataclass",
                "dataclass_type_token": dc_entry[0],
                "fields": projected_fields,
            }

    return {"raw_type": "unsupported_object"}


def raw_blocked_projection(raw_request: Any) -> bytes:
    """Return the canonical JSON bytes of the raw blocked projection.

    Format (Section 7.6 container wrapper)::

        {
          "projection_version": "task024.raw-blocked-projection.v3",
          "request": <raw_value_projection(raw_request)>
        }

    The bytes are deterministic and free of float / live Decimal / bytes /
    set / datetime / arbitrary objects.
    """
    projection = {
        "projection_version": _RAW_BLOCKED_PROJECTION_VERSION,
        "request": _raw_value_projection(raw_request),
    }
    return _canonical_json_bytes(projection)


def canonical_json_bytes(value: Any) -> bytes:
    """Return compact UTF-8 canonical JSON bytes for ``value``.

    Domain: ``None``, ``bool``, ``int``, ``str``, ``list``, ``dict`` of
    permitted values. ``float``, live ``Decimal``, ``bytes``, ``set``,
    ``datetime``, arbitrary objects raise ``TypeError``.
    """
    return _canonical_json_bytes(value)


def sha256_canonical(value: Any) -> bytes:
    """Return the SHA-256 digest of the canonical JSON bytes for ``value``.

    If ``value`` is already the bytes form returned by
    ``canonical_json_bytes`` or ``raw_blocked_projection``, the digest is
    computed on those bytes directly. Otherwise the value is encoded to
    canonical JSON bytes first.
    """
    canonical_bytes = value if type(value) is bytes else _canonical_json_bytes(value)
    return hashlib.sha256(canonical_bytes).digest()


def uuid5_from_hash(namespace_hex: str, payload: Any) -> str:
    """Return a deterministic UUID5 string from ``sha256_canonical(payload)``.

    ``namespace_hex`` is a 32-character hex namespace used to bind the
    UUID to a specific TASK-024 namespace. The UUID standard only
    supports ``uuid.NAMESPACE_DNS``, ``uuid.NAMESPACE_URL``, etc.; this
    helper derives an effective namespace from a frozen hex literal so
    that the namespace can be reproduced without code execution
    dependencies.

    The ``name`` argument to ``uuid.uuid5`` is the canonical lowercase
    hexadecimal representation of the SHA-256 digest of
    ``canonical_json_bytes(payload)``. Using the hex string (rather
    than the raw 32-byte digest) satisfies ``uuid.uuid5``'s ``str``
    name requirement and aligns with the rest of the baffle-geometry
    module's hex-string conventions (compare
    ``task022_geometry_id`` and ``task021_position_id``). The UUID
    namespace is a ``uuid.UUID`` derived from the 32-char hex
    ``namespace_hex`` literal.
    """
    if len(namespace_hex) != 32:
        raise ValueError("uuid5_from_hash requires a 32-char hex namespace")
    digest = hashlib.sha256(_canonical_json_bytes(payload)).digest()
    namespace_uuid_bytes = bytes.fromhex(namespace_hex)
    ns_uuid = uuid.UUID(bytes=namespace_uuid_bytes)
    # ``name`` is the canonical lowercase hex string of the SHA-256
    # digest. This is the only valid ``str`` form of the hash and
    # is consistent with how the rest of the baffle-geometry module
    # expresses SHA-256 hashes.
    name = digest.hex()
    return str(uuid.uuid5(ns_uuid, name))


DECIMAL_PRECISION: Final[int] = _DECIMAL_PRECISION
DECIMAL_ROUNDING: Final[str] = _DECIMAL_ROUNDING
COORDINATE_QUANTUM_M: Final[str] = _COORDINATE_QUANTUM_M
SQUARED_COORDINATE_QUANTUM_M2: Final[str] = _SQUARED_COORDINATE_QUANTUM_M2
CANONICAL_ZERO: Final[str] = _CANONICAL_ZERO
RAW_BLOCKED_PROJECTION_VERSION: Final[str] = _RAW_BLOCKED_PROJECTION_VERSION

__all__ = (
    "DECIMAL_PRECISION",
    "DECIMAL_ROUNDING",
    "COORDINATE_QUANTUM_M",
    "SQUARED_COORDINATE_QUANTUM_M2",
    "CANONICAL_ZERO",
    "RAW_BLOCKED_PROJECTION_VERSION",
    "STATIC_RECOGNIZED_ENUMS",
    "STATIC_RECOGNIZED_DATACLASSES",
    "canonical_decimal_string",
    "canonical_json_bytes",
    "sha256_canonical",
    "uuid5_from_hash",
    "raw_blocked_projection",
)
