"""
TASK-009 Phase 2 — candidate identity models for physical and
source-qualified candidate deduplication and ordering.
"""

from __future__ import annotations

import dataclasses
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from hexagent.core.canonical import sha256_digest
from hexagent.optimization._quantum import canonicalize_length_quantum
from hexagent.optimization.catalog import catalog_identity_key, compute_catalog_content_hash
from hexagent.optimization.context import (
    _MATERIALIZATION_TOKEN,
    MaterializedCandidateSet,
    PassedSizingGate,
    _create_materialized_candidate_set,
)
from hexagent.optimization.materialization import materialize_lengths_for_option
from hexagent.optimization.models import (
    CatalogSnapshotRef,
    CompleteDoublePipeAssemblyOption,
    CompleteDoublePipeCatalogSnapshot,
    OptionRawCountRecord,
    option_raw_count_record_identity_key,
)

# ---------------------------------------------------------------------------
# PhysicalCandidateIdentity
# ---------------------------------------------------------------------------


class PhysicalCandidateIdentity(BaseModel):
    """Identity of a candidate based solely on physical geometry and length.

    Two candidates with the same physical parameters but different
    catalog/option sources produce the same ``physical_identity_digest``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    inner_tube_inner_diameter_m: float
    inner_tube_outer_diameter_m: float
    outer_pipe_inner_diameter_m: float
    effective_length_m_canonical: str
    wall_thermal_conductivity_w_m_k: float
    inner_surface_roughness_m: float
    annulus_surface_roughness_m: float
    inner_fouling_resistance_m2k_w: float
    outer_fouling_resistance_m2k_w: float

    @property
    def physical_identity_digest(self) -> str:
        """Deterministic SHA-256 content hash of this identity."""
        return sha256_digest(self)


# ---------------------------------------------------------------------------
# SourceQualifiedCandidateIdentity
# ---------------------------------------------------------------------------


class SourceQualifiedCandidateIdentity(BaseModel):
    """Identity of a candidate qualified by its source catalog context.

    The deduplication key is the *full* identity, not just the physical
    digest.  Two candidates from different catalogs with the same
    physical parameters have different source-qualified identities.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    physical_identity_digest: str
    catalog_id: str
    catalog_version: str
    catalog_content_hash: str
    assembly_option_id: str
    manufacturing_option_identity: str

    @property
    def source_qualified_candidate_id(self) -> str:
        """Deterministic SHA-256 content hash of this source-qualified identity."""
        return sha256_digest(self)


# ---------------------------------------------------------------------------
# CatalogSnapshotRef helpers (used internally)
# ---------------------------------------------------------------------------


def catalog_snapshot_ref(cat: CompleteDoublePipeCatalogSnapshot) -> CatalogSnapshotRef:
    """Build a snapshot-ref from a typed catalog snapshot."""
    return CatalogSnapshotRef(
        catalog_id=cat.catalog_id,
        catalog_version=cat.catalog_version,
        catalog_content_hash=cat.catalog_content_hash,
        source_identity=cat.source_identity,
        schema_version=cat.schema_version,
    )


# ---------------------------------------------------------------------------
# ManufacturableCandidate — the Phase 2 aggregate
# ---------------------------------------------------------------------------


