"""Physical consistency gates for EngineeringHydraulicPathInputV1 (R26G-A)."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from hexagent.properties.base import FluidIdentifier
from hexagent.properties.coolprop_provider import CoolPropProvider
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
    return {
        "INPUT_AUTHORITY_STATUS": "INPUT_AUTHORITY_NOT_VERIFIED",
        "verified_authorized_component_count": 0,
        "authorized_component_count": len(authorized_components),
        "disclosure": (
            "AUTHORIZED_ENGINEERING_INPUT and OWNER-APPROVED-* refs do not verify real owner "
            "approval without independent auditable evidence; production eligibility remains closed."
        ),
    }


def _side_upstream_blockers(
    postpass: dict[str, Any],
    side: Literal["TUBE", "SHELL"],
) -> list[str]:
    blockers: list[str] = []
    if postpass.get("hydraulic_constraint_status") == "BLOCKED":
        blockers.append("HYDRAULIC_CONSTRAINT_BLOCKED")
    if postpass.get("blockers"):
        blockers.append("HYDRAULIC_POSTPASS_BLOCKERS_PRESENT")
    applicability = postpass.get("correlation_applicability_status")
    if applicability not in _ALLOWED_UPSTREAM_APPLICABILITY:
        blockers.append(f"CORRELATION_APPLICABILITY_{applicability or 'NOT_EVALUATED'}")

    props = postpass.get("property_inputs") or {}
    if side == "TUBE":
        if postpass.get("tube_hydraulic_recompute_status") not in _TUBE_RECOMPUTE_OK:
            blockers.append(
                f"TUBE_HYDRAULIC_RECOMPUTE_{postpass.get('tube_hydraulic_recompute_status') or 'NOT_EVALUATED'}"
            )
        if postpass.get("recalculated_tube_dp_pa") is None:
            blockers.append("TUBE_RECALCULATED_DP_MISSING")
        if not props.get("tube"):
            blockers.append("TUBE_PROPERTY_INPUT_MISSING")
    else:
        if postpass.get("shell_hydraulic_recompute_status") not in _SHELL_RECOMPUTE_OK:
            blockers.append(
                f"SHELL_HYDRAULIC_RECOMPUTE_{postpass.get('shell_hydraulic_recompute_status') or 'NOT_EVALUATED'}"
            )
        if postpass.get("recalculated_shell_dp_pa") is None:
            blockers.append("SHELL_RECALCULATED_DP_MISSING")
        if not props.get("shell"):
            blockers.append("SHELL_PROPERTY_INPUT_MISSING")

    coolprop_checks = postpass.get("coolprop_outlet_domain_checks") or {}
    side_key = "tube" if side == "TUBE" else "shell"
    check = coolprop_checks.get(side_key)
    if isinstance(check, dict) and check.get("ok") is False:
        blockers.append(f"COOLPROP_OUTLET_DOMAIN_{side}_FAILED")
    return blockers


def assess_upstream_hydraulic_postpass_for_full_path(
    postpass: dict[str, Any] | None,
) -> dict[str, Any]:
    if not postpass:
        return {
            "UPSTREAM_POSTPASS_STATUS": "NOT_AVAILABLE",
            "tube_side_numeric_usable": False,
            "shell_side_numeric_usable": False,
            "upstream_blockers": ["POSTPASS_MISSING"],
            "tube_upstream_blockers": ["POSTPASS_MISSING"],
            "shell_upstream_blockers": ["POSTPASS_MISSING"],
        }
    tube_blockers = _side_upstream_blockers(postpass, "TUBE")
    shell_blockers = _side_upstream_blockers(postpass, "SHELL")
    all_blockers = sorted(set(tube_blockers + shell_blockers))

    return {
        "UPSTREAM_POSTPASS_STATUS": "USABLE" if not all_blockers else "BLOCKED",
        "tube_side_numeric_usable": len(tube_blockers) == 0,
        "shell_side_numeric_usable": len(shell_blockers) == 0,
        "upstream_blockers": all_blockers,
        "tube_upstream_blockers": tube_blockers,
        "shell_upstream_blockers": shell_blockers,
        "partial_model_tube_dp_constraint": postpass.get("tube_dp_constraint"),
        "partial_model_shell_dp_constraint": postpass.get("shell_dp_constraint"),
        "disclosure": (
            "NOT_SATISFIED on partial dp_constraint does not block full-path Δp composition; "
            "BLOCKED recompute, correlation, CoolProp outlet domain, or missing upstream data does."
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
    del partial_breakdown  # full-path friction must not be inferred from partial breakdown totals
    blockers: list[str] = []
    exp = postpass.get("experimental_transitional_tube_hydraulic") or {}
    recompute = postpass.get("tube_hydraulic_recompute_status")

    friction_raw = exp.get("tube_friction_dp_pa")
    local_raw = exp.get("tube_local_loss_dp_pa")
    total_raw = exp.get("total_tube_dp_pa") or postpass.get("recalculated_tube_dp_pa")

    if friction_raw is not None and recompute == "EXPERIMENTAL_TRANSITIONAL_SUCCESS":
        tube_friction = Decimal(str(friction_raw))
        if local_raw is not None and total_raw is not None:
            total_d = Decimal(str(total_raw))
            local_d = Decimal(str(local_raw))
            if abs(total_d - (tube_friction + local_d)) > Decimal("0.01"):
                blockers.append("R20_TRANSITIONAL_DECOMPOSITION_MISMATCH")
                return None, "TUBE_FRICTION_SEPARATION_UNRELIABLE", blockers
        return tube_friction, "R20_TRANSITIONAL_FRICTION", blockers

    if recompute == "SUCCESS" and friction_raw is None:
        blockers.append(
            "TUBE_FRICTION_SEPARATION_UNRELIABLE: Task029 total must not be used as bundle friction"
        )
        return None, "TUBE_FRICTION_SEPARATION_UNRELIABLE", blockers

    embedded = postpass_embedded_local_loss_pa(postpass)
    if (
        friction_raw is None
        and local_raw is not None
        and total_raw is not None
        and embedded > 0
        and abs(Decimal(str(local_raw)) - embedded) <= Decimal("0.01")
    ):
        tube_friction = Decimal(str(total_raw)) - embedded
        return tube_friction, "VERIFIED_TASK028_LOCAL_DECOMPOSITION", blockers

    blockers.append(
        "TUBE_FRICTION_SEPARATION_UNRELIABLE: no independent Task027/R20 friction or verified decomposition"
    )
    return None, "TUBE_FRICTION_SEPARATION_UNRELIABLE", blockers


_COOLPROP_MIN_PRESSURE_PA = Decimal("100000")
_COOLPROP_MAX_PRESSURE_PA = Decimal("10000000")


def _outlet_domain_ok(
    provider: CoolPropProvider,
    *,
    temperature_k: Decimal,
    pressure_pa: Decimal,
) -> tuple[bool, str | None]:
    try:
        state = provider.state_tp(
            FluidIdentifier("Water", "HEOS"),
            float(temperature_k),
            float(pressure_pa),
        )
    except Exception as exc:
        return False, f"COOLPROP_TP_ERROR:{type(exc).__name__}"
    phase_name = getattr(state.phase, "value", str(state.phase)).lower()
    if "liquid" not in phase_name:
        return False, f"COOLPROP_PHASE_{phase_name}"
    if not (_COOLPROP_MIN_PRESSURE_PA <= pressure_pa <= _COOLPROP_MAX_PRESSURE_PA):
        return False, "COOLPROP_PRESSURE_OUT_OF_MODEL_ENVELOPE"
    return True, None


def assess_full_path_hydraulic_constraints(
    *,
    case: EngineeringCase,
    postpass: dict[str, Any],
    tube_full_dp: Decimal | None,
    shell_full_dp: Decimal | None,
    provider: CoolPropProvider | None = None,
) -> dict[str, Any]:
    provider = provider or CoolPropProvider()
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

    tube_outlet_domain = "NOT_COMPUTED"
    shell_outlet_domain = "NOT_COMPUTED"
    tube_outlet_detail = None
    shell_outlet_detail = None

    if tube_full_dp is not None:
        tube_margin = max_tube - tube_full_dp
        tube_outlet_p = tube_inlet_p - tube_full_dp
        tube_constraint = "SATISFIED" if tube_full_dp <= max_tube else "NOT_SATISFIED"
        tube_t_out = Decimal(
            str(postpass.get("tube_outlet_temperature_k", case.tube_side.inlet_temperature_k))
        )
        ok, detail = _outlet_domain_ok(
            provider, temperature_k=tube_t_out, pressure_pa=tube_outlet_p
        )
        tube_outlet_domain = "SATISFIED" if ok else "OUTLET_PRESSURE_OUT_OF_DOMAIN"
        tube_outlet_detail = detail
    if shell_full_dp is not None:
        shell_margin = max_shell - shell_full_dp
        shell_outlet_p = shell_inlet_p - shell_full_dp
        shell_constraint = "SATISFIED" if shell_full_dp <= max_shell else "NOT_SATISFIED"
        shell_t_out = Decimal(
            str(postpass.get("shell_outlet_temperature_k", case.shell_side.inlet_temperature_k))
        )
        ok, detail = _outlet_domain_ok(
            provider, temperature_k=shell_t_out, pressure_pa=shell_outlet_p
        )
        shell_outlet_domain = "SATISFIED" if ok else "OUTLET_PRESSURE_OUT_OF_DOMAIN"
        shell_outlet_detail = detail

    if tube_constraint == "NOT_COMPUTED" or shell_constraint == "NOT_COMPUTED":
        combined = "NOT_COMPUTED"
    elif tube_outlet_domain == "OUTLET_PRESSURE_OUT_OF_DOMAIN" or (
        shell_outlet_domain == "OUTLET_PRESSURE_OUT_OF_DOMAIN"
    ):
        combined = "OUTLET_PRESSURE_DOMAIN_BLOCKED"
    elif tube_constraint == "SATISFIED" and shell_constraint == "SATISFIED":
        combined = "SATISFIED"
    else:
        combined = "NOT_SATISFIED"

    return {
        "TUBE_FULL_PATH_DP_MARGIN_PA": str(tube_margin) if tube_margin is not None else None,
        "SHELL_FULL_PATH_DP_MARGIN_PA": str(shell_margin) if shell_margin is not None else None,
        "FULL_PATH_TUBE_CONSTRAINT_STATUS": tube_constraint,
        "FULL_PATH_SHELL_CONSTRAINT_STATUS": shell_constraint,
        "FULL_PATH_TUBE_OUTLET_DOMAIN_STATUS": tube_outlet_domain,
        "FULL_PATH_SHELL_OUTLET_DOMAIN_STATUS": shell_outlet_domain,
        "FULL_PATH_TUBE_OUTLET_DOMAIN_DETAIL": tube_outlet_detail,
        "FULL_PATH_SHELL_OUTLET_DOMAIN_DETAIL": shell_outlet_detail,
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
