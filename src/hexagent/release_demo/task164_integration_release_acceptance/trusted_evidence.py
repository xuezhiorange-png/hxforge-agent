"""Trusted, local observations used by TASK164.

The parent process is the only authority for the acceptance result.  This
module provides two deliberately narrow observations: local Git delivery
integrity and the isolated dual-runtime child capture.  Neither accepts
caller-supplied evidence as authoritative.
"""

from __future__ import annotations

import ast
import hashlib
import os
import shutil
import struct
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

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
    Task164ForbiddenCapabilityToken,
    Task164PairingKey,
    Task164ParityStatus,
    Task164ParitySurface,
    Task164PythonVersion,
    Task164RunnerIdentity,
    Task164RuntimeObservation,
    Task164ScopeFenceEvidence,
    Task164ScopeStatus,
    Task164SurfaceHashRecord,
    runtime_identity_for_version,
)

BASE_MAIN_SHA = "66dabc275bcf1a35d97e4d57fc70c2ccf05697e9"
BASE_MAIN_TREE = "5ff628f1327873dfd3eb195a672bb2a2c706cbdb"
TASK164_DELIVERY_SHA = "6fd31c597cc3572f20baea42afbbaa642531fb40"
TASK164_CHILD_MODULE = (
    "hexagent.release_demo.task164_integration_release_acceptance.trusted_evidence"
)
TASK164_CHILD_ARGV = ("--child", "TASK164_PARITY_CHILD_V1")
TASK164_CHILD_ENVIRONMENT = {
    "PYTHONHASHSEED": "0",
    "LC_ALL": "C.UTF-8",
    "TZ": "UTC",
    "PYTHONNOUSERSITE": "1",
    "TASK164_NETWORK_DISABLED": "1",
}
TASK164_CHILD_OUTPUT_FIELDS = (
    "actual_python_major_minor",
    "runtime_identity",
    "verified_head_sha",
    "verified_head_tree",
    "runner_identity",
    "command_identity",
    "identity_projection_sha256",
    "evidence_projection_sha256",
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

    del cwd
    root_path = _repository_root()
    if root_path is None:
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
    root = str(root_path)
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
    ancestor_ok, _ = one(
        ("merge-base", "--is-ancestor", TASK164_DELIVERY_SHA, "HEAD")
    )
    paths_ok, path_text = one(
        ("diff", "--name-only", f"{BASE_MAIN_SHA}..{TASK164_DELIVERY_SHA}")
    )
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


def _repository_root() -> Path | None:
    configured_root = os.environ.get("TASK164_REPOSITORY_ROOT")
    if configured_root:
        configured_path = Path(configured_root).resolve()
        if (configured_path / ".git").exists() and (configured_path / "pyproject.toml").is_file():
            return configured_path
    module_path = Path(__file__).resolve()
    current_path = Path.cwd().resolve()
    for candidate in (
        current_path,
        *current_path.parents,
        module_path.parent,
        *module_path.parents,
    ):
        if (candidate / ".git").exists() and (candidate / "pyproject.toml").is_file():
            return candidate
    return None


def _u32(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError("truncated u32")
    return struct.unpack_from(">I", data, offset)[0], offset + 4


def _u64(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 8 > len(data):
        raise ValueError("truncated u64")
    return struct.unpack_from(">Q", data, offset)[0], offset + 8


def _read_bytes(data: bytes, offset: int, length: int) -> tuple[bytes, int]:
    end = offset + length
    if end > len(data):
        raise ValueError("truncated payload")
    return data[offset:end], end


def _parse_record(data: bytes) -> tuple[str, dict[str, tuple[bytes, bytes]]]:
    ns_len, offset = _u32(data, 0)
    namespace_bytes, offset = _read_bytes(data, offset, ns_len)
    namespace = namespace_bytes.decode("utf-8", "strict")
    field_count, offset = _u32(data, offset)
    fields: dict[str, tuple[bytes, bytes]] = {}
    for _ in range(field_count):
        name_len, offset = _u32(data, offset)
        name_bytes, offset = _read_bytes(data, offset, name_len)
        name = name_bytes.decode("utf-8", "strict")
        kind_len, offset = _u32(data, offset)
        kind, offset = _read_bytes(data, offset, kind_len)
        payload_len, offset = _u64(data, offset)
        payload, offset = _read_bytes(data, offset, payload_len)
        if name in fields:
            raise ValueError("duplicate parity input field")
        fields[name] = (kind, payload)
    if offset != len(data):
        raise ValueError("trailing parity input bytes")
    return namespace, fields


def _string_field(fields: dict[str, tuple[bytes, bytes]], name: str) -> str:
    kind, payload = fields[name]
    if kind != KIND_STRING:
        raise ValueError(f"parity field {name} is not a string")
    return payload.decode("utf-8", "strict")


_PARITY_FIELDS = (
    "schema_version",
    "original_task163_request_projection_hash",
    "task163_result_hash",
    "task163_result_id",
    "task163_provenance_hash",
    "applicability_projection_hash",
    "completeness_projection_hash",
    "scenario_matrix_projection_hash",
    "repeat_run_evidence_projection_hash",
    "terminal_capability_projection_hash",
    "scope_fence_projection_hash",
    "head_sha",
    "head_tree",
    "task164_design_version",
    "runtime_contract_version",
)


def _projection_bytes(values: dict[str, str], names: tuple[str, ...], domain: str) -> bytes:
    return frame_record(
        domain,
        tuple((name, KIND_STRING, values[name].encode("utf-8", "strict")) for name in names),
    )


def _parent_projection_digests(input_value: Task164CrossPythonParityInput) -> tuple[str, str]:
    values = {
        "schema_version": input_value.schema_version,
        "original_task163_request_projection_hash": (
            input_value.original_task163_request_projection_hash
        ),
        "task163_result_hash": input_value.task163_result_hash,
        "task163_result_id": input_value.task163_result_id,
        "task163_provenance_hash": input_value.task163_provenance_hash,
        "applicability_projection_hash": input_value.applicability_projection_hash,
        "completeness_projection_hash": input_value.completeness_projection_hash,
        "scenario_matrix_projection_hash": input_value.scenario_matrix_projection_hash,
        "repeat_run_evidence_projection_hash": input_value.repeat_run_evidence_projection_hash,
        "terminal_capability_projection_hash": input_value.terminal_capability_projection_hash,
        "scope_fence_projection_hash": input_value.scope_fence_projection_hash,
        "head_sha": input_value.head_sha,
        "head_tree": input_value.head_tree,
        "task164_design_version": input_value.task164_design_version,
        "runtime_contract_version": input_value.runtime_contract_version,
    }
    return (
        hashlib.sha256(
            _projection_bytes(values, _IDENTITY_FIELDS, "TASK164_XPY_IDENTITY_PROJECTION_V1")
        ).hexdigest(),
        hashlib.sha256(
            _projection_bytes(values, _EVIDENCE_FIELDS, "TASK164_XPY_EVIDENCE_PROJECTION_V1")
        ).hexdigest(),
    )


_IDENTITY_FIELDS = (
    "schema_version",
    "original_task163_request_projection_hash",
    "task163_result_hash",
    "task163_result_id",
    "task163_provenance_hash",
    "head_sha",
    "head_tree",
    "task164_design_version",
    "runtime_contract_version",
)
_EVIDENCE_FIELDS = (
    "schema_version",
    "applicability_projection_hash",
    "completeness_projection_hash",
    "scenario_matrix_projection_hash",
    "repeat_run_evidence_projection_hash",
    "terminal_capability_projection_hash",
    "scope_fence_projection_hash",
    "head_sha",
    "head_tree",
    "task164_design_version",
    "runtime_contract_version",
)


def _child_payload(data: bytes) -> bytes:
    namespace, fields = _parse_record(data)
    if namespace != "TASK164_CROSS_PYTHON_PARITY_INPUT_V1":
        raise ValueError("unexpected parity input namespace")
    if tuple(fields) != _PARITY_FIELDS or set(fields) != set(_PARITY_FIELDS):
        raise ValueError("unexpected parity input fields")
    values = {name: _string_field(fields, name) for name in _PARITY_FIELDS}
    root = _repository_root()
    git = shutil.which("git")
    if root is None or git is None:
        raise ValueError("parity child cannot establish repository authority")

    def git_identity(revision: str) -> str:
        code, stdout, stderr = _run_git(git, str(root), ("rev-parse", revision))
        if code != 0 or stderr:
            raise ValueError("parity child git observation failed")
        return stdout.decode("ascii", "strict").strip()

    observed_head = git_identity("HEAD")
    observed_tree = git_identity("HEAD^{tree}")
    if observed_head != values["head_sha"] or observed_tree != values["head_tree"]:
        raise ValueError("parity child observed a different checkout")
    major_minor = f"{sys.version_info.major}.{sys.version_info.minor}"
    runtime_identity = f"{sys.implementation.name}:{major_minor}"
    identity = hashlib.sha256(
        _projection_bytes(values, _IDENTITY_FIELDS, "TASK164_XPY_IDENTITY_PROJECTION_V1")
    ).hexdigest()
    evidence = hashlib.sha256(
        _projection_bytes(values, _EVIDENCE_FIELDS, "TASK164_XPY_EVIDENCE_PROJECTION_V1")
    ).hexdigest()
    return frame_record(
        "TASK164_PARITY_CHILD_OUTPUT_V2",
        (
            ("actual_python_major_minor", KIND_STRING, major_minor.encode("ascii")),
            ("runtime_identity", KIND_STRING, runtime_identity.encode("utf-8", "strict")),
            ("verified_head_sha", KIND_STRING, observed_head.encode("ascii")),
            ("verified_head_tree", KIND_STRING, observed_tree.encode("ascii")),
            (
                "runner_identity",
                KIND_STRING,
                Task164RunnerIdentity.TASK164_INTERNAL_DUAL_RUNTIME_RUNNER_V1.value.encode("ascii"),
            ),
            (
                "command_identity",
                KIND_STRING,
                Task164CommandIdentity.TASK164_INTERNAL_DUAL_RUNTIME_PARITY_CAPTURE_V1.value.encode(
                    "ascii"
                ),
            ),
            ("identity_projection_sha256", KIND_STRING, identity.encode("ascii")),
            ("evidence_projection_sha256", KIND_STRING, evidence.encode("ascii")),
        ),
    )


def _child_main() -> int:
    if tuple(sys.argv[1:]) != TASK164_CHILD_ARGV:
        return 2
    data = os.read(0, 16 * 1024 * 1024)
    os.write(1, _child_payload(data))
    return 0


def _runtime_surface(
    identity_digest: str, evidence_digest: str
) -> tuple[Task164SurfaceHashRecord, ...]:
    return (
        Task164SurfaceHashRecord(
            surface=Task164ParitySurface.TASK164_XPY_IDENTITY_PROJECTION_V1,
            sha256=identity_digest,
            authority=Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
            evidence_ref="TASK164_DUAL_RUNTIME:identity",
        ),
        Task164SurfaceHashRecord(
            surface=Task164ParitySurface.TASK164_XPY_EVIDENCE_PROJECTION_V1,
            sha256=evidence_digest,
            authority=Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
            evidence_ref="TASK164_DUAL_RUNTIME:evidence",
        ),
    )


def _child_surface_digest(identity_digest: str, evidence_digest: str) -> str:
    payload = frame_record(
        "TASK164_PARITY_CHILD_SURFACE_DIGEST_V1",
        (
            ("identity_projection_sha256", KIND_STRING, identity_digest.encode("ascii")),
            ("evidence_projection_sha256", KIND_STRING, evidence_digest.encode("ascii")),
        ),
    )
    return hashlib.sha256(payload).hexdigest()


def _blocked_runtime_observation(version: Task164PythonVersion) -> Task164RuntimeObservation:
    return Task164RuntimeObservation(
        python_version=version,
        head_sha="",
        head_tree="",
        runner_identity=Task164RunnerIdentity.TASK164_INTERNAL_DUAL_RUNTIME_RUNNER_V1,
        command_identity=Task164CommandIdentity.TASK164_INTERNAL_DUAL_RUNTIME_PARITY_CAPTURE_V1,
        surface_records=_runtime_surface("0" * 64, "0" * 64),
        child_output_sha256="0" * 64,
        conclusion=Task164ParityStatus.BLOCKED,
    )


def _run_runtime(
    executable: str,
    version: Task164PythonVersion,
    input_bytes: bytes,
    head_sha: str,
    head_tree: str,
) -> Task164RuntimeObservation:
    environment = dict(TASK164_CHILD_ENVIRONMENT)
    environment["PATH"] = os.environ.get("PATH", "")
    repository_root = _repository_root()
    if repository_root is not None:
        environment["TASK164_REPOSITORY_ROOT"] = str(repository_root)
    identity_digest = evidence_digest = "0" * 64
    actual_major_minor = ""
    runtime_identity = ""
    observed_head = observed_tree = ""
    runner_identity = Task164RunnerIdentity.TASK164_INTERNAL_DUAL_RUNTIME_RUNNER_V1
    command_identity = Task164CommandIdentity.TASK164_INTERNAL_DUAL_RUNTIME_PARITY_CAPTURE_V1
    valid = False
    try:
        completed = subprocess.run(
            [executable, "-I", "-m", TASK164_CHILD_MODULE, *TASK164_CHILD_ARGV],
            input=input_bytes,
            capture_output=True,
            env=environment,
            timeout=30,
            check=False,
        )
        valid = completed.returncode == 0 and not completed.stderr and bool(completed.stdout)
        namespace, fields = _parse_record(completed.stdout) if valid else ("", {})
        if namespace != "TASK164_PARITY_CHILD_OUTPUT_V2":
            raise ValueError("unexpected parity child namespace")
        if tuple(fields) != TASK164_CHILD_OUTPUT_FIELDS:
            raise ValueError("unexpected parity child fields")
        actual_major_minor = _string_field(fields, "actual_python_major_minor")
        runtime_identity = _string_field(fields, "runtime_identity")
        observed_head = _string_field(fields, "verified_head_sha")
        observed_tree = _string_field(fields, "verified_head_tree")
        child_runner_identity = _string_field(fields, "runner_identity")
        child_command_identity = _string_field(fields, "command_identity")
        identity_digest = _string_field(fields, "identity_projection_sha256")
        evidence_digest = _string_field(fields, "evidence_projection_sha256")
        expected_major_minor = version.value.removeprefix("PYTHON_").replace("_", ".")
        if (
            actual_major_minor != expected_major_minor
            or runtime_identity != runtime_identity_for_version(version)
            or observed_head != head_sha
            or observed_tree != head_tree
            or child_runner_identity
            != Task164RunnerIdentity.TASK164_INTERNAL_DUAL_RUNTIME_RUNNER_V1.value
            or child_command_identity
            != Task164CommandIdentity.TASK164_INTERNAL_DUAL_RUNTIME_PARITY_CAPTURE_V1.value
        ):
            raise ValueError("parity child metadata does not match its assigned runtime")
        if any(
            len(value) != 64 or any(char not in "0123456789abcdef" for char in value)
            for value in (identity_digest, evidence_digest)
        ):
            raise ValueError("invalid parity child digest")
        output_sha = _child_surface_digest(identity_digest, evidence_digest)
    except (OSError, subprocess.SubprocessError):
        valid = False
    except (UnicodeError, ValueError, struct.error):
        valid = False
    except BaseException:
        valid = False
    if not valid:
        return _blocked_runtime_observation(version)
    return Task164RuntimeObservation(
        python_version=version,
        head_sha=observed_head,
        head_tree=observed_tree,
        runner_identity=runner_identity,
        command_identity=command_identity,
        surface_records=_runtime_surface(identity_digest, evidence_digest),
        child_output_sha256=output_sha,
        conclusion=Task164ParityStatus.PASS,
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
    expected_identity, expected_evidence = _parent_projection_digests(input_value)
    if py311 and py312 and os.path.abspath(py311) == os.path.abspath(py312):
        first = _blocked_runtime_observation(Task164PythonVersion.PYTHON_3_11)
        second = _blocked_runtime_observation(Task164PythonVersion.PYTHON_3_12)
        return Task164DualRuntimeObservation(
            pairing_key=Task164PairingKey.TASK164_PYTHON_3_11__TASK164_PYTHON_3_12,
            python311_observation=first,
            python312_observation=second,
            status=Task164ParityStatus.BLOCKED,
            evidence_refs=("TASK164_DUAL_RUNTIME_INTERNAL_OBSERVATION",),
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
        and first.python_version is Task164PythonVersion.PYTHON_3_11
        and second.python_version is Task164PythonVersion.PYTHON_3_12
        and first.head_sha == second.head_sha == head_sha
        and first.head_tree == second.head_tree == head_tree
        and first.runner_identity is Task164RunnerIdentity.TASK164_INTERNAL_DUAL_RUNTIME_RUNNER_V1
        and second.runner_identity is Task164RunnerIdentity.TASK164_INTERNAL_DUAL_RUNTIME_RUNNER_V1
        and first.command_identity
        is Task164CommandIdentity.TASK164_INTERNAL_DUAL_RUNTIME_PARITY_CAPTURE_V1
        and second.command_identity
        is Task164CommandIdentity.TASK164_INTERNAL_DUAL_RUNTIME_PARITY_CAPTURE_V1
        and first.surface_records == second.surface_records
        and first.child_output_sha256 == second.child_output_sha256
        and first.surface_records[0].sha256 == expected_identity
        and first.surface_records[1].sha256 == expected_evidence
        and second.surface_records[0].sha256 == expected_identity
        and second.surface_records[1].sha256 == expected_evidence
    )
    return Task164DualRuntimeObservation(
        pairing_key=Task164PairingKey.TASK164_PYTHON_3_11__TASK164_PYTHON_3_12,
        python311_observation=first,
        python312_observation=second,
        status=Task164ParityStatus.PASS if equal else Task164ParityStatus.BLOCKED,
        evidence_refs=("TASK164_DUAL_RUNTIME_INTERNAL_OBSERVATION",),
    )


_SCOPE_FORBIDDEN_IDENTIFIERS = {
    "lmtd",
    "calculatelmtd",
    "lmtdcorrection",
    "lmtdcorrectionfactor",
    "ffactor",
    "calculateffactor",
    "ntu",
    "effectiveness",
    "heatduty",
    "calculateheatduty",
    "outlettemperature",
    "calculateoutlettemperature",
    "energybalance",
    "calculateenergybalance",
    "terminaltemperature",
    "calculateterminaltemperature",
    "task165",
}


def _normalize_identifier(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _scope_marker_for_identifier(value: str) -> str | None:
    normalized = _normalize_identifier(value)
    if "lmtdcorrectionfactor" in normalized or "lmtdcorrection" in normalized:
        return "LMTD_CORRECTION_FACTOR"
    if "lmtd" in normalized:
        return "LMTD"
    if "ffactor" in normalized:
        return "F_FACTOR"
    if "ntu" in normalized:
        return "NEW_NTU"
    if "effectiveness" in normalized:
        return "NEW_EFFECTIVENESS"
    if "heatduty" in normalized:
        return "NEW_HEAT_DUTY"
    if "outlettemperature" in normalized:
        return "NEW_OUTLET_TEMPERATURE"
    if "energybalance" in normalized:
        return "NEW_ENERGY_BALANCE"
    if "terminaltemperature" in normalized:
        return "NEW_TERMINAL_TEMPERATURE"
    if normalized == "task165" or normalized.endswith("task165"):
        return "TASK165"
    if normalized in _SCOPE_FORBIDDEN_IDENTIFIERS:
        return normalized.upper()
    return None


def _is_enum_class(node: ast.ClassDef) -> bool:
    return any(
        (isinstance(base, ast.Name) and _normalize_identifier(base.id) in {"enum", "strenum"})
        or (
            isinstance(base, ast.Attribute)
            and _normalize_identifier(base.attr) in {"enum", "strenum"}
        )
        for base in node.bases
    )


def _is_inside_enum(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    current: ast.AST | None = node
    while current is not None:
        if isinstance(current, ast.ClassDef) and _is_enum_class(current):
            return True
        current = parents.get(current)
    return False


def _scope_failure() -> Task164ScopeFenceEvidence:
    return Task164ScopeFenceEvidence(
        forbidden_capability_tokens_absent=(),
        forbidden_formula_surface_absent=False,
        upstream_replay_absent=False,
        private_upstream_access_absent=False,
        task165_absent=False,
        status=Task164ScopeStatus.BLOCKED,
    )


def observe_scope_fence(*, source_root: Path | str | None = None) -> Task164ScopeFenceEvidence:
    """Audit every package Python file for executable scope violations."""

    package_root = (
        Path(source_root).resolve() if source_root is not None else Path(__file__).resolve().parent
    )
    try:
        source_paths = tuple(
            sorted(
                (path for path in package_root.glob("*.py") if path.is_file()),
                key=lambda path: path.name.encode("utf-8"),
            )
        )
        if not source_paths:
            return _scope_failure()
        trees: dict[Path, ast.Module] = {}
        for path in source_paths:
            trees[path] = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except BaseException:
        return _scope_failure()

    violations: set[str] = set()
    upstream_modules = (
        "thermal_stream_state",
        "flow_arrangement_performance_method_authority",
        "overall_heat_transfer_coefficient_ua",
    )
    allowed_model_modules = {
        "hexagent.exchangers.shell_tube.thermal_stream_state.models",
        "hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority.models",
        "hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models",
    }
    allowed_canonical_names = {
        "task038_result_identity_projection",
        "task160_result_identity_projection",
        "task161_result_identity_projection",
        "task162_result_identity_projection",
        "task162_success_replay_evidence_identity_projection",
    }
    enum_class_names = {
        node.name
        for tree in trees.values()
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and _is_enum_class(node)
    }
    forbidden_upstream = False
    private_import = False
    for _path, tree in trees.items():
        parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        for node in ast.walk(tree):
            if not _is_inside_enum(node, parents):
                names: tuple[str, ...] = ()
                if isinstance(node, ast.Name):
                    names = (node.id,)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names = (node.name,)
                elif isinstance(node, ast.Attribute):
                    names = (
                        ()
                        if isinstance(node.value, ast.Name) and node.value.id in enum_class_names
                        else (node.attr,)
                    )
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = tuple(alias.name for alias in node.names) + tuple(
                        alias.asname for alias in node.names if alias.asname is not None
                    )
                for name in names:
                    marker = _scope_marker_for_identifier(name)
                    if marker is not None:
                        violations.add(marker)
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if any(alias.name.startswith("_") for alias in node.names):
                    private_import = True
                if any(item in module for item in upstream_modules):
                    if module in allowed_model_modules:
                        continue
                    if module.endswith(".service"):
                        if tuple(alias.name for alias in node.names) != ("validate_request",):
                            forbidden_upstream = True
                        continue
                    if module.endswith(".canonical"):
                        if any(alias.name not in allowed_canonical_names for alias in node.names):
                            forbidden_upstream = True
                        continue
                    forbidden_upstream = True
            elif isinstance(node, ast.Import) and any(
                alias.name.startswith("_") for alias in node.names
            ):
                private_import = True

    try:
        from . import scenarios as scenario_module
        from . import service as service_module

        public_task163 = (
            getattr(service_module, "validate_task163_request", None),
            getattr(scenario_module, "validate_task163_request", None),
        )
        public_replay = all(
            getattr(value, "__module__", "")
            == "hexagent.exchangers.shell_tube.thermal_rating_composition.service"
            and getattr(value, "__name__", "") == "validate_request"
            for value in public_task163
        )
    except BaseException:
        public_replay = False

    forbidden_tokens = tuple(Task164ForbiddenCapabilityToken)
    present = set(violations)
    absent = tuple(token for token in forbidden_tokens if token.value not in present)
    formula_violations = present - {"TASK165"}
    formula_ok = not formula_violations
    task165_ok = "TASK165" not in present
    upstream_ok = not forbidden_upstream
    private_ok = not private_import
    status = (
        Task164ScopeStatus.PASS
        if len(absent) == len(forbidden_tokens)
        and formula_ok
        and upstream_ok
        and private_ok
        and task165_ok
        and public_replay
        else Task164ScopeStatus.BLOCKED
    )
    return Task164ScopeFenceEvidence(
        forbidden_capability_tokens_absent=absent,
        forbidden_formula_surface_absent=formula_ok,
        upstream_replay_absent=upstream_ok,
        private_upstream_access_absent=private_ok and public_replay,
        task165_absent=task165_ok,
        status=status,
    )


if __name__ == "__main__":  # pragma: no cover - exercised by CI child command
    raise SystemExit(_child_main())


__all__ = [
    "MainDeliveryObservation",
    "observe_dual_runtime",
    "observe_main_delivery",
    "observe_scope_fence",
]
