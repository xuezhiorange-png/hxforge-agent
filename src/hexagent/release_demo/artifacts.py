"""Deterministic renderers for the six frozen TASK036 D23 artifacts."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .canonical import canonical_json, manifest_hash
from .schema import (
    ARTIFACT_IDS,
    ARTIFACT_PATHS,
    AVAILABLE_CAPABILITIES,
    MANIFEST_DIGEST_SERIALIZATION_PATHS,
    MANIFEST_FIELDS,
    MANIFEST_PEER_PATHS,
    RELEASE_VERSION,
    RELEASE_VERSION_DISPLAY_LABEL,
    TARGET_DISTRIBUTION_VERSION,
    UNAVAILABLE_CAPABILITIES,
)

RELEASE_EVIDENCE_ROOT = Path("release_evidence/v0.3.0")


def exact_file_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_json_bytes(evidence: Mapping[str, Any]) -> bytes:
    """Render normalized JSON evidence with one final LF."""

    return canonical_json(dict(evidence), trailing_newline=True)


def render_demo_markdown_bytes(evidence: Mapping[str, Any]) -> bytes:
    """Render the stable four-part demo evidence document."""

    graph = evidence["production_graph"]
    success = evidence["success_demo"]
    blocked = evidence["blocked_demos"]
    identities = evidence["producer_identities"]
    lines = [
        f"# {RELEASE_VERSION_DISPLAY_LABEL} TASK-020 -> TASK-035 Demonstration",
        "",
        "## Release Identity",
        "",
        f"- schema_version: `{evidence['schema_version']}`",
        f"- release_version: `{RELEASE_VERSION}`",
        f"- source_commit: `{evidence['source_commit']}`",
        f"- source_tree: `{evidence['source_tree']}`",
        f"- demo_id: `{success['demo_id']}`",
        "",
        "## Production Graph",
        "",
        f"- stages: `{graph['stages']}`",
        f"- actual_public_operations: `{graph['actual_public_operations']}`",
        f"- fixture_only_result_substitution: `{graph['fixture_only_result_substitution']}`",
        f"- expected_output_used_as_input: `{graph['expected_output_used_as_input']}`",
        f"- synthetic_oracle_substitution: `{graph['synthetic_oracle_substitution']}`",
        "",
        "### Public Statuses",
        "",
    ]
    for task in ("TASK031", "TASK032", "TASK033", "TASK034", "TASK035"):
        lines.append(f"- {task}: `{graph['statuses'][task]}`")
    lines.extend(
        [
            "",
            "## Success Demonstration",
            "",
            f"- demo_id: `{success['demo_id']}`",
            f"- status: `{success['status']}`",
            f"- task034_result_hash: `{success['task034_result_hash']}`",
            f"- task034_result_id: `{success['task034_result_id']}`",
            f"- task035_result_hash: `{success['task035_result_hash']}`",
            f"- task035_result_id: `{success['task035_result_id']}`",
            "",
            "## Blocked Demonstrations",
            "",
        ]
    )
    for item in blocked:
        lines.append(
            f"- `{item['demo_id']}`: stage=`{item['stage']}` "
            f"code=`{item['blocker_code']}` status=`{item['status']}`"
        )
    lines.extend(["", "## Producer Identity Bindings", ""])
    for key in (
        "TASK031_REQUEST_HASH",
        "TASK031_RESULT_HASH",
        "TASK031_RESULT_ID",
        "TASK032_REQUEST_HASH",
        "TASK032_RESULT_HASH",
        "TASK032_RESULT_ID",
        "TASK033_REQUEST_HASH",
        "TASK033_RESULT_HASH",
        "TASK033_RESULT_ID",
        "TASK034_REQUEST_HASH",
        "TASK034_RESULT_HASH",
        "TASK034_RESULT_ID",
        "TASK035_REQUEST_HASH",
        "TASK035_RESULT_HASH",
        "TASK035_RESULT_ID",
    ):
        lines.append(f"- {key}: `{identities[key]}`")
    lines.extend(
        [
            "",
            "## Capability Boundary",
            "",
            "- available: `" + ", ".join(AVAILABLE_CAPABILITIES) + "`",
            "- unavailable: `" + ", ".join(UNAVAILABLE_CAPABILITIES) + "`",
            "- release_acceptance_is_not_engineering_correctness_proof: `true`",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def render_acceptance_bytes(checklist: Mapping[str, Any]) -> bytes:
    lines = [
        f"# {RELEASE_VERSION_DISPLAY_LABEL} Release Acceptance",
        "",
        "- schema_version: `task036.release-acceptance-markdown.v1`",
        f"- release_version: `{RELEASE_VERSION}`",
        f"- checklist_id: `{checklist['checklist_id']}`",
        "",
        "## Acceptance Checklist",
        "",
    ]
    for item in checklist["required_test_ids"]:
        lines.append(f"- `{item}`: `PASS`")
    lines.extend(
        [
            "",
            "## Capability Boundary",
            "",
            "- required_available_capabilities: `" + ", ".join(AVAILABLE_CAPABILITIES) + "`",
            "- intentionally_unavailable_capabilities: `"
            + ", ".join(UNAVAILABLE_CAPABILITIES)
            + "`",
            "- release_acceptance_is_not_engineering_correctness_proof: `true`",
            "",
            "## Identity Boundary",
            "",
            "- upstream engineering values are consumed from public producer results",
            "- no upstream engineering equation is recomputed by TASK036",
            "- TASK036 internal result identity is distinct from release acceptance "
            "ledger identity",
        ]
    )
    return "\n".join(lines).encode("utf-8") + b"\n"


def build_manifest(
    *,
    source_commit: str,
    source_tree: str,
    artifact_bytes: Mapping[str, bytes],
    upstream_evidence_ledger_ref: str,
    release_acceptance_ledger_ref: str,
    acceptance_checklist_ref: str,
) -> dict[str, Any]:
    """Build N15 from the closed six-path inventory and three peer digests."""

    expected = set(ARTIFACT_PATHS)
    if set(artifact_bytes) != expected:
        missing = sorted(expected - set(artifact_bytes))
        extra = sorted(set(artifact_bytes) - expected)
        raise ValueError(f"artifact inventory mismatch; missing={missing}, extra={extra}")
    inventory = [
        {
            "artifact_id": artifact_id,
            "path": path,
            "required": True,
        }
        for artifact_id, path in zip(ARTIFACT_IDS, ARTIFACT_PATHS, strict=True)
    ]
    digest_set = [
        {"path": path, "sha256": exact_file_digest(artifact_bytes[path])}
        for path in MANIFEST_DIGEST_SERIALIZATION_PATHS
    ]
    record: dict[str, Any] = {
        "schema_version": "task036.manifest.v1",
        "manifest_id": "TASK036-MANIFEST-0.3.0",
        "release_version": TARGET_DISTRIBUTION_VERSION,
        "source_commit": source_commit,
        "source_tree": source_tree,
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
    if tuple(item["path"] for item in digest_set) != MANIFEST_DIGEST_SERIALIZATION_PATHS:
        raise AssertionError("manifest digest order drift")
    if set(MANIFEST_PEER_PATHS) - {item["path"] for item in inventory}:
        raise AssertionError("manifest peer path is outside the frozen inventory")
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
    """Materialize only the four persisted evidence files owned by N10/N14/N15."""

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "demo_json": output_dir / "task020-to-task035-demo.json",
        "demo_markdown": output_dir / "task020-to-task035-demo.md",
        "manifest": output_dir / "release-manifest.json",
        "acceptance": output_dir / "release-acceptance.md",
    }
    paths["demo_json"].write_bytes(demo_json_bytes)
    paths["demo_markdown"].write_bytes(demo_markdown_bytes)
    paths["acceptance"].write_bytes(acceptance_markdown_bytes)
    paths["manifest"].write_bytes(manifest_bytes)
    return paths


__all__ = [
    "RELEASE_EVIDENCE_ROOT",
    "build_manifest",
    "exact_file_digest",
    "render_acceptance_bytes",
    "render_demo_markdown_bytes",
    "render_json_bytes",
    "render_manifest_bytes",
    "write_release_evidence",
]