class ManufacturableCandidate(BaseModel):
    """A fully qualified, materialised candidate ready for TASK-008 evaluation.

    ``evaluation_order_index`` is assigned after deduplication and
    canonical sorting so that repeated runs produce identical order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Core identity records
    physical_identity: PhysicalCandidateIdentity
    physical_identity_digest: str
    source_qualified_identity: SourceQualifiedCandidateIdentity
    source_qualified_candidate_id: str

    # Source context
    catalog_snapshot_ref: CatalogSnapshotRef
    assembly_option_id: str
    manufacturing_option_identity: str
    manufacturing_metadata: tuple[tuple[str, str], ...]

    # Materialised length
    effective_length_m_canonical: str

    # Evaluation order (assigned after dedup + canonical sort)
    evaluation_order_index: int

    @model_validator(mode="after")
    def _verify_self_consistency(self) -> Self:
        errors: list[str] = []

        # physical_identity_digest == physical_identity.physical_identity_digest
        expected_physical_digest = self.physical_identity.physical_identity_digest
        if self.physical_identity_digest != expected_physical_digest:
            errors.append(
                f"physical_identity_digest mismatch: "
                f"{self.physical_identity_digest!r} != {expected_physical_digest!r}"
            )

        # source_qualified_identity.physical_identity_digest == physical_identity_digest
        if self.source_qualified_identity.physical_identity_digest != self.physical_identity_digest:
            errors.append(
                "source_qualified_identity.physical_identity_digest "
                f"({self.source_qualified_identity.physical_identity_digest!r}) "
                f"!= physical_identity_digest ({self.physical_identity_digest!r})"
            )

        # source_qualified_candidate_id
        expected_sq_id = self.source_qualified_identity.source_qualified_candidate_id
        if self.source_qualified_candidate_id != expected_sq_id:
            errors.append(
                f"source_qualified_candidate_id mismatch: "
                f"{self.source_qualified_candidate_id!r} != {expected_sq_id!r}"
            )

        # catalog_snapshot_ref fields match source-qualified catalog fields
        sr = self.catalog_snapshot_ref
        sq = self.source_qualified_identity
        if sr.catalog_id != sq.catalog_id:
            errors.append(f"catalog_id: {sr.catalog_id!r} != {sq.catalog_id!r}")
        if sr.catalog_version != sq.catalog_version:
            errors.append(f"catalog_version: {sr.catalog_version!r} != {sq.catalog_version!r}")
        if sr.catalog_content_hash != sq.catalog_content_hash:
            errors.append(
                f"catalog_content_hash: {sr.catalog_content_hash!r} != {sq.catalog_content_hash!r}"
            )

        # assembly_option_id matches source-qualified
        if self.assembly_option_id != sq.assembly_option_id:
            errors.append(
                f"assembly_option_id: {self.assembly_option_id!r} != {sq.assembly_option_id!r}"
            )

        # manufacturing_option_identity matches source-qualified
        if self.manufacturing_option_identity != sq.manufacturing_option_identity:
            errors.append(
                f"manufacturing_option_identity: "
                f"{self.manufacturing_option_identity!r} != "
                f"{sq.manufacturing_option_identity!r}"
            )

        # effective_length_m_canonical matches physical identity
        if self.effective_length_m_canonical != self.physical_identity.effective_length_m_canonical:
            errors.append("effective_length_m_canonical mismatch with physical_identity")

        # evaluation_order_index >= -1
        if self.evaluation_order_index < -1:
            errors.append(
                f"evaluation_order_index must be >= -1, got {self.evaluation_order_index}"
            )

        if errors:
            raise ValueError("; ".join(errors))
        return self


# ---------------------------------------------------------------------------
# Deduplication and ordering
# ---------------------------------------------------------------------------


def deduplicate_and_order_candidates(
    candidates: tuple[ManufacturableCandidate, ...],
) -> tuple[ManufacturableCandidate, ...]:
    """Deduplicate by ``source_qualified_candidate_id`` and sort by ID.

    Returns a new tuple with deduplicated, canonically ordered
    candidates.  ``evaluation_order_index`` is reassigned to
    0..N-1 in sort order.
    """
    seen: dict[str, ManufacturableCandidate] = {}
    for c in candidates:
        key = c.source_qualified_candidate_id
        if key not in seen:
            seen[key] = c

    sorted_candidates = tuple(sorted(seen.values(), key=lambda c: c.source_qualified_candidate_id))
    # Reassign evaluation order indices
    return tuple(
        c.model_copy(update={"evaluation_order_index": i}) for i, c in enumerate(sorted_candidates)
    )


# ---------------------------------------------------------------------------
# Factory: build candidate from source option + length
# ---------------------------------------------------------------------------


def build_candidate(
    catalog: CompleteDoublePipeCatalogSnapshot,
    option: CompleteDoublePipeAssemblyOption,
    effective_length_m_canonical: str,
    evaluation_order_index: int = -1,
) -> ManufacturableCandidate:
    """Build a single ``ManufacturableCandidate`` from its constituents."""
    physical = PhysicalCandidateIdentity(
        inner_tube_inner_diameter_m=option.inner_tube_inner_diameter_m,
        inner_tube_outer_diameter_m=option.inner_tube_outer_diameter_m,
        outer_pipe_inner_diameter_m=option.outer_pipe_inner_diameter_m,
        effective_length_m_canonical=effective_length_m_canonical,
        wall_thermal_conductivity_w_m_k=option.wall_thermal_conductivity_w_m_k,
        inner_surface_roughness_m=option.inner_surface_roughness_m,
        annulus_surface_roughness_m=option.annulus_surface_roughness_m,
        inner_fouling_resistance_m2k_w=option.inner_fouling_resistance_m2k_w,
        outer_fouling_resistance_m2k_w=option.outer_fouling_resistance_m2k_w,
    )
    p_digest = physical.physical_identity_digest

    sq = SourceQualifiedCandidateIdentity(
        physical_identity_digest=p_digest,
        catalog_id=catalog.catalog_id,
        catalog_version=catalog.catalog_version,
        catalog_content_hash=catalog.catalog_content_hash,
        assembly_option_id=option.assembly_option_id,
        manufacturing_option_identity=option.manufacturing_option_identity,
    )
    sq_id = sq.source_qualified_candidate_id

    return ManufacturableCandidate(
        physical_identity=physical,
        physical_identity_digest=p_digest,
        source_qualified_identity=sq,
        source_qualified_candidate_id=sq_id,
        catalog_snapshot_ref=catalog_snapshot_ref(catalog),
        assembly_option_id=option.assembly_option_id,
        manufacturing_option_identity=option.manufacturing_option_identity,
        manufacturing_metadata=option.manufacturing_metadata,
        effective_length_m_canonical=effective_length_m_canonical,
        evaluation_order_index=evaluation_order_index,
    )


# ---------------------------------------------------------------------------
# ReplayedMaterialization and replay function
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ReplayedMaterialization:
    """Result of replaying materialization from source artifacts."""

    replayed_candidates: tuple[ManufacturableCandidate, ...]
    replayed_catalog_snapshot_identities: tuple[CatalogSnapshotRef, ...]
    replayed_raw_combination_count: int
    replayed_unique_candidate_count: int
    replayed_ordered_candidate_ids: tuple[str, ...]


def _replay_materialization(
    *,
    catalogs: tuple[CompleteDoublePipeCatalogSnapshot, ...],
    sizing_gate: PassedSizingGate,
    minimum_effective_length_m: float | None,
    maximum_effective_length_m: float | None,
) -> ReplayedMaterialization:
    """Pure function that replays the full materialization pipeline.

    1. Verifies catalog content hashes (recomputes each)
    2. Confirms canonical catalog order
    3. Matches gate records to catalog options (7-field key)
    4. Materializes lengths per option with bounds
    5. Builds candidates
    6. Deduplicates and orders
    """
    errors: list[str] = []

    # Step 1: Recompute catalog content hashes
    for cat in catalogs:
        expected_hash = compute_catalog_content_hash(
            catalog_id=cat.catalog_id,
            catalog_version=cat.catalog_version,
            source_identity=cat.source_identity,
            schema_version=cat.schema_version,
            assembly_options=cat.assembly_options,
        )
        if expected_hash != cat.catalog_content_hash:
            errors.append(
                f"Catalog {cat.catalog_id}: recomputed hash {expected_hash} "
                f"!= stored {cat.catalog_content_hash}"
            )

    if errors:
        raise ValueError("Catalog hash verification failed:\n  - " + "\n  - ".join(errors))

    # Step 2: Build catalog refs in canonical order
    sorted_catalogs = tuple(sorted(catalogs, key=catalog_identity_key))
    replayed_refs = tuple(catalog_snapshot_ref(cat) for cat in sorted_catalogs)

    # Step 3: Build gate record lookup (7-field key)
    record_map: dict[tuple[str, str, str, str, str, str, str], OptionRawCountRecord] = {}
    for rec in sizing_gate.per_option_records:
        key = option_raw_count_record_identity_key(rec)
        if key in record_map:
            errors.append(f"Duplicate gate record key: {key}")
        record_map[key] = rec

    if errors:
        raise ValueError("; ".join(errors))

    # Step 4 & 5: Materialize lengths and build candidates
    all_candidates: list[ManufacturableCandidate] = []
    total_materialized = 0

    for cat in sorted_catalogs:
        for opt in cat.assembly_options:
            quantum = canonicalize_length_quantum(opt.length_source.length_quantum_m)
            lookup_record = OptionRawCountRecord(
                catalog_id=cat.catalog_id,
                catalog_version=cat.catalog_version,
                catalog_content_hash=cat.catalog_content_hash,
                source_identity=cat.source_identity,
                schema_version=cat.schema_version,
                assembly_option_id=opt.assembly_option_id,
                canonical_length_quantum_m=quantum,
                raw_count=0,
            )
            lookup_key = option_raw_count_record_identity_key(lookup_record)

            try:
                rec = record_map.pop(lookup_key)
            except KeyError:
                errors.append(f"Missing gate record: {lookup_key}")
                continue

            lengths = materialize_lengths_for_option(
                opt,
                minimum_effective_length_m=minimum_effective_length_m,
                maximum_effective_length_m=maximum_effective_length_m,
            )

            if len(lengths) != rec.raw_count:
                errors.append(
                    f"Option {opt.assembly_option_id}: materialized {len(lengths)} "
                    f"!= expected {rec.raw_count}"
                )

            for length_str in lengths:
                all_candidates.append(build_candidate(cat, opt, length_str))
            total_materialized += len(lengths)

    if record_map:
        unconsumed = sorted(record_map.keys())
        errors.append(f"Unconsumed gate records: {unconsumed}")

    if errors:
        raise ValueError("Materialization replay failed:\n  - " + "\n  - ".join(errors))

    # Step 6: Deduplicate and order
    deduped = deduplicate_and_order_candidates(tuple(all_candidates))

    return ReplayedMaterialization(
        replayed_candidates=deduped,
        replayed_catalog_snapshot_identities=replayed_refs,
        replayed_raw_combination_count=total_materialized,
        replayed_unique_candidate_count=len(deduped),
        replayed_ordered_candidate_ids=tuple(c.source_qualified_candidate_id for c in deduped),
    )


# ---------------------------------------------------------------------------
# MaterializationResult — binds candidates + MaterializedCandidateSet
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class MaterializationResult:
    """Bundled result of materialize_all_candidates().

    ``candidates``, ``candidate_set``, ``sizing_gate``, and
    ``catalog_snapshots`` are bound together at construction time and
    cannot be separately provided later.

    Construction requires the module-private ``_MATERIALIZATION_TOKEN``
    as an accidental-misuse guard — it is not a security or provenance
    boundary.  Full semantic validation is performed in ``_validate()``
    to ensure candidates-to-set-and-gate invariants hold.

    Use ``verify_or_raise()`` before any TASK-008 evaluation to
    confirm full provenance verification of the materialization result.
    """

    candidates: tuple[ManufacturableCandidate, ...]
    candidate_set: MaterializedCandidateSet
    sizing_gate: PassedSizingGate  # P0-5: full gate binding
    catalog_snapshots: tuple[CompleteDoublePipeCatalogSnapshot, ...]
    minimum_effective_length_m: float | None = None
    maximum_effective_length_m: float | None = None

    def __init__(
        self,
        *,
        candidates: tuple[ManufacturableCandidate, ...],
        candidate_set: MaterializedCandidateSet,
        sizing_gate: PassedSizingGate,
        catalog_snapshots: tuple[CompleteDoublePipeCatalogSnapshot, ...],
        minimum_effective_length_m: float | None = None,
        maximum_effective_length_m: float | None = None,
        _token: object,
    ) -> None:
        if _token is not _MATERIALIZATION_TOKEN:
            raise TypeError("MaterializationResult must be created by materialize_all_candidates()")
        # Use object.__setattr__ to bypass frozen dataclass
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "candidate_set", candidate_set)
        object.__setattr__(self, "sizing_gate", sizing_gate)
        object.__setattr__(self, "catalog_snapshots", catalog_snapshots)
        object.__setattr__(self, "minimum_effective_length_m", minimum_effective_length_m)
        object.__setattr__(self, "maximum_effective_length_m", maximum_effective_length_m)
        self._validate()

    def _validate(self) -> None:
        """Validate invariants at construction (P0-12 — full semantic validation)."""
        errors: list[str] = []

        # unique_candidate_count == len(candidates)
        if self.candidate_set.unique_candidate_count != len(self.candidates):
            errors.append(
                f"unique_candidate_count ({self.candidate_set.unique_candidate_count}) "
                f"!= len(candidates) ({len(self.candidates)})"
            )

        # ordered_candidate_ids == tuple(candidate IDs)
        actual_ids = tuple(c.source_qualified_candidate_id for c in self.candidates)
        if self.candidate_set.ordered_candidate_ids != actual_ids:
            errors.append(
                f"ordered_candidate_ids mismatch: "
                f"expected {self.candidate_set.ordered_candidate_ids}, "
                f"got {actual_ids}"
            )

        # evaluation_order_index == 0..N-1
        for i, c in enumerate(self.candidates):
            if c.evaluation_order_index != i:
                errors.append(
                    f"candidate[{i}] evaluation_order_index={c.evaluation_order_index} != {i}"
                )

        # No duplicate candidate IDs
        seen_ids_set: set[str] = set()
        for c in self.candidates:
            sqid = c.source_qualified_candidate_id
            if sqid in seen_ids_set:
                errors.append(f"Duplicate candidate ID: {sqid}")
            seen_ids_set.add(sqid)

        # Candidate IDs canonical sorted
        if tuple(self.candidate_set.ordered_candidate_ids) != tuple(
            sorted(self.candidate_set.ordered_candidate_ids)
        ):
            errors.append("candidate IDs not in canonical sorted order")

        # candidate_set.verify_digest() must be True (P0-12)
        if not self.candidate_set.verify_digest():
            errors.append("candidate_set.verify_digest() returned False")

        # Every candidate's catalog_snapshot_ref must appear in candidate_set refs
        set_refs = {
            (
                ref.catalog_id,
                ref.catalog_version,
                ref.catalog_content_hash,
                ref.source_identity,
                ref.schema_version,
            )
            for ref in self.candidate_set.catalog_snapshot_identities
        }
        for c in self.candidates:
            ref = c.catalog_snapshot_ref
            ref_key = (
                ref.catalog_id,
                ref.catalog_version,
                ref.catalog_content_hash,
                ref.source_identity,
                ref.schema_version,
            )
            if ref_key not in set_refs:
                errors.append(
                    f"candidate {c.source_qualified_candidate_id!r}: "
                    f"catalog ref {ref_key} not found in candidate_set refs"
                )

        # raw_combination_count >= unique candidate count (gate invariant)
        if self.candidate_set.raw_combination_count < self.candidate_set.unique_candidate_count:
            errors.append(
                f"raw_combination_count ({self.candidate_set.raw_combination_count}) < "
                f"unique_candidate_count ({self.candidate_set.unique_candidate_count})"
            )

        # Each candidate must have valid source/schema fields matching candidate_set
        for c in self.candidates:
            ref = c.catalog_snapshot_ref
            if not ref.source_identity:
                errors.append(
                    f"candidate {c.source_qualified_candidate_id!r}: source_identity is empty"
                )
            if not ref.schema_version:
                errors.append(
                    f"candidate {c.source_qualified_candidate_id!r}: schema_version is empty"
                )

        # NEW: Gate binding checks (P0-5)
        if not self.sizing_gate.verify_digest():
            errors.append("sizing_gate.verify_digest() returned False")
        if (
            self.sizing_gate.sizing_request_identity_digest
            != self.candidate_set.sizing_request_identity_digest
        ):
            errors.append(
                "gate sizing_request_identity_digest"
                " != candidate_set sizing_request_identity_digest"
            )
        if self.sizing_gate.raw_combination_count != self.candidate_set.raw_combination_count:
            errors.append("gate raw_combination_count != candidate_set raw_combination_count")
        if self.sizing_gate.gate_digest != self.candidate_set.passed_gate_digest:
            errors.append("gate.gate_digest != candidate_set.passed_gate_digest")

        # P0-5: Gate catalog refs must exactly match candidate_set catalog refs
        gate_catalog_keys: set[tuple[str, str, str, str, str]] = set()
        for rec in self.sizing_gate.per_option_records:
            key = (
                rec.catalog_id,
                rec.catalog_version,
                rec.catalog_content_hash,
                rec.source_identity,
                rec.schema_version,
            )
            gate_catalog_keys.add(key)

        set_catalog_keys: set[tuple[str, str, str, str, str]] = set()
        for ref in self.candidate_set.catalog_snapshot_identities:
            key = (
                ref.catalog_id,
                ref.catalog_version,
                ref.catalog_content_hash,
                ref.source_identity,
                ref.schema_version,
            )
            set_catalog_keys.add(key)

        if gate_catalog_keys != set_catalog_keys:
            errors.append(
                f"Gate catalog keys {gate_catalog_keys} != "
                f"candidate_set catalog keys {set_catalog_keys}"
            )

        # P0-5: Each candidate must match a gate per-option record
        gate_option_keys: set[tuple[str, str, str, str, str, str]] = set()
        for rec in self.sizing_gate.per_option_records:
            opt_key = (
                rec.catalog_id,
                rec.catalog_version,
                rec.catalog_content_hash,
                rec.source_identity,
                rec.schema_version,
                rec.assembly_option_id,
            )
            gate_option_keys.add(opt_key)

        for c in self.candidates:
            ref = c.catalog_snapshot_ref
            cand_key = (
                ref.catalog_id,
                ref.catalog_version,
                ref.catalog_content_hash,
                ref.source_identity,
                ref.schema_version,
                c.assembly_option_id,
            )
            if cand_key not in gate_option_keys:
                errors.append(
                    f"Candidate {c.source_qualified_candidate_id!r}: "
                    f"option key {cand_key} not found in gate records"
                )

        if errors:
            raise ValueError("; ".join(errors))

    def verify_or_raise(self) -> None:
        """Full provenance verification of the materialization result.

        1. Gate self-verification (BEFORE replay)
        2. Gate→candidate-set digest chain
        3. Gate aggregate raw-count consistency
        4. Candidate-set self-verification
        5. Replay materialization from source artifacts
        6. Replay → candidate_set binding
        7. Full candidate model revalidation

        Must be called before any TASK-008 evaluation.
        """
        errors: list[str] = []

        # 1. Gate self-verification (BEFORE replay)
        if not self.sizing_gate.verify_digest():
            errors.append("sizing_gate.verify_digest() failed")

        # 2. Gate→candidate-set digest chain
        if self.sizing_gate.gate_digest != self.candidate_set.passed_gate_digest:
            errors.append("gate.gate_digest != candidate_set.passed_gate_digest")
        if (
            self.sizing_gate.sizing_request_identity_digest
            != self.candidate_set.sizing_request_identity_digest
        ):
            errors.append("gate sizing_request_identity_digest != candidate_set")

        # 3. Gate aggregate raw-count consistency
        per_option_sum = sum(r.raw_count for r in self.sizing_gate.per_option_records)
        if per_option_sum != self.sizing_gate.raw_combination_count:
            errors.append(
                f"gate per-option sum ({per_option_sum}) "
                f"!= gate.raw_combination_count ({self.sizing_gate.raw_combination_count})"
            )

        # 4. Candidate-set self-verification
        if not self.candidate_set.verify_digest():
            errors.append("candidate_set.verify_digest() failed")

        # P0-5: Bounds cross-check — materialization result bounds must match candidate_set
        if self.minimum_effective_length_m != self.candidate_set.minimum_effective_length_m:
            errors.append(
                f"MaterializationResult minimum_effective_length_m "
                f"({self.minimum_effective_length_m}) != "
                f"candidate_set ({self.candidate_set.minimum_effective_length_m})"
            )
        if self.maximum_effective_length_m != self.candidate_set.maximum_effective_length_m:
            errors.append(
                f"MaterializationResult maximum_effective_length_m "
                f"({self.maximum_effective_length_m}) != "
                f"candidate_set ({self.candidate_set.maximum_effective_length_m})"
            )

        if errors:
            raise ValueError(
                "MaterializationResult verification failed:\n  - " + "\n  - ".join(errors)
            )

        # 5. Replay materialization from source artifacts
        try:
            replay = _replay_materialization(
                catalogs=self.catalog_snapshots,
                sizing_gate=self.sizing_gate,
                minimum_effective_length_m=self.minimum_effective_length_m,
                maximum_effective_length_m=self.maximum_effective_length_m,
            )
        except ValueError as exc:
            raise ValueError(
                f"MaterializationResult verification failed: replay error: {exc}"
            ) from exc

        # 6. Replay → candidate_set binding
        self._compare_replay_to_set(replay, errors)

        # 7. Full candidate model comparison
        self._compare_replay_candidates(replay, errors)

        if errors:
            raise ValueError(
                "MaterializationResult verification failed:\n  - " + "\n  - ".join(errors)
            )

    def _compare_replay_to_set(
        self,
        replay: ReplayedMaterialization,
        errors: list[str],
    ) -> None:
        """Compare replay results with stored candidate_set."""
        if (
            replay.replayed_catalog_snapshot_identities
            != self.candidate_set.catalog_snapshot_identities
        ):
            errors.append(
                "replayed catalog identities != candidate_set.catalog_snapshot_identities"
            )

        if replay.replayed_raw_combination_count != self.candidate_set.raw_combination_count:
            errors.append(
                f"replayed raw_count {replay.replayed_raw_combination_count} "
                f"!= candidate_set {self.candidate_set.raw_combination_count}"
            )

        if replay.replayed_raw_combination_count != self.sizing_gate.raw_combination_count:
            errors.append(
                f"replayed raw_count {replay.replayed_raw_combination_count} "
                f"!= gate {self.sizing_gate.raw_combination_count}"
            )

        if replay.replayed_unique_candidate_count != self.candidate_set.unique_candidate_count:
            errors.append(
                f"replayed unique count {replay.replayed_unique_candidate_count} "
                f"!= candidate_set {self.candidate_set.unique_candidate_count}"
            )

        if replay.replayed_ordered_candidate_ids != self.candidate_set.ordered_candidate_ids:
            errors.append("replayed ordered IDs != candidate_set.ordered_candidate_ids")

    def _compare_replay_candidates(
        self,
        replay: ReplayedMaterialization,
        errors: list[str],
    ) -> None:
        """Re-validate stored candidates and compare full models with replay."""
        # Re-validate each stored candidate through model_validate
        validated_stored: list[ManufacturableCandidate] = []
        for i, c in enumerate(self.candidates):
            try:
                validated = ManufacturableCandidate.model_validate(c.model_dump(mode="python"))
                validated_stored.append(validated)
            except Exception as exc:
                errors.append(f"stored candidate[{i}] model_validate failed: {exc}")
                return  # cannot continue comparison

        if len(validated_stored) != len(replay.replayed_candidates):
            errors.append(
                f"candidate count: stored {len(validated_stored)} "
                f"!= replayed {len(replay.replayed_candidates)}"
            )
            return

        for i, (stored, replayed) in enumerate(
            zip(validated_stored, replay.replayed_candidates, strict=True)
        ):
            # Full model equality
            if stored != replayed:
                # Diagnose specific field mismatches
                if stored.source_qualified_candidate_id != replayed.source_qualified_candidate_id:
                    errors.append(
                        f"candidate[{i}] ID mismatch: "
                        f"{stored.source_qualified_candidate_id} "
                        f"!= {replayed.source_qualified_candidate_id}"
                    )
                elif stored.physical_identity_digest != replayed.physical_identity_digest:
                    errors.append(f"candidate[{i}] physical digest mismatch")
                elif stored.effective_length_m_canonical != replayed.effective_length_m_canonical:
                    errors.append(
                        f"candidate[{i}] length: "
                        f"{stored.effective_length_m_canonical} "
                        f"!= {replayed.effective_length_m_canonical}"
                    )
                elif stored.manufacturing_option_identity != replayed.manufacturing_option_identity:
                    errors.append(f"candidate[{i}] manufacturing identity mismatch")
                elif stored.manufacturing_metadata != replayed.manufacturing_metadata:
                    errors.append(f"candidate[{i}] manufacturing metadata mismatch")
                elif stored.assembly_option_id != replayed.assembly_option_id:
                    errors.append(f"candidate[{i}] assembly_option_id mismatch")
                elif stored.catalog_snapshot_ref != replayed.catalog_snapshot_ref:
                    errors.append(f"candidate[{i}] catalog_snapshot_ref mismatch")
                elif stored.physical_identity != replayed.physical_identity:
                    errors.append(f"candidate[{i}] physical_identity mismatch")
                elif stored.evaluation_order_index != replayed.evaluation_order_index:
                    errors.append(
                        f"candidate[{i}] order_index: "
                        f"{stored.evaluation_order_index} "
                        f"!= {replayed.evaluation_order_index}"
                    )
                else:
                    errors.append(f"candidate[{i}] model mismatch (unexpected field)")


# ---------------------------------------------------------------------------
# Materialize all candidates for a request (aggregate pipeline step)
# ---------------------------------------------------------------------------


def materialize_all_candidates(
    catalogs: tuple[CompleteDoublePipeCatalogSnapshot, ...],
    sizing_gate: PassedSizingGate,
    minimum_effective_length_m: float | None = None,
    maximum_effective_length_m: float | None = None,
) -> MaterializationResult:
    """Materialise and deduplicate all candidates for a sizing request.

    ``sizing_request_identity_digest`` is taken strictly from
    ``sizing_gate.sizing_request_identity_digest`` — the caller cannot
    supply a separate digest (P0-1).
    """
    # --- P0-1: verify gate digest before consuming any records ---
    if not sizing_gate.verify_digest():
        raise ValueError("PassedSizingGate digest verification failed")

    # Replay using the pure replay function
    replay = _replay_materialization(
        catalogs=catalogs,
        sizing_gate=sizing_gate,
        minimum_effective_length_m=minimum_effective_length_m,
        maximum_effective_length_m=maximum_effective_length_m,
    )

    # Build candidate_set from replayed data
    sorted_catalogs = tuple(sorted(catalogs, key=catalog_identity_key))
    catalog_snapshot_identities = tuple(catalog_snapshot_ref(cat) for cat in sorted_catalogs)

    candidate_set = _create_materialized_candidate_set(
        sizing_request_identity_digest=sizing_gate.sizing_request_identity_digest,
        passed_gate_digest=sizing_gate.gate_digest,
        catalog_snapshot_identities=catalog_snapshot_identities,
        minimum_effective_length_m=minimum_effective_length_m,
        maximum_effective_length_m=maximum_effective_length_m,
        raw_combination_count=sizing_gate.raw_combination_count,
        ordered_candidates=replay.replayed_candidates,
    )

    return MaterializationResult(
        candidates=replay.replayed_candidates,
        candidate_set=candidate_set,
        sizing_gate=sizing_gate,
        catalog_snapshots=catalogs,
        minimum_effective_length_m=minimum_effective_length_m,
        maximum_effective_length_m=maximum_effective_length_m,
        _token=_MATERIALIZATION_TOKEN,
    )


__all__ = [
    "MaterializationResult",
    "PhysicalCandidateIdentity",
    "ReplayedMaterialization",
    "SourceQualifiedCandidateIdentity",
    "ManufacturableCandidate",
    "build_candidate",
    "catalog_snapshot_ref",
    "deduplicate_and_order_candidates",
    "materialize_all_candidates",
]
