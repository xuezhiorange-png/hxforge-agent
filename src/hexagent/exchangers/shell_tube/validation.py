"""TASK-020 validation pipeline — top-level entry point.

This module provides the single public entry point
``validate_request`` which converts a §8 request payload into either a
§7.7 ``ConfigurationValidationResult(status = VALID)`` carrying a
fully-normalized ``ShellAndTubeConfiguration``, or a result with
``status = BLOCKED`` and a list of §10.4 ``ErrorEntry`` blockers.

Slice A scope
-------------
- §8.1 — strict field validation + unknown-field rejection
- §8.2 — structural token normalization
- §8.3 — authority-mode consistency
- §8.4 — no unit-bearing geometry inputs (any such field is
  ``STC_UNKNOWN_FIELD``)
- §7.3 — CaseRevisionAuthority binding
- §7.5 — ConfigurationAuthorityBinding assembly
- §9 — normalized configuration output
- §9.3 — closed ``deferred_capabilities`` set
- §10 — blocker / warning model
- §11 — canonical serialization + SHA-256 + UUIDv5

NOT in scope (Slice B, DEFERRED)
--------------------------------
- ``rule_pack_adapter.py`` (TASK-012 runtime adapter)
- 4 rule-pack fixture packs
- ``ci-shard-manifest.yml`` modification
- ``APPROVED_RULE_PACK`` mode beyond the §10.1 fail-closed ``STC_RULE_PACK_REQUIRED`` blocker
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from hexagent.exchangers.shell_tube import canonical, errors, schema
from hexagent.exchangers.shell_tube.authority import (
    bind_request_to_configuration_authority,
    from_case_revision_payload,
    from_requested_rule_pack_identity,
)
from hexagent.exchangers.shell_tube.models import (
    DEFERRED_CAPABILITIES,
    AuthorityMode,
    CaseRevisionAuthority,
    ComponentTokens,
    ConfigurationValidationResult,
    ConstructionFamily,
    EquipmentFamily,
    ErrorEntry,
    EvaluatedRulePackAuthority,
    Orientation,
    RequestedRulePackIdentity,
    ShellAndTubeConfiguration,
    ShellAndTubeConfigurationRequest,
    StandardClaimStatus,
    ValidationStatus,
)
from hexagent.exchangers.shell_tube.schema import (
    CONFIGURATION_SCHEMA_VERSION,
    REQUEST_ALLOWED_FIELDS,
    REQUEST_SCHEMA_VERSION,
    check_authority_mode_consistency,
    normalize_token,
)

# ---------------------------------------------------------------------------
# §8.1 — Internal payload → domain request conversion
# ---------------------------------------------------------------------------


def _parse_case_authority(payload: Mapping[str, Any]) -> CaseRevisionAuthority:
    """Parse the ``case_authority`` sub-payload per §7.3 / §8.1."""
    if "case_authority" not in payload or payload["case_authority"] is None:
        raise errors.BlockerError("STC_CASE_AUTHORITY_MISSING", "case_authority required")
    raw = payload["case_authority"]
    if not isinstance(raw, Mapping):
        raise errors.BlockerError(
            "STC_AUTHORITY_FIELDS_INCONSISTENT", "case_authority must be mapping"
        )
    return from_case_revision_payload(
        revision_id=str(raw.get("revision_id", "")),
        payload_hash=str(raw.get("payload_hash", "")),
        domain_snapshot_hash=str(raw.get("domain_snapshot_hash", "")),
        status=str(raw.get("status", "")),
    )


def _parse_requested_rule_pack_identity(
    payload: Mapping[str, Any],
) -> RequestedRulePackIdentity | None:
    if payload.get("requested_rule_pack_identity") is None:
        return None
    raw = payload["requested_rule_pack_identity"]
    if not isinstance(raw, Mapping):
        raise errors.BlockerError(
            "STC_REQUESTED_RULE_PACK_IDENTITY_MISSING",
            "requested_rule_pack_identity must be mapping",
        )
    return from_requested_rule_pack_identity(
        rule_pack_id=str(raw.get("rule_pack_id", "")),
        rule_pack_version=str(raw.get("rule_pack_version", "")),
        rule_pack_canonical_hash=str(raw.get("rule_pack_canonical_hash", "")),
    )


def _payload_to_request(
    payload: Mapping[str, Any],
) -> ShellAndTubeConfigurationRequest:
    """Strict payload → domain object conversion per §8.1."""
    # §8.1 — schema version
    schema_version = str(payload.get("schema_version", ""))
    if schema_version != REQUEST_SCHEMA_VERSION:
        raise errors.BlockerError("STC_SCHEMA_VERSION_UNSUPPORTED", schema_version)

    # §8.1 — case authority (§7.3)
    case_authority = _parse_case_authority(payload)

    # §8.1 — equipment / authority / construction / orientation
    equipment_family_raw = payload.get("equipment_family", "")
    if equipment_family_raw != EquipmentFamily.SHELL_AND_TUBE.value:
        raise errors.BlockerError("STC_EQUIPMENT_FAMILY_INVALID", str(equipment_family_raw))
    equipment_family = EquipmentFamily.SHELL_AND_TUBE

    authority_mode_raw = payload.get("authority_mode", "")
    try:
        authority_mode = AuthorityMode(authority_mode_raw)
    except ValueError as exc:
        raise errors.BlockerError("STC_AUTHORITY_MODE_INVALID", str(exc)) from exc

    construction_family_raw = payload.get("construction_family", "")
    try:
        construction_family = ConstructionFamily(construction_family_raw)
    except ValueError as exc:
        raise errors.BlockerError("STC_CONSTRUCTION_FAMILY_INVALID", str(exc)) from exc

    orientation_raw = payload.get("orientation", "")
    try:
        orientation = Orientation(orientation_raw)
    except ValueError as exc:
        raise errors.BlockerError("STC_ORIENTATION_INVALID", str(exc)) from exc

    # §8.1 — pass counts
    shell_pass_count = payload.get("shell_pass_count", 0)
    if (
        not isinstance(shell_pass_count, int)
        or isinstance(shell_pass_count, bool)
        or shell_pass_count < 1
    ):
        raise errors.BlockerError(
            "STC_PASS_COUNT_INVALID", f"shell_pass_count={shell_pass_count!r}"
        )
    tube_pass_count = payload.get("tube_pass_count", 0)
    if (
        not isinstance(tube_pass_count, int)
        or isinstance(tube_pass_count, bool)
        or tube_pass_count < 1
    ):
        raise errors.BlockerError("STC_PASS_COUNT_INVALID", f"tube_pass_count={tube_pass_count!r}")

    # §8.2 — structural tokens
    front_head_token = normalize_token(payload.get("front_head_token"))
    shell_token = normalize_token(payload.get("shell_token"))
    rear_head_token = normalize_token(payload.get("rear_head_token"))
    component_tokens = ComponentTokens(
        front_head=front_head_token,
        shell=shell_token,
        rear_head=rear_head_token,
    )

    # §8.1 — standard system id + rule-pack identity
    standard_system_id = payload.get("standard_system_id")
    if standard_system_id is not None and not isinstance(standard_system_id, str):
        raise errors.BlockerError(
            "STC_AUTHORITY_FIELDS_INCONSISTENT",
            f"standard_system_id type={type(standard_system_id).__name__}",
        )
    requested_rule_pack_identity = _parse_requested_rule_pack_identity(payload)

    # §8.3 — authority-mode consistency
    check_authority_mode_consistency(
        authority_mode=authority_mode,
        requested_rule_pack_identity=requested_rule_pack_identity,
        standard_system_id=standard_system_id,
    )

    # §8.1 — evidence refs
    raw_evidence = payload.get("evidence_refs", [])
    if raw_evidence is None:
        raw_evidence = []
    if not isinstance(raw_evidence, list):
        raise errors.BlockerError(
            "STC_AUTHORITY_FIELDS_INCONSISTENT",
            f"evidence_refs must be list, got {type(raw_evidence).__name__}",
        )
    evidence_refs = canonical.sort_evidence_refs(str(ref) for ref in raw_evidence)

    return ShellAndTubeConfigurationRequest(
        schema_version=schema_version,
        case_authority=case_authority,
        equipment_family=equipment_family,
        authority_mode=authority_mode,
        construction_family=construction_family,
        orientation=orientation,
        shell_pass_count=shell_pass_count,
        tube_pass_count=tube_pass_count,
        component_tokens=component_tokens,
        standard_system_id=standard_system_id,
        requested_rule_pack_identity=requested_rule_pack_identity,
        evidence_refs=evidence_refs,
    )


# ---------------------------------------------------------------------------
# §10.4 — error entry construction
# ---------------------------------------------------------------------------


def _error_entry_from_exception(exc: errors.ShellTubeError) -> ErrorEntry:
    """Convert a ``ShellTubeError`` into a §10.4 ``ErrorEntry``."""
    return ErrorEntry(
        code=exc.code,
        field_path=None,
        message_key=exc.code,
        evidence_refs=(),
        details=None,
    )


def _canonicalize_error_entries(
    entries: list[ErrorEntry],
) -> tuple[ErrorEntry, ...]:
    """Return ``entries`` sorted in §11.4 ascending order."""
    sorted_dicts = canonical.sort_error_entries(
        {
            "code": e.code,
            "field_path": e.field_path,
            "message_key": e.message_key,
            "evidence_refs": list(e.evidence_refs),
            "details": e.details,
        }
        for e in entries
    )
    # Map back to ErrorEntry instances preserving the canonical order.
    by_key = {
        (
            e.code,
            e.field_path,
            e.message_key,
        ): e
        for e in entries
    }
    out: list[ErrorEntry] = []
    for d in sorted_dicts:
        key = (d["code"], d["field_path"], d["message_key"])
        out.append(by_key[key])
    return tuple(out)


# ---------------------------------------------------------------------------
# §9.1 — Normalized configuration assembly
# ---------------------------------------------------------------------------


def _build_normalized_configuration(
    request: ShellAndTubeConfigurationRequest,
    warnings: tuple[ErrorEntry, ...],
    blockers: tuple[ErrorEntry, ...],
) -> tuple[ShellAndTubeConfiguration, str, str]:
    """Build the §9.1 normalized configuration + (hash, id)."""
    # §9.1 — authority binding
    evaluated_rpa: EvaluatedRulePackAuthority | None = None
    if request.authority_mode == AuthorityMode.APPROVED_RULE_PACK:
        # Slice A does NOT load or evaluate rule packs (§16.1). The
        # binding carries a null rule-pack slot for the FAIL-CLOSED
        # BLOCKED path; the result is BLOCKED before the binding is
        # serialized.
        evaluated_rpa = None
    authority_binding = bind_request_to_configuration_authority(
        request_authority_mode=request.authority_mode,
        case_authority=request.case_authority,
        standard_system_id=request.standard_system_id,
        evaluated_rule_pack_authority=evaluated_rpa,
        case_authority_evidence_refs=request.evidence_refs,
    )

    # §9.1 — standard_claim_status
    if request.authority_mode == AuthorityMode.APPROVED_RULE_PACK:
        standard_claim_status = StandardClaimStatus.RULE_PACK_VALIDATED
    else:
        standard_claim_status = StandardClaimStatus.NO_STANDARD_CLAIM

    # §11.2 — canonical payload
    configuration_dict: dict[str, Any] = {
        "equipment_family": request.equipment_family.value,
        "authority_mode": request.authority_mode.value,
        "standard_claim_status": standard_claim_status.value,
        "construction_family": request.construction_family.value,
        "orientation": request.orientation.value,
        "shell_pass_count": request.shell_pass_count,
        "tube_pass_count": request.tube_pass_count,
        "component_tokens": {
            "front_head": request.component_tokens.front_head,
            "shell": request.component_tokens.shell,
            "rear_head": request.component_tokens.rear_head,
        },
    }
    case_authority_dict: dict[str, Any] = {
        "revision_id": request.case_authority.revision_id,
        "payload_hash": request.case_authority.payload_hash,
        "domain_snapshot_hash": request.case_authority.domain_snapshot_hash,
        "revision_status": request.case_authority.revision_status.value,
    }
    authority_binding_dict: dict[str, Any] = {
        "authority_mode": authority_binding.authority_mode.value,
        "standard_system_id": authority_binding.standard_system_id,
        "case_authority": case_authority_dict,
        "case_authority_evidence_refs": list(authority_binding.case_authority_evidence_refs),
        "evaluated_rule_pack_authority": (
            None
            if authority_binding.evaluated_rule_pack_authority is None
            else {
                "rule_pack_id": (authority_binding.evaluated_rule_pack_authority.rule_pack_id),
                "rule_pack_version": (
                    authority_binding.evaluated_rule_pack_authority.rule_pack_version
                ),
                "rule_pack_canonical_hash": (
                    authority_binding.evaluated_rule_pack_authority.rule_pack_canonical_hash
                ),
                "validation_status": (
                    authority_binding.evaluated_rule_pack_authority.validation_status
                ),
                "selected_rule_authorities": [
                    {
                        "rule_id": sra.rule_id,
                        "rule_version": sra.rule_version,
                        "rule_artifact_canonical_hash": (sra.rule_artifact_canonical_hash),
                        "source_class": sra.source_class,
                        "license_evidence": sra.license_evidence,
                        "approval_status": sra.approval_status,
                        "provenance_edge_ids": list(sra.provenance_edge_ids),
                        "evidence_refs": list(sra.evidence_refs),
                    }
                    for sra in (
                        authority_binding.evaluated_rule_pack_authority.selected_rule_authorities
                    )
                ],
            }
        ),
    }

    payload = canonical.canonical_payload(
        configuration=configuration_dict,
        case_authority=case_authority_dict,
        evaluated_rule_pack_authority=(authority_binding_dict["evaluated_rule_pack_authority"]),
        canonical_warnings=[_error_entry_to_dict(e) for e in warnings],
        canonical_blockers=[_error_entry_to_dict(e) for e in blockers],
        deferred_capabilities=DEFERRED_CAPABILITIES,
        authority_binding=authority_binding_dict,
        schema_version=CONFIGURATION_SCHEMA_VERSION,
    )
    config_hash = canonical.configuration_hash(payload)
    config_id = canonical.configuration_id(config_hash)

    configuration = ShellAndTubeConfiguration(
        schema_version=CONFIGURATION_SCHEMA_VERSION,
        configuration_id=config_id,
        configuration_hash=config_hash,
        equipment_family=request.equipment_family,
        authority_mode=request.authority_mode,
        standard_claim_status=standard_claim_status,
        construction_family=request.construction_family,
        orientation=request.orientation,
        shell_pass_count=request.shell_pass_count,
        tube_pass_count=request.tube_pass_count,
        component_tokens=request.component_tokens,
        authority_binding=authority_binding,
        case_authority=request.case_authority,
        warnings=warnings,
        blockers=blockers,
        deferred_capabilities=DEFERRED_CAPABILITIES,
    )
    return configuration, config_hash, config_id


def _error_entry_to_dict(entry: ErrorEntry) -> dict[str, Any]:
    return {
        "code": entry.code,
        "field_path": entry.field_path,
        "message_key": entry.message_key,
        "evidence_refs": list(entry.evidence_refs),
        "details": dict(entry.details) if entry.details is not None else None,
    }


# ---------------------------------------------------------------------------
# §7.7 — top-level entry point
# ---------------------------------------------------------------------------


def validate_request(
    payload: Mapping[str, Any],
) -> ConfigurationValidationResult:
    """Validate a §8 request payload.

    Returns a §7.7 ``ConfigurationValidationResult``. On any blocker,
    the result has ``status == BLOCKED`` and the normalized
    configuration is **not** produced (§10.1).

    For ``APPROVED_RULE_PACK`` mode, the result is BLOCKED with
    ``STC_RULE_PACK_REQUIRED`` (Slice A does NOT load or evaluate
    rule packs).
    """
    blockers: list[ErrorEntry] = []
    warnings: list[ErrorEntry] = []

    try:
        # §8.1 — unknown fields
        try:
            schema._check_unknown_fields(payload, REQUEST_ALLOWED_FIELDS)
            schema._check_request_forbidden_fields(payload)
        except errors.BlockerError as exc:
            blockers.append(_error_entry_from_exception(exc))
            return _finalize_blocked(blockers, warnings)

        # §8.1 — payload → request
        try:
            request = _payload_to_request(payload)
        except errors.BlockerError as exc:
            blockers.append(_error_entry_from_exception(exc))
            return _finalize_blocked(blockers, warnings)

        # §8.3 — authority-mode consistency already enforced in _payload_to_request

        # §16.1 — Slice A: APPROVED_RULE_PACK mode emits fail-closed
        # blocker (no rule-pack loading / evaluation).
        if request.authority_mode == AuthorityMode.APPROVED_RULE_PACK:
            blockers.append(
                ErrorEntry(
                    code="STC_RULE_PACK_REQUIRED",
                    field_path="authority_mode",
                    message_key="STC_RULE_PACK_REQUIRED",
                    evidence_refs=(),
                    details=None,
                )
            )
            return _finalize_blocked(blockers, warnings)

        # §9.1 — normalized configuration
        configuration, _, _ = _build_normalized_configuration(
            request=request,
            warnings=tuple(warnings),
            blockers=tuple(blockers),
        )
        return ConfigurationValidationResult(
            status=ValidationStatus.VALID,
            configuration=configuration,
            warnings=tuple(warnings),
            blockers=(),
            deferred_capabilities=DEFERRED_CAPABILITIES,
        )
    except errors.BlockerError as exc:
        # Top-level catch — any unhandled blocker path returns BLOCKED.
        blockers.append(_error_entry_from_exception(exc))
        return _finalize_blocked(blockers, warnings)


def _finalize_blocked(
    blockers: list[ErrorEntry],
    warnings: list[ErrorEntry],
) -> ConfigurationValidationResult:
    return ConfigurationValidationResult(
        status=ValidationStatus.BLOCKED,
        configuration=None,
        warnings=tuple(warnings),
        blockers=_canonicalize_error_entries(blockers),
        deferred_capabilities=DEFERRED_CAPABILITIES,
    )


__all__ = [
    "validate_request",
]
