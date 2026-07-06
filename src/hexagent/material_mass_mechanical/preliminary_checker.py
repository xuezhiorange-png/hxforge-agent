"""TASK-017 Slice C + Slice D — PreliminaryMechanicalChecker.

Implements the TASK-017 frozen design contract
(docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md,
Frozen Contract Authority Commit SHA
``6ed5b7dc7d8df163796eacb838afcf5702a4c53a``,
Frozen Contract Authority Base SHA
``fbb05ae71f21e6cfd4d1041afb5958c863166248``) for the
PreliminaryMechanicalChecker's three screening checks (design
§5.3 + §9.1 + §9.2 + §9.3 + §7 codes 11-13 + §8 provenance +
§10.3 + §10.4).

Slice C (allowable-stress check, §9.1) is preserved unchanged —
its dataclasses, helpers, and the ``preliminary_check`` function
remain byte-identical to the Slice C round's committed behavior.
Slice C tests under ``TestClosedSetGuard`` / ``TestHoopStressFormula``
/ etc. continue to pass without modification.

Slice D extends this module with two ADDITIVE screening checks
per design §14 (planning doc §3 / §10):

- ``check_minimum_wall`` (§9.2) — preliminary screening for
  effective wall thickness below the documented minimums.
- ``check_straight_pipe_span`` (§9.3) — preliminary screening
  for elastic deflection of a simply-supported straight pipe
  exceeding the L/360 allowable ratio.

Plus a §5.3 ``MechanicalCheckReport`` orchestrator
(``run_mechanical_check_report``) that combines the §9.1
allowable-stress check (re-using ``preliminary_check``), §9.2
minimum-wall check, and §9.3 straight-pipe-span check into a
single ``MechanicalCheckReport`` with a 4-tier ``overall_verdict``
(``pass`` / ``marginal`` / ``blocked_preliminary`` /
``blocked_for_detailed_design``) per design §5.3.

Slice D scope is BOUNDED by frozen design §3.2 / §9.2 / §9.3:
preliminary screening ONLY, NOT detailed mechanical design.
The implementation MUST NOT introduce FEA, fatigue, creep,
seismic, wind, weld, NDE, code-stamp judgement, or any
escalation beyond ``BLOCKED_FOR_DETAILED_DESIGN``.

Slice D is a READ-ONLY consumer of Slice A
MaterialResolutionResult. It does NOT mutate TASK-013 material
records, does NOT mutate TASK-016 geometry records, does NOT
introduce pressure-drop / C4 / cost / new-solver logic, and does
NOT escalate to detailed mechanical design.

Slice D NEVER references Closeout tokens.
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
_SOFTWARE_VERSION_SLICE_C: Final[str] = "task-017-slice-c-v0.1.0"
_SOFTWARE_VERSION_SLICE_D: Final[str] = "task-017-slice-d-v0.1.0"
# Backwards-compatible alias for Slice C callers (the Slice C
# _SOFTWARE_VERSION was pinned to "task-017-slice-c-v0.1.0" at the
# Slice C round; Slice D does not rotate that pinned value).
_SOFTWARE_VERSION: Final[str] = _SOFTWARE_VERSION_SLICE_C
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


# ════════════════════════════════════════════════════════════════════════
# Slice D — Minimum-wall check (§9.2) + straight-pipe span check (§9.3)
# ════════════════════════════════════════════════════════════════════════
#
# Slice D is ADDITIVE. Slice C's dataclasses / helpers /
# ``preliminary_check`` function remain unchanged above.
#
# §9.2 thresholds (literal):
#   - PASS iff effective_wall_m >= 1.5 mm AND
#     effective_wall_m / outer_diameter_m >= 0.0005
#   - BLOCKED_PRELIMINARY iff either threshold is violated
#   - BLOCKED_FOR_DETAILED_DESIGN iff outer_diameter_m > 1.0 m
#
# §9.3 formula (literal):
#   outer_d, inner_d in m; K_load = 1.5; L / 360 deflection ratio
#   weight_per_length = density * pi * ((outer_d/2)^2 - (inner_d/2)^2) * 9.80665
#   w = weight_per_length * K_load
#   I = (pi/64) * (outer_d^4 - inner_d^4)
#   deflection_m = (5 * w * L^4) / (384 * E_pa * I)
#   allowable_deflection_m = L / 360
#   PASS iff deflection_m <= allowable_deflection_m
#   BLOCKED_PRELIMINARY iff deflection_m > allowable_deflection_m
#   BLOCKED_FOR_DETAILED_DESIGN iff:
#     - unsupported_span_m > 12 m, OR
#     - material_modulus_gpa is None, OR
#     - outer_diameter_m > 1.0 m
#
# §9.3 verdict literals are 3-tier (no MARGINAL); the 4-tier
# ``PreliminaryVerdict`` Literal alias is reused for the result
# type, with ``marginal`` simply not produced by §9.2 / §9.3.
# This is consistent with design §5.3: ``MechanicalCheckReport.overall_verdict``
# is 4-tier because the allowable-stress check (§9.1) can
# produce ``marginal``; §9.2 and §9.3 contribute PASS /
# BLOCKED_PRELIMINARY / BLOCKED_FOR_DETAILED_DESIGN.

# §9.2 minimum wall thresholds (literal; normative).
_MINIMUM_WALL_ABSOLUTE_M: Final[Decimal] = Decimal("0.0015")  # 1.5 mm
_MINIMUM_WALL_DIAMETER_RATIO: Final[Decimal] = Decimal("0.0005")  # 0.05 %
# §9.3 envelope constants (literal; normative).
_SPAN_PRELIMINARY_ENVELOPE_MAX_M: Final[Decimal] = Decimal("12.0")
_SPAN_DEFLECTION_RATIO: Final[Decimal] = Decimal("360")  # L / 360
_SPAN_K_LOAD: Final[Decimal] = Decimal("1.5")
# Gravitational acceleration 9.80665 m/s^2 — SI standard (ISO 80000-3).
_GRAVITY_M_PER_S2: Final[Decimal] = Decimal("9.80665")


# ── §9.2 Minimum-wall check request / result ──────────────────────────
@dataclass(frozen=True)
class MinimumWallCheckRequest:
    """Request payload for the §9.2 minimum-wall screening check.

    Slice D introduces this request type ADDITIVELY. The Slice C
    ``PreliminaryCheckRequest`` is preserved unchanged.
    """

    component_role: str
    material_resolution: MaterialResolutionResult
    outer_diameter_m: Decimal
    inner_diameter_m: Decimal
    corrosion_allowance_m: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.component_role, str):
            raise TypeError("component_role must be a str")
        if not isinstance(self.material_resolution, MaterialResolutionResult):
            raise TypeError("material_resolution must be a MaterialResolutionResult")
        if not isinstance(self.outer_diameter_m, Decimal):
            raise TypeError("outer_diameter_m must be a Decimal")
        if not isinstance(self.inner_diameter_m, Decimal):
            raise TypeError("inner_diameter_m must be a Decimal")
        if not isinstance(self.corrosion_allowance_m, Decimal):
            raise TypeError("corrosion_allowance_m must be a Decimal")


@dataclass(frozen=True)
class MinimumWallCheckProvenance:
    """Audit provenance for a §9.2 minimum-wall check (design §8)."""

    material_record_id: str
    applicable_standard_id: str | None
    software_version: str = _SOFTWARE_VERSION_SLICE_D
    git_commit: str = _GIT_COMMIT
    result_hash: str = ""
    outer_diameter_m: Decimal = Decimal("0")
    inner_diameter_m: Decimal = Decimal("0")
    corrosion_allowance_m: Decimal = Decimal("0")
    effective_wall_m: Decimal = Decimal("0")

    def to_dict(self) -> dict[str, Any]:
        """Stable dict for serialization (§10.4 canonical-JSON)."""
        return {
            "material_record_id": self.material_record_id,
            "applicable_standard_id": self.applicable_standard_id,
            "software_version": self.software_version,
            "git_commit": self.git_commit,
            "result_hash": self.result_hash,
            "outer_diameter_m": _decimal_to_str(self.outer_diameter_m),
            "inner_diameter_m": _decimal_to_str(self.inner_diameter_m),
            "corrosion_allowance_m": _decimal_to_str(self.corrosion_allowance_m),
            "effective_wall_m": _decimal_to_str(self.effective_wall_m),
        }


@dataclass(frozen=True)
class MinimumWallCheckResult:
    """Result of a §9.2 minimum-wall screening check.

    Verdict is 3-tier: ``pass`` / ``blocked_preliminary`` /
    ``blocked_for_detailed_design``. ``marginal`` is not produced
    by §9.2 (per design §9.2 verdict rules) but the
    ``PreliminaryVerdict`` Literal alias is reused for type
    consistency with the §5.3 ``MechanicalCheckReport.overall_verdict``
    aggregation.
    """

    component_role: str
    outer_diameter_m: Decimal
    inner_diameter_m: Decimal
    wall_thickness_m: Decimal
    corrosion_allowance_m: Decimal
    effective_wall_m: Decimal
    effective_wall_absolute_threshold_m: Decimal
    effective_wall_diameter_ratio_threshold: Decimal
    effective_wall_diameter_ratio: Decimal
    verdict: PreliminaryVerdict
    provenance: MinimumWallCheckProvenance
    minimum_wall_check_result_hash: str

    def to_dict(self) -> dict[str, Any]:
        """Stable dict for serialization (§10.4 canonical-JSON)."""
        return {
            "component_role": self.component_role,
            "outer_diameter_m": _decimal_to_str(self.outer_diameter_m),
            "inner_diameter_m": _decimal_to_str(self.inner_diameter_m),
            "wall_thickness_m": _decimal_to_str(self.wall_thickness_m),
            "corrosion_allowance_m": _decimal_to_str(self.corrosion_allowance_m),
            "effective_wall_m": _decimal_to_str(self.effective_wall_m),
            "effective_wall_absolute_threshold_m": _decimal_to_str(
                self.effective_wall_absolute_threshold_m
            ),
            "effective_wall_diameter_ratio_threshold": _decimal_to_str(
                self.effective_wall_diameter_ratio_threshold
            ),
            "effective_wall_diameter_ratio": _decimal_to_str(self.effective_wall_diameter_ratio),
            "verdict": self.verdict,
            "provenance": self.provenance.to_dict(),
            "minimum_wall_check_result_hash": self.minimum_wall_check_result_hash,
        }


# ── §9.3 Straight-pipe span check request / result ────────────────────
@dataclass(frozen=True)
class StraightPipeSpanCheckRequest:
    """Request payload for the §9.3 straight-pipe span screening check.

    Slice D introduces this request type ADDITIVELY.
    """

    component_role: str
    material_resolution: MaterialResolutionResult
    outer_diameter_m: Decimal
    inner_diameter_m: Decimal
    unsupported_span_m: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.component_role, str):
            raise TypeError("component_role must be a str")
        if not isinstance(self.material_resolution, MaterialResolutionResult):
            raise TypeError("material_resolution must be a MaterialResolutionResult")
        if not isinstance(self.outer_diameter_m, Decimal):
            raise TypeError("outer_diameter_m must be a Decimal")
        if not isinstance(self.inner_diameter_m, Decimal):
            raise TypeError("inner_diameter_m must be a Decimal")
        if not isinstance(self.unsupported_span_m, Decimal):
            raise TypeError("unsupported_span_m must be a Decimal")


@dataclass(frozen=True)
class StraightPipeSpanCheckProvenance:
    """Audit provenance for a §9.3 straight-pipe span check (design §8)."""

    material_record_id: str
    applicable_standard_id: str | None
    software_version: str = _SOFTWARE_VERSION_SLICE_D
    git_commit: str = _GIT_COMMIT
    result_hash: str = ""
    outer_diameter_m: Decimal = Decimal("0")
    inner_diameter_m: Decimal = Decimal("0")
    unsupported_span_m: Decimal = Decimal("0")
    material_modulus_gpa: float | None = None
    material_density_kg_m3: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Stable dict for serialization (§10.4 canonical-JSON)."""
        return {
            "material_record_id": self.material_record_id,
            "applicable_standard_id": self.applicable_standard_id,
            "software_version": self.software_version,
            "git_commit": self.git_commit,
            "result_hash": self.result_hash,
            "outer_diameter_m": _decimal_to_str(self.outer_diameter_m),
            "inner_diameter_m": _decimal_to_str(self.inner_diameter_m),
            "unsupported_span_m": _decimal_to_str(self.unsupported_span_m),
            "material_modulus_gpa": self.material_modulus_gpa,
            "material_density_kg_m3": self.material_density_kg_m3,
        }


