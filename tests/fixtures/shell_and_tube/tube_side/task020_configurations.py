"""TASK-020 identity fixtures (CONFIG-A / CONFIG-B)."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.models import (
    AuthorityMode,
    ConstructionFamily,
    EquipmentFamily,
    Orientation,
    ShellAndTubeConfiguration,
    StandardClaimStatus,
)


def config_a() -> ShellAndTubeConfiguration:
    """CONFIG-A — shell-and-tube, fixed-tubesheet, horizontal, 1 pass / 1 pass."""
    return ShellAndTubeConfiguration(
        schema_version="task020.configuration.v1",
        configuration_id="config-a-001",
        configuration_hash="a" * 64,
        equipment_family=EquipmentFamily.SHELL_AND_TUBE,
        authority_mode=AuthorityMode.INTERNAL_GENERIC,
        standard_claim_status=StandardClaimStatus.NO_STANDARD_CLAIM,
        construction_family=ConstructionFamily.FIXED_TUBESHEET,
        orientation=Orientation.HORIZONTAL,
        shell_pass_count=1,
        tube_pass_count=1,
        component_tokens=None,  # type: ignore[arg-type]
        authority_binding=None,  # type: ignore[arg-type]
        case_authority=None,  # type: ignore[arg-type]
    )


def config_b() -> ShellAndTubeConfiguration:
    """CONFIG-B — same family but different identity (for negative tests)."""
    return ShellAndTubeConfiguration(
        schema_version="task020.configuration.v1",
        configuration_id="config-b-002",
        configuration_hash="f" * 64,
        equipment_family=EquipmentFamily.SHELL_AND_TUBE,
        authority_mode=AuthorityMode.INTERNAL_GENERIC,
        standard_claim_status=StandardClaimStatus.NO_STANDARD_CLAIM,
        construction_family=ConstructionFamily.FIXED_TUBESHEET,
        orientation=Orientation.VERTICAL,
        shell_pass_count=1,
        tube_pass_count=1,
        component_tokens=None,  # type: ignore[arg-type]
        authority_binding=None,  # type: ignore[arg-type]
        case_authority=None,  # type: ignore[arg-type]
    )


__all__ = ["config_a", "config_b"]
