"""GEOMETRY_IDENTITY_V2 for V08 experimental geometry deduplication (V1 hash unchanged)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.bell_delaware.models import Task166Result
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import CandidateSpec
from prototypes.v08_geometry_candidate_generation.discrete_space import format_engineering_decimal
from prototypes.v08_geometry_candidate_generation.generator import _geometry_projection_hash
from prototypes.v08_geometry_candidate_generation.structural_bundles import (
    V08StructuralGeometryBundle,
)


@dataclass(frozen=True)
class ResolvedBaffleAuthority:
    spec_baffle_count: int
    baffle_hole_position_count: int
    task166_baffle_count: int | None
    baffle_count_authoritative: int
    cross_check_ok: bool


def resolve_baffle_authority(*, candidate: CandidateSpec, bundle: Any) -> ResolvedBaffleAuthority:
    """Authoritative baffle count is CandidateSpec; position_count is tube-hole layout only."""
    t024 = bundle.task024_geometry
    hole_positions = int(t024.position_count)
    spec_count = int(candidate.baffle_count)
    bell_count: int | None = None
    t166 = getattr(bundle, "task166_result", None)
    if isinstance(t166, Task166Result) and t166.bell_geometry is not None:
        bell_count = int(t166.bell_geometry.baffle_count)
    cross_ok = bell_count is None or bell_count == spec_count
    return ResolvedBaffleAuthority(
        spec_baffle_count=spec_count,
        baffle_hole_position_count=hole_positions,
        task166_baffle_count=bell_count,
        baffle_count_authoritative=spec_count,
        cross_check_ok=cross_ok,
    )


def _shell_clearances(bundle: Any, t166: object | None) -> dict[str, str]:
    t022 = getattr(bundle, "task022_geometry", None)
    out: dict[str, str] = {}
    if t022 is not None:
        for attr in (
            "bundle_outer_envelope_diameter_m",
            "shell_to_bundle_diametral_clearance_m",
            "shell_to_baffle_diametral_clearance_m",
        ):
            if hasattr(t022, attr):
                out[attr] = str(getattr(t022, attr))
    if isinstance(t166, Task166Result) and t166.bell_geometry is not None:
        bell = t166.bell_geometry
        out["bell_bundle_outer_diameter_m"] = str(bell.bundle_outer_diameter_m)
        out["bell_shell_to_bundle_diametral_clearance_m"] = str(
            bell.shell_to_bundle_diametral_clearance_m
        )
        out["bell_shell_to_baffle_diametral_clearance_m"] = str(
            bell.shell_to_baffle_diametral_clearance_m
        )
    return out


def authoritative_baffle_cut_fraction(*, candidate: CandidateSpec, bundle: Any) -> str:
    """Baffle cut from CandidateSpec, cross-checked against Task024 when present."""
    spec_cut = format_engineering_decimal(candidate.baffle_cut_fraction)
    t024 = bundle.task024_geometry
    da = getattr(t024, "design_authority", None)
    if da is not None:
        t024_cut = str(getattr(da, "baffle_cut_fraction", "")).strip()
        if t024_cut and format_engineering_decimal(Decimal(t024_cut)) != spec_cut:
            raise ValueError(
                f"baffle_cut mismatch: candidate={spec_cut} task024.design_authority={t024_cut}"
            )
    t166 = getattr(bundle, "task166_result", None)
    if isinstance(t166, Task166Result) and t166.bell_geometry is not None:
        bell_cut = format_engineering_decimal(t166.bell_geometry.baffle_cut_fraction)
        if bell_cut != spec_cut:
            raise ValueError(f"baffle_cut mismatch: candidate={spec_cut} task166.bell={bell_cut}")
    return spec_cut


def geometry_identity_v2_hash(bundle: V08StructuralGeometryBundle) -> str:
    """Deterministic V2 identity including baffle cut/count/type and layout hash."""
    candidate = bundle.candidate
    raw = bundle.bundle
    layout = raw.task021_layout
    t024 = raw.task024_geometry
    shell_id = str(bundle.shell_record.shell_inside_diameter_m)
    cut = authoritative_baffle_cut_fraction(candidate=candidate, bundle=raw)
    baffle = resolve_baffle_authority(candidate=candidate, bundle=raw)
    clearances = _shell_clearances(raw, getattr(raw, "task166_result", None))
    payload: dict[str, str] = {
        "schema": "hxforge.geometry-identity.v2",
        "shell_inside_diameter_m": shell_id,
        "tube_outer_diameter_m": format_engineering_decimal(candidate.tube_outer_diameter_m),
        "tube_wall_thickness_m": format_engineering_decimal(candidate.tube_wall_thickness_m),
        "tube_pitch_m": format_engineering_decimal(candidate.tube_pitch_m),
        "tube_layout_id": str(getattr(layout, "layout_id", "")),
        "tube_layout_hash": str(getattr(layout, "layout_hash", "")),
        "tube_pass_count": str(int(candidate.tube_pass_count)),
        "physical_tube_count": str(int(layout.physical_tube_count)),
        "tube_length_m": format_engineering_decimal(candidate.tube_length_m),
        "baffle_type": str(candidate.baffle_type),
        "baffle_cut_fraction": cut,
        "baffle_count": str(baffle.baffle_count_authoritative),
        "baffle_hole_position_count": str(baffle.baffle_hole_position_count),
        "baffle_spacing_m": format_engineering_decimal(candidate.baffle_spacing_m),
        "task024_geometry_hash": str(getattr(t024, "geometry_hash", "")),
    }
    for key, value in sorted(clearances.items()):
        payload[f"clearance.{key}"] = value
    return canonical_sha256(payload)


def geometry_projection_hash_v1(bundle: V08StructuralGeometryBundle) -> str:
    """Legacy V1 projection (R1 published compatibility)."""
    candidate = bundle.candidate
    layout = bundle.bundle.task021_layout
    return _geometry_projection_hash(
        shell_inside_diameter_m=str(bundle.shell_record.shell_inside_diameter_m),
        tube_length_m=format_engineering_decimal(candidate.tube_length_m),
        baffle_spacing_m=format_engineering_decimal(candidate.baffle_spacing_m),
        tube_pass_count=int(candidate.tube_pass_count),
        physical_tube_count=int(layout.physical_tube_count),
    )


def legacy_geometry_projection_aliases(
    entries: tuple[tuple[str, str], ...],
) -> frozenset[str]:
    """V1 hashes that map to more than one distinct V2 hash → LEGACY_GEOMETRY_PROJECTION_ALIAS."""
    by_v1: dict[str, set[str]] = {}
    for v1, v2 in entries:
        by_v1.setdefault(v1, set()).add(v2)
    return frozenset(h for h, v2s in by_v1.items() if len(v2s) > 1)


def sample_v2_cut_distinctness(
    bundle_a: V08StructuralGeometryBundle,
    bundle_b: V08StructuralGeometryBundle,
) -> tuple[str, str]:
    """Return V2 hashes for two bundles with different authoritative baffle cuts."""
    return geometry_identity_v2_hash(bundle_a), geometry_identity_v2_hash(bundle_b)


__all__ = [
    "ResolvedBaffleAuthority",
    "authoritative_baffle_cut_fraction",
    "geometry_identity_v2_hash",
    "geometry_projection_hash_v1",
    "legacy_geometry_projection_aliases",
    "resolve_baffle_authority",
    "sample_v2_cut_distinctness",
]
