"""TASK-025 unique typed request schema.

§5 — Task025Request exact public field tuple.
"""

from __future__ import annotations

from dataclasses import dataclass

from hexagent.exchangers.shell_tube.models import ShellAndTubeConfiguration
from hexagent.exchangers.shell_tube.tube_layout.models import TubeLayout
from hexagent.exchangers.shell_tube.tube_side.hydraulic_participation_authority import (
    Task025HydraulicParticipationAuthority,
)
from hexagent.exchangers.shell_tube.tube_side.length_authorities import (
    HeatTransferLengthAuthority,
    InternalFlowLengthAuthority,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    FlowPathMode,
    HydraulicAuthorityMode,
)

# §5.1 — TASK025_REQUEST_FIELDS tuple.
TASK025_REQUEST_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "task020_configuration",
    "task021_layout",
    "internal_flow_authority",
    "heat_transfer_authority",
    "hydraulic_participation_authority",
    "flow_path_mode",
    "hydraulic_authority_mode",
    "evidence_refs",
)


# §5.7 — Supported profile-id and software-version.
SUPPORTED_PROFILE_IDS: tuple[str, ...] = ("profile-001",)
SUPPORTED_SOFTWARE_VERSION: tuple[str, ...] = ("0.1.0",)


def _validate_non_empty_string_tuple(
    value: tuple[str, ...] | list[str], field_path: str
) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{field_path} must be a tuple/list of str")
    items = tuple(value)
    for item in items:
        if not isinstance(item, str) or not item:
            raise ValueError(f"{field_path} entries must be non-empty str")
    return items


@dataclass(frozen=True)
class Task025Request:
    """§5 — Unique TASK-025 typed request value object."""

    schema_version: str
    profile_id: str
    task020_configuration: ShellAndTubeConfiguration
    task021_layout: TubeLayout
    internal_flow_authority: InternalFlowLengthAuthority
    heat_transfer_authority: HeatTransferLengthAuthority
    hydraulic_participation_authority: Task025HydraulicParticipationAuthority
    flow_path_mode: FlowPathMode
    hydraulic_authority_mode: HydraulicAuthorityMode
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise ValueError("schema_version must be a non-empty str")
        if not isinstance(self.profile_id, str) or not self.profile_id:
            raise ValueError("profile_id must be a non-empty str")
        if self.profile_id not in SUPPORTED_PROFILE_IDS:
            raise ValueError(
                f"profile_id must be one of {SUPPORTED_PROFILE_IDS!r}; got {self.profile_id!r}"
            )
        if not isinstance(self.task020_configuration, ShellAndTubeConfiguration):
            raise ValueError(
                "task020_configuration must be ShellAndTubeConfiguration; "
                f"got {type(self.task020_configuration).__name__}"
            )
        if not isinstance(self.task021_layout, TubeLayout):
            raise ValueError(
                "task021_layout must be TubeLayout; "
                f"got {type(self.task021_layout).__name__}"
            )
        if not isinstance(self.internal_flow_authority, InternalFlowLengthAuthority):
            raise ValueError(
                "internal_flow_authority must be InternalFlowLengthAuthority; "
                f"got {type(self.internal_flow_authority).__name__}"
            )
        if not isinstance(self.heat_transfer_authority, HeatTransferLengthAuthority):
            raise ValueError(
                "heat_transfer_authority must be HeatTransferLengthAuthority; "
                f"got {type(self.heat_transfer_authority).__name__}"
            )
        if not isinstance(
            self.hydraulic_participation_authority,
            Task025HydraulicParticipationAuthority,
        ):
            raise ValueError(
                "hydraulic_participation_authority must be "
                f"Task025HydraulicParticipationAuthority; got "
                f"{type(self.hydraulic_participation_authority).__name__}"
            )
        if not isinstance(self.flow_path_mode, FlowPathMode):
            raise ValueError(
                "flow_path_mode must be FlowPathMode; "
                f"got {type(self.flow_path_mode).__name__}"
            )
        if not isinstance(self.hydraulic_authority_mode, HydraulicAuthorityMode):
            raise ValueError(
                "hydraulic_authority_mode must be HydraulicAuthorityMode; "
                f"got {type(self.hydraulic_authority_mode).__name__}"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_non_empty_string_tuple(self.evidence_refs, "evidence_refs"),
        )


__all__ = [
    "Task025Request",
    "TASK025_REQUEST_FIELDS",
    "SUPPORTED_PROFILE_IDS",
    "SUPPORTED_SOFTWARE_VERSION",
]