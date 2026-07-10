"""TASK-020 schema validation — §8 / §10 of the TASK-020 design contract.

This module provides the **strict** schema validators. Every validator
emits a stable ``STC_*`` ``BlockerCode`` or ``WarningCode`` on
violation; the validation layer (``validation.py``) converts the
raised errors into §10.4 ``ErrorEntry`` objects.

Scope (Slice A, §16.1)
-----------------------
- §8.1 — request field requirements + §8.1 forbidden fields
- §8.2 — structural token normalization
- §8.3 — authority-mode consistency
- §8.4 — no unit-bearing geometry inputs
- §10.2 — frozen blocker code set (subset relevant to Slice A)
- §10.3 — frozen warning code set
- §10.4 — error object 5-field shape

Slice B (rule-pack evaluation) is **not** implemented here. The
``APPROVED_RULE_PACK`` path emits ``STC_RULE_PACK_REQUIRED`` from
``validation.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from hexagent.exchangers.shell_tube.authority import (
    is_valid_structural_token,
)
from hexagent.exchangers.shell_tube.errors import BlockerError
from hexagent.exchangers.shell_tube.models import (
    DEFERRED_CAPABILITIES,
    AuthorityMode,
    BlockerCode,
    ConstructionFamily,
    EquipmentFamily,
    Orientation,
    RequestedRulePackIdentity,
)

# ---------------------------------------------------------------------------
# §8.1 — schema version + forbidden fields
# ---------------------------------------------------------------------------


REQUEST_SCHEMA_VERSION = "task020.configuration-request.v1"
CONFIGURATION_SCHEMA_VERSION = "task020.configuration.v1"


def _check_request_schema_version(request_version: str) -> None:
    if request_version != REQUEST_SCHEMA_VERSION:
        raise BlockerError(
            BlockerCode.STC_SCHEMA_VERSION_UNSUPPORTED.value,
            str(request_version),
        )


def _check_unknown_fields(
    payload: Mapping[str, Any],
    allowed_fields: frozenset[str],
) -> None:
    """Emit STC_UNKNOWN_FIELD for any payload key not in ``allowed_fields`` (§8.1)."""
    for key in payload:
        if key not in allowed_fields:
            raise BlockerError(
                BlockerCode.STC_UNKNOWN_FIELD.value,
                str(key),
            )


# §8.1 frozen field set (request side)
REQUEST_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
        "schema_version",
        "case_authority",
        "equipment_family",
        "authority_mode",
        "construction_family",
        "orientation",
        "shell_pass_count",
        "tube_pass_count",
        "front_head_token",
        "shell_token",
        "rear_head_token",
        "standard_system_id",
        "requested_rule_pack_identity",
        "evidence_refs",
    }
)

# Forbidden request-side field names (§8.1 lines 673–685)
REQUEST_FORBIDDEN_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "rule_pack_id",
        "rule_pack_version",
        "rule_pack_canonical_hash",
        "rule_pack_authority",
        "evaluated_rule_pack_authority",
        "selected_rule_ids",
        "selected_rule_artifact_hashes",
        "validation_status",
        "content_hash",
        "rule_pack_hash",
    }
)


def _check_request_forbidden_fields(payload: Mapping[str, Any]) -> None:
    """Emit STC_UNKNOWN_FIELD for any request-side forbidden field name (§8.1)."""
    for forbidden_name in REQUEST_FORBIDDEN_FIELD_NAMES:
        if forbidden_name in payload:
            raise BlockerError(
                BlockerCode.STC_UNKNOWN_FIELD.value,
                forbidden_name,
            )


# ---------------------------------------------------------------------------
# §8.2 — structural token normalization
# ---------------------------------------------------------------------------


def normalize_token(raw: str | None) -> str | None:
    """Normalize a structural component token per §8.2.

    1. trimmed
    2. uppercased ASCII
    3. matches ``^[A-Z0-9][A-Z0-9._-]{0,15}$``
    4. opaque to the core schema

    Returns ``None`` for ``None`` input. Raises ``STC_TOKEN_MALFORMED``
    if the normalized token does not match the §8.2 pattern.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise BlockerError(BlockerCode.STC_TOKEN_MALFORMED.value, str(raw))
    trimmed = raw.strip()
    if not trimmed:
        return None
    upper = trimmed.upper()
    if not is_valid_structural_token(upper):
        raise BlockerError(BlockerCode.STC_TOKEN_MALFORMED.value, str(raw))
    return upper


