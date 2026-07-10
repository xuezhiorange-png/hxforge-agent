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
"""

from __future__ import annotations

import enum

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


__all__ = [
    "ALL_BLOCKER_CODES",
    "ALL_WARNING_CODES",
    "BlockerError",
    "ShellTubeError",
    "WarningSignal",
]
