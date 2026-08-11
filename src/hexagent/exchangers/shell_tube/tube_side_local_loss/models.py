"""TASK-028 core dataclasses: Authority (17-field), ComponentResult (14-field).

§5 — Authority, §12 — Component result.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from hexagent.exchangers.shell_tube.tube_side_local_loss.enums import (
    CoefficientPermissionStatus,
    LossCoefficientConvention,
    Task028ComponentFlowDirectionAssertion,
    Task028ComponentType,
)

# §5 — 17-field authority
AUTHORITY_FIELD_COUNT: Final[int] = 17

# §12 — 14-field component result
COMPONENT_RESULT_FIELD_COUNT: Final[int] = 14

# §5 — Source authority (8 frozen fields)
TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELDS: Final[tuple[str, ...]] = (
    "source_id",
    "source_title",
    "source_version",
    "source_location",
    "source_scope",
    "admitted_formula",
    "admitted_coefficient_semantics",
    "permission_status",
)
TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELD_COUNT: Final[int] = 8

# §7 — Frozen source authority values
TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_ID: Final[str] = "USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL"
TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_TITLE: Final[str] = "USACE HEC-RAS Hydraulic Reference Manual"
TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_VERSION: Final[str] = "2024.1"
TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_LOCATION: Final[str] = (
    "USACE HEC-RAS Hydraulic Reference Manual, Section 6.2.1"
)
TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_SCOPE: Final[str] = (
    "Pipe Minor Losses, entrance/exit local velocity-head loss treatment, "
    "Expansion and Contraction Coefficients"
)
TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FORMULA: Final[str] = (
    "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2"
)
TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_COEFFICIENT_SEMANTICS: Final[str] = (
    "IRREVERSIBLE_LOCAL_LOSS_COEFFICIENT"
)
TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_PERMISSION_STATUS: Final[str] = "ADMITTED"


@dataclass(frozen=True)
class Task028LocalLossSourceAuthority:
    """§7 — Frozen source authority as a typed dataclass for injectable test seam."""

    source_id: str
    source_title: str
    source_version: str
    source_location: str
    source_scope: str
    admitted_formula: str
    admitted_coefficient_semantics: str
    permission_status: str


_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY = Task028LocalLossSourceAuthority(
    source_id="USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL",
    source_title="USACE HEC-RAS Hydraulic Reference Manual",
    source_version="2024.1",
    source_location="USACE HEC-RAS Hydraulic Reference Manual, Section 6.2.1",
    source_scope=(
        "Pipe Minor Losses, entrance/exit local velocity-head loss treatment, "
        "Expansion and Contraction Coefficients"
    ),
    admitted_formula="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
    admitted_coefficient_semantics="IRREVERSIBLE_LOCAL_LOSS_COEFFICIENT",
    permission_status="ADMITTED",
)


@dataclass(frozen=True)
class TubeSideLocalLossComponentAuthority:
    """§5 — Immutable 17-field component authority record.

    Ordered fields exactly match the canonical hash projection.
    Fields 1–16 are included in the authority_hash computation (field 17).
    """

    schema_version: str
    component_id: str
    component_type: Task028ComponentType
    path_sequence_index: int
    upstream_reference_plane: str
    downstream_reference_plane: str
    flow_direction_assertion: Task028ComponentFlowDirectionAssertion
    loss_coefficient: Decimal
    loss_coefficient_convention: LossCoefficientConvention
    reference_flow_area_m2: Decimal
    multiplicity: int
    geometry_evidence_refs: tuple[str, ...]
    coefficient_source_id: str
    coefficient_source_version: str
    coefficient_source_location: str
    coefficient_permission_status: CoefficientPermissionStatus
    authority_hash: str


@dataclass(frozen=True)
class TubeSideLocalLossComponentResult:
    """§12 — Immutable 14-field component result record."""

    component_id: str
    component_type: Task028ComponentType
    path_sequence_index: int
    upstream_reference_plane: str
    downstream_reference_plane: str
    flow_direction_assertion: Task028ComponentFlowDirectionAssertion
    authority_hash: str
    reference_flow_area_m2: Decimal
    reference_velocity_m_s: Decimal
    loss_coefficient: Decimal
    loss_coefficient_convention: LossCoefficientConvention
    multiplicity: int
    single_occurrence_irreversible_pressure_loss_pa: Decimal
    component_irreversible_pressure_loss_pa: Decimal


__all__ = [
    "AUTHORITY_FIELD_COUNT",
    "COMPONENT_RESULT_FIELD_COUNT",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELDS",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELD_COUNT",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_ID",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_TITLE",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_VERSION",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_LOCATION",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_SCOPE",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FORMULA",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_COEFFICIENT_SEMANTICS",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_PERMISSION_STATUS",
    "TubeSideLocalLossComponentAuthority",
    "TubeSideLocalLossComponentResult",
    "Task028LocalLossSourceAuthority",
    "_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY",
]