# ---------------------------------------------------------------------------
# §8.3 — authority-mode consistency (P1-2)
# ---------------------------------------------------------------------------


def check_authority_mode_consistency(
    authority_mode: AuthorityMode,
    requested_rule_pack_identity: RequestedRulePackIdentity | None,
    standard_system_id: str | None,
) -> None:
    """Enforce §8.3 authority-mode consistency.

    For ``INTERNAL_GENERIC``:
    - the only rule-pack field the request carries is
      ``requested_rule_pack_identity``, and its value MUST be exactly
      ``null`` (line 705)
    - legacy names are forbidden (lines 706–711)
    - no standard compliance claim is emitted
    - the request's ``requested_rule_pack_identity`` slot is ``null``
      and the adapter MUST NOT treat any other name as the rule-pack
      slot on the request

    For ``APPROVED_RULE_PACK``:
    - the request MUST carry a non-null ``requested_rule_pack_identity``
      with three frozen fields
    """
    if authority_mode == AuthorityMode.INTERNAL_GENERIC:
        if requested_rule_pack_identity is not None:
            raise BlockerError(
                BlockerCode.STC_AUTHORITY_FIELDS_INCONSISTENT.value,
                "INTERNAL_GENERIC requires requested_rule_pack_identity = null",
            )
        if standard_system_id is not None:
            raise BlockerError(
                BlockerCode.STC_AUTHORITY_FIELDS_INCONSISTENT.value,
                "INTERNAL_GENERIC forbids standard_system_id",
            )
    elif authority_mode == AuthorityMode.APPROVED_RULE_PACK:
        if requested_rule_pack_identity is None:
            raise BlockerError(
                BlockerCode.STC_REQUESTED_RULE_PACK_IDENTITY_MISSING.value,
                "APPROVED_RULE_PACK requires non-null requested_rule_pack_identity",
            )
        if standard_system_id is None:
            raise BlockerError(
                BlockerCode.STC_AUTHORITY_FIELDS_INCONSISTENT.value,
                "APPROVED_RULE_PACK requires standard_system_id",
            )
    else:  # pragma: no cover - AuthorityMode is a closed enum
        raise BlockerError(BlockerCode.STC_AUTHORITY_MODE_INVALID.value, str(authority_mode))


# ---------------------------------------------------------------------------
# §8.1 — strict field validation helpers
# ---------------------------------------------------------------------------


def check_equipment_family(value: Any) -> None:
    if not isinstance(value, EquipmentFamily) or value != EquipmentFamily.SHELL_AND_TUBE:
        raise BlockerError(BlockerCode.STC_EQUIPMENT_FAMILY_INVALID.value, str(value))


def check_authority_mode(value: Any) -> None:
    if not isinstance(value, AuthorityMode):
        raise BlockerError(BlockerCode.STC_AUTHORITY_MODE_INVALID.value, str(value))


def check_construction_family(value: Any) -> None:
    if not isinstance(value, ConstructionFamily):
        raise BlockerError(BlockerCode.STC_CONSTRUCTION_FAMILY_INVALID.value, str(value))


def check_orientation(value: Any) -> None:
    if not isinstance(value, Orientation):
        raise BlockerError(BlockerCode.STC_ORIENTATION_INVALID.value, str(value))


def check_pass_count(value: Any, *, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise BlockerError(
            BlockerCode.STC_PASS_COUNT_INVALID.value,
            f"{field_name}={value!r}",
        )


__all__ = [
    "CONFIGURATION_SCHEMA_VERSION",
    "DEFERRED_CAPABILITIES",
    "REQUEST_ALLOWED_FIELDS",
    "REQUEST_FORBIDDEN_FIELD_NAMES",
    "REQUEST_SCHEMA_VERSION",
    "check_authority_mode",
    "check_authority_mode_consistency",
    "check_construction_family",
    "check_equipment_family",
    "check_orientation",
    "check_pass_count",
    "normalize_token",
]
