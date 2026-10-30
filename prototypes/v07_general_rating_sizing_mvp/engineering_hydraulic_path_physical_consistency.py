"""Physical consistency gates for EngineeringHydraulicPathInputV1 (R26G-A)."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    EngineeringHydraulicPathInputV1,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_transitional_tube_hydraulic import (
    APPLICABILITY_STATUS as R20_TRANSITIONAL_APPLICABILITY,
)

_ALLOWED_UPSTREAM_APPLICABILITY = frozenset({"APPLICABLE", R20_TRANSITIONAL_APPLICABILITY})

_TUBE_RECOMPUTE_OK = frozenset({"SUCCESS", "EXPERIMENTAL_TRANSITIONAL_SUCCESS"})
_SHELL_RECOMPUTE_OK = frozenset({"SUCCESS"})


def _equipment_mass_flow_kg_s(case: EngineeringCase, side: Literal["TUBE", "SHELL"]) -> Decimal:
    if side == "TUBE":
        return Decimal(str(case.tube_side.mass_flow_kg_s))
    return Decimal(str(case.shell_side.mass_flow_kg_s))


def validate_path_input_physical_consistency(
    path_input: EngineeringHydraulicPathInputV1,
    *,
    case: EngineeringCase,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    tube_flows = {c.mass_flow_kg_s for c in path_input.tube_side_components}
    shell_flows = {c.mass_flow_kg_s for c in path_input.shell_external_components}
    equip_tube = _equipment_mass_flow_kg_s(case, "TUBE")
    equip_shell = _equipment_mass_flow_kg_s(case, "SHELL")

    if len(tube_flows) > 1:
        errors.append(
            "PARALLEL_TUBE_FLOW_SPLIT_UNDECLARED: multiple tube mass_flow_kg_s without split contract"
        )
    if len(shell_flows) > 1:
        errors.append(
            "PARALLEL_SHELL_FLOW_SPLIT_UNDECLARED: multiple shell mass_flow_kg_s without split contract"
        )
    for component in path_input.tube_side_components:
        if component.mass_flow_kg_s != equip_tube:
            errors.append(
                f"TUBE_MASS_FLOW_MISMATCH:{component.component_id} "
                f"({component.mass_flow_kg_s}) != equipment ({equip_tube})"
            )
    for component in path_input.shell_external_components:
        if component.mass_flow_kg_s != equip_shell:
            errors.append(
                f"SHELL_MASS_FLOW_MISMATCH:{component.component_id} "
                f"({component.mass_flow_kg_s}) != equipment ({equip_shell})"
            )

    all_components = (
        *path_input.tube_side_components,
        *path_input.shell_external_components,
    )
    seen_ids: set[str] = set()
    for component in all_components:
        if component.component_id in seen_ids:
            errors.append(f"DUPLICATE_COMPONENT_ID:{component.component_id}")
        seen_ids.add(component.component_id)
        side_role = "TUBE_SIDE" if component.side == "TUBE" else "SHELL_SIDE"
        source = component.fluid_density_source
        if source.kind == "CASE_SIDE_INLET" and source.fluid_role != side_role:
            errors.append(
                f"DENSITY_SIDE_MISMATCH:{component.component_id} "
                f"component side={component.side} fluid_role={source.fluid_role}"
            )
        if source.kind == "COOLPROP_TP":
            if source.temperature_k is None or source.pressure_pa is None:
                errors.append(f"COOLPROP_TP_INCOMPLETE:{component.component_id}")
            elif not source.property_source_id or not source.property_source_version:
                errors.append(f"COOLPROP_TP_PROPERTY_SOURCE_UNDECLARED:{component.component_id}")

    for side_name, components in (
        ("TUBE", path_input.tube_side_components),
        ("SHELL", path_input.shell_external_components),
    ):
        indices = [c.path_sequence_index for c in components]
        if len(indices) != len(set(indices)):
            errors.append(f"DUPLICATE_PATH_SEQUENCE_INDEX:{side_name}")
        planes = [c.reference_plane for c in components]
        if len(planes) != len(set(planes)):
            warnings.append(f"DUPLICATE_REFERENCE_PLANE:{side_name}")

    authority_status = assess_engineering_input_authority(path_input)

    return {
        "PHYSICAL_CONSISTENCY_STATUS": "PASS" if not errors else "BLOCKED",
        "physical_consistency_errors": errors,
        "physical_consistency_warnings": warnings,
        "INPUT_AUTHORITY_STATUS": authority_status["INPUT_AUTHORITY_STATUS"],
        "input_authority_detail": authority_status,
    }


def assess_engineering_input_authority(
    path_input: EngineeringHydraulicPathInputV1,
) -> dict[str, Any]:
    authorized_components = [
        c
        for c in (
            *path_input.tube_side_components,
            *path_input.shell_external_components,
        )
        if c.engineering_input_status == "AUTHORIZED_ENGINEERING_INPUT"
    ]
    if not authorized_components:
        return {
            "INPUT_AUTHORITY_STATUS": "DEMONSTRATION_ONLY",
            "verified_authorized_component_count": 0,
            "disclosure": "All components marked DEMONSTRATION.",
        }
    verified = 0
    for component in authorized_components:
        refs = component.geometry_evidence_refs
        if any(ref.startswith("OWNER-APPROVED-") for ref in refs):
            verified += 1
    if verified == len(authorized_components):
        status = "AUTHORIZED_EVIDENCE_PRESENT"
    else:
        status = "INPUT_AUTHORITY_NOT_VERIFIED"
    return {
        "INPUT_AUTHORITY_STATUS": status,
        "verified_authorized_component_count": verified,
        "authorized_component_count": len(authorized_components),
        "disclosure": (
            "AUTHORIZED_ENGINEERING_INPUT string alone does not verify owner approval; "
            "requires geometry_evidence_refs with OWNER-APPROVED- prefix."
        ),
    }


def assess_upstream_hydraulic_postpass_for_full_path(
    postpass: dict[str, Any] | None,
) -> dict[str, Any]:
    if not postpass:
        return {
            "UPSTREAM_POSTPASS_STATUS": "NOT_AVAILABLE",
            "tube_side_numeric_usable": False,
            "shell_side_numeric_usable": False,
            "upstream_blockers": ["POSTPASS_MISSING"],
        }
    blockers: list[str] = []
    tube_status = postpass.get("tube_hydraulic_recompute_status")
    shell_status = postpass.get("shell_hydraulic_recompute_status")
    if tube_status not in _TUBE_RECOMPUTE_OK:
        blockers.append(f"TUBE_HYDRAULIC_RECOMPUTE_{tube_status or 'NOT_EVALUATED'}")
    if shell_status not in _SHELL_RECOMPUTE_OK:
        blockers.append(f"SHELL_HYDRAULIC_RECOMPUTE_{shell_status or 'NOT_EVALUATED'}")
    applicability = postpass.get("correlation_applicability_status")
    if applicability not in _ALLOWED_UPSTREAM_APPLICABILITY:
        blockers.append(f"CORRELATION_APPLICABILITY_{applicability or 'NOT_EVALUATED'}")
    if postpass.get("blockers"):
        blockers.append("HYDRAULIC_POSTPASS_BLOCKERS_PRESENT")
    coolprop_checks = postpass.get("coolprop_outlet_domain_checks") or {}
    for side, check in coolprop_checks.items():
        if isinstance(check, dict) and check.get("ok") is False:
            blockers.append(f"COOLPROP_OUTLET_DOMAIN_{side.upper()}_FAILED")

    tube_usable = not any(b.startswith("TUBE_HYDRAULIC") for b in blockers) and not any(
        b.startswith("CORRELATION") for b in blockers
    )
    shell_usable = not any(b.startswith("SHELL_HYDRAULIC") for b in blockers) and not any(
        b.startswith("CORRELATION") for b in blockers
    )
    if postpass.get("blockers"):
        tube_usable = False
        shell_usable = False

    return {
        "UPSTREAM_POSTPASS_STATUS": "USABLE" if not blockers else "BLOCKED",
        "tube_side_numeric_usable": tube_usable,
        "shell_side_numeric_usable": shell_usable,
        "upstream_blockers": blockers,
        "partial_model_tube_dp_constraint": postpass.get("tube_dp_constraint"),
        "partial_model_shell_dp_constraint": postpass.get("shell_dp_constraint"),
        "disclosure": (
            "NOT_SATISFIED on partial dp_constraint does not block full-path Δp composition; "
            "BLOCKED recompute status does."
        ),
    }


def postpass_embedded_local_loss_pa(postpass: dict[str, Any]) -> Decimal:
    total = Decimal("0")
    for comp in (postpass.get("tube_local_loss_engineering") or {}).get(
        "computed_local_loss_components"
    ) or []:
        loss = comp.get("component_irreversible_pressure_loss_pa")
        if loss is not None:
            total += Decimal(str(loss))
    return total


def postpass_embedded_local_component_ids(postpass: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for comp in (postpass.get("tube_local_loss_engineering") or {}).get(
        "computed_local_loss_components"
    ) or []:
        cid = comp.get("component_id")
        if cid:
            ids.add(str(cid))
    return ids


def validate_no_duplicate_local_loss_with_postpass(
    path_input: EngineeringHydraulicPathInputV1,
    postpass: dict[str, Any],
) -> list[str]:
    embedded_ids = postpass_embedded_local_component_ids(postpass)
    errors: list[str] = []
    for component in path_input.tube_side_components:
        if component.component_id in embedded_ids:
            errors.append(f"DUPLICATE_LOCAL_LOSS_ALREADY_IN_POSTPASS:{component.component_id}")
    return errors


def assess_tube_internal_friction_separation(
    postpass: dict[str, Any],
    *,
    partial_breakdown: dict[str, Any],
) -> tuple[Decimal | None, str, list[str]]:
    """Return (friction_pa, authority, blockers)."""
    blockers: list[str] = []
    exp = postpass.get("experimental_transitional_tube_hydraulic") or {}
    tube_friction = None
    if exp.get("tube_friction_dp_pa") is not None:
        tube_friction = Decimal(str(exp["tube_friction_dp_pa"]))
        return tube_friction, "EXPLICIT_TRANSITIONAL_FRICTION", blockers

    if partial_breakdown.get("TUBE_FRICTION_DP_PA") is not None:
        tube_friction = Decimal(str(partial_breakdown["TUBE_FRICTION_DP_PA"]))
        return tube_friction, "PARTIAL_BREAKDOWN_FRICTION", blockers

    tube_total = postpass.get("recalculated_tube_dp_pa")
    if tube_total is None:
        blockers.append("TUBE_RECALCULATED_DP_MISSING")
        return None, "UNRELIABLE", blockers

    tube_total_d = Decimal(str(tube_total))
    partial_local = partial_breakdown.get("TUBE_LOCAL_LOSS_DP_PA")
    if partial_local is not None:
        tube_friction = tube_total_d - Decimal(str(partial_local))
        return tube_friction, "TOTAL_MINUS_BREAKDOWN_LOCAL", blockers

    if exp.get("tube_local_loss_dp_pa") is not None:
        tube_friction = tube_total_d - Decimal(str(exp["tube_local_loss_dp_pa"]))
        return tube_friction, "TOTAL_MINUS_TRANSITIONAL_LOCAL", blockers

    embedded = postpass_embedded_local_loss_pa(postpass)
    if embedded > 0 or (postpass.get("tube_local_loss_engineering") or {}).get(
        "computed_local_loss_components"
    ):
        tube_friction = tube_total_d - embedded
        return tube_friction, "TOTAL_MINUS_POSTPASS_EMBEDDED_LOCAL", blockers

    if postpass.get("tube_local_loss_engineering") and embedded == 0:
        blockers.append("TUBE_LOCAL_LOSS_DOC_PRESENT_BUT_NO_COMPONENTS")
        return None, "UNRELIABLE", blockers

    if postpass.get("tube_hydraulic_recompute_status") in _TUBE_RECOMPUTE_OK:
        local_doc = postpass.get("tube_local_loss_engineering") or {}
        if not local_doc.get("computed_local_loss_components"):
            return tube_total_d, "PARTIAL_TOTAL_AS_BUNDLE_FRICTION_ONLY", blockers

    blockers.append(
        "TUBE_FRICTION_SEPARATION_UNRELIABLE: cannot split bundle friction from historical local loss"
    )
    return None, "UNRELIABLE", blockers


def assess_full_path_hydraulic_constraints(
    *,
    case: EngineeringCase,
    postpass: dict[str, Any],
    tube_full_dp: Decimal | None,
    shell_full_dp: Decimal | None,
) -> dict[str, Any]:
    tube_inlet_p = Decimal(
        str(postpass.get("tube_inlet_pressure_pa", case.tube_side.inlet_pressure_pa))
    )
    shell_inlet_p = Decimal(
        str(postpass.get("shell_inlet_pressure_pa", case.shell_side.inlet_pressure_pa))
    )
    max_tube = case.max_tube_side_pressure_drop_pa
    max_shell = case.max_shell_side_pressure_drop_pa

    tube_margin = None
    shell_margin = None
    tube_constraint = "NOT_COMPUTED"
    shell_constraint = "NOT_COMPUTED"
    tube_outlet_p = None
    shell_outlet_p = None

    if tube_full_dp is not None:
        tube_margin = max_tube - tube_full_dp
        tube_outlet_p = tube_inlet_p - tube_full_dp
        tube_constraint = "SATISFIED" if tube_full_dp <= max_tube else "NOT_SATISFIED"
    if shell_full_dp is not None:
        shell_margin = max_shell - shell_full_dp
        shell_outlet_p = shell_inlet_p - shell_full_dp
        shell_constraint = "SATISFIED" if shell_full_dp <= max_shell else "NOT_SATISFIED"

    if tube_constraint == "NOT_COMPUTED" or shell_constraint == "NOT_COMPUTED":
        combined = "NOT_COMPUTED"
    elif tube_constraint == "SATISFIED" and shell_constraint == "SATISFIED":
        combined = "SATISFIED"
    else:
        combined = "NOT_SATISFIED"

    return {
        "TUBE_FULL_PATH_DP_MARGIN_PA": str(tube_margin) if tube_margin is not None else None,
        "SHELL_FULL_PATH_DP_MARGIN_PA": str(shell_margin) if shell_margin is not None else None,
        "FULL_PATH_TUBE_CONSTRAINT_STATUS": tube_constraint,
        "FULL_PATH_SHELL_CONSTRAINT_STATUS": shell_constraint,
        "FULL_PATH_HYDRAULIC_STATUS": combined,
        "full_path_tube_outlet_pressure_pa": str(tube_outlet_p)
        if tube_outlet_p is not None
        else None,
        "full_path_shell_outlet_pressure_pa": (
            str(shell_outlet_p) if shell_outlet_p is not None else None
        ),
        "partial_model_tube_dp_constraint": postpass.get("tube_dp_constraint"),
        "partial_model_shell_dp_constraint": postpass.get("shell_dp_constraint"),
        "disclosure": "Full-path constraint status is independent of partial-model nominal flags.",
    }
