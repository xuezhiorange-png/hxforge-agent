"""Closed-set error / blocker / warning code enumeration.

TASK-018 frozen contract §9 (Error / blocker model) defines a frozen
closed set of error and warning codes. No new codes may be introduced
without amending §9 via a separate TASK-018 design-amendment PR.

Slice A scope (TASK-018 implementation Round 1): the
``CostModelSelector`` consumes these codes. CostCalculator (Slice B)
and LifeCycleEnergyEstimator (Slice C) will also reuse the same closed
set; their specific additional codes (e.g. C0/C1 subtotal blockers)
are NOT included here — Slice B / C will extend the set under their
own authorization rounds.

Per TASK-018 §9.1 / §9.2, the closed-set conventions are:
    - ``cost_*_blocker`` — frozen termination: result becomes ``NOT_COMPUTABLE``.
    - ``cost_*_warning`` — frozen advisory: result becomes ``COMPUTABLE_WITH_WARNINGS``.
    - ``unspecified_*`` — safety-net bucket; if a runtime fault falls outside
      a named code, the application MUST emit ``unspecified_blocker`` or
      ``unspecified_warning`` rather than introduce a new code.
"""

from __future__ import annotations

import enum
from typing import Final


class CostSelectorError(Exception):
    """Base exception for CostModelSelector failures.

    Carries a frozen closed-set ``code`` (see ``BLOCKER_CODES`` /
    ``WARNING_CODES``) and an opaque ``details`` mapping for diagnostics.
    """

    def __init__(self, code: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(f"{code}: {details or {}}")
        self.code = code
        self.details: dict[str, object] = dict(details or {})


class CostSelectorWarning(UserWarning):
    """Surface a frozen-warning code without terminating selection."""

    def __init__(self, code: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(f"{code}: {details or {}}")
        self.code = code
        self.details: dict[str, object] = dict(details or {})


class _FrozenStrEnum(str, enum.Enum):  # noqa: UP042  (deliberate Py3.10+ compat)
    """``str``-valued enum so frozen codes serialize as plain strings.

    Uses the ``(str, Enum)`` mixin pattern (compatible with Python 3.10+)
    rather than ``enum.StrEnum`` so the same code runs on the project's
    pinned ``python_requires >= 3.11`` interpreter AND the local ``python3.10``
    helper used for offline linting.
    """


class BlockerCode(_FrozenStrEnum):
    """Frozen closed set of TASK-018 §9.1 blocker codes.

    The list deliberately matches the design contract verbatim. Adding
    a new entry here without amending the design contract is a
    contract violation (per TASK-018 §19.3 anti-rewrite rule).
    """

    CURRENCY_MISMATCH_BLOCKER = "currency_mismatch_blocker"
    REGION_UNSUPPORTED_BLOCKER = "region_unsupported_blocker"
    VALIDITY_ENVELOPE_BLOCKER = "validity_envelope_blocker"
    MISSING_REQUIRED_LIFECYCLE_INPUT_BLOCKER = "missing_required_lifecycle_input_blocker"
    RESTRICTED_BODY_PROPAGATION_BLOCKER = "restricted_body_propagation_blocker"
    UNSPECIFIED_BLOCKER = "unspecified_blocker"


class WarningCode(_FrozenStrEnum):
    """Frozen closed set of TASK-018 §9.2 warning codes."""

    CURRENCY_FALLBACK_USED_WARNING = "currency_fallback_used_warning"
    REGION_FALLBACK_USED_WARNING = "region_fallback_used_warning"
    FOULING_ENERGY_PENALTY_FACTOR_AT_UPPER_BOUND_WARNING = (
        "fouling_energy_penalty_factor_at_upper_bound_warning"
    )
    DISCOUNT_RATE_ZERO_WARNING = "discount_rate_zero_warning"
    RESTRICTED_ONLY_PROVENANCE_WARNING = "restricted_only_provenance_warning"
    UNSPECIFIED_WARNING = "unspecified_warning"


# Concrete ``Final`` tuples for runtime guards + closed-set inventory assertions.
BLOCKER_CODES: Final[tuple[str, ...]] = tuple(c.value for c in BlockerCode)
WARNING_CODES: Final[tuple[str, ...]] = tuple(c.value for c in WarningCode)


__all__ = [
    "BLOCKER_CODES",
    "BlockerCode",
    "CostSelectorError",
    "CostSelectorWarning",
    "WARNING_CODES",
    "WarningCode",
]
