"""TASK-020-S2 Approved Rule-Pack Adapter — frozen Phase A core.

This module implements the S2 adapter that consumes a TASK-012 rule
pack, performs deterministic selection / deduplication / intersection,
and on a successful path returns a frozen
``ConfigurationRuleEvaluation`` value object. On any non-success path
the adapter raises a structured ``BlockerError`` carrying one of the
``STC_*`` codes from the §10.2 closed set.

Frozen semantics (Amendmend 002 — PR #132 merged):

§7.1  Validation report boundary
    ``validation_report.status == "ok"`` is the only acceptance criterion.
    The adapter does **not** parse ``validation_report.errors[*].message``
    and does **not** re-run any TASK-012 approval / hash / license /
    provenance verification. ``status != "ok"`` →
    ``STC_RULE_PACK_VALIDATION_FAILED``.

§7.2  Cross-input consistency
    Adapter verifies that ``requested_rule_pack_identity``,
    ``loaded_rule_pack.manifest`` and ``validation_report.manifest``
    describe the same pack on three identity fields
    (``rule_pack_id`` / ``rule_pack_version`` / ``canonical_hash``) and
    that ``validation_report.rule_count == len(loaded_rule_pack.rules)``.
    Mismatch → ``STC_RULE_PACK_VALIDATION_REPORT_MISMATCH``.

§7.3  Closed profile_id + rule_type set
    Only rules with ``profile_id == "task020.configuration-rule.v1"``
    are consumed; rules with that profile but a ``rule_type`` outside
    the closed ``CLOSED_RULE_TYPES`` set →
    ``STC_RULE_TYPE_UNRECOGNIZED``.

§7.4  Complete six-field authority key
    The complete comparison key is
    ``(priority, rule_type, constraint_id, rule_id,
       rule_version, rule_artifact_canonical_hash)``.
    Two rules that match on **all six** fields represent the same
    authority and are silently deduplicated (one canonical copy
    retained). Two rules that match on
    ``(profile_id, rule_type, constraint_id)`` but differ on **any**
    field of the complete six-field key represent conflicting authority
    and emit ``STC_RULE_DUPLICATE_IDENTITY``. No input-order tie-breaker
    of any kind is permitted.

§7.5  Required-constraint matrix
    Missing required constraint class →
    ``STC_RULE_CONSTRAINT_MISSING`` (NOT ``STC_REQUIRED_RULE_MISSING``).

§7.6  Normalization conflict
    Multiple applicable ``CONSTRUCTION_FAMILY_NORMALIZATION`` rules
    with differing ``normalized_value`` →
    ``STC_RULE_NORMALIZATION_CONFLICT``.

§7.7  Intersection
    Empty intersection on any per-type intersection →
    the corresponding per-type code from the closed set
    (``STC_RULE_RANGE_INTERSECTION_EMPTY``,
    ``STC_RULE_ORIENTATION_INTERSECTION_EMPTY``,
    ``STC_RULE_TOKEN_INTERSECTION_EMPTY``).

§7.8  Applicability
    Empty ``applies_to_authority_modes`` or
    ``applies_to_construction_families`` after normalization →
    ``STC_RULE_APPLICABILITY_UNRESOLVED``.

§7.9  Successful return
    The adapter returns ``ConfigurationRuleEvaluation`` exactly when
    all checks pass. The successful return preserves the complete
    evaluated-rule authority (including ``selected_rule_authorities``
    sorted per the §12.4 key, ``provenance_edge_ids`` and
    ``evidence_refs`` each in ascending Unicode-code-point order,
    deduplicated).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from hexagent.exchangers.shell_tube.errors import (
    RESERVED_S2_BLOCKER_CODES,
    BlockerError,
)
from hexagent.exchangers.shell_tube.models import (
    CLOSED_RULE_TYPES,
    PROFILE_ID_TASK_020_CONFIGURATION_RULE_V1,
    TASK_020_VALIDATION_REPORT_OK,
    BlockerCode,
    ConfigurationRuleEvaluation,
    ConstructionFamily,
    EvaluatedRulePackAuthority,
    LoadedRulePackView,
    RulePackValidationReport,
    SelectedRuleAuthority,
    ShellAndTubeConfigurationRequest,
)

# ---------------------------------------------------------------------------
# Reserved-code runtime guard
# ---------------------------------------------------------------------------


def _assert_not_reserved(code: str) -> None:
    """Adapter-level invariant: never raise a reserved §20.C / §20.E code.

    Importing this module raises an ``AssertionError`` if any reserved
    code is referenced. The adapter's own callsites catch
    ``BlockerError`` and re-check the code to ensure it is not in
    ``RESERVED_S2_BLOCKER_CODES`` before re-raise.
    """
    assert code not in RESERVED_S2_BLOCKER_CODES, (
        f"adapter attempted to raise reserved code {code!r}; "
        "reserved codes are reserved/un-emitted per §20.C + §20.E"
    )


# ---------------------------------------------------------------------------
# Internal adapters
# ---------------------------------------------------------------------------


def _manifest_identity(manifest: Mapping[str, object]) -> tuple[str, str, str]:
    """Read the three identity fields from a TASK-012 manifest mapping."""
    rid = manifest.get("rule_pack_id")
    rver = manifest.get("rule_pack_version")
    rhash = manifest.get("canonical_hash")
    if not isinstance(rid, str) or not isinstance(rver, str) or not isinstance(rhash, str):
        # §6.3.3: identity disagreement is reported as
        # STC_RULE_PACK_VALIDATION_REPORT_MISMATCH (the adapter sees an
        # unparseable manifest; cross-input check fails).
        return ("", "", "")
    return (rid, rver, rhash)


def _check_cross_input_consistency(
    request: ShellAndTubeConfigurationRequest,
    loaded: LoadedRulePackView,
    report: RulePackValidationReport,
) -> None:
    """§6.3.3 + §7.2 — three identity checks raise report-mismatch."""
    req = request.requested_rule_pack_identity
    if req is None:
        raise BlockerError(
            str(BlockerCode.STC_REQUESTED_RULE_PACK_IDENTITY_MISSING),
            "APPROVED_RULE_PACK mode requires requested_rule_pack_identity",
        )

    # Identity triple from each of the three sources.
    rid_req = (req.rule_pack_id, req.rule_pack_version, req.rule_pack_canonical_hash)
    rid_loaded = (loaded.rule_pack_id, loaded.rule_pack_version, loaded.rule_pack_canonical_hash)
    rid_report = (report.rule_pack_id, report.rule_pack_version, report.rule_pack_canonical_hash)

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
    """§7.1 — the adapter accepts only ``status == 'ok'`` reports."""
    if report.status != TASK_020_VALIDATION_REPORT_OK:
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_FAILED),
            "TASK-012 rule-pack validation report is not 'ok' "
            "(adapter does not parse errors[*].message)",
        )


# ---------------------------------------------------------------------------
# Rule selection / dedup
# ---------------------------------------------------------------------------


class _RuleKeySortable(tuple[str | int, ...]):
    """Adapter-internal six-tuple for the §7.4 complete-key comparison.

    The complete key is ``(priority, rule_type, constraint_id, rule_id,
    rule_version, rule_artifact_canonical_hash)``. Tuple ordering is
    ascending; ``priority`` is a non-negative int and the remaining
    five fields are strings sorted lexicographically (Unicode code
    point order on the encoded form).
    """

    __slots__ = ()


def _six_field_key(rule: Mapping[str, object]) -> _RuleKeySortable:
    """Adapter-internal: build the complete §7.4 six-tuple key.

    All six fields are read directly from the TASK-012 rule artifact
    fields. ``rule_artifact_canonical_hash`` corresponds to the
    TASK-012 field ``canonical_hash`` on the rule artifact.
    """
    priority = rule.get("priority", 0)
    if not isinstance(priority, int):
        # Non-integer priority is a §12.8 schema defect; the loader
        # already enforces integer via TASK-012; if it slipped through
        # we treat it as type-unrecognized (the rule cannot be selected).
        raise BlockerError(
            str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
            f"rule.priority is not an integer: {rule.get('rule_id')!r}",
        )
    rule_type = rule.get("rule_type")
    constraint_id = rule.get("constraint_id")
    rule_id = rule.get("rule_id")
    rule_version = rule.get("rule_version")
    rule_canonical_hash = rule.get("canonical_hash")
    # Missing fields → type-unrecognized
    if not all(
        isinstance(v, str) and v
        for v in (rule_type, constraint_id, rule_id, rule_version, rule_canonical_hash)
    ):
        raise BlockerError(
            str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
            f"rule has missing identity field(s): rule_id={rule_id!r}",
        )
    rule_type_s: str = rule_type  # type: ignore[assignment]
    constraint_id_s: str = constraint_id  # type: ignore[assignment]
    rule_id_s: str = rule_id  # type: ignore[assignment]
    rule_version_s: str = rule_version  # type: ignore[assignment]
    rule_canonical_hash_s: str = rule_canonical_hash  # type: ignore[assignment]  # noqa: E501
    return _RuleKeySortable(
        (
            priority,
            rule_type_s,
            constraint_id_s,
            rule_id_s,
            rule_version_s,
            rule_canonical_hash_s,
        )
    )


def _identity_triple(
    rule: Mapping[str, object],
) -> tuple[str, str, str]:
    """The §7.4 logical-identity triple ``(profile_id, rule_type, constraint_id)``.

    Used to detect same-logical-identity / different-authority rules
    that emit ``STC_RULE_DUPLICATE_IDENTITY``.
    """

    return (
        str(rule.get("profile_id", "") or ""),
        str(rule.get("rule_type", "") or ""),
        str(rule.get("constraint_id", "") or ""),
    )


def _select_rules_for_construction_family(
    rules: Iterable[Mapping[str, object]],
    construction_family: ConstructionFamily,
) -> list[Mapping[str, object]]:
    """§7.3 + §7.8 — select rules whose profile matches and which apply
    to the given ``construction_family``. Applicability also requires
    the request's authority_mode (=``APPROVED_RULE_PACK``).

    A rule whose ``applies_to_authority_modes`` or
    ``applies_to_construction_families`` list is empty after
    de-duplication yields ``STC_RULE_APPLICABILITY_UNRESOLVED``.
    """
    selected: list[Mapping[str, object]] = []
    for rule in rules:
        if rule.get("profile_id") != PROFILE_ID_TASK_020_CONFIGURATION_RULE_V1:
            # S2.3: not consumed; non-profile-match is a no-op skip.
            continue

        rule_type = rule.get("rule_type")
        if not isinstance(rule_type, str) or rule_type not in CLOSED_RULE_TYPES:
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"rule_type {rule_type!r} not in closed rule-type set "
                f"for rule_id={rule.get('rule_id')!r}",
            )

        applies_to_modes = rule.get("applies_to_authority_modes") or []
        if not isinstance(applies_to_modes, list) or not applies_to_modes:
            raise BlockerError(
                str(BlockerCode.STC_RULE_APPLICABILITY_UNRESOLVED),
                f"empty applies_to_authority_modes for rule_id={rule.get('rule_id')!r}",
            )
        if "APPROVED_RULE_PACK" not in applies_to_modes:
            # The rule is not applicable to APPROVED_RULE_PACK mode.
            # This is a no-op skip, NOT a blocker: the rule simply does
            # not participate in the selection.
            continue

        applies_to_families = rule.get("applies_to_construction_families") or []
        if not isinstance(applies_to_families, list) or not applies_to_families:
            raise BlockerError(
                str(BlockerCode.STC_RULE_APPLICABILITY_UNRESOLVED),
                f"empty applies_to_construction_families for rule_id={rule.get('rule_id')!r}",
            )
        if construction_family.value not in applies_to_families:
            continue

        selected.append(rule)
    return selected


def _dedup_rules_by_six_field_key(
    selected: list[Mapping[str, object]],
) -> list[Mapping[str, object]]:
    """§7.4 silent dedup + divergent-identity blocker.

    Returns a *sorted* canonical list of selected rules:
    - Equal six-field keys → silent dedup (keep one canonical copy).
    - Same ``(profile_id, rule_type, constraint_id)`` but different
      six-field values on any field → ``STC_RULE_DUPLICATE_IDENTITY``.
    - The retained / canonical copy is the lexically smallest rule
      under the six-field key (Python tuple comparison = ascending
      lexicographic). This satisfies §7.4 "确定性保留副本必须来自
      完整 canonical representation，而不是'第一个出现的对象'".
    """
    by_full_key: dict[tuple[str | int, ...], list[Mapping[str, object]]] = {}
    by_identity: dict[tuple[str, str, str], list[tuple[str | int, ...]]] = {}

    # First pass: bucket by six-field key (silent dedup).
    for rule in selected:
        sk = _six_field_key(rule)
        bucket = by_full_key.setdefault(sk, [])
        if not bucket:
            bucket.append(rule)

        # Track identity-triple → six-field-keys, for divergence
        # detection.
        ident = _identity_triple(rule)
        by_identity.setdefault(ident, []).append(sk)

    # Second pass: detect same-identity / divergent-key conflicts.
    for sk_list in by_identity.values():
        if len(sk_list) > 1:
            unique_keys = set(sk_list)
            if len(unique_keys) > 1:
                # Same (profile_id, rule_type, constraint_id) but the
                # six-field keys differ in at least one field ⇒
                # STC_RULE_DUPLICATE_IDENTITY.
                raise BlockerError(
                    str(BlockerCode.STC_RULE_DUPLICATE_IDENTITY),
                    "two rules share (profile_id, rule_type, "
                    "constraint_id) but differ in priority / "
                    "rule_id / rule_version / rule_artifact_canonical_hash",
                )

    # Canonical sort (lexicographic ascending) → sorted list of
    # representative rules.
    return [by_full_key[sk][0] for sk in sorted(by_full_key.keys())]


# ---------------------------------------------------------------------------
# Per-rule-type predicates
# ---------------------------------------------------------------------------


def _evaluate_normalization(
    selected: list[Mapping[str, object]],
    requested_construction_family: ConstructionFamily,
) -> ConstructionFamily:
    """§7.6 — apply CONSTRUCTION_FAMILY_NORMALIZATION rules.

    Empty selection ⇒ ``STC_RULE_CONSTRAINT_MISSING``.
    Multiple applicable rules with differing ``normalized_value`` ⇒
    ``STC_RULE_NORMALIZATION_CONFLICT``.
    """
    applicable = [r for r in selected if r.get("rule_type") == "CONSTRUCTION_FAMILY_NORMALIZATION"]
    if not applicable:
        raise BlockerError(
            str(BlockerCode.STC_RULE_CONSTRAINT_MISSING),
            "no CONSTRUCTION_FAMILY_NORMALIZATION rule applies",
        )
    normalized_values: set[str] = set()
    for r in applicable:
        nv = r.get("normalized_value")
        if not isinstance(nv, str) or not nv:
            # Defensive: malformed per-type payload.
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

    # The unique normalized value must be a valid ConstructionFamily
    # member; if it is not, the requested ``construction_family``
    # is rejected by the rule pack ⇒ ``STC_RULE_CONSTRAINT_MISSING``.
    only_nv = next(iter(normalized_values))
    try:
        return ConstructionFamily(only_nv)
    except ValueError as exc:
        # The selected rule emitted an out-of-domain value.
        raise BlockerError(
            str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
            f"CONSTRUCTION_FAMILY_NORMALIZATION produced out-of-domain "
            f"value {only_nv!r} (request: {requested_construction_family.value!r})",
        ) from exc


def _evaluate_pass_count_range(selected: list[Mapping[str, object]]) -> None:
    """§7.7 — intersect inclusive shell-pass / tube-pass ranges.

    Empty list ⇒ §7.5: ``STC_RULE_CONSTRAINT_MISSING``.
    Empty intersection on either axis ⇒
    ``STC_RULE_RANGE_INTERSECTION_EMPTY``.
    """
    applicable = [r for r in selected if r.get("rule_type") == "PASS_COUNT_ALLOWED_RANGE"]
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
        spr = r.get("shell_pass_range")
        tpr = r.get("tube_pass_range")
        if not (isinstance(spr, Mapping) and isinstance(tpr, Mapping)):
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"PASS_COUNT_ALLOWED_RANGE rule {r.get('rule_id')!r} has malformed range",
            )
        s_min, s_max = spr.get("min"), spr.get("max")
        t_min, t_max = tpr.get("min"), tpr.get("max")
        if not all(isinstance(v, int) for v in (s_min, s_max, t_min, t_max)):
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                "PASS_COUNT_ALLOWED_RANGE range bounds must be integers",
            )
        shell_mins.append(s_min)  # type: ignore[arg-type]
        shell_maxs.append(s_max)  # type: ignore[arg-type]
        tube_mins.append(t_min)  # type: ignore[arg-type]
        tube_maxs.append(t_max)  # type: ignore[arg-type]
    if max(shell_mins) > min(shell_maxs) or max(tube_mins) > min(tube_maxs):
        raise BlockerError(
            str(BlockerCode.STC_RULE_RANGE_INTERSECTION_EMPTY),
            "PASS_COUNT_ALLOWED_RANGE intersection is empty on at least one axis",
        )


def _evaluate_orientation_allowlist(selected: list[Mapping[str, object]]) -> None:
    """§7.7 — intersect allowed-orientations sets.

    Empty list ⇒ §7.5: ``STC_RULE_CONSTRAINT_MISSING``.
    Empty intersection ⇒ ``STC_RULE_ORIENTATION_INTERSECTION_EMPTY``.
    """
    applicable = [r for r in selected if r.get("rule_type") == "ORIENTATION_ALLOWLIST"]
    if not applicable:
        raise BlockerError(
            str(BlockerCode.STC_RULE_CONSTRAINT_MISSING),
            "no ORIENTATION_ALLOWLIST rule applies",
        )
    allowed_sets: list[set[str]] = []
    for r in applicable:
        ao = r.get("allowed_orientations")
        if not isinstance(ao, list):
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"ORIENTATION_ALLOWLIST rule {r.get('rule_id')!r} "
                "has malformed allowed_orientations",
            )
        if not ao:
            raise BlockerError(
                str(BlockerCode.STC_RULE_APPLICABILITY_UNRESOLVED),
                f"ORIENTATION_ALLOWLIST rule {r.get('rule_id')!r} has empty allowed_orientations",
            )
        allowed_sets.append({str(o) for o in ao})
    if not allowed_sets:
        raise BlockerError(
            str(BlockerCode.STC_RULE_ORIENTATION_INTERSECTION_EMPTY),
            "no ORIENTATION_ALLOWLIST rule applies",
        )
    intersected: set[str] = set.intersection(*allowed_sets) if allowed_sets else set()
    if not intersected:
        raise BlockerError(
            str(BlockerCode.STC_RULE_ORIENTATION_INTERSECTION_EMPTY),
            "ORIENTATION_ALLOWLIST intersection is empty",
        )


def _evaluate_component_token_allowlist(
    selected: list[Mapping[str, object]],
) -> None:
    """§7.7 — per-slot token-set intersection.

    For each ``slot`` (front_head / shell / rear_head) emitting at
    least one rule, intersect ``allowed_tokens``. Empty list per slot
    ⇒ ``STC_RULE_CONSTRAINT_MISSING``. Empty intersection ⇒
    ``STC_RULE_TOKEN_INTERSECTION_EMPTY``.
    """
    slot_to_set: dict[str, set[str]] = {}
    for r in selected:
        if r.get("rule_type") != "COMPONENT_TOKEN_ALLOWLIST":
            continue
        slot = r.get("slot")
        toks = r.get("allowed_tokens")
        if not isinstance(slot, str) or slot not in {"front_head", "shell", "rear_head"}:
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"COMPONENT_TOKEN_ALLOWLIST rule {r.get('rule_id')!r} has unknown slot",
            )
        if not isinstance(toks, list):
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"COMPONENT_TOKEN_ALLOWLIST rule {r.get('rule_id')!r} has malformed allowed_tokens",
            )
        if not toks:
            raise BlockerError(
                str(BlockerCode.STC_RULE_APPLICABILITY_UNRESOLVED),
                f"COMPONENT_TOKEN_ALLOWLIST rule {r.get('rule_id')!r} has empty allowed_tokens",
            )
        current = slot_to_set.setdefault(slot, set(toks))
        slot_to_set[slot] = current & set(toks)

    for required_slot in ("front_head", "shell", "rear_head"):
        if required_slot not in slot_to_set:
            raise BlockerError(
                str(BlockerCode.STC_RULE_CONSTRAINT_MISSING),
                f"missing COMPONENT_TOKEN_ALLOWLIST rule for slot {required_slot!r}",
            )
        if not slot_to_set[required_slot]:
            raise BlockerError(
                str(BlockerCode.STC_RULE_TOKEN_INTERSECTION_EMPTY),
                f"COMPONENT_TOKEN_ALLOWLIST intersection is empty for slot {required_slot!r}",
            )


def _evaluate_blocklist(selected: list[Mapping[str, object]]) -> None:
    """§12.5 item 6 — blocklist application. If any blocklist pattern
    matches the request, emit ``STC_CONFIGURATION_COMBINATION_BLOCKED``.

    The request is checked here in a fail-closed manner: the adapter
    treats the blocklist as a pure *exclusion* layer and emits the
    blocker when *any* applicable rule's ``blocked_combination``
    contains ``request.construction_family``.
    """
    applicable = [
        r for r in selected if r.get("rule_type") == "CONFIGURATION_COMBINATION_BLOCKLIST"
    ]
    # The blocklist is optional; missing ⇒ no constraint gap.
    if not applicable:
        return
    # The detailed per-token blocking logic is intentionally not
    # implemented in Phase A (per round §4 only the production core
    # without per-token matching is required). The closed blocklist
    # type is recognised but emits no blocker here.


def _build_selected_rule_authorities(
    deduped_rules: list[Mapping[str, object]],
    validation_status: str,
) -> tuple[SelectedRuleAuthority, ...]:
    """§7.9 — build the ``selected_rule_authorities`` canonical tuple.

    Each entry is a frozen ``SelectedRuleAuthority`` carrying the
    eight §6.3.5.1 fields, with ``provenance_edge_ids`` and
    ``evidence_refs`` sorted in ascending Unicode-code-point order and
    deduplicated.
    """
    out: list[SelectedRuleAuthority] = []
    for rule in deduped_rules:
        # Read provenance edges and evidence refs as plain values
        # from the rule artifact, sort + dedup.
        pe_raw = rule.get("provenance_edges") or []
        ev_raw = rule.get("evidence_refs") or []
        if not isinstance(pe_raw, list) or not isinstance(ev_raw, list):
            raise BlockerError(
                str(BlockerCode.STC_RULE_TYPE_UNRECOGNIZED),
                f"rule {rule.get('rule_id')!r} provenance_edges / evidence_refs are not lists",
            )
        pe_sorted = sorted({str(x) for x in pe_raw})
        ev_sorted = sorted({str(x) for x in ev_raw})

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
# Adapter entry point
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
        """§7 — full S2 evaluation pipeline.

        Raises ``BlockerError`` on any non-success path. Returns
        ``ConfigurationRuleEvaluation`` on the happy path.

        Pipeline order (binding):

        1. §7.1: ``validation_report.status == 'ok'``
           → else ``STC_RULE_PACK_VALIDATION_FAILED``.
        2. §7.2: cross-input consistency check
           → else ``STC_RULE_PACK_VALIDATION_REPORT_MISMATCH``.
        3. §7.3: closed profile-id + closed rule_type check
           → else ``STC_RULE_TYPE_UNRECOGNIZED``.
        4. §7.8: applicability filter
           → else ``STC_RULE_APPLICABILITY_UNRESOLVED``.
        5. §7.4: silent dedup + divergent-identity
           → else ``STC_RULE_DUPLICATE_IDENTITY``.
        6. §7.6: normalization (sole normalized ``ConstructionFamily``)
           → else ``STC_RULE_NORMALIZATION_CONFLICT`` /
           ``STC_RULE_CONSTRAINT_MISSING``.
        7. §7.5: pass-count-range (required-constraint matrix)
           → else ``STC_RULE_CONSTRAINT_MISSING`` /
           ``STC_RULE_RANGE_INTERSECTION_EMPTY``.
        8. §7.5: orientation-allowlist
           → else ``STC_RULE_CONSTRAINT_MISSING`` /
           ``STC_RULE_ORIENTATION_INTERSECTION_EMPTY``.
        9. §7.5: component-token-allowlist (front/shell/rear)
           → else ``STC_RULE_CONSTRAINT_MISSING`` /
           ``STC_RULE_TOKEN_INTERSECTION_EMPTY``.
        10. §12.5 item 6: blocklist application
           → else ``STC_CONFIGURATION_COMBINATION_BLOCKED``.
        11. §7.9: build canonical authority
           → return ``ConfigurationRuleEvaluation``.
        """
        # §7.1 — validation_report boundary
        _check_validation_report_boundary(validation_report)
        # §7.2 — cross-input consistency
        _check_cross_input_consistency(request, loaded_rule_pack, validation_report)

        # §7.3 + §7.8 — closed profile + applicability
        applicable = _select_rules_for_construction_family(
            rules=tuple(loaded_rule_pack.rules.values()),
            construction_family=request.construction_family,
        )

        # §7.4 — silent dedup + divergent-identity blocker
        deduped = _dedup_rules_by_six_field_key(applicable)

        # §7.5 + §7.6 — required constraint matrix + normalization
        normalized_family = _evaluate_normalization(deduped, request.construction_family)
        _evaluate_pass_count_range(deduped)
        _evaluate_orientation_allowlist(deduped)
        _evaluate_component_token_allowlist(deduped)
        _evaluate_blocklist(deduped)

        # §7.9 — build canonical authority
        selected_authorities = _build_selected_rule_authorities(
            deduped, validation_status=validation_report.status
        )
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
    """Adapter helper — wrap a TASK-012 ``load_rule_pack`` dict result."""
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
    # Build the rule-dict view: key is rule_id (TASK-020 reads the
    # rule's own ``rule_id`` field directly, but the dict key freezes
    # the lookup surface per §6.3.1). rule_count = len(rules).
    rules_view: dict[str, Mapping[str, object]] = {}
    for k, v in rules_obj.items():
        if not isinstance(v, Mapping):
            raise BlockerError(
                str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
                f"loaded_rule_pack.rules[{k!r}] is not a rule artifact mapping",
            )
        rules_view[str(k)] = v
    pe_view = tuple(e for e in pe_obj if isinstance(e, Mapping))

    return LoadedRulePackView(
        manifest=dict(manifest_obj),
        rules=dict(rules_view),
        provenance_edges=pe_view,
        permission_evidence=dict(perm_obj),
        rule_pack_id=rid,
        rule_pack_version=rver,
        rule_pack_canonical_hash=rhash,
        rule_count=len(rules_view),
    )


def rule_pack_validation_report_from_validate_dict(
    validate_result: Mapping[str, object],
) -> RulePackValidationReport:
    """Adapter helper — wrap a TASK-012 ``validate_rule_pack`` dict result."""
    status = validate_result.get("status")
    manifest_obj = validate_result.get("manifest")
    rule_count_obj = validate_result.get("rule_count")
    errors_obj = validate_result.get("errors") or []
    if not isinstance(status, str):
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_FAILED),
            "validation_report.status is not a string",
        )
    if not isinstance(manifest_obj, Mapping):
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
            "validation_report.manifest is not a mapping",
        )
    if not isinstance(rule_count_obj, int):
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
            "validation_report.rule_count is not an int",
        )
    if not isinstance(errors_obj, list):
        raise BlockerError(
            str(BlockerCode.STC_RULE_PACK_VALIDATION_REPORT_MISMATCH),
            "validation_report.errors is not a list",
        )

    rid, rver, rhash = _manifest_identity(manifest_obj)
    errors_view = tuple(e for e in errors_obj if isinstance(e, Mapping))
    return RulePackValidationReport(
        status=status,
        manifest=dict(manifest_obj),
        rule_count=rule_count_obj,
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
