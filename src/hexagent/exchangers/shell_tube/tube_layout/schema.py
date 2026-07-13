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
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, TypeVar

from hexagent.exchangers.shell_tube.models import ShellAndTubeConfiguration

from .canonical import (
    CanonicalizationError,
    FrozenJsonArray,
    FrozenJsonObject,
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
    """Validate a raw value as canonical JSON domain and return a FROZEN form.

    Round 5 §1.1 (deep immutability): rather than returning the caller-
    owned original (which the caller might mutate after validation), this
    function now returns the strict_public_json_snapshot — a value whose
    mappings are ``MappingProxyType`` and sequences are ``tuple`` of
    canonical atoms. This is the **detached frozen snapshot** the round-5
    spec requires.

    Public canonical domain (round 3 P1-1 + round 5 §1.1): null/bool/int/
    str/list/string-keyed dict ONLY. Any other type (Decimal, float,
    bytes, tuple, set, frozenset, non-string-keyed mapping, arbitrary
    object, dataclass, Enum) raises STL_CANONICALIZATION_FAILED.
    """

    try:
        return strict_public_json_snapshot(value)
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


def _is_frozen_canonical_fragment(value: Any) -> bool:
    """Return True if value is already a strict public canonical fragment.

    Round 7 type-system unification: a strict public canonical fragment
    is either:

    * ``None`` / ``bool`` / ``int`` / ``str`` (canonical atom)
    * :class:`FrozenJsonObject` (the canonical internal-frozen mapping
      container produced by ``strict_public_json_snapshot(dict)``)
    * :class:`FrozenJsonArray` (the canonical internal-frozen array
      container)
    * legacy ``MappingProxyType`` / ``tuple`` (pre-R7 representations,
      still detected for safety-net purposes)

    Anything else (decimal, bytes, dataclass, Enum, ordinary dict,
    ordinary list, set, frozenset) returns False so the caller can
    re-snap.
    """

    if value is None or isinstance(value, (bool, int, str)):
        return True
    if isinstance(value, (FrozenJsonArray, FrozenJsonObject)):
        return True
    from types import MappingProxyType

    return bool(isinstance(value, (tuple, MappingProxyType)))


# --------------------------------------------------------------------------- #
# Stage 2 / Stage 3 collector (round 4 P0-1)
# --------------------------------------------------------------------------- #
#
# Round 4 §3.2 requires that every Stage 2 / Stage 3 check emits its OWN
# complete blocker, that no field's failure short-circuits the rest of the
# stage, and that the strict ordering between Stage 2 and Stage 3 holds even
# when individual helpers internally read schema-version fields. The
# ``Stage2Collector`` accumulates per-field blockers during Stage 2, and the
# ``Stage3Aggregator`` returns the union of schema-version blockers after
# every Stage 2 check has run.
#
# The frozen design contract states "同一个阶段产生的所有完整 blocker 必须保留".
# This collector is the single source of truth: every parser above passes its
# raw Schemafailure through the collector's ``record_failure`` method.


@dataclass(frozen=True)
class Stage2FieldReport:
    """Per-field Stage-2 verification outcome.

    ``value`` is the canonical-primitive form (after Stage-2 normalization)
    or ``None`` if the field's validation failed. ``blockers`` is the complete
    tuple of MessageEntry objects emitted for this field; the empty tuple
    means the field passed Stage 2. ``raw_failing_field`` is the original raw
    value that the field validation rejected (for §12.8 identity bookkeeping).
    """

    field_path: str
    value: Any
    blockers: tuple[MessageEntry, ...] = ()
    raw_failing_field: Any | None = None


@dataclass(frozen=True)
class Stage2Result:
    """Aggregate of all Stage-2 per-field reports.

    The validator instantiates this with one ``Stage2FieldReport`` per top-level
    request field. A failed Stage-2 field is represented by a non-empty
    ``blockers`` tuple; a passed field carries the normalized primitive in
    ``value`` and an empty ``blockers`` tuple. ``all_blockers`` is the union
    of every per-field blocker set.
    """

    request_schema_version: Stage2FieldReport
    configuration: Stage2FieldReport
    tube_geometry: Stage2FieldReport
    layout_rule_authority: Stage2FieldReport
    placement_envelope: Stage2FieldReport
    origin_mode: Stage2FieldReport
    axis_orientation: Stage2FieldReport
    u_tube_pairing_plan: Stage2FieldReport
    evidence_refs: Stage2FieldReport

    @property
    def passed(self) -> bool:
        return all(not report.blockers for report in self._reports)

    @property
    def all_blockers(self) -> tuple[MessageEntry, ...]:
        collected: list[MessageEntry] = []
        for report in self._reports:
            collected.extend(report.blockers)
        return tuple(collected)

    @property
    def raw_failing_fields(self) -> dict[str, Any]:
        """Return only the per-field raw values that triggered a Stage-2 failure."""

        return {
            report.field_path: report.raw_failing_field
            for report in self._reports
            if report.blockers and report.raw_failing_field is not None
        }

    @property
    def failed_field_paths(self) -> tuple[str, ...]:
        """Canonical metadata — just the field paths that triggered a Stage-2 failure.

        Round 5 §4.2: this is the only legitimate stage-2-derived description
        of a failed-field. Raw values are NOT allowed here.
        """

        return tuple(report.field_path for report in self._reports if report.blockers)

    @property
    def primary_raw_failing_field(self) -> Any | None:
        """Return the FIRST failed-field raw value (round 5 §4.2 primary raw).

        ``canonical_raw_json_or_none`` on the §12.8 identity side may decide
        whether to surface the canonical raw (when one exists) or ``None``
        (when the value has no canonical raw — e.g. arbitrary object).
        """

        for report in self._reports:
            if report.blockers and report.raw_failing_field is not None:
                return report.raw_failing_field
        return None

    @property
    def _reports(self) -> tuple[Stage2FieldReport, ...]:
        return (
            self.request_schema_version,
            self.configuration,
            self.tube_geometry,
            self.layout_rule_authority,
            self.placement_envelope,
            self.origin_mode,
            self.axis_orientation,
            self.u_tube_pairing_plan,
            self.evidence_refs,
        )


def _safe_stage2(
    *,
    field_path: str,
    parser: Callable[[], Any],
) -> Stage2FieldReport:
    """Run a Stage-2 parser, collecting any ``SchemaFailure`` blockers.

    The parser MUST already use ``stage=2`` for every internal check. The
    returned report carries the canonical primitive form when the parser
    succeeds, or the full blockers tuple when it fails.
    """

    try:
        value = parser()
    except SchemaFailure as exc:
        return Stage2FieldReport(
            field_path=field_path,
            value=None,
            blockers=exc.blockers,
            raw_failing_field=exc.raw_failing_field,
        )
    return Stage2FieldReport(field_path=field_path, value=value)


def collect_stage2(payload: Mapping[str, Any]) -> Stage2Result:
    """Run every Stage-2 parser and accumulate per-field complete blockers.

    This is the round-4 §3.2 collector. Each top-level field produces its
    OWN Stage-2 report; no per-field failure short-circuits the others. The
    returned ``Stage2Result`` is the single source of truth that downstream
    Stage-3 schema-version validation reads after every field has been
    checked at Stage 2.
    """

    return Stage2Result(
        request_schema_version=_safe_stage2(
            field_path="schema_version",
            parser=lambda: _validate_request_schema_version_raw(payload.get("schema_version")),
        ),
        configuration=_safe_stage2(
            field_path="configuration",
            parser=lambda: _validate_configuration_shape(payload["configuration"]),
        ),
        tube_geometry=_safe_stage2(
            field_path="tube_geometry",
            parser=lambda: parse_geometry(payload["tube_geometry"]),
        ),
        layout_rule_authority=_safe_stage2(
            field_path="layout_rule_authority",
            parser=lambda: parse_layout_rule(payload["layout_rule_authority"]),
        ),
        placement_envelope=_safe_stage2(
            field_path="placement_envelope",
            parser=lambda: parse_envelope_raw(payload["placement_envelope"]),
        ),
        origin_mode=_safe_stage2(
            field_path="origin_mode",
            parser=lambda: _enum(payload["origin_mode"], OriginMode, "origin_mode"),
        ),
        axis_orientation=_safe_stage2(
            field_path="axis_orientation",
            parser=lambda: _enum(payload["axis_orientation"], AxisOrientation, "axis_orientation"),
        ),
        u_tube_pairing_plan=_safe_stage2(
            field_path="u_tube_pairing_plan",
            parser=lambda: parse_pairing_plan_raw(payload["u_tube_pairing_plan"]),
        ),
        evidence_refs=_safe_stage2(
            field_path="evidence_refs",
            parser=lambda: _string_array(payload["evidence_refs"], "evidence_refs"),
        ),
    )


def _validate_configuration_shape(value: Any) -> ShellAndTubeConfiguration:
    """Stage-2 configuration shape check.

    The TASK-020 fragment is constructed upstream; Stage 2 only checks raw
    type / null / expected dataclass instance. Future rounds may extend
    schema_version/raw-fields validation here if §9 Stage 4 ever moves.
    """

    if value is None:
        raise _schema_failure(
            2,
            (
                _block(
                    BlockerCode.STL_RAW_TYPE_INVALID,
                    "configuration",
                    "configuration_null",
                ),
            ),
            raw_failing_field=None,
        )
    if not isinstance(value, ShellAndTubeConfiguration):
        raise _schema_failure(
            2,
            (
                _block(
                    BlockerCode.STL_RAW_TYPE_INVALID,
                    "configuration",
                    "configuration_wrong_type",
                    details={"actual_type": type(value).__name__},
                ),
            ),
            raw_failing_field=value,
        )
    return value


@dataclass(frozen=True)
class Stage3Result:
    """Aggregate of all Stage-3 schema-version blockers."""

    blockers: tuple[MessageEntry, ...]
    failed_field_paths: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.blockers


def _validate_request_schema_version_raw(value: Any) -> str:
    """Stage 2 — top-level request schema_version raw type check (NO version compare).

    Round 5 §3.1: Stage 2 verifies that ``value`` is a non-empty string; it
    does NOT compare it against the expected version. Stage 3 does the
    version comparison after Stage 2 has finished. This function raises
    SchemaFailure with complete Stage-2 blockers on raw-type failure.
    """

    if not isinstance(value, str) or not value:
        raise _schema_failure(
            2,
            (
                _block(
                    BlockerCode.STL_RAW_TYPE_INVALID,
                    "schema_version",
                    "schema_version_raw_type_invalid",
                    details={
                        "actual_type": type(value).__name__,
                        "expected_type": "str",
                    },
                ),
            ),
            raw_failing_field=value,
        )
    return value


def validate_all_schema_versions(
    request_schema_version: str,
    envelope_schema_version: str,
    envelope_field_path: str,
    pairing_schema_version: str | None,
    pairing_field_path: str | None,
) -> Stage3Result:
    """Stage 3 — ALL schema versions checked atomically AFTER Stage 2 ends.

    Round 5 §3 refines round 4: all three schema-version inputs are now
    pre-validated non-empty strings (Stage 2 is responsible for raw-type
    checking). Stage 3 only does version equality comparison and emits
    the COMPLETE set of unsupported-version blockers, never partial.

    The returned ``failed_field_paths`` carries the field paths that
    triggered a Stage-3 failure for round-5 §4.2 canonical metadata.
    Raw failing values are NOT included — only field paths.
    """

    blockers: list[MessageEntry] = []
    failed_field_paths: list[str] = []

    if request_schema_version != REQUEST_SCHEMA_VERSION:
        blockers.append(
            _block(
                BlockerCode.STL_SCHEMA_VERSION_UNSUPPORTED,
                "schema_version",
                "request_schema_version_unsupported",
            )
        )
        failed_field_paths.append("schema_version")

    if envelope_schema_version != ENVELOPE_SCHEMA_VERSION:
        blockers.append(
            _block(
                BlockerCode.STL_SCHEMA_VERSION_UNSUPPORTED,
                envelope_field_path,
                "envelope_schema_version_unsupported",
            )
        )
        failed_field_paths.append(envelope_field_path)

    if pairing_field_path is not None:
        if pairing_schema_version is None:
            blockers.append(
                _block(
                    BlockerCode.STL_RAW_TYPE_INVALID,
                    pairing_field_path,
                    "pairing_schema_version_missing",
                )
            )
            failed_field_paths.append(pairing_field_path)
        elif pairing_schema_version != PAIRING_SCHEMA_VERSION:
            blockers.append(
                _block(
                    BlockerCode.STL_SCHEMA_VERSION_UNSUPPORTED,
                    pairing_field_path,
                    "pairing_schema_version_unsupported",
                )
            )
            failed_field_paths.append(pairing_field_path)

    return Stage3Result(
        blockers=tuple(blockers),
        failed_field_paths=tuple(failed_field_paths),
    )


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


# --------------------------------------------------------------------------- #
# Stage-2 nested-object complete-blocker accumulator (round-5 §5)
# --------------------------------------------------------------------------- #


@dataclass
class StageAccumulator:
    """Round-5 §5: per-field independent Stage-2 validator accumulator.

    Each per-field validator is registered via ``capture``; a failing
    validator contributes its complete ``MessageEntry`` blockers without
    short-circuiting sibling fields. The accumulator keeps two parallel
    views: ``blockers`` (the union of every failed-field ``MessageEntry``)
    and ``values`` (the validated values keyed by field path).
    """

    blockers: list[MessageEntry] = field(default_factory=list)
    values: dict[str, Any] = field(default_factory=dict)

    def capture(self, field_path: str, validator: Callable[[], Any]) -> None:
        try:
            self.values[field_path] = validator()
        except SchemaFailure as exc:
            self.blockers.extend(exc.blockers)

    def finalize(self, *, object_path: str | None = None) -> Mapping[str, Any]:
        """Return the accumulated values mapping if ``blockers`` is empty,
        otherwise raise a single SchemaFailure combining every blocker."""

        if not self.blockers:
            return self.values
        raise _schema_failure(
            2,
            tuple(self.blockers),
            raw_failing_field=None,
        )


def parse_geometry(value: Any) -> ApprovedTubeGeometrySnapshot:
    """Pure shape / raw-type validation for tube_geometry (Stages 1-3).

    Round 5 §5.2: per-field raw checks are independent; each failing field
    contributes its complete blockers without skipping the rest. Only when
    the outer mapping check fails is the entire nested-validation skipped.
    """

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

    # Outer mapping shape check; preserve at-least-one blocker when
    # the input isn't a mapping.
    try:
        data = _mapping(value, "tube_geometry", fields, stage=2)
    except SchemaFailure as exc:
        raise SchemaFailure(
            2,
            exc.blockers,
            raw_failing_field=exc.raw_failing_field,
        ) from exc

    # Per-field raw validators run independently.
    acc = StageAccumulator()

    def _nonempty_field(field: str) -> Callable[[], str]:
        def _v() -> str:
            return _nonempty_string(data[field], f"tube_geometry.{field}", stage=2)

        _v.__name__ = f"_g_nonempty_{field}"
        return _v

    def _sha_field(field: str) -> Callable[[], str]:
        def _v() -> str:
            return _sha(data[field], f"tube_geometry.{field}", stage=2)

        _v.__name__ = f"_g_sha_{field}"
        return _v

    def _decimal_field(field: str, *, positive: bool = True) -> Callable[[], str]:
        def _v() -> str:
            return _decimal(
                data[field],
                f"tube_geometry.{field}",
                positive=positive,
                stage=2,
            )

        _v.__name__ = f"_decimal_{field}"
        return _v

    acc.capture("geometry_id", _nonempty_field("geometry_id"))
    acc.capture("geometry_type", _nonempty_field("geometry_type"))
    acc.capture("revision", _nonempty_field("revision"))
    acc.capture("approval_state", _nonempty_field("approval_state"))
    acc.capture("outer_diameter_m", _decimal_field("outer_diameter_m"))
    acc.capture("inner_diameter_m", _decimal_field("inner_diameter_m"))
    acc.capture("wall_thickness_m", _decimal_field("wall_thickness_m"))
    acc.capture("record_hash", _sha_field("record_hash"))
    acc.capture("snapshot_hash", _sha_field("snapshot_hash"))
    acc.capture(
        "source_binding",
        lambda: parse_source_binding(data["source_binding"], "tube_geometry.source_binding"),
    )

    if acc.blockers:
        raise _schema_failure(
            2,
            tuple(acc.blockers),
            raw_failing_field=None,
        )

    return ApprovedTubeGeometrySnapshot(
        geometry_id=acc.values["geometry_id"],
        geometry_type=acc.values["geometry_type"],
        revision=acc.values["revision"],
        approval_state=acc.values["approval_state"],
        outer_diameter_m=acc.values["outer_diameter_m"],
        inner_diameter_m=acc.values["inner_diameter_m"],
        wall_thickness_m=acc.values["wall_thickness_m"],
        record_hash=acc.values["record_hash"],
        snapshot_hash=acc.values["snapshot_hash"],
        source_binding=acc.values["source_binding"],
    )


def parse_layout_rule(value: Any) -> LayoutRuleAuthoritySnapshot:
    """Pure shape / raw-type validation for layout_rule_authority (Stages 1-3).

    Round 5 §5.1: per-field raw checks are independent; each failing field
    contributes its complete blockers without skipping the rest. Only when
    the outer mapping check fails is the entire nested-validation skipped.
    """

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
    try:
        data = _mapping(value, "layout_rule_authority", fields, stage=2)
    except SchemaFailure as exc:
        raise SchemaFailure(
            2,
            exc.blockers,
            raw_failing_field=exc.raw_failing_field,
        ) from exc

    acc = StageAccumulator()

    def _nonempty_field(field: str) -> Callable[[], str]:
        def _v() -> str:
            return _nonempty_string(data[field], f"layout_rule_authority.{field}", stage=2)

        _v.__name__ = f"_lr_nonempty_{field}"
        return _v

    def _sha_field(field: str) -> Callable[[], str]:
        def _v() -> str:
            return _sha(data[field], f"layout_rule_authority.{field}", stage=2)

        _v.__name__ = f"_lr_sha_{field}"
        return _v

    acc.capture("profile_id", _nonempty_field("profile_id"))
    acc.capture(
        "authority_mode",
        lambda: _enum(
            data["authority_mode"],
            AuthorityMode,
            "layout_rule_authority.authority_mode",
            stage=2,
        ),
    )
    acc.capture("rule_id", _nonempty_field("rule_id"))
    acc.capture("rule_version", _nonempty_field("rule_version"))
    acc.capture("rule_artifact_canonical_hash", _sha_field("rule_artifact_canonical_hash"))
    acc.capture("source_class", _nonempty_field("source_class"))
    acc.capture(
        "license_evidence",
        lambda: _canonical_json_value(
            data["license_evidence"],
            "layout_rule_authority.license_evidence",
            stage=2,
        ),
    )
    acc.capture("approval_status", _nonempty_field("approval_status"))
    acc.capture(
        "provenance_edge_ids",
        lambda: _string_array(
            data["provenance_edge_ids"],
            "layout_rule_authority.provenance_edge_ids",
            stage=2,
        ),
    )
    acc.capture(
        "evidence_refs",
        lambda: _string_array(
            data["evidence_refs"],
            "layout_rule_authority.evidence_refs",
            stage=2,
        ),
    )

    def _rule_pack() -> Any:
        rule_pack_raw = data["rule_pack_identity"]
        if rule_pack_raw is None:
            return None
        return parse_rule_pack_identity(rule_pack_raw, "layout_rule_authority.rule_pack_identity")

    acc.capture("rule_pack_identity", _rule_pack)
    acc.capture(
        "pattern_family",
        lambda: _enum(
            data["pattern_family"],
            PatternFamily,
            "layout_rule_authority.pattern_family",
            stage=2,
        ),
    )
    acc.capture(
        "pitch_m",
        lambda: _decimal(
            data["pitch_m"],
            "layout_rule_authority.pitch_m",
            positive=True,
            code=BlockerCode.STL_PITCH_INVALID,
            message_key="pitch_invalid",
            stage=2,
        ),
    )
    acc.capture(
        "edge_clearance_m",
        lambda: _decimal(
            data["edge_clearance_m"],
            "layout_rule_authority.edge_clearance_m",
            positive=False,
            code=BlockerCode.STL_EDGE_CLEARANCE_INVALID,
            message_key="edge_clearance_invalid",
            stage=2,
        ),
    )
    acc.capture(
        "allowed_origin_modes",
        lambda: _enum_array(
            data["allowed_origin_modes"],
            OriginMode,
            "layout_rule_authority.allowed_origin_modes",
            stage=2,
        ),
    )
    acc.capture(
        "allowed_axis_orientations",
        lambda: _enum_array(
            data["allowed_axis_orientations"],
            AxisOrientation,
            "layout_rule_authority.allowed_axis_orientations",
            stage=2,
        ),
    )
    acc.capture(
        "allowed_exclusion_zone_types",
        lambda: _enum_array(
            data["allowed_exclusion_zone_types"],
            ExclusionZoneType,
            "layout_rule_authority.allowed_exclusion_zone_types",
            allow_empty=True,
            stage=2,
        ),
    )
    acc.capture(
        "maximum_candidate_positions",
        lambda: _integer(
            data["maximum_candidate_positions"],
            "layout_rule_authority.maximum_candidate_positions",
            minimum=1,
            stage=2,
        ),
    )
    acc.capture("snapshot_hash", _sha_field("snapshot_hash"))

    if acc.blockers:
        raise _schema_failure(
            2,
            tuple(acc.blockers),
            raw_failing_field=None,
        )

    # Round-5 §1: license_evidence must be a frozen canonical fragment.
    # We post-process the validated value here.
    license_evidence_frozen = acc.values["license_evidence"]
    if not _is_frozen_canonical_fragment(license_evidence_frozen):
        # Re-snap to canonical if validator left a non-frozen value.
        license_evidence_frozen = _canonical_json_value(
            data["license_evidence"],
            "layout_rule_authority.license_evidence",
            stage=2,
        )

    return LayoutRuleAuthoritySnapshot(
        profile_id=acc.values["profile_id"],
        authority_mode=acc.values["authority_mode"],
        rule_id=acc.values["rule_id"],
        rule_version=acc.values["rule_version"],
        rule_artifact_canonical_hash=acc.values["rule_artifact_canonical_hash"],
        source_class=acc.values["source_class"],
        license_evidence=license_evidence_frozen,
        approval_status=acc.values["approval_status"],
        provenance_edge_ids=acc.values["provenance_edge_ids"],
        evidence_refs=acc.values["evidence_refs"],
        rule_pack_identity=acc.values["rule_pack_identity"],
        pattern_family=acc.values["pattern_family"],
        pitch_m=acc.values["pitch_m"],
        edge_clearance_m=acc.values["edge_clearance_m"],
        allowed_origin_modes=acc.values["allowed_origin_modes"],
        allowed_axis_orientations=acc.values["allowed_axis_orientations"],
        allowed_exclusion_zone_types=acc.values["allowed_exclusion_zone_types"],
        maximum_candidate_positions=acc.values["maximum_candidate_positions"],
        snapshot_hash=acc.values["snapshot_hash"],
    )


def parse_envelope_raw(value: Any) -> EnvelopeRaw:
    """Stage-2-only raw parser for the placement envelope.

    Round 4 §3.1 + round 5 §5.3: this function MUST NOT compare
    schema_version against the expected version, and per-field raw
    checks (schema_version/tube_center_envelope_diameter_m/evidence_refs)
    run independently through the ``StageAccumulator`` so that multiple
    failures all surface as complete blockers.

    Only shape / raw-type / numeric-shape work happens here. The round-3
    public boundary still rejects non-canonical mapping shapes.
    """

    fields = {"schema_version", "tube_center_envelope_diameter_m", "evidence_refs"}
    try:
        data = _mapping(value, "placement_envelope", fields, stage=2)
    except SchemaFailure as exc:
        raise SchemaFailure(
            2,
            exc.blockers,
            raw_failing_field=exc.raw_failing_field,
        ) from exc

    acc = StageAccumulator()
    acc.capture(
        "schema_version",
        lambda: _nonempty_string(
            data["schema_version"],
            "placement_envelope.schema_version",
            stage=2,
        ),
    )
    acc.capture(
        "tube_center_envelope_diameter_m",
        lambda: _decimal(
            data["tube_center_envelope_diameter_m"],
            "placement_envelope.tube_center_envelope_diameter_m",
            positive=True,
            code=BlockerCode.STL_ENVELOPE_INVALID,
            message_key="envelope_diameter_invalid",
            stage=2,
        ),
    )
    acc.capture(
        "evidence_refs",
        lambda: _string_array(
            data["evidence_refs"],
            "placement_envelope.evidence_refs",
            allow_empty=False,
            stage=2,
        ),
    )

    if acc.blockers:
        raise _schema_failure(
            2,
            tuple(acc.blockers),
            raw_failing_field=None,
        )

    return EnvelopeRaw(
        schema_version=acc.values["schema_version"],
        tube_center_envelope_diameter_m=acc.values["tube_center_envelope_diameter_m"],
        evidence_refs=acc.values["evidence_refs"],
    )


@dataclass(frozen=True)
class EnvelopeRaw:
    """Stage-2 placement-envelope raw value preservation.

    Round 4 §3.1 keeps the schema_version string in this intermediate
    dataclass; Stage 3 compares it against the expected version AFTER every
    Stage-2 raw-type check has completed. The legacy constructor path
    accepts this raw form and constructs the canonical
    :class:`CircularTubeCenterEnvelope` only when the schema_version check
    passes.
    """

    schema_version: str
    tube_center_envelope_diameter_m: str
    evidence_refs: tuple[str, ...]


def parse_envelope_payload(value: Any) -> CircularTubeCenterEnvelope:
    """Legacy envelope parser retained for backward compatibility.

    Performs Stage-2 raw validation AND Stage-3 schema_version comparison
    in one call. Round-4 callers MUST use
    :func:`parse_envelope_raw` + :func:`validate_all_schema_versions` to keep
    Stage 2 / Stage 3 strictly separated; this legacy helper exists only for
    fixture builder compatibility.
    """

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


def parse_envelope(value: Any) -> CircularTubeCenterEnvelope:
    """Default public envelope parser.

    Accepts either a raw mapping (Stage-2 + Stage-3 in one call) OR a
    pre-validated :class:`EnvelopeRaw` (from Stage-2-only raw collection
    followed by Stage 3). Round 4 keeps both call sites working.

    Callers that want strict Stage-2-then-Stage-3 separation MUST use
    :func:`parse_envelope_raw` + :func:`validate_all_schema_versions` and
    then construct :class:`CircularTubeCenterEnvelope` directly from the
    Stage-2-preserved raw + Stage-3-verified schema_version.
    """

    if isinstance(value, EnvelopeRaw):
        return CircularTubeCenterEnvelope(
            schema_version=ENVELOPE_SCHEMA_VERSION,
            tube_center_envelope_diameter_m=value.tube_center_envelope_diameter_m,
            evidence_refs=value.evidence_refs,
        )
    raw = parse_envelope_raw(value)
    if raw.schema_version != ENVELOPE_SCHEMA_VERSION:
        raise _schema_failure(
            3,
            (
                _block(
                    BlockerCode.STL_SCHEMA_VERSION_UNSUPPORTED,
                    "placement_envelope.schema_version",
                    "envelope_schema_version_unsupported",
                ),
            ),
            raw_failing_field=raw.schema_version,
        )
    return CircularTubeCenterEnvelope(
        schema_version=ENVELOPE_SCHEMA_VERSION,
        tube_center_envelope_diameter_m=raw.tube_center_envelope_diameter_m,
        evidence_refs=raw.evidence_refs,
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


@dataclass(frozen=True)
class PairingPlanRaw:
    """Stage-2 pairing-plan raw value preservation.

    Round 4 §3.1 keeps the schema_version string and the validated pairs in
    this intermediate dataclass; Stage 3 compares schema_version against
    the expected version AFTER every other Stage-2 check has completed.
    """

    schema_version: str | None
    pairs: tuple[UTubePair, ...]
    evidence_refs: tuple[str, ...]
    pairing_plan_hash: str


def parse_pairing_plan_raw(value: Any) -> PairingPlanRaw | None:
    """Stage-2-only raw parser for the U-tube pairing plan.

    Round 4 §3.1 + round 5 §5.3: schema_version is preserved verbatim
    (or ``None`` when the plan itself is absent). Per-field raw checks
    run independently through the ``StageAccumulator`` so multiple
    failures all surface as complete blockers.

    Pair-pair shape validation (Stage 2 numeric / array raw types) DOES
    happen here because that is exactly what Stage 2 is for. Only the
    schema_version comparison is deferred.
    """

    if value is None:
        return None
    try:
        data = _mapping(
            value,
            "u_tube_pairing_plan",
            {"schema_version", "pairs", "evidence_refs", "pairing_plan_hash"},
            stage=2,
        )
    except SchemaFailure as exc:
        raise SchemaFailure(
            2,
            exc.blockers,
            raw_failing_field=exc.raw_failing_field,
        ) from exc

    acc = StageAccumulator()
    acc.capture(
        "schema_version",
        lambda: _nonempty_string(
            data["schema_version"],
            "u_tube_pairing_plan.schema_version",
            stage=2,
        ),
    )

    # Round-5 §5.3: pair-array raw check runs independently from the
    # other top-level fields.
    def _pairs_check() -> tuple[UTubePair, ...]:
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

        built_pairs: list[UTubePair] = []
        for index, raw_pair in enumerate(raw_pairs):
            inner_field_path = f"u_tube_pairing_plan.pairs[{index}]"
            try:
                pair_data = _mapping(
                    raw_pair,
                    inner_field_path,
                    {"pair_id", "leg_a", "leg_b", "evidence_refs"},
                    stage=2,
                )
            except SchemaFailure as exc:
                # Round-5 §5.3: when one pair's shape fails we surface
                # its blocker but continue validating the rest of the
                # pairs — at the outer accumulator boundary. We push
                # the blocker into the parent accumulator via the
                # exception chain.
                raise SchemaFailure(
                    2,
                    exc.blockers,
                    raw_failing_field=exc.raw_failing_field,
                ) from exc
            built_pairs.append(
                UTubePair(
                    pair_id=_nonempty_string(
                        pair_data["pair_id"], f"{inner_field_path}.pair_id", stage=2
                    ),
                    leg_a=parse_leg(pair_data["leg_a"], f"{inner_field_path}.leg_a"),
                    leg_b=parse_leg(pair_data["leg_b"], f"{inner_field_path}.leg_b"),
                    evidence_refs=_string_array(
                        pair_data["evidence_refs"],
                        f"{inner_field_path}.evidence_refs",
                        stage=2,
                    ),
                )
            )
        return tuple(built_pairs)

    acc.capture("pairs", _pairs_check)
    acc.capture(
        "evidence_refs",
        lambda: _string_array(
            data["evidence_refs"],
            "u_tube_pairing_plan.evidence_refs",
            allow_empty=False,
            stage=2,
        ),
    )
    acc.capture(
        "pairing_plan_hash",
        lambda: _sha(
            data["pairing_plan_hash"],
            "u_tube_pairing_plan.pairing_plan_hash",
            stage=2,
        ),
    )

    if acc.blockers:
        raise _schema_failure(
            2,
            tuple(acc.blockers),
            raw_failing_field=None,
        )

    return PairingPlanRaw(
        schema_version=acc.values["schema_version"],
        pairs=acc.values["pairs"],
        evidence_refs=acc.values["evidence_refs"],
        pairing_plan_hash=acc.values["pairing_plan_hash"],
    )


def parse_pairing_plan(value: Any) -> UTubePairingPlan | None:
    """Pure shape / raw-type validation for the U-tube pairing plan (Stages 1-3)."""

    raw = parse_pairing_plan_raw(value)
    if raw is None:
        return None
    if raw.schema_version != PAIRING_SCHEMA_VERSION:
        raise _schema_failure(
            3,
            (
                _block(
                    BlockerCode.STL_SCHEMA_VERSION_UNSUPPORTED,
                    "u_tube_pairing_plan.schema_version",
                    "pairing_schema_version_unsupported",
                ),
            ),
            raw_failing_field=raw.schema_version,
        )
    return UTubePairingPlan(
        schema_version=PAIRING_SCHEMA_VERSION,
        pairs=raw.pairs,
        evidence_refs=raw.evidence_refs,
        pairing_plan_hash=raw.pairing_plan_hash,
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
    "EnvelopeRaw",
    "PairingPlanRaw",
    "REQUEST_FIELDS",
    "REQUEST_SCHEMA_VERSION",
    "SchemaFailure",
    "Stage2FieldReport",
    "Stage2Result",
    "Stage3Result",
    "canonical_mapping",
    "canonical_json",
    "collect_stage2",
    "parse_envelope",
    "parse_envelope_raw",
    "parse_geometry",
    "parse_layout_rule",
    "parse_pairing_plan",
    "parse_pairing_plan_raw",
    "parse_request",
    "parse_source_binding",
    "parse_zone",
    "validate_all_schema_versions",
    "validate_request_schema_version",
    "validate_top_level_mapping",
]
