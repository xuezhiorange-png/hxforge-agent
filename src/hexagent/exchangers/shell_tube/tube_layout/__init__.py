"""TASK-021 deterministic shell-and-tube layout core."""

from .authority import (
    AuthorityFailure,
    verify_geometry_snapshot,
    verify_layout_rule_snapshot,
    verify_task020_configuration,
)
from .canonical import (
    COORDINATE_QUANTUM,
    DECIMAL_PRECISION,
    SQRT_3,
    CanonicalizationError,
    canonical_json,
    layout_id,
    parse_decimal,
    position_id,
    sha256_hex,
)
from .enumeration import (
    Candidate,
    EnumerationFailure,
    EnumerationPlan,
    build_plan,
    enumerate_candidates,
)
from .geometry import (
    AcceptedCoordinate,
    GeometryFailure,
    GeometryResult,
    evaluate_geometry,
)
from . import models as _models
from .models import *  # noqa: F403
from .pairing import (
    PairingFailure,
    canonical_pair,
    canonical_pairs,
    compute_pairing_plan_hash,
    pairing_plan_payload,
    validate_pairing_plan,
)
from .schema import SchemaFailure, parse_request
from .validation import validate_request

__all__ = [
    "AcceptedCoordinate",
    "AuthorityFailure",
    "COORDINATE_QUANTUM",
    "Candidate",
    "CanonicalizationError",
    "DECIMAL_PRECISION",
    "EnumerationFailure",
    "EnumerationPlan",
    "GeometryFailure",
    "GeometryResult",
    "PairingFailure",
    "SQRT_3",
    "SchemaFailure",
    "build_plan",
    "canonical_json",
    "canonical_pair",
    "canonical_pairs",
    "compute_pairing_plan_hash",
    "enumerate_candidates",
    "evaluate_geometry",
    "layout_id",
    "pairing_plan_payload",
    "parse_decimal",
    "parse_request",
    "position_id",
    "sha256_hex",
    "validate_pairing_plan",
    "validate_request",
    "verify_geometry_snapshot",
    "verify_layout_rule_snapshot",
    "verify_task020_configuration",
    *_models.__all__,
]
