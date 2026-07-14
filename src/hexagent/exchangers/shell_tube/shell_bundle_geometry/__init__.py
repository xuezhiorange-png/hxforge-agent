"""TASK-022 deterministic shell-and-bundle geometry core."""

from . import models as _models
from .adapter_blockers import (
    RULE_PACK_ADAPTER_BLOCKER_CODES,
    AdapterFailure,
    RulePackAdapterBlockerCode,
    build_message_entry,
    sort_adapter_blockers,
)
from .authority import (
    AuthorityFailure,
    verify_cross_binding,
    verify_rule_authority,
    verify_shell_authority,
    verify_task020_configuration,
    verify_task021_layout,
)
from .canonical import (
    CanonicalizationError,
    canonical_json,
    decimal_string,
    geometry_id,
    parse_decimal,
    sha256_hex,
)
from .geometry import GeometryFailure
from .models import *  # noqa: F403
from .rule_pack_adapter import build_shell_bundle_rule_authority_snapshot
from .schema import SchemaFailure, parse_request
from .validation import validate_request

__all__ = [
    "AdapterFailure",
    "AuthorityFailure",
    "CanonicalizationError",
    "GeometryFailure",
    "RULE_PACK_ADAPTER_BLOCKER_CODES",
    "RulePackAdapterBlockerCode",
    "SchemaFailure",
    "build_message_entry",
    "build_shell_bundle_rule_authority_snapshot",
    "canonical_json",
    "decimal_string",
    "geometry_id",
    "parse_decimal",
    "parse_request",
    "sha256_hex",
    "sort_adapter_blockers",
    "validate_request",
    "verify_cross_binding",
    "verify_rule_authority",
    "verify_shell_authority",
    "verify_task020_configuration",
    "verify_task021_layout",
    *_models.__all__,
]
# Narrow additive B1 exports per Issue #147 Record 6 / spec §13:
# AdapterFailure, RulePackAdapterBlockerCode,
# RULE_PACK_ADAPTER_BLOCKER_CODES, build_message_entry,
# sort_adapter_blockers, build_shell_bundle_rule_authority_snapshot.
# Existing Slice A exports (AuthorityFailure / CanonicalizationError /
# GeometryFailure / SchemaFailure / canonical_json / decimal_string /
# geometry_id / parse_decimal / parse_request / sha256_hex /
# validate_request / verify_* / *_models.__all__) remain unchanged.
