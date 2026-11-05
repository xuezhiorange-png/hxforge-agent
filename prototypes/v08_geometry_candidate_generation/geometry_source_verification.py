"""Verify V08-02 discrete geometry sources against on-disk engineering authorities."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]

_TASK172_CATALOG = (
    _REPO_ROOT / "docs/tasks/evidence/TASK-172-r117-approved-tube-geometry-catalog-r1.json"
)


def _resolve_repo_path(relative: str) -> Path:
    return _REPO_ROOT / relative


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"geometry evidence file missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"geometry evidence must be object: {path}")
    return payload


def _match_decimal(left: Decimal, right: Decimal) -> bool:
    return left.quantize(Decimal("0.0000001")) == right.quantize(Decimal("0.0000001"))


def verify_discrete_space_payload(payload: dict[str, Any]) -> None:
    """Fail closed unless dimensions trace to approved evidence and structural rules hold."""
    approval = str(payload.get("approval_status", ""))
    if not approval.startswith("APPROVED"):
        raise ValueError(f"discrete space approval_status not authorized: {approval!r}")
    if payload.get("source_class") != "AUTHORIZED_PROJECT_DEFINED_DISCRETE_SET":
        raise ValueError(
            "discrete space source_class is not AUTHORIZED_PROJECT_DEFINED_DISCRETE_SET"
        )

    for ref in payload.get("evidence_refs", ()):
        ref_text = str(ref)
        if ref_text.startswith("docs/"):
            path_part = ref_text.split("#", 1)[0]
            if path_part.endswith((".json", ".md")) and not _resolve_repo_path(path_part).is_file():
                raise ValueError(f"evidence ref path missing on disk: {ref_text}")
        if ref_text.startswith("http"):
            continue

    tube_binding = payload.get("tube_geometry_catalog_binding")
    if not isinstance(tube_binding, dict):
        raise ValueError("tube_geometry_catalog_binding required")
    catalog_path = _resolve_repo_path(str(tube_binding["catalog_path"]))
    catalog = _load_json(catalog_path)
    record_id = str(tube_binding["record_geometry_id"])
    record = next(
        (row for row in catalog.get("records", ()) if row.get("geometry_id") == record_id),
        None,
    )
    if record is None:
        raise ValueError(f"TASK-172 catalog record not found: {record_id}")
    if str(record.get("approval_state")) != "approved":
        raise ValueError("TASK-172 tube record is not approved")

    tube = payload["tube_geometry"]
    od = Decimal(str(tube["tube_outer_diameter_m"]))
    wall = Decimal(str(tube["tube_wall_thickness_m"]))
    pitch = Decimal(str(tube["tube_pitch_m"]))
    if not _match_decimal(od, Decimal(str(record["outer_diameter_m"]))):
        raise ValueError("tube_outer_diameter_m does not match TASK-172 catalog record")
    if not _match_decimal(wall, Decimal(str(record["wall_thickness_m"]))):
        raise ValueError("tube_wall_thickness_m does not match TASK-172 catalog record")

    expected_pitch = (od * Decimal(4) / Decimal(3)).quantize(Decimal("0.0000001"))
    if not _match_decimal(pitch, expected_pitch):
        raise ValueError("tube_pitch_m fails V08 triangular 4/3*OD binding rule")

    shell_path = _resolve_repo_path(str(payload["shell_and_ladder_authority_path"]))
    shell_auth = _load_json(shell_path)
    shell_approval = str(shell_auth.get("approval_status", ""))
    if not shell_approval.startswith("APPROVED"):
        raise ValueError("shell/ladder authority is not approved for V08-02")
    auth_shells = [Decimal(str(row["value_m"])) for row in shell_auth["shell_inside_diameters_m"]]
    payload_shells = [Decimal(str(value)) for value in payload["shell_inside_diameters_m"]]
    if auth_shells != payload_shells:
        raise ValueError("shell_inside_diameters_m inconsistent with shell/ladder authority")

    rule = shell_auth["tube_baffle_ladder_rule"]
    ratio = Decimal(str(rule["length_to_spacing_ratio"]))
    fixed_count = int(rule["baffle_count_fixed"])
    allowed_steps = {
        (
            str(step["tube_length_m"]),
            str(step["baffle_spacing_m"]),
            int(step["baffle_count"]),
        )
        for step in rule["allowed_steps"]
    }
    for row in payload["tube_baffle_ladder"]:
        length = Decimal(str(row["tube_length_m"]))
        spacing = Decimal(str(row["baffle_spacing_m"]))
        count = int(row["baffle_count"])
        key = (str(row["tube_length_m"]), str(row["baffle_spacing_m"]), count)
        if key not in allowed_steps:
            raise ValueError(f"tube_baffle_ladder step not authorized: {key}")
        if count != fixed_count:
            raise ValueError("baffle_count inconsistent with ladder rule")
        if not _match_decimal(length, spacing * ratio):
            raise ValueError("tube_length_m must equal spacing * length_to_spacing_ratio")

    seg = shell_auth["baffle_segmental"]
    if str(payload["baffle_type"]) != str(seg["baffle_type"]):
        raise ValueError("baffle_type inconsistent with shell/ladder authority")
    if not _match_decimal(Decimal(str(payload["baffle_cut"])), Decimal(str(seg["baffle_cut"]))):
        raise ValueError("baffle_cut inconsistent with shell/ladder authority")
    if str(payload["construction_family"]) != str(shell_auth["construction_family"]["value"]):
        raise ValueError("construction_family inconsistent with shell/ladder authority")

    if str(tube["tube_layout"]) != str(tube_binding["tube_layout"]):
        raise ValueError("tube_layout inconsistent with tube_geometry_catalog_binding")

    pass_counts = tuple(int(value) for value in tube["tube_pass_counts"])
    bound_pass = tuple(int(value) for value in tube_binding["tube_pass_counts"])
    if pass_counts != bound_pass:
        raise ValueError("tube_pass_counts inconsistent with tube_geometry_catalog_binding")
