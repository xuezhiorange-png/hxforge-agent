"""TASK-020 Shell-and-Tube Configuration Schema Foundation.

This package implements TASK-020 Design Contract Slice A:

- Domain models (request, normalized configuration, validation result)
- Strict schema validation
- CaseRevisionAuthority binding (read-only value object, no persistence)
- Normalization (structural token, ordering)
- Warning/blocker objects (fail-closed)
- Canonical serialization (deterministic SHA-256 + UUIDv5)
- Internal-generic mode (full pipeline; APPROVED_RULE_PACK emits blocker)

Scope per TASK-020 design §16.1: Slice A does NOT load or evaluate rule
packs. Approved-rule-pack mode emits ``STC_RULE_PACK_REQUIRED`` blocker.

Architecture
------------
Package: ``src/hexagent/exchangers/shell_tube/``
Pattern follows ``src/hexagent/case_revisions/`` (TASK-014) and
``src/hexagent/validation_report/`` (TASK-019).

Forbidden
---------
- Heat transfer / thermal rating / pressure drop calculations
- Kern / Bell–Delaware / TEMA calculation logic
- Cost stack / CAPEX / OPEX / discount / salvage
- TASK-021 through TASK-039 capability allocation
- Persistence queries
- Mutating frozen TASK-001 through TASK-019 contract files
"""

from __future__ import annotations

from hexagent.exchangers.shell_tube import (
    authority,
    canonical,
    errors,
    models,
    schema,
    validation,
)

# Public surface — only the stable types and entry points.
__all__ = [
    # Submodules
    "authority",
    "canonical",
    "errors",
    "models",
    "schema",
    "validation",
    # Schema-version constants (used by callers and tests).
    "REQUEST_SCHEMA_VERSION",
    "CONFIGURATION_SCHEMA_VERSION",
    # Top-level entry point.
    "validate_request",
    # Stable types re-exported for convenience.
    "AuthorityMode",
    "CaseRevisionAuthority",
    "ComponentTokens",
    "ConfigurationAuthorityBinding",
    "ConfigurationValidationResult",
    "ConstructionFamily",
    "EquipmentFamily",
    "EvaluatedRulePackAuthority",
    "Orientation",
    "RequestRulePackIdentity",
    "RequestedRulePackIdentity",
    "SelectedRuleAuthority",
    "ShellAndTubeConfiguration",
    "ShellAndTubeConfigurationRequest",
    "StandardClaimStatus",
    "ValidationStatus",
]

# Stable types re-exported for convenience. These are also re-exported
# from ``models``; we import from ``models`` here to keep the
# public-surface contract in a single location.
from hexagent.exchangers.shell_tube.models import (
    AuthorityMode,
    CaseRevisionAuthority,
    ComponentTokens,
    ConfigurationAuthorityBinding,
    ConfigurationValidationResult,
    ConstructionFamily,
    EquipmentFamily,
    EvaluatedRulePackAuthority,
    Orientation,
    RequestedRulePackIdentity,
    RequestRulePackIdentity,
    SelectedRuleAuthority,
    ShellAndTubeConfiguration,
    ShellAndTubeConfigurationRequest,
    StandardClaimStatus,
    ValidationStatus,
)
from hexagent.exchangers.shell_tube.validation import validate_request

# Schema-version constants are frozen at the values fixed in
# ``docs/tasks/TASK-020-shell-and-tube-configuration-schema.md`` §8.1 and §9.1.
REQUEST_SCHEMA_VERSION = "task020.configuration-request.v1"
CONFIGURATION_SCHEMA_VERSION = "task020.configuration.v1"
