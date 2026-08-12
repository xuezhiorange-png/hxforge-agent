"""Task028Request 11-field dataclass, build_task028_request factory.

§11 — Request contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from hexagent.exchangers.shell_tube.tube_side.valid_result import Task025ValidResult
from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
    SUPPORTED_PROFILE_IDS,
    TASK028_REQUEST_SCHEMA_VERSION,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.enums import (
    Task028ApplicabilityAssertion,
    Task028RequestFlowDirectionAssertion,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.models import (
    TubeSideLocalLossComponentAuthority,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.property_snapshot import PropertySnapshot
from hexagent.exchangers.shell_tube.tube_side_thermal.result import TubeSideThermalResult


@dataclass(frozen=True)
class Task028Request:
    """§4.2 — Layer B: 11-field typed request. Only valid upstream results accepted."""

    schema_version: str
    profile_id: str
    task025_valid_result: Task025ValidResult
    task026_success_result: TubeSideThermalResult
    property_snapshot: PropertySnapshot
    property_snapshot_hash: str
    constant_density_path_assertion: Task028ApplicabilityAssertion
    zero_net_elevation_change_assertion: Task028ApplicabilityAssertion
    flow_direction_assertion: Task028RequestFlowDirectionAssertion
    component_authorities: tuple[TubeSideLocalLossComponentAuthority, ...]
    request_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != TASK028_REQUEST_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be '{TASK028_REQUEST_SCHEMA_VERSION}'")
        if self.profile_id not in SUPPORTED_PROFILE_IDS:
            raise ValueError(f"profile_id must be one of {SUPPORTED_PROFILE_IDS}")


def build_task028_request(
    *,
    profile_id: str,
    task025_valid_result: Task025ValidResult,
    task026_success_result: TubeSideThermalResult,
    property_snapshot: PropertySnapshot,
    property_snapshot_hash: str,
    constant_density_path_assertion: Task028ApplicabilityAssertion,
    zero_net_elevation_change_assertion: Task028ApplicabilityAssertion,
    flow_direction_assertion: Task028RequestFlowDirectionAssertion,
    component_authorities: tuple[TubeSideLocalLossComponentAuthority, ...],
    request_hash: str,
) -> Task028Request:
    """Build a frozen Task028Request with schema_version from constants."""
    return Task028Request(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id=profile_id,
        task025_valid_result=task025_valid_result,
        task026_success_result=task026_success_result,
        property_snapshot=property_snapshot,
        property_snapshot_hash=property_snapshot_hash,
        constant_density_path_assertion=constant_density_path_assertion,
        zero_net_elevation_change_assertion=zero_net_elevation_change_assertion,
        flow_direction_assertion=flow_direction_assertion,
        component_authorities=component_authorities,
        request_hash=request_hash,
    )


__all__ = [
    "Task028Request",
    "build_task028_request",
]
