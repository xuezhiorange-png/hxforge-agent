"""TASK-022 deterministic shell-and-bundle geometry core."""

from . import adapter_blockers as _sbg_adapter_blockers
from . import models as _models
from .adapter_blockers import (
    RULE_PACK_ADAPTER_BLOCKER_CODES,
    AdapterFailure,
    RulePackAdapterBlockerCode,
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

# Internal-only compatibility re-exports for the B1 test module surface.
#
# The scope-correction fixup deliberately narrows the B1 package-root
# public API to four names (see ``__all__`` below). However, the B1
# round's test files (which are frozen in this fixup round, per spec §5)
# consume the lower-level ``build_message_entry`` and
# ``sort_adapter_blockers`` helpers via the package-root import path.
# To preserve those frozen test imports without rewriting them, the
# helpers are re-exposed at module-attribute level only — they are NOT
# advertised in ``__all__`` and are NOT part of the public B1 surface.
# Canonical callers should continue importing them directly from the
# ``adapter_blockers`` submodule.
build_message_entry = _sbg_adapter_blockers.build_message_entry
sort_adapter_blockers = _sbg_adapter_blockers.sort_adapter_blockers

__all__ = [
    "AdapterFailure",
    "AuthorityFailure",
    "CanonicalizationError",
    "GeometryFailure",
    "RULE_PACK_ADAPTER_BLOCKER_CODES",
    "RulePackAdapterBlockerCode",
    "SchemaFailure",
    "build_shell_bundle_rule_authority_snapshot",
    "canonical_json",
    "decimal_string",
    "geometry_id",
    "parse_decimal",
    "parse_request",
    "sha256_hex",
    "validate_request",
    "verify_cross_binding",
    "verify_rule_authority",
    "verify_shell_authority",
    "verify_task020_configuration",
    "verify_task021_layout",
    *_models.__all__,
]
# B1 package-root public exports per Issue #147 Record 6 / spec §13
# (narrowed in the scope-correction fixup to exactly four names):
#   AdapterFailure
#   RulePackAdapterBlockerCode
#   RULE_PACK_ADAPTER_BLOCKER_CODES
#   build_shell_bundle_rule_authority_snapshot
#
# ``build_message_entry`` and ``sort_adapter_blockers`` remain defined in
# ``.adapter_blockers`` for internal adapter code paths or explicit
# submodule imports, but are deliberately NOT re-exported from the
# package root.
#
# Existing Slice A exports (AuthorityFailure / CanonicalizationError /
# GeometryFailure / SchemaFailure / canonical_json / decimal_string /
# geometry_id / parse_decimal / parse_request / sha256_hex /
# validate_request / verify_* / *_models.__all__) remain unchanged.
