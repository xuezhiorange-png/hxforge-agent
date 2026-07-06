"""TASK-017 Slice C — PreliminaryMechanicalChecker (allowable-stress check).

Implements the TASK-017 frozen design contract
(docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md,
Frozen Contract Authority Commit SHA
``6ed5b7dc7d8df163796eacb838afcf5702a4c53a``,
Frozen Contract Authority Base SHA
``fbb05ae71f21e6cfd4d1041afb5958c863166248``) for the
PreliminaryMechanicalChecker's allowable-stress screening check
(design §9.1 + §7 codes 11-13 + §8 provenance + §10.3 +
§10.4).

Slice C scope is the allowable-stress check ONLY per planning
doc §3. Slice D will extend this module with the minimum-wall
check (§9.2) and the straight-pipe span check (§9.3); Slice C
MUST NOT implement those.

Slice C is a READ-ONLY consumer of the Slice A
MaterialResolutionResult. It does NOT mutate TASK-013 material
records, does NOT mutate TASK-016 geometry records, does NOT
introduce pressure-drop / C4 / cost / new-solver logic, and does
NOT escalate to detailed mechanical design.

Slice C NEVER references Slice D / Closeout tokens.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any, Final, Literal

from hexagent.canonical_json import canonical_json_bytes
from hexagent.material_mass_mechanical.material_selector import (
    MaterialResolutionResult,
    MaterialSelectorError,
)

# ── Software provenance constants (per §8) ────────────────────────────
_SOFTWARE_VERSION: Final[str] = "task-017-slice-c-v0.1.0"
_GIT_COMMIT: Final[str] = "see task-017 implementation head"

# Decimal 6dp quantizer per §10.3.
_DECIMAL_QUANTUM: Final[Decimal] = Decimal("0.000001")

# ── Preliminary envelope constants (per §9.1 envelope rule) ──────────
# Geometry outside this envelope returns BLOCKED_FOR_DETAILED_DESIGN.
PRELIMINARY_ENVELOPE_MAX_DIAMETER_M: Final[Decimal] = Decimal("1.0")

# ── §9.1 Verdict thresholds ──────────────────────────────────────────
# PASS: hoop_stress <= 0.6 * allowable_stress
# MARGINAL: 0.6 * allowable < hoop_stress <= 0.8 * allowable
# BLOCKED_PRELIMINARY: hoop_stress > 0.8 * allowable
_THRESHOLD_PASS: Final[Decimal] = Decimal("0.6")
_THRESHOLD_MARGINAL: Final[Decimal] = Decimal("0.8")

# Verdict literals per design §9.1 — 4-tier screening verdict.
PreliminaryVerdict = Literal[
    "pass",
    "marginal",
    "blocked_preliminary",
    "blocked_for_detailed_design",
]

# Component roles that participate in the allowable-stress check
# (design §5.2.2: pressure-bearing metal components only).
SUPPORTED_MECHANICAL_ROLES: Final[frozenset[str]] = frozenset({"inner_tube", "outer_pipe"})
MECHANICAL_ROLES_FROZEN_ORDER: Final[tuple[str, ...]] = (
    "inner_tube",
    "outer_pipe",
)


# ── §7 Frozen error codes (codes 11-13, single source of truth) ───────
ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT: Final[str] = (
    "MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT"
)
ERROR_MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT: Final[str] = (
    "MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT"
)
ERROR_MECHANICAL_CHECK_UNSUPPORTED_ROLE: Final[str] = "MECHANICAL_CHECK_UNSUPPORTED_ROLE"


# ── §8 Provenance dataclass ──────────────────────────────────────────
@dataclass(frozen=True)
class PreliminaryCheckProvenance:
    """Audit provenance for a preliminary allowable-stress check (§8)."""

    material_record_id: str
    applicable_standard_id: str | None
    design_pressure_mpa: Decimal
    design_temperature_c: float
    correlation_ids: tuple[str, ...] = ()
    software_version: str = _SOFTWARE_VERSION
    git_commit: str = _GIT_COMMIT
    result_hash: str = ""
    outer_diameter_m: Decimal = Decimal("0")
    inner_diameter_m: Decimal = Decimal("0")
    wall_thickness_m: Decimal = Decimal("0")
    allowable_temperature_c: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Stable dict for serialization (§10.4 canonical-JSON)."""
        return {
            "material_record_id": self.material_record_id,
            "applicable_standard_id": self.applicable_standard_id,
            "design_pressure_mpa": _decimal_to_str(self.design_pressure_mpa),
            "design_temperature_c": float(self.design_temperature_c),
            "correlation_ids": list(self.correlation_ids),
            "software_version": self.software_version,
            "git_commit": self.git_commit,
            "result_hash": self.result_hash,
            "outer_diameter_m": _decimal_to_str(self.outer_diameter_m),
            "inner_diameter_m": _decimal_to_str(self.inner_diameter_m),
            "wall_thickness_m": _decimal_to_str(self.wall_thickness_m),
            "allowable_temperature_c": self.allowable_temperature_c,
        }


