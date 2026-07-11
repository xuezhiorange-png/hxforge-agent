"""TASK-020 authority and provenance representation — §6.3 / §7.3 / §7.5.

This module provides the **factory** and **validation helpers** for the
TASK-020 authority value objects. The TASK-020 adapter treats all
authority inputs as **read-only** and **does not** perform any
persistence query (per §7.3 lines 596–601).

Preservation contract (P1-1, P1-2, P1-3)
----------------------------------------
- CaseRevisionAuthority (§7.3): 1-to-1 mapping from TASK-014
  ``CaseRevision``. TASK-020 owns the value object; TASK-014 is not
  imported.
- SelectedRuleAuthority (§6.3.5.1): 8-field versioned object; the
  only per-rule identity carrier.
- EvaluatedRulePackAuthority (§6.3.5): output-only, contains the
  typed ``selected_rule_authorities`` list. The deleted parallel
  ``selected_rule_ids`` / ``selected_rule_artifact_hashes`` lists are
  never re-introduced.

Public surface
--------------
- ``from_case_revision_payload``: construct a CaseRevisionAuthority
  from the 4 TASK-014 fields. This is the public entry point for the
  TASK-014 → TASK-020 mapping. The function enforces the §7.3
  acceptance subset on the status field and the lowercase 64-char
  SHA-256 hex pattern on the hash fields.
- ``from_requested_rule_pack_identity``: construct a
  RequestedRulePackIdentity from raw fields with §6.3.4 hash-format
  enforcement.
- ``bind_request_to_configuration_authority``: produce the §7.5
  ``ConfigurationAuthorityBinding`` for a request, with the rule-pack
  slot ``null`` for ``INTERNAL_GENERIC`` mode.
"""

from __future__ import annotations

import re

from hexagent.exchangers.shell_tube.errors import BlockerError
from hexagent.exchangers.shell_tube.models import (
    TASK_020_ACCEPTED_LIFECYCLE_VALUES,
    AuthorityMode,
    CaseRevisionAuthority,
    CaseRevisionStatus,
    ConfigurationAuthorityBinding,
    EvaluatedRulePackAuthority,
    RequestedRulePackIdentity,
    SelectedRuleAuthority,
)

# ---------------------------------------------------------------------------
# Hash / ID / evidence_refs format patterns (frozen at §7.3 / §8.2 / §11.3)
# ---------------------------------------------------------------------------


# Lowercase 64-character SHA-256 hex string. Matches the §7.3 lines
# 571–576 frozen pattern. Used for ``payload_hash``,
# ``domain_snapshot_hash``, and ``rule_pack_canonical_hash`` validation.
_SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")

# §8.2 structural token pattern: trimmed, uppercased ASCII; matches
# ``^[A-Z0-9][A-Z0-9._-]{0,15}$`` (length 1–16). The core schema does
# not interpret a token as a particular external-standard symbol; the
# pattern is enforced only at the schema layer.
_TOKEN_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,15}$")


def is_valid_sha256_hex(value: str) -> bool:
    """Return True iff ``value`` is a lowercase 64-character hex string."""
    return isinstance(value, str) and bool(_SHA256_HEX_PATTERN.match(value))


def is_valid_structural_token(value: str) -> bool:
    """Return True iff ``value`` matches the §8.2 structural token pattern."""
    return isinstance(value, str) and bool(_TOKEN_PATTERN.match(value))


# ---------------------------------------------------------------------------
# §7.3 — CaseRevisionAuthority factory
# ---------------------------------------------------------------------------


def from_case_revision_payload(
    *,
    revision_id: str,
    payload_hash: str,
    domain_snapshot_hash: str,
    status: str,
) -> CaseRevisionAuthority:
    """Construct a ``CaseRevisionAuthority`` from the TASK-014 ``CaseRevision`` fields.

    Enforces the §7.3 acceptance subset on the status field and the
    lowercase 64-char SHA-256 hex pattern on both hash fields. Raises
    ``BlockerError`` with the appropriate ``STC_*`` code on violation
    (the caller converts the raised error into a §10.4 blocker
    object).

    Parameters
    ----------
    revision_id: str
        Opaque, project-unique revision identifier. Non-empty.
    payload_hash: str
        Lowercase 64-character SHA-256 hex string.
    domain_snapshot_hash: str
        Lowercase 64-character SHA-256 hex string.
    status: str
        TASK-014 ``CaseRevision.status`` lifecycle value. Must be
        in the TASK-020 acceptance subset
        ``{committed, superseded, archived}``.

    Returns
    -------
    CaseRevisionAuthority
        The frozen 1-to-1 mapped value object.

    Raises
    ------
    BlockerError
        ``STC_CASE_REVISION_ID_MISSING`` / ``STC_CASE_PAYLOAD_HASH_INVALID``
        / ``STC_CASE_DOMAIN_SNAPSHOT_HASH_INVALID`` /
        ``STC_CASE_REVISION_STATUS_BLOCKED`` on input violation.
    """
    if not isinstance(revision_id, str) or not revision_id:
        raise BlockerError("STC_CASE_REVISION_ID_MISSING", str(revision_id))
    if not is_valid_sha256_hex(payload_hash):
        raise BlockerError("STC_CASE_PAYLOAD_HASH_INVALID", str(payload_hash))
    if not is_valid_sha256_hex(domain_snapshot_hash):
        raise BlockerError("STC_CASE_DOMAIN_SNAPSHOT_HASH_INVALID", str(domain_snapshot_hash))
    if status not in TASK_020_ACCEPTED_LIFECYCLE_VALUES:
        raise BlockerError("STC_CASE_REVISION_STATUS_BLOCKED", str(status))
    return CaseRevisionAuthority(
        revision_id=revision_id,
        payload_hash=payload_hash,
        domain_snapshot_hash=domain_snapshot_hash,
        revision_status=CaseRevisionStatus(status),
    )


