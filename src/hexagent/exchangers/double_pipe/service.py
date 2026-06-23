"""Double-pipe heat-exchanger domain service.

Bridges the DesignCase domain model to the pure rating kernel.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hexagent.core.heat_balance import CalculationContext
from hexagent.domain.models import DesignCase
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import rate_double_pipe
from hexagent.exchangers.double_pipe.result import RatingResult
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.properties.base import FluidIdentifier, PropertyProvider

if TYPE_CHECKING:
    from hexagent.domain.models import CalculationResult


class DoublePipeRatingService:
    """Domain service for fixed-geometry double-pipe rating.

    Wraps the pure ``rate_double_pipe`` kernel with DesignCase-level
    input extraction and error handling.
    """

    def __init__(
        self,
        provider: PropertyProvider,
    ) -> None:
        self._provider = provider

    def rate(
        self,
        case: DesignCase,
        geometry: DoublePipeGeometry,
        *,
        tube_in_hot: bool = True,
        flow_arrangement: FlowArrangement = FlowArrangement.COUNTERFLOW,
        solver_params: SolverParams | None = None,
        context: CalculationContext | None = None,
    ) -> RatingResult:
        """Execute a fixed-geometry double-pipe rating.

        Parameters
        ----------
        case :
            DesignCase with hot and cold stream specifications.
        geometry :
            Fixed geometry of the double-pipe exchanger.
        tube_in_hot :
            If True, the hot fluid flows in the inner tube.
        flow_arrangement :
            Counter-flow or parallel-flow.
        solver_params :
            Solver control parameters (uses defaults if None).
        context :
            Optional calculation context for provenance.
        """
        # Extract fluid identifiers
        hot_fluid = FluidIdentifier(
            name=case.hot_stream.fluid.name,
            equation_of_state_backend=case.hot_stream.fluid.backend,
        )
        cold_fluid = FluidIdentifier(
            name=case.cold_stream.fluid.name,
            equation_of_state_backend=case.cold_stream.fluid.backend,
        )

        # Extract stream inputs
        hot_inlet_t = case.hot_stream.inlet_temperature_k
        hot_inlet_p = case.hot_stream.inlet_pressure_pa
        cold_inlet_t = case.cold_stream.inlet_temperature_k
        cold_inlet_p = case.cold_stream.inlet_pressure_pa

        if hot_inlet_t is None or hot_inlet_p is None:
            raise ValueError("Hot stream must have inlet temperature and pressure")
        if cold_inlet_t is None or cold_inlet_p is None:
            raise ValueError("Cold stream must have inlet temperature and pressure")

        hot_mass_flow = case.hot_stream.mass_flow.si_value
        cold_mass_flow = case.cold_stream.mass_flow.si_value

        # Build fouling from stream specs
        hot_fouling = case.hot_stream.fouling_resistance.value.si_value
        cold_fouling = case.cold_stream.fouling_resistance.value.si_value

        # Override geometry fouling with stream-level values
        geom = DoublePipeGeometry(
            inner_tube_inner_diameter_m=geometry.inner_tube_inner_diameter_m,
            inner_tube_outer_diameter_m=geometry.inner_tube_outer_diameter_m,
            outer_pipe_inner_diameter_m=geometry.outer_pipe_inner_diameter_m,
            effective_length_m=geometry.effective_length_m,
            wall_thermal_conductivity_w_m_k=geometry.wall_thermal_conductivity_w_m_k,
            inner_surface_roughness_m=geometry.inner_surface_roughness_m,
            annulus_surface_roughness_m=geometry.annulus_surface_roughness_m,
            inner_fouling_resistance_m2k_w=hot_fouling if tube_in_hot else cold_fouling,
            outer_fouling_resistance_m2k_w=cold_fouling if tube_in_hot else hot_fouling,
        )

        return rate_double_pipe(
            geometry=geom,
            hot_fluid=hot_fluid,
            cold_fluid=cold_fluid,
            hot_mass_flow_kg_s=hot_mass_flow,
            cold_mass_flow_kg_s=cold_mass_flow,
            hot_inlet_temperature_k=hot_inlet_t,
            cold_inlet_temperature_k=cold_inlet_t,
            hot_inlet_pressure_pa=hot_inlet_p,
            cold_inlet_pressure_pa=cold_inlet_p,
            tube_in_hot=tube_in_hot,
            flow_arrangement=flow_arrangement,
            provider=self._provider,
            solver_params=solver_params,
            context=context,
        )


class DoublePipeService:
    """Minimal demonstrator. Replace with validated correlations before production use."""

    exchanger_type = "double_pipe"

    def size(self, case: DesignCase) -> CalculationResult:
        from hexagent.core.units import to_si
        from hexagent.correlations.thermal import counterflow_lmtd
        from hexagent.domain.models import CalculationResult, ProvenanceRecord, WarningMessage

        hot_out = case.hot_stream.outlet_temperature
        cold_out = case.cold_stream.outlet_temperature
        if hot_out is None or cold_out is None:
            return CalculationResult(
                status="NOT_IMPLEMENTED",
                outputs={},
                warnings=[
                    WarningMessage(
                        code="DP-001",
                        severity="error",
                        message="Starter implementation requires both outlet temperatures.",
                    )
                ],
            )

        for label, stream in [("hot", case.hot_stream), ("cold", case.cold_stream)]:
            st = stream.state_spec_type
            if st is not None and st != "TP":
                return CalculationResult(
                    status="NOT_IMPLEMENTED",
                    outputs={},
                    warnings=[
                        WarningMessage(
                            code="DP-004",
                            severity="error",
                            message=(
                                f"Double-pipe solver only supports TP state"
                                f" spec, got {st} for {label} stream."
                            ),
                        )
                    ],
                )

        th_in_k = case.hot_stream.inlet_temperature_k
        tc_in_k = case.cold_stream.inlet_temperature_k
        if th_in_k is None or tc_in_k is None:
            return CalculationResult(
                status="NOT_IMPLEMENTED",
                outputs={},
                warnings=[
                    WarningMessage(
                        code="DP-003",
                        severity="error",
                        message=(
                            "Inlet temperatures could not be resolved from"
                            " state specs or legacy fields."
                        ),
                    )
                ],
            )
        th_out = to_si(hot_out, "kelvin")
        tc_out = to_si(cold_out, "kelvin")
        lmtd = counterflow_lmtd(th_in_k, th_out, tc_in_k, tc_out)

        if case.target_duty is None:
            return CalculationResult(
                status="NOT_IMPLEMENTED",
                outputs={"lmtd_k": lmtd},
                warnings=[
                    WarningMessage(
                        code="DP-002",
                        severity="error",
                        message="Starter implementation requires target_duty.",
                    )
                ],
            )

        duty_w = to_si(case.target_duty, "watt")
        assumed_u = 500.0
        required_area = duty_w / (assumed_u * lmtd)
        margin = case.constraints.required_area_margin_fraction
        design_area = required_area * (1.0 + margin)

        return CalculationResult(
            status="PRELIMINARY",
            outputs={
                "exchanger_type": self.exchanger_type,
                "duty_w": duty_w,
                "lmtd_k": lmtd,
                "assumed_u_w_m2_k": assumed_u,
                "required_area_m2": required_area,
                "design_area_m2": design_area,
            },
            warnings=[
                WarningMessage(
                    code="DP-DEMO-U",
                    severity="warning",
                    message=(
                        "Overall heat-transfer coefficient is a placeholder."
                        " Do not use this result for procurement"
                        " or construction."
                    ),
                )
            ],
            provenance=[
                ProvenanceRecord(
                    formula_id="thermal.counterflow_lmtd.v1",
                    formula_version="1.0.0",
                    source_reference="standard heat-transfer relation",
                    inputs={
                        "hot_in_k": th_in_k,
                        "hot_out_k": th_out,
                        "cold_in_k": tc_in_k,
                        "cold_out_k": tc_out,
                    },
                    outputs={"lmtd_k": lmtd},
                    applicability_status="within_basic_definition",
                )
            ],
        )

    def rate(self, case: DesignCase, geometry: dict[str, float]) -> CalculationResult:
        area = geometry.get("area_m2")
        u_value = geometry.get("u_w_m2_k")
        if area is None or u_value is None or area <= 0.0 or u_value <= 0.0:
            raise ValueError("geometry requires positive area_m2 and u_w_m2_k")
        from hexagent.domain.models import CalculationResult, WarningMessage

        return CalculationResult(
            status="NOT_IMPLEMENTED",
            outputs={"area_m2": area, "u_w_m2_k": u_value},
            warnings=[
                WarningMessage(
                    code="DP-RATE-001",
                    severity="error",
                    message="Detailed rating solver has not been implemented.",
                )
            ],
        )
