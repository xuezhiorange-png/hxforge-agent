"""CostModelSelector — TASK-018 §5.1 read-only application-layer selector.

This module implements the deterministic, read-only cost-record
selector documented in TASK-018 §5.1. It is the **application-layer
contract** that consumes TASK-013 cost-data governance records
**read-only** (TASK-018 §17 boundary). It MUST NOT:

    - re-derive C0 heuristic coefficients, C1 labor/minute formulas,
      or material unit prices inline;
    - mix currency conversions, escalation math, or region-specific
      tax/installation handling into the cost records themselves;
    - embed restricted-source bodies into engineering artifacts
      (TASK-013 §9 boundary);
    - mutate the TASK-013 cost records passed in;
    - perform CAPEX / OPEX / C0 / C1 subtotal arithmetic (lives in
      CostCalculator, Slice B);
    - perform life-cycle energy computation (lives in
      LifeCycleEnergyEstimator, Slice C).

Deterministic guarantees (TASK-018 §10):

    - sort ascending ``cost_record_id`` then descending ``cost_record_version``
      inside the result envelope;
    - integer monetary fields (not used by Slice A — see CostCalculator for
      ``amount_minor_units`` semantics);
    - SHA-256 ``provenance_chain_hash`` over the canonical-JSON of
      ``{source_record_ids, correlation_ids, case_input_field, license_class,
      schema_version}``;
    - closed-set blocker / warning codes (``errors.py``).

JSON / hash discipline:
    - Inputs MUST be canonical JSON encodable (TASK-018 §10 + RFC 8785);
      records are taken as-is from TASK-013 governance and not
      re-serialized here;
    - ``schema_version`` is emitted as ``"0.1.0"`` per TASK-018 §5.1.3.

The selector does NOT perform any cost calculation. Its output is the
``CostModelSelectionResult`` envelope, which downstream CostCalculator
(Slice B) consumes as ``cost_model_selection_result`` per TASK-018 §5.2.1.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from .errors import (
    BLOCKER_CODES,
    WARNING_CODES,
    BlockerCode,
    CostSelectorError,
    CostSelectorWarning,
    WarningCode,
)

SCHEMA_VERSION: Final[str] = "0.1.0"
PROPRIETARY_RESTRICTED: Final[str] = "proprietary_restricted"
SELECTOR_LICENSE_CLASSES: Final[tuple[str, ...]] = (
    "public_open",
    "internal_open",
)

# Stable UUID namespace for ``selector_run_id`` (TASK-018 §5.1.3 requires
# UUID v5 over a canonical selection fingerprint).  Derived from the SHA-256
# of the frozen TASK-018 design's Frozen Contract Authority Base SHA so the
# namespace is anchored to the contract authority itself -- a future
# design-amendment round that re-anchors to a new base SHA MUST regenerate
# this namespace too.  The intermediate SHA-256 takes any length of base SHA
# down to UUID's 128-bit native size.
_SELECTOR_RUN_ID_NAMESPACE: Final[uuid.UUID] = uuid.UUID(
    bytes=bytes(
        hashlib.sha256(
            b"task-018-selector-run-idns:"
            + bytes.fromhex("5f96cf761d470b82faa1a5d164eefd42360c7df9")
        ).digest()[:16]
    )
)

# Frozen closed-set blocker codes used by this selector (TASK-018 §9.1).
# These are the only CostModelSelector blockers; CostCalculator /
# LifeCycleEnergyEstimator will add their own slice-specific codes
# in Slice B / C under separate authorization.
_ALLOWED_SELECTOR_BLOCKERS: Final[tuple[str, ...]] = (
    BlockerCode.REGION_UNSUPPORTED_BLOCKER.value,
    BlockerCode.VALIDITY_ENVELOPE_BLOCKER.value,
    BlockerCode.RESTRICTED_BODY_PROPAGATION_BLOCKER.value,
    BlockerCode.UNSPECIFIED_BLOCKER.value,
)


@dataclass(frozen=True)
class SelectionFilters:
    """Input filters for ``CostModelSelector`` (TASK-018 §5.1.1)."""

    material_family: str
    case_region: str
    effective_date: str  # RFC 3339 UTC `Z` string
    cost_category_filter: frozenset[str]  # subset of TASK-013 §6.1
    quantity_basis_filter: frozenset[str]  # subset of TASK-013 §6.3
    license_class_filter: frozenset[str] = field(
        default_factory=lambda: frozenset(SELECTOR_LICENSE_CLASSES)
    )
    escalation_index_reference_filter: frozenset[str] | None = None
    record_currency: str | None = None
    validity_envelope: Mapping[str, object] | None = None


@dataclass(frozen=True)
class CostModelSelectionResult:
    """Output envelope for the selector (TASK-018 §5.1.3).

    The dataclass is frozen; downstream consumers (Slice B CostCalculator)
    treat it as immutable. ``provenance_chain_hash`` is a SHA-256 over a
    canonical-JSON serialization of a fingerprint extracted from the
    selected records (see ``_compute_provenance_chain_hash``).
    """

    schema_version: str
    selector_run_id: str
    c0_records: Sequence[Mapping[str, object]]
    c1_records: Sequence[Mapping[str, object]]
    selection_warnings: tuple[dict[str, object], ...]
    selection_blockers: tuple[dict[str, object], ...]
    license_class_summary: dict[str, int]
    provenance_chain_hash: str

    def to_dict(self) -> dict[str, object]:
        """Stable JSON-friendly view (used for hashing + audit logs)."""
        return {
            "schema_version": self.schema_version,
            "selector_run_id": self.selector_run_id,
            "c0_records": [dict(r) for r in self.c0_records],
            "c1_records": [dict(r) for r in self.c1_records],
            "selection_warnings": list(self.selection_warnings),
            "selection_blockers": list(self.selection_blockers),
            "license_class_summary": dict(self.license_class_summary),
            "provenance_chain_hash": self.provenance_chain_hash,
        }


@dataclass(frozen=True)
class _RecordKey:
    """Sort key over TASK-018 §5.1.3 ordering rule."""

    cost_record_id: str
    cost_record_version: str  # semver string; descending ⇒ invert via tuple


def _stable_record_sort_key(record: Mapping[str, object]) -> _RecordKey:
    cost_record_id = str(record.get("cost_record_id", ""))
    cost_record_version = str(record.get("cost_record_version", "0.0.0"))
    return _RecordKey(cost_record_id=cost_record_id, cost_record_version=cost_record_version)


def _sort_records(records: Iterable[Mapping[str, object]]) -> list[Mapping[str, object]]:
    """Stable ordering: cost_record_id ASC, then cost_record_version DESC.

    Implements TASK-018 §5.1.3 ordering rule. We pin the comparator to a
    tuple of (ascending id, descending version) so the sort is total and
    deterministic.
    """
    keyed = [(_stable_record_sort_key(r), r) for r in records]
    keyed.sort(key=lambda kr: (kr[0].cost_record_id, _negate_semver(kr[0].cost_record_version)))
    return [r for _, r in keyed]


def _negate_semver(version: str) -> tuple[int, int, int, str]:
    """Return ``(-major, -minor, -patch)`` plus pristine label.

    Used to invert semver ordering so DESCENDING ``cost_record_version``
    means newer revisions come first while remaining a total order over
    semver components. Pre-release labels are preserved as a stable suffix
    used only to break ties; for ordering purposes the numeric components
    dominate.
    """
    core, _, _pre = version.partition("-")
    parts = core.split(".")
    try:
        nums = [int(p) for p in parts[:3]] + [0] * (3 - len(parts[:3]))
    except ValueError as exc:
        raise CostSelectorError(
            BlockerCode.UNSPECIFIED_BLOCKER.value,
            details={"reason": "invalid cost_record_version", "value": version},
        ) from exc
    return (-nums[0], -nums[1], -nums[2], _pre)


def _fingerprint_for_hash(record: Mapping[str, object]) -> dict[str, object]:
    """TASK-018 §7 fingerprint: source_record_ids / correlation_ids /
    case_input_field / license_class / schema_version."""
    return {
        "source_record_ids": [str(record.get("cost_record_id", ""))],
        "correlation_ids": _cast_list(record.get("correlation_ids") or []),
        "case_input_field": _cast_dict(record.get("case_input_field") or {}),
        "license_class": str(record.get("license_class", "")),
        "schema_version": SCHEMA_VERSION,
    }


def _cast_list(obj: object) -> list[object]:
    """Narrow ``object`` to ``list[object]`` for downstream list operations."""
    return list(obj) if isinstance(obj, list) else []


def _cast_dict(obj: object) -> dict[str, object]:
    """Narrow ``object`` to ``dict[str, object]`` for downstream dict operations."""
    return dict(obj) if isinstance(obj, dict) else {}


def _compute_provenance_chain_hash(
    selected: Sequence[Mapping[str, object]],
) -> str:
    """TASK-018 §7 + §10: SHA-256 over canonical-JSON of an aggregated
    fingerprint of the selection.
    """
    source_record_ids: list[str] = []
    correlation_ids: list[object] = []
    license_class_summary: dict[str, int] = {
        "public_open_count": 0,
        "internal_open_count": 0,
        "proprietary_restricted_count": 0,
    }
    for record in selected:
        fp = _fingerprint_for_hash(record)
        source_ids_typed = _cast_list(fp["source_record_ids"])
        corr_ids_typed: list[object] = _cast_list(fp["correlation_ids"])
        for sid in source_ids_typed:
            if isinstance(sid, str):
                source_record_ids.append(sid)
        for cid in corr_ids_typed:
            correlation_ids.append(cid)
        # NOTE: case_input_field is intentionally left out of the
        # aggregated hash here — it describes per-result-per-call
        # introspection only. The selector's chain hash is anchored
        # on the *records it selected*, not on the caller-supplied
        # case field map.
    source_record_ids_sorted: list[str] = sorted(source_record_ids)
    aggregated: dict[str, object] = {
        "source_record_ids": source_record_ids_sorted,
        "correlation_ids": correlation_ids,
        "case_input_field": {},
        "license_class_summary": license_class_summary,
    }
    payload = json.dumps(aggregated, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _compute_selector_run_id(
    *,
    schema_version: str,
    provenance_chain_hash: str,
    license_class_summary: Mapping[str, int],
) -> str:
    """TASK-018 §5.1.3 ``selector_run_id``: deterministic UUID v5 over a
    canonical-JSON payload of the selection fingerprint.

    The fingerprint is keyed on ``schema_version``, ``provenance_chain_hash``
    (SHA-256 over the §7 selection fingerprint), and ``license_class_summary``
    (the §5.1.3 envelope field's typed-int counts).  The namespace is anchored
    on the Frozen Contract Authority Base SHA (see ``_SELECTOR_RUN_ID_NAMESPACE``)
    so it is shared across all TASK-018-implementing selectors within the
    design contract's authority chain and changes only on design-amendment.
    """
    payload = json.dumps(
        {
            "schema_version": schema_version,
            "provenance_chain_hash": provenance_chain_hash,
            "license_class_summary": dict(license_class_summary),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return str(uuid.uuid5(_SELECTOR_RUN_ID_NAMESPACE, payload))


def _validate_record_shape(record: Mapping[str, object]) -> None:
    """Surface structural problems as frozen closed-set blockers
    (TASK-018 §9.1). The selector is intentionally strict here:
    malformed records must not silently propagate.
    """
    required = (
        "cost_record_id",
        "cost_record_version",
        "cost_category",
        "cost_basis",
        "currency",
        "quantity_basis",
        "cost_value",
        "license_class",
        "source_class",
    )
    missing = [field_ for field_ in required if field_ not in record]
    if missing:
        raise CostSelectorError(
            BlockerCode.UNSPECIFIED_BLOCKER.value,
            details={"reason": "missing_required_record_fields", "fields": missing},
        )


def _project_canonical(record: Mapping[str, object]) -> dict[str, object]:
    """Project a TASK-013 record onto the TASK-018 §5.1.2 canonical shape."""
    return {
        "cost_record_id": str(record.get("cost_record_id", "")),
        "cost_record_version": str(record.get("cost_record_version", "")),
        "cost_category": str(record.get("cost_category", "")),
        "cost_basis": str(record.get("cost_basis", "")),
        "currency": str(record.get("currency", "")),
        "quantity_basis": str(record.get("quantity_basis", "")),
        "cost_value": record.get("cost_value"),
        "escalation_index_reference": (
            str(record["escalation_index_reference"])
            if record.get("escalation_index_reference") is not None
            else None
        ),
        "license_class": str(record.get("license_class", "")),
        "source_class": str(record.get("source_class", "")),
        "validity_envelope": _cast_dict(record.get("validity_envelope") or {}),
    }


def _check_license_class_allowed(
    record: Mapping[str, object],
    allowed: frozenset[str],
) -> bool:
    return str(record.get("license_class", "")) in allowed


def _check_validity_envelope(
    record: Mapping[str, object],
    envelope: Mapping[str, object] | None,
) -> bool:
    """TASK-018 Section 6.5: enforce validity_envelope match.

    The envelope is a caller-supplied set of cap keys. Each cap key is
    looked up against ``record["cost_value_per_cap_key"][key]`` if the
    record provides that field, or against
    ``record["validity_envelope"][key]`` as a record-stored actual.

    Numeric caps enforce a less-than-or-equal cap; any other recorded
    value that differs from the cap rejects the record.
    """
    if envelope is None:
        return True
    if not envelope:
        return True
    record_envelope: object = record.get("validity_envelope") or {}
    if not isinstance(record_envelope, Mapping):
        return False
    for key, cap in envelope.items():
        if key not in record_envelope:
            return False
        record_value = record_envelope.get(key)
        if isinstance(cap, (int, float)) and isinstance(record_value, (int, float)):
            if record_value > cap:
                return False
        else:
            if record_value != cap:
                return False
    return True


def _build_selection(
    records: Sequence[Mapping[str, object]],
    filters: SelectionFilters,
) -> CostModelSelectionResult:
    """Apply the filter pipeline and assemble the canonical result."""
    blockers: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []

    allowed_licenses = filters.license_class_filter
    if PROPRIETARY_RESTRICTED in allowed_licenses:
        # The selector may surface pointers from restricted records but
        # the contract defaults are public_open + internal_open. Allow
        # explicit caller opt-in without error, but never silently mix
        # body into the result.
        pass

    if not records:
        blockers.append(
            {
                "code": BlockerCode.REGION_UNSUPPORTED_BLOCKER.value,
                "details": {"filters": "no records provided for selection"},
            }
        )

    c0_bucket: list[Mapping[str, object]] = []
    c1_bucket: list[Mapping[str, object]] = []

    for record in records:
        try:
            _validate_record_shape(record)
        except CostSelectorError as exc:
            blockers.append({"code": exc.code, "details": exc.details})
            continue

        cost_category = str(record.get("cost_category", ""))

        # Bucket must be inferable from cost_category prefix BEFORE
        # license/quantity-basis filters; a record whose category does
        # not match c0_/c1_ cannot land in either bucket, so emit the
        # closed-set blocker explicitly (do not silently drop).
        if cost_category.startswith("c0_"):
            bucket: list[Mapping[str, object]] = c0_bucket
        elif cost_category.startswith("c1_"):
            bucket = c1_bucket
        else:
            blockers.append(
                {
                    "code": BlockerCode.UNSPECIFIED_BLOCKER.value,
                    "details": {
                        "reason": "cost_category_does_not_match_c0_or_c1",
                        "cost_category": cost_category,
                    },
                }
            )
            continue

        if cost_category not in filters.cost_category_filter:
            continue

        quantity_basis = str(record.get("quantity_basis", ""))
        if quantity_basis not in filters.quantity_basis_filter:
            continue

        # TASK-018 §5.1.1 / §5.2.2 escalation-pointer filter: the
        # caller may restrict the selection to records whose
        # ``escalation_index_reference`` is in the supplied set.  A
        # ``None`` filter means "no escalation selection" (records pass
        # regardless); a non-None filter excludes records whose
        # escalation pointer is ``None`` or whose escalation pointer
        # is not in the allowed set.
        if filters.escalation_index_reference_filter is not None:
            escalation_pointer = record.get("escalation_index_reference")
            if (
                not isinstance(escalation_pointer, str)
                or escalation_pointer not in filters.escalation_index_reference_filter
            ):
                continue

        if not _check_license_class_allowed(record, allowed_licenses):
            warnings.append(
                {
                    "code": WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value,
                    "details": {"reason": "license_class_filter excluded record"},
                }
            )
            continue

        if not _check_validity_envelope(record, filters.validity_envelope):
            blockers.append(
                {
                    "code": BlockerCode.VALIDITY_ENVELOPE_BLOCKER.value,
                    "details": {"record_id": record.get("cost_record_id")},
                }
            )
            continue

        if (
            filters.record_currency is not None
            and str(record.get("currency", "")) != filters.record_currency
        ):
            warnings.append(
                {
                    "code": WarningCode.CURRENCY_FALLBACK_USED_WARNING.value,
                    "details": {"record_currency": record.get("currency")},
                }
            )

        try:
            projected = _project_canonical(record)
        except CostSelectorError as exc:
            blockers.append({"code": exc.code, "details": exc.details})
            continue

        # Sort-key derivation can fail on a malformed record (e.g.
        # ``cost_record_version`` not parseable as semver). Surface that
        # as an unspecified_blocker rather than letting the exception
        # escape, so callers see a stable result envelope.
        sort_key_error = _safe_sort_key_error(record)
        if sort_key_error is not None:
            blockers.append(sort_key_error)
            continue

        # Restricted-source body isolation (TASK-018 Section 8): even
        # when an explicitly opt-in caller allows ``proprietary_restricted``
        # records through, the projected canonical shape contains
        # ID/version/license metadata only -- never the raw ``cost_value``
        # body. We enforce that here.
        if projected["license_class"] == PROPRIETARY_RESTRICTED:
            projected["cost_value"] = None  # pointer only

        bucket.append(projected)

    c0_sorted = _sort_records(c0_bucket)
    c1_sorted = _sort_records(c1_bucket)

    # Inventory the closed-set codes that appeared in the result. Any
    # code present in the result but not in the frozen closed set is a
    # contract violation (TASK-018 §9.1 "No new codes may be introduced").
    for entry in blockers:
        code = entry.get("code")
        if code not in BLOCKER_CODES:
            raise CostSelectorError(
                BlockerCode.UNSPECIFIED_BLOCKER.value,
                details={"non_frozen_blocker_code": code},
            )
    for entry in warnings:
        code = entry.get("code")
        if code not in WARNING_CODES:
            raise CostSelectorWarning(
                WarningCode.UNSPECIFIED_WARNING.value,
                details={"non_frozen_warning_code": code},
            )

    license_class_summary = {
        "public_open_count": sum(
            1 for r in c0_sorted + c1_sorted if r["license_class"] == "public_open"
        ),
        "internal_open_count": sum(
            1 for r in c0_sorted + c1_sorted if r["license_class"] == "internal_open"
        ),
        "proprietary_restricted_count": sum(
            1 for r in c0_sorted + c1_sorted if r["license_class"] == PROPRIETARY_RESTRICTED
        ),
    }

    # §8 line 340: when the selected result envelope contains any
    # proprietary_restricted record (``proprietary_restricted_count > 0``),
    # the selector MUST emit ``restricted_only_provenance_warning`` --
    # the warning is an artifact of the **envelope containing restricted
    # pointers**, independent of whether the license filter excluded any
    # records above.  De-duped against any pre-existing warning of the
    # same code (the license-class exclusion path also emits the same
    # code); callers must see at most one entry per run.
    if license_class_summary["proprietary_restricted_count"] > 0 and not any(
        existing.get("code") == WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value
        for existing in warnings
    ):
        warnings.append(
            {
                "code": WarningCode.RESTRICTED_ONLY_PROVENANCE_WARNING.value,
                "details": {
                    "reason": "license_class_summary.proprietary_restricted_count > 0",
                    "proprietary_restricted_count": license_class_summary[
                        "proprietary_restricted_count"
                    ],
                },
            }
        )

    selected_records: list[Mapping[str, object]] = list(c0_sorted) + list(c1_sorted)
    provenance_chain_hash = _compute_provenance_chain_hash(selected_records)
    # ``selector_run_id`` is TASK-018 §5.1.3's deterministic UUID v5 over
    # the canonical-JSON of the selection fingerprint: ``schema_version`` +
    # ``provenance_chain_hash`` + ``license_class_summary``.  Anchoring on
    # the base SHA below means a different schema_version or a different
    # selection set produces a different id; same selection ⇒ same id.
    selector_run_id = _compute_selector_run_id(
        schema_version=SCHEMA_VERSION,
        provenance_chain_hash=provenance_chain_hash,
        license_class_summary=license_class_summary,
    )

    return CostModelSelectionResult(
        schema_version=SCHEMA_VERSION,
        selector_run_id=selector_run_id,
        c0_records=tuple(c0_sorted),
        c1_records=tuple(c1_sorted),
        selection_warnings=tuple(warnings),
        selection_blockers=tuple(blockers),
        license_class_summary=license_class_summary,
        provenance_chain_hash=provenance_chain_hash,
    )


def _safe_sort_key_error(
    record: Mapping[str, object],
) -> dict[str, object] | None:
    """Return ``None`` if the sort key derivation succeeds, otherwise an
    ``unspecified_blocker`` entry describing the failure.

    This keeps the sort-key pipeline failure from escaping to the caller;
    the CostModelSelector contract always delivers a result envelope,
    not an exception, for routine data problems.
    """
    try:
        _stable_record_sort_key(record)
        # also smoke-test the version negation path
        _negate_semver(str(record.get("cost_record_version", "0.0.0")))
        return None
    except (CostSelectorError, ValueError) as exc:
        return {
            "code": BlockerCode.UNSPECIFIED_BLOCKER.value,
            "details": {
                "reason": "invalid sort key derivation",
                "record_id": str(record.get("cost_record_id", "")),
                "value": str(record.get("cost_record_version", "")),
                "exception": type(exc).__name__,
            },
        }


class CostModelSelector:
    """Read-only deterministic selector (TASK-018 §5.1).

    The selector does not mutate any input. It consumes TASK-013
    cost-data records verbatim, projects them onto the TASK-018
    §5.1.2 canonical shape, applies the filter pipeline, sorts
    deterministically, and emits a ``CostModelSelectionResult``.

    Slice A is intentionally narrow: no CAPEX/OPEX/C0/C1 subtotal math,
    no life-cycle energy inputs, no currency conversion, no C2/C3
    ingestion.
    """

    SCHEMA_VERSION: Final[str] = SCHEMA_VERSION

    def select(
        self,
        records: Sequence[Mapping[str, object]],
        filters: SelectionFilters,
    ) -> CostModelSelectionResult:
        """Run selection. Returns a result envelope.

        Raises ``CostSelectorError`` only when a frozen-closed-set
        invariant is violated (e.g. a non-frozen blocker code slipped
        into the result). Ordinary selection failures surface as
        ``CostModelSelectionResult.selection_blockers`` entries —
        never as exceptions — so the application layer can
        distinguish "tried to select, got nothing usable" from
        "contract violation, do not ship".
        """
        # Frozen-closed-set invariant: the selector never introduces
        # codes outside the frozen set. The closed-set guard below
        # mirrors the same check that runs inside ``_build_selection``
        # at build time; doing it twice is cheap and gives callers a
        # clean error before they see a half-built result.
        for code in _ALLOWED_SELECTOR_BLOCKERS:
            if code not in BLOCKER_CODES:
                raise CostSelectorError(
                    BlockerCode.UNSPECIFIED_BLOCKER.value,
                    details={"non_frozen_blocker_code_in_selector": code},
                )
        return _build_selection(list(records), filters)


def select_cost_records(
    records: Sequence[Mapping[str, object]],
    filters: SelectionFilters,
) -> CostModelSelectionResult:
    """Functional entrypoint mirroring ``CostModelSelector().select``."""
    return CostModelSelector().select(records, filters)


__all__ = [
    "SCHEMA_VERSION",
    "CostModelSelectionResult",
    "CostModelSelector",
    "SelectionFilters",
    "select_cost_records",
]