# ── §5.2.2 Request / Result dataclasses ──────────────────────────────
@dataclass(frozen=True)
class PreliminaryCheckRequest:
    """Request payload for a single component's allowable-stress check."""

    component_role: str
    material_resolution: MaterialResolutionResult
    design_pressure_mpa: Decimal
    design_temperature_c: float
    outer_diameter_m: Decimal
    inner_diameter_m: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.component_role, str):
            raise TypeError("component_role must be a str")
        if not isinstance(self.material_resolution, MaterialResolutionResult):
            raise TypeError("material_resolution must be a MaterialResolutionResult")
        if not isinstance(self.design_pressure_mpa, Decimal):
            raise TypeError("design_pressure_mpa must be a Decimal")
        if not isinstance(self.design_temperature_c, (int, float)):
            raise TypeError("design_temperature_c must be a number")
        if not isinstance(self.outer_diameter_m, Decimal):
            raise TypeError("outer_diameter_m must be a Decimal")
        if not isinstance(self.inner_diameter_m, Decimal):
            raise TypeError("inner_diameter_m must be a Decimal")


@dataclass(frozen=True)
class PreliminaryCheckResult:
    """Result of a single component's allowable-stress check (§9.1)."""

    component_role: str
    hoop_stress_mpa: Decimal
    allowable_stress_mpa: Decimal
    stress_utilization_ratio: Decimal
    verdict: PreliminaryVerdict
    provenance: PreliminaryCheckProvenance
    preliminary_check_result_hash: str

    def to_dict(self) -> dict[str, Any]:
        """Stable dict for serialization (§10.4 canonical-JSON)."""
        return {
            "component_role": self.component_role,
            "hoop_stress_mpa": _decimal_to_str(self.hoop_stress_mpa),
            "allowable_stress_mpa": _decimal_to_str(self.allowable_stress_mpa),
            "stress_utilization_ratio": _decimal_to_str(self.stress_utilization_ratio),
            "verdict": self.verdict,
            "provenance": self.provenance.to_dict(),
            "preliminary_check_result_hash": self.preliminary_check_result_hash,
        }


# ── Helpers ──────────────────────────────────────────────────────────
def _decimal_to_str(value: Decimal) -> str:
    """Decimal → stable str (avoids float repr drift)."""
    if not isinstance(value, Decimal):
        raise TypeError(f"expected Decimal, got {type(value).__name__}")
    return format(value, "f")


def _quantize_6dp(value: Decimal) -> Decimal:
    """Decimal 6dp quantization per §10.3."""
    return value.quantize(_DECIMAL_QUANTUM)


def _compute_result_hash(payload: dict[str, Any]) -> str:
    """SHA-256 hex digest over canonical JSON of payload (§10.4)."""
    encoded = canonical_json_bytes(payload)
    return hashlib.sha256(encoded).hexdigest()


def _resolve_allowable_stress(
    resolution: MaterialResolutionResult,
    design_temperature_c: float,
) -> tuple[Decimal, float]:
    """Look up allowable_stress at design_temperature_c (§9.1).

    Returns (allowable_stress_mpa, lookup_temperature_c). Raises
    MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT if the table is
    missing, empty, or has no entry at design_temperature_c.

    Per design §5.1.2 + §9.1: allowable_stress_mpa is a
    dict[float, float] keyed by °C. The selector MUST NOT perform
    interpolation or extrapolation (§5.1.2); so lookup is an exact
    key match.
    """
    table = resolution.allowable_stress_mpa
    if table is None or len(table) == 0:
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT,
            message=(
                "PreliminaryMechanicalChecker requires "
                "MaterialResolutionResult.allowable_stress_mpa to be a "
                "non-empty dict keyed by temperature_c; got "
                f"{'None' if table is None else 'empty dict'}."
            ),
            context={
                "material_record_id": resolution.material_record_id,
                "component_role": (resolution.material_grade),  # closest stable id from result
            },
        )
    if design_temperature_c not in table:
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT,
            message=(
                "PreliminaryMechanicalChecker requires exact-key lookup "
                "of allowable_stress_mpa at design_temperature_c; "
                f"design_temperature_c={design_temperature_c!r} not in "
                f"available keys {sorted(table.keys())!r}."
            ),
            context={
                "material_record_id": resolution.material_record_id,
                "design_temperature_c": design_temperature_c,
                "available_keys": sorted(table.keys()),
            },
        )
    value = table[design_temperature_c]
    return (Decimal(str(value)), design_temperature_c)


