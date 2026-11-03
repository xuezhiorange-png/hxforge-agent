"""Diagnostics for native request binding and authority gates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

DiagnosticResult = Literal["PASS", "BLOCKED", "FIXED"]


@dataclass(frozen=True)
class NativeBindingDiagnostic:
    stage: str
    field_path: str
    actual_blocker: str
    root_cause: str
    fixed_field: str | None
    source_identity: str
    result: DiagnosticResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "STAGE": self.stage,
            "FIELD_PATH": self.field_path,
            "ACTUAL_BLOCKER": self.actual_blocker,
            "ROOT_CAUSE": self.root_cause,
            "FIXED_FIELD": self.fixed_field,
            "SOURCE_IDENTITY": self.source_identity,
            "RESULT": self.result,
        }


def write_native_binding_diagnostics(
    output_dir: Path,
    entries: tuple[NativeBindingDiagnostic, ...],
) -> Path:
    path = output_dir / "NATIVE_REQUEST_BINDING_DIAGNOSTICS.json"
    payload = {
        "schema_version": "hxforge.native-binding-diagnostics.v1",
        "entries": [item.to_dict() for item in entries],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


EVALUATION_AUTHORITY_ORIENTATION_FIX = NativeBindingDiagnostic(
    stage="BAFFLE_GEOMETRY",
    field_path="evaluation_input_authority.task024_request_template.design_authority.orientation_sequence",
    actual_blocker="EVALUATION_AUTHORITY_REQUIRED",
    root_cause=(
        "Task173 sizing invoked Task168 with preserve_baffle_orientation_sequence=True while the "
        "validation task024 template carries three orientations for four baffles; sizing now uses "
        "per-candidate orientations (preserve_baffle_orientation_sequence=False)."
    ),
    fixed_field="task173_integrated_sizing.validate_sizing_request.preserve_baffle_orientation_sequence",
    source_identity="V07-T173-SIZING-IMPLEMENTATION-VALIDATION-CANDIDATE-SPACE-R2",
    result="FIXED",
)
