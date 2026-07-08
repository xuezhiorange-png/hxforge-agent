"""TASK-019 validation-report module.

Slice 1 scope: deterministic helpers + schema constants + report builder skeleton.
No full upstream calculation chain. No public API. No CLI. No DB schema.
No renderer. No external integration. No Feishu integration.
"""

from hexagent.validation_report.double_pipe_validation_report import (
    # Schema constants
    TASK_019_VALIDATION_REPORT_V1,
    TASK_019_GOLDEN_CASE_IDS,
    ALLOWED_OVERALL_STATUSES,
    # Deterministic helpers
    canonical_json_dumps,
    sha256_hex,
    deterministic_report_id,
    # Report builder skeleton
    build_double_pipe_validation_report,
)

__all__ = [
    "TASK_019_VALIDATION_REPORT_V1",
    "TASK_019_GOLDEN_CASE_IDS",
    "ALLOWED_OVERALL_STATUSES",
    "canonical_json_dumps",
    "sha256_hex",
    "deterministic_report_id",
    "build_double_pipe_validation_report",
]