@dataclass(frozen=True)
class StraightPipeSpanCheckResult:
    """Result of a §9.3 straight-pipe span screening check.

    Verdict is 3-tier: ``pass`` / ``blocked_preliminary`` /
    ``blocked_for_detailed_design``. ``marginal`` is not produced
    by §9.3 (per design §9.3 verdict rules).
    """

    component_role: str
    outer_diameter_m: Decimal
    inner_diameter_m: Decimal
    unsupported_span_m: Decimal
    material_modulus_gpa: float
    material_density_kg_m3: float
    deflection_m: Decimal
    allowable_deflection_m: Decimal
    k_load: Decimal
    deflection_ratio_denominator: Decimal
    verdict: PreliminaryVerdict
    provenance: StraightPipeSpanCheckProvenance
    straight_pipe_span_check_result_hash: str

    def to_dict(self) -> dict[str, Any]:
        """Stable dict for serialization (§10.4 canonical-JSON)."""
        return {
            "component_role": self.component_role,
            "outer_diameter_m": _decimal_to_str(self.outer_diameter_m),
            "inner_diameter_m": _decimal_to_str(self.inner_diameter_m),
            "unsupported_span_m": _decimal_to_str(self.unsupported_span_m),
            "material_modulus_gpa": self.material_modulus_gpa,
            "material_density_kg_m3": self.material_density_kg_m3,
            "deflection_m": _decimal_to_str(self.deflection_m),
            "allowable_deflection_m": _decimal_to_str(self.allowable_deflection_m),
            "k_load": _decimal_to_str(self.k_load),
            "deflection_ratio_denominator": _decimal_to_str(self.deflection_ratio_denominator),
            "verdict": self.verdict,
            "provenance": self.provenance.to_dict(),
            "straight_pipe_span_check_result_hash": (self.straight_pipe_span_check_result_hash),
        }


