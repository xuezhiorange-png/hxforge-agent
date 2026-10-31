"""Experimental live-rating run identity (not production rating request authority)."""

from __future__ import annotations

import subprocess
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    EXPERIMENTAL_THERMAL_BOUNDARY_AUTHORITY_ID,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.property_provider_identity import (
    build_property_provider_identity,
)


def _git_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_experimental_live_rating_run_identity(
    *,
    case: EngineeringCase,
    native_candidate_id: str,
    native_candidate_hash: str,
    rating_request_hash: str,
    task171_result_hash: str,
    task174_result_hash: str,
    task025_parallel_area_m2: str,
    thermal_boundary_binding_doc: dict[str, Any],
    mesh_level: int,
    enable_ephemeral_tp_cache: bool,
    provider: CoolPropProvider,
    candidate_rating_entries: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    """Build disclosure + EXPERIMENTAL_LIVE_RATING_RUN_HASH."""
    provider_identity = build_property_provider_identity(provider)
    payload_for_hash = {
        "schema_version": "hxforge.experimental-live-rating-run-identity.v1",
        "native_candidate_rating_request_hash": rating_request_hash,
        "candidate_id": native_candidate_id,
        "candidate_hash": native_candidate_hash,
        "task171_result_hash": task171_result_hash,
        "task174_result_hash": task174_result_hash,
        "task025_parallel_area_m2": task025_parallel_area_m2,
        "engineering_case_id": case.engineering_case_id,
        "tube_inlet_temperature_k": thermal_boundary_binding_doc.get("tube_inlet_temperature_k"),
        "shell_inlet_temperature_k": thermal_boundary_binding_doc.get("shell_inlet_temperature_k"),
        "tube_inlet_enthalpy_j_kg": thermal_boundary_binding_doc.get("tube_inlet_enthalpy_j_kg"),
        "shell_inlet_enthalpy_j_kg": thermal_boundary_binding_doc.get("shell_inlet_enthalpy_j_kg"),
        "tube_mass_flow_kg_s": thermal_boundary_binding_doc.get("tube_mass_flow_kg_s"),
        "shell_mass_flow_kg_s": thermal_boundary_binding_doc.get("shell_mass_flow_kg_s"),
        "experimental_thermal_boundary_authority_id": EXPERIMENTAL_THERMAL_BOUNDARY_AUTHORITY_ID,
        "experimental_thermal_boundary_binding_hash": canonical_sha256(
            {
                "tube_inlet_temperature_k": thermal_boundary_binding_doc.get(
                    "tube_inlet_temperature_k"
                ),
                "shell_inlet_temperature_k": thermal_boundary_binding_doc.get(
                    "shell_inlet_temperature_k"
                ),
                "tube_inlet_enthalpy_j_kg": thermal_boundary_binding_doc.get(
                    "tube_inlet_enthalpy_j_kg"
                ),
                "shell_inlet_enthalpy_j_kg": thermal_boundary_binding_doc.get(
                    "shell_inlet_enthalpy_j_kg"
                ),
                "tube_mass_flow_kg_s": thermal_boundary_binding_doc.get("tube_mass_flow_kg_s"),
                "shell_mass_flow_kg_s": thermal_boundary_binding_doc.get("shell_mass_flow_kg_s"),
                "authority_id": thermal_boundary_binding_doc.get("authority_id"),
            }
        ),
        "property_provider_identity": provider_identity,
        "candidate_rating_entries": candidate_rating_entries,
        "git_revision": _git_revision(),
        "solver_source_revision": provider_identity["solver_source_revision"],
        "mesh_level": mesh_level,
        "enable_ephemeral_tp_cache": enable_ephemeral_tp_cache,
        "mode": "experimental-live-rating",
    }
    run_hash = canonical_sha256(payload_for_hash)
    return {
        **payload_for_hash,
        "EXPERIMENTAL_LIVE_RATING_RUN_HASH": run_hash,
        "production_rating_request_hash_semantics": "UNCHANGED_NATIVE_CANDIDATE_HASH_ONLY",
        "numerical_authority_status": "CANDIDATE",
        "disclosure": disclosure_document_from_doc(thermal_boundary_binding_doc),
    }


def disclosure_document_from_doc(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "binding_status": doc.get("binding_status"),
        "authority_id": doc.get("authority_id"),
        "participates_in_task173_mesh": doc.get("participates_in_task173_mesh"),
    }
