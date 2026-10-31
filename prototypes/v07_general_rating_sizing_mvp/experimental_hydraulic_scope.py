"""Hydraulic evaluation scope disclosure for experimental live rating."""

from __future__ import annotations

from typing import Any


def build_hydraulic_model_scope_document() -> dict[str, Any]:
    return {
        "schema_version": "hxforge.experimental-hydraulic-model-scope.v1",
        "task174_hydraulic_status": "HYDRAULIC_REFERENCE_MODEL_PREVIEW",
        "explanation": (
            "Task174 tube/shell pressure drops are evaluated from the Task168→Task174 "
            "native hydraulic chain at the sizing request thermal templates. They are "
            "not re-coupled to the experimental live tube inlet temperature (e.g. 299.70 K) "
            "during mesh rating. Live-boundary thermal results (duty, outlet temperatures) "
            "use the experimental thermal binding; Δp previews reference Task174 frozen "
            "hydraulic identities."
        ),
        "live_boundary_hydraulic_evaluated": False,
        "live_thermal_boundary_coupled_to_mesh": True,
    }
