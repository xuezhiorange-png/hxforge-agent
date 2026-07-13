"""Strict raw-shape validation for TASK-021 Slice A.

This module deliberately splits Stage 1 / Stage 2 / Stage 3 / Stage 10 of the
frozen §9 pipeline into individual helpers. Round 3 §3 (P0-1) requires the
real 1→21 ordering to be enforceable: the top-level mapping is checked
(Stage 1), raw value types are checked (Stage 2), and schema versions are
checked (Stage 3) BEFORE any Stage-4+ work begins. Stage 10 (zones) must
run only AFTER Stage 9 (authorizations) per the contract; this module
exposes helpers the validator calls in that strict order.
"""

from __future__ import annotations

import enum
import re
from collections.abc import Mapping
from typing import Any, TypeVar

from hexagent.exchangers.shell_tube.models import ShellAndTubeConfiguration

from .canonical import (
    CanonicalizationError,
    canonical_json,
    decimal_string,
    parse_decimal,
    sorted_unique_strings,
    strict_public_json_snapshot,
)
from .models import (
    ENVELOPE_SCHEMA_VERSION,
    PAIRING_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    ApprovedTubeGeometrySnapshot,
    AuthorityMode,
    AxisOrientation,
    BlockerCode,
    CircularTubeCenterEnvelope,
    ExclusionZone,
    ExclusionZoneType,
    LatticeIndex,
    LayoutRuleAuthoritySnapshot,
    MessageEntry,
    OriginMode,
    PatternFamily,
    RulePackIdentitySnapshot,
    SourceBindingSnapshot,
    TubeLayoutRequest,
    UTubePair,
    UTubePairingPlan,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
E = TypeVar("E", bound=enum.StrEnum)


# Top-level field-set for the request payload (Stage 1).
REQUEST_FIELDS: frozenset[str] = frozenset(
    {
        "schema_version",
        "configuration",
        "tube_geometry",
        "layout_rule_authority",
        "placement_envelope",
        "origin_mode",
        "axis_orientation",
        "exclusion_zones",
        "u_tube_pairing_plan",
        "evidence_refs",
    }
)


class SchemaFailure(ValueError):
    """Fail-closed schema error carrying stage ordinal and §12.8 fields."""

    def __init__(
        self,
        stage: int,
        blockers: tuple[MessageEntry, ...],
        *,
        raw_failing_field: Any | None = None,
        normalized_context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(blockers[0].message_key if blockers else "schema_failure")
        self.stage = stage
        self.blockers = blockers
        self.raw_failing_field = raw_failing_field
        self.normalized_context: dict[str, Any] = (
            dict(normalized_context) if normalized_context is not None else {}
        )


def _block(
    code: BlockerCode,
    field_path: str | None,
    message_key: str,
    *,
    details: Mapping[str, Any] | None = None,
    evidence_refs: tuple[str, ...] = (),
) -> MessageEntry:
    return MessageEntry(
        code=code.value,
        field_path=field_path,
        message_key=message_key,
        evidence_refs=evidence_refs,
        details=details,
    )


def _schema_failure(
    stage: int,
    blockers: tuple[MessageEntry, ...],
    *,
    raw_failing_field: Any | None = None,
    normalized_context: Mapping[str, Any] | None = None,
) -> SchemaFailure:
    return SchemaFailure(
        stage,
        blockers,
        raw_failing_field=raw_failing_field,
        normalized_context=normalized_context,
    )


# Raw-type and field-set primitives. Each emits a SchemaFailure at the
# explicit stage passed in by the caller. Round-3 §3 (P0-1) requires that
# every failure carries the actual stage at which the check ran.


def _mapping(
    value: Any,
    field_path: str,
    expected: set[str],
    *,
    stage: int = 1,
    raw_failing_field: Any | None = None,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _schema_failure(
            stage,
            (_block(BlockerCode.STL_RAW_TYPE_INVALID, field_path, "mapping_required"),),
            raw_failing_field=raw_failing_field if raw_failing_field is not None else value,
        )
    unknown = sorted(set(value) - expected)
    if unknown:
        raise _schema_failure(
            stage,
            (
                _block(
                    BlockerCode.STL_UNKNOWN_FIELD,
                    field_path,
                    "unknown_field",
                    details={"fields": unknown},
                ),
            ),
            raw_failing_field=raw_failing_field if raw_failing_field is not None else value,
        )
    missing = sorted(expected - set(value))
    if missing:
        raise _schema_failure(
            stage,
            (
                _block(
                    BlockerCode.STL_RAW_TYPE_INVALID,
                    field_path,
                    "missing_required_field",
                    details={"fields": missing},
                ),
            ),
            raw_failing_field=raw_failing_field if raw_failing_field is not None else value,
        )
    return value


def _nonempty_string(value: Any, field_path: str, *, stage: int = 2) -> str:
    if not isinstance(value, str) or not value:
        raise _schema_failure(
            stage,
            (_block(BlockerCode.STL_RAW_TYPE_INVALID, field_path, "nonempty_string_required"),),
            raw_failing_field=value,
        )
    return value


def _decimal(
    value: Any,
    field_path: str,
    *,
    positive: bool | None = None,
    code: BlockerCode = BlockerCode.STL_DECIMAL_LEXICAL_INVALID,
    message_key: str = "decimal_invalid",
    stage: int = 2,
) -> str:
    text = _nonempty_string(value, field_path, stage=stage)
    try:
        return decimal_string(parse_decimal(text, positive=positive))
    except CanonicalizationError as exc:
        raise _schema_failure(
            stage,
            (_block(code, field_path, message_key),),
            raw_failing_field=value,
        ) from exc


def _sha(value: Any, field_path: str, *, stage: int = 2) -> str:
    text = _nonempty_string(value, field_path, stage=stage)
    if not _SHA256_RE.fullmatch(text):
        raise _schema_failure(
            stage,
            (_block(BlockerCode.STL_RAW_TYPE_INVALID, field_path, "sha256_hex_required"),),
            raw_failing_field=value,
        )
    return text


def _integer(value: Any, field_path: str, *, minimum: int | None = None, stage: int = 2) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _schema_failure(
            stage,
            (_block(BlockerCode.STL_RAW_TYPE_INVALID, field_path, "integer_required"),),
            raw_failing_field=value,
        )
    if minimum is not None and value < minimum:
        raise _schema_failure(
            stage,
            (_block(BlockerCode.STL_RAW_TYPE_INVALID, field_path, "integer_below_minimum"),),
            raw_failing_field=value,
        )
    return value


def _enum(value: Any, enum_type: type[E], field_path: str, *, stage: int = 2) -> E:
    if not isinstance(value, str):
        raise _schema_failure(
            stage,
            (_block(BlockerCode.STL_RAW_TYPE_INVALID, field_path, "enum_string_required"),),
            raw_failing_field=value,
        )
    try:
        return enum_type(value)
    except ValueError as exc:
        raise _schema_failure(
            stage,
            (
                _block(
                    BlockerCode.STL_RAW_TYPE_INVALID,
                    field_path,
                    "enum_value_invalid",
                    details={"value": value},
                ),
            ),
            raw_failing_field=value,
        ) from exc


def _string_array(
    value: Any, field_path: str, *, allow_empty: bool = True, stage: int = 2
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise _schema_failure(
            stage,
            (_block(BlockerCode.STL_RAW_TYPE_INVALID, field_path, "array_required"),),
            raw_failing_field=value,
        )
    try:
        return sorted_unique_strings(value, allow_empty=allow_empty)
    except (TypeError, ValueError) as exc:
        message_key = "duplicate_array_item" if "duplicate" in str(exc) else "string_array_invalid"
        raise _schema_failure(
            stage,
            (_block(BlockerCode.STL_RAW_TYPE_INVALID, field_path, message_key),),
            raw_failing_field=value,
        ) from exc


def _enum_array(
    value: Any,
    enum_type: type[E],
    field_path: str,
    *,
    allow_empty: bool = False,
    stage: int = 2,
) -> tuple[E, ...]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise _schema_failure(
            stage,
            (_block(BlockerCode.STL_RAW_TYPE_INVALID, field_path, "enum_array_invalid"),),
            raw_failing_field=value,
        )
    items = tuple(_enum(item, enum_type, f"{field_path}[]") for item in value)
    if len(set(items)) != len(items):
        raise _schema_failure(
            stage,
            (_block(BlockerCode.STL_RAW_TYPE_INVALID, field_path, "duplicate_array_item"),),
            raw_failing_field=value,
        )
    order = {member: index for index, member in enumerate(list(enum_type))}
    return tuple(sorted(items, key=order.__getitem__))


def _canonical_json_value(value: Any, field_path: str, *, stage: int = 2) -> Any:
    """Validate a raw value as canonical JSON domain. Fail-closed on rejection.

    Public canonical domain (round 3 P1-1): null/bool/int/str/list/string-keyed
    dict ONLY. Any other type (Decimal, float, bytes, tuple, set, frozenset,
    non-string-keyed mapping, arbitrary object) raises STL_CANONICALIZATION_FAILED.
    """

    try:
        strict_public_json_snapshot(value)
    except Exception as exc:  # PublicCanonicalDomainError is the only expected one
        raise _schema_failure(
            stage,
            (
                _block(
                    BlockerCode.STL_CANONICALIZATION_FAILED,
                    field_path,
                    "canonical_value_invalid",
                    details={"type": type(value).__name__},
                ),
            ),
            raw_failing_field=value,
        ) from exc
    return value


# --------------------------------------------------------------------------- #
# Public canonical mapping (round 3 P1-1)
# --------------------------------------------------------------------------- #


def canonical_mapping(value: Any) -> Any:
    """Validate ``value`` as a public canonical boundary fragment.

    This is the round-3 P1-1 boundary function for any "frozen fragment"
    (license_evidence, MessageEntry.details, etc.). It accepts only the §6.1
    canonical JSON domain. The caller is expected to capture the result and
    treat it as immutable (never re-mutate the original mapping).
    """

    return strict_public_json_snapshot(value)


# --------------------------------------------------------------------------- #
# Stage 1 + Stage 2 + Stage 3 helpers
# --------------------------------------------------------------------------- #


def validate_top_level_mapping(payload: Any) -> Mapping[str, Any]:
    """Stage 1 — top-level mapping and exact field set."""

    return _mapping(payload, "request", set(REQUEST_FIELDS), stage=1, raw_failing_field=payload)


def validate_request_schema_version(value: Any) -> str:
    """Stage 3 — request schema_version (the top-level version check)."""

    text = _nonempty_string(value, "schema_version", stage=3)
    if text != REQUEST_SCHEMA_VERSION:
        raise _schema_failure(
            3,
            (
                _block(
                    BlockerCode.STL_SCHEMA_VERSION_UNSUPPORTED,
                    "schema_version",
                    "request_schema_version_unsupported",
                ),
            ),
            raw_failing_field=value,
        )
    return text


def parse_source_binding(value: Any, field_path: str) -> SourceBindingSnapshot:
    fields = {
        "source_id",
        "source_type",
        "source_revision",
        "source_location",
        "evidence_ref",
        "approved_by",
        "approved_at",
    }
    data = _mapping(value, field_path, fields, stage=2)
    return SourceBindingSnapshot(
        **{name: _nonempty_string(data[name], f"{field_path}.{name}", stage=2) for name in fields}
    )


def parse_rule_pack_identity(value: Any, field_path: str) -> RulePackIdentitySnapshot:
    fields = {"rule_pack_id", "rule_pack_version", "rule_pack_canonical_hash"}
    data = _mapping(value, field_path, fields, stage=2)
    return RulePackIdentitySnapshot(
        rule_pack_id=_nonempty_string(data["rule_pack_id"], f"{field_path}.rule_pack_id", stage=2),
        rule_pack_version=_nonempty_string(
            data["rule_pack_version"], f"{field_path}.rule_pack_version", stage=2
        ),
        rule_pack_canonical_hash=_sha(
            data["rule_pack_canonical_hash"],
            f"{field_path}.rule_pack_canonical_hash",
            stage=2,
        ),
    )


def parse_geometry(value: Any) -> ApprovedTubeGeometrySnapshot:
    """Pure shape / raw-type validation for tube_geometry (Stages 1-3)."""

    if value is None:
        raise _schema_failure(
            2,
            (
                _block(
                    BlockerCode.STL_TUBE_GEOMETRY_MISSING,
                    "tube_geometry",
                    "tube_geometry_missing",
                ),
            ),
            raw_failing_field=None,
        )
    fields = {
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
    }
    data = _mapping(value, "tube_geometry", fields, stage=2)
    outer_diameter_m = _decimal(
        data["outer_diameter_m"],
        "tube_geometry.outer_diameter_m",
        positive=True,
        stage=2,
    )
    inner_diameter_m = _decimal(
        data["inner_diameter_m"],
        "tube_geometry.inner_diameter_m",
        positive=True,
        stage=2,
    )
    wall_thickness_m = _decimal(
        data["wall_thickness_m"],
        "tube_geometry.wall_thickness_m",
        positive=True,
        stage=2,
    )
    return ApprovedTubeGeometrySnapshot(
        geometry_id=_nonempty_string(data["geometry_id"], "tube_geometry.geometry_id", stage=2),
        geometry_type=_nonempty_string(
            data["geometry_type"], "tube_geometry.geometry_type", stage=2
        ),
        revision=_nonempty_string(data["revision"], "tube_geometry.revision", stage=2),
        approval_state=_nonempty_string(
            data["approval_state"], "tube_geometry.approval_state", stage=2
        ),
        outer_diameter_m=outer_diameter_m,
        inner_diameter_m=inner_diameter_m,
        wall_thickness_m=wall_thickness_m,
        record_hash=_sha(data["record_hash"], "tube_geometry.record_hash", stage=2),
        snapshot_hash=_sha(data["snapshot_hash"], "tube_geometry.snapshot_hash", stage=2),
        source_binding=parse_source_binding(data["source_binding"], "tube_geometry.source_binding"),
    )


def parse_layout_rule(value: Any) -> LayoutRuleAuthoritySnapshot:
    """Pure shape / raw-type validation for layout_rule_authority (Stages 1-3)."""

    if value is None:
        raise _schema_failure(
            2,
            (
                _block(
                    BlockerCode.STL_LAYOUT_RULE_AUTHORITY_MISSING,
                    "layout_rule_authority",
                    "layout_rule_authority_missing",
                ),
            ),
            raw_failing_field=None,
        )
    fields = {
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
    }
    data = _mapping(value, "layout_rule_authority", fields, stage=2)
    pitch_m = _decimal(
        data["pitch_m"],
        "layout_rule_authority.pitch_m",
        positive=True,
        code=BlockerCode.STL_PITCH_INVALID,
        message_key="pitch_invalid",
        stage=2,
    )
    edge_clearance_m = _decimal(
        data["edge_clearance_m"],
        "layout_rule_authority.edge_clearance_m",
        positive=False,
        code=BlockerCode.STL_EDGE_CLEARANCE_INVALID,
        message_key="edge_clearance_invalid",
        stage=2,
    )
    rule_pack_raw = data["rule_pack_identity"]
    rule_pack = (
        None
        if rule_pack_raw is None
        else parse_rule_pack_identity(rule_pack_raw, "layout_rule_authority.rule_pack_identity")
    )
    return LayoutRuleAuthoritySnapshot(
        profile_id=_nonempty_string(
            data["profile_id"], "layout_rule_authority.profile_id", stage=2
        ),
        authority_mode=_enum(
            data["authority_mode"],
            AuthorityMode,
            "layout_rule_authority.authority_mode",
            stage=2,
        ),
        rule_id=_nonempty_string(data["rule_id"], "layout_rule_authority.rule_id", stage=2),
        rule_version=_nonempty_string(
            data["rule_version"], "layout_rule_authority.rule_version", stage=2
        ),
        rule_artifact_canonical_hash=_sha(
            data["rule_artifact_canonical_hash"],
            "layout_rule_authority.rule_artifact_canonical_hash",
            stage=2,
        ),
        source_class=_nonempty_string(
            data["source_class"], "layout_rule_authority.source_class", stage=2
        ),
        license_evidence=_canonical_json_value(
            data["license_evidence"],
            "layout_rule_authority.license_evidence",
            stage=2,
        ),
        approval_status=_nonempty_string(
            data["approval_status"],
            "layout_rule_authority.approval_status",
            stage=2,
        ),
        provenance_edge_ids=_string_array(
            data["provenance_edge_ids"],
            "layout_rule_authority.provenance_edge_ids",
            stage=2,
        ),
        evidence_refs=_string_array(
            data["evidence_refs"], "layout_rule_authority.evidence_refs", stage=2
        ),
        rule_pack_identity=rule_pack,
        pattern_family=_enum(
            data["pattern_family"],
            PatternFamily,
            "layout_rule_authority.pattern_family",
            stage=2,
        ),
        pitch_m=pitch_m,
        edge_clearance_m=edge_clearance_m,
        allowed_origin_modes=_enum_array(
            data["allowed_origin_modes"],
            OriginMode,
            "layout_rule_authority.allowed_origin_modes",
            stage=2,
        ),
        allowed_axis_orientations=_enum_array(
            data["allowed_axis_orientations"],
            AxisOrientation,
            "layout_rule_authority.allowed_axis_orientations",
            stage=2,
        ),
        allowed_exclusion_zone_types=_enum_array(
            data["allowed_exclusion_zone_types"],
            ExclusionZoneType,
            "layout_rule_authority.allowed_exclusion_zone_types",
            allow_empty=True,
            stage=2,
        ),
        maximum_candidate_positions=_integer(
            data["maximum_candidate_positions"],
            "layout_rule_authority.maximum_candidate_positions",
            minimum=1,
            stage=2,
        ),
        snapshot_hash=_sha(
            data["snapshot_hash"],
            "layout_rule_authority.snapshot_hash",
            stage=2,
        ),
    )


def parse_envelope(value: Any) -> CircularTubeCenterEnvelope:
    """Pure shape / raw-type validation for the placement envelope (Stages 1-3)."""

    fields = {"schema_version", "tube_center_envelope_diameter_m", "evidence_refs"}
    data = _mapping(value, "placement_envelope", fields, stage=2)
    schema_version_text = _nonempty_string(
        data["schema_version"], "placement_envelope.schema_version", stage=2
    )
    if schema_version_text != ENVELOPE_SCHEMA_VERSION:
        raise _schema_failure(
            3,
            (
                _block(
                    BlockerCode.STL_SCHEMA_VERSION_UNSUPPORTED,
                    "placement_envelope.schema_version",
                    "envelope_schema_version_unsupported",
                ),
            ),
            raw_failing_field=data["schema_version"],
        )
    envelope_diameter_m = _decimal(
        data["tube_center_envelope_diameter_m"],
        "placement_envelope.tube_center_envelope_diameter_m",
        positive=True,
        code=BlockerCode.STL_ENVELOPE_INVALID,
        message_key="envelope_diameter_invalid",
        stage=2,
    )
    return CircularTubeCenterEnvelope(
        schema_version=ENVELOPE_SCHEMA_VERSION,
        tube_center_envelope_diameter_m=envelope_diameter_m,
        evidence_refs=_string_array(
            data["evidence_refs"],
            "placement_envelope.evidence_refs",
            allow_empty=False,
            stage=2,
        ),
    )


def parse_zone(value: Any, index: int) -> ExclusionZone:
    """Stage 10 — exclusion-zone exact shape."""

    field_path = f"exclusion_zones[{index}]"
    fields = {
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
    }
    data = _mapping(value, field_path, fields, stage=10)
    zone_type = _enum(
        data["zone_type"],
        ExclusionZoneType,
        f"{field_path}.zone_type",
        stage=10,
    )
    center_x_m = _decimal(
        data["center_x_m"],
        f"{field_path}.center_x_m",
        code=BlockerCode.STL_EXCLUSION_ZONE_INVALID,
        message_key="exclusion_decimal_invalid",
        stage=10,
    )
    center_y_m = _decimal(
        data["center_y_m"],
        f"{field_path}.center_y_m",
        code=BlockerCode.STL_EXCLUSION_ZONE_INVALID,
        message_key="exclusion_decimal_invalid",
        stage=10,
    )
    clearance_m = _decimal(
        data["clearance_m"],
        f"{field_path}.clearance_m",
        positive=False,
        code=BlockerCode.STL_EXCLUSION_ZONE_INVALID,
        message_key="exclusion_decimal_invalid",
        stage=10,
    )
    width = data["width_m"]
    height = data["height_m"]
    radius = data["radius_m"]
    if zone_type is ExclusionZoneType.AXIS_ALIGNED_RECTANGLE:
        if not isinstance(width, str) or not isinstance(height, str) or radius is not None:
            raise _schema_failure(
                10,
                (
                    _block(
                        BlockerCode.STL_EXCLUSION_ZONE_INVALID,
                        field_path,
                        "rectangle_shape_invalid",
                    ),
                ),
                raw_failing_field=value,
            )
        width = _decimal(
            width,
            f"{field_path}.width_m",
            positive=True,
            code=BlockerCode.STL_EXCLUSION_ZONE_INVALID,
            message_key="rectangle_dimension_invalid",
            stage=10,
        )
        height = _decimal(
            height,
            f"{field_path}.height_m",
            positive=True,
            code=BlockerCode.STL_EXCLUSION_ZONE_INVALID,
            message_key="rectangle_dimension_invalid",
            stage=10,
        )
    else:
        if width is not None or height is not None or not isinstance(radius, str):
            raise _schema_failure(
                10,
                (
                    _block(
                        BlockerCode.STL_EXCLUSION_ZONE_INVALID,
                        field_path,
                        "circle_shape_invalid",
                    ),
                ),
                raw_failing_field=value,
            )
        radius = _decimal(
            radius,
            f"{field_path}.radius_m",
            positive=True,
            code=BlockerCode.STL_EXCLUSION_ZONE_INVALID,
            message_key="circle_radius_invalid",
            stage=10,
        )
    return ExclusionZone(
        zone_id=_nonempty_string(data["zone_id"], f"{field_path}.zone_id", stage=10),
        zone_type=zone_type,
        center_x_m=center_x_m,
        center_y_m=center_y_m,
        clearance_m=clearance_m,
        reason_code=_nonempty_string(data["reason_code"], f"{field_path}.reason_code", stage=10),
        evidence_refs=_string_array(
            data["evidence_refs"],
            f"{field_path}.evidence_refs",
            allow_empty=False,
            stage=10,
        ),
        width_m=width,
        height_m=height,
        radius_m=radius,
    )


def parse_leg(value: Any, field_path: str) -> LatticeIndex:
    data = _mapping(value, field_path, {"u", "v"}, stage=2)
    return LatticeIndex(
        u=_integer(data["u"], f"{field_path}.u", stage=2),
        v=_integer(data["v"], f"{field_path}.v", stage=2),
    )


def parse_pairing_plan(value: Any) -> UTubePairingPlan | None:
    """Pure shape / raw-type validation for the U-tube pairing plan (Stages 1-3)."""

    if value is None:
        return None
    data = _mapping(
        value,
        "u_tube_pairing_plan",
        {"schema_version", "pairs", "evidence_refs", "pairing_plan_hash"},
        stage=2,
    )
    schema_version_text = _nonempty_string(
        data["schema_version"], "u_tube_pairing_plan.schema_version", stage=2
    )
    if schema_version_text != PAIRING_SCHEMA_VERSION:
        raise _schema_failure(
            3,
            (
                _block(
                    BlockerCode.STL_SCHEMA_VERSION_UNSUPPORTED,
                    "u_tube_pairing_plan.schema_version",
                    "pairing_schema_version_unsupported",
                ),
            ),
            raw_failing_field=data["schema_version"],
        )
    raw_pairs = data["pairs"]
    if not isinstance(raw_pairs, list) or not raw_pairs:
        raise _schema_failure(
            2,
            (
                _block(
                    BlockerCode.STL_UTUBE_PAIRING_INVALID,
                    "u_tube_pairing_plan.pairs",
                    "u_tube_pair_raw_shape_invalid",
                ),
            ),
            raw_failing_field=raw_pairs,
        )
    pairs: list[UTubePair] = []
    for index, raw_pair in enumerate(raw_pairs):
        field_path = f"u_tube_pairing_plan.pairs[{index}]"
        pair_data = _mapping(
            raw_pair,
            field_path,
            {"pair_id", "leg_a", "leg_b", "evidence_refs"},
            stage=2,
        )
        pairs.append(
            UTubePair(
                pair_id=_nonempty_string(pair_data["pair_id"], f"{field_path}.pair_id", stage=2),
                leg_a=parse_leg(pair_data["leg_a"], f"{field_path}.leg_a"),
                leg_b=parse_leg(pair_data["leg_b"], f"{field_path}.leg_b"),
                evidence_refs=_string_array(
                    pair_data["evidence_refs"],
                    f"{field_path}.evidence_refs",
                    stage=2,
                ),
            )
        )
    return UTubePairingPlan(
        schema_version=PAIRING_SCHEMA_VERSION,
        pairs=tuple(pairs),
        evidence_refs=_string_array(
            data["evidence_refs"],
            "u_tube_pairing_plan.evidence_refs",
            allow_empty=False,
            stage=2,
        ),
        pairing_plan_hash=_sha(
            data["pairing_plan_hash"],
            "u_tube_pairing_plan.pairing_plan_hash",
            stage=2,
        ),
    )


# Backwards-compatible aggregator for legacy callers/tests.
# New validator code MUST NOT call this — it represents the §9 ordering
# violation that round-3 fixes. Kept only so existing tests still compile.


def parse_request(payload: Any) -> TubeLayoutRequest:
    """Legacy all-at-once parser for tests and pre-existing tooling only.

    Round-3 §3 (P0-1) requires strict 1→21 ordering. The production validator
    does NOT use this function; it runs the per-stage helpers directly. This
    remains for backward compatibility with test helpers and the fixture-based
    acceptance contract.
    """

    data = validate_top_level_mapping(payload)
    validate_request_schema_version(data["schema_version"])
    configuration = data["configuration"]
    if configuration is None:
        raise _schema_failure(
            4,
            (
                _block(
                    BlockerCode.STL_TASK020_CONFIGURATION_MISSING,
                    "configuration",
                    "task020_configuration_missing",
                ),
            ),
            raw_failing_field=None,
        )
    if not isinstance(configuration, ShellAndTubeConfiguration):
        raise _schema_failure(
            4,
            (
                _block(
                    BlockerCode.STL_TASK020_CONFIGURATION_INVALID,
                    "configuration",
                    "task020_configuration_type_invalid",
                ),
            ),
            raw_failing_field=configuration,
        )
    zones_raw = data["exclusion_zones"]
    if not isinstance(zones_raw, list):
        raise _schema_failure(
            10,
            (
                _block(
                    BlockerCode.STL_RAW_TYPE_INVALID,
                    "exclusion_zones",
                    "array_required",
                ),
            ),
            raw_failing_field=zones_raw,
        )
    zones = tuple(
        sorted(
            (parse_zone(item, index) for index, item in enumerate(zones_raw)),
            key=lambda z: z.zone_id,
        )
    )
    if len({zone.zone_id for zone in zones}) != len(zones):
        raise _schema_failure(
            10,
            (
                _block(
                    BlockerCode.STL_EXCLUSION_ZONE_DUPLICATE_ID,
                    "exclusion_zones",
                    "duplicate_zone_id",
                ),
            ),
            raw_failing_field=zones_raw,
        )
    return TubeLayoutRequest(
        schema_version=REQUEST_SCHEMA_VERSION,
        configuration=configuration,
        tube_geometry=parse_geometry(data["tube_geometry"]),
        layout_rule_authority=parse_layout_rule(data["layout_rule_authority"]),
        placement_envelope=parse_envelope(data["placement_envelope"]),
        origin_mode=_enum(data["origin_mode"], OriginMode, "origin_mode", stage=2),
        axis_orientation=_enum(
            data["axis_orientation"], AxisOrientation, "axis_orientation", stage=2
        ),
        exclusion_zones=zones,
        u_tube_pairing_plan=parse_pairing_plan(data["u_tube_pairing_plan"]),
        evidence_refs=_string_array(data["evidence_refs"], "evidence_refs", stage=2),
    )


__all__ = [
    "CanonicalizationError",
    "REQUEST_FIELDS",
    "REQUEST_SCHEMA_VERSION",
    "SchemaFailure",
    "canonical_mapping",
    "canonical_json",
    "parse_envelope",
    "parse_geometry",
    "parse_layout_rule",
    "parse_pairing_plan",
    "parse_request",
    "parse_source_binding",
    "parse_zone",
    "validate_request_schema_version",
    "validate_top_level_mapping",
]
