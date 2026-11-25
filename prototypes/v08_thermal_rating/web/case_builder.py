"""Build hxforge.general-user-design-case.v1 JSON from web form fields."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def form_to_case_json(fields: dict[str, Any]) -> str:
    import json

    case_id = str(fields.get("engineering_case_id") or "WEB_USER_CASE").strip()[:128]
    target_kw = Decimal(str(fields["target_duty_kw"]))
    tube_t_k = Decimal(str(fields["tube_inlet_temperature_k"]))
    shell_t_k = Decimal(str(fields["shell_inlet_temperature_k"]))
    tube_p = Decimal(str(fields["tube_inlet_pressure_pa"]))
    shell_p = Decimal(str(fields["shell_inlet_pressure_pa"]))
    tube_mdot = Decimal(str(fields["tube_mass_flow_kg_s"]))
    shell_mdot = Decimal(str(fields["shell_mass_flow_kg_s"]))
    tube_dp = Decimal(str(fields["max_tube_side_pressure_drop_pa"]))
    shell_dp = Decimal(str(fields["max_shell_side_pressure_drop_pa"]))
    envelope: dict[str, Any] = {
        "provenance_note": "V08 experimental user trial web MVP",
    }
    if fields.get("max_shell_inside_diameter_m"):
        envelope["max_shell_inside_diameter_m"] = str(fields["max_shell_inside_diameter_m"])
    if fields.get("max_tube_length_m"):
        envelope["max_tube_length_m"] = str(fields["max_tube_length_m"])
    payload = {
        "schema_version": "hxforge.general-user-design-case.v1",
        "engineering_case_id": case_id,
        "exchanger_type": "SHELL_AND_TUBE_FIXED_TUBESHEET_SINGLE_PHASE",
        "tube_side": {
            "fluid": fields.get("tube_fluid") or "PURE_ORDINARY_WATER",
            "inlet_temperature_k": str(tube_t_k),
            "inlet_pressure_pa": str(tube_p),
            "mass_flow_kg_s": str(tube_mdot),
        },
        "shell_side": {
            "fluid": fields.get("shell_fluid") or "PURE_ORDINARY_WATER",
            "inlet_temperature_k": str(shell_t_k),
            "inlet_pressure_pa": str(shell_p),
            "mass_flow_kg_s": str(shell_mdot),
        },
        "target_duty_w": str((target_kw * Decimal(1000)).quantize(Decimal("0.1"))),
        "max_tube_side_pressure_drop_pa": str(tube_dp),
        "max_shell_side_pressure_drop_pa": str(shell_dp),
        "design_envelope": envelope,
        "notes": str(fields.get("notes") or "V08_EXPERIMENTAL_USER_TRIAL_WEB_MVP"),
    }
    return json.dumps(payload, indent=2)


def celsius_to_k(c: float) -> str:
    return str(Decimal(str(c)) + Decimal("273.15"))


def kpa_to_pa(kpa: float) -> str:
    return str(Decimal(str(kpa)) * Decimal(1000))


def preset_fields(preset_key: str) -> dict[str, Any]:
    """Map built-in fixture presets to web form fields."""
    from pathlib import Path

    from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_250, FIXTURE_330

    repo = Path(__file__).resolve().parents[3]
    paths = {
        "330kw": FIXTURE_330,
        "250kw": FIXTURE_250,
        "constraint_change": repo / "tests/fixtures/v08_user_case_330kw_tight_envelope.json",
        "infeasible": repo / "tests/fixtures/v08_user_case_infeasible_duty_5mw.json",
    }
    path = paths[preset_key]
    import json

    doc = json.loads(path.read_text(encoding="utf-8"))
    return {
        "engineering_case_id": doc["engineering_case_id"],
        "tube_fluid": doc["tube_side"]["fluid"],
        "shell_fluid": doc["shell_side"]["fluid"],
        "tube_inlet_temperature_k": doc["tube_side"]["inlet_temperature_k"],
        "shell_inlet_temperature_k": doc["shell_side"]["inlet_temperature_k"],
        "tube_inlet_pressure_pa": doc["tube_side"]["inlet_pressure_pa"],
        "shell_inlet_pressure_pa": doc["shell_side"]["inlet_pressure_pa"],
        "tube_mass_flow_kg_s": doc["tube_side"]["mass_flow_kg_s"],
        "shell_mass_flow_kg_s": doc["shell_side"]["mass_flow_kg_s"],
        "target_duty_kw": str(Decimal(doc["target_duty_w"]) / Decimal(1000)),
        "max_tube_side_pressure_drop_pa": doc["max_tube_side_pressure_drop_pa"],
        "max_shell_side_pressure_drop_pa": doc["max_shell_side_pressure_drop_pa"],
        "max_shell_inside_diameter_m": (doc.get("design_envelope") or {}).get(
            "max_shell_inside_diameter_m"
        ),
        "max_tube_length_m": (doc.get("design_envelope") or {}).get("max_tube_length_m"),
        "preset_key": preset_key,
    }