# ── §9.2 Minimum-wall check implementation ───────────────────────────
def check_minimum_wall(request: MinimumWallCheckRequest) -> MinimumWallCheckResult:
    """Run the §9.2 minimum-wall preliminary screening check.

    Implements design §9.2:

    - ``effective_wall_m = wall_thickness_m - corrosion_allowance_m``
      where ``wall_thickness_m = (outer_diameter_m - inner_diameter_m) / 2``.
    - ``PASS`` iff ``effective_wall_m >= 1.5 mm`` AND
      ``effective_wall_m / outer_diameter_m >= 0.0005``.
    - ``BLOCKED_PRELIMINARY`` iff either threshold is violated.
    - ``BLOCKED_FOR_DETAILED_DESIGN`` iff
      ``outer_diameter_m > PRELIMINARY_ENVELOPE_MAX_DIAMETER_M``
      (1.0 m — same envelope as §9.1; design §3.2).

    Slice D is screening only — does NOT escalate to detailed
    mechanical design (design §3.2).

    Input-guard rules follow Slice C conventions:

    - Component role MUST be in ``SUPPORTED_MECHANICAL_ROLES``
      (pressure-bearing metal components only); otherwise
      ``MaterialSelectorError`` with code
      ``ERROR_MECHANICAL_CHECK_UNSUPPORTED_ROLE``.
    - Outer / inner diameters MUST be positive / non-negative and
      outer > inner; otherwise
      ``ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT``.
    - ``corrosion_allowance_m`` MUST be ≥ 0; otherwise
      ``ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT``.
    """
    # §5.2.2 closed-set guard: pressure-bearing metal components only.
    if request.component_role not in SUPPORTED_MECHANICAL_ROLES:
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_UNSUPPORTED_ROLE,
            message=(
                f"check_minimum_wall does not support "
                f"component_role={request.component_role!r}; supported "
                f"roles are {sorted(SUPPORTED_MECHANICAL_ROLES)}."
            ),
            context={
                "component_role": request.component_role,
                "supported_roles": sorted(SUPPORTED_MECHANICAL_ROLES),
            },
        )

    # §7 input guard: outer diameter must be positive.
    if request.outer_diameter_m <= Decimal("0"):
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT,
            message=(
                "check_minimum_wall requires outer_diameter_m > 0; "
                f"got {_decimal_to_str(request.outer_diameter_m)}."
            ),
            context={
                "outer_diameter_m": _decimal_to_str(request.outer_diameter_m),
            },
        )

    # §7 input guard: inner diameter must be ≥ 0.
    if request.inner_diameter_m < Decimal("0"):
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT,
            message=(
                "check_minimum_wall requires inner_diameter_m >= 0; "
                f"got {_decimal_to_str(request.inner_diameter_m)}."
            ),
            context={
                "inner_diameter_m": _decimal_to_str(request.inner_diameter_m),
            },
        )

    # §7 input guard: outer must be > inner.
    if request.inner_diameter_m >= request.outer_diameter_m:
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT,
            message=(
                "check_minimum_wall requires inner_diameter_m < "
                "outer_diameter_m; got "
                f"inner={_decimal_to_str(request.inner_diameter_m)}, "
                f"outer={_decimal_to_str(request.outer_diameter_m)}."
            ),
            context={
                "inner_diameter_m": _decimal_to_str(request.inner_diameter_m),
                "outer_diameter_m": _decimal_to_str(request.outer_diameter_m),
            },
        )

    # §7 input guard: corrosion allowance must be ≥ 0.
    if request.corrosion_allowance_m < Decimal("0"):
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT,
            message=(
                "check_minimum_wall requires corrosion_allowance_m >= 0; "
                f"got {_decimal_to_str(request.corrosion_allowance_m)}."
            ),
            context={
                "corrosion_allowance_m": _decimal_to_str(request.corrosion_allowance_m),
            },
        )

    # §9.2 envelope guard: diameter > 1.0 m → BLOCKED_FOR_DETAILED_DESIGN.
    if request.outer_diameter_m > PRELIMINARY_ENVELOPE_MAX_DIAMETER_M:
        provenance = MinimumWallCheckProvenance(
            material_record_id=(request.material_resolution.material_record_id),
            applicable_standard_id=(request.material_resolution.provenance.applicable_standard_id),
            outer_diameter_m=_quantize_6dp(request.outer_diameter_m),
            inner_diameter_m=_quantize_6dp(request.inner_diameter_m),
            corrosion_allowance_m=_quantize_6dp(request.corrosion_allowance_m),
            effective_wall_m=Decimal("0.000000"),
        )
        hash_payload: dict[str, Any] = {
            "component_role": request.component_role,
            "outer_diameter_m": _decimal_to_str(provenance.outer_diameter_m),
            "inner_diameter_m": _decimal_to_str(provenance.inner_diameter_m),
            "wall_thickness_m": "0.000000",
            "corrosion_allowance_m": _decimal_to_str(provenance.corrosion_allowance_m),
            "effective_wall_m": "0.000000",
            "effective_wall_absolute_threshold_m": _decimal_to_str(
                _quantize_6dp(_MINIMUM_WALL_ABSOLUTE_M)
            ),
            "effective_wall_diameter_ratio_threshold": _decimal_to_str(
                _MINIMUM_WALL_DIAMETER_RATIO
            ),
            "effective_wall_diameter_ratio": "0.000000",
            "verdict": "blocked_for_detailed_design",
            "provenance": provenance.to_dict(),
        }
        result_hash = _compute_result_hash(hash_payload)
        provenance = replace(provenance, result_hash=result_hash)
        return MinimumWallCheckResult(
            component_role=request.component_role,
            outer_diameter_m=provenance.outer_diameter_m,
            inner_diameter_m=provenance.inner_diameter_m,
            wall_thickness_m=Decimal("0.000000"),
            corrosion_allowance_m=provenance.corrosion_allowance_m,
            effective_wall_m=Decimal("0.000000"),
            effective_wall_absolute_threshold_m=_quantize_6dp(_MINIMUM_WALL_ABSOLUTE_M),
            effective_wall_diameter_ratio_threshold=(_MINIMUM_WALL_DIAMETER_RATIO),
            effective_wall_diameter_ratio=Decimal("0.000000"),
            verdict="blocked_for_detailed_design",
            provenance=provenance,
            minimum_wall_check_result_hash=result_hash,
        )

    # §9.2 wall thickness (thin-wall approx., consistent with §9.1).
    wall_thickness_m = (request.outer_diameter_m - request.inner_diameter_m) / Decimal("2")
    # §9.2 effective wall after corrosion allowance.
    effective_wall_m_raw = wall_thickness_m - request.corrosion_allowance_m

    # §9.2 diameter ratio: effective_wall / outer_diameter.
    # Decimal division; outer_diameter_m is already guarded > 0.
    effective_wall_diameter_ratio_raw = effective_wall_m_raw / request.outer_diameter_m

    # §10.3 Decimal 6dp quantization.
    wall_thickness_m = _quantize_6dp(wall_thickness_m)
    effective_wall_m = _quantize_6dp(effective_wall_m_raw)
    effective_wall_diameter_ratio = _quantize_6dp(effective_wall_diameter_ratio_raw)
    effective_wall_absolute_threshold_m = _quantize_6dp(_MINIMUM_WALL_ABSOLUTE_M)

    # §9.2 verdict: PASS iff BOTH thresholds satisfied.
    abs_ok = effective_wall_m >= effective_wall_absolute_threshold_m
    ratio_ok = effective_wall_diameter_ratio >= _MINIMUM_WALL_DIAMETER_RATIO
    if abs_ok and ratio_ok:
        verdict: PreliminaryVerdict = "pass"
    else:
        verdict = "blocked_preliminary"

    provenance = MinimumWallCheckProvenance(
        material_record_id=request.material_resolution.material_record_id,
        applicable_standard_id=(request.material_resolution.provenance.applicable_standard_id),
        outer_diameter_m=_quantize_6dp(request.outer_diameter_m),
        inner_diameter_m=_quantize_6dp(request.inner_diameter_m),
        corrosion_allowance_m=_quantize_6dp(request.corrosion_allowance_m),
        effective_wall_m=effective_wall_m,
    )
    hash_payload = {
        "component_role": request.component_role,
        "outer_diameter_m": _decimal_to_str(provenance.outer_diameter_m),
        "inner_diameter_m": _decimal_to_str(provenance.inner_diameter_m),
        "wall_thickness_m": _decimal_to_str(wall_thickness_m),
        "corrosion_allowance_m": _decimal_to_str(provenance.corrosion_allowance_m),
        "effective_wall_m": _decimal_to_str(effective_wall_m),
        "effective_wall_absolute_threshold_m": _decimal_to_str(effective_wall_absolute_threshold_m),
        "effective_wall_diameter_ratio_threshold": _decimal_to_str(_MINIMUM_WALL_DIAMETER_RATIO),
        "effective_wall_diameter_ratio": _decimal_to_str(effective_wall_diameter_ratio),
        "verdict": verdict,
        "provenance": provenance.to_dict(),
    }
    result_hash = _compute_result_hash(hash_payload)
    provenance = replace(provenance, result_hash=result_hash)
    return MinimumWallCheckResult(
        component_role=request.component_role,
        outer_diameter_m=provenance.outer_diameter_m,
        inner_diameter_m=provenance.inner_diameter_m,
        wall_thickness_m=wall_thickness_m,
        corrosion_allowance_m=provenance.corrosion_allowance_m,
        effective_wall_m=effective_wall_m,
        effective_wall_absolute_threshold_m=effective_wall_absolute_threshold_m,
        effective_wall_diameter_ratio_threshold=(_MINIMUM_WALL_DIAMETER_RATIO),
        effective_wall_diameter_ratio=effective_wall_diameter_ratio,
        verdict=verdict,
        provenance=provenance,
        minimum_wall_check_result_hash=result_hash,
    )


