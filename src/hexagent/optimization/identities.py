"""
TASK-009 Phase 2 — candidate identity models for physical and
source-qualified candidate deduplication and ordering.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from hexagent.core.canonical import sha256_digest
from hexagent.optimization.models import (
    CatalogSnapshotRef,
    CompleteDoublePipeAssemblyOption,
    CompleteDoublePipeCatalogSnapshot,
    OptionRawCountRecord,
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
        # First occurrence wins (deterministic — we process in input order,
        # but sort afterwards anyway)
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
# Materialize all candidates for a request (aggregate pipeline step)
# ---------------------------------------------------------------------------


def materialize_all_candidates(
    catalogs: tuple[CompleteDoublePipeCatalogSnapshot, ...],
    per_option_records: tuple[OptionRawCountRecord, ...],
    minimum_effective_length_m: float | None = None,
    maximum_effective_length_m: float | None = None,
) -> tuple[ManufacturableCandidate, ...]:
    """Materialise and deduplicate all candidates for a sizing request.

    This is the Phase 2 pipeline entry-point after the cap gate passes.
    """
    from hexagent.optimization.materialization import materialize_lengths_for_option

    all_candidates: list[ManufacturableCandidate] = []

    for cat in catalogs:
        for opt in cat.assembly_options:
            lengths = materialize_lengths_for_option(
                opt,
                minimum_effective_length_m=minimum_effective_length_m,
                maximum_effective_length_m=maximum_effective_length_m,
            )
            for length_str in lengths:
                all_candidates.append(build_candidate(cat, opt, length_str))

    return deduplicate_and_order_candidates(tuple(all_candidates))


__all__ = [
    "PhysicalCandidateIdentity",
    "SourceQualifiedCandidateIdentity",
    "ManufacturableCandidate",
    "build_candidate",
    "catalog_snapshot_ref",
    "deduplicate_and_order_candidates",
    "materialize_all_candidates",
]
