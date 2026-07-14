"""TASK-022 Slice B1 — rule-pack adapter.

Implements the frozen ``build_shell_bundle_rule_authority_snapshot``
operation described in Issue #147 Record 2 / Record 3 / Record 4 /
Record 5. It is a pure in-memory adapter that consumes an already
loaded TASK-012 rule-pack mapping ``{manifest, rules,
provenance_edges, permission_evidence}`` (the exact shape produced by
``hexagent.rule_packs.loader.load_rule_pack``) and returns a TASK-022
``ShellBundleGeometryRuleAuthoritySnapshot`` on the success path.

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
* inference of any default field;
* calls to ``load_rule_pack`` — the caller MUST supply the in-memory
  mapping directly;
* calls to ``validate_rule_pack(Path(...))`` — the adapter operates
  on already-loaded mappings only.

It reuses the existing pure TASK-012 validators in
``hexagent.rule_packs.{schema, license_boundary, provenance}`` and the
existing slice-A canonical / hash / projection / ordering authorities
in ``.canonical`` and ``.models``. No new fixture, mock, default rule,
or stub catalog is introduced as production authority.

The TASK-012 ``source_class`` enum is governed per the §4.1 governance
matrix:

* runtime-capable: PUBLIC_DOMAIN, OPEN_LICENSE, INTERNAL_ENGINEERING_RULE,
  DERIVED_ENGINEERING_RULE, VENDOR_PERMISSIONED;
* runtime-forbidden: USER_PROVIDED_LICENSED_SUMMARY,
  REFERENCE_ONLY_RESTRICTED_STANDARD.

``VENDOR_PERMISSIONED`` requires all four TASK-012 ``usage_scope``
permission tokens; absence of any token blocks. The TASK-022
``verify_rule_authority`` defensive terminal additionally requires
the canonical ``REPOSITORY_REDISTRIBUTION_PERMITTED`` and
``RUNTIME_USE_PERMITTED`` license-evidence tokens per Issue #147
Record 5 / frozen design §7.6.

The TASK-022 profile projection fields (``profile_id``,
``allowed_shell_authority_modes``,
``minimum_bundle_peripheral_allowance_m``, ``minimum_radial_clearance_m``,
``maximum_position_count``, ``evidence_refs``) are read verbatim from
the upstream rule's ``rule_body`` mapping under the TASK-020-S2
read-source discipline. No inference is performed on missing or
unknown fields; missing fields block and unknown fields block.

The ``profile_id`` is required to match the frozen TASK-022 profile
constant exactly; it is NEVER caller-supplied, per Issue #147
Record 2.

The slice-A ``verify_rule_authority`` (frozen design §9) is run as
the defensive terminal check before the adapter returns. Any
verification failure is converted to the frozen
``SBG_RULE_ADAPTER_SNAPSHOT_VERIFICATION_FAILED`` blocker; no
partial snapshot is ever returned.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Any, Final, cast

from hexagent.rule_packs.license_boundary import (
    enforce_full_license_boundary,
    enforce_vendor_permission_scope,
)
from hexagent.rule_packs.models import ApprovalStatus as Task012ApprovalStatus
from hexagent.rule_packs.models import SourceClass as Task012SourceClass
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
    RULE_PACK_ADAPTER_DEFAULT_FIELD_PATH,
    RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY,
    AdapterFailure,
    RulePackAdapterBlockerCode,
    build_message_entry,
)
from .canonical import (
    DECIMAL_PRECISION,
    CanonicalizationError,
    dataclass_to_mapping,
    decimal_string,
    parse_decimal,
    sha256_hex,
)
from .models import (
    PROFILE_ID,
    RULE_SNAPSHOT_SCHEMA_VERSION,
    MessageEntry,
    RuleAuthorityMode,
    RulePackIdentitySnapshot,
    ShellBundleGeometryRuleAuthoritySnapshot,
    ShellInsideDiameterAuthorityMode,
)

# Source classes that are RUNTIME-FORBIDDEN under the TASK-012 §4.1
# governance matrix (Issue #147 Record 5). Any rule whose source_class
# lands in this set blocks ``SBG_RULE_ADAPTER_SOURCE_CLASS_RUNTIME_FORBIDDEN``
# before any TASK-022 projection happens.
RUNTIME_FORBIDDEN_SOURCE_CLASSES: Final[frozenset[str]] = frozenset(
    {
        Task012SourceClass.USER_PROVIDED_LICENSED_SUMMARY.value,
        Task012SourceClass.REFERENCE_ONLY_RESTRICTED_STANDARD.value,
    }
)

# TASK-012 ``approval_status`` must equal this token (Record 5).
TASK012_APPROVED: Final[str] = Task012ApprovalStatus.APPROVED.value

# Frozen list of TASK-022 ``rule_body`` projection fields. These are
# the ONLY rule_body entries the adapter reads; any other key blocks.
# Issue #147 Record 3 (binding commit 4964516300).
TASK022_RULE_BODY_PROJECTION_FIELDS: Final[tuple[str, ...]] = (
    "profile_id",
    "allowed_shell_authority_modes",
    "minimum_bundle_peripheral_allowance_m",
    "minimum_radial_clearance_m",
    "maximum_position_count",
    "evidence_refs",
)

# TASK-012 manifest required top-level fields. The loader emits all
# of these on a valid pack, but the adapter performs its own existence
# check first because the ``loaded_rule_pack`` parameter is
# caller-supplied and may omit any.
TASK012_MANIFEST_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
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

# TASK-012 rule artifact required top-level fields (subset that the
# adapter actually reads). The adapter reads `rule_id`, `rule_version`,
# `canonical_hash`, `source_class`, `license_evidence`,
# `approval_status`, `provenance_edges`, and `rule_body` for projection;
# remaining TASK-012 fields are checked by the `validate_rule`
# validator that the adapter invokes.
TASK012_RULE_TOP_LEVEL_FIELDS: Final[tuple[str, ...]] = (
    "rule_id",
    "rule_version",
    "canonical_hash",
    "source_class",
    "license_evidence",
    "approval_status",
    "provenance_edges",
    "rule_body",
)

# Exact four top-level keys a TASK-012 ``load_rule_pack`` output MUST
# carry. No unknown keys, no missing keys.
TASK012_LOADED_PACK_REQUIRED_KEYS: Final[tuple[str, ...]] = (
    "manifest",
    "rules",
    "provenance_edges",
    "permission_evidence",
)


# --- 16-stage validation pipeline (Issue #147 Record 4) -------------------


# Stage ranks are 1-based. Stages map to the closed Issue #147 Record 4
# pipeline order:
STAGE_RAW_ARG: Final[int] = 1
STAGE_PACK_SHAPE: Final[int] = 2
STAGE_MANIFEST_SCHEMA: Final[int] = 3
STAGE_MANIFEST_HASH: Final[int] = 4
STAGE_MANIFEST_REFERENCES: Final[int] = 5
STAGE_RULE_ID_LEXICAL: Final[int] = 6
STAGE_RULE_LOOKUP: Final[int] = 7
STAGE_RULE_SCHEMA: Final[int] = 8
STAGE_RULE_HASH: Final[int] = 9
STAGE_RULE_IDENTITY: Final[int] = 10
STAGE_RULE_APPROVAL: Final[int] = 11
STAGE_SOURCE_CLASS_LICENSE: Final[int] = 12
STAGE_PROVENANCE: Final[int] = 13
STAGE_RULE_BODY: Final[int] = 14
STAGE_SNAPSHOT_BUILD: Final[int] = 15
STAGE_SNAPSHOT_VERIFY: Final[int] = 16


# --- adapter helpers --------------------------------------------------------


def _empty_evidence_refs() -> tuple[str, ...]:
    return ()


def _collect_blockers_by_stage(
    stage_blockers: dict[int, list[MessageEntry]],
) -> list[MessageEntry]:
    """Flatten a stage-bucketed blocker dict into a single list.

    Stage ordering is preserved (1, 2, 3, ...). Within a single stage,
    the relative accumulation order from the validator is preserved
    (callers append in the order defects are discovered).
    """
    out: list[MessageEntry] = []
    for stage in sorted(stage_blockers):
        out.extend(stage_blockers[stage])
    return out


def _make_blocker(
    stage: int,
    code: str,
    field_path: str | None = None,
    *,
    message_key: str | None = None,
    evidence_refs: Sequence[str] = (),
    details: Mapping[str, Any] | None = None,
    identity_to_stage: dict[int, int] | None = None,
) -> MessageEntry:
    """Build one canonical MessageEntry and optionally stage-rank it.

    Defaults the ``field_path`` and ``message_key`` from the closed
    frozen mappings (Record 4 defaults). Records ``stage`` against
    ``identity_to_stage[id(entry)]`` so the final ordering knows
    which adapter-stage this blocker belongs to.
    """
    entry = build_message_entry(
        code=code,
        field_path=(
            field_path if field_path is not None else RULE_PACK_ADAPTER_DEFAULT_FIELD_PATH[code]
        ),
        message_key=(
            message_key if message_key is not None else RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY[code]
        ),
        evidence_refs=evidence_refs,
        details=details,
    )
    if identity_to_stage is not None:
        identity_to_stage[id(entry)] = stage
    return entry


def _coerce_decimal_string(
    value: Any,
    *,
    field_name: str,
    rule_id: str,
    allow_zero: bool,
) -> str:
    """Convert an upstream value to a TASK-022 canonical decimal string.

    Accepts ``str`` / ``int`` / ``Decimal``. ``bool`` is rejected
    explicitly. Negative numbers are rejected when ``allow_zero`` is
    False. NaN / infinity are rejected. The 50-digit
    ``ROUND_HALF_EVEN`` context is enforced.
    """
    if isinstance(value, bool):
        raise CanonicalizationError(
            f"rule_id={rule_id!r} field={field_name!r} bool is not a number"
        )
    if isinstance(value, str):
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            ctx.rounding = ROUND_HALF_EVEN
            parsed = parse_decimal(value, positive=not allow_zero)
        if not allow_zero and not parsed.is_finite():
            raise CanonicalizationError(f"rule_id={rule_id!r} field={field_name!r} not finite")
        if not allow_zero and parsed < 0:
            raise CanonicalizationError(
                f"rule_id={rule_id!r} field={field_name!r} negative not allowed"
            )
        if not parsed.is_finite():
            raise CanonicalizationError(f"rule_id={rule_id!r} field={field_name!r} not finite")
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            ctx.rounding = ROUND_HALF_EVEN
            return decimal_string(parsed)
    if isinstance(value, int):
        parsed = Decimal(value)
        if not parsed.is_finite():
            raise CanonicalizationError(f"rule_id={rule_id!r} field={field_name!r} not finite")
        if not allow_zero and parsed < 0:
            raise CanonicalizationError(
                f"rule_id={rule_id!r} field={field_name!r} negative not allowed"
            )
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            ctx.rounding = ROUND_HALF_EVEN
            return decimal_string(parsed)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise CanonicalizationError(f"rule_id={rule_id!r} field={field_name!r} not finite")
        if not allow_zero and value < 0:
            raise CanonicalizationError(
                f"rule_id={rule_id!r} field={field_name!r} negative not allowed"
            )
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            ctx.rounding = ROUND_HALF_EVEN
            return decimal_string(value)
    raise CanonicalizationError(
        f"rule_id={rule_id!r} field={field_name!r} unsupported type {type(value).__name__}"
    )


def _coerce_authority_modes(
    values: Any,
    *,
    rule_id: str,
) -> tuple[ShellInsideDiameterAuthorityMode, ...]:
    """Coerce ``rule_body.allowed_shell_authority_modes``.

    Rejects non-lists, empty lists, non-strings, unknown tokens, and
    duplicates; returns the Unicode code-point sorted tuple of
    :class:`ShellInsideDiameterAuthorityMode` members.
    """
    if not isinstance(values, list) or not values:
        raise CanonicalizationError(
            f"rule_id={rule_id!r} allowed_shell_authority_modes must be a non-empty list of strings"
        )
    seen: set[str] = set()
    coerced: list[str] = []
    for entry in values:
        if not isinstance(entry, str) or not entry:
            raise CanonicalizationError(
                f"rule_id={rule_id!r} allowed_shell_authority_modes entry "
                f"{entry!r} is not a non-empty string"
            )
        if entry in seen:
            raise CanonicalizationError(
                f"rule_id={rule_id!r} allowed_shell_authority_modes "
                f"contains duplicate entry {entry!r}"
            )
        seen.add(entry)
        try:
            ShellInsideDiameterAuthorityMode(entry)
        except ValueError as exc:
            raise CanonicalizationError(
                f"rule_id={rule_id!r} allowed_shell_authority_modes entry "
                f"{entry!r} is not a closed-shell-authority-mode token"
            ) from exc
        coerced.append(entry)
    return tuple(ShellInsideDiameterAuthorityMode(value) for value in sorted(coerced))


def _coerce_string_array(
    values: Any,
    *,
    field_name: str,
    rule_id: str,
) -> tuple[str, ...]:
    """Coerce a ``list[str]`` into a sorted-unique tuple.

    Rejects non-lists, non-string entries, empty strings, and
    duplicates. Used for ``rule_body.evidence_refs`` and
    ``provenance_edge_ids`` (the latter is sorted via the same
    helper after the raw ``provenance_edges`` rule-body list is
    selected).
    """
    if not isinstance(values, list) or not values:
        raise CanonicalizationError(
            f"rule_id={rule_id!r} {field_name} must be a non-empty list of non-empty strings"
        )
    seen: set[str] = set()
    for entry in values:
        if not isinstance(entry, str) or not entry:
            raise CanonicalizationError(
                f"rule_id={rule_id!r} {field_name} entry {entry!r} is not a non-empty string"
            )
        if entry in seen:
            raise CanonicalizationError(
                f"rule_id={rule_id!r} {field_name} contains duplicate entry {entry!r}"
            )
        seen.add(entry)
    return tuple(sorted(seen))


def _coerce_positive_int(value: Any, *, field_name: str, rule_id: str) -> int:
    """Coerce ``maximum_position_count`` to a strict positive ``int``.

    ``bool`` rejected (Python bool is a subclass of int but
    disallowed). Non-int / float / string rejected. Zero / negative
    rejected.
    """
    if isinstance(value, bool):
        raise CanonicalizationError(f"rule_id={rule_id!r} {field_name} bool is not an integer")
    if isinstance(value, int):
        coerced = value
    else:
        raise CanonicalizationError(
            f"rule_id={rule_id!r} {field_name} unsupported type "
            f"{type(value).__name__}; expected integer"
        )
    if coerced <= 0:
        raise CanonicalizationError(f"rule_id={rule_id!r} {field_name} must be > 0")
    return coerced


def _coerce_license_evidence(value: Any) -> Mapping[str, Any]:
    """Project a TASK-012 ``license_evidence`` to a canonical mapping.

    Per TASK-012 §7.2 the rule's ``license_evidence`` is one of four
    controlled forms (SPDX / public_domain / permission_evidence_pointer /
    project_internal_authority). TASK-022 ``license_evidence`` is a
    canonical JSON value; the simplest faithful projection is a
    mapping ``{form, value}`` carrying the classification + the raw
    token string for cross-document traceability.
    """
    if not isinstance(value, str) or not value:
        raise CanonicalizationError("license_evidence must be a non-empty string")
    return {"form": "spdx", "value": value}


# --- top-level adapter ----------------------------------------------------


def build_shell_bundle_rule_authority_snapshot(
    *,
    loaded_rule_pack: Mapping[str, Any],
    rule_id: str,
) -> ShellBundleGeometryRuleAuthoritySnapshot:
    """Construct a TASK-022 ``ShellBundleGeometryRuleAuthoritySnapshot``.

    Stage order follows Issue #147 Record 4 exactly:

    1. raw argument type validation;
    2. loaded-pack exact top-level field validation;
    3. manifest schema validation;
    4. manifest canonical-hash verification;
    5. manifest rule-reference integrity validation;
    6. explicit ``rule_id`` lexical validation;
    7. exact selected-rule lookup;
    8. selected-rule schema validation;
    9. selected-rule canonical-hash verification;
    10. selected-rule key/body identity and manifest-reference verification;
    11. approval-state validation;
    12. source-class, license and vendor-permission validation;
    13. provenance and supersedes-edge validation;
    14. TASK-022 ``rule_body`` exact-field/type/profile validation;
    15. snapshot projection, canonicalization and snapshot-hash construction;
    16. terminal slice-A ``verify_rule_authority`` verification.

    Within a single stage, every independent defect is accumulated;
    later dependent stages do not execute after their prerequisite
    stage blocks. The adapter never returns a partial snapshot.
    """
    # One dict carries the in-flight blockers and the per-identity stage
    # map. We keep blockers bucketed by stage so the final ordering can
    # collapse into the canonical composite key with stable ranks.
    stage_blockers: dict[int, list[MessageEntry]] = {}
    identity_to_stage: dict[int, int] = {}

    def stage(stage_rank: int, code: str, *args: Any, **kwargs: Any) -> MessageEntry:
        bucket = stage_blockers.setdefault(stage_rank, [])
        entry = _make_blocker(
            stage_rank,
            code,
            *args,
            identity_to_stage=identity_to_stage,
            **kwargs,
        )
        bucket.append(entry)
        return entry

    # Stage 1 — raw argument type validation.
    if not isinstance(loaded_rule_pack, Mapping):
        stage(
            STAGE_RAW_ARG,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RAW_TYPE_INVALID.value,
            details={"actual_type": type(loaded_rule_pack).__name__},
        )
    # Stage 1 (cont.) — rule_id raw type.
    if not isinstance(rule_id, str) or not rule_id:
        stage(
            STAGE_RAW_ARG,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RAW_TYPE_INVALID.value,
            field_path="rule_id",
            details={
                "actual_type": type(rule_id).__name__,
                "is_empty": isinstance(rule_id, str) and not rule_id,
            },
        )

    early_bl = _collect_blockers_by_stage(stage_blockers)
    if early_bl:
        raise AdapterFailure(early_bl, stage_by_identity=identity_to_stage)

    assert isinstance(loaded_rule_pack, Mapping)
    assert isinstance(rule_id, str) and rule_id

    # Stage 2 — loaded-pack exact top-level field validation.
    seen_keys = set(loaded_rule_pack.keys())
    missing_keys: list[str] = []
    for key in TASK012_LOADED_PACK_REQUIRED_KEYS:
        if key not in seen_keys:
            missing_keys.append(key)
    if missing_keys:
        stage(
            STAGE_PACK_SHAPE,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_UNKNOWN_FIELD.value,
            details={"missing_keys": sorted(missing_keys)},
        )
    extra_keys = sorted(seen_keys - set(TASK012_LOADED_PACK_REQUIRED_KEYS))
    if extra_keys:
        stage(
            STAGE_PACK_SHAPE,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_UNKNOWN_FIELD.value,
            details={"extra_keys": extra_keys},
        )
    if stage_blockers:
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(early_bl, stage_by_identity=identity_to_stage)

    manifest = loaded_rule_pack["manifest"]
    rules = loaded_rule_pack["rules"]
    provenance_edges = loaded_rule_pack["provenance_edges"]
    permission_evidence = loaded_rule_pack["permission_evidence"]

    if not isinstance(manifest, Mapping):
        stage(
            STAGE_PACK_SHAPE,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_MANIFEST_INVALID.value,
            details={"actual_type": type(manifest).__name__},
        )
    if not isinstance(rules, Mapping):
        stage(
            STAGE_PACK_SHAPE,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_UPSTREAM_OBJECT_INVALID.value,
            details={"actual_type": type(rules).__name__},
        )
    if not isinstance(provenance_edges, list):
        stage(
            STAGE_PACK_SHAPE,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_PROVENANCE_INVALID.value,
            details={"actual_type": type(provenance_edges).__name__},
        )
    if not isinstance(permission_evidence, Mapping):
        stage(
            STAGE_PACK_SHAPE,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_UPSTREAM_OBJECT_INVALID.value,
            details={"actual_type": type(permission_evidence).__name__},
        )
    if stage_blockers:
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(early_bl, stage_by_identity=identity_to_stage)

    assert isinstance(manifest, Mapping)
    assert isinstance(rules, Mapping)
    assert isinstance(provenance_edges, list)
    assert isinstance(permission_evidence, Mapping)

    # Stage 3 — manifest schema validation. Per Record 4 / Issue #147
    # we surface any TASK-012 schema failure with the dedicated
    # ``SBG_RULE_ADAPTER_MANIFEST_INVALID`` code so the caller can
    # distinguish schema-level defects from the higher-level structural
    # checks we run in stages 2 / 4 / 5.
    try:
        validate_manifest(dict(manifest))
    except Exception as exc:  # noqa: BLE001 - record all upstream errors
        stage(
            STAGE_MANIFEST_SCHEMA,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_MANIFEST_INVALID.value,
            details={"error_type": type(exc).__name__, "message": str(exc)},
        )
    manifest_required_field_missing: list[str] = sorted(
        set(TASK012_MANIFEST_REQUIRED_FIELDS) - set(manifest.keys())
    )
    if manifest_required_field_missing:
        stage(
            STAGE_MANIFEST_SCHEMA,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_MANIFEST_INVALID.value,
            details={"missing_fields": manifest_required_field_missing},
        )
    if stage_blockers:
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(early_bl, stage_by_identity=identity_to_stage)

    # Stage 4 — manifest canonical-hash verification.
    try:
        validate_manifest_canonical_hash(dict(manifest))
    except Exception as exc:  # noqa: BLE001
        stage(
            STAGE_MANIFEST_HASH,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_MANIFEST_HASH_MISMATCH.value,
            details={"error_type": type(exc).__name__, "message": str(exc)},
        )

    # Stage 5 — manifest rule-reference integrity validation.
    try:
        validate_manifest_only_references_approved_rules(
            dict(manifest), cast("dict[str, dict[str, Any]]", dict(rules))
        )
    except Exception as exc:  # noqa: BLE001
        stage(
            STAGE_MANIFEST_REFERENCES,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_MANIFEST_REFERENCE_INVALID.value,
            details={"error_type": type(exc).__name__, "message": str(exc)},
        )
    if stage_blockers:
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(early_bl, stage_by_identity=identity_to_stage)

    # Stage 6 — explicit ``rule_id`` lexical validation.
    if not rule_id or not isinstance(rule_id, str):
        stage(
            STAGE_RULE_ID_LEXICAL,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_ID_INVALID.value,
            field_path="rule_id",
            details={"rule_id": rule_id},
        )
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(early_bl, stage_by_identity=identity_to_stage)

    # Stage 7 — exact selected-rule lookup.
    if rule_id not in rules:
        stage(
            STAGE_RULE_LOOKUP,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_NOT_FOUND.value,
            details={"requested_rule_id": rule_id},
        )
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(early_bl, stage_by_identity=identity_to_stage)
    rule = rules[rule_id]
    if not isinstance(rule, Mapping):
        stage(
            STAGE_RULE_LOOKUP,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_INVALID.value,
            details={"actual_type": type(rule).__name__},
        )
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(early_bl, stage_by_identity=identity_to_stage)
    rule_dict: dict[str, Any] = dict(rule)

    # Stage 8 — selected-rule schema validation.
    try:
        validate_rule(rule_dict)
    except Exception as exc:  # noqa: BLE001
        stage(
            STAGE_RULE_SCHEMA,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_INVALID.value,
            details={"error_type": type(exc).__name__, "message": str(exc)},
        )

    # Stage 9 — selected-rule canonical-hash verification.
    try:
        validate_canonical_hash(rule_dict)
    except Exception as exc:  # noqa: BLE001
        stage(
            STAGE_RULE_HASH,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_HASH_MISMATCH.value,
            details={"error_type": type(exc).__name__, "message": str(exc)},
        )

    # Stage 10 — selected-rule key/body identity and manifest-reference verification.
    rule_internal_id = rule_dict.get("rule_id")
    if rule_internal_id != rule_id:
        stage(
            STAGE_RULE_IDENTITY,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_IDENTITY_MISMATCH.value,
            details={"key": rule_id, "rule_id": rule_internal_id},
        )
    # The manifest must list the selected rule_id exactly once.
    manifest_rule_list = manifest.get("rules")
    if not isinstance(manifest_rule_list, list) or manifest_rule_list.count(rule_id) != 1:
        stage(
            STAGE_RULE_IDENTITY,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_IDENTITY_MISMATCH.value,
            details={"manifest_rule_count": manifest_rule_list.count(rule_id)}
            if isinstance(manifest_rule_list, list)
            else {"manifest_rule_count": None},
        )

    # Stage 11 — approval-state validation. Spec mandates ``approved``.
    approval_status = rule_dict.get("approval_status")
    if approval_status != TASK012_APPROVED:
        stage(
            STAGE_RULE_APPROVAL,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_UNAPPROVED.value,
            details={"approval_status": approval_status},
        )
    if stage_blockers:
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(early_bl, stage_by_identity=identity_to_stage)

    # Stage 12 — source-class, license and vendor-permission validation.
    source_class_token = rule_dict.get("source_class")
    if source_class_token in RUNTIME_FORBIDDEN_SOURCE_CLASSES:
        stage(
            STAGE_SOURCE_CLASS_LICENSE,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_SOURCE_CLASS_RUNTIME_FORBIDDEN.value,
            details={"source_class": source_class_token},
        )
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(early_bl, stage_by_identity=identity_to_stage)

    # Vendor-scope check FIRST for VENDOR-source rules: Record 5 maps
    # missing scope tokens to the dedicated
    # ``SBG_RULE_ADAPTER_VENDOR_PERMISSION_SCOPE_INCOMPLETE`` code.
    # For non-VENDOR classes the helper is a no-op. The
    # ``operation="runtime_rulepack"`` token corresponds to the
    # ``runtime_rulepack`` operation in
    # ``hexagent.rule_packs.license_boundary.enforce_vendor_permission_scope``.
    if source_class_token == Task012SourceClass.VENDOR_PERMISSIONED.value:
        try:
            enforce_vendor_permission_scope(rule_dict, operation="runtime_rulepack")
        except Exception as exc:  # noqa: BLE001
            stage(
                STAGE_SOURCE_CLASS_LICENSE,
                RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_VENDOR_PERMISSION_SCOPE_INCOMPLETE.value,
                details={
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                    "operation": "runtime_rulepack",
                },
            )
            early_bl = _collect_blockers_by_stage(stage_blockers)
            raise AdapterFailure(  # noqa: B904 - upstream captured in details
                early_bl, stage_by_identity=identity_to_stage
            ) from None

    # Then generic license-boundary enforcement (also covers the
    # vendor-scope recorded-token requirement via the layered
    # ``enforce_vendor_permission_scope_full_recorded``).
    try:
        enforce_full_license_boundary(rule_dict)
    except Exception as exc:  # noqa: BLE001
        stage(
            STAGE_SOURCE_CLASS_LICENSE,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_LICENSE_BLOCKED.value,
            details={"error_type": type(exc).__name__, "message": str(exc)},
        )

    if stage_blockers:
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(early_bl, stage_by_identity=identity_to_stage)

    # Stage 13 — provenance and supersedes-edge validation. Defensive:
    # even if TASK-012 schema already enforces a non-empty
    # provenance list, the adapter performs an independent structural
    # check via the existing TASK-012 validators and accumulates
    # every edge-level defect.
    try:
        validate_provenance_edges(
            cast("dict[str, dict[str, Any]]", dict(rules)),
            list(provenance_edges),
        )
    except Exception as exc:  # noqa: BLE001
        stage(
            STAGE_PROVENANCE,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_PROVENANCE_INVALID.value,
            details={"error_type": type(exc).__name__, "message": str(exc)},
        )
    try:
        validate_supersedes_edges(
            cast("dict[str, dict[str, Any]]", dict(rules)),
            list(provenance_edges),
        )
    except Exception as exc:  # noqa: BLE001
        stage(
            STAGE_PROVENANCE,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_PROVENANCE_INVALID.value,
            details={"error_type": type(exc).__name__, "message": str(exc)},
        )
    if stage_blockers:
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(early_bl, stage_by_identity=identity_to_stage)

    # Stage 14 — TASK-022 ``rule_body`` exact-field/type/profile validation.
    rule_body = rule_dict.get("rule_body")
    if not isinstance(rule_body, Mapping):
        stage(
            STAGE_RULE_BODY,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_BODY_INVALID.value,
            details={"actual_type": type(rule_body).__name__},
        )
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(early_bl, stage_by_identity=identity_to_stage)
    rule_body_dict = cast("Mapping[str, Any]", rule_body)
    rule_body_keys = set(rule_body_dict.keys())
    missing_projection_fields = sorted(set(TASK022_RULE_BODY_PROJECTION_FIELDS) - rule_body_keys)
    if missing_projection_fields:
        stage(
            STAGE_RULE_BODY,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_BODY_INVALID.value,
            details={"missing_projection_fields": missing_projection_fields},
        )
    extra_projection_fields = sorted(rule_body_keys - set(TASK022_RULE_BODY_PROJECTION_FIELDS))
    if extra_projection_fields:
        stage(
            STAGE_RULE_BODY,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_BODY_INVALID.value,
            details={"unknown_projection_fields": extra_projection_fields},
        )

    # profile_id exact match — Issue #147 Record 3, the only field for
    # which the caller has no override authority.
    profile_id_value = rule_body_dict.get("profile_id")
    if profile_id_value != PROFILE_ID:
        stage(
            STAGE_RULE_BODY,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_PROFILE_UNSUPPORTED.value,
            details={"actual": profile_id_value, "expected": PROFILE_ID},
        )

    # allowed_shell_authority_modes.
    try:
        allowed_modes = _coerce_authority_modes(
            rule_body_dict.get("allowed_shell_authority_modes"),
            rule_id=rule_id,
        )
    except CanonicalizationError as exc:
        stage(
            STAGE_RULE_BODY,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_BODY_INVALID.value,
            field_path="rule_body.allowed_shell_authority_modes",
            details={"error_message": str(exc)},
        )
        allowed_modes = cast("tuple[ShellInsideDiameterAuthorityMode, ...]", ())

    # minimum_bundle_peripheral_allowance_m.
    try:
        minimum_allowance = _coerce_decimal_string(
            rule_body_dict.get("minimum_bundle_peripheral_allowance_m"),
            field_name="minimum_bundle_peripheral_allowance_m",
            rule_id=rule_id,
            allow_zero=True,
        )
    except CanonicalizationError as exc:
        stage(
            STAGE_RULE_BODY,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_BODY_INVALID.value,
            field_path="rule_body.minimum_bundle_peripheral_allowance_m",
            details={"error_message": str(exc)},
        )
        minimum_allowance = "0"

    # minimum_radial_clearance_m.
    try:
        minimum_clearance = _coerce_decimal_string(
            rule_body_dict.get("minimum_radial_clearance_m"),
            field_name="minimum_radial_clearance_m",
            rule_id=rule_id,
            allow_zero=True,
        )
    except CanonicalizationError as exc:
        stage(
            STAGE_RULE_BODY,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_BODY_INVALID.value,
            field_path="rule_body.minimum_radial_clearance_m",
            details={"error_message": str(exc)},
        )
        minimum_clearance = "0"

    # maximum_position_count.
    try:
        maximum_position_count = _coerce_positive_int(
            rule_body_dict.get("maximum_position_count"),
            field_name="maximum_position_count",
            rule_id=rule_id,
        )
    except CanonicalizationError as exc:
        stage(
            STAGE_RULE_BODY,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_BODY_INVALID.value,
            field_path="rule_body.maximum_position_count",
            details={"error_message": str(exc)},
        )
        maximum_position_count = 0

    # rule_body.evidence_refs.
    try:
        evidence_refs = _coerce_string_array(
            rule_body_dict.get("evidence_refs"),
            field_name="evidence_refs",
            rule_id=rule_id,
        )
    except CanonicalizationError as exc:
        stage(
            STAGE_RULE_BODY,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_RULE_BODY_INVALID.value,
            field_path="rule_body.evidence_refs",
            details={"error_message": str(exc)},
        )
        evidence_refs = ()

    # Selected-rule provenance edge ids (TASK-022 projection column).
    try:
        rule_provenance_edge_ids = _coerce_string_array(
            rule_dict.get("provenance_edges"),
            field_name="provenance_edges",
            rule_id=rule_id,
        )
    except CanonicalizationError as exc:
        stage(
            STAGE_RULE_BODY,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_PROVENANCE_INVALID.value,
            field_path="rule.provenance_edges",
            details={"error_message": str(exc)},
        )
        rule_provenance_edge_ids = ()

    if stage_blockers:
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(early_bl, stage_by_identity=identity_to_stage)

    # Stage 15 — snapshot projection, canonicalization, and snapshot-hash construction.
    try:
        license_evidence_mapping = _coerce_license_evidence(
            rule_dict.get("license_evidence"),
        )
        rule_pack_identity = RulePackIdentitySnapshot(
            rule_pack_id=str(manifest["rule_pack_id"]),
            rule_pack_version=str(manifest["rule_pack_version"]),
            rule_pack_canonical_hash=str(manifest["canonical_hash"]),
        )
        snapshot = ShellBundleGeometryRuleAuthoritySnapshot(
            schema_version=RULE_SNAPSHOT_SCHEMA_VERSION,
            profile_id=PROFILE_ID,
            authority_mode=RuleAuthorityMode.APPROVED_RULE_PACK,
            rule_id=str(rule_dict["rule_id"]),
            rule_version=str(rule_dict["rule_version"]),
            rule_artifact_canonical_hash=str(rule_dict["canonical_hash"]),
            source_class=str(rule_dict["source_class"]),
            license_evidence=license_evidence_mapping,
            approval_status=str(rule_dict["approval_status"]),
            provenance_edge_ids=rule_provenance_edge_ids,
            evidence_refs=evidence_refs,
            rule_pack_identity=rule_pack_identity,
            allowed_shell_authority_modes=allowed_modes,
            minimum_bundle_peripheral_allowance_m=minimum_allowance,
            minimum_radial_clearance_m=minimum_clearance,
            maximum_position_count=maximum_position_count,
            snapshot_hash="",  # placeholder, recomputed below
        )
        # Stage 15 (cont.) — recompute snapshot_hash over every field
        # except ``snapshot_hash`` itself. The exact byte-for-byte
        # equivalent of the slice-A ``_hash_without`` helper:
        # ``sha256_hex(dataclass_to_mapping(snapshot) without the
        # ``snapshot_hash`` key)``. Both helpers use the slice-A
        # public canonical surface only (``dataclass_to_mapping`` +
        # ``sha256_hex``); the inline call avoids exposing Slice A's
        # private hash helper while keeping the byte stream
        # identical.
        new_payload = dict(dataclass_to_mapping(snapshot))
        new_payload.pop("snapshot_hash", None)
        new_hash = sha256_hex(new_payload)
        object.__setattr__(snapshot, "snapshot_hash", new_hash)
    except AdapterFailure:
        raise
    except Exception as exc:  # noqa: BLE001
        stage(
            STAGE_SNAPSHOT_BUILD,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_SNAPSHOT_HASH_MISMATCH.value,
            details={"error_type": type(exc).__name__, "message": str(exc)},
        )
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(  # noqa: B904 - upstream captured in details
            early_bl, stage_by_identity=identity_to_stage
        ) from None

    # Stage 16 — terminal slice-A ``verify_rule_authority`` verification.
    # The defensive terminal check is mandatory per Issue #147 Record 4.
    from .authority import verify_rule_authority  # local import.

    try:
        verify_rule_authority(snapshot)
    except Exception as exc:  # noqa: BLE001
        stage(
            STAGE_SNAPSHOT_VERIFY,
            RulePackAdapterBlockerCode.SBG_RULE_ADAPTER_SNAPSHOT_VERIFICATION_FAILED.value,
            details={"error_type": type(exc).__name__, "message": str(exc)},
        )
        early_bl = _collect_blockers_by_stage(stage_blockers)
        raise AdapterFailure(  # noqa: B904 - upstream captured in details
            early_bl, stage_by_identity=identity_to_stage
        ) from None

    return snapshot


# --- module guard ----------------------------------------------------------

# Forbidden I/O tokens (filesystem / network / database / environment /
# clock / locale / registry) are enforced by the architecture test
# ``tests/exchangers/shell_tube/shell_bundle_geometry/
# test_rule_pack_adapter_architecture.py``. This file imports only
# stdlib + TASK-012 validators + the slice-A canonical/authority/model
# surface, all of which are pure.


__all__ = [
    "AdapterFailure",
    "RulePackAdapterBlockerCode",
    "TASK022_RULE_BODY_PROJECTION_FIELDS",
    "build_shell_bundle_rule_authority_snapshot",
]
# AdapterFailure + RulePackAdapterBlockerCode + the projection field
# tuple + the public operation. Closed-set name lists
# (RULE_PACK_ADAPTER_BLOCKER_CODES / DEFAULT_MESSAGE_KEY /
# DEFAULT_FIELD_PATH) are re-exported from ``adapter_blockers`` so
# they live in that module's ``__all__``.
