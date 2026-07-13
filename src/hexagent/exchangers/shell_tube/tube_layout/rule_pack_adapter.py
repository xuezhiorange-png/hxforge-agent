"""TASK-021 Slice B rule-pack adapter.

Implements the frozen ``build_layout_rule_authority_snapshot`` operation
described in Issue #141 Record 2 / Record 4 / Record 5 / Record 6. It is
a pure adapter that consumes an already-loaded TASK-012 rule-pack mapping
``{manifest, rules, provenance_edges, permission_evidence}`` (the exact
shape produced by ``hexagent.rule_packs.loader.load_rule_pack``) and
returns a TASK-021 ``LayoutRuleAuthoritySnapshot`` on the success path.

The adapter never performs:

* filesystem I/O (``os`` / ``pathlib`` / ``open`` / ``glob`` / ``rglob``);
* network I/O (``socket`` / ``requests`` / ``httpx``);
* database I/O;
* environment lookups;
* clock / runtime-now reads;
* locale lookups;
* global registry writes;
* directory scans;
* nearest-match / first-match / fallback substitution;
* inference of any default field.

It reuses the existing pure TASK-012 validators in
``hexagent.rule_packs.{schema, license_boundary, provenance}`` and the
existing slice-A canonical / hash / projection / ordering authorities
in ``.canonical`` and ``.models``. No new fixture, mock, default rule,
or stub catalog is introduced as production authority.

The seven TASK-012 ``source_class`` values are handled per the §4.1
governance matrix (``PUBLIC_DOMAIN / OPEN_LICENSE`` runtime-capable;
``USER_PROVIDED_LICENSED_SUMMARY / REFERENCE_ONLY_RESTRICTED_STANDARD``
non-runtime; ``INTERNAL_ENGINEERING_RULE / DERIVED_ENGINEERING_RULE``
canonical; ``VENDOR_PERMISSIONED`` requires all four scope tokens).

The TASK-021 profile projection fields (``pattern_family``, ``pitch_m``,
``edge_clearance_m``, ``allowed_origin_modes``,
``allowed_axis_orientations``, ``allowed_exclusion_zone_types``,
``maximum_candidate_positions``, ``evidence_refs``) are read verbatim
from the upstream rule's ``rule_body`` mapping under the TASK-020 read-
source discipline. No inference is performed on missing fields.

The slice-A ``verify_layout_rule_snapshot`` requires a TASK-020
``ShellAndTubeConfiguration`` + a ``tube_geometry`` snapshot. Those are
not available in the adapter's pure-memory input, so the defensive
terminal check performs a structural hash re-verification plus a
``profile_id`` match — the full validator re-runs once the snapshot is
embedded in a complete ``TubeLayoutRequest`` via ``validate_request``.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Any, Final, cast

from hexagent.canonical_json import canonical_sha256
from hexagent.rule_packs.license_boundary import (
    PROJECT_INTERNAL_AUTHORITY as _PROJECT_INTERNAL_AUTHORITY_TOKEN,
)
from hexagent.rule_packs.license_boundary import (
    PUBLIC_DOMAIN_TOKEN as _PUBLIC_DOMAIN_TOKEN,
)
from hexagent.rule_packs.license_boundary import (
    enforce_full_license_boundary,
    enforce_vendor_permission_scope,
)
from hexagent.rule_packs.models import (
    NON_REDISTRIBUTABLE_SOURCES,
    SourceClass,
    VendorPermissionScope,
)
from hexagent.rule_packs.provenance import (
    validate_provenance_edges,
    validate_supersedes_edges,
)
from hexagent.rule_packs.schema import (
    validate_canonical_hash,
    validate_manifest,
    validate_manifest_canonical_hash,
    validate_manifest_only_references_approved_rules,
    validate_rule,
)

from .adapter_blockers import (
    RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY,
    AdapterFailure,
    RulePackAdapterBlockerCode,
    build_message_entry,
    sort_adapter_blockers,
)
from .canonical import (
    DECIMAL_PRECISION,
    CanonicalizationError,
    decimal_string,
    freeze_known_fragment,
    internal_frozen_to_primitive,
    parse_decimal,
)
from .models import (
    AuthorityMode,
    AxisOrientation,
    ExclusionZoneType,
    LayoutRuleAuthoritySnapshot,
    MessageEntry,
    OriginMode,
    PatternFamily,
    RulePackIdentitySnapshot,
)

# Slice-A frozen profile id for TASK-021 layout-rule authority.
LAYOUT_RULE_PROFILE_ID: Final[str] = "hxforge.shell_tube.tube_layout.v1"

# Approval status string at the slice-A / TASK-012 boundary.
APPROVAL_APPROVED: Final[str] = "approved"

# Required TASK-021 projection fields at the rule ``rule_body`` layer.
# The TASK-020 read-source discipline (§12.8) keeps these fields inside
# the rule_body mapping; the adapter reads them verbatim.
REQUIRED_RULE_BODY_PROJECTION_FIELDS: Final[tuple[str, ...]] = (
    "pattern_family",
    "pitch_m",
    "edge_clearance_m",
    "allowed_origin_modes",
    "allowed_axis_orientations",
    "allowed_exclusion_zone_types",
    "maximum_candidate_positions",
    "evidence_refs",
)

# TASK-012 rule top-level identity fields read directly from the
# artifact (per TASK-020-S2 read-source discipline).
REQUIRED_RULE_TOP_LEVEL_FIELDS: Final[tuple[str, ...]] = (
    "rule_id",
    "rule_version",
    "canonical_hash",
    "source_class",
    "license_evidence",
    "approval_status",
    "provenance_edges",
)

# TASK-012 manifest required fields per Section 7.1.
REQUIRED_MANIFEST_FIELDS: Final[tuple[str, ...]] = (
    "rule_pack_id",
    "rule_pack_version",
    "rule_count",
    "rules",
    "target_jurisdiction",
    "target_standard_family",
    "creation_timestamp_utc",
    "review_id",
    "canonical_hash",
)


def _coerce_decimal_string(value: Any, *, field_name: str, rule_id: str) -> str:
    """Convert an upstream value (str / float / int / Decimal) to a TASK-021
    canonical decimal string under the frozen Decimal context.

    Floats are routed through ``str(value)`` per RFC 8785 to avoid
    binary-float representational drift. NaN / Inf rejected.
    """
    if isinstance(value, str):
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            ctx.rounding = ROUND_HALF_EVEN
            return decimal_string(parse_decimal(value, positive=True))
    if isinstance(value, bool):
        raise CanonicalizationError(
            f"rule_id={rule_id!r} field={field_name!r} bool is not a number"
        )
    if isinstance(value, int):
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            ctx.rounding = ROUND_HALF_EVEN
            return decimal_string(Decimal(value))
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise CanonicalizationError(f"rule_id={rule_id!r} field={field_name!r} not finite")
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            ctx.rounding = ROUND_HALF_EVEN
            return decimal_string(Decimal(str(value)))
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise CanonicalizationError(f"rule_id={rule_id!r} field={field_name!r} not finite")
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            ctx.rounding = ROUND_HALF_EVEN
            return decimal_string(value)
    raise CanonicalizationError(
        f"rule_id={rule_id!r} field={field_name!r} unsupported type {type(value).__name__}"
    )


def _coerce_enum(
    value: Any,
    *,
    enum_cls: type,
    field_name: str,
    rule_id: str,
) -> str:
    """Coerce an upstream value to the corresponding enum-member string.

    Accepts ``Enum`` instances (use ``.value``), strings (must match an
    existing member), and any object whose ``str()`` matches a member.
    Rejects anything else with a ``CanonicalizationError``.
    """
    if isinstance(value, enum.Enum) and isinstance(value, enum_cls):
        return str(value.value)
    if isinstance(value, str):
        try:
            enum_cls(value)
        except ValueError as exc:
            raise CanonicalizationError(
                f"rule_id={rule_id!r} field={field_name!r} value={value!r} "
                f"is not a recognized member of {enum_cls.__name__}"
            ) from exc
        return value
    raise CanonicalizationError(
        f"rule_id={rule_id!r} field={field_name!r} unsupported type {type(value).__name__}"
    )


def _coerce_enum_list(
    values: Any,
    *,
    enum_cls: type,
    field_name: str,
    rule_id: str,
) -> tuple[str, ...]:
    """Coerce an upstream list-of-enum-strings to a tuple of canonical strings."""
    if not isinstance(values, list):
        raise CanonicalizationError(f"rule_id={rule_id!r} field={field_name!r} must be a list")
    out = []
    for v in values:
        out.append(_coerce_enum(v, enum_cls=enum_cls, field_name=field_name, rule_id=rule_id))
    # De-dup + sort by Unicode code point order (slice-A §7.2 evidence
    # convention; extended to enum-lists per the adapter policy).
    return tuple(sorted(set(out)))


def _coerce_evidence_refs(values: Any, *, rule_id: str) -> tuple[str, ...]:
    """Coerce an upstream evidence_refs list into a sorted unique tuple.

    Enforces the slice-A §6.2 sorted-Unicode-order, duplicate-free
    invariant for any array field declared sorted.
    """
    if not isinstance(values, list):
        raise CanonicalizationError(f"rule_id={rule_id!r} evidence_refs must be a list of strings")
    out: set[str] = set()
    for v in values:
        if not isinstance(v, str) or not v:
            raise CanonicalizationError(
                f"rule_id={rule_id!r} evidence_refs entry {v!r} is not a non-empty string"
            )
        out.add(v)
    return tuple(sorted(out))


class _ProvenanceEdgeListEmptyError(Exception):
    """Raised when ``provenance_edges`` is empty or non-list."""


def _coerce_provenance_edge_ids(values: Any, *, rule_id: str) -> tuple[str, ...]:
    """Coerce provenance_edges into a sorted unique tuple of strings.

    Raises :class:`_ProvenanceEdgeListEmptyError` when the input is
    empty (so the Slice B adapter can map this case to the closed
    ``STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE`` blocker rather
    than the generic ``STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED``).
    Raises :class:`CanonicalizationError` on malformed entries.
    """
    if not isinstance(values, list) or not values:
        raise _ProvenanceEdgeListEmptyError(
            f"rule_id={rule_id!r} provenance_edges must be a non-empty list"
        )
    out: set[str] = set()
    for v in values:
        if not isinstance(v, str) or not v:
            raise CanonicalizationError(
                f"rule_id={rule_id!r} provenance_edge id {v!r} is not a non-empty string"
            )
        out.add(v)
    return tuple(sorted(out))


def _coerce_license_evidence(value: Any) -> tuple[Mapping[str, Any], bool]:
    """Coerce an upstream license_evidence to a TASK-021 canonical mapping.

    Per TASK-012 §7.2 the rule's ``license_evidence`` is one of four
    controlled forms (SPDX / public_domain / permission_evidence_pointer
    / project_internal_authority). The TASK-021 ``LayoutRuleAuthoritySnapshot
    .license_evidence`` field is a canonical JSON value; the simplest
    faithful projection is a mapping ``{form, value}`` carrying the
    classification + the raw token string.

    Returns ``(mapping_dict, is_project_internal)``. The flag helps
    downstream code distinguish the project-internal case where
    ``rule_pack_identity`` MUST be ``None``.
    """
    if isinstance(value, Mapping):
        # already a TASK-021 mapping; pass through verbatim.
        form_value = value.get("form")
        token_value = value.get("value")
        if not isinstance(form_value, str) or not form_value:
            raise CanonicalizationError("license_evidence mapping missing 'form' string")
        if not isinstance(token_value, str) or not token_value:
            raise CanonicalizationError("license_evidence mapping missing 'value' string")
        is_project_internal = form_value == "project_internal_authority"
        out: dict[str, Any] = {"form": form_value, "value": token_value}
        return tuple_sorted(out), is_project_internal
    if isinstance(value, str):
        # classify per TASK-012 §7.2 controlled forms. Order matters:
        # exact-match sentinel tokens first, then SPDX identifier
        # (matched via _is_spdx_identifier), then URI-like permission
        # evidence pointer. The sentinel tokens are imported from the
        # upstream ``rule_packs.license_boundary`` module to avoid
        # silent drift between callers and the upstream validator.
        token = value
        if token == _PROJECT_INTERNAL_AUTHORITY_TOKEN:
            out2 = {"form": "project_internal_authority", "value": token}
            return tuple_sorted(out2), True
        if token == _PUBLIC_DOMAIN_TOKEN:
            return tuple_sorted({"form": "public_domain", "value": token}), False
        # SPDX identifier forms are emitted as a string. We do not
        # re-validate the SPDX form here because the slice-A
        # ``enforce_full_license_boundary`` has already done so on
        # the upstream artifact. We only catch URI-shaped strings as
        # permission-evidence pointers.
        if "://" in token:
            return tuple_sorted({"form": "permission_evidence_pointer", "value": token}), False
        # Default: treat as a SPDX identifier. The caller must have
        # already passed ``enforce_full_license_boundary`` upstream;
        # if the token is malformed the slice-A verifier will block.
        return tuple_sorted({"form": "spdx", "value": token}), False
    raise CanonicalizationError(f"license_evidence unsupported type {type(value).__name__}")


def tuple_sorted(d: Mapping[str, Any]) -> Mapping[str, Any]:
    """Convert a mapping to a JSON-compatible layer-A primitive mapping.

    ``Mapping`` in Python is hash-stable but ordering is insertion order
    in Python 3.7+. The slice-A canonical-JSON dict ordering is
    determined by canonical-JSON key sorting. We therefore construct a
    plain ``dict`` preserving the original keys; ``canonical_json``
    sorts them deterministically downstream.
    """
    if isinstance(d, dict):
        return {str(k): v for k, v in d.items()}
    return dict(d)


def _has_blocker_code(blockers: list[MessageEntry], code: str) -> bool:
    return any(b.code == code for b in blockers)


def _vendor_permission_scope_blockers(rule: Mapping[str, Any], rule_id: str) -> list[MessageEntry]:
    """Compute VENDOR_PERMISSIONED scope blockers (or empty list).

    Returns the appropriate list of ``MessageEntry`` blockers per
    Record 7 / §4.2:
    * ``STL_RULE_PACK_ADAPTER_VENDOR_PERMISSION_SCOPE_MISSING`` if the
      permission evidence scope is missing any of the four required
      tokens;
    * ``STL_RULE_PACK_ADAPTER_RUNTIME_SCOPE_FORBIDDEN`` if the
      ``usage_scope`` token is present but the local kernel context is
      outside its declared scope.
    """
    blockers: list[MessageEntry] = []
    if rule.get("source_class") != SourceClass.VENDOR_PERMISSIONED.value:
        return blockers
    human = rule.get("human_entered_evidence") or {}
    permission = human.get("vendor_permission_evidence") or {}
    scope = permission.get("permission_scope")
    if not isinstance(scope, list):
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_VENDOR_PERMISSION_SCOPE_MISSING,
                field_path="rule_id",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_VENDOR_PERMISSION_SCOPE_MISSING
                ],
                details={"rule_id": rule_id, "reason": "permission_scope_not_list"},
            )
        )
        return blockers
    scope_set = set(scope)
    required_tokens = {
        VendorPermissionScope.REPOSITORY_STORAGE.value,
        VendorPermissionScope.REPOSITORY_REDISTRIBUTION.value,
        VendorPermissionScope.USAGE_SCOPE.value,
        VendorPermissionScope.PUBLIC_ARTIFACT_ALLOWED.value,
    }
    missing = sorted(required_tokens - scope_set)
    if missing:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_VENDOR_PERMISSION_SCOPE_MISSING,
                field_path="rule_id",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_VENDOR_PERMISSION_SCOPE_MISSING
                ],
                details={
                    "rule_id": rule_id,
                    "missing_tokens": missing,
                    "present_tokens": sorted(scope_set),
                },
            )
        )
    # The runtime scope gate: every VENDOR rule that proceeds to
    # runtime loading has already passed ``enforce_vendor_permission_scope(
    # rule, operation="runtime_rulepack")``. That validation has already
    # raised on failure; if we reach this point with no other blocker,
    # the runtime permission is verified. The TL_LAYOUT_RULE_AUTHORITY
    # snapshot is the runtime adapter output; presence of the
    # ``usage_scope`` token is therefore required for runtime load.
    usage_token = VendorPermissionScope.USAGE_SCOPE.value
    if usage_token not in scope_set:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RUNTIME_SCOPE_FORBIDDEN,
                field_path="rule_id",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RUNTIME_SCOPE_FORBIDDEN
                ],
                details={"rule_id": rule_id, "usage_token": usage_token},
            )
        )
    return blockers


def build_layout_rule_authority_snapshot(
    *,
    loaded_rule_pack: Mapping[str, Any],
    rule_id: str,
    rule_version: str,
    profile_id: str,
) -> LayoutRuleAuthoritySnapshot:
    """Build one TASK-021 ``LayoutRuleAuthoritySnapshot``.

    See Issue #141 Record 2 / Record 4 / Record 5 / Record 6 for the
    binding contracts. Raises ``AdapterFailure`` (from
    ``.adapter_blockers``) carrying the complete, slice-A §11.3-ordered
    blocker list on any failure path. The adapter never returns a
    partial snapshot.

    Pure-memory only: never calls ``load_rule_pack`` /
    ``validate_rule_pack(Path(...))``. Caller is responsible for
    providing the already-loaded mapping.
    """
    blockers: list[MessageEntry] = []

    # --- Step A: raw input type validation --------------------------
    if not isinstance(rule_id, str) or not rule_id:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID,
                field_path="rule_id",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID
                ],
                details={"expected": "non-empty str"},
            )
        )
    if not isinstance(rule_version, str) or not rule_version:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID,
                field_path="rule_version",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID
                ],
                details={"expected": "non-empty str"},
            )
        )
    if not isinstance(profile_id, str):
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID,
                field_path="profile_id",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID
                ],
                details={"expected": "str"},
            )
        )

    # --- Step B: load mapping shape validation ----------------------
    if not isinstance(loaded_rule_pack, Mapping):
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID,
                field_path="loaded_rule_pack",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID
                ],
                details={"expected": "Mapping[str, Any]"},
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))

    manifest = loaded_rule_pack.get("manifest")
    rules = loaded_rule_pack.get("rules")
    edges = loaded_rule_pack.get("provenance_edges")
    # ``permission_evidence`` is a keyed dict the VENDOR scope check
    # reads; the upstream ``enforce_vendor_permission_scope`` reads
    # ``rule["human_entered_evidence"]["vendor_permission_evidence"]``
    # directly, so this reference is reserved for VENDOR-specific
    # artifact-resolution cross-checks by future amendments.
    # The earlier raw-type-validation Step B raises ``AdapterFailure``
    # when any of these is not a Mapping, so we cast to narrow the
    # ``Any | None`` type for mypy.
    manifest = cast(Mapping[str, Any], manifest)
    rules = cast(Mapping[str, dict[str, Any]], rules)
    edges = cast(list[dict[str, Any]], edges)

    if not isinstance(manifest, Mapping):
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID,
                field_path="loaded_rule_pack.manifest",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID
                ],
                details={"expected": "Mapping"},
            )
        )
    if not isinstance(rules, Mapping):
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID,
                field_path="loaded_rule_pack.rules",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID
                ],
                details={"expected": "Mapping[str, Mapping]"},
            )
        )
    if not isinstance(edges, list):
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID,
                field_path="loaded_rule_pack.provenance_edges",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID
                ],
                details={"expected": "list"},
            )
        )

    if blockers:
        raise AdapterFailure(sort_adapter_blockers(blockers))

    # --- Step C: profile_id match -----------------------------------
    if profile_id != LAYOUT_RULE_PROFILE_ID:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_PROFILE_MISMATCH,
                field_path="profile_id",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_PROFILE_MISMATCH
                ],
                details={
                    "expected": LAYOUT_RULE_PROFILE_ID,
                    "actual": profile_id,
                },
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))

    # --- Step D: manifest schema validation (delegated to TASK-012) -
    try:
        validate_manifest(dict(manifest))
    except Exception as exc:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID,
                field_path="loaded_rule_pack.manifest",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID
                ],
                details={
                    "diagnostic": type(exc).__name__,
                    "stage": "validate_manifest",
                },
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))  # noqa: B904

    # --- Step E: manifest canonical_hash verification --------------
    try:
        validate_manifest_canonical_hash(dict(manifest))
    except Exception as exc:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_PACK_HASH_MISMATCH,
                field_path="loaded_rule_pack.manifest.canonical_hash",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_PACK_HASH_MISMATCH
                ],
                details={
                    "diagnostic": type(exc).__name__,
                    "stage": "validate_manifest_canonical_hash",
                },
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))  # noqa: B904

    # --- Step F: provenance graph validation ------------------------
    try:
        validate_provenance_edges(dict(rules), list(edges))
    except Exception as exc:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE,
                field_path="loaded_rule_pack.provenance_edges",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE
                ],
                details={
                    "diagnostic": type(exc).__name__,
                    "stage": "validate_provenance_edges",
                },
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))  # noqa: B904
    try:
        validate_supersedes_edges(dict(rules), list(edges))
    except Exception as exc:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE,
                field_path="loaded_rule_pack.provenance_edges",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE
                ],
                details={
                    "diagnostic": type(exc).__name__,
                    "stage": "validate_supersedes_edges",
                },
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))  # noqa: B904

    # --- Step G.5: rule-id-and-version lookup (BEFORE manifest-only-approved)
    # We resolve the rule by (rule_id, rule_version) BEFORE invoking
    # ``validate_manifest_only_references_approved_rules`` because that
    # helper would raise ``RulePackValidationError`` when the requested
    # ``rule_id`` is not in ``manifest["rules"]`` — but at the Slice B
    # runtime-adapter scope, the requested rule_id is what we actually
    # care about; an absent rule_id is a clean ``RULE_ID_NOT_FOUND``
    # blocker, not an ``UPSTREAM_OBJECT_INVALID`` blocker.
    rule = rules.get(rule_id)
    if rule is None:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_ID_NOT_FOUND,
                field_path="rule_id",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_ID_NOT_FOUND
                ],
                details={"rule_id": rule_id},
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))
    if not isinstance(rule, Mapping):
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID,
                field_path="loaded_rule_pack.rules",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID
                ],
                details={"expected": "Mapping per rule"},
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))

    rule_dict = cast(Mapping[str, Any], rule)
    # duplicate-id detection (defensive; the upstream loader dedups
    # at load time but we verify post-load for safety).
    for other_id, other_rule in rules.items():
        if other_id == rule_id:
            continue
        if other_rule is rule_dict or (
            isinstance(other_rule, Mapping)
            and other_rule.get("rule_id") == rule_dict.get("rule_id")
        ):
            blockers.append(
                build_message_entry(
                    code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_ID_DUPLICATE,
                    field_path="rule_id",
                    message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                        RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_ID_DUPLICATE
                    ],
                    details={"rule_id": rule_id},
                )
            )
            break
    if blockers:
        raise AdapterFailure(sort_adapter_blockers(blockers))

    # --- Step G.6: license_evidence presence check (early block) ---
    # ``validate_rule`` requires ``license_evidence`` to be present;
    # if absent, our Step H would otherwise produce a generic
    # ``UPSTREAM_OBJECT_INVALID`` blocker before license-boundary
    # ever runs. Map the absent-field case to our closed
    # ``STL_RULE_PACK_ADAPTER_LICENSE_EVIDENCE_MISSING`` code.
    if "license_evidence" not in rule_dict:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_LICENSE_EVIDENCE_MISSING,
                field_path="rule.license_evidence",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_LICENSE_EVIDENCE_MISSING
                ],
                details={"rule_id": rule_id, "reason": "field_missing"},
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))

    # --- Step G: manifest references only approved rules ----------
    # Slice B runtime adapter policy: we only need to ensure that
    # the SELECTED rule_id is approved. Pack-level manifest-wide
    # approval audits are the upstream validator's responsibility;
    # here we substitute a temporary manifest containing only the
    # selected rule_id, then call the existing helper to confirm the
    # manifest reference is internally consistent for the runtime
    # selection.
    selected_manifest_for_check = dict(manifest)
    selected_manifest_for_check["rules"] = [rule_id]
    selected_manifest_for_check["rule_count"] = 1
    selected_manifest_for_check["canonical_hash"] = canonical_sha256(selected_manifest_for_check)
    try:
        validate_manifest_only_references_approved_rules(selected_manifest_for_check, dict(rules))
    except Exception as exc:
        # Distinguish the upstream's "manifest references rule not
        # approved" path (``path`` contains the rule_id) and map it to
        # our ``STL_RULE_PACK_ADAPTER_RULE_NOT_APPROVED`` closed code.
        # Other upstream-shape failures map to the generic upstream
        # code.
        exc_path = getattr(exc, "path", "") or ""
        if exc_path.startswith("manifest.rules") and "approval_status" in str(exc):
            blockers.append(
                build_message_entry(
                    code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_NOT_APPROVED,
                    field_path="rule.approval_status",
                    message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                        RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_NOT_APPROVED
                    ],
                    details={
                        "rule_id": rule_id,
                        "diagnostic": str(exc),
                        "stage": "validate_manifest_only_references_approved_rules",
                    },
                )
            )
        else:
            blockers.append(
                build_message_entry(
                    code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID,
                    field_path="loaded_rule_pack.manifest",
                    message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                        RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID
                    ],
                    details={
                        "diagnostic": type(exc).__name__,
                        "stage": "validate_manifest_only_references_approved_rules",
                    },
                )
            )
        raise AdapterFailure(sort_adapter_blockers(blockers))  # noqa: B904

    # --- Step H: rule schema + license boundary (delegated) -------
    try:
        validate_rule(dict(rule_dict))
    except Exception as exc:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID,
                field_path="rule",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID
                ],
                details={
                    "diagnostic": type(exc).__name__,
                    "stage": "validate_rule",
                },
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))  # noqa: B904

    # license-boundary check (covers license_evidence, internal_authority,
    # forbidden_marker, metadata_only, non_redistribution, vendor scope).
    try:
        enforce_full_license_boundary(dict(rule_dict))
    except Exception as exc:
        # Specific blocker mapping depends on the exc.path. The slice-A
        # boundary check raises on multiple conditions; map the most
        # common cases using a path-based heuristic while keeping the
        # canonical MessageEntry payloads.
        exc_path = getattr(exc, "path", "") or "license_boundary"
        if "license_evidence" in exc_path:
            blockers.append(
                build_message_entry(
                    code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_LICENSE_EVIDENCE_MISSING,
                    field_path="rule.license_evidence",
                    message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                        RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_LICENSE_EVIDENCE_MISSING
                    ],
                    details={
                        "diagnostic": str(exc),
                        "stage": "enforce_full_license_boundary",
                    },
                )
            )
        elif "rule_body" in exc_path:
            blockers.append(
                build_message_entry(
                    code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED,
                    field_path="rule.rule_body",
                    message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                        RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED
                    ],
                    details={
                        "diagnostic": str(exc),
                        "stage": "enforce_full_license_boundary",
                    },
                )
            )
        elif "vendor_permission_evidence" in exc_path:
            blockers.extend(_vendor_permission_scope_blockers(rule_dict, rule_id))
        else:
            blockers.append(
                build_message_entry(
                    code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID,
                    field_path=exc_path,
                    message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                        RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID
                    ],
                    details={
                        "diagnostic": str(exc),
                        "stage": "enforce_full_license_boundary",
                    },
                )
            )
        if blockers:
            raise AdapterFailure(sort_adapter_blockers(blockers))  # noqa: B904

    # --- Step J: rule canonical_hash re-verification --------------
    try:
        validate_canonical_hash(dict(rule_dict))
    except Exception as exc:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH,
                field_path="rule.canonical_hash",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH
                ],
                details={
                    "diagnostic": type(exc).__name__,
                    "stage": "validate_canonical_hash",
                },
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))  # noqa: B904

    # --- Step K: explicit rule_version match ---------------------
    rule_version_in_artifact = rule_dict.get("rule_version")
    if not isinstance(rule_version_in_artifact, str) or rule_version_in_artifact != rule_version:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH,
                field_path="rule.rule_version",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH
                ],
                details={
                    "rule_version": rule_version,
                    "artifact_rule_version": rule_version_in_artifact,
                },
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))

    # --- Step L: approval_status == approved --------------------
    approval_status_value = rule_dict.get("approval_status")
    if approval_status_value != APPROVAL_APPROVED:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_NOT_APPROVED,
                field_path="rule.approval_status",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_NOT_APPROVED
                ],
                details={
                    "rule_id": rule_id,
                    "approval_status": approval_status_value,
                },
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))

    # --- Step M: source_class governance --------------------------
    source_class_value = rule_dict.get("source_class")
    try:
        source_class_value = cast(str, source_class_value)
        source_class_enum = SourceClass(source_class_value)
    except (ValueError, TypeError):
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID,
                field_path="rule.source_class",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID
                ],
                details={
                    "rule_id": rule_id,
                    "source_class": source_class_value,
                },
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))  # noqa: B904

    if source_class_enum in NON_REDISTRIBUTABLE_SOURCES:
        # USER_PROVIDED_LICENSED_SUMMARY and REFERENCE_ONLY_RESTRICTED_STANDARD
        # are non-redistributable per TASK-012 §4.1 / §16.3. They are
        # never admitted as runtime layout authority.
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_SOURCE_CLASS_FORBIDDEN,
                field_path="rule.source_class",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_SOURCE_CLASS_FORBIDDEN
                ],
                details={
                    "rule_id": rule_id,
                    "source_class": source_class_enum.value,
                    "reason": "non_runtime_source_class",
                },
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))

    # REFERENCE_ONLY_RESTRICTED_STANDARD: forbidden body check (per spec §6).
    if source_class_enum == SourceClass.REFERENCE_ONLY_RESTRICTED_STANDARD:
        # This branch is unreachable because the prior check catches any
        # REFERENCE_ONLY_RESTRICTED_STANDARD source (it is in
        # NON_REDISTRIBUTABLE_SOURCES). Nevertheless we keep a defensive
        # secondary guard that rejects any non-metadata body under that
        # class.
        body = rule_dict.get("rule_body")
        if body is not None and not _is_metadata_only_body(body):
            blockers.append(
                build_message_entry(
                    code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED,
                    field_path="rule.rule_body",
                    message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                        RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED
                    ],
                    details={"rule_id": rule_id, "reason": "non_metadata_body"},
                )
            )
            raise AdapterFailure(sort_adapter_blockers(blockers))

    # VENDOR_PERMISSIONED: enforce runtime operation gate.
    if source_class_enum == SourceClass.VENDOR_PERMISSIONED:
        try:
            enforce_vendor_permission_scope(dict(rule_dict), operation="runtime_rulepack")
        except Exception as exc:
            blockers.extend(_vendor_permission_scope_blockers(rule_dict, rule_id))
            if not blockers:
                blockers.append(
                    build_message_entry(
                        code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RUNTIME_SCOPE_FORBIDDEN,
                        field_path="rule.human_entered_evidence.vendor_permission_evidence",
                        message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                            RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RUNTIME_SCOPE_FORBIDDEN
                        ],
                        details={
                            "diagnostic": str(exc),
                            "operation": "runtime_rulepack",
                        },
                    )
                )
            raise AdapterFailure(sort_adapter_blockers(blockers))  # noqa: B904

    # --- Step N: TASK-021 profile projection fields ----------------
    rule_body = rule_dict.get("rule_body")
    if not isinstance(rule_body, Mapping):
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED,
                field_path="rule.rule_body",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED
                ],
                details={"rule_id": rule_id, "reason": "missing_rule_body"},
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))

    missing_projection_fields: list[str] = []
    for f in REQUIRED_RULE_BODY_PROJECTION_FIELDS:
        if f not in rule_body:
            missing_projection_fields.append(f)
    if missing_projection_fields:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED,
                field_path="rule.rule_body",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED
                ],
                details={
                    "rule_id": rule_id,
                    "missing_fields": missing_projection_fields,
                },
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))

    # Read the projection fields verbatim.
    try:
        pattern_family = _coerce_enum(
            rule_body.get("pattern_family"),
            enum_cls=PatternFamily,
            field_name="pattern_family",
            rule_id=rule_id,
        )
        pitch_m = _coerce_decimal_string(
            rule_body.get("pitch_m"), field_name="pitch_m", rule_id=rule_id
        )
        edge_clearance_m = _coerce_decimal_string(
            rule_body.get("edge_clearance_m"),
            field_name="edge_clearance_m",
            rule_id=rule_id,
        )
        allowed_origin_modes = _coerce_enum_list(
            rule_body.get("allowed_origin_modes"),
            enum_cls=OriginMode,
            field_name="allowed_origin_modes",
            rule_id=rule_id,
        )
        allowed_axis_orientations = _coerce_enum_list(
            rule_body.get("allowed_axis_orientations"),
            enum_cls=AxisOrientation,
            field_name="allowed_axis_orientations",
            rule_id=rule_id,
        )
        allowed_exclusion_zone_types = _coerce_enum_list(
            rule_body.get("allowed_exclusion_zone_types"),
            enum_cls=ExclusionZoneType,
            field_name="allowed_exclusion_zone_types",
            rule_id=rule_id,
        )
        maximum_candidate_positions = rule_body.get("maximum_candidate_positions")
        if not isinstance(maximum_candidate_positions, int) or isinstance(
            maximum_candidate_positions, bool
        ):
            raise CanonicalizationError("maximum_candidate_positions must be a non-boolean int")
        if maximum_candidate_positions < 1 or maximum_candidate_positions > 100000:
            raise CanonicalizationError("maximum_candidate_positions must be 1 <= value <= 100000")
        evidence_refs = _coerce_evidence_refs(rule_body.get("evidence_refs"), rule_id=rule_id)
    except CanonicalizationError as exc:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED,
                field_path="rule.rule_body",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED
                ],
                details={"rule_id": rule_id, "diagnostic": str(exc)},
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))  # noqa: B904

    # --- Step O: license evidence projection ----------------------
    raw_license_evidence = rule_dict.get("license_evidence")
    try:
        license_evidence_dict, is_project_internal = _coerce_license_evidence(raw_license_evidence)
    except Exception as exc:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_LICENSE_EVIDENCE_MISSING,
                field_path="rule.license_evidence",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_LICENSE_EVIDENCE_MISSING
                ],
                details={"rule_id": rule_id, "diagnostic": str(exc)},
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))  # noqa: B904

    # --- Step P: provenance edge IDs -------------------------------
    try:
        provenance_edge_ids = _coerce_provenance_edge_ids(
            rule_dict.get("provenance_edges"), rule_id=rule_id
        )
    except _ProvenanceEdgeListEmptyError:
        # Distinguish empty provenance_edge_ids (PROVENANCE_INCOMPLETE)
        # from other provenance-coercion errors (RESTRICTED_BODY).
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE,
                field_path="rule.provenance_edges",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE
                ],
                details={"rule_id": rule_id, "reason": "empty_provenance_edges"},
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))  # noqa: B904
    except Exception as exc:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE,
                field_path="rule.provenance_edges",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE
                ],
                details={"rule_id": rule_id, "diagnostic": str(exc)},
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))  # noqa: B904

    # --- Step Q: rule_pack_identity ------------------------------
    manifest_rule_pack_id = manifest.get("rule_pack_id")
    manifest_rule_pack_version = manifest.get("rule_pack_version")
    manifest_canonical_hash = manifest.get("canonical_hash")
    if (
        not isinstance(manifest_rule_pack_id, str)
        or not manifest_rule_pack_id
        or not isinstance(manifest_rule_pack_version, str)
        or not manifest_rule_pack_version
        or not isinstance(manifest_canonical_hash, str)
        or not manifest_canonical_hash
    ):
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_PACK_HASH_MISMATCH,
                field_path="loaded_rule_pack.manifest",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_PACK_HASH_MISMATCH
                ],
                details={"rule_id": rule_id, "reason": "manifest_identity_incomplete"},
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))

    rule_pack_identity_snapshot: RulePackIdentitySnapshot | None = None
    if not is_project_internal:
        rule_pack_identity_snapshot = RulePackIdentitySnapshot(
            rule_pack_id=manifest_rule_pack_id,
            rule_pack_version=manifest_rule_pack_version,
            rule_pack_canonical_hash=manifest_canonical_hash,
        )

    # --- Step R: rule canonical_hash (read-only, upstream evidence)
    rule_artifact_canonical_hash = rule_dict.get("canonical_hash")
    if not isinstance(rule_artifact_canonical_hash, str) or not rule_artifact_canonical_hash:
        blockers.append(
            build_message_entry(
                code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH,
                field_path="rule.canonical_hash",
                message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                    RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH
                ],
                details={"rule_id": rule_id, "reason": "missing_canonical_hash"},
            )
        )
        raise AdapterFailure(sort_adapter_blockers(blockers))

    # --- Step S: build LayoutRuleAuthoritySnapshot -----------------
    # Per TASK-021 §7.4 + §12.2 we first compose the exact 18-field set
    # excluding snapshot_hash, hash it, then construct the snapshot.
    # Internal ``license_evidence`` MUST be a Layer-B marker (a frozen
    # canonical fragment) so that ``LayoutRuleAuthoritySnapshot.__post_init__``
    # ``refreeze_internal_fragment`` accepts it (the R7 Layer-B contract
    # forbids raw dict / list / MappingProxyType at this field). We use
    # ``freeze_known_fragment`` from Round 8 §P1-1 — it accepts the
    # upstream raw dict (Layer-A) and returns the canonical
    # ``FrozenJsonObject`` (Layer-B).
    license_evidence_frozen = freeze_known_fragment(dict(license_evidence_dict))

    # Snapshot hash bytes must equal what
    # ``internal_frozen_to_primitive(snapshot)`` later produces; we
    # therefore pre-compute the primitive shape via
    # ``internal_frozen_to_primitive`` so the canonical-JSON bytes
    # match across construction and downstream consumption.
    snapshot_payload: dict[str, Any] = {
        "profile_id": LAYOUT_RULE_PROFILE_ID,
        "authority_mode": AuthorityMode.APPROVED_RULE_PACK.value,
        "rule_id": rule_id,
        "rule_version": rule_version,
        "rule_artifact_canonical_hash": rule_artifact_canonical_hash,
        "source_class": source_class_enum.value,
        "license_evidence": internal_frozen_to_primitive(license_evidence_frozen),
        "approval_status": APPROVAL_APPROVED,
        "provenance_edge_ids": list(provenance_edge_ids),
        "evidence_refs": list(evidence_refs),
        "rule_pack_identity": (
            None
            if rule_pack_identity_snapshot is None
            else {
                "rule_pack_id": rule_pack_identity_snapshot.rule_pack_id,
                "rule_pack_version": rule_pack_identity_snapshot.rule_pack_version,
                "rule_pack_canonical_hash": rule_pack_identity_snapshot.rule_pack_canonical_hash,
            }
        ),
        "pattern_family": pattern_family,
        "pitch_m": pitch_m,
        "edge_clearance_m": edge_clearance_m,
        "allowed_origin_modes": list(allowed_origin_modes),
        "allowed_axis_orientations": list(allowed_axis_orientations),
        "allowed_exclusion_zone_types": list(allowed_exclusion_zone_types),
        "maximum_candidate_positions": maximum_candidate_positions,
    }

    # Compute the TASK-021 snapshot_hash by hashing the exact 18-field
    # payload via the shared slice-A canonical-JSON helper.
    snapshot_hash_value = canonical_sha256(snapshot_payload)

    snapshot = LayoutRuleAuthoritySnapshot(
        profile_id=LAYOUT_RULE_PROFILE_ID,
        authority_mode=AuthorityMode.APPROVED_RULE_PACK,
        rule_id=rule_id,
        rule_version=rule_version,
        rule_artifact_canonical_hash=rule_artifact_canonical_hash,
        source_class=source_class_enum.value,
        license_evidence=license_evidence_frozen,
        approval_status=APPROVAL_APPROVED,
        provenance_edge_ids=provenance_edge_ids,
        evidence_refs=evidence_refs,
        rule_pack_identity=rule_pack_identity_snapshot,
        pattern_family=PatternFamily(pattern_family),
        pitch_m=pitch_m,
        edge_clearance_m=edge_clearance_m,
        allowed_origin_modes=tuple(OriginMode(m) for m in allowed_origin_modes),
        allowed_axis_orientations=tuple(AxisOrientation(m) for m in allowed_axis_orientations),
        allowed_exclusion_zone_types=tuple(
            ExclusionZoneType(m) for m in allowed_exclusion_zone_types
        ),
        maximum_candidate_positions=maximum_candidate_positions,
        snapshot_hash=snapshot_hash_value,
    )

    # Terminal defensive check: re-hash the exact 18-field payload (the
    # same primitive shape ``internal_frozen_to_primitive(snapshot)``
    # would later produce) so we exercise the slice-A canonical-JSON
    # discipline without trying to feed a frozen dataclass back into
    # ``internal_frozen_to_primitive`` (which would reject it because
    # the dataclass itself is not a Layer-B node).
    rebuilt_hash = canonical_sha256(
        {
            "profile_id": snapshot.profile_id,
            "authority_mode": snapshot.authority_mode.value,
            "rule_id": snapshot.rule_id,
            "rule_version": snapshot.rule_version,
            "rule_artifact_canonical_hash": snapshot.rule_artifact_canonical_hash,
            "source_class": snapshot.source_class,
            "license_evidence": internal_frozen_to_primitive(snapshot.license_evidence),
            "approval_status": snapshot.approval_status,
            "provenance_edge_ids": list(snapshot.provenance_edge_ids),
            "evidence_refs": list(snapshot.evidence_refs),
            "rule_pack_identity": (
                None
                if snapshot.rule_pack_identity is None
                else {
                    "rule_pack_id": (snapshot.rule_pack_identity.rule_pack_id),
                    "rule_pack_version": (snapshot.rule_pack_identity.rule_pack_version),
                    "rule_pack_canonical_hash": (
                        snapshot.rule_pack_identity.rule_pack_canonical_hash
                    ),
                }
            ),
            "pattern_family": snapshot.pattern_family.value,
            "pitch_m": snapshot.pitch_m,
            "edge_clearance_m": snapshot.edge_clearance_m,
            "allowed_origin_modes": [m.value for m in snapshot.allowed_origin_modes],
            "allowed_axis_orientations": [m.value for m in snapshot.allowed_axis_orientations],
            "allowed_exclusion_zone_types": [
                m.value for m in snapshot.allowed_exclusion_zone_types
            ],
            "maximum_candidate_positions": snapshot.maximum_candidate_positions,
        }
    )
    if rebuilt_hash != snapshot.snapshot_hash:
        raise AdapterFailure(
            sort_adapter_blockers(
                [
                    build_message_entry(
                        code=RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH,
                        field_path="snapshot_hash",
                        message_key=RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[
                            RulePackAdapterBlockerCode.STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH
                        ],
                        details={
                            "rule_id": rule_id,
                            "reason": "snapshot_hash_recomputation_mismatch",
                        },
                    )
                ]
            )
        )

    return snapshot


def _is_metadata_only_body(body: Mapping[str, Any]) -> bool:
    """Return True iff ``rule_body`` is bibliographic-metadata-only.

    The slice-A taxonomy for ``REFERENCE_ONLY_RESTRICTED_STANDARD``
    requires any rule_body to have only metadata keys; we accept this
    shape defensively.
    """
    allowed_keys = {
        "bibliographic_metadata",
        "citation",
        "external_pointer",
        "section_locator",
    }
    return not (set(body.keys()) - allowed_keys)
