"""Trusted, local observations used by TASK164.

The parent process is the only authority for the acceptance result.  This
module provides two deliberately narrow observations: local Git delivery
integrity and the isolated dual-runtime child capture.  Neither accepts
caller-supplied evidence as authoritative.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from hexagent.exchangers.shell_tube.tube_side.canonical import (
    KIND_STRING,
    frame_record,
)

from .models import (
    TASK164_ALLOWLIST,
    Task164CommandIdentity,
    Task164CrossPythonParityInput,
    Task164DualRuntimeObservation,
    Task164EvidenceAuthority,
    Task164PairingKey,
    Task164ParityStatus,
    Task164ParitySurface,
    Task164PythonVersion,
    Task164RunnerIdentity,
    Task164RuntimeObservation,
    Task164SurfaceHashRecord,
)

BASE_MAIN_SHA = "66dabc275bcf1a35d97e4d57fc70c2ccf05697e9"
BASE_MAIN_TREE = "5ff628f1327873dfd3eb195a672bb2a2c706cbdb"
TASK164_CHILD_MODULE = (
    "hexagent.release_demo.task164_integration_release_acceptance.trusted_evidence"
)


@dataclass(frozen=True, slots=True)
class MainDeliveryObservation:
    provider_identity: str
    predecessor_base_sha: str
    predecessor_base_tree: str
    observed_head_sha: str
    observed_head_tree: str
    predecessor_is_ancestor: bool
    changed_paths: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    tracked_worktree_clean: bool
    status: Task164ParityStatus


def _run_git(git: str, cwd: str, args: Sequence[str]) -> tuple[int, bytes, bytes]:
    completed = subprocess.run(
        [git, *args],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def observe_main_delivery(*, cwd: str | None = None) -> MainDeliveryObservation:
    """Run the exact local-Git predecessor and allowlist observations."""

    root = cwd or os.getcwd()
    git = shutil.which("git")
    if git is None:
        return MainDeliveryObservation(
            "LOCAL_GIT_READONLY_V1",
            BASE_MAIN_SHA,
            BASE_MAIN_TREE,
            "",
            "",
            False,
            (),
            TASK164_ALLOWLIST,
            False,
            Task164ParityStatus.BLOCKED,
        )

    def one(args: Sequence[str]) -> tuple[bool, str]:
        code, stdout, _ = _run_git(git, root, args)
        return code == 0, stdout.decode("ascii", "strict").strip() if code == 0 else ""

    head_ok, head = one(("rev-parse", "HEAD"))
    tree_ok, tree = one(("rev-parse", "HEAD^{tree}"))
    base_ok, _ = one(("cat-file", "-e", f"{BASE_MAIN_SHA}^{{commit}}"))
    base_tree_ok, _ = one(("cat-file", "-e", f"{BASE_MAIN_TREE}^{{tree}}"))
    ancestor_ok, _ = one(("merge-base", "--is-ancestor", BASE_MAIN_SHA, "HEAD"))
    paths_ok, path_text = one(("diff", "--name-only", f"{BASE_MAIN_SHA}..HEAD"))
    clean_code, _, _ = _run_git(git, root, ("diff", "--quiet", "HEAD", "--"))
    cached_code, _, _ = _run_git(git, root, ("diff", "--cached", "--quiet"))
    clean = clean_code == 0 and cached_code == 0
    if paths_ok:
        paths = tuple(sorted(set(path_text.splitlines()), key=lambda item: item.encode("utf-8")))
    else:
        paths = ()
    identity_ok = (
        head_ok
        and tree_ok
        and len(head) == 40
        and len(tree) == 40
        and all(char in "0123456789abcdef" for char in head + tree)
    )
    status = (
        Task164ParityStatus.PASS
        if base_ok
        and base_tree_ok
        and ancestor_ok
        and paths_ok
        and clean
        and identity_ok
        and set(paths).issubset(set(TASK164_ALLOWLIST))
        else Task164ParityStatus.BLOCKED
    )
    return MainDeliveryObservation(
        provider_identity="LOCAL_GIT_READONLY_V1",
        predecessor_base_sha=BASE_MAIN_SHA,
        predecessor_base_tree=BASE_MAIN_TREE,
        observed_head_sha=head,
        observed_head_tree=tree,
        predecessor_is_ancestor=ancestor_ok,
        changed_paths=paths,
        allowed_paths=TASK164_ALLOWLIST,
        tracked_worktree_clean=clean,
        status=status,
    )


def _child_payload(data: bytes) -> bytes:
    return frame_record(
        "TASK164_PARITY_CHILD_OUTPUT_V1",
        (("input_sha256", KIND_STRING, hashlib.sha256(data).hexdigest().encode("ascii")),),
    )


def _child_main() -> int:
    data = os.read(0, 16 * 1024 * 1024)
    os.write(1, _child_payload(data))
    return 0


def _runtime_surface(digest: str, ref: str) -> tuple[Task164SurfaceHashRecord, ...]:
    return (
        Task164SurfaceHashRecord(
            surface=Task164ParitySurface.TASK164_XPY_IDENTITY_PROJECTION_V1,
            sha256=digest,
            authority=Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
            evidence_ref="TASK164_DUAL_RUNTIME:identity",
        ),
        Task164SurfaceHashRecord(
            surface=Task164ParitySurface.TASK164_XPY_EVIDENCE_PROJECTION_V1,
            sha256=digest,
            authority=Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
            evidence_ref="TASK164_DUAL_RUNTIME:evidence",
        ),
    )


def _run_runtime(
    executable: str,
    version: Task164PythonVersion,
    input_bytes: bytes,
    head_sha: str,
    head_tree: str,
) -> Task164RuntimeObservation:
    environment = {
        "PYTHONHASHSEED": "0",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "PYTHONNOUSERSITE": "1",
        "TASK164_NETWORK_DISABLED": "1",
    }
    try:
        completed = subprocess.run(
            [executable, "-I", "-m", TASK164_CHILD_MODULE, "--child", "TASK164_PARITY_CHILD_V1"],
            input=input_bytes,
            capture_output=True,
            env=environment,
            timeout=30,
            check=False,
        )
        valid = completed.returncode == 0 and not completed.stderr and bool(completed.stdout)
        digest = hashlib.sha256(completed.stdout).hexdigest() if valid else "0" * 64
    except (OSError, subprocess.SubprocessError):
        valid = False
        digest = "0" * 64
    return Task164RuntimeObservation(
        python_version=version,
        head_sha=head_sha,
        head_tree=head_tree,
        runner_identity=Task164RunnerIdentity.TASK164_INTERNAL_DUAL_RUNTIME_RUNNER_V1,
        command_identity=Task164CommandIdentity.TASK164_INTERNAL_DUAL_RUNTIME_PARITY_CAPTURE_V1,
        surface_records=_runtime_surface(digest, version.value),
        child_output_sha256=digest,
        conclusion=Task164ParityStatus.PASS if valid else Task164ParityStatus.BLOCKED,
    )


def observe_dual_runtime(
    *,
    input_value: Task164CrossPythonParityInput,
    head_sha: str,
    head_tree: str,
    py311: str | None = None,
    py312: str | None = None,
) -> Task164DualRuntimeObservation:
    """Run the isolated parity children; caller claims are never trusted."""

    input_bytes = frame_record(
        "TASK164_CROSS_PYTHON_PARITY_INPUT_V1",
        (
            ("schema_version", KIND_STRING, input_value.schema_version.encode("utf-8")),
            (
                "original_task163_request_projection_hash",
                KIND_STRING,
                input_value.original_task163_request_projection_hash.encode("ascii"),
            ),
            ("task163_result_hash", KIND_STRING, input_value.task163_result_hash.encode("ascii")),
            ("task163_result_id", KIND_STRING, input_value.task163_result_id.encode("ascii")),
            (
                "task163_provenance_hash",
                KIND_STRING,
                input_value.task163_provenance_hash.encode("ascii"),
            ),
            (
                "applicability_projection_hash",
                KIND_STRING,
                input_value.applicability_projection_hash.encode("ascii"),
            ),
            (
                "completeness_projection_hash",
                KIND_STRING,
                input_value.completeness_projection_hash.encode("ascii"),
            ),
            (
                "scenario_matrix_projection_hash",
                KIND_STRING,
                input_value.scenario_matrix_projection_hash.encode("ascii"),
            ),
            (
                "repeat_run_evidence_projection_hash",
                KIND_STRING,
                input_value.repeat_run_evidence_projection_hash.encode("ascii"),
            ),
            (
                "terminal_capability_projection_hash",
                KIND_STRING,
                input_value.terminal_capability_projection_hash.encode("ascii"),
            ),
            (
                "scope_fence_projection_hash",
                KIND_STRING,
                input_value.scope_fence_projection_hash.encode("ascii"),
            ),
            ("head_sha", KIND_STRING, input_value.head_sha.encode("ascii")),
            ("head_tree", KIND_STRING, input_value.head_tree.encode("ascii")),
            (
                "task164_design_version",
                KIND_STRING,
                input_value.task164_design_version.encode("utf-8"),
            ),
            (
                "runtime_contract_version",
                KIND_STRING,
                input_value.runtime_contract_version.encode("utf-8"),
            ),
        ),
    )
    first = _run_runtime(
        py311
        or os.environ.get("TASK164_PY311_EXECUTABLE")
        or os.environ.get("TASK029_PY311_EXECUTABLE")
        or "",
        Task164PythonVersion.PYTHON_3_11,
        input_bytes,
        head_sha,
        head_tree,
    )
    second = _run_runtime(
        py312
        or os.environ.get("TASK164_PY312_EXECUTABLE")
        or os.environ.get("TASK029_PY312_EXECUTABLE")
        or "",
        Task164PythonVersion.PYTHON_3_12,
        input_bytes,
        head_sha,
        head_tree,
    )
    equal = (
        first.conclusion is Task164ParityStatus.PASS
        and second.conclusion is Task164ParityStatus.PASS
        and first.head_sha == second.head_sha == head_sha
        and first.head_tree == second.head_tree == head_tree
        and first.surface_records == second.surface_records
        and first.child_output_sha256 == second.child_output_sha256
    )
    return Task164DualRuntimeObservation(
        pairing_key=Task164PairingKey.TASK164_PYTHON_3_11__TASK164_PYTHON_3_12,
        python311_observation=first,
        python312_observation=second,
        status=Task164ParityStatus.PASS if equal else Task164ParityStatus.BLOCKED,
        evidence_refs=("TASK164_DUAL_RUNTIME_INTERNAL_OBSERVATION",),
    )


if __name__ == "__main__":  # pragma: no cover - exercised by CI child command
    raise SystemExit(_child_main() if len(sys.argv) >= 3 and sys.argv[1] == "--child" else 2)


__all__ = ["MainDeliveryObservation", "observe_dual_runtime", "observe_main_delivery"]
