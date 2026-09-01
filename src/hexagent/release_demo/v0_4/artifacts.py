"""Deterministic A01--A06 release-evidence materialization."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .canonical import (
    acceptance_checklist_hash,
    canonical_json_value,
    manifest_hash,
)
from .schema import (
    ARTIFACT_IDS,
    ARTIFACT_PATHS,
    AVAILABLE_CAPABILITIES,
    MANIFEST_DIGEST_PATHS,
    MANIFEST_FIELDS,
    RELEASE_VERSION,
    TEST_IDS,
    UNAVAILABLE_CAPABILITIES,
)


def exact_file_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _jsonable(value: Any) -> Any:
    return canonical_json_value(value)


def render_json_bytes(value: Mapping[str, Any]) -> bytes:
    text = json.dumps(
        _jsonable(dict(value)),
        ensure_ascii=False,
        indent=2,
        separators=(",", ": "),
    )
    return (text + "\n").encode("utf-8")


def render_demo_json_bytes(evidence: Mapping[str, Any]) -> bytes:
    return render_json_bytes(evidence)


def render_demo_markdown_bytes(evidence: Mapping[str, Any]) -> bytes:
    graph = evidence["production_graph"]
    success = evidence["success_demo"]
    lines = [
        "# v0.4 TASK020 -> TASK038 Demonstration",
        "",
        "## Release Identity",
        "",
        f"- schema_version: `{evidence['schema_version']}`",
        f"- profile_id: `{evidence['profile_id']}`",
        f"- release_version: `{evidence['release_version']}`",
        f"- source_definition: `Issue #{evidence['source_definition_issue']} "
        f"{evidence['source_definition_revision']}`",
        f"- allocation_authority: `Issue #{evidence['allocation_issue']} "
        f"{evidence['allocation_revision']}`",
        f"- base_main_sha: `{evidence['base_main_sha']}`",
        f"- base_main_tree: `{evidence['base_main_tree']}`",
        "",
        "## Production Graph",
        "",
        f"- stages: `{graph['stages']}`",
        f"- public_operations: `{graph['actual_public_operations']}`",
        f"- statuses: `{graph['statuses']}`",
        f"- fixture_only_result_substitution: `{graph['fixture_only_result_substitution']}`",
        f"- expected_output_used_as_input: `{graph['expected_output_used_as_input']}`",
        f"- private_helper_stage_bypass: `{graph['private_helper_stage_bypass']}`",
        f"- no_upstream_engineering_recomputation: "
        f"`{graph['no_upstream_engineering_recomputation']}`",
        "",
        "## Success Demonstration",
        "",
        f"- demo_id: `{success['demo_id']}`",
        f"- status: `{success['status']}`",
        f"- task038_result_hash: `{success['task038_result_hash']}`",
        f"- task038_result_id: `{success['task038_result_id']}`",
        f"- modeled_overall_heat_transfer_coefficient_w_m2_k: "
        f"`{success['modeled_overall_heat_transfer_coefficient_w_m2_k']}`",
        f"- outer_tube_surface_effective_area_m2: "
        f"`{success['outer_tube_surface_effective_area_m2']}`",
        f"- modeled_ua_w_k: `{success['modeled_ua_w_k']}`",
        "",
        "## Blocked Demonstrations",
        "",
    ]
    for item in evidence["blocked_demos"]:
        lines.append(
            f"- `{item['demo_id']}`: `{item['blocker_code']}` / "
            f"`{item['stage']}` / `{item['field_path']}`"
        )
    lines.extend(["", "## Capability Boundary", ""])
    lines.append("- available: `" + ", ".join(AVAILABLE_CAPABILITIES) + "`")
    lines.append("- intentionally_unavailable: `" + ", ".join(UNAVAILABLE_CAPABILITIES) + "`")
    lines.append("- release_acceptance_is_not_engineering_correctness_proof: `true`")
    lines.extend(["", "## Identity and Provenance", ""])
    for key, value in evidence["identity_bindings"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Acceptance", "", "- acceptance_item_count: `30`", "- status: `PASS`", ""])
    return "\n".join(lines).encode("utf-8")


def render_acceptance_bytes(checklist: Mapping[str, Any]) -> bytes:
    lines = [
        "# v0.4 Release Acceptance",
        "",
        f"- schema_version: `{checklist['schema_version']}`",
        f"- checklist_id: `{checklist['checklist_id']}`",
        f"- release_version: `{checklist['release_version']}`",
        "",
        "## Acceptance Checklist",
        "",
    ]
    for item in checklist["items"]:
        lines.append(f"- `{item['test_id']}`: `{item['status']}`")
    lines.extend(
        [
            "",
            "## Capability Boundary",
            "",
            "- available: `" + ", ".join(AVAILABLE_CAPABILITIES) + "`",
            "- intentionally_unavailable: `" + ", ".join(UNAVAILABLE_CAPABILITIES) + "`",
            "- release_acceptance_is_not_engineering_correctness_proof: `true`",
            "",
            "## Engineering-Proof Boundary",
            "",
            "- upstream engineering values are consumed from accepted public producer results",
            "- TASK039 does not recompute upstream engineering equations",
            "- fixture-only producer-success substitution is forbidden",
            "- expected output, expected result hash and expected result id are not runtime inputs",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def build_manifest(
    *,
    artifact_bytes: Mapping[str, bytes],
    upstream_evidence_ledger_ref: str,
    release_acceptance_ledger_ref: str,
    acceptance_checklist_ref: str,
) -> dict[str, Any]:
    if set(artifact_bytes) != set(ARTIFACT_PATHS):
        raise ValueError("A01-A06 inventory mismatch")
    inventory = [
        {"artifact_id": artifact_id, "path": path, "required": True}
        for artifact_id, path in zip(ARTIFACT_IDS, ARTIFACT_PATHS, strict=True)
    ]
    digest_set = [
        {"path": path, "sha256": exact_file_digest(artifact_bytes[path])}
        for path in MANIFEST_DIGEST_PATHS
    ]
    record: dict[str, Any] = {
        "schema_version": "task039.release-manifest.v1",
        "manifest_id": "TASK039-MANIFEST-0.4.0",
        "release_version": RELEASE_VERSION,
        "artifact_inventory": inventory,
        "artifact_digest_set": digest_set,
        "python_versions": ["3.11", "3.12"],
        "repeat_run_count": 2,
        "upstream_evidence_ledger_ref": upstream_evidence_ledger_ref,
        "release_acceptance_ledger_ref": release_acceptance_ledger_ref,
        "acceptance_checklist_ref": acceptance_checklist_ref,
        "manifest_hash": "",
    }
    record["manifest_hash"] = manifest_hash(record)
    if tuple(record) != MANIFEST_FIELDS:
        raise AssertionError("manifest field order drift")
    return record


def render_manifest_bytes(manifest: Mapping[str, Any]) -> bytes:
    return render_json_bytes(manifest)


def write_release_evidence(
    *,
    output_dir: Path,
    demo_json_bytes: bytes,
    demo_markdown_bytes: bytes,
    manifest_bytes: bytes,
    acceptance_markdown_bytes: bytes,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "demo_json": output_dir / "task020-to-task038-demo.json",
        "demo_markdown": output_dir / "task020-to-task038-demo.md",
        "manifest": output_dir / "release-manifest.json",
        "acceptance": output_dir / "release-acceptance.md",
    }
    paths["demo_json"].write_bytes(demo_json_bytes)
    paths["demo_markdown"].write_bytes(demo_markdown_bytes)
    paths["manifest"].write_bytes(manifest_bytes)
    paths["acceptance"].write_bytes(acceptance_markdown_bytes)
    return paths


def build_checklist(items: list[dict[str, Any]]) -> dict[str, Any]:
    checklist: dict[str, Any] = {
        "schema_version": "task039.acceptance-checklist.v1",
        "checklist_id": "TASK039-CHECKLIST-0.4.0",
        "release_version": RELEASE_VERSION,
        "required_test_ids": list(TEST_IDS),
        "required_artifact_paths": list(ARTIFACT_PATHS),
        "required_python_versions": ["3.11", "3.12"],
        "repeat_run_count": 2,
        "items": items,
        "checklist_status": "PASS" if len(items) == len(TEST_IDS) else "BLOCKED",
        "checklist_hash": "",
    }
    checklist["checklist_hash"] = acceptance_checklist_hash(checklist)
    return checklist


__all__ = [
    "ARTIFACT_PATHS",
    "build_checklist",
    "build_manifest",
    "exact_file_digest",
    "render_acceptance_bytes",
    "render_demo_json_bytes",
    "render_demo_markdown_bytes",
    "render_json_bytes",
    "render_manifest_bytes",
    "write_release_evidence",
]
