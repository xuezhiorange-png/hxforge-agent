"""Disclose actual CoolProp provider identity for experimental runs."""

from __future__ import annotations

import subprocess
from typing import Any

from hexagent.exchangers.shell_tube.task172_local_runtime.models import PROFILE_ID
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import REFERENCE_PRESSURE_PA
from hexagent.properties.base import ReferenceStatePolicy
from hexagent.properties.coolprop_provider import CoolPropProvider


def _solver_source_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_property_provider_identity(provider: CoolPropProvider) -> dict[str, Any]:
    return {
        "schema_version": "hxforge.property-provider-identity.v1",
        "provider_class": "CoolPropProvider",
        "provider_name": "CoolProp HEOS",
        "coolprop_version": provider.version,
        "coolprop_git_revision": provider.git_revision,
        "property_profile_id": PROFILE_ID,
        "reference_pressure_pa": str(REFERENCE_PRESSURE_PA),
        "reference_state_policy": ReferenceStatePolicy.DEF.name,
        "solver_source_revision": _solver_source_revision(),
    }
