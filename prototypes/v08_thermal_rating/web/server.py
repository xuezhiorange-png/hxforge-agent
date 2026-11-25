"""V08 experimental user-trial web server (local only)."""

# ruff: noqa: E501

from __future__ import annotations

import json
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_250, FIXTURE_330
from prototypes.v08_thermal_rating.v08_05_qualified_top_n_engineering_report import (
    merged_web_api_payload,
    render_v08_05_markdown,
    run_v08_05_qualified_selection,
)
from prototypes.v08_thermal_rating.v08_autonomous_design_tool import (
    render_design_report_markdown,
)
from prototypes.v08_thermal_rating.v08_kernel_engineering_report_v1 import (
    kernel_web_payload,
    run_kernel_case_engineering_matrix,
)
from prototypes.v08_thermal_rating.web.case_builder import form_to_case_json, preset_fields
from prototypes.v08_thermal_rating.web.svg_diagrams import diagrams_for_report

STATIC = Path(__file__).resolve().parent / "static"
app = FastAPI(title="HXForge V08 Experimental Design", version="0.1.0")
_PROVIDER = CoolPropProvider()


class DesignForm(BaseModel):
    engineering_case_id: str = "WEB_USER_CASE"
    tube_fluid: str = "PURE_ORDINARY_WATER"
    shell_fluid: str = "PURE_ORDINARY_WATER"
    tube_inlet_temperature_k: str
    shell_inlet_temperature_k: str
    tube_inlet_pressure_pa: str = "101325"
    shell_inlet_pressure_pa: str = "101325"
    tube_mass_flow_kg_s: str
    shell_mass_flow_kg_s: str
    target_duty_kw: str
    max_tube_side_pressure_drop_pa: str
    max_shell_side_pressure_drop_pa: str
    max_shell_inside_diameter_m: str | None = None
    max_tube_length_m: str | None = None
    notes: str = ""
    max_candidates: int = Field(default=32, ge=4, le=64)
    run_mdot_verification: bool = True
    rating_engine: str = Field(
        default="prescreen",
        description="prescreen (legacy ε-NTU chain) or kernel_v1 (independent rating kernel)",
    )


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _fixture_for_kernel_case(case_json: str) -> Path | None:
    try:
        case = load_general_user_design_case_json(case_json)
        pipeline = validate_and_build_solver_handoff(case, provider=_PROVIDER)
        duty = float(pipeline.normalized.target_duty_w)
        if duty >= 320_000:
            return FIXTURE_330.parent / "v08_user_case_hxforge_330kw_strict_dp.json"
        if duty <= 225_000:
            alt = FIXTURE_330.parent / "v08_user_case_no_geometry_task174_admissible_alt.json"
            if abs(duty - 220_000) < abs(duty - 250_000):
                return alt
        return FIXTURE_250
    except Exception:
        return None


def _compute_with_progress(
    case_json: str,
    *,
    max_candidates: int,
    run_mdot: bool,
    rating_engine: str = "prescreen",
) -> Generator[str, None, None]:
    t0 = time.time()
    yield _sse("progress", {"stage": "VALIDATE_INPUT", "message": "校验输入与单位…"})
    case_text = case_json
    if rating_engine == "kernel_v1":
        fx = _fixture_for_kernel_case(case_text) or FIXTURE_250
        yield _sse(
            "progress",
            {
                "stage": "KERNEL_RATING_JOINT",
                "message": "独立 Rating 内核 + 四接管/全路径水力…",
            },
        )
        kernel_rep = run_kernel_case_engineering_matrix(
            fx, provider=_PROVIDER, max_candidates=max_candidates
        )
        payload = kernel_web_payload(kernel_rep)
        payload["elapsed_s"] = round(time.time() - t0, 2)
        payload["fixture_used"] = str(fx)
        yield _sse("result", {"report": payload})
        return
    yield _sse(
        "progress", {"stage": "RUN_DESIGN_TOOL", "message": "调用自动设计内核（结构→热工→水力）…"}
    )
    report = run_v08_05_qualified_selection(
        case_text,
        provider=_PROVIDER,
        max_candidates=max_candidates,
        run_mdot_on_recommendation=run_mdot,
    )
    elapsed = round(time.time() - t0, 2)
    mirror = report.design_tool_mirror
    gen_n = mirror.structural_candidates_generated if mirror else len(report.candidates)
    eval_n = mirror.structural_candidates_evaluated if mirror else len(report.candidates)
    yield _sse(
        "progress",
        {
            "stage": "STRUCTURAL_ENUMERATION",
            "message": f"结构候选 {gen_n} 个，已评估 {eval_n} 个",
            "generated": gen_n,
            "evaluated": eval_n,
        },
    )
    payload = merged_web_api_payload(report)
    payload["markdown_report"] = render_v08_05_markdown(report)
    if mirror:
        payload["legacy_markdown"] = render_design_report_markdown(mirror)
    payload["diagrams"] = diagrams_for_report(payload)
    payload["elapsed_s"] = elapsed
    yield _sse("result", {"report": payload})


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/presets/{key}")
def get_preset(key: str) -> dict[str, Any]:
    if key not in ("330kw", "250kw", "constraint_change", "infeasible"):
        raise HTTPException(404, "unknown preset")
    return preset_fields(key)


@app.post("/api/design/run-stream")
def run_design_stream(form: DesignForm) -> StreamingResponse:
    case_json = form_to_case_json(form.model_dump())
    gen = _compute_with_progress(
        case_json,
        max_candidates=form.max_candidates,
        run_mdot=form.run_mdot_verification,
        rating_engine=form.rating_engine,
    )
    return StreamingResponse(gen, media_type="text/event-stream")


@app.post("/api/design/run")
def run_design_sync(form: DesignForm) -> dict[str, Any]:
    case_json = form_to_case_json(form.model_dump())
    report = run_v08_05_qualified_selection(
        case_json,
        provider=_PROVIDER,
        max_candidates=form.max_candidates,
        run_mdot_on_recommendation=form.run_mdot_verification,
    )
    payload = merged_web_api_payload(report)
    payload["markdown_report"] = render_v08_05_markdown(report)
    payload["case_json_submitted"] = json.loads(case_json)
    payload["diagrams"] = diagrams_for_report(payload)
    return payload


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


def main() -> None:
    import uvicorn

    uvicorn.run(
        "prototypes.v08_thermal_rating.web.server:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
    )


if __name__ == "__main__":
    main()
