"""TASK-028 frozen enums: ComponentType, FlowDirection (two domains), Convention, Permission, Applicability.

§18 — Frozen exact enums.
"""

from __future__ import annotations

import enum


class Task028ComponentType(enum.StrEnum):
    """§5.1 — Supported component types for TASK-028 V1."""

    ENTRANCE = "ENTRANCE"
    EXIT = "EXIT"
    CHANNEL_HEAD = "CHANNEL_HEAD"
    NOZZLE = "NOZZLE"
    CONTRACTION = "CONTRACTION"
    EXPANSION = "EXPANSION"


# Known unsupported component tokens (for routing at raw boundary)
KNOWN_UNSUPPORTED_RAW_COMPONENT_TOKENS: tuple[str, ...] = (
    "PASS_PARTITION",
    "RETURN_HEADER",
    "RETURN_BEND",
    "U_BEND",
)


class Task028RequestFlowDirectionAssertion(enum.StrEnum):
    """§5.2 — Request-level flow direction assertion (V1: START_TO_END only)."""

    START_TO_END = "START_TO_END"


class Task028ComponentFlowDirectionAssertion(enum.StrEnum):
    """§5.3 — Component-level flow direction assertion."""

    START_TO_END = "START_TO_END"
    END_TO_START = "END_TO_START"


class LossCoefficientConvention(enum.StrEnum):
    """§5.4 — Frozen loss coefficient convention."""

    K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2 = (
        "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2"
    )


class CoefficientPermissionStatus(enum.StrEnum):
    """§5.6 — Coefficient permission status."""

    ADMITTED = "ADMITTED"


class Task028ApplicabilityAssertion(enum.StrEnum):
    """§5.5 — Applicability assertion states."""

    TRUE = "TRUE"
    FALSE = "FALSE"


__all__ = [
    "Task028ComponentType",
    "Task028RequestFlowDirectionAssertion",
    "Task028ComponentFlowDirectionAssertion",
    "LossCoefficientConvention",
    "CoefficientPermissionStatus",
    "Task028ApplicabilityAssertion",
    "KNOWN_UNSUPPORTED_RAW_COMPONENT_TOKENS",
]