# ---------------------------------------------------------------------------
# §6.3.4 — RequestedRulePackIdentity factory
# ---------------------------------------------------------------------------


def from_requested_rule_pack_identity(
    *,
    rule_pack_id: str,
    rule_pack_version: str,
    rule_pack_canonical_hash: str,
) -> RequestedRulePackIdentity:
    """Construct a ``RequestedRulePackIdentity`` from raw fields.

    Per §6.3.4, the only rule-pack object the request carries. The
    hash field is bound to the TASK-012 manifest ``canonical_hash``
    (§6.3 lines 250–256) and MUST be a lowercase 64-char SHA-256 hex
    string.

    Raises
    ------
    BlockerError
        ``STC_RULE_PACK_CANONICAL_HASH_MISMATCH`` is the design's
        name for an invalid hash; we re-use that code here for
        shape-violation, since the design does not enumerate a
        separate shape-only code.
    """
    if not isinstance(rule_pack_id, str) or not rule_pack_id:
        raise BlockerError("STC_RULE_PACK_NOT_FOUND", str(rule_pack_id))
    if not isinstance(rule_pack_version, str) or not rule_pack_version:
        raise BlockerError("STC_REQUESTED_RULE_PACK_IDENTITY_MISSING", str(rule_pack_version))
    if not is_valid_sha256_hex(rule_pack_canonical_hash):
        raise BlockerError("STC_RULE_PACK_CANONICAL_HASH_MISMATCH", str(rule_pack_canonical_hash))
    return RequestedRulePackIdentity(
        rule_pack_id=rule_pack_id,
        rule_pack_version=rule_pack_version,
        rule_pack_canonical_hash=rule_pack_canonical_hash,
    )


# ---------------------------------------------------------------------------
# §7.5 — ConfigurationAuthorityBinding assembly
# ---------------------------------------------------------------------------


def bind_request_to_configuration_authority(
    request_authority_mode: AuthorityMode,
    case_authority: CaseRevisionAuthority,
    standard_system_id: str | None,
    evaluated_rule_pack_authority: EvaluatedRulePackAuthority | None,
    *,
    case_authority_evidence_refs: tuple[str, ...] = (),
) -> ConfigurationAuthorityBinding:
    """Assemble a §7.5 ``ConfigurationAuthorityBinding``.

    For ``INTERNAL_GENERIC`` mode the rule-pack slot is ``None`` and
    the input-side ``RequestedRulePackIdentity`` is not part of the
    binding. For ``APPROVED_RULE_PACK`` mode the binding carries the
    complete ``EvaluatedRulePackAuthority`` value object (§6.3.5).
    """
    return ConfigurationAuthorityBinding(
        authority_mode=request_authority_mode,
        standard_system_id=standard_system_id,
        case_authority=case_authority,
        evaluated_rule_pack_authority=evaluated_rule_pack_authority,
        case_authority_evidence_refs=case_authority_evidence_refs,
    )


# ---------------------------------------------------------------------------
# §6.3.5.1 — SelectedRuleAuthority builder (deterministic ordering)
# ---------------------------------------------------------------------------


def finalize_selected_rule_authority(
    item: SelectedRuleAuthority,
) -> SelectedRuleAuthority:
    """Return ``item`` with evidence_refs and provenance_edge_ids sorted.

    §6.3.5.1 lines 467–476: lists are sorted in ascending Unicode
    code-point order at canonicalization time and deduplicated at
    construction time. The dataclass ``__post_init__`` (in
    ``models.py``) does **not** sort these lists — the canonicalizer
    is the only place that may re-order them.
    """
    return SelectedRuleAuthority(
        rule_id=item.rule_id,
        rule_version=item.rule_version,
        rule_artifact_canonical_hash=item.rule_artifact_canonical_hash,
        source_class=item.source_class,
        license_evidence=item.license_evidence,
        approval_status=item.approval_status,
        provenance_edge_ids=tuple(sorted({edge_id for edge_id in item.provenance_edge_ids})),
        evidence_refs=tuple(sorted({evidence_ref for evidence_ref in item.evidence_refs})),
    )


__all__ = [
    "bind_request_to_configuration_authority",
    "finalize_selected_rule_authority",
    "from_case_revision_payload",
    "from_requested_rule_pack_identity",
    "is_valid_sha256_hex",
    "is_valid_structural_token",
]