# ── §9.1 Allowable-stress check ──────────────────────────────────────
def preliminary_check(
    request: PreliminaryCheckRequest,
) -> PreliminaryCheckResult:
    """Run the §9.1 allowable-stress preliminary screening check.

    Implements design §9.1 (hoop stress σ = p·D/(2·t) compared
    against the allowable stress at design_temperature_c). Returns
    a 4-tier verdict: ``pass`` / ``marginal`` /
    ``blocked_preliminary`` / ``blocked_for_detailed_design``.

    Slice C is screening only — does NOT escalate to detailed
    mechanical design (§3.2).
    """
    # §5.2.2 closed-set guard: pressure-bearing metal components only
    if request.component_role not in SUPPORTED_MECHANICAL_ROLES:
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_UNSUPPORTED_ROLE,
            message=(
                f"PreliminaryMechanicalChecker does not support "
                f"component_role={request.component_role!r}; supported "
                f"roles are {sorted(SUPPORTED_MECHANICAL_ROLES)}."
            ),
            context={
                "component_role": request.component_role,
                "supported_roles": sorted(SUPPORTED_MECHANICAL_ROLES),
            },
        )

    # §7 input guard: pressure must be positive
    if request.design_pressure_mpa <= Decimal("0"):
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT,
            message=(
                "PreliminaryMechanicalChecker requires "
                "design_pressure_mpa > 0; got "
                f"{_decimal_to_str(request.design_pressure_mpa)}."
            ),
            context={
                "design_pressure_mpa": _decimal_to_str(request.design_pressure_mpa),
            },
        )

    # §9.1 envelope guard: diameter must be within preliminary envelope
    if request.outer_diameter_m > PRELIMINARY_ENVELOPE_MAX_DIAMETER_M:
        return _blocked_for_detailed_design_result(
            request=request,
            reason_diameter_m=request.outer_diameter_m,
            envelope_max_m=PRELIMINARY_ENVELOPE_MAX_DIAMETER_M,
        )

    # §7 input guard: outer diameter must be positive
    if request.outer_diameter_m <= Decimal("0"):
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT,
            message=(
                "PreliminaryMechanicalChecker requires outer_diameter_m > 0; "
                f"got {_decimal_to_str(request.outer_diameter_m)}."
            ),
            context={
                "outer_diameter_m": _decimal_to_str(request.outer_diameter_m),
            },
        )

    # §7 input guard: inner diameter must be ≥ 0 and < outer_diameter_m
    if request.inner_diameter_m < Decimal("0"):
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT,
            message=(
                "PreliminaryMechanicalChecker requires inner_diameter_m >= 0; "
                f"got {_decimal_to_str(request.inner_diameter_m)}."
            ),
            context={
                "inner_diameter_m": _decimal_to_str(request.inner_diameter_m),
            },
        )
    if request.inner_diameter_m >= request.outer_diameter_m:
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT,
            message=(
                "PreliminaryMechanicalChecker requires "
                "inner_diameter_m < outer_diameter_m; got "
                f"inner={_decimal_to_str(request.inner_diameter_m)}, "
                f"outer={_decimal_to_str(request.outer_diameter_m)}."
            ),
            context={
                "inner_diameter_m": _decimal_to_str(request.inner_diameter_m),
                "outer_diameter_m": _decimal_to_str(request.outer_diameter_m),
            },
        )

    # §9.1 wall thickness: t = (D_o − D_i) / 2 (thin-wall approx.)
    wall_thickness_m = (request.outer_diameter_m - request.inner_diameter_m) / Decimal("2")
    if wall_thickness_m <= Decimal("0"):
        # Defensive guard; the D_i < D_o check above already catches this.
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT,
            message=(
                "PreliminaryMechanicalChecker requires wall_thickness_m > 0; "
                f"got {_decimal_to_str(wall_thickness_m)}."
            ),
            context={
                "wall_thickness_m": _decimal_to_str(wall_thickness_m),
            },
        )

    # §9.1 hoop stress: σ = p·D/(2·t)
    hoop_stress_mpa_raw = (request.design_pressure_mpa * request.outer_diameter_m) / (
        Decimal("2") * wall_thickness_m
    )

    # §9.1 allowable stress lookup at design_temperature_c
    allowable_stress_mpa_raw, lookup_temperature_c = _resolve_allowable_stress(
        request.material_resolution,
        float(request.design_temperature_c),
    )
    if allowable_stress_mpa_raw <= Decimal("0"):
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT,
            message=(
                "PreliminaryMechanicalChecker requires "
                "allowable_stress_mpa > 0; got "
                f"{_decimal_to_str(allowable_stress_mpa_raw)}."
            ),
            context={
                "material_record_id": (request.material_resolution.material_record_id),
                "allowable_stress_mpa": _decimal_to_str(allowable_stress_mpa_raw),
            },
        )

    # §9.1 stress utilization ratio: hoop / allowable
    utilization_ratio_raw = hoop_stress_mpa_raw / allowable_stress_mpa_raw

    # §10.3 Decimal 6dp quantization
    hoop_stress_mpa = _quantize_6dp(hoop_stress_mpa_raw)
    allowable_stress_mpa = _quantize_6dp(allowable_stress_mpa_raw)
    utilization_ratio = _quantize_6dp(utilization_ratio_raw)

    # §9.1 verdict: 4-tier based on utilization ratio thresholds
    if utilization_ratio <= _THRESHOLD_PASS:
        verdict: PreliminaryVerdict = "pass"
    elif utilization_ratio <= _THRESHOLD_MARGINAL:
        verdict = "marginal"
    else:
        verdict = "blocked_preliminary"

    # §8 provenance assembly (result_hash placeholder, filled after hash)
    provenance = PreliminaryCheckProvenance(
        material_record_id=request.material_resolution.material_record_id,
        applicable_standard_id=(request.material_resolution.provenance.applicable_standard_id),
        design_pressure_mpa=_quantize_6dp(request.design_pressure_mpa),
        design_temperature_c=float(request.design_temperature_c),
        correlation_ids=(),
        software_version=_SOFTWARE_VERSION,
        git_commit=_GIT_COMMIT,
        result_hash="",  # placeholder, filled below
        outer_diameter_m=_quantize_6dp(request.outer_diameter_m),
        inner_diameter_m=_quantize_6dp(request.inner_diameter_m),
        wall_thickness_m=_quantize_6dp(wall_thickness_m),
        allowable_temperature_c=lookup_temperature_c,
    )

    # §10.4 hash over canonical JSON of result payload
    hash_payload = {
        "component_role": request.component_role,
        "hoop_stress_mpa": _decimal_to_str(hoop_stress_mpa),
        "allowable_stress_mpa": _decimal_to_str(allowable_stress_mpa),
        "stress_utilization_ratio": _decimal_to_str(utilization_ratio),
        "verdict": verdict,
        "provenance": provenance.to_dict(),
    }
    result_hash = _compute_result_hash(hash_payload)

    # Replace placeholder with actual hash in provenance
    provenance = replace(provenance, result_hash=result_hash)

    return PreliminaryCheckResult(
        component_role=request.component_role,
        hoop_stress_mpa=hoop_stress_mpa,
        allowable_stress_mpa=allowable_stress_mpa,
        stress_utilization_ratio=utilization_ratio,
        verdict=verdict,
        provenance=provenance,
        preliminary_check_result_hash=result_hash,
    )


