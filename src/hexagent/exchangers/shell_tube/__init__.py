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
    rule_pack_adapter,
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
    "rule_pack_adapter",
    "schema",
    "validation",
    # Schema-version constants (used by callers and tests).
    "REQUEST_SCHEMA_VERSION",
    "CONFIGURATION_SCHEMA_VERSION",
    # Top-level entry points.
    "validate_request",
    "ConfigurationRulePackAdapter",
    # Stable types re-exported for convenience.
    "AuthorityMode",
    "CASE_REVISION_AUTHORITY_VALUES",
    "CLOSED_RULE_TYPES",
    "CaseRevisionAuthority",
    "ComponentTokens",
    "ConfigurationAuthorityBinding",
    "ConfigurationRuleEvaluation",
    "ConfigurationValidationResult",
    "ConstructionFamily",
    "EquipmentFamily",
    "EvaluatedRulePackAuthority",
    "LoadedRulePackView",
    "Orientation",
    "PROFILE_ID_TASK_020_CONFIGURATION_RULE_V1",
    "RequestRulePackIdentity",
    "RequestedRulePackIdentity",
    "RulePackValidationReport",
    "SelectedRuleAuthority",
    "ShellAndTubeConfiguration",
    "ShellAndTubeConfigurationRequest",
    "StandardClaimStatus",
    "TASK_020_VALIDATION_REPORT_OK",
    "ValidationStatus",
    "loaded_rule_pack_view_from_loader_dict",
    "rule_pack_validation_report_from_validate_dict",
]  # noqa: E501

# Stable types re-exported for convenience. These are also re-exported
# from ``models``; we import from ``models`` here to keep the
# public-surface contract in a single location.
from hexagent.exchangers.shell_tube.models import (
    CASE_REVISION_AUTHORITY_VALUES,
    CLOSED_RULE_TYPES,
    PROFILE_ID_TASK_020_CONFIGURATION_RULE_V1,
    TASK_020_VALIDATION_REPORT_OK,
    AuthorityMode,
    CaseRevisionAuthority,
    ComponentTokens,
    ConfigurationAuthorityBinding,
    ConfigurationRuleEvaluation,
    ConfigurationValidationResult,
    ConstructionFamily,
    EquipmentFamily,
    EvaluatedRulePackAuthority,
    LoadedRulePackView,
    Orientation,
    RequestedRulePackIdentity,
    RequestRulePackIdentity,
    RulePackValidationReport,
    SelectedRuleAuthority,
    ShellAndTubeConfiguration,
    ShellAndTubeConfigurationRequest,
    StandardClaimStatus,
    ValidationStatus,
)
from hexagent.exchangers.shell_tube.rule_pack_adapter import (
    ConfigurationRulePackAdapter,
    loaded_rule_pack_view_from_loader_dict,
    rule_pack_validation_report_from_validate_dict,
)
from hexagent.exchangers.shell_tube.validation import validate_request

# Schema-version constants are frozen at the values fixed in
# ``docs/tasks/TASK-020-shell-and-tube-configuration-schema.md`` §8.1 and §9.1.
REQUEST_SCHEMA_VERSION = "task020.configuration-request.v1"
CONFIGURATION_SCHEMA_VERSION = "task020.configuration.v1"