# ── §9.3 Straight-pipe span check implementation ───────────────────────
def check_straight_pipe_span(
    request: StraightPipeSpanCheckRequest,
) -> StraightPipeSpanCheckResult:
    """Run the §9.3 straight-pipe span preliminary screening check.

    Implements design §9.3:

    - weight per unit length (N/m) =
      ``density * pi * ((outer_d / 2)^2 - (inner_d / 2)^2) * 9.80665``
      using only the metal cross-section for ``component_under_check``.
    - distributed load ``w = weight_per_length * K_load`` (K_load = 1.5).
    - second moment of area ``I = (pi/64) * (outer_d^4 - inner_d^4)``
      (thin-walled circular tube).
    - elastic deflection ``deflection_m = (5 * w * L^4) / (384 * E_pa * I)``.
    - allowable deflection ``L / 360``.
    - ``PASS`` iff ``deflection_m <= allowable_deflection_m``.
    - ``BLOCKED_PRELIMINARY`` iff ``deflection_m > allowable_deflection_m``.
    - ``BLOCKED_FOR_DETAILED_DESIGN`` iff any of:
      - ``unsupported_span_m > 12 m``,
      - ``material_modulus_gpa is None``,
      - ``outer_diameter_m > PRELIMINARY_ENVELOPE_MAX_DIAMETER_M``
        (1.0 m).

    Per design §9.3 the envelope-block on missing modulus returns
    ``BLOCKED_FOR_DETAILED_DESIGN`` (NOT
    ``MECHANICAL_CHECK_UNSUPPORTED_ROLE``); the caller must
    escalate to detailed mechanical design.

    Slice D is screening only — does NOT escalate to detailed
    mechanical design.
    """
    # §5.2.2 closed-set guard: pressure-bearing metal components only.
    if request.component_role not in SUPPORTED_MECHANICAL_ROLES:
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_UNSUPPORTED_ROLE,
            message=(
                f"check_straight_pipe_span does not support "
                f"component_role={request.component_role!r}; supported "
                f"roles are {sorted(SUPPORTED_MECHANICAL_ROLES)}."
            ),
            context={
                "component_role": request.component_role,
                "supported_roles": sorted(SUPPORTED_MECHANICAL_ROLES),
            },
        )

    # §7 input guard: outer diameter must be positive.
    if request.outer_diameter_m <= Decimal("0"):
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT,
            message=(
                "check_straight_pipe_span requires outer_diameter_m > 0; "
                f"got {_decimal_to_str(request.outer_diameter_m)}."
            ),
            context={
                "outer_diameter_m": _decimal_to_str(request.outer_diameter_m),
            },
        )

    # §7 input guard: inner diameter must be ≥ 0 and < outer.
    if request.inner_diameter_m < Decimal("0"):
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT,
            message=(
                "check_straight_pipe_span requires inner_diameter_m >= 0; "
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
                "check_straight_pipe_span requires inner_diameter_m < "
                "outer_diameter_m; got "
                f"inner={_decimal_to_str(request.inner_diameter_m)}, "
                f"outer={_decimal_to_str(request.outer_diameter_m)}."
            ),
            context={
                "inner_diameter_m": _decimal_to_str(request.inner_diameter_m),
                "outer_diameter_m": _decimal_to_str(request.outer_diameter_m),
            },
        )

    # §7 input guard: unsupported_span_m must be > 0 (zero / negative
    # span is dimensionally inconsistent).
    if request.unsupported_span_m <= Decimal("0"):
        raise MaterialSelectorError(
            code=ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT,
            message=(
                "check_straight_pipe_span requires unsupported_span_m > 0; "
                f"got {_decimal_to_str(request.unsupported_span_m)}."
            ),
            context={
                "unsupported_span_m": _decimal_to_str(request.unsupported_span_m),
            },
        )

    # §9.3 envelope guard: missing modulus → BLOCKED_FOR_DETAILED_DESIGN.
    if request.material_resolution.youngs_modulus_gpa is None:
        return _span_blocked_for_detailed_design_result(
            request=request,
            envelope_reason="material_modulus_gpa is None",
        )

    # §9.3 envelope guard: missing density → BLOCKED_FOR_DETAILED_DESIGN.
    # (The §9.3 formula uses material_density_kg_m3 in
    # weight_per_length; density is REQUIRED for §9.3 per §5.1.2
    # used-for §9.3 row.)
    if request.material_resolution.density_kg_m3 is None:
        return _span_blocked_for_detailed_design_result(
            request=request,
            envelope_reason="material_density_kg_m3 is None",
        )

    # §9.3 envelope guard: span > 12 m → BLOCKED_FOR_DETAILED_DESIGN.
    if request.unsupported_span_m > _SPAN_PRELIMINARY_ENVELOPE_MAX_M:
        return _span_blocked_for_detailed_design_result(
            request=request,
            envelope_reason="unsupported_span_m > 12 m",
        )

    # §9.3 envelope guard: diameter > 1.0 m → BLOCKED_FOR_DETAILED_DESIGN.
    if request.outer_diameter_m > PRELIMINARY_ENVELOPE_MAX_DIAMETER_M:
        return _span_blocked_for_detailed_design_result(
            request=request,
            envelope_reason="outer_diameter_m > 1.0 m",
        )

    modulus_gpa = float(request.material_resolution.youngs_modulus_gpa)
    density_kg_m3 = float(request.material_resolution.density_kg_m3)

    # Defensive: modulus / density must be positive.
    if modulus_gpa <= 0:
        return _span_blocked_for_detailed_design_result(
            request=request,
            envelope_reason="material_modulus_gpa <= 0",
        )
    if density_kg_m3 <= 0:
        return _span_blocked_for_detailed_design_result(
            request=request,
            envelope_reason="material_density_kg_m3 <= 0",
        )

    # §9.3 formula (literal). Compute in Decimal for precision,
    # then quantize to 6dp per §10.3.
    outer_d = request.outer_diameter_m
    inner_d = request.inner_diameter_m
    L = request.unsupported_span_m
    # cross-section area (m^2) — metal-only, conservatively.
    cross_section_area_m2 = Decimal("3.14159265358979323846264338327950288419716939937510") * (
        (outer_d / Decimal("2")) * (outer_d / Decimal("2"))
        - (inner_d / Decimal("2")) * (inner_d / Decimal("2"))
    )
    weight_per_length_n_per_m = (
        Decimal(str(density_kg_m3)) * cross_section_area_m2 * _GRAVITY_M_PER_S2
    )
    w = weight_per_length_n_per_m * _SPAN_K_LOAD
    # Second moment of area (m^4) — thin-walled circular tube.
    # Named ``second_moment_of_area_m4`` to avoid the E741 ambiguous
    # single-letter variable name flagged by ruff; in beam-mechanics
    # literature this quantity is conventionally ``I`` but Python
    # style here prefers a descriptive identifier.
    second_moment_of_area_m4 = (
        Decimal("3.14159265358979323846264338327950288419716939937510")
        / Decimal("64")
        * (outer_d**4 - inner_d**4)
    )
    if Decimal("0") >= second_moment_of_area_m4:
        # Defensive: outer_d > inner_d guard above already ensures
        # second_moment_of_area > 0, but keep an explicit guard for
        # safety.
        return _span_blocked_for_detailed_design_result(
            request=request,
            envelope_reason="second_moment_of_area <= 0",
        )
    e_pa = Decimal(str(modulus_gpa)) * Decimal("1000000000")  # GPa → Pa
    deflection_m_raw = (Decimal("5") * w * (L**4)) / (
        Decimal("384") * e_pa * second_moment_of_area_m4
    )
    allowable_deflection_m_raw = L / _SPAN_DEFLECTION_RATIO

    # §10.3 Decimal 6dp quantization.
    deflection_m = _quantize_6dp(deflection_m_raw)
    allowable_deflection_m = _quantize_6dp(allowable_deflection_m_raw)

    # §9.3 verdict.
    # Type-annotated as PreliminaryVerdict Literal so mypy accepts
    # the ternary return value (otherwise mypy widens to str and
    # the dataclass Literal field rejects it).
    verdict: PreliminaryVerdict = (
        "pass" if deflection_m <= allowable_deflection_m else "blocked_preliminary"
    )

    provenance = StraightPipeSpanCheckProvenance(
        material_record_id=request.material_resolution.material_record_id,
        applicable_standard_id=(request.material_resolution.provenance.applicable_standard_id),
        outer_diameter_m=_quantize_6dp(request.outer_diameter_m),
        inner_diameter_m=_quantize_6dp(request.inner_diameter_m),
        unsupported_span_m=_quantize_6dp(request.unsupported_span_m),
        material_modulus_gpa=modulus_gpa,
        material_density_kg_m3=density_kg_m3,
    )
    hash_payload = {
        "component_role": request.component_role,
        "outer_diameter_m": _decimal_to_str(provenance.outer_diameter_m),
        "inner_diameter_m": _decimal_to_str(provenance.inner_diameter_m),
        "unsupported_span_m": _decimal_to_str(provenance.unsupported_span_m),
        "material_modulus_gpa": provenance.material_modulus_gpa,
        "material_density_kg_m3": provenance.material_density_kg_m3,
        "deflection_m": _decimal_to_str(deflection_m),
        "allowable_deflection_m": _decimal_to_str(allowable_deflection_m),
        "k_load": _decimal_to_str(_quantize_6dp(_SPAN_K_LOAD)),
        "deflection_ratio_denominator": _decimal_to_str(_SPAN_DEFLECTION_RATIO),
        "verdict": verdict,
        "provenance": provenance.to_dict(),
    }
    result_hash = _compute_result_hash(hash_payload)
    provenance = replace(provenance, result_hash=result_hash)
    return StraightPipeSpanCheckResult(
        component_role=request.component_role,
        outer_diameter_m=provenance.outer_diameter_m,
        inner_diameter_m=provenance.inner_diameter_m,
        unsupported_span_m=provenance.unsupported_span_m,
        material_modulus_gpa=modulus_gpa,
        material_density_kg_m3=density_kg_m3,
        deflection_m=deflection_m,
        allowable_deflection_m=allowable_deflection_m,
        k_load=_quantize_6dp(_SPAN_K_LOAD),
        deflection_ratio_denominator=_SPAN_DEFLECTION_RATIO,
        verdict=verdict,
        provenance=provenance,
        straight_pipe_span_check_result_hash=result_hash,
    )


