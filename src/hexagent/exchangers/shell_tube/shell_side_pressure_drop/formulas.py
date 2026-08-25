"""Kern/Bayram-Sevilgen Eq. 15-17 evaluation in the frozen order."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, DecimalException
from typing import Any

from .decimal_quantization import engineering_context, finite_decimal

FORMULA_OPERATION_COUNT = 20
FORMULA_OPERATIONS: tuple[str, ...] = (
    "mu_ratio = context.divide(mu_b, mu_w)",
    "ratio_ln = context.ln(mu_ratio)",
    'ratio_ln_times_7 = context.multiply(ratio_ln, Decimal("7"))',
    'ratio_exp_arg = context.divide(ratio_ln_times_7, Decimal("50"))',
    "phi_s = context.exp(ratio_exp_arg)",
    "re_ln = context.ln(Re_s)",
    'friction_term = context.multiply(Decimal("0.19"), re_ln)',
    'friction_exp_arg = context.subtract(Decimal("0.576"), friction_term)',
    "f_s = context.exp(friction_exp_arg)",
    "g_s_squared = context.multiply(G_s, G_s)",
    "n_b_decimal = context.create_decimal(str(N_b))",
    'n_b_plus_one = context.add(n_b_decimal, Decimal("1"))',
    "numerator_f_g2 = context.multiply(f_s, g_s_squared)",
    "numerator_f_g2_nb = context.multiply(numerator_f_g2, n_b_plus_one)",
    "numerator = context.multiply(numerator_f_g2_nb, D_s)",
    'two_rho = context.multiply(Decimal("2"), rho_s)',
    "denominator_two_rho_de = context.multiply(two_rho, D_e)",
    "denominator = context.multiply(denominator_two_rho_de, phi_s)",
    "delta_p_raw = context.divide(numerator, denominator)",
    'delta_p_public = quantize(delta_p_raw, Decimal("0.001"), ROUND_HALF_EVEN)',
)


class FormulaCalculationError(ValueError):
    def __init__(
        self, operation: str, message: str = "Decimal engineering calculation failed"
    ) -> None:
        super().__init__(f"{operation}: {message}")
        self.operation = operation


def _step(operation: str, calculation: Callable[[], Decimal]) -> Decimal:
    try:
        return calculation()
    except (DecimalException, ArithmeticError, TypeError, ValueError) as exc:
        raise FormulaCalculationError(operation) from exc


@dataclass(frozen=True)
class FrictionAndWallCorrection:
    mu_ratio: Decimal
    phi_s: Decimal
    f_s: Decimal


@dataclass(frozen=True)
class PressureDropEvaluation:
    raw: Decimal
    public: Decimal | None
    mu_ratio: Decimal
    phi_s: Decimal
    f_s: Decimal
    numerator: Decimal
    denominator: Decimal


class EngineeringInputDomainError(ValueError):
    """Raised when the S12 formula input domain is not accepted."""


def validate_engineering_inputs(**values: object) -> dict[str, Any]:
    """Validate and normalize the finite positive S12 engineering inputs."""
    decimal_names = ("Re_s", "G_s", "rho_s", "D_s", "D_e", "mu_b", "mu_w")
    try:
        normalized: dict[str, Any] = {name: Decimal(str(values[name])) for name in decimal_names}
        normalized["N_b"] = values["N_b"]
    except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
        raise EngineeringInputDomainError("engineering_inputs") from exc

    if any(not finite_decimal(normalized[name]) for name in decimal_names):
        raise EngineeringInputDomainError("engineering_inputs")
    n_b = normalized["N_b"]
    if type(n_b) is not int:
        raise EngineeringInputDomainError("engineering_inputs")
    if (
        any(
            normalized[name] <= 0 for name in ("Re_s", "G_s", "rho_s", "D_s", "D_e", "mu_b", "mu_w")
        )
        or n_b < 0
    ):
        raise EngineeringInputDomainError("engineering_inputs")
    return normalized


def evaluate_friction_and_wall_correction(
    *, Re_s: Decimal, mu_b: Decimal, mu_w: Decimal
) -> FrictionAndWallCorrection:
    """Execute the frozen S13 friction-factor and wall-correction operations."""
    context = engineering_context()
    mu_ratio = _step("F13_DECIMAL_PHI_POWER", lambda: context.divide(mu_b, mu_w))
    ratio_ln = _step("F13_DECIMAL_PHI_POWER", lambda: context.ln(mu_ratio))
    ratio_ln_times_7 = _step(
        "F13_DECIMAL_PHI_POWER", lambda: context.multiply(ratio_ln, Decimal("7"))
    )
    ratio_exp_arg = _step(
        "F13_DECIMAL_PHI_POWER", lambda: context.divide(ratio_ln_times_7, Decimal("50"))
    )
    phi_s = _step("F13_DECIMAL_PHI_POWER", lambda: context.exp(ratio_exp_arg))
    re_ln = _step("F13_DECIMAL_LN_RE", lambda: context.ln(Re_s))
    friction_term = _step(
        "F13_DECIMAL_EXP_FRICTION", lambda: context.multiply(Decimal("0.19"), re_ln)
    )
    friction_exp_arg = _step(
        "F13_DECIMAL_EXP_FRICTION",
        lambda: context.subtract(Decimal("0.576"), friction_term),
    )
    f_s = _step("F13_DECIMAL_EXP_FRICTION", lambda: context.exp(friction_exp_arg))
    return FrictionAndWallCorrection(mu_ratio=mu_ratio, phi_s=phi_s, f_s=f_s)


def evaluate_pressure_drop(
    *,
    G_s: Decimal,
    rho_s: Decimal,
    D_s: Decimal,
    D_e: Decimal,
    N_b: int,
    f_s: Decimal,
    phi_s: Decimal,
    mu_ratio: Decimal,
) -> PressureDropEvaluation:
    """Evaluate only the frozen S14 raw pressure-drop arithmetic."""
    context = engineering_context()
    g_s_squared = _step("F14_PRESSURE_DROP", lambda: context.multiply(G_s, G_s))
    n_b_decimal = _step("F14_PRESSURE_DROP", lambda: context.create_decimal(str(N_b)))
    n_b_plus_one = _step("F14_PRESSURE_DROP", lambda: context.add(n_b_decimal, Decimal("1")))
    numerator_f_g2 = _step("F14_PRESSURE_DROP", lambda: context.multiply(f_s, g_s_squared))
    numerator_f_g2_nb = _step(
        "F14_PRESSURE_DROP", lambda: context.multiply(numerator_f_g2, n_b_plus_one)
    )
    numerator = _step("F14_PRESSURE_DROP", lambda: context.multiply(numerator_f_g2_nb, D_s))
    two_rho = _step("F14_PRESSURE_DROP", lambda: context.multiply(Decimal("2"), rho_s))
    denominator_two_rho_de = _step("F14_PRESSURE_DROP", lambda: context.multiply(two_rho, D_e))
    denominator = _step(
        "F14_PRESSURE_DROP",
        lambda: context.multiply(denominator_two_rho_de, phi_s),
    )
    delta_p_raw = _step("F14_PRESSURE_DROP", lambda: context.divide(numerator, denominator))
    return PressureDropEvaluation(
        raw=delta_p_raw,
        public=None,
        mu_ratio=mu_ratio,
        phi_s=phi_s,
        f_s=f_s,
        numerator=numerator,
        denominator=denominator,
    )


__all__ = [
    "EngineeringInputDomainError",
    "FormulaCalculationError",
    "FrictionAndWallCorrection",
    "PressureDropEvaluation",
    "evaluate_friction_and_wall_correction",
    "evaluate_pressure_drop",
    "validate_engineering_inputs",
]
