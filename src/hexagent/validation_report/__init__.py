"""TASK-019 validation-report module.

Slice 1 scope: deterministic helpers + schema constants + report builder skeleton.
No full upstream calculation chain. No public API. No CLI. No DB schema.
No renderer. No external integration. No Feishu integration.
"""

from hexagent.validation_report.double_pipe_validation_report import (
    ALLOWED_OVERALL_STATUSES,
    TASK_019_GOLDEN_CASE_IDS,
    # Schema constants
    TASK_019_VALIDATION_REPORT_V1,
    # Report builder skeleton
    build_double_pipe_validation_report,
    # Deterministic helpers
    canonical_json_dumps,
    deterministic_report_id,
    sha256_hex,
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