def _span_blocked_for_detailed_design_result(
    *,
    request: StraightPipeSpanCheckRequest,
    envelope_reason: str,
) -> StraightPipeSpanCheckResult:
    """Build a BLOCKED_FOR_DETAILED_DESIGN result for §9.3 envelope rule."""
    modulus_gpa: float | None = request.material_resolution.youngs_modulus_gpa
    density_kg_m3: float | None = request.material_resolution.density_kg_m3
    provenance = StraightPipeSpanCheckProvenance(
        material_record_id=request.material_resolution.material_record_id,
        applicable_standard_id=(request.material_resolution.provenance.applicable_standard_id),
        outer_diameter_m=_quantize_6dp(request.outer_diameter_m),
        inner_diameter_m=_quantize_6dp(request.inner_diameter_m),
        unsupported_span_m=_quantize_6dp(request.unsupported_span_m),
        material_modulus_gpa=modulus_gpa,
        material_density_kg_m3=density_kg_m3,
    )
    hash_payload = {
        "component_role": request.component_role,
        "outer_diameter_m": _decimal_to_str(provenance.outer_diameter_m),
        "inner_diameter_m": _decimal_to_str(provenance.inner_diameter_m),
        "unsupported_span_m": _decimal_to_str(provenance.unsupported_span_m),
        "material_modulus_gpa": provenance.material_modulus_gpa,
        "material_density_kg_m3": provenance.material_density_kg_m3,
        "deflection_m": "0.000000",
        "allowable_deflection_m": "0.000000",
        "k_load": _decimal_to_str(_quantize_6dp(_SPAN_K_LOAD)),
        "deflection_ratio_denominator": _decimal_to_str(_SPAN_DEFLECTION_RATIO),
        "verdict": "blocked_for_detailed_design",
        "provenance": provenance.to_dict(),
        "envelope_reason": envelope_reason,
    }
    result_hash = _compute_result_hash(hash_payload)
    provenance = replace(provenance, result_hash=result_hash)
    return StraightPipeSpanCheckResult(
        component_role=request.component_role,
        outer_diameter_m=provenance.outer_diameter_m,
        inner_diameter_m=provenance.inner_diameter_m,
        unsupported_span_m=provenance.unsupported_span_m,
        material_modulus_gpa=modulus_gpa if modulus_gpa is not None else 0.0,
        material_density_kg_m3=density_kg_m3 if density_kg_m3 is not None else 0.0,
        deflection_m=Decimal("0.000000"),
        allowable_deflection_m=Decimal("0.000000"),
        k_load=_quantize_6dp(_SPAN_K_LOAD),
        deflection_ratio_denominator=_SPAN_DEFLECTION_RATIO,
        verdict="blocked_for_detailed_design",
        provenance=provenance,
        straight_pipe_span_check_result_hash=result_hash,
    )