def _blocked_for_detailed_design_result(
    *,
    request: PreliminaryCheckRequest,
    reason_diameter_m: Decimal,
    envelope_max_m: Decimal,
) -> PreliminaryCheckResult:
    """Build a BLOCKED_FOR_DETAILED_DESIGN result (§9.1 envelope rule)."""
    provenance = PreliminaryCheckProvenance(
        material_record_id=request.material_resolution.material_record_id,
        applicable_standard_id=(request.material_resolution.provenance.applicable_standard_id),
        design_pressure_mpa=_quantize_6dp(request.design_pressure_mpa),
        design_temperature_c=float(request.design_temperature_c),
        outer_diameter_m=_quantize_6dp(request.outer_diameter_m),
        inner_diameter_m=_quantize_6dp(request.inner_diameter_m),
        wall_thickness_m=Decimal("0"),
        allowable_temperature_c=None,
    )

    hash_payload = {
        "component_role": request.component_role,
        "hoop_stress_mpa": "0.000000",
        "allowable_stress_mpa": "0.000000",
        "stress_utilization_ratio": "0.000000",
        "verdict": "blocked_for_detailed_design",
        "provenance": provenance.to_dict(),
    }
    result_hash = _compute_result_hash(hash_payload)
    provenance = replace(provenance, result_hash=result_hash)

    return PreliminaryCheckResult(
        component_role=request.component_role,
        hoop_stress_mpa=Decimal("0.000000"),
        allowable_stress_mpa=Decimal("0.000000"),
        stress_utilization_ratio=Decimal("0.000000"),
        verdict="blocked_for_detailed_design",
        provenance=provenance,
        preliminary_check_result_hash=result_hash,
    )


__all__ = [
    "ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT",
    "ERROR_MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT",
    "ERROR_MECHANICAL_CHECK_UNSUPPORTED_ROLE",
    "MECHANICAL_ROLES_FROZEN_ORDER",
    "PreliminaryCheckProvenance",
    "PreliminaryCheckRequest",
    "PreliminaryCheckResult",
    "PreliminaryVerdict",
    "SUPPORTED_MECHANICAL_ROLES",
    "preliminary_check",
]
