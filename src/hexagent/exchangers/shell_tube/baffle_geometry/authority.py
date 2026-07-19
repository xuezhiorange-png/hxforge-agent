"""TASK-024 Round 4 authority validation foundation.

This module implements the **in-memory** authority-validation foundation
that lives between the Stage-1 schema parser and the Stage-9 geometry
foundation. It accepts a fully-typed :class:`BaffleGeometryRequest`
whose upstream objects (``ShellAndTubeConfiguration``, ``TubeLayout``,
``ShellBundleGeometry``) and caller-supplied authorities
(``CallerSuppliedBaffleAxialSpan``, ``CallerSuppliedBaffleDesignAuthority``)
have already been parsed by the Stage-1 schema parser. It does not
accept raw mappings, does not handle :class:`BaffleGeometrySchemaFailure`,
and does not construct a public
:class:`BaffleGeometryValidationResult`.

Stages implemented (Section 7 + 8 of the TASK-024 design contract):

- Stage 2 — TASK-020 configuration validation (typed configuration only).
- Stage 3 — TASK-021 layout validation (typed layout only).
- Stage 4 — TASK-022 geometry validation (typed geometry only).
- Stage 5 — three-way upstream cross-binding (configuration ↔ layout ↔ geometry).
- Stage 6 — supported v1 slice (FIXED_TUBESHEET / shell-pass 1 / SINGLE_SEGMENTAL).
- Stage 7 — axial authority identity (exact hash recompute).
- Stage 8 — design authority identity (exact hash recompute).

Stages 9 through 19 are explicitly **deferred** to later rounds. This
module does not read any TASK-023 catalog, does not compute any baffle
geometry, does not emit a public validation result, does not compute a
public request_hash / geometry_hash / blocked_result_hash / provenance.

Pure-in-memory architecture (Section 7 of design contract):

- No filesystem / network / database / environment / clock / locale /
  random / subprocess / dynamic-import access.
- No second canonical JSON serializer; reuses
  ``baffle_geometry.canonical.canonical_json_bytes`` and
  ``baffle_geometry.canonical.sha256_canonical``.
- No ``dataclasses.asdict``; no runtime field discovery; no
  ``str(object)``; no JSON default fallback; no binary float.
- All upstream-hash recompute paths either delegate to the existing
  TASK-020 canonical ``canonical_payload`` + ``configuration_hash`` +
  ``configuration_id`` triple, or rebuild a frozen literal payload
  dict with hardcoded field names.

All public-facing message codes are sourced from
:class:`baffle_geometry.models.BlockerCode` and
:class:`baffle_geometry.models.WarningCode` (Section 11 + 12 of the
design contract). The module-local result type
:class:`_AuthorityFoundationResult` is **module-private** and is **not**
exported through ``__all__``. No public dataclass is added.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final

from hexagent.exchangers.shell_tube import canonical as _task020_canonical
from hexagent.exchangers.shell_tube.baffle_geometry import (
    canonical as _t024_canonical,
)
from hexagent.exchangers.shell_tube.baffle_geometry import (
    models as _t024,
)
from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
    canonical as _task022_canonical,
)
from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
    models as _task022,
)
from hexagent.exchangers.shell_tube.tube_layout import (
    canonical as _task021_canonical,
)
from hexagent.exchangers.shell_tube.tube_layout import (
    models as _task021,
)
from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    internal_frozen_to_primitive,
)

# ---------------------------------------------------------------------------
# Stage rank constants (Section 6.3 / Section 10 of the design contract).
# ---------------------------------------------------------------------------

_STAGE_2_RANK: Final[int] = 2
_STAGE_3_RANK: Final[int] = 3
_STAGE_4_RANK: Final[int] = 4
_STAGE_5_RANK: Final[int] = 5
_STAGE_6_RANK: Final[int] = 6
_STAGE_7_RANK: Final[int] = 7
_STAGE_8_RANK: Final[int] = 8
_LAST_STAGE_RANK: Final[int] = 8

# Schema version tokens for the upstream objects (frozen at the
# corresponding TASK-020/021/022 design contracts).
_TASK020_CONFIGURATION_SCHEMA: Final[str] = "task020.configuration.v1"
_TASK021_TUBE_LAYOUT_SCHEMA: Final[str] = "task021.tube-layout.v1"
_TASK022_SHELL_BUNDLE_GEOMETRY_SCHEMA: Final[str] = "task022.shell-bundle-geometry.v1"

# Axial-span and design-authority schema versions (Section 8.1 / 8.2).
_AXIAL_SPAN_SCHEMA: Final[str] = _t024.AXIAL_SPAN_SCHEMA_VERSION
_DESIGN_AUTHORITY_SCHEMA: Final[str] = _t024.DESIGN_AUTHORITY_SCHEMA_VERSION

# Supported v1 slice (Section 6.2 / 3.2).
_SUPPORTED_CONSTRUCTION_FAMILY: Final[str] = "FIXED_TUBESHEET"
_SUPPORTED_SHELL_PASS_COUNT: Final[int] = 1
_SUPPORTED_BAFFLE_TYPE_TOKEN: Final[str] = "SINGLE_SEGMENTAL"

# Lowercase 64-character SHA-256 hex pattern.
_SHA256_HEX_PATTERN: Final[str] = "0123456789abcdef"
_SHA256_HEX_LENGTH: Final[int] = 64


# ---------------------------------------------------------------------------
# Module-private result and warning/context types (Section 6.3).
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _RankedMessage:
    """Module-private record binding a message to its stage rank."""

    validation_stage_rank: int
    entry: _t024.MessageEntry


@dataclass(frozen=True, slots=True)
class _AuthorityFoundationResult:
    """Module-private result of the Round-4 authority foundation.

    Not exported. Not part of the public canonical projection. Used by
    later ``validation.py`` to assemble a public result.
    """

    request: _t024.BaffleGeometryRequest
    completed_stage_rank: int
    warnings: tuple[_t024.MessageEntry, ...]
    blockers: tuple[_t024.MessageEntry, ...]


# ---------------------------------------------------------------------------
# Internal helpers — message construction and ordering.
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


def _evidence_refs_sort_key(
    evidence_refs: tuple[str, ...],
) -> str:
    """Deterministic projection of evidence_refs for the global sort key."""
    return _t024_canonical.canonical_json_bytes(list(evidence_refs)).decode("ascii")


def _details_sort_key(details: tuple[tuple[str, str], ...]) -> str:
    """Deterministic projection of details for the global sort key."""
    return _t024_canonical.canonical_json_bytes([list(pair) for pair in details]).decode("ascii")


def _global_sort_key(ranked: _RankedMessage) -> tuple[int, str, str, str, str, str]:
    """Global deterministic ordering key (Section 13 of the design contract).

    Tuple ordering matches the brief verbatim:

        (
            validation_stage_rank,
            code,
            field_path_or_empty,
            message_key,
            sha256(canonical_details),
            sha256(canonical_evidence_refs),
        )
    """
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


def _sort_messages(messages: tuple[_RankedMessage, ...]) -> tuple[_RankedMessage, ...]:
    return tuple(sorted(messages, key=_global_sort_key))


# ---------------------------------------------------------------------------
# Stage 2 — TASK-020 configuration validation.
# ---------------------------------------------------------------------------


def _stage2_validate(
    request: _t024.BaffleGeometryRequest,
) -> tuple[tuple[_RankedMessage, ...], tuple[_RankedMessage, ...]]:
    """Validate the supplied ``ShellAndTubeConfiguration`` object.

    Returns ``(blockers, warnings)``. ``warnings`` is always empty for
    Stage 2 by design (Section 8 of the brief).
    """
    from hexagent.exchangers.shell_tube import (
        models as _t020,
    )

    configuration = request.configuration
    blockers: list[_RankedMessage] = []

    if type(configuration) is not _t020.ShellAndTubeConfiguration:
        blockers.append(
            _rank_blocker(
                _STAGE_2_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK020_CONFIGURATION_INVALID.value,
                    field_path="configuration",
                    message_key="task020_configuration_exact_type_required",
                    details=(("actual_type", type(configuration).__name__),),
                ),
            )
        )
        return tuple(blockers), ()

    if configuration.schema_version != _TASK020_CONFIGURATION_SCHEMA:
        blockers.append(
            _rank_blocker(
                _STAGE_2_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK020_CONFIGURATION_INVALID.value,
                    field_path="configuration.schema_version",
                    message_key="task020_configuration_schema_version_unsupported",
                    details=(("actual", configuration.schema_version),),
                ),
            )
        )

    if configuration.equipment_family.value != "SHELL_AND_TUBE":
        blockers.append(
            _rank_blocker(
                _STAGE_2_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK020_CONFIGURATION_INVALID.value,
                    field_path="configuration.equipment_family",
                    message_key="task020_configuration_equipment_family_invalid",
                    details=(("actual", configuration.equipment_family.value),),
                ),
            )
        )

    if configuration.blockers:
        blockers.append(
            _rank_blocker(
                _STAGE_2_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK020_CONFIGURATION_INVALID.value,
                    field_path="configuration.blockers",
                    message_key="task020_configuration_upstream_blockers_present",
                    details=(("blocker_count", str(len(configuration.blockers))),),
                ),
            )
        )

    # Required case authority presence.
    if configuration.case_authority is None:  # pragma: no cover - guarded by call site
        blockers.append(
            _rank_blocker(
                _STAGE_2_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK020_CONFIGURATION_INVALID.value,
                    field_path="configuration.case_authority",
                    message_key="task020_configuration_case_authority_missing",
                ),
            )
        )

    # Required authority binding presence.
    if configuration.authority_binding is None:  # pragma: no cover - guarded by call site
        blockers.append(
            _rank_blocker(
                _STAGE_2_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK020_CONFIGURATION_INVALID.value,
                    field_path="configuration.authority_binding",
                    message_key="task020_configuration_authority_binding_missing",
                ),
            )
        )

    if blockers:
        return tuple(blockers), ()

    # Recompute the configuration hash using TASK-020's canonical pipeline.
    primitive = _task020_primitive(configuration)
    primitive_authority_binding = primitive["authority_binding"]
    payload = _task020_canonical.canonical_payload(
        primitive,
        case_authority=primitive["case_authority"],
        evaluated_rule_pack_authority=primitive_authority_binding.get(
            "evaluated_rule_pack_authority"
        ),
        canonical_warnings=primitive["warnings"],
        canonical_blockers=primitive["blockers"],
        deferred_capabilities=primitive["deferred_capabilities"],
        authority_binding=primitive_authority_binding,
        schema_version=configuration.schema_version,
    )
    expected_hash = _task020_canonical.configuration_hash(payload)
    expected_id = _task020_canonical.configuration_id(expected_hash)
    if (
        expected_hash != configuration.configuration_hash
        or expected_id != configuration.configuration_id
    ):
        blockers.append(
            _rank_blocker(
                _STAGE_2_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK020_CONFIGURATION_IDENTITY_MISMATCH.value,
                    field_path="configuration",
                    message_key="task020_configuration_identity_mismatch",
                    details=(
                        ("expected_hash", expected_hash),
                        ("expected_id", expected_id),
                    ),
                ),
            )
        )

    return tuple(blockers), ()


def _task020_primitive(configuration: Any) -> dict[str, Any]:
    """Return the manual literal projection of ``ShellAndTubeConfiguration``.

    The field list is hardcoded (no runtime discovery). Enum values are
    projected via ``.value``; tuple fields are kept as tuples.
    """

    def _component_tokens_to_primitive(tokens: Any) -> dict[str, Any]:
        return {
            "front_head": tokens.front_head,
            "shell": tokens.shell,
            "rear_head": tokens.rear_head,
        }

    def _case_authority_to_primitive(case: Any) -> dict[str, Any]:
        return {
            "revision_id": case.revision_id,
            "payload_hash": case.payload_hash,
            "domain_snapshot_hash": case.domain_snapshot_hash,
            "revision_status": case.revision_status.value,
        }

    def _authority_binding_to_primitive(binding: Any) -> dict[str, Any]:
        case = _case_authority_to_primitive(binding.case_authority)
        evaluated = binding.evaluated_rule_pack_authority
        evaluated_primitive: dict[str, Any] | None
        if evaluated is None:
            evaluated_primitive = None
        else:
            selected: list[dict[str, Any]] = []
            for item in evaluated.selected_rule_authorities:
                selected.append(
                    {
                        "rule_id": item.rule_id,
                        "rule_version": item.rule_version,
                        "rule_artifact_canonical_hash": item.rule_artifact_canonical_hash,
                        "source_class": item.source_class,
                        "license_evidence": dict(item.license_evidence),
                        "approval_status": item.approval_status,
                        "provenance_edge_ids": list(item.provenance_edge_ids),
                        "evidence_refs": list(item.evidence_refs),
                    }
                )
            evaluated_primitive = {
                "rule_pack_id": evaluated.rule_pack_id,
                "rule_pack_version": evaluated.rule_pack_version,
                "rule_pack_canonical_hash": evaluated.rule_pack_canonical_hash,
                "validation_status": evaluated.validation_status,
                "selected_rule_authorities": selected,
            }
        return {
            "authority_mode": binding.authority_mode.value,
            "standard_system_id": binding.standard_system_id,
            "case_authority": case,
            "evaluated_rule_pack_authority": evaluated_primitive,
            "case_authority_evidence_refs": list(binding.case_authority_evidence_refs),
        }

    return {
        "schema_version": configuration.schema_version,
        "equipment_family": configuration.equipment_family.value,
        "authority_mode": configuration.authority_mode.value,
        "standard_claim_status": configuration.standard_claim_status.value,
        "construction_family": configuration.construction_family.value,
        "orientation": configuration.orientation.value,
        "shell_pass_count": configuration.shell_pass_count,
        "tube_pass_count": configuration.tube_pass_count,
        "component_tokens": _component_tokens_to_primitive(configuration.component_tokens),
        "case_authority": _case_authority_to_primitive(configuration.case_authority),
        "warnings": [dict(w) for w in configuration.warnings],
        "blockers": [dict(b) for b in configuration.blockers],
        "deferred_capabilities": list(configuration.deferred_capabilities),
        "authority_binding": _authority_binding_to_primitive(configuration.authority_binding),
    }


# ---------------------------------------------------------------------------
# Stage 3 — TASK-021 layout validation.
# ---------------------------------------------------------------------------


def _stage3_validate(
    request: _t024.BaffleGeometryRequest,
) -> tuple[tuple[_RankedMessage, ...], tuple[_RankedMessage, ...]]:
    """Validate the supplied ``TubeLayout`` object."""
    layout = request.tube_layout
    blockers: list[_RankedMessage] = []

    if type(layout) is not _task021.TubeLayout:
        blockers.append(
            _rank_blocker(
                _STAGE_3_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK021_LAYOUT_INVALID.value,
                    field_path="tube_layout",
                    message_key="task021_layout_exact_type_required",
                    details=(("actual_type", type(layout).__name__),),
                ),
            )
        )
        return tuple(blockers), ()

    if layout.schema_version != _TASK021_TUBE_LAYOUT_SCHEMA:
        blockers.append(
            _rank_blocker(
                _STAGE_3_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK021_LAYOUT_INVALID.value,
                    field_path="tube_layout.schema_version",
                    message_key="task021_layout_schema_version_unsupported",
                    details=(("actual", layout.schema_version),),
                ),
            )
        )

    if layout.blockers:
        blockers.append(
            _rank_blocker(
                _STAGE_3_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK021_LAYOUT_HAS_BLOCKERS.value,
                    field_path="tube_layout.blockers",
                    message_key="task021_layout_upstream_blockers_present",
                    details=(("blocker_count", str(len(layout.blockers))),),
                ),
            )
        )

    if not layout.positions:
        blockers.append(
            _rank_blocker(
                _STAGE_3_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK021_LAYOUT_HAS_NO_POSITIONS.value,
                    field_path="tube_layout.positions",
                    message_key="task021_layout_has_no_positions",
                ),
            )
        )

    # Duplicate position_id check.
    seen_ids: set[str] = set()
    duplicates: list[str] = []
    for pos in layout.positions:
        if pos.position_id in seen_ids:
            duplicates.append(pos.position_id)
        seen_ids.add(pos.position_id)
    if duplicates:
        blockers.append(
            _rank_blocker(
                _STAGE_3_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK021_LAYOUT_IDENTITY_MISMATCH.value,
                    field_path="tube_layout.positions",
                    message_key="task021_layout_duplicate_position_ids",
                    details=(("duplicates", ",".join(sorted(set(duplicates)))),),
                ),
            )
        )

    # tube_hole_count consistency.
    if layout.tube_hole_count != len(layout.positions):
        blockers.append(
            _rank_blocker(
                _STAGE_3_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK021_LAYOUT_IDENTITY_MISMATCH.value,
                    field_path="tube_layout.tube_hole_count",
                    message_key="task021_layout_tube_hole_count_mismatch",
                    details=(
                        ("expected", str(len(layout.positions))),
                        ("actual", str(layout.tube_hole_count)),
                    ),
                ),
            )
        )

    if blockers:
        return tuple(blockers), ()

    # Identity recompute: rebuild the layout_hash_payload exactly as
    # tube_layout/validation.py does (Section 14 of TASK-021 design) and
    # verify both the hash and the derived id match the stored values.
    payload = _task021_layout_hash_payload(layout)
    expected_hash = _task021_canonical.sha256_hex(payload)
    expected_id = _task021_canonical.layout_id(expected_hash)
    if expected_hash != layout.layout_hash or expected_id != layout.layout_id:
        blockers.append(
            _rank_blocker(
                _STAGE_3_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK021_LAYOUT_IDENTITY_MISMATCH.value,
                    field_path="tube_layout",
                    message_key="task021_layout_identity_mismatch",
                    details=(
                        ("expected_hash", expected_hash),
                        ("expected_id", expected_id),
                    ),
                ),
            )
        )

    return tuple(blockers), ()


def _task021_layout_hash_payload(layout: Any) -> dict[str, Any]:
    """Return the literal frozen layout_hash_payload used by TASK-021.

    Mirrors tube_layout/validation.py:1317-1357 exactly so the hash
    recompute is byte-equivalent. Uses hardcoded field names; no
    runtime field discovery.
    """
    positions: list[dict[str, Any]] = []
    for pos in layout.positions:
        positions.append(
            {
                "position_id": pos.position_id,
                "u": pos.u,
                "v": pos.v,
                "x_m": pos.x_m,
                "y_m": pos.y_m,
            }
        )
    exclusion_audit: list[dict[str, Any]] = []
    for audit in layout.exclusion_audit:
        exclusion_audit.append(
            {
                "zone_id": audit.zone_id,
                "rejected_position_count": audit.rejected_position_count,
                "reason_code": audit.reason_code,
                "evidence_refs": list(audit.evidence_refs),
            }
        )
    warnings: list[dict[str, Any]] = []
    for w in layout.warnings:
        warnings.append(
            {
                "code": w.code,
                "field_path": w.field_path,
                "message_key": w.message_key,
                "evidence_refs": list(w.evidence_refs),
                "details": w.details,
            }
        )
    return {
        "schema_version": layout.schema_version,
        "request_hash": layout.request_hash,
        "positions": positions,
        "tube_hole_count": layout.tube_hole_count,
        "physical_tube_count": layout.physical_tube_count,
        "boundary_rejection_count": layout.boundary_rejection_count,
        "exclusion_rejection_count": layout.exclusion_rejection_count,
        "exclusion_audit": exclusion_audit,
        "warnings": warnings,
        "blockers": [],
        "deferred_capabilities": list(layout.deferred_capabilities),
        "provenance_pre_hash": _task021_layout_provenance_pre_hash(layout),
    }


def _task021_layout_provenance_pre_hash(layout: Any) -> dict[str, Any]:
    """Reconstruct the provenance-pre-hash fragment by hardcoded fields.

    The fragment stored on a valid ``TubeLayout.provenance`` is the
    TASK-021 ``provenance_pre_hash`` payload (Section 14.5 of the
    TASK-021 design). Stage 3 rebuilds it via hardcoded field access
    (no runtime discovery) so that ``sha256_hex(layout_hash_payload)``
    reproduces the stored ``layout_hash``.
    """
    # ``layout.provenance`` is a FrozenJsonObject (Layer-B marker);
    # reduce it to a plain primitive mapping before walking.
    prov = internal_frozen_to_primitive(layout.provenance)
    case_authority = _task020_case_authority_primitive(prov["task020_case_authority"])
    geometry_source = _task021_source_binding_primitive(prov["geometry_source_binding"])
    rule_pack_raw = prov["rule_pack_identity"]
    if rule_pack_raw is None:
        rule_pack: dict[str, Any] | None = None
    else:
        rule_pack = _task021_rule_pack_identity_primitive(rule_pack_raw)
    layout_rule_evidence_refs = list(prov["layout_rule_evidence_refs"])
    exclusion_zone_evidence_refs = [list(refs) for refs in prov["exclusion_zone_evidence_refs"]]
    u_tube_pairing_evidence_refs_raw = prov["u_tube_pairing_evidence_refs"]
    u_tube_pairing_evidence_refs: list[str] | None = (
        None if u_tube_pairing_evidence_refs_raw is None else list(u_tube_pairing_evidence_refs_raw)
    )
    warnings_list: list[dict[str, Any]] = []
    for w in prov["warnings"]:
        warnings_list.append(
            {
                "code": w["code"],
                "field_path": w["field_path"],
                "message_key": w["message_key"],
                "evidence_refs": list(w["evidence_refs"]),
                "details": w["details"],
            }
        )
    deferred_capabilities = list(prov["deferred_capabilities"])
    return {
        "task_id": prov["task_id"],
        "design_contract_path": prov["design_contract_path"],
        "task020_configuration_id": prov["task020_configuration_id"],
        "task020_configuration_hash": prov["task020_configuration_hash"],
        "task020_case_authority": case_authority,
        "geometry_id": prov["geometry_id"],
        "geometry_revision": prov["geometry_revision"],
        "geometry_record_hash": prov["geometry_record_hash"],
        "tube_geometry_snapshot_hash": prov["tube_geometry_snapshot_hash"],
        "geometry_source_binding": geometry_source,
        "layout_rule_profile_id": prov["layout_rule_profile_id"],
        "layout_rule_id": prov["layout_rule_id"],
        "layout_rule_version": prov["layout_rule_version"],
        "rule_artifact_canonical_hash": prov["rule_artifact_canonical_hash"],
        "layout_rule_snapshot_hash": prov["layout_rule_snapshot_hash"],
        "source_class": prov["source_class"],
        "approval_status": prov["approval_status"],
        "provenance_edge_ids": list(prov["provenance_edge_ids"]),
        "layout_rule_evidence_refs": layout_rule_evidence_refs,
        "rule_pack_identity": rule_pack,
        "envelope_evidence_refs": list(prov["envelope_evidence_refs"]),
        "exclusion_zone_evidence_refs": exclusion_zone_evidence_refs,
        "u_tube_pairing_evidence_refs": u_tube_pairing_evidence_refs,
        "software_version": prov["software_version"],
        "git_commit": prov["git_commit"],
        "request_hash": prov["request_hash"],
        "warnings": warnings_list,
        "deferred_capabilities": deferred_capabilities,
    }


def _task020_case_authority_primitive(case: Any) -> dict[str, Any]:
    return {
        "revision_id": case["revision_id"],
        "payload_hash": case["payload_hash"],
        "domain_snapshot_hash": case["domain_snapshot_hash"],
        "revision_status": case["revision_status"],
    }


def _task021_source_binding_primitive(source: Any) -> dict[str, Any]:
    return {
        "source_id": source["source_id"],
        "source_type": source["source_type"],
        "source_revision": source["source_revision"],
        "source_location": source["source_location"],
        "evidence_ref": source["evidence_ref"],
        "approved_by": source["approved_by"],
        "approved_at": source["approved_at"],
    }


def _task021_rule_pack_identity_primitive(identity: Any) -> dict[str, Any]:
    return {
        "rule_pack_id": identity["rule_pack_id"],
        "rule_pack_version": identity["rule_pack_version"],
        "rule_pack_canonical_hash": identity["rule_pack_canonical_hash"],
    }


# ---------------------------------------------------------------------------
# Stage 4 — TASK-022 geometry validation.
# ---------------------------------------------------------------------------


def _stage4_validate(
    request: _t024.BaffleGeometryRequest,
) -> tuple[tuple[_RankedMessage, ...], tuple[_RankedMessage, ...]]:
    """Validate the supplied ``ShellBundleGeometry`` object."""
    geometry = request.shell_bundle_geometry
    blockers: list[_RankedMessage] = []

    if type(geometry) is not _task022.ShellBundleGeometry:
        blockers.append(
            _rank_blocker(
                _STAGE_4_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK022_GEOMETRY_INVALID.value,
                    field_path="shell_bundle_geometry",
                    message_key="task022_geometry_exact_type_required",
                    details=(("actual_type", type(geometry).__name__),),
                ),
            )
        )
        return tuple(blockers), ()

    if geometry.schema_version != _TASK022_SHELL_BUNDLE_GEOMETRY_SCHEMA:
        blockers.append(
            _rank_blocker(
                _STAGE_4_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK022_GEOMETRY_INVALID.value,
                    field_path="shell_bundle_geometry.schema_version",
                    message_key="task022_geometry_schema_version_unsupported",
                    details=(("actual", geometry.schema_version),),
                ),
            )
        )

    if geometry.blockers:
        blockers.append(
            _rank_blocker(
                _STAGE_4_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK022_GEOMETRY_HAS_BLOCKERS.value,
                    field_path="shell_bundle_geometry.blockers",
                    message_key="task022_geometry_upstream_blockers_present",
                    details=(("blocker_count", str(len(geometry.blockers))),),
                ),
            )
        )

    if not geometry.shell_inside_diameter_m:
        blockers.append(
            _rank_blocker(
                _STAGE_4_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK022_GEOMETRY_INVALID.value,
                    field_path="shell_bundle_geometry.shell_inside_diameter_m",
                    message_key="task022_geometry_shell_inside_diameter_missing",
                ),
            )
        )

    if blockers:
        return tuple(blockers), ()

    # Identity recompute: rebuild the geometry_hash_payload exactly as
    # shell_bundle_geometry/validation.py does (Section 14 of TASK-022
    # design) and verify both the hash and the derived id match the
    # stored values.
    payload = _task022_geometry_hash_payload(geometry)
    expected_hash = _task021_canonical.sha256_hex(payload)
    expected_id = _task022_canonical.geometry_id(expected_hash)
    if expected_hash != geometry.geometry_hash or expected_id != geometry.geometry_id:
        blockers.append(
            _rank_blocker(
                _STAGE_4_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_TASK022_GEOMETRY_IDENTITY_MISMATCH.value,
                    field_path="shell_bundle_geometry",
                    message_key="task022_geometry_identity_mismatch",
                    details=(
                        ("expected_hash", expected_hash),
                        ("expected_id", expected_id),
                    ),
                ),
            )
        )

    return tuple(blockers), ()


def _task022_geometry_hash_payload(geometry: Any) -> dict[str, Any]:
    """Reconstruct the geometry_hash_payload used by TASK-022 validation.

    Mirrors shell_bundle_geometry/validation.py:430-460 exactly. The
    literal field list is hardcoded; no runtime field discovery.
    """
    warnings: list[dict[str, Any]] = []
    for w in geometry.warnings:
        warnings.append(
            {
                "code": w.code,
                "field_path": w.field_path,
                "message_key": w.message_key,
                "evidence_refs": list(w.evidence_refs),
                "details": w.details,
            }
        )
    return {
        "schema_version": geometry.schema_version,
        "request_hash": geometry.request_hash,
        "task020_configuration_id": geometry.task020_configuration_id,
        "task020_configuration_hash": geometry.task020_configuration_hash,
        "task021_layout_id": geometry.task021_layout_id,
        "task021_layout_hash": geometry.task021_layout_hash,
        "tube_geometry_snapshot_hash": geometry.tube_geometry_snapshot_hash,
        "shell_inside_diameter_m": geometry.shell_inside_diameter_m,
        "warnings": warnings,
        "blockers": [],
        "deferred_capabilities": list(geometry.deferred_capabilities),
        "provenance_pre_hash": _task022_provenance_pre_hash(geometry),
    }


def _task022_provenance_pre_hash(geometry: Any) -> dict[str, Any]:
    """Reconstruct the TASK-022 ``provenance_pre_hash`` payload.

    The stored ``geometry.provenance`` is the deterministic primitive
    mapping built by TASK-022 validation; Stage 4 rebuilds it
    field-by-field (no runtime discovery).
    """
    prov = internal_frozen_to_primitive(geometry.provenance)
    return {
        "task_id": prov["task_id"],
        "design_contract_path": prov["design_contract_path"],
        "task020_configuration_id": prov["task020_configuration_id"],
        "task020_configuration_hash": prov["task020_configuration_hash"],
        "task021_layout_id": prov["task021_layout_id"],
        "task021_layout_hash": prov["task021_layout_hash"],
        "task020_case_authority": _task020_case_authority_primitive(prov["task020_case_authority"]),
        "tube_geometry_snapshot_hash": prov["tube_geometry_snapshot_hash"],
        "geometry_source_binding": _task021_source_binding_primitive(
            prov["geometry_source_binding"]
        ),
        "shell_authority_mode": prov["shell_authority_mode"],
        "caller_supplied_shell": _task022_caller_supplied_shell_primitive(
            prov["caller_supplied_shell"]
        ),
        "approved_shell_geometry": _task022_approved_shell_primitive(
            prov["approved_shell_geometry"]
        ),
        "geometry_rule_authority": _task022_rule_authority_primitive(
            prov["geometry_rule_authority"]
        ),
        "shell_inside_diameter_m": prov["shell_inside_diameter_m"],
        "shell_radius_m": prov["shell_radius_m"],
        "bare_tube_bundle_radius_m": prov["bare_tube_bundle_radius_m"],
        "bare_tube_bundle_diameter_m": prov["bare_tube_bundle_diameter_m"],
        "bundle_peripheral_allowance_m": prov["bundle_peripheral_allowance_m"],
        "bundle_outer_envelope_radius_m": prov["bundle_outer_envelope_radius_m"],
        "bundle_outer_envelope_diameter_m": prov["bundle_outer_envelope_diameter_m"],
        "shell_to_bundle_radial_clearance_m": prov["shell_to_bundle_radial_clearance_m"],
        "shell_to_bundle_diametral_clearance_m": prov["shell_to_bundle_diametral_clearance_m"],
        "required_minimum_radial_clearance_m": prov["required_minimum_radial_clearance_m"],
        "radial_clearance_margin_m": prov["radial_clearance_margin_m"],
        "limiting_position_ids": list(prov["limiting_position_ids"]),
        "position_count": prov["position_count"],
        "warnings": [
            {
                "code": w["code"],
                "field_path": w["field_path"],
                "message_key": w["message_key"],
                "evidence_refs": list(w["evidence_refs"]),
                "details": w["details"],
            }
            for w in prov["warnings"]
        ],
        "deferred_capabilities": list(prov["deferred_capabilities"]),
        "software_version": prov["software_version"],
        "git_commit": prov["git_commit"],
    }


def _task022_caller_supplied_shell_primitive(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "schema_version": value["schema_version"],
        "shell_inside_diameter_m": value["shell_inside_diameter_m"],
        "evidence_refs": list(value["evidence_refs"]),
        "authority_hash": value["authority_hash"],
    }


def _task022_approved_shell_primitive(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "schema_version": value["schema_version"],
        "geometry_id": value["geometry_id"],
        "geometry_type": value["geometry_type"],
        "revision": value["revision"],
        "approval_state": value["approval_state"],
        "shell_inside_diameter_m": value["shell_inside_diameter_m"],
        "record_hash": value["record_hash"],
        "source_binding": _task021_source_binding_primitive(value["source_binding"]),
        "snapshot_hash": value["snapshot_hash"],
    }


def _task022_rule_authority_primitive(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    rule_pack = value["rule_pack_identity"]
    return {
        "schema_version": value["schema_version"],
        "profile_id": value["profile_id"],
        "authority_mode": value["authority_mode"],
        "rule_id": value["rule_id"],
        "rule_version": value["rule_version"],
        "rule_artifact_canonical_hash": value["rule_artifact_canonical_hash"],
        "source_class": value["source_class"],
        "license_evidence": dict(value["license_evidence"]),
        "approval_status": value["approval_status"],
        "provenance_edge_ids": list(value["provenance_edge_ids"]),
        "evidence_refs": list(value["evidence_refs"]),
        "rule_pack_identity": (
            None
            if rule_pack is None
            else {
                "rule_pack_id": rule_pack["rule_pack_id"],
                "rule_pack_version": rule_pack["rule_pack_version"],
                "rule_pack_canonical_hash": rule_pack["rule_pack_canonical_hash"],
            }
        ),
        "allowed_shell_authority_modes": list(value["allowed_shell_authority_modes"]),
        "minimum_bundle_peripheral_allowance_m": value["minimum_bundle_peripheral_allowance_m"],
        "minimum_radial_clearance_m": value["minimum_radial_clearance_m"],
        "maximum_position_count": value["maximum_position_count"],
        "snapshot_hash": value["snapshot_hash"],
    }


# ---------------------------------------------------------------------------
# Stage 5 — three-way upstream cross-binding.
# ---------------------------------------------------------------------------


def _stage5_validate(
    request: _t024.BaffleGeometryRequest,
) -> tuple[tuple[_RankedMessage, ...], tuple[_RankedMessage, ...]]:
    """Cross-bind configuration ↔ layout ↔ geometry fields.

    Aggregates every independent deterministic mismatch encountered.
    No first-error-only short-circuiting within Stage 5.
    """
    configuration = request.configuration
    layout = request.tube_layout
    geometry = request.shell_bundle_geometry
    blockers: list[_RankedMessage] = []

    configuration_id_match = configuration.configuration_id == layout.task020_configuration_id
    configuration_hash_match = configuration.configuration_hash == layout.task020_configuration_hash
    if not (configuration_id_match and configuration_hash_match):
        blockers.append(
            _rank_blocker(
                _STAGE_5_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_UPSTREAM_CONFIGURATION_BINDING_MISMATCH.value,
                    field_path="tube_layout",
                    message_key="upstream_configuration_binding_mismatch",
                    details=(
                        ("expected_id", configuration.configuration_id),
                        ("actual_id", layout.task020_configuration_id),
                        ("expected_hash", configuration.configuration_hash),
                        ("actual_hash", layout.task020_configuration_hash),
                    ),
                ),
            )
        )

    layout_id_match = layout.layout_id == geometry.task021_layout_id
    layout_hash_match = layout.layout_hash == geometry.task021_layout_hash
    if not (layout_id_match and layout_hash_match):
        blockers.append(
            _rank_blocker(
                _STAGE_5_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_UPSTREAM_LAYOUT_BINDING_MISMATCH.value,
                    field_path="shell_bundle_geometry",
                    message_key="upstream_layout_binding_mismatch",
                    details=(
                        ("expected_id", layout.layout_id),
                        ("actual_id", geometry.task021_layout_id),
                        ("expected_hash", layout.layout_hash),
                        ("actual_hash", geometry.task021_layout_hash),
                    ),
                ),
            )
        )

    layout_snapshot_hash = layout.tube_geometry.snapshot_hash
    if layout_snapshot_hash != geometry.tube_geometry_snapshot_hash:
        blockers.append(
            _rank_blocker(
                _STAGE_5_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_UPSTREAM_TUBE_GEOMETRY_BINDING_MISMATCH.value,
                    field_path="shell_bundle_geometry",
                    message_key="upstream_tube_geometry_binding_mismatch",
                    details=(
                        ("expected_snapshot_hash", layout_snapshot_hash),
                        ("actual_snapshot_hash", geometry.tube_geometry_snapshot_hash),
                    ),
                ),
            )
        )

    family_match = (
        configuration.construction_family.value
        == layout.construction_family
        == geometry.construction_family
    )
    if not family_match:
        blockers.append(
            _rank_blocker(
                _STAGE_5_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_UPSTREAM_CONSTRUCTION_FAMILY_MISMATCH.value,
                    field_path="configuration",
                    message_key="upstream_construction_family_mismatch",
                    details=(
                        ("configuration_family", configuration.construction_family.value),
                        ("layout_family", layout.construction_family),
                        ("geometry_family", geometry.construction_family),
                    ),
                ),
            )
        )

    orientation_match = (
        configuration.orientation.value
        == layout.equipment_orientation
        == geometry.equipment_orientation
    )
    if not orientation_match:
        blockers.append(
            _rank_blocker(
                _STAGE_5_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_UPSTREAM_ORIENTATION_MISMATCH.value,
                    field_path="configuration",
                    message_key="upstream_orientation_mismatch",
                    details=(
                        ("configuration_orientation", configuration.orientation.value),
                        ("layout_orientation", layout.equipment_orientation),
                        ("geometry_orientation", geometry.equipment_orientation),
                    ),
                ),
            )
        )

    shell_pass_match = (
        configuration.shell_pass_count == layout.shell_pass_count == geometry.shell_pass_count
    )
    if not shell_pass_match:
        blockers.append(
            _rank_blocker(
                _STAGE_5_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_UPSTREAM_PASS_COUNT_MISMATCH.value,
                    field_path="configuration",
                    message_key="upstream_pass_count_mismatch",
                    details=(
                        ("configuration_shell_pass", str(configuration.shell_pass_count)),
                        ("layout_shell_pass", str(layout.shell_pass_count)),
                        ("geometry_shell_pass", str(geometry.shell_pass_count)),
                        ("configuration_tube_pass", str(configuration.tube_pass_count)),
                        ("layout_tube_pass", str(layout.tube_pass_count)),
                        ("geometry_tube_pass", str(geometry.tube_pass_count)),
                    ),
                ),
            )
        )

    position_count_match = (
        layout.tube_hole_count == len(layout.positions) == geometry.position_count
    )
    if not position_count_match:
        blockers.append(
            _rank_blocker(
                _STAGE_5_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_UPSTREAM_POSITION_COUNT_MISMATCH.value,
                    field_path="tube_layout",
                    message_key="upstream_position_count_mismatch",
                    details=(
                        ("layout_tube_hole_count", str(layout.tube_hole_count)),
                        ("layout_position_count", str(len(layout.positions))),
                        ("geometry_position_count", str(geometry.position_count)),
                    ),
                ),
            )
        )

    return tuple(blockers), ()


# ---------------------------------------------------------------------------
# Stage 6 — supported v1 slice.
# ---------------------------------------------------------------------------


def _stage6_validate(
    request: _t024.BaffleGeometryRequest,
) -> tuple[tuple[_RankedMessage, ...], tuple[_RankedMessage, ...]]:
    """Validate supported v1 slice and emit the four baseline warnings."""
    configuration = request.configuration
    design_authority = request.design_authority
    blockers: list[_RankedMessage] = []

    if configuration.construction_family.value != _SUPPORTED_CONSTRUCTION_FAMILY:
        blockers.append(
            _rank_blocker(
                _STAGE_6_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_CONSTRUCTION_FAMILY_UNSUPPORTED.value,
                    field_path="configuration.construction_family",
                    message_key="construction_family_unsupported",
                    details=(("actual", configuration.construction_family.value),),
                ),
            )
        )

    if configuration.shell_pass_count != _SUPPORTED_SHELL_PASS_COUNT:
        blockers.append(
            _rank_blocker(
                _STAGE_6_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_SHELL_PASS_COUNT_UNSUPPORTED.value,
                    field_path="configuration.shell_pass_count",
                    message_key="shell_pass_count_unsupported",
                    details=(("actual", str(configuration.shell_pass_count)),),
                ),
            )
        )

    if design_authority.baffle_type.value != _SUPPORTED_BAFFLE_TYPE_TOKEN:
        blockers.append(
            _rank_blocker(
                _STAGE_6_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_BAFFLE_TYPE_UNSUPPORTED.value,
                    field_path="design_authority.baffle_type",
                    message_key="baffle_type_unsupported",
                    details=(("actual", design_authority.baffle_type.value),),
                ),
            )
        )

    if blockers:
        return tuple(blockers), ()

    warnings: list[_RankedMessage] = [
        _rank_warning(
            _STAGE_6_RANK,
            _make_message(
                _t024.WarningCode.BFG_FIXED_TUBESHEET_ONLY_V1.value,
                field_path="configuration.construction_family",
                message_key="fixed_tubesheet_only_v1",
                evidence_refs=request.evidence_refs,
                details=(("construction_family", _SUPPORTED_CONSTRUCTION_FAMILY),),
            ),
        ),
        _rank_warning(
            _STAGE_6_RANK,
            _make_message(
                _t024.WarningCode.BFG_GEOMETRY_NOT_FLOW_AREA.value,
                field_path=None,
                message_key="geometry_not_flow_area",
                evidence_refs=request.evidence_refs,
                details=(("flow_area_calculation_performed", "false"),),
            ),
        ),
        _rank_warning(
            _STAGE_6_RANK,
            _make_message(
                _t024.WarningCode.BFG_NOZZLE_POSITION_DEFERRED.value,
                field_path=None,
                message_key="nozzle_position_deferred",
                evidence_refs=request.evidence_refs,
                details=(("nozzle_position_inference_performed", "false"),),
            ),
        ),
        _rank_warning(
            _STAGE_6_RANK,
            _make_message(
                _t024.WarningCode.BFG_THERMAL_HYDRAULIC_DEFERRED.value,
                field_path=None,
                message_key="thermal_hydraulic_deferred",
                evidence_refs=request.evidence_refs,
                details=(("thermal_hydraulic_calculation_performed", "false"),),
            ),
        ),
    ]
    return (), tuple(warnings)


# ---------------------------------------------------------------------------
# Stage 7 — axial authority identity.
# ---------------------------------------------------------------------------


def _stage7_validate(
    request: _t024.BaffleGeometryRequest,
) -> tuple[tuple[_RankedMessage, ...], tuple[_RankedMessage, ...]]:
    """Validate the supplied ``CallerSuppliedBaffleAxialSpan`` object.

    Computes the exact SHA-256 of the canonical projection of the
    literal payload ``(schema_version, axial_start_coordinate_m,
    axial_end_coordinate_m, evidence_refs)`` (authority_hash itself is
    excluded) and compares it to ``authority_hash``.
    """
    span = request.axial_span
    blockers: list[_RankedMessage] = []

    if not isinstance(span, _t024.CallerSuppliedBaffleAxialSpan):
        blockers.append(
            _rank_blocker(
                _STAGE_7_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_AXIAL_SPAN_MISSING.value,
                    field_path="axial_span",
                    message_key="axial_span_exact_type_required",
                    details=(("actual_type", type(span).__name__),),
                ),
            )
        )
        return tuple(blockers), ()

    if span.schema_version != _AXIAL_SPAN_SCHEMA:
        blockers.append(
            _rank_blocker(
                _STAGE_7_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_AXIAL_SPAN_SCHEMA_UNSUPPORTED.value,
                    field_path="axial_span.schema_version",
                    message_key="axial_span_schema_version_unsupported",
                    details=(("actual", span.schema_version),),
                ),
            )
        )

    if not span.evidence_refs:
        blockers.append(
            _rank_blocker(
                _STAGE_7_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_AXIAL_SPAN_EVIDENCE_MISSING.value,
                    field_path="axial_span.evidence_refs",
                    message_key="axial_span_evidence_refs_missing",
                ),
            )
        )

    if not _is_lowercase_sha256_hex(span.authority_hash):
        blockers.append(
            _rank_blocker(
                _STAGE_7_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_AXIAL_SPAN_AUTHORITY_HASH_MISMATCH.value,
                    field_path="axial_span.authority_hash",
                    message_key="axial_span_authority_hash_malformed",
                    details=(("actual", span.authority_hash),),
                ),
            )
        )
        return tuple(blockers), ()

    if not _is_sorted_unique_strings(span.evidence_refs):
        blockers.append(
            _rank_blocker(
                _STAGE_7_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_AXIAL_SPAN_EVIDENCE_MISSING.value,
                    field_path="axial_span.evidence_refs",
                    message_key="axial_span_evidence_refs_unsorted_or_duplicate",
                ),
            )
        )
        return tuple(blockers), ()

    expected_hash = _axial_authority_hash(span)
    if expected_hash != span.authority_hash:
        blockers.append(
            _rank_blocker(
                _STAGE_7_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_AXIAL_SPAN_AUTHORITY_HASH_MISMATCH.value,
                    field_path="axial_span.authority_hash",
                    message_key="axial_span_authority_hash_mismatch",
                    details=(
                        ("expected", expected_hash),
                        ("actual", span.authority_hash),
                    ),
                ),
            )
        )

    return tuple(blockers), ()


def _axial_authority_hash(span: _t024.CallerSuppliedBaffleAxialSpan) -> str:
    payload = {
        "axial_end_coordinate_m": span.axial_end_coordinate_m,
        "axial_start_coordinate_m": span.axial_start_coordinate_m,
        "evidence_refs": list(span.evidence_refs),
        "schema_version": span.schema_version,
    }
    return hashlib.sha256(_t024_canonical.canonical_json_bytes(payload)).hexdigest()


# ---------------------------------------------------------------------------
# Stage 8 — design authority identity.
# ---------------------------------------------------------------------------


def _stage8_validate(
    request: _t024.BaffleGeometryRequest,
) -> tuple[tuple[_RankedMessage, ...], tuple[_RankedMessage, ...]]:
    """Validate the supplied ``CallerSuppliedBaffleDesignAuthority`` object.

    Computes the exact SHA-256 of the canonical projection of the
    literal payload (Section 8.2 of the design contract) and emits the
    CALLER_SUPPLIED_NO_STANDARD_CLAIM warning on success.
    """
    authority = request.design_authority
    blockers: list[_RankedMessage] = []

    if not isinstance(authority, _t024.CallerSuppliedBaffleDesignAuthority):
        blockers.append(
            _rank_blocker(
                _STAGE_8_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_DESIGN_AUTHORITY_MISSING.value,
                    field_path="design_authority",
                    message_key="design_authority_exact_type_required",
                    details=(("actual_type", type(authority).__name__),),
                ),
            )
        )
        return tuple(blockers), ()

    if authority.schema_version != _DESIGN_AUTHORITY_SCHEMA:
        blockers.append(
            _rank_blocker(
                _STAGE_8_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_DESIGN_AUTHORITY_SCHEMA_UNSUPPORTED.value,
                    field_path="design_authority.schema_version",
                    message_key="design_authority_schema_version_unsupported",
                    details=(("actual", authority.schema_version),),
                ),
            )
        )

    if not authority.evidence_refs:
        blockers.append(
            _rank_blocker(
                _STAGE_8_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_DESIGN_AUTHORITY_EVIDENCE_MISSING.value,
                    field_path="design_authority.evidence_refs",
                    message_key="design_authority_evidence_refs_missing",
                ),
            )
        )

    if not _is_lowercase_sha256_hex(authority.authority_hash):
        blockers.append(
            _rank_blocker(
                _STAGE_8_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_DESIGN_AUTHORITY_HASH_MISMATCH.value,
                    field_path="design_authority.authority_hash",
                    message_key="design_authority_authority_hash_malformed",
                    details=(("actual", authority.authority_hash),),
                ),
            )
        )
        return tuple(blockers), ()

    if not _is_sorted_unique_strings(authority.evidence_refs):
        blockers.append(
            _rank_blocker(
                _STAGE_8_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_DESIGN_AUTHORITY_EVIDENCE_MISSING.value,
                    field_path="design_authority.evidence_refs",
                    message_key="design_authority_evidence_refs_unsorted_or_duplicate",
                ),
            )
        )
        return tuple(blockers), ()

    if not _is_sorted_enums(authority.orientation_sequence):
        blockers.append(
            _rank_blocker(
                _STAGE_8_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_DESIGN_AUTHORITY_HASH_MISMATCH.value,
                    field_path="design_authority.orientation_sequence",
                    message_key="design_authority_orientation_sequence_unsorted_or_duplicate",
                ),
            )
        )
        return tuple(blockers), ()

    expected_hash = _design_authority_hash(authority)
    if expected_hash != authority.authority_hash:
        blockers.append(
            _rank_blocker(
                _STAGE_8_RANK,
                _make_message(
                    _t024.BlockerCode.BFG_DESIGN_AUTHORITY_HASH_MISMATCH.value,
                    field_path="design_authority.authority_hash",
                    message_key="design_authority_authority_hash_mismatch",
                    details=(
                        ("expected", expected_hash),
                        ("actual", authority.authority_hash),
                    ),
                ),
            )
        )
        return tuple(blockers), ()

    warnings: tuple[_RankedMessage, ...] = (
        _rank_warning(
            _STAGE_8_RANK,
            _make_message(
                _t024.WarningCode.BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM.value,
                field_path="design_authority",
                message_key="caller_supplied_no_standard_claim",
                evidence_refs=authority.evidence_refs,
                details=(
                    ("authority_mode", "CALLER_SUPPLIED_EXPLICIT"),
                    ("standard_claim_status", "NO_STANDARD_CLAIM"),
                ),
            ),
        ),
    )
    return (), warnings


def _design_authority_hash(
    authority: _t024.CallerSuppliedBaffleDesignAuthority,
) -> str:
    payload = {
        "baffle_count": authority.baffle_count,
        "baffle_cut_fraction": authority.baffle_cut_fraction,
        "baffle_thickness_m": authority.baffle_thickness_m,
        "baffle_type": authority.baffle_type.value,
        "evidence_refs": list(authority.evidence_refs),
        "orientation_sequence": [item.value for item in authority.orientation_sequence],
        "schema_version": authority.schema_version,
        "shell_to_baffle_diametral_clearance_m": (authority.shell_to_baffle_diametral_clearance_m),
        "spacing_sequence_m": list(authority.spacing_sequence_m),
        "tube_to_baffle_hole_diametral_clearance_m": (
            authority.tube_to_baffle_hole_diametral_clearance_m
        ),
    }
    return hashlib.sha256(_t024_canonical.canonical_json_bytes(payload)).hexdigest()


# ---------------------------------------------------------------------------
# Helpers — string validation.
# ---------------------------------------------------------------------------


def _is_lowercase_sha256_hex(value: str) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) != _SHA256_HEX_LENGTH:
        return False
    return all(ch in _SHA256_HEX_PATTERN for ch in value)


def _is_sorted_unique_strings(values: tuple[str, ...]) -> bool:
    return tuple(values) == tuple(sorted(set(values)))


def _is_sorted_enums(values: tuple[Enum, ...]) -> bool:
    """Return True iff the orientation_sequence is sorted by enum token.

    Duplicates are permitted by Section 8.2 (multiple baffles may share
    the same orientation token); only the order is constrained.
    """
    tokens = [item.value for item in values]
    return tokens == sorted(tokens)


# ---------------------------------------------------------------------------
# Public module-internal orchestration callable (Section 6.3 of design).
# ---------------------------------------------------------------------------


def validate_authority_foundation(
    request: _t024.BaffleGeometryRequest,
) -> _AuthorityFoundationResult:
    """Run Stages 2 through 8 in strict rank order.

    Section 7 semantics: a stage failure aborts subsequent stages; only
    warnings from fully-completed prior stages are carried forward.
    """
    prior_warnings: list[_RankedMessage] = []
    completed_stage_rank = _STAGE_2_RANK - 1

    stage_functions = (
        (_STAGE_2_RANK, _stage2_validate),
        (_STAGE_3_RANK, _stage3_validate),
        (_STAGE_4_RANK, _stage4_validate),
        (_STAGE_5_RANK, _stage5_validate),
        (_STAGE_6_RANK, _stage6_validate),
        (_STAGE_7_RANK, _stage7_validate),
        (_STAGE_8_RANK, _stage8_validate),
    )

    for rank, function in stage_functions:
        blockers, warnings = function(request)
        if blockers:
            sorted_blockers = _sort_messages(blockers)
            sorted_warnings = _sort_messages(tuple(prior_warnings))
            return _AuthorityFoundationResult(
                request=request,
                completed_stage_rank=completed_stage_rank,
                warnings=tuple(item.entry for item in sorted_warnings),
                blockers=tuple(item.entry for item in sorted_blockers),
            )
        prior_warnings.extend(warnings)
        completed_stage_rank = rank

    sorted_warnings = _sort_messages(tuple(prior_warnings))
    return _AuthorityFoundationResult(
        request=request,
        completed_stage_rank=completed_stage_rank,
        warnings=tuple(item.entry for item in sorted_warnings),
        blockers=(),
    )


# ``validate_authority_foundation`` is intentionally NOT in ``__all__``.
# It is a module-internal orchestration callable consumed only by the
# Round-5 ``validation.py`` composition. Section 6.3 of the design
# contract forbids exporting it through the package ``__init__``.