# ── §5.3 MechanicalCheckReport orchestrator ──────────────────────────
@dataclass(frozen=True)
class MechanicalCheckRequest:
    """Combined request for the §5.3 MechanicalCheckReport orchestrator.

    Combines the §9.1 allowable-stress request fields, §9.2
    corrosion_allowance_m, and §9.3 unsupported_span_m. Slice D
    introduces this ADDITIVELY for the §5.3 ``MechanicalCheckReport``
    orchestrator (``run_mechanical_check_report``).
    """

    component_role: str
    material_resolution: MaterialResolutionResult
    design_pressure_mpa: Decimal
    design_temperature_c: float
    outer_diameter_m: Decimal
    inner_diameter_m: Decimal
    corrosion_allowance_m: Decimal
    unsupported_span_m: Decimal

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
        if not isinstance(self.corrosion_allowance_m, Decimal):
            raise TypeError("corrosion_allowance_m must be a Decimal")
        if not isinstance(self.unsupported_span_m, Decimal):
            raise TypeError("unsupported_span_m must be a Decimal")


@dataclass(frozen=True)
class MechanicalCheckReportProvenance:
    """Provenance block for the §5.3 MechanicalCheckReport (design §8).

    Echoes the material record id, the applicable standard id (if
    any), the input envelope, the slice-D software version, and
    the report-level ``result_hash``. The per-check result hashes
    are also embedded for traceability.
    """

    material_record_id: str
    applicable_standard_id: str | None
    software_version: str = _SOFTWARE_VERSION_SLICE_D
    git_commit: str = _GIT_COMMIT
    result_hash: str = ""
    design_pressure_mpa: Decimal = Decimal("0")
    design_temperature_c: float = 0.0
    allowable_stress_check_result_hash: str = ""
    minimum_wall_check_result_hash: str = ""
    straight_pipe_span_check_result_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Stable dict for serialization (§10.4 canonical-JSON)."""
        return {
            "material_record_id": self.material_record_id,
            "applicable_standard_id": self.applicable_standard_id,
            "software_version": self.software_version,
            "git_commit": self.git_commit,
            "result_hash": self.result_hash,
            "design_pressure_mpa": _decimal_to_str(self.design_pressure_mpa),
            "design_temperature_c": float(self.design_temperature_c),
            "allowable_stress_check_result_hash": (self.allowable_stress_check_result_hash),
            "minimum_wall_check_result_hash": (self.minimum_wall_check_result_hash),
            "straight_pipe_span_check_result_hash": (self.straight_pipe_span_check_result_hash),
        }


@dataclass(frozen=True)
class MechanicalCheckReport:
    """§5.3 MechanicalCheckReport — combines §9.1 + §9.2 + §9.3 results.

    ``overall_verdict`` aggregation (per design §5.3):

    - If any check returns ``BLOCKED_FOR_DETAILED_DESIGN`` →
      ``overall_verdict = BLOCKED_FOR_DETAILED_DESIGN``.
    - Else if any check returns ``BLOCKED_PRELIMINARY`` →
      ``overall_verdict = BLOCKED_PRELIMINARY``.
    - Else if any check returns ``MARGINAL`` →
      ``overall_verdict = MARGINAL``.
    - Else → ``PASS``.
    """

    component_role: str
    allowable_stress_check: PreliminaryCheckResult
    minimum_wall_check: MinimumWallCheckResult
    straight_pipe_span_check: StraightPipeSpanCheckResult
    overall_verdict: PreliminaryVerdict
    provenance: MechanicalCheckReportProvenance
    mechanical_check_report_result_hash: str

    def to_dict(self) -> dict[str, Any]:
        """Stable dict for serialization (§10.4 canonical-JSON)."""
        return {
            "component_role": self.component_role,
            "allowable_stress_check": self.allowable_stress_check.to_dict(),
            "minimum_wall_check": self.minimum_wall_check.to_dict(),
            "straight_pipe_span_check": (self.straight_pipe_span_check.to_dict()),
            "overall_verdict": self.overall_verdict,
            "provenance": self.provenance.to_dict(),
            "mechanical_check_report_result_hash": (self.mechanical_check_report_result_hash),
        }


# Verdict severity ladder used by the §5.3 orchestrator to pick
# ``overall_verdict`` (per design §5.3 aggregation rules).
_OVERALL_VERDICT_SEVERITY: Final[dict[str, int]] = {
    "pass": 0,
    "marginal": 1,
    "blocked_preliminary": 2,
    "blocked_for_detailed_design": 3,
}


def run_mechanical_check_report(
    request: MechanicalCheckRequest,
) -> MechanicalCheckReport:
    """Run the §5.3 ``MechanicalCheckReport`` orchestrator.

    Composes ``preliminary_check`` (§9.1, Slice C),
    ``check_minimum_wall`` (§9.2, Slice D), and
    ``check_straight_pipe_span`` (§9.3, Slice D) into a single
    ``MechanicalCheckReport`` with a 4-tier ``overall_verdict``.

    The per-check functions raise their own
    ``MaterialSelectorError`` for input-dimensional inconsistency;
    that behavior is preserved (no swallowing). Any per-check
    verdict drives the overall verdict aggregation.
    """
    # §9.1 (Slice C). The legacy PreliminaryCheckRequest is rebuilt
    # from the MechanicalCheckRequest fields.
    allowable_stress_request = PreliminaryCheckRequest(
        component_role=request.component_role,
        material_resolution=request.material_resolution,
        design_pressure_mpa=request.design_pressure_mpa,
        design_temperature_c=request.design_temperature_c,
        outer_diameter_m=request.outer_diameter_m,
        inner_diameter_m=request.inner_diameter_m,
    )
    allowable_stress_result = preliminary_check(allowable_stress_request)

    # §9.2 (Slice D).
    minimum_wall_request = MinimumWallCheckRequest(
        component_role=request.component_role,
        material_resolution=request.material_resolution,
        outer_diameter_m=request.outer_diameter_m,
        inner_diameter_m=request.inner_diameter_m,
        corrosion_allowance_m=request.corrosion_allowance_m,
    )
    minimum_wall_result = check_minimum_wall(minimum_wall_request)

    # §9.3 (Slice D).
    straight_pipe_span_request = StraightPipeSpanCheckRequest(
        component_role=request.component_role,
        material_resolution=request.material_resolution,
        outer_diameter_m=request.outer_diameter_m,
        inner_diameter_m=request.inner_diameter_m,
        unsupported_span_m=request.unsupported_span_m,
    )
    straight_pipe_span_result = check_straight_pipe_span(straight_pipe_span_request)

    # §5.3 overall verdict aggregation.
    verdicts = (
        allowable_stress_result.verdict,
        minimum_wall_result.verdict,
        straight_pipe_span_result.verdict,
    )
    overall_verdict: PreliminaryVerdict = max(verdicts, key=lambda v: _OVERALL_VERDICT_SEVERITY[v])

    provenance = MechanicalCheckReportProvenance(
        material_record_id=request.material_resolution.material_record_id,
        applicable_standard_id=(request.material_resolution.provenance.applicable_standard_id),
        design_pressure_mpa=_quantize_6dp(request.design_pressure_mpa),
        design_temperature_c=float(request.design_temperature_c),
        allowable_stress_check_result_hash=(allowable_stress_result.preliminary_check_result_hash),
        minimum_wall_check_result_hash=(minimum_wall_result.minimum_wall_check_result_hash),
        straight_pipe_span_check_result_hash=(
            straight_pipe_span_result.straight_pipe_span_check_result_hash
        ),
    )
    hash_payload: dict[str, Any] = {
        "component_role": request.component_role,
        "allowable_stress_check": allowable_stress_result.to_dict(),
        "minimum_wall_check": minimum_wall_result.to_dict(),
        "straight_pipe_span_check": (straight_pipe_span_result.to_dict()),
        "overall_verdict": overall_verdict,
        "provenance": provenance.to_dict(),
    }
    result_hash = _compute_result_hash(hash_payload)
    provenance = replace(provenance, result_hash=result_hash)
    return MechanicalCheckReport(
        component_role=request.component_role,
        allowable_stress_check=allowable_stress_result,
        minimum_wall_check=minimum_wall_result,
        straight_pipe_span_check=straight_pipe_span_result,
        overall_verdict=overall_verdict,
        provenance=provenance,
        mechanical_check_report_result_hash=result_hash,
    )


__all__ = [
    "ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT",
    "ERROR_MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT",
    "ERROR_MECHANICAL_CHECK_UNSUPPORTED_ROLE",
    "MECHANICAL_ROLES_FROZEN_ORDER",
    "MechanicalCheckReport",
    "MechanicalCheckReportProvenance",
    "MechanicalCheckRequest",
    "MinimumWallCheckProvenance",
    "MinimumWallCheckRequest",
    "MinimumWallCheckResult",
    "PreliminaryCheckProvenance",
    "PreliminaryCheckRequest",
    "PreliminaryCheckResult",
    "PreliminaryVerdict",
    "StraightPipeSpanCheckProvenance",
    "StraightPipeSpanCheckRequest",
    "StraightPipeSpanCheckResult",
    "SUPPORTED_MECHANICAL_ROLES",
    "check_minimum_wall",
    "check_straight_pipe_span",
    "preliminary_check",
    "run_mechanical_check_report",
]
