"""TASK-022 deterministic shell-and-bundle geometry core."""

from . import models as _models
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
from .schema import SchemaFailure, parse_request
from .validation import validate_request

__all__ = [
    "AuthorityFailure",
    "CanonicalizationError",
    "GeometryFailure",
    "SchemaFailure",
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
