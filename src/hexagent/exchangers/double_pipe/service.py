from __future__ import annotations

from hexagent.correlations.thermal import counterflow_lmtd
from hexagent.core.units import to_si
from hexagent.domain.models import (
    CalculationResult,
    DesignCase,
    ProvenanceRecord,
    WarningMessage,
)


class DoublePipeService:
    """Minimal demonstrator. Replace with validated correlations before production use."""

    exchanger_type = "double_pipe"

    def size(self, case: DesignCase) -> CalculationResult:
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

        th_in = to_si(case.hot_stream.inlet_temperature, "kelvin")
        th_out = to_si(hot_out, "kelvin")
        tc_in = to_si(case.cold_stream.inlet_temperature, "kelvin")
        tc_out = to_si(cold_out, "kelvin")
        lmtd = counterflow_lmtd(th_in, th_out, tc_in, tc_out)

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

        # Deliberately explicit placeholder assumption.
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
                        "Overall heat-transfer coefficient is a placeholder. "
                        "Do not use this result for procurement or construction."
                    ),
                )
            ],
            provenance=[
                ProvenanceRecord(
                    formula_id="thermal.counterflow_lmtd.v1",
                    formula_version="1.0.0",
                    source_reference="standard heat-transfer relation",
                    inputs={
                        "hot_in_k": th_in,
                        "hot_out_k": th_out,
                        "cold_in_k": tc_in,
                        "cold_out_k": tc_out,
                    },
                    outputs={"lmtd_k": lmtd},
                    applicability_status="within_basic_definition",
                ),
                ProvenanceRecord(
                    formula_id="double_pipe.demo_area.v1",
                    formula_version="0.1.0",
                    source_reference="architecture demonstrator only",
                    inputs={"duty_w": duty_w, "u_w_m2_k": assumed_u, "lmtd_k": lmtd},
                    outputs={"required_area_m2": required_area},
                    applicability_status="placeholder_not_validated",
                ),
            ],
        )

    def rate(self, case: DesignCase, geometry: dict[str, float]) -> CalculationResult:
        area = geometry.get("area_m2")
        u_value = geometry.get("u_w_m2_k")
        if area is None or u_value is None or area <= 0.0 or u_value <= 0.0:
            raise ValueError("geometry requires positive area_m2 and u_w_m2_k")
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
