"""Kern Eq.58 Decimal evaluation for TASK-033."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .decimal_quantization import engineering_context, quantization_collision, quantize_public_htc

REYNOLDS_LOWER_EXCLUSIVE = Decimal("2e3")
REYNOLDS_UPPER_EXCLUSIVE = Decimal("1e6")


class FormulaCalculationError(Exception):
    """Raised when the explicit Decimal formula cannot be evaluated."""


@dataclass(frozen=True)
class FormulaEvaluation:
    raw: Decimal
    public: Decimal


def _positive_finite(value: Decimal) -> bool:
    return isinstance(value, Decimal) and value.is_finite() and value > 0


def evaluate_htc(
    *,
    reynolds: Decimal,
    prandtl: Decimal,
    thermal_conductivity: Decimal,
    equivalent_diameter: Decimal,
) -> FormulaEvaluation:
    values = (reynolds, prandtl, thermal_conductivity, equivalent_diameter)
    if not all(_positive_finite(value) for value in values):
        raise FormulaCalculationError("SSHT_FORMULA_INPUT_DOMAIN_VIOLATION")
    context = engineering_context()
    try:
        re_ln = context.ln(reynolds)
        re_exp_arg = context.divide(context.multiply(re_ln, Decimal(11)), Decimal(20))
        re_pow = context.exp(re_exp_arg)

        pr_ln = context.ln(prandtl)
        pr_exp_arg = context.divide(pr_ln, Decimal(3))
        pr_pow = context.exp(pr_exp_arg)

        prefactor_1 = context.multiply(Decimal("0.36"), thermal_conductivity)
        prefactor = context.divide(prefactor_1, equivalent_diameter)
        h_partial = context.multiply(prefactor, re_pow)
        h_raw = context.multiply(h_partial, pr_pow)
        h_public = quantize_public_htc(h_raw)
    except Exception as exc:
        raise FormulaCalculationError("SSHT_FORMULA_CALCULATION_FAILED") from exc
    if not h_raw.is_finite() or not h_public.is_finite():
        raise FormulaCalculationError("SSHT_FORMULA_CALCULATION_FAILED")
    return FormulaEvaluation(raw=h_raw, public=h_public)


__all__ = [
    "FormulaCalculationError",
    "FormulaEvaluation",
    "REYNOLDS_LOWER_EXCLUSIVE",
    "REYNOLDS_UPPER_EXCLUSIVE",
    "evaluate_htc",
    "quantization_collision",
]
