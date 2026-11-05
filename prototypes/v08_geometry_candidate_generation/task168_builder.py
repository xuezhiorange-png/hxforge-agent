"""Build Task168 requests for V08-02 from validated user case handoff."""

# ruff: noqa: E501

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    discrete_authority_hash,
    evaluation_input_authority_hash,
    shell_catalog_hash,
    shell_record_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.implementation_validation_task168 import (
    build_implementation_validation_task168_reference,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    ConstructionFamily,
    DiscreteAuthoritySource,
    DiscreteCandidateSetAuthority,
    DiscreteDimensionRole,
    Task168Request,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.variable_shell_r13 import (
    VARIABLE_SHELL_TASK021_PLACEMENT_ENVELOPE_OPT_IN_R13,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.canonical import (
    mass_flow_authority_hash,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.schema import (
    parse_request as parse_task032,
)
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import (
    NormalizedUserDesignCase,
    OptionalDesignEnvelopeConstraints,
)
from prototypes.v08_geometry_candidate_generation.discrete_space import (
    V08DiscreteSpaceAuthority,
    format_engineering_decimal,
)

_V08_SPACE_ID = "V08-GENERAL-GEOMETRY-DISCRETE-SPACE-R1"


def filter_discrete_space_by_envelope(
    space: V08DiscreteSpaceAuthority,
    envelope: OptionalDesignEnvelopeConstraints | None,
) -> tuple[V08DiscreteSpaceAuthority, tuple[str, ...]]:
    """Return filtered space and envelope filter audit messages."""
    if envelope is None:
        return space, ()
    messages: list[str] = []
    shells = list(space.shell_inside_diameters_m)
    if envelope.min_shell_inside_diameter_m is not None:
        shells = [d for d in shells if d >= envelope.min_shell_inside_diameter_m]
        messages.append("applied min_shell_inside_diameter_m")
    if envelope.max_shell_inside_diameter_m is not None:
        shells = [d for d in shells if d <= envelope.max_shell_inside_diameter_m]
        messages.append("applied max_shell_inside_diameter_m")
    ladder = list(space.tube_baffle_ladder)
    if envelope.min_tube_length_m is not None:
        ladder = [step for step in ladder if step.tube_length_m >= envelope.min_tube_length_m]
        messages.append("applied min_tube_length_m")
    if envelope.max_tube_length_m is not None:
        ladder = [step for step in ladder if step.tube_length_m <= envelope.max_tube_length_m]
        messages.append("applied max_tube_length_m")
    if envelope.max_overall_length_m is not None:
        ladder = [
            step for step in ladder if step.tube_length_m <= envelope.max_overall_length_m
        ]
        messages.append("applied max_overall_length_m")
    if not shells or not ladder:
        filtered = replace(
            space,
            shell_inside_diameters_m=tuple(shells),
            tube_baffle_ladder=tuple(ladder),
        )
        return filtered, tuple(messages)
    filtered = replace(
        space,
        shell_inside_diameters_m=tuple(shells),
        tube_baffle_ladder=tuple(ladder),
    )
    return filtered, tuple(messages)


def build_v08_task168_request(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    space: V08DiscreteSpaceAuthority,
) -> Task168Request:
    if handoff.normalized_input_hash != canonical_sha256(normalized.input_snapshot_dict()):
        raise ValueError("handoff normalized_input_hash does not match user case")
    if not space.shell_inside_diameters_m or not space.tube_baffle_ladder:
        raise ValueError("discrete space empty after envelope filtering")

    first_shell = space.shell_inside_diameters_m[0]
    first_ladder = space.tube_baffle_ladder[0]
    reference = build_implementation_validation_task168_reference(
        shell_diameter=format_engineering_decimal(first_shell),
        tube_outer_diameter=format_engineering_decimal(space.tube_outer_diameter_m),
        tube_wall_thickness=format_engineering_decimal(space.tube_wall_thickness_m),
        tube_length=format_engineering_decimal(first_ladder.tube_length_m),
        tube_pitch=format_engineering_decimal(space.tube_pitch_m),
        baffle_spacing=format_engineering_decimal(first_ladder.baffle_spacing_m),
        baffle_count=first_ladder.baffle_count,
    )
    reference = _apply_multi_shell_catalog(reference, space.shell_inside_diameters_m)
    reference = _apply_v08_discrete_authorities(reference, space)
    reference = _bind_handoff_to_evaluation_templates(reference, handoff)
    metadata = (
        ("v08_task_id", "V08_02_AUTOMATIC_GEOMETRY_GENERATION"),
        ("normalized_input_hash", handoff.normalized_input_hash),
        ("target_duty_w", handoff.consumable_parameters.get("target_duty_w", "")),
        ("tube_mass_flow_kg_s", handoff.consumable_parameters.get("tube_mass_flow_kg_s", "")),
        ("shell_mass_flow_kg_s", handoff.consumable_parameters.get("shell_mass_flow_kg_s", "")),
        ("max_tube_side_dp_pa", handoff.pressure_limits_pa.get("max_tube_side_pressure_drop_pa", "")),
        ("max_shell_side_dp_pa", handoff.pressure_limits_pa.get("max_shell_side_pressure_drop_pa", "")),
        ("geometry_source_authority", space.authority_id),
        ("geometry_source_content_hash", space.content_hash),
    )
    return replace(reference, request_metadata=metadata)


def _apply_multi_shell_catalog(
    request: Task168Request, diameters: tuple[Decimal, ...]
) -> Task168Request:
    shell_records: list[Any] = []
    multi_shell = len(diameters) > 1
    for diameter in diameters:
        template = request.shell_geometry_catalog.records[0]
        geometry_id = template.geometry_id
        if multi_shell:
            geometry_id = f"{template.geometry_id}::SHELL_D_{diameter}"
        shell_record = replace(
            template,
            geometry_id=geometry_id,
            shell_inside_diameter_m=format_engineering_decimal(diameter),
            nominal_label=f"shell_ID_{diameter}m",
            record_hash="",
        )
        shell_record = replace(shell_record, record_hash=shell_record_hash(shell_record))
        shell_records.append(shell_record)
    catalog = replace(
        request.shell_geometry_catalog,
        records=tuple(shell_records),
        catalog_hash="",
    )
    catalog = replace(catalog, catalog_hash=shell_catalog_hash(catalog))
    evaluation = request.evaluation_input_authority
    task021_template = cast(dict[str, Any], deepcopy(evaluation.task021_request_template))
    primary_shell = diameters[0]
    envelope_m = (primary_shell * Decimal("0.9")).quantize(Decimal("0.0000000001"))
    task021_template["placement_envelope"]["tube_center_envelope_diameter_m"] = str(envelope_m)
    task021_template["placement_envelope"]["evidence_refs"] = [
        "V08-02-GENERAL-GEOMETRY-PLACEMENT-ENVELOPE"
    ]
    evaluation = replace(evaluation, task021_request_template=task021_template, canonical_hash="")
    evidence = tuple(evaluation.evidence_refs)
    if multi_shell and VARIABLE_SHELL_TASK021_PLACEMENT_ENVELOPE_OPT_IN_R13 not in evidence:
        evidence = (*evidence, VARIABLE_SHELL_TASK021_PLACEMENT_ENVELOPE_OPT_IN_R13)
    evaluation = replace(evaluation, evidence_refs=evidence, canonical_hash="")
    evaluation = replace(evaluation, canonical_hash=evaluation_input_authority_hash(evaluation))
    return replace(
        request,
        shell_geometry_catalog=catalog,
        evaluation_input_authority=evaluation,
    )


def _apply_v08_discrete_authorities(
    request: Task168Request, space: V08DiscreteSpaceAuthority
) -> Task168Request:
    role_values: dict[DiscreteDimensionRole, tuple[object, ...]] = {
        DiscreteDimensionRole.CONSTRUCTION_FAMILY: (ConstructionFamily.FIXED_TUBESHEET,),
        DiscreteDimensionRole.TUBE_OUTER_DIAMETER: (space.tube_outer_diameter_m,),
        DiscreteDimensionRole.TUBE_WALL_THICKNESS: (space.tube_wall_thickness_m,),
        DiscreteDimensionRole.TUBE_LENGTH: space.tube_lengths_m,
        DiscreteDimensionRole.TUBE_PITCH: (space.tube_pitch_m,),
        DiscreteDimensionRole.TUBE_LAYOUT: (space.tube_layout,),
        DiscreteDimensionRole.TUBE_PASS_COUNT: space.tube_pass_counts,
        DiscreteDimensionRole.BAFFLE_TYPE: (space.baffle_type,),
        DiscreteDimensionRole.BAFFLE_CUT: (space.baffle_cut,),
        DiscreteDimensionRole.BAFFLE_SPACING: space.baffle_spacings_m,
        DiscreteDimensionRole.BAFFLE_COUNT: (
            space.tube_baffle_ladder[0].baffle_count,
        ),
    }
    authorities: list[DiscreteCandidateSetAuthority] = []
    for authority in request.discrete_candidate_set_authorities:
        values = role_values.get(authority.dimension_role)
        if values is None:
            authorities.append(authority)
            continue
        changed = replace(
            authority,
            authority_id=f"{_V08_SPACE_ID}:{authority.dimension_role.value}",
            authority_version=space.authority_version,
            source_class=DiscreteAuthoritySource.AUTHORIZED_PROJECT_DEFINED_DISCRETE_SET,
            source_id=space.authority_id,
            source_revision=space.authority_version,
            approval_status=space.approval_status,
            values=values,
            evidence_refs=space.evidence_refs,
            provenance_refs=("V08-02-GENERAL-GEOMETRY-GENERATION",),
            canonical_hash="",
        )
        authorities.append(replace(changed, canonical_hash=discrete_authority_hash(changed)))
    return replace(request, discrete_candidate_set_authorities=tuple(authorities))


def _bind_handoff_to_evaluation_templates(
    request: Task168Request, handoff: V08SolverHandoffV1
) -> Task168Request:
    evaluation = request.evaluation_input_authority
    params = handoff.consumable_parameters
    shell_mass = params.get("shell_mass_flow_kg_s", "20")
    tube_mass = params.get("tube_mass_flow_kg_s", "14.5")
    shell_t_k = params.get("shell_inlet_temperature_k", "295.15")
    tube_t_k = params.get("tube_inlet_temperature_k", "318.15")

    task032_template = cast(dict[str, Any], deepcopy(evaluation.task032_request_template))
    mass = dict(task032_template["mass_flow_authority"])
    mass["mass_flow_rate_kg_s"] = shell_mass
    check032 = dict(task032_template)
    check032["mass_flow_authority"] = mass
    mass["authority_hash"] = mass_flow_authority_hash(
        parse_task032(check032).mass_flow_authority
    )

    task160_template = cast(dict[str, Any], deepcopy(evaluation.task160_request_template))
    streams = list(cast(list[dict[str, Any]], task160_template["stream_records"]))
    if len(streams) >= 2:
        tube_stream = dict(streams[0])
        shell_stream = dict(streams[1])
        tube_stream["inlet_temperature_k"] = tube_t_k
        shell_stream["inlet_temperature_k"] = shell_t_k
        streams[0] = tube_stream
        streams[1] = shell_stream
        task160_template["stream_records"] = streams

    task031_template = cast(dict[str, Any], deepcopy(evaluation.task031_request_template))
    if "mass_flow_rate_kg_s" in task031_template:
        task031_template["mass_flow_rate_kg_s"] = tube_mass

    evaluation = replace(
        evaluation,
        task032_request_template=task032_template,
        task032_mass_flow_authority=mass,
        task160_request_template=task160_template,
        task031_request_template=task031_template,
        canonical_hash="",
    )
    evaluation = replace(evaluation, canonical_hash=evaluation_input_authority_hash(evaluation))
    return replace(request, evaluation_input_authority=evaluation)
