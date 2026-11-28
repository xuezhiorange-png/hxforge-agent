"""Frozen experimental design C: strict four-port pass + mid joint prescreen."""

from __future__ import annotations

from decimal import Decimal

CANDIDATE_C_TUBE_NOZZLE_ID_MM = Decimal("123.80")
CANDIDATE_C_SHELL_NOZZLE_ID_MM = Decimal("159.00")
CANDIDATE_C_TUBE_NOZZLE_ID_M = CANDIDATE_C_TUBE_NOZZLE_ID_MM / Decimal("1000")
CANDIDATE_C_SHELL_NOZZLE_ID_M = CANDIDATE_C_SHELL_NOZZLE_ID_MM / Decimal("1000")

__all__ = [
    "CANDIDATE_C_SHELL_NOZZLE_ID_M",
    "CANDIDATE_C_SHELL_NOZZLE_ID_MM",
    "CANDIDATE_C_TUBE_NOZZLE_ID_M",
    "CANDIDATE_C_TUBE_NOZZLE_ID_MM",
]
