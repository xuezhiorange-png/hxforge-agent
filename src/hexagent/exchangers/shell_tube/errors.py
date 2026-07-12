"""TASK-020 domain error types.

Domain error categories for the TASK-020 configuration schema pipeline.
These are **value-error sentinels** — every error is identified by a frozen
``STC_*`` code from the §10.2 / §10.3 closed set in the TASK-020 design
contract, never by free-form string. The full set of blocker / warning
codes is defined in ``models.py``; this module provides the error *class*
hierarchy and the ``STCErrorCode`` base enumeration.

All TASK-020 errors MUST be raised as ``ShellTubeError`` or one of its
subclasses so that the validation layer can convert them into stable
``ConfigurationValidationResult.blockers`` entries.

S2 (Amendment 002) reserved-codes audit
----------------------------------------

The following ``STC_*`` codes are declared in the §10.2 closed list for
historical / forward-compatibility reasons but MUST NOT be raised by the
TASK-020-S2 adapter (per §20.C + §20.E of the design contract). They are
**reserved** — TASK-020 reads only ``validation_report.status`` (not the
free-form ``errors[*].message``) and does not re-verify approval /
canonical-hash / license / provenance. ``STC_REQUIRED_RULE_MISSING`` is
likewise reserved because the §12.9 required-constraint matrix gap is
emitted as ``STC_RULE_CONSTRAINT_MISSING`` and the two are not aliases.

The frozen set is exposed here as ``RESERVED_S2_BLOCKER_CODES`` so the
adapter can assert guard-level invariants in tests / adapters
(``assert code not in RESERVED_S2_BLOCKER_CODES``).
"""

from __future__ import annotations

from hexagent.exchangers.shell_tube.models import (
    BlockerCode,
    WarningCode,
)


class ShellTubeError(Exception):
    """Base class for all TASK-020 domain errors.

    Subclasses MUST carry a stable ``STC_*`` code so that the validation
    layer can convert the error into a blocker / warning object without
    parsing exception messages.
    """

    code: str

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


class BlockerError(ShellTubeError):
    """A TASK-020 blocker — validation MUST fail closed on these."""


class WarningSignal(ShellTubeError):
    """A TASK-020 warning — validation may succeed with these surfaced.

    Warnings are non-blocking by definition (§10.3). This class exists
    so callers can signal "produce a warning, not an exception" by
    raising it from a domain check.
    """


# Sentinel: a closed list of every error code that the validation layer
# is allowed to emit. This is a runtime assertion aid, NOT a substitute
# for the static closed sets in §10.2 / §10.3 of the design contract.
ALL_BLOCKER_CODES: frozenset[str] = frozenset(c.value for c in BlockerCode)
ALL_WARNING_CODES: frozenset[str] = frozenset(c.value for c in WarningCode)


# S2 reserved codes — declared in the §10.2 closed list but NOT raised by
# the TASK-020-S2 adapter. See module docstring for the §20.C / §20.E
# rationale.
RESERVED_S2_BLOCKER_CODES: frozenset[str] = frozenset(
    {
        "STC_RULE_UNAPPROVED",
        "STC_RULE_CANONICAL_HASH_MISMATCH",
        "STC_RULE_LICENSE_BLOCKED",
        "STC_RULE_PROVENANCE_BLOCKED",
        "STC_REQUIRED_RULE_MISSING",
    }
)

# S2 intersection-empty family — three per-rule-type codes
# (range / orientation / token). Round §5 / §6.7 references
# ``STC_RULE_INTERSECTION_EMPTY`` generically; the closed list emits
# one of the three type-specific codes instead.
S2_INTERSECTION_EMPTY_FAMILY: frozenset[str] = frozenset(
    {
        "STC_RULE_RANGE_INTERSECTION_EMPTY",
        "STC_RULE_ORIENTATION_INTERSECTION_EMPTY",
        "STC_RULE_TOKEN_INTERSECTION_EMPTY",
    }
)


__all__ = [
    "ALL_BLOCKER_CODES",
    "ALL_WARNING_CODES",
    "BlockerError",
    "RESERVED_S2_BLOCKER_CODES",
    "S2_INTERSECTION_EMPTY_FAMILY",
    "ShellTubeError",
    "WarningSignal",
]
