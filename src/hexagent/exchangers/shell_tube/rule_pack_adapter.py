"""TASK-020-S2 Approved Rule-Pack Adapter — real TASK-012 integration.

This module implements the S2 adapter that consumes a TASK-012 rule pack,
performs deterministic selection / deduplication / intersection, and on a
successful path returns a frozen ``ConfigurationRuleEvaluation`` value
object. On any non-success path the adapter raises ``BlockerError`` carrying
one of the ``STC_*`` codes from the §10.2 closed set.

This revision is the **real TASK-012 integration corrective round**. It
corrects the seven blocking-review defects identified in PR #135 review
comment ``4680303360`` against the post-Amendment-003 TASK-020 frozen
contract (§§12.3 / 12.4 / 12.5 / 12.8.1–12.8.5 / 12.9 / 19.F / 19.G /
20.B / 20.D). The adapter's public surface
(``ConfigurationRulePackAdapter.validate``, ``loaded_rule_pack_view_from_loader_dict``,
``rule_pack_validation_report_from_validate_dict``, ``__all__``) is
unchanged from the prior corrective commit. No TASK-012 / TASK-014 /
TASK-019 contract is mutated. No file other than this module is modified
by this revision.

Real TASK-012 integration
-------------------------

The adapter reads TASK-012 rule artifacts and the TASK-012 validation
report through their authoritative interfaces:

* ``hexagent.rule_packs.loader.load_rule_pack(root)`` — constructs the
  loader payload ``{manifest, rules, provenance_edges, permission_evidence}``.
* ``hexagent.rule_packs.validation.validate_rule_pack(root)`` — runs
  the full TASK-012 schema / license / canonical-hash / provenance /
  approval pipeline and returns the structured report.

The adapter does NOT carry its own JSON loader or its own canonical-hash
helper. All artifact contents come from real TASK-012 disk artifacts.

Read-source discipline (binding)
--------------------------------

Per the TASK-020 frozen contract §12.8 and the Round-2 corrective
authority, every TASK-020 predicate field is read from the
``rule_body`` mapping inside the TASK-012 rule artifact:

    profile_id
    rule_type
    constraint_id
    priority
    applies_to_authority_modes
    applies_to_construction_families  (NON-NORMALIZATION types only)
    input_value                        (CONSTRUCTION_FAMILY_NORMALIZATION)
    normalized_value                  (CONSTRUCTION_FAMILY_NORMALIZATION)
    shell_pass_count: {min_inclusive, max_inclusive}
    tube_pass_count:  {min_inclusive, max_inclusive}
    allowed_orientations
    component_slot, nullable, allowed_tokens
    blocked_combination: {front_head_token, shell_token, rear_head_token}
    evidence_refs

The TASK-012 directive-identity fields stay at the artifact top level
and are read directly from there:

    rule_id, rule_version, canonical_hash,
    source_class, license_evidence, approval_status,
    provenance_edges, rule_title, ...

The complete six-field §12.4 authority key is composed from BOTH sources:

    (rule_body.priority,
     rule_body.rule_type,
     rule_body.constraint_id,
     artifact.rule_id,
     artifact.rule_version,
     artifact.canonical_hash)

The TASK-020 predicate fields MUST NOT be re-bound to artifact top-level
keys, and the TASK-012 directive identity MUST NOT be moved into
``rule_body``. The contract record-keeping separates "projectinternal
rule identity" (TASK-012 directive layer) from "project-internal
predicate configuration" (TASK-020 rule_body).

View boundary discipline
------------------------

The view builders are explicitly shape-aligned to TASK-012's contracts:

* ``loaded_rule_pack_view_from_loader_dict`` ignores the input mapping's
  original keys entirely. The ``rules_view`` dict is keyed by the
  artifact's direct ``rule_id`` (``Mapping[str, Mapping]``), regardless
  of the input mapping's key set. A duplicate direct ``rule_id`` inside
  the loaded mapping is rejected.

* ``rule_pack_validation_report_from_validate_dict`` reads ``status``
  first. When ``status == "fail"`` the minimal shape ``{status, errors}``
  is accepted without requiring ``manifest`` or ``rule_count``. When
  ``status == "ok"`` both ``manifest`` (mapping) and ``rule_count``
  (``int``) are required. The adapter never invents fake identity.

Iteration discipline
--------------------

Every iteration over ``loaded_rule_pack.rules`` is by sorted
Unicode-code-point order on the ``rule_id`` key. No filesystem-order
tie-break, no manifest-array-order tie-break, no dict-insertion-order
tie-break, no glob / rglob / os.walk / recursive discovery.

Frozen-corrected semantics (contract alignment)
----------------------------------------------

§12.3 — Closed rule_type set:

    - COMPONENT_TOKEN_ALLOWLIST
    - CONSTRUCTION_FAMILY_NORMALIZATION
    - CONFIGURATION_COMBINATION_BLOCKLIST
    - PASS_COUNT_ALLOWED_RANGE
    - ORIENTATION_ALLOWLIST

§12.4 + §20.B — Complete six-field authority key. Equal keys silent-dedup;
identical ``(profile_id, rule_type, constraint_id)`` triples with
different complete keys emit ``STC_RULE_DUPLICATE_IDENTITY``.

§12.5 items 7 / 8 — empty ``applies_to_authority_modes`` or empty
``applies_to_construction_families`` (after normalization) emit
``STC_RULE_APPLICABILITY_UNRESOLVED``.

§12.8.1 — ``COMPONENT_TOKEN_ALLOWLIST`` payload reads frozen fields
``component_slot`` (closed = ``{front_head, shell, rear_head}``),
``nullable`` (boolean), ``allowed_tokens`` (list[str]).

§12.8.3 — ``CONSTRUCTION_FAMILY_NORMALIZATION`` does **not** carry an
``applies_to_construction_families`` field. Applicability is computed
from ``input_value``: the rule applies iff
``request.construction_family.value == rule.input_value`` AND
``request.authority_mode in rule.applies_to_authority_modes``.
A missing or empty ``input_value`` is a
``STC_RULE_TYPE_UNRECOGNIZED`` malformed-payload defect.

§12.8.4 — ``PASS_COUNT_ALLOWED_RANGE`` reads frozen fields
``shell_pass_count.min_inclusive`` / ``shell_pass_count.max_inclusive``
and ``tube_pass_count.min_inclusive`` / ``tube_pass_count.max_inclusive``.
A rule with ``min_inclusive > max_inclusive`` (on either axis) emits
``STC_RULE_APPLICABILITY_UNRESOLVED``. When the intersection over
all applicable rules is non-empty, the request's
``shell_pass_count`` and ``tube_pass_count`` are checked against the
intersection; if either falls outside the intersection, the adapter
emits ``STC_PASS_COUNT_INVALID``.

§12.8.5 — ``ORIENTATION_ALLOWLIST`` is evaluated as a closed-set
intersection across all applicable rules. When the intersection
is non-empty, the request's ``orientation`` is checked against the
intersection; an out-of-intersection orientation emits
``STC_ORIENTATION_INVALID``.

§12.5 item 6 — ``CONFIGURATION_COMBINATION_BLOCKLIST`` evaluates the
request's ``(front_head_token, shell_token, rear_head_token)`` triple
against each applicable rule's ``blocked_combination`` triple using the
frozen AND-across-fields + OR-within-field semantics: a per-field
array is a wildcard when empty (matches any value, including ``null``)
and an OR membership match when non-empty. The first applicable
matching rule emits ``STC_CONFIGURATION_COMBINATION_BLOCKED`` and the
adapter stops. Subsequent matches do not multiply the effect.

§12.9 — Required-constraint matrix. The matrix in §12.9 is the
**sole** source of required-rule truth. Missing a required class
emits ``STC_RULE_CONSTRAINT_MISSING`` and stops. The previously-
emitted-but-reserved ``STC_REQUIRED_RULE_MISSING`` code is **never**
emitted by this adapter; the two are not aliases.

§19.G + §20.C + §20.E — Reserved / historical codes that this
adapter MUST NOT emit:

    - STC_RULE_PACK_REQUIRED
    - STC_REQUIRED_RULE_MISSING
    - STC_RULE_UNAPPROVED
    - STC_RULE_CANONICAL_HASH_MISMATCH
    - STC_RULE_LICENSE_BLOCKED
    - STC_RULE_PROVENANCE_BLOCKED

Non-actions preserved (§§12.7 / 17 / 19.G / 20.C — binding):

    - No parsing of ``validation_report.errors[*].message``.
    - No re-running TASK-012 approval / canonical-hash / license /
      provenance verification.
    - No filesystem order / manifest-array order / dict-insertion
      order / unordered-iteration order / input-order surrogate as
      a tie-break.
    - No producing any engineering value, numeric coefficient,
      expected output, or standard quote.
    - No clock / network / environment / locale / unordered
      filesystem state.
    - No glob / rglob / os.walk / recursive directory discovery.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Final

from hexagent.exchangers.shell_tube.errors import (
    RESERVED_S2_BLOCKER_CODES,
    BlockerError,
)
from hexagent.exchangers.shell_tube.models import (
    CLOSED_RULE_TYPES,
    PROFILE_ID_TASK_020_CONFIGURATION_RULE_V1,
    TASK_020_VALIDATION_REPORT_OK,
    BlockerCode,
    ComponentTokens,
    ConfigurationRuleEvaluation,
    ConstructionFamily,
    EvaluatedRulePackAuthority,
    LoadedRulePackView,
    RulePackValidationReport,
    SelectedRuleAuthority,
    ShellAndTubeConfigurationRequest,
)

# ---------------------------------------------------------------------------
# Frozen constants
# ---------------------------------------------------------------------------

# §12.8.1 — closed component_slot enum used by COMPONENT_TOKEN_ALLOWLIST
_CLOSED_COMPONENT_SLOTS: Final[frozenset[str]] = frozenset({"front_head", "shell", "rear_head"})

# §12.3 / §12.5 item 6 — blocklist is optional, not part of §12.9 required matrix
_BLOCKLIST_RULE_TYPE: Final[str] = "CONFIGURATION_COMBINATION_BLOCKLIST"

# ---------------------------------------------------------------------------
# Adapter-internal utilities
# ---------------------------------------------------------------------------


def _assert_not_reserved(code: str) -> None:
    """Adapter-internal invariant: never raise a reserved code.

    Reserved / historical / un-emitted per §19.G + §20.C + §20.E.
    The set bound here is the ``RESERVED_S2_BLOCKER_CODES`` set
    defined in ``errors.py``, which is the authoritative runtime
    sentinel (not a duplicate string literal).
    """
    assert code not in RESERVED_S2_BLOCKER_CODES, (
        f"adapter attempted to raise reserved code {code!r}; "
        "reserved codes are reserved/un-emitted per §19.G + §20.C + §20.E"
    )


def _task020_rule_body(rule: Mapping[str, object]) -> Mapping[str, object]:
    """Return the TASK-020 predicate payload from inside the artifact.

    Per the Round-2 corrective authority, every TASK-020 predicate field
    (``profile_id``, ``rule_type``, ``constraint_id``, ``priority``,
    ``applies_to_authority_modes``, ``applies_to_construction_families``,
    rule-type-specific predicates and ``evidence_refs``) lives inside the
    TASK-012 rule artifact's ``rule_body`` mapping. Top-level
    counterfeit predicate fields are NOT honored — the adapter reads
    strictly from ``rule_body``.

    A rule without a mapping ``rule_body`` is a malformed
    TASK-020-payload defect and emits
    ``STC_RULE_TYPE_UNRECOGNIZED``.
    """
    body = rule.get("rule_body")
    if not isinstance(body, Mapping):
        raise BlockerError(
            str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
            f"rule {rule.get('rule_id')!r} missing rule_body mapping",
        )
    return body


def _manifest_identity(manifest: Mapping[str, object]) -> tuple[str, str, str]:
    """Read the three identity fields from a TASK-012 manifest mapping."""
    rid = manifest.get("rule_pack_id")
    rver = manifest.get("rule_pack_version")
    rhash = manifest.get("canonical_hash")
    if not (
        isinstance(rid, str)
        and isinstance(rver, str)
        and isinstance(rhash, str)
        and rid
        and rver
        and rhash
    ):
        return ("", "", "")
    return (rid, rver, rhash)


# ---------------------------------------------------------------------------
# §6.3.3 — cross-input consistency
# ---------------------------------------------------------------------------


def _check_cross_input_consistency(
    request: ShellAndTubeConfigurationRequest,
    loaded: LoadedRulePackView,
    report: RulePackValidationReport,
) -> None:
    """§6.3.3 + §7.2 — three identity checks raise report-mismatch.

    Only fires when ``status == "ok"``; on ``status == "fail"`` the report
    carries minimal identity (no manifest / rule_count), and the rule-pack
    pre-validation already short-circuits with ``STC_RULE_PACK_VALIDATION_FAILED``.

    Final-cleanup-round narrowing (binding): if the caller somehow
    managed to construct a ``status == 'ok'`` report without ``manifest``
    or ``rule_count`` (the dataclass guards forbid it, but defensive
    check anyway) the cross-input check fails closed with
    ``STC_RULE_PACK_VALIDATION_REPORT_MISMATCH``. ``None`` is rejected
    rather than coerced to ``{}`` / ``0``.
    """
    if report.manifest is None or report.rule_count is None:
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
            "status='ok' validation_report must carry manifest and rule_count",
        )

    req = request.requested_rule_pack_identity
    if req is None:
        raise BlockerError(
            str(BlockerCode.STC_REQUESTED_RULE_PACK_IDENTITY_MISSING),
            "APPROVED_RULE_PACK mode requires requested_rule_pack_identity",
        )

    rid_req = (req.rule_pack_id, req.rule_pack_version, req.rule_pack_canonical_hash)
    rid_loaded = (
        loaded.rule_pack_id,
        loaded.rule_pack_version,
        loaded.rule_pack_canonical_hash,
    )
    rid_report = (
        report.rule_pack_id,
        report.rule_pack_version,
        report.rule_pack_canonical_hash,
    )

    if rid_loaded != rid_report or rid_req != rid_loaded or rid_req != rid_report:
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
            "rule-pack identity disagreement between request / loaded pack / validation report",
        )

    if report.rule_count != loaded.rule_count or report.rule_count != len(loaded.rules):
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
            "rule_count mismatch between loaded pack and validation report",
        )


def _check_validation_report_boundary(report: RulePackValidationReport) -> None:
    """§7.1 — the adapter accepts only ``status == 'ok'`` reports.

    The TASK-020 adapter does **not** parse
    ``validation_report.errors[*].message`` and does **not** re-run any
    TASK-012 approval / hash / license / provenance verification
    (per §6.3.2 + §6.3.3 + §20.C).
    """
    if report.status != TASK_020_VALIDATION_REPORT_OK:
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_FAILED),
            "TASK-012 rule-pack validation report is not 'ok' "
            "(adapter does not parse errors[*].message)",
        )


# ---------------------------------------------------------------------------
# §12.4 / §20.B — complete six-field authority key (mixed source)
# ---------------------------------------------------------------------------


def _six_field_key(rule: Mapping[str, object]) -> tuple[object, ...]:
    """Build the complete §12.4 six-tuple key.

    The key is composed from TWO sources (Round-2 binding):

        * From ``rule_body``:
            - priority
            - rule_type
            - constraint_id
        * From artifact top-level (TASK-012 directive identity):
            - rule_id
            - rule_version
            - canonical_hash
    """
    body = _task020_rule_body(rule)
    priority = body.get("priority", 0)
    if not isinstance(priority, int):
        raise BlockerError(
            str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
            f"rule_body.priority is not an integer: {rule.get('rule_id')!r}",
        )
    rule_type = body.get("rule_type")
    constraint_id = body.get("constraint_id")
    rule_id = rule.get("rule_id")
    rule_version = rule.get("rule_version")
    rule_canonical_hash = rule.get("canonical_hash")
    if not all(
        isinstance(v, str) and v
        for v in (rule_type, constraint_id, rule_id, rule_version, rule_canonical_hash)
    ):
        raise BlockerError(
            str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
            f"rule has missing identity field(s): rule_id={rule_id!r}",
        )
    return (
        priority,
        rule_type,
        constraint_id,
        rule_id,
        rule_version,
        rule_canonical_hash,
    )


def _identity_triple(rule: Mapping[str, object]) -> tuple[str, str, str]:
    """§12.4 — ``(profile_id, rule_type, constraint_id)`` logical-identity triple.

    All three fields come from inside ``rule_body`` (Round-2 binding).
    """
    body = _task020_rule_body(rule)
    return (
        str(body.get("profile_id", "") or ""),
        str(body.get("rule_type", "") or ""),
        str(body.get("constraint_id", "") or ""),
    )


def _normalize_string_list(raw: object) -> list[str]:
    """Normalize a JSON-array-of-strings into the deduped ascending unicode form."""
    if not isinstance(raw, list):
        return []
    out: set[str] = set()
    for v in raw:
        if isinstance(v, str) and v:
            out.add(v)
    return sorted(out)


# ---------------------------------------------------------------------------
# §12.5 / §12.8 — type-specific applicability (read from rule_body)
# ---------------------------------------------------------------------------


def _is_normalization(rule: Mapping[str, object]) -> bool:
    body = _task020_rule_body(rule)
    return body.get("rule_type") == "CONSTRUCTION_FAMILY_NORMALIZATION"


def _rule_applies(
    rule: Mapping[str, object],
    request: ShellAndTubeConfigurationRequest,
) -> bool:
    """§12.5 + §12.8 — type-specific applicability predicate.

    All applicability fields are read from ``rule_body`` (Round-2 binding).

    Non-normalization rules: applies iff
    ``request.authority_mode in rule_body.applies_to_authority_modes`` AND
    ``request.construction_family.value in rule_body.applies_to_construction_families``.

    Normalization rules: applies iff
    ``request.authority_mode in rule_body.applies_to_authority_modes`` AND
    ``request.construction_family.value == rule_body.input_value``.

    A normalization rule does **not** carry
    ``rule_body.applies_to_construction_families`` per §12.8.3.
    """
    body = _task020_rule_body(rule)
    modes_raw = body.get("applies_to_authority_modes") or []
    modes = _normalize_string_list(modes_raw)
    if not modes:
        # §12.5 item 8 — caller raises STC_RULE_APPLICABILITY_UNRESOLVED.
        return False
    if request.authority_mode.value not in modes:
        return False

    if body.get("rule_type") == "CONSTRUCTION_FAMILY_NORMALIZATION":
        # §12.8.3 — normalization rules use input_value (NOT
        # applies_to_construction_families) to match the request's
        # construction family.
        iv = body.get("input_value")
        if not isinstance(iv, str) or not iv:
            return False
        return iv == request.construction_family.value

    fams_raw = body.get("applies_to_construction_families") or []
    fams = _normalize_string_list(fams_raw)
    if not fams:
        return False
    return request.construction_family.value in fams


# ---------------------------------------------------------------------------
# §7.3 + §12.5 — closed profile-id + applicability + selection
# ---------------------------------------------------------------------------


def _select_rules(
    rules: Iterable[Mapping[str, object]],
    request: ShellAndTubeConfigurationRequest,
) -> list[Mapping[str, object]]:
    """§12.2 / §12.3 / §12.5 — return all rules whose profile matches and which
    are applicable to the request.

    Rules whose ``rule_body.profile_id`` is **not** the frozen
    ``task020.configuration-rule.v1`` are silently ignored (no blocker).
    A rule with the TASK-020 ``profile_id`` and a ``rule_type`` outside
    the closed ``CLOSED_RULE_TYPES`` set emits
    ``STC_RULE_TYPE_UNRECOGNIZED`` and stops.
    A rule with the TASK-020 ``profile_id``, a closed ``rule_type``
    and an **empty** ``applies_to_authority_modes`` set emits
    ``STC_RULE_APPLICABILITY_UNRESOLVED`` and stops; the same is true
    for non-normalization rules with an empty
    ``applies_to_construction_families`` set (per §12.5 item 8).
    A normalization rule with a missing or empty ``input_value`` is a
    malformed-payload defect and emits ``STC_RULE_TYPE_UNRECOGNIZED``.
    """
    selected: list[Mapping[str, object]] = []
    for rule in rules:
        body = _task020_rule_body(rule)
        if body.get("profile_id") != PROFILE_ID_TASK_020_CONFIGURATION_RULE_V1:
            # §12.2 — silent skip on cross-profile rule.
            continue

        rule_type = body.get("rule_type")
        if not isinstance(rule_type, str) or rule_type not in CLOSED_RULE_TYPES:
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"rule_type {rule_type!r} not in closed rule-type set "
                f"for rule_id={rule.get('rule_id')!r}",
            )

        # §12.5 item 8 — empty applicability set → UNRESOLVED.
        modes_raw = body.get("applies_to_authority_modes") or []
        if not isinstance(modes_raw, list) or not _normalize_string_list(modes_raw):
            raise BlockerError(
                str(BlockerCode.STC_RULE_APPLICABILITY_UNRESOLVED),
                f"empty applies_to_authority_modes for rule_id={rule.get('rule_id')!r}",
            )

        if rule_type != "CONSTRUCTION_FAMILY_NORMALIZATION":
            fams_raw = body.get("applies_to_construction_families") or []
            if not isinstance(fams_raw, list) or not _normalize_string_list(fams_raw):
                raise BlockerError(
                    str(BlockerCode.STC_RULE_APPLICABILITY_UNRESOLVED),
                    f"empty applies_to_construction_families for rule_id={rule.get('rule_id')!r}",
                )

        if rule_type == "CONSTRUCTION_FAMILY_NORMALIZATION":
            iv = body.get("input_value")
            if not isinstance(iv, str) or not iv:
                raise BlockerError(
                    str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                    f"CONSTRUCTION_FAMILY_NORMALIZATION rule "
                    f"{rule.get('rule_id')!r} has empty or missing input_value",
                )

        if _rule_applies(rule, request):
            selected.append(rule)
        # Non-applicable rules are silently ignored (no blocker); the
        # adapter does not emit a "rule does not apply" blocker.
    return selected


# ---------------------------------------------------------------------------
# §12.4 + §12.5 item 1 + §20.B — silent dedup + divergent-identity blocker
# ---------------------------------------------------------------------------


def _dedup_rules_by_six_field_key(
    selected: list[Mapping[str, object]],
) -> list[Mapping[str, object]]:
    """§12.4 / §12.5 item 1 / §20.B — silent dedup + divergent-identity blocker.

    - Equal six-field keys → silent dedup (keep one canonical copy).
    - Same ``(profile_id, rule_type, constraint_id)`` triple with
      different six-field values on any field → emit
      ``STC_RULE_DUPLICATE_IDENTITY`` and stop.
    - The retained canonical copy is the lexically smallest rule
      under the six-field key (tuple ordering = ascending
      lexicographic). This satisfies the §12.4 deterministic
      selection without filesystem / manifest-array / dict-insertion
      / unordered-iteration order tie-break.
    """
    by_full_key: dict[tuple[object, ...], list[Mapping[str, object]]] = {}
    by_identity: dict[tuple[str, str, str], list[tuple[object, ...]]] = {}

    for rule in selected:
        sk = _six_field_key(rule)
        bucket = by_full_key.setdefault(sk, [])
        if not bucket:
            bucket.append(rule)
        ident = _identity_triple(rule)
        by_identity.setdefault(ident, []).append(sk)

    for sk_list in by_identity.values():
        if len(sk_list) > 1:
            unique_keys = set(sk_list)
            if len(unique_keys) > 1:
                raise BlockerError(
                    str(BlockerCode.STC_RULE_DUPLICATE_IDENTITY),
                    "two rules share (profile_id, rule_type, "
                    "constraint_id) but differ in priority / "
                    "rule_id / rule_version / rule_artifact_canonical_hash",
                )

    return [by_full_key[sk][0] for sk in sorted(by_full_key.keys())]


# ---------------------------------------------------------------------------
# §7.6 / §12.5 item 2 / §12.8.3 — normalization
# ---------------------------------------------------------------------------


def _evaluate_normalization(
    selected: list[Mapping[str, object]],
    requested_construction_family: ConstructionFamily,
) -> ConstructionFamily:
    """§7.6 / §12.5 item 2 / §12.8.3 — apply CONSTRUCTION_FAMILY_NORMALIZATION.

    All normalization fields (``input_value`` / ``normalized_value``)
    are read from ``rule_body``. Empty selection →
    ``STC_RULE_CONSTRAINT_MISSING``. Multiple applicable rules with
    differing ``normalized_value`` → ``STC_RULE_NORMALIZATION_CONFLICT``.
    """
    applicable = [
        r
        for r in selected
        if _task020_rule_body(r).get("rule_type") == "CONSTRUCTION_FAMILY_NORMALIZATION"
    ]
    if not applicable:
        raise BlockerError(
            str(BlockerCode.STC_RULE_CONSTRAINT_MISSING),
            "no CONSTRUCTION_FAMILY_NORMALIZATION rule applies",
        )
    normalized_values: set[str] = set()
    for r in applicable:
        nv = _task020_rule_body(r).get("normalized_value")
        if not isinstance(nv, str) or not nv:
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"CONSTRUCTION_FAMILY_NORMALIZATION rule "
                f"{r.get('rule_id')!r} has empty normalized_value",
            )
        normalized_values.add(nv)
    if len(normalized_values) > 1:
        raise BlockerError(
            str(BlockerCode.STC_RULE_NORMALIZATION_CONFLICT),
            "multiple CONSTRUCTION_FAMILY_NORMALIZATION rules disagree",
        )

    only_nv = next(iter(normalized_values))
    try:
        return ConstructionFamily(only_nv)
    except ValueError as exc:
        raise BlockerError(
            str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
            f"CONSTRUCTION_FAMILY_NORMALIZATION produced out-of-domain "
            f"value {only_nv!r} (request: {requested_construction_family.value!r})",
        ) from exc


# ---------------------------------------------------------------------------
# §12.5 item 3 / §12.8.4 — pass-count range intersection + request predicate
# ---------------------------------------------------------------------------


def _evaluate_pass_count_range(
    selected: list[Mapping[str, object]],
    request: ShellAndTubeConfigurationRequest,
) -> None:
    """§7.7 + §12.5 item 3 + §12.8.4 — PASS_COUNT_ALLOWED_RANGE evaluation.

    Frozen payload fields per §12.8.4 (read from ``rule_body``):

        shell_pass_count: {min_inclusive, max_inclusive}
        tube_pass_count:  {min_inclusive, max_inclusive}

    Reads frozen names ``shell_pass_count.min_inclusive`` /
    ``shell_pass_count.max_inclusive`` and the equivalent
    ``tube_pass_count`` mapping — never the legacy
    ``shell_pass_range.min``/``max`` / ``tube_pass_range.min``/``max``
    naming.

    A rule with ``min_inclusive > max_inclusive`` on either axis is
    malformed and emits ``STC_RULE_APPLICABILITY_UNRESOLVED``.

    After intersecting the inclusive ranges across all applicable rules,
    the request's ``shell_pass_count`` and ``tube_pass_count`` are
    checked against the intersection; if either falls outside the
    intersected range, the adapter emits ``STC_PASS_COUNT_INVALID``.
    Empty selection → ``STC_RULE_CONSTRAINT_MISSING``.
    Empty intersection → ``STC_RULE_RANGE_INTERSECTION_EMPTY``.
    """
    applicable = [
        r for r in selected if _task020_rule_body(r).get("rule_type") == "PASS_COUNT_ALLOWED_RANGE"
    ]
    if not applicable:
        raise BlockerError(
            str(BlockerCode.STC_RULE_CONSTRAINT_MISSING),
            "no PASS_COUNT_ALLOWED_RANGE rule applies",
        )

    shell_mins: list[int] = []
    shell_maxs: list[int] = []
    tube_mins: list[int] = []
    tube_maxs: list[int] = []

    for r in applicable:
        body = _task020_rule_body(r)
        spc = body.get("shell_pass_count")
        tpc = body.get("tube_pass_count")
        if not (isinstance(spc, Mapping) and isinstance(tpc, Mapping)):
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"PASS_COUNT_ALLOWED_RANGE rule {r.get('rule_id')!r} has malformed payload",
            )
        s_min = spc.get("min_inclusive")
        s_max = spc.get("max_inclusive")
        t_min = tpc.get("min_inclusive")
        t_max = tpc.get("max_inclusive")
        if not all(
            isinstance(v, int) and not isinstance(v, bool) for v in (s_min, s_max, t_min, t_max)
        ):
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                "PASS_COUNT_ALLOWED_RANGE range bounds must be integers",
            )
        s_min_i: int = s_min  # type: ignore[assignment]
        s_max_i: int = s_max  # type: ignore[assignment]
        t_min_i: int = t_min  # type: ignore[assignment]
        t_max_i: int = t_max  # type: ignore[assignment]
        # §12.8.4 — min_inclusive > max_inclusive is malformed.
        if s_min_i > s_max_i or t_min_i > t_max_i:
            raise BlockerError(
                str(BlockerCode.STC_RULE_APPLICABILITY_UNRESOLVED),
                f"PASS_COUNT_ALLOWED_RANGE rule {r.get('rule_id')!r} has "
                "min_inclusive > max_inclusive",
            )
        shell_mins.append(s_min_i)
        shell_maxs.append(s_max_i)
        tube_mins.append(t_min_i)
        tube_maxs.append(t_max_i)

    # §12.5 item 3 — inclusive intersection on each axis.
    shell_min = max(shell_mins)
    shell_max = min(shell_maxs)
    tube_min = max(tube_mins)
    tube_max = min(tube_maxs)
    if shell_min > shell_max or tube_min > tube_max:
        raise BlockerError(
            str(BlockerCode.STC_RULE_RANGE_INTERSECTION_EMPTY),
            "PASS_COUNT_ALLOWED_RANGE intersection is empty on at least one axis",
        )

    # §12.8.4 — request-value predicate.
    if not (shell_min <= request.shell_pass_count <= shell_max) or not (
        tube_min <= request.tube_pass_count <= tube_max
    ):
        raise BlockerError(
            str(BlockerCode.STC_PASS_COUNT_INVALID),
            f"request pass counts ({request.shell_pass_count}, "
            f"{request.tube_pass_count}) outside the rule-pack "
            f"intersected range "
            f"shell=[{shell_min}, {shell_max}] tube=[{tube_min}, {tube_max}]",
        )


# ---------------------------------------------------------------------------
# §12.5 item 4 / §12.8.5 — orientation allowlist + request predicate
# ---------------------------------------------------------------------------


def _evaluate_orientation_allowlist(
    selected: list[Mapping[str, object]],
    request: ShellAndTubeConfigurationRequest,
) -> None:
    """§7.7 + §12.5 item 4 + §12.8.5 — ORIENTATION_ALLOWLIST evaluation.

    Frozen payload field per §12.8.5 (read from ``rule_body``):
    ``allowed_orientations: list[str]``.
    """
    applicable = [
        r for r in selected if _task020_rule_body(r).get("rule_type") == "ORIENTATION_ALLOWLIST"
    ]
    if not applicable:
        raise BlockerError(
            str(BlockerCode.STC_RULE_CONSTRAINT_MISSING),
            "no ORIENTATION_ALLOWLIST rule applies",
        )

    allowed_sets: list[frozenset[str]] = []
    for r in applicable:
        body = _task020_rule_body(r)
        ao = body.get("allowed_orientations")
        if not isinstance(ao, list):
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"ORIENTATION_ALLOWLIST rule {r.get('rule_id')!r} "
                "has malformed allowed_orientations",
            )
        ao_norm = _normalize_string_list(ao)
        if not ao_norm:
            # §12.5 item 8 — empty allowed_orientations is malformed.
            raise BlockerError(
                str(BlockerCode.STC_RULE_APPLICABILITY_UNRESOLVED),
                f"ORIENTATION_ALLOWLIST rule {r.get('rule_id')!r} has empty allowed_orientations",
            )
        allowed_sets.append(frozenset(ao_norm))

    intersected: set[str] = (
        set.intersection(*[set(s) for s in allowed_sets]) if allowed_sets else set()
    )
    if not intersected:
        raise BlockerError(
            str(BlockerCode.STC_RULE_ORIENTATION_INTERSECTION_EMPTY),
            "ORIENTATION_ALLOWLIST intersection is empty",
        )

    # §12.8.5 — request-value predicate: the request orientation
    # must lie inside the closed intersection.
    request_orientation = request.orientation.value
    if request_orientation not in intersected:
        raise BlockerError(
            str(BlockerCode.STC_ORIENTATION_INVALID),
            f"request orientation {request_orientation!r} is outside the "
            f"intersected orientation allowlist {sorted(intersected)!r}",
        )


# ---------------------------------------------------------------------------
# §12.5 item 5 / §12.8.1 — component token allowlist + request predicate
# ---------------------------------------------------------------------------


def _slot_token(
    slot: str,
    tokens: ComponentTokens,
) -> str | None:
    if slot == "front_head":
        return tokens.front_head
    if slot == "shell":
        return tokens.shell
    if slot == "rear_head":
        return tokens.rear_head
    raise BlockerError(
        str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
        f"unknown component slot {slot!r}",
    )


def _evaluate_component_token_allowlist(
    selected: list[Mapping[str, object]],
    request: ShellAndTubeConfigurationRequest,
) -> None:
    """§7.7 + §12.5 item 5 + §12.8.1 / §12.9 — COMPONENT_TOKEN_ALLOWLIST.

    Frozen payload fields per §12.8.1 (read from ``rule_body``):

        component_slot: closed ``{front_head, shell, rear_head}``
        nullable: bool
        allowed_tokens: list[str]

    Per §12.5 item 5 + §12.8.1 + §12.9 the frozen behavior is:

    - For each required slot in ``{front_head, shell, rear_head}``,
      the intersected ``allowed_tokens`` set across all applicable
      rules for that slot is computed. Empty selection per slot emits
      ``STC_RULE_CONSTRAINT_MISSING``. Empty intersection per slot
      emits ``STC_RULE_TOKEN_INTERSECTION_EMPTY``.
    - The request's token for a slot is then evaluated against the
      intersected set:
        - token is null AND every applicable rule for the slot
          declares ``nullable = true`` → pass;
        - token is null AND any applicable rule declares
          ``nullable = false`` → ``STC_TOKEN_UNSUPPORTED_BY_RULE_PACK``;
        - token is non-null AND token is in the intersected set → pass;
        - token is non-null AND token is not in the intersected set
          → ``STC_TOKEN_UNSUPPORTED_BY_RULE_PACK``.
    - A rule with empty ``allowed_tokens`` array is a malformed
      payload and emits ``STC_RULE_APPLICABILITY_UNRESOLVED``.
    """
    slot_to_set: dict[str, set[str]] = {}
    slot_to_nullable_required: dict[str, bool] = {}

    for r in selected:
        body = _task020_rule_body(r)
        if body.get("rule_type") != "COMPONENT_TOKEN_ALLOWLIST":
            continue
        slot = body.get("component_slot")
        if not isinstance(slot, str) or slot not in _CLOSED_COMPONENT_SLOTS:
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"COMPONENT_TOKEN_ALLOWLIST rule {r.get('rule_id')!r} has "
                "unknown or malformed component_slot",
            )
        toks_raw = body.get("allowed_tokens")
        if not isinstance(toks_raw, list):
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"COMPONENT_TOKEN_ALLOWLIST rule {r.get('rule_id')!r} has malformed allowed_tokens",
            )
        toks = _normalize_string_list(toks_raw)
        if not toks:
            raise BlockerError(
                str(BlockerCode.STC_RULE_APPLICABILITY_UNRESOLVED),
                f"COMPONENT_TOKEN_ALLOWLIST rule {r.get('rule_id')!r} has empty allowed_tokens",
            )
        # §12.8.1 — ``nullable`` is a required boolean field on every
        # COMPONENT_TOKEN_ALLOWLIST rule. A missing field defaulting
        # to ``False`` keeps the conservative fail-closed behavior.
        nullable = body.get("nullable", False)
        if not isinstance(nullable, bool):
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"COMPONENT_TOKEN_ALLOWLIST rule {r.get('rule_id')!r} has non-boolean nullable",
            )

        current = slot_to_set.setdefault(slot, set(toks))
        slot_to_set[slot] = current & set(toks)

        # Track whether every applicable rule for the slot declares
        # ``nullable = true``; if any rule says ``nullable = false``
        # the slot is required to be non-null.
        slot_required = slot_to_nullable_required.get(slot, True)
        slot_to_nullable_required[slot] = slot_required and nullable

    for required_slot in sorted(_CLOSED_COMPONENT_SLOTS):
        if required_slot not in slot_to_set:
            raise BlockerError(
                str(BlockerCode.STC_RULE_CONSTRAINT_MISSING),
                f"missing COMPONENT_TOKEN_ALLOWLIST rule for slot {required_slot!r}",
            )
        intersected = slot_to_set[required_slot]
        if not intersected:
            raise BlockerError(
                str(BlockerCode.STC_RULE_TOKEN_INTERSECTION_EMPTY),
                f"COMPONENT_TOKEN_ALLOWLIST intersection is empty for slot {required_slot!r}",
            )

        request_token = _slot_token(required_slot, request.component_tokens)
        all_nullable = slot_to_nullable_required.get(required_slot, False)
        if request_token is None:
            if not all_nullable:
                raise BlockerError(
                    str(BlockerCode.STC_TOKEN_UNSUPPORTED_BY_RULE_PACK),
                    f"component slot {required_slot!r} is null but "
                    "rule pack does not declare nullable=true",
                )
            continue
        if request_token not in intersected:
            raise BlockerError(
                str(BlockerCode.STC_TOKEN_UNSUPPORTED_BY_RULE_PACK),
                f"component slot {required_slot!r} token {request_token!r} "
                "is not in the intersected allowlist",
            )


# ---------------------------------------------------------------------------
# §12.5 item 6 / §12.8.2 — combination blocklist
# ---------------------------------------------------------------------------


def _field_matches(
    field_value: str | None,
    blocked_values: list[str],
) -> bool:
    """§12.8.2 — per-field membership.

    Empty ``blocked_values`` array → wildcard match (matches any value,
    including ``None``). Non-empty array → OR-within-field membership.
    """
    if not blocked_values:
        return True
    return field_value in blocked_values


def _evaluate_blocklist(
    selected: list[Mapping[str, object]],
    request: ShellAndTubeConfigurationRequest,
) -> None:
    """§12.5 item 6 + §12.8.2 — CONFIGURATION_COMBINATION_BLOCKLIST.

    Frozen payload field per §12.8.2 (read from ``rule_body``):

        blocked_combination: {
            front_head_token: list[str],
            shell_token: list[str],
            rear_head_token: list[str],
        }

    Match semantics — AND across the three fields, OR within each
    field:

        request matches a rule iff
            _field_matches(request.front_head_token, rule.front_head_token) AND
            _field_matches(request.shell_token,        rule.shell_token) AND
            _field_matches(request.rear_head_token,    rule.rear_head_token).

    Per-field array semantics:

        - non-empty array → OR-within-field (request token must be one
          of the listed values);
        - empty array → wildcard (matches any value of the field,
          including ``null``).

    The first applicable matching rule emits exactly
    ``STC_CONFIGURATION_COMBINATION_BLOCKED`` and the adapter stops.
    """
    applicable_rules = [
        r for r in selected if _task020_rule_body(r).get("rule_type") == _BLOCKLIST_RULE_TYPE
    ]
    # §12.9 — blocklist is not part of the required-constraint matrix;
    # zero applicable rules means no exclusion to apply.
    if not applicable_rules:
        return

    tokens = request.component_tokens
    front = tokens.front_head
    shell = tokens.shell
    rear = tokens.rear_head

    for r in applicable_rules:
        body = _task020_rule_body(r)
        bc = body.get("blocked_combination")
        if not isinstance(bc, Mapping):
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"CONFIGURATION_COMBINATION_BLOCKLIST rule "
                f"{r.get('rule_id')!r} has malformed blocked_combination",
            )
        front_l = bc.get("front_head_token") or []
        shell_l = bc.get("shell_token") or []
        rear_l = bc.get("rear_head_token") or []
        if not (
            isinstance(front_l, list) and isinstance(shell_l, list) and isinstance(rear_l, list)
        ):
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"CONFIGURATION_COMBINATION_BLOCKLIST rule "
                f"{r.get('rule_id')!r} has non-list blocked_combination fields",
            )
        if not _field_matches(front, list(front_l)):
            continue
        if not _field_matches(shell, list(shell_l)):
            continue
        if not _field_matches(rear, list(rear_l)):
            continue
        # All three fields matched → first-match semantics emit the
        # blocker; subsequent matches are not evaluated.
        raise BlockerError(
            str(BlockerCode.STC_CONFIGURATION_COMBINATION_BLOCKED),
            f"configuration combination blocked by rule_id={r.get('rule_id')!r}",
        )


# ---------------------------------------------------------------------------
# §7.9 — selected rule authorities
# ---------------------------------------------------------------------------


def _build_selected_rule_authorities(
    deduped_rules: list[Mapping[str, object]],
) -> tuple[SelectedRuleAuthority, ...]:
    """§6.3.5.1 + §7.9 + §12.4 — build the canonical
    ``selected_rule_authorities`` tuple.

    Each entry carries the 8 §6.3.5.1 fields. The TASK-012 directive
    identity fields (``rule_id``, ``rule_version``, ``canonical_hash``,
    ``source_class``, ``license_evidence``, ``approval_status``,
    ``provenance_edges``) are read directly from the artifact top level
    (Round-2 binding). The TASK-020 predicate body is not stamped into
    the SelectedRuleAuthority — the rule body lives inside the
    §6.3.5 rule-payload context, not in the per-rule identity record.

    ``provenance_edge_ids`` and ``evidence_refs`` are sorted in ascending
    Unicode-code-point order and deduplicated. The 6-field §12.4 sort
    key is the canonical ordering of the selected rules (already sorted
    in ``_dedup_rules_by_six_field_key``).
    """
    out: list[SelectedRuleAuthority] = []
    for rule in deduped_rules:
        # provenance_edges come from the TASK-012 directive layer.
        pe_raw = rule.get("provenance_edges") or []
        # evidence_refs come from the TASK-020 rule_body.
        body = _task020_rule_body(rule)
        ev_raw = body.get("evidence_refs") or []
        if not isinstance(pe_raw, list) or not isinstance(ev_raw, list):
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"rule {rule.get('rule_id')!r} provenance_edges / evidence_refs are not lists",
            )
        pe_sorted = sorted({str(x) for x in pe_raw if isinstance(x, str) and x})
        ev_sorted = sorted({str(x) for x in ev_raw if isinstance(x, str) and x})

        out.append(
            SelectedRuleAuthority(
                rule_id=str(rule["rule_id"]),
                rule_version=str(rule["rule_version"]),
                rule_artifact_canonical_hash=str(rule["canonical_hash"]),
                source_class=str(rule.get("source_class", "")),
                license_evidence=rule.get("license_evidence"),
                approval_status=str(rule.get("approval_status", "")),
                provenance_edge_ids=tuple(pe_sorted),
                evidence_refs=tuple(ev_sorted),
            )
        )
    return tuple(out)


# ---------------------------------------------------------------------------
# §12.1 — adapter entry point
# ---------------------------------------------------------------------------


class ConfigurationRulePackAdapter:
    """§12.1 / §19.E — frozen public entry point for the S2 adapter.

    The class owns one static method, ``validate``. The signature is
    preserved exactly per §19.E so that callers can chain it from
    ``validate_request``. The successful path returns
    ``ConfigurationRuleEvaluation``; any non-success path raises
    ``BlockerError`` carrying one closed ``STC_*`` code from the §10.2
    closed set.
    """

    @staticmethod
    def validate(
        request: ShellAndTubeConfigurationRequest,
        loaded_rule_pack: LoadedRulePackView,
        validation_report: RulePackValidationReport,
    ) -> ConfigurationRuleEvaluation:
        """§7 / §12 — full S2 evaluation pipeline.

        Raises ``BlockerError`` on any non-success path. Returns
        ``ConfigurationRuleEvaluation`` on the happy path.

        Pipeline order (binding):

        1. §7.1: ``validation_report.status == 'ok'``
           → else ``STC_RULE_PACK_VALIDATION_FAILED``.
        2. §7.2: cross-input consistency check
           → else ``STC_RULE_PACK_VALIDATION_REPORT_MISMATCH``.
        3. §12.2 / §12.3 / §12.5 item 8 / §12.8.3: closed profile-id +
           closed rule_type + type-specific applicability filter
           → else ``STC_RULE_TYPE_UNRECOGNIZED`` /
           ``STC_RULE_APPLICABILITY_UNRESOLVED``.
        4. §12.4 / §20.B: silent dedup + divergent-identity blocker
           → else ``STC_RULE_DUPLICATE_IDENTITY``.
        5. §7.6 / §12.5 item 2 / §12.8.3: normalization
           → else ``STC_RULE_NORMALIZATION_CONFLICT`` /
           ``STC_RULE_CONSTRAINT_MISSING``.
        6. §7.7 / §12.5 item 3 / §12.8.4: pass-count range
           → else ``STC_RULE_CONSTRAINT_MISSING`` /
           ``STC_RULE_RANGE_INTERSECTION_EMPTY`` /
           ``STC_PASS_COUNT_INVALID``.
        7. §7.7 / §12.5 item 4 / §12.8.5: orientation allowlist
           → else ``STC_RULE_CONSTRAINT_MISSING`` /
           ``STC_RULE_ORIENTATION_INTERSECTION_EMPTY`` /
           ``STC_ORIENTATION_INVALID``.
        8. §7.7 / §12.5 item 5 / §12.8.1 / §12.9: component-token
           allowlist (front / shell / rear) + nullable semantics
           → else ``STC_RULE_CONSTRAINT_MISSING`` /
           ``STC_RULE_TOKEN_INTERSECTION_EMPTY`` /
           ``STC_TOKEN_UNSUPPORTED_BY_RULE_PACK``.
        9. §12.5 item 6 / §12.8.2: blocklist application
           → else ``STC_CONFIGURATION_COMBINATION_BLOCKED``.
        10. §7.9: build canonical authority
            → return ``ConfigurationRuleEvaluation``.
        """
        # §7.1 — validation_report boundary.
        _check_validation_report_boundary(validation_report)
        # §7.2 — cross-input consistency.
        _check_cross_input_consistency(request, loaded_rule_pack, validation_report)

        # Iteration discipline: ascending Unicode-code-point order on
        # the rule_id key. Never use dict-insertion order, manifest-array
        # order, or filesystem order as a tie-break.
        ordered_rule_ids = sorted(loaded_rule_pack.rules.keys())
        ordered_rules = [loaded_rule_pack.rules[k] for k in ordered_rule_ids]

        # §12.2 / §12.3 / §12.5 item 8 / §12.8 — applicability.
        applicable = _select_rules(rules=ordered_rules, request=request)

        # §12.4 / §12.5 item 1 / §20.B — silent dedup + divergent-identity.
        deduped = _dedup_rules_by_six_field_key(applicable)

        # §7.6 / §12.5 item 2 / §12.8.3 — normalization.
        normalized_family = _evaluate_normalization(deduped, request.construction_family)

        # §7.7 / §12.5 items 3 / §12.8.4 — pass-count range.
        _evaluate_pass_count_range(deduped, request)
        # §7.7 / §12.5 items 4 / §12.8.5 — orientation allowlist.
        _evaluate_orientation_allowlist(deduped, request)
        # §7.7 / §12.5 item 5 / §12.8.1 / §12.9 — component-token allowlist.
        _evaluate_component_token_allowlist(deduped, request)
        # §12.5 item 6 / §12.8.2 — blocklist application.
        _evaluate_blocklist(deduped, request)

        # §7.9 — build canonical authority.
        selected_authorities = _build_selected_rule_authorities(deduped)
        era = EvaluatedRulePackAuthority(
            rule_pack_id=loaded_rule_pack.rule_pack_id,
            rule_pack_version=loaded_rule_pack.rule_pack_version,
            rule_pack_canonical_hash=loaded_rule_pack.rule_pack_canonical_hash,
            validation_status=validation_report.status,
            selected_rule_authorities=selected_authorities,
        )
        return ConfigurationRuleEvaluation(
            normalized_construction_family=normalized_family,
            evaluated_rule_pack_authority=era,
        )


# ---------------------------------------------------------------------------
# Phase A: helper loaders that build a LoadedRulePackView /
# RulePackValidationReport from TASK-012 plain dicts.
# ---------------------------------------------------------------------------


def loaded_rule_pack_view_from_loader_dict(
    loader_result: Mapping[str, object],
) -> LoadedRulePackView:
    """Adapter helper — wrap a TASK-012 ``load_rule_pack`` dict result.

    Round-2 re-keying discipline (binding):

    The input dict's original ``rules`` mapping is REJECTED as authority.
    The output ``rules_view`` dict is keyed by each rule artifact's
    direct ``rule_id`` (the artifact top-level ``rule_id`` string), not
    by the input mapping key. A duplicate direct ``rule_id`` inside
    the loader payload is rejected with
    ``STC_RULE_PACK_VALIDATION_REPORT_MISMATCH``.

    Final-cleanup-round permission-evidence re-keying (binding):

    The input dict's original ``permission_evidence`` mapping is also
    REJECTED as authority. The output ``permission_view`` dict is keyed
    by each permission artifact's direct ``permission_id`` (the
    artifact top-level ``permission_id`` string), not by the input
    mapping key. A duplicate direct ``permission_id`` is rejected with
    ``STC_RULE_PACK_VALIDATION_REPORT_MISMATCH``. Permission artifacts
    missing a non-empty ``permission_id`` are also rejected.

    The TASK-012 ``load_rule_pack`` loader itself keys rules by their
    direct ``rule_id`` (per Section 7.2); the rule re-keying enforces
    the adapter's invariant independently of the loader's internal
    iteration order. Permission re-keying is analogous but enforced
    here for the first time.

    Provenance edges are mapped into a tuple without re-keying (the
    adapter does not consume them by edge id).
    """
    manifest_obj = loader_result.get("manifest")
    rules_obj = loader_result.get("rules")
    pe_obj = loader_result.get("provenance_edges")
    perm_obj = loader_result.get("permission_evidence")
    if not isinstance(manifest_obj, Mapping):
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
            "loaded_rule_pack.manifest is not a mapping",
        )
    if not isinstance(rules_obj, Mapping):
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
            "loaded_rule_pack.rules is not a dict of rule artifacts",
        )
    if not isinstance(pe_obj, list):
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
            "loaded_rule_pack.provenance_edges is not a list",
        )
    if not isinstance(perm_obj, Mapping):
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
            "loaded_rule_pack.permission_evidence is not a dict",
        )

    rid, rver, rhash = _manifest_identity(manifest_obj)
    rules_view: dict[str, Mapping[str, object]] = {}
    seen_direct_rule_ids: set[str] = set()
    # Round-2 re-keying: ignore the input mapping key. Key by each
    # artifact's direct ``rule_id`` (Round-2 §7). Tuple of input
    # mapping keys is irrelevant to authority — the artifact's direct
    # ``rule_id`` field is the sole authority.
    for _input_key, artifact in rules_obj.items():
        if not isinstance(artifact, Mapping):
            raise BlockerError(
                str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
                f"loaded_rule_pack.rules[{_input_key!r}] is not a rule artifact mapping",
            )
        direct_rule_id = artifact.get("rule_id")
        if not isinstance(direct_rule_id, str) or not direct_rule_id:
            raise BlockerError(
                str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
                f"loaded_rule_pack.rules[{_input_key!r}] missing direct rule_id",
            )
        if direct_rule_id in seen_direct_rule_ids:
            raise BlockerError(
                str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
                f"duplicate direct rule_id {direct_rule_id!r}",
            )
        seen_direct_rule_ids.add(direct_rule_id)
        rules_view[direct_rule_id] = artifact
    pe_view = tuple(e for e in pe_obj if isinstance(e, Mapping))

    # Final-cleanup-round re-keying of permission_evidence. The input
    # mapping's keys are NOT authoritative; the artifact's direct
    # ``permission_id`` is. Artifacts missing ``permission_id`` or
    # carrying a duplicate ``permission_id`` are rejected.
    permission_view: dict[str, Mapping[str, object]] = {}
    seen_permission_ids: set[str] = set()
    for _input_perm_key, artifact in perm_obj.items():
        if not isinstance(artifact, Mapping):
            raise BlockerError(
                str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
                f"loaded_rule_pack.permission_evidence[{_input_perm_key!r}] "
                "is not a permission artifact mapping",
            )
        permission_id = artifact.get("permission_id")
        if not isinstance(permission_id, str) or not permission_id:
            raise BlockerError(
                str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
                f"loaded_rule_pack.permission_evidence[{_input_perm_key!r}] "
                "missing direct permission_id",
            )
        if permission_id in seen_permission_ids:
            raise BlockerError(
                str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
                f"duplicate direct permission_id {permission_id!r}",
            )
        seen_permission_ids.add(permission_id)
        permission_view[permission_id] = artifact

    return LoadedRulePackView(
        manifest=dict(manifest_obj),
        rules=dict(rules_view),
        provenance_edges=pe_view,
        permission_evidence=dict(permission_view),
        rule_pack_id=rid,
        rule_pack_version=rver,
        rule_pack_canonical_hash=rhash,
        rule_count=len(rules_view),
    )


def rule_pack_validation_report_from_validate_dict(
    validate_result: Mapping[str, object],
) -> RulePackValidationReport:
    """Adapter helper — wrap a TASK-012 ``validate_rule_pack`` dict result.

    Final-narrow-corrective-round fail-shape discipline (binding):

    The adapter reads ``status`` first. On ``status != "ok"`` the
    minimal TASK-012 failure shape ``{status, errors}`` is accepted
    and the resulting ``RulePackValidationReport`` carries:

        * ``manifest: None`` — when ``manifest`` key is missing;
        * ``manifest: dict(raw_manifest)`` — when ``manifest`` key is
          explicitly present and a valid mapping; the identity triple
          is extracted from it (when present);
        * ``rule_count: None`` — when ``rule_count`` key is missing;
        * ``rule_count: raw_rule_count`` — when ``rule_count`` key is
          explicitly present, isinstance int (not bool), non-negative.

    The wrapper distinguishes **key missing** from **key present but
    illegal value**:

        * ``status != "ok"``, ``manifest`` key missing:
          ``report.manifest is None`` (truthful absence).
        * ``status != "ok"``, ``manifest`` key explicit Mapping:
          ``report.manifest == dict(raw_manifest)`` (preserved).
        * ``status != "ok"``, ``manifest`` key explicit non-Mapping
          (str / list / int / etc.):
          ``STC_RULE_PACK_VALIDATION_REPORT_MISMATCH``. NO silent
          conversion to ``None`` and NO leakage of bare ``TypeError``
          from the dataclass.
        * ``status != "ok"``, ``rule_count`` key missing:
          ``report.rule_count is None``.
        * ``status != "ok"``, ``rule_count`` key explicit non-negative
          int (not bool):
          ``report.rule_count == raw_rule_count`` (preserved, may be 0).
        * ``status != "ok"``, ``rule_count`` key explicit illegal value
          (bool / negative int / float / str / list / mapping / None):
          ``STC_RULE_PACK_VALIDATION_REPORT_MISMATCH``. NO silent
          conversion to ``None`` and NO leakage of bare ``TypeError``.

    On ``status == "ok"`` both ``manifest`` (mapping) and ``rule_count``
    (``int``, non-negative, ``bool`` rejected) are required. The
    adapter never invents them either — they come from the real
    TASK-012 validator's report.

    The adapter NEVER parses ``errors[*].message`` and NEVER runs any
    TASK-012 approval / hash / license / provenance verification
    (per §6.3.2 + §6.3.3 + §20.C).
    """
    status = validate_result.get("status")
    if not isinstance(status, str) or not status:
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_FAILED),
            "validation_report.status is not a string",
        )

    errors_obj = validate_result.get("errors") or []
    if not isinstance(errors_obj, list):
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
            "validation_report.errors is not a list",
        )
    errors_view = tuple(e for e in errors_obj if isinstance(e, Mapping))

    if status == TASK_020_VALIDATION_REPORT_OK:
        # Success path — manifest + rule_count are REQUIRED.
        manifest_obj = validate_result.get("manifest")
        rule_count_obj = validate_result.get("rule_count")
        if not isinstance(manifest_obj, Mapping):
            raise BlockerError(
                str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
                "validation_report.manifest is not a mapping on status=ok",
            )
        if not isinstance(rule_count_obj, int) or isinstance(rule_count_obj, bool):
            raise BlockerError(
                str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
                "validation_report.rule_count is not an int on status=ok",
            )
        rid, rver, rhash = _manifest_identity(manifest_obj)
        return RulePackValidationReport(
            status=status,
            manifest=dict(manifest_obj),
            rule_count=rule_count_obj,
            errors=errors_view,
            rule_pack_id=rid,
            rule_pack_version=rver,
            rule_pack_canonical_hash=rhash,
        )

    # Failure path — precise key-presence semantics.
    #
    # ``manifest``:
    #   key missing → manifest_value = None
    #   key explicit Mapping → manifest_value = dict(raw_manifest),
    #                            identity triple extracted
    #   key explicit non-Mapping → BlockerError(MISMATCH); no
    #                               silent coercion to None
    #
    # ``rule_count``:
    #   key missing → rule_count_value = None
    #   key explicit non-negative int (not bool) → preserved
    #   key explicit any other type → BlockerError(MISMATCH); no
    #                                    silent coercion to None and
    #                                    no bare TypeError leakage.
    manifest_value: Mapping[str, object] | None = None
    rule_count_value: int | None = None
    rid = ""
    rver = ""
    rhash = ""

    if "manifest" in validate_result:
        raw_manifest = validate_result["manifest"]
        if not isinstance(raw_manifest, Mapping):
            raise BlockerError(
                str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
                "validation_report.manifest must be a mapping when "
                "explicitly supplied on a failure report",
            )
        manifest_value = dict(raw_manifest)
        rid, rver, rhash = _manifest_identity(raw_manifest)

    if "rule_count" in validate_result:
        raw_rule_count = validate_result["rule_count"]
        if (
            not isinstance(raw_rule_count, int)
            or isinstance(raw_rule_count, bool)
            or raw_rule_count < 0
        ):
            raise BlockerError(
                str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
                "validation_report.rule_count must be a non-negative int "
                "(bool rejected) when explicitly supplied on a failure report",
            )
        rule_count_value = raw_rule_count

    return RulePackValidationReport(
        status=status,
        manifest=manifest_value,
        rule_count=rule_count_value,
        errors=errors_view,
        rule_pack_id=rid,
        rule_pack_version=rver,
        rule_pack_canonical_hash=rhash,
    )


__all__ = [
    "ConfigurationRulePackAdapter",
    "loaded_rule_pack_view_from_loader_dict",
    "rule_pack_validation_report_from_validate_dict",
]
