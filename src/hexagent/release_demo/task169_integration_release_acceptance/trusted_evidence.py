"""Trusted cross-Python observations for TASK-169.

The parent constructs the parity input from results it produced by replaying
the TASK-168 request.  The child receives only framed bytes, verifies its own
interpreter and checkout, and returns observations.  Caller-provided hashes or
runtime claims are never accepted as evidence.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from hexagent.exchangers.shell_tube.tube_side.canonical import KIND_STRING, frame_record

PARITY_SCHEMA_VERSION = "task169.cross-python-parity-input.v1"
RUNNER_IDENTITY = "TASK169_INTERNAL_DUAL_RUNTIME_RUNNER_V1"
COMMAND_IDENTITY = "TASK169_INTERNAL_DUAL_RUNTIME_CAPTURE_V1"
CHILD_MODULE = "hexagent.release_demo.task169_integration_release_acceptance.trusted_evidence"
CHILD_ENVIRONMENT = {
    "PYTHONHASHSEED": "0",
    "LC_ALL": "C.UTF-8",
    "TZ": "UTC",
    "PYTHONNOUSERSITE": "1",
    "TASK169_NETWORK_DISABLED": "1",
}
_FIELD_NAMES = (
    "schema_version",
    "release_request_hash",
    "task168_request_hashes",
    "task168_result_hashes",
    "task169_result_hashes",
    "task169_result_ids",
    "head_sha",
    "head_tree",
    "software_version",
)
_CHILD_OUTPUT_FIELDS = (
    "actual_python_major_minor",
    "runtime_identity",
    "verified_head_sha",
    "verified_head_tree",
    "canonical_input_sha256",
    "task169_result_hashes",
    "task169_result_ids",
    "identity_projection_sha256",
    "runner_identity",
    "command_identity",
)


@dataclass(frozen=True, slots=True)
class Task169ParityInput:
    release_request_hash: str
    task168_request_hashes: tuple[tuple[str, str], ...]
    task168_result_hashes: tuple[tuple[str, str], ...]
    task169_result_hashes: tuple[tuple[str, str], ...]
    task169_result_ids: tuple[tuple[str, str], ...]
    head_sha: str
    head_tree: str
    software_version: str
    schema_version: str = PARITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "task168_request_hashes",
            "task168_result_hashes",
            "task169_result_hashes",
            "task169_result_ids",
        ):
            value = getattr(self, field_name)
            object.__setattr__(
                self,
                field_name,
                tuple(
                    sorted(
                        value,
                        key=lambda pair: (
                            pair[0].encode("utf-8", "strict"),
                            pair[1].encode("utf-8", "strict"),
                        ),
                    )
                ),
            )


@dataclass(frozen=True, slots=True)
class Task169RuntimeObservation:
    runtime_id: str
    actual_python_major_minor: str
    runtime_identity: str
    head_sha: str
    head_tree: str
    canonical_input_sha256: str
    task169_result_hashes: tuple[tuple[str, str], ...]
    task169_result_ids: tuple[tuple[str, str], ...]
    identity_projection_sha256: str
    runner_identity: str
    command_identity: str
    status: str


@dataclass(frozen=True, slots=True)
class Task169DualRuntimeObservation:
    python311: Task169RuntimeObservation
    python312: Task169RuntimeObservation
    status: str
    observation_hash: str
    evidence_refs: tuple[str, ...]


def _pairs_text(value: tuple[tuple[str, str], ...]) -> str:
    """Encode canonical pairs without process-dependent ``repr`` output."""

    return "\x1f".join(f"{name}\x1e{item}" for name, item in value)


def _input_values(value: Task169ParityInput) -> dict[str, str]:
    return {
        "schema_version": value.schema_version,
        "release_request_hash": value.release_request_hash,
        "task168_request_hashes": _pairs_text(value.task168_request_hashes),
        "task168_result_hashes": _pairs_text(value.task168_result_hashes),
        "task169_result_hashes": _pairs_text(value.task169_result_hashes),
        "task169_result_ids": _pairs_text(value.task169_result_ids),
        "head_sha": value.head_sha,
        "head_tree": value.head_tree,
        "software_version": value.software_version,
    }


def _encode_input(value: Task169ParityInput) -> bytes:
    values = _input_values(value)
    return frame_record(
        PARITY_SCHEMA_VERSION,
        tuple((name, KIND_STRING, values[name].encode("utf-8", "strict")) for name in _FIELD_NAMES),
    )


def _identity_projection(value: Task169ParityInput) -> bytes:
    values = _input_values(value)
    identity_names = (
        "schema_version",
        "release_request_hash",
        "task168_request_hashes",
        "task168_result_hashes",
        "task169_result_hashes",
        "task169_result_ids",
        "head_sha",
        "head_tree",
        "software_version",
    )
    return frame_record(
        "TASK169_IDENTITY_PROJECTION_V1",
        tuple(
            (name, KIND_STRING, values[name].encode("utf-8", "strict")) for name in identity_names
        ),
    )


def expected_digests(value: Task169ParityInput) -> tuple[str, str]:
    input_bytes = _encode_input(value)
    identity = hashlib.sha256(_identity_projection(value)).hexdigest()
    return hashlib.sha256(input_bytes).hexdigest(), identity


def _u32(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError("truncated u32")
    return struct.unpack_from(">I", data, offset)[0], offset + 4


def _u64(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 8 > len(data):
        raise ValueError("truncated u64")
    return struct.unpack_from(">Q", data, offset)[0], offset + 8


def _read(data: bytes, offset: int, length: int) -> tuple[bytes, int]:
    end = offset + length
    if end > len(data):
        raise ValueError("truncated record")
    return data[offset:end], end


def _parse_record(data: bytes) -> tuple[str, dict[str, tuple[bytes, bytes]]]:
    namespace_length, offset = _u32(data, 0)
    namespace_bytes, offset = _read(data, offset, namespace_length)
    namespace = namespace_bytes.decode("utf-8", "strict")
    field_count, offset = _u32(data, offset)
    fields: dict[str, tuple[bytes, bytes]] = {}
    for _ in range(field_count):
        name_length, offset = _u32(data, offset)
        name_bytes, offset = _read(data, offset, name_length)
        name = name_bytes.decode("utf-8", "strict")
        kind_length, offset = _u32(data, offset)
        kind, offset = _read(data, offset, kind_length)
        payload_length, offset = _u64(data, offset)
        payload, offset = _read(data, offset, payload_length)
        if name in fields:
            raise ValueError("duplicate parity field")
        fields[name] = (kind, payload)
    if offset != len(data):
        raise ValueError("trailing parity bytes")
    return namespace, fields


def _string_field(fields: dict[str, tuple[bytes, bytes]], name: str) -> str:
    kind, payload = fields[name]
    if kind != KIND_STRING:
        raise ValueError(f"parity field {name} is not a string")
    return payload.decode("utf-8", "strict")


def _repository_root() -> Path | None:
    configured = os.environ.get("TASK169_REPOSITORY_ROOT")
    if configured:
        path = Path(configured).resolve()
        if (path / ".git").exists() and (path / "pyproject.toml").is_file():
            return path
    for path in (Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parent):
        if (path / ".git").exists() and (path / "pyproject.toml").is_file():
            return path
    return None


def repository_identity() -> tuple[str, str] | None:
    root = _repository_root()
    git = shutil.which("git")
    if root is None or git is None:
        return None
    try:
        head = subprocess.run(
            [git, "rev-parse", "HEAD"], cwd=root, capture_output=True, check=False
        )
        tree = subprocess.run(
            [git, "rev-parse", "HEAD^{tree}"], cwd=root, capture_output=True, check=False
        )
        if head.returncode or tree.returncode or head.stderr or tree.stderr:
            return None
        return (
            head.stdout.decode("ascii", "strict").strip(),
            tree.stdout.decode("ascii", "strict").strip(),
        )
    except (OSError, UnicodeError):
        return None


def _child_payload(data: bytes, expected_runtime: str) -> bytes:
    namespace, fields = _parse_record(data)
    if namespace != PARITY_SCHEMA_VERSION or tuple(fields) != _FIELD_NAMES:
        raise ValueError("unexpected TASK-169 parity input")
    values = {name: _string_field(fields, name) for name in _FIELD_NAMES}
    actual = f"{sys.version_info.major}.{sys.version_info.minor}"
    if actual != expected_runtime:
        raise ValueError("child interpreter version does not match assignment")
    root = _repository_root()
    git = shutil.which("git")
    if root is None or git is None:
        raise ValueError("child cannot establish repository root")
    head = subprocess.run([git, "rev-parse", "HEAD"], cwd=root, capture_output=True, check=False)
    tree = subprocess.run(
        [git, "rev-parse", "HEAD^{tree}"], cwd=root, capture_output=True, check=False
    )
    observed_head = head.stdout.decode("ascii", "strict").strip()
    observed_tree = tree.stdout.decode("ascii", "strict").strip()
    if (
        head.returncode
        or tree.returncode
        or head.stderr
        or tree.stderr
        or observed_head != values["head_sha"]
        or observed_tree != values["head_tree"]
    ):
        raise ValueError("child observed a different checkout")
    input_sha = hashlib.sha256(data).hexdigest()
    identity_values = {name: values[name] for name in _FIELD_NAMES}
    identity = hashlib.sha256(
        frame_record(
            "TASK169_IDENTITY_PROJECTION_V1",
            tuple(
                (name, KIND_STRING, identity_values[name].encode("utf-8", "strict"))
                for name in (
                    "schema_version",
                    "release_request_hash",
                    "task168_request_hashes",
                    "task168_result_hashes",
                    "task169_result_hashes",
                    "task169_result_ids",
                    "head_sha",
                    "head_tree",
                    "software_version",
                )
            ),
        )
    ).hexdigest()
    return frame_record(
        "TASK169_PARITY_CHILD_OUTPUT_V1",
        (
            ("actual_python_major_minor", KIND_STRING, actual.encode("ascii")),
            (
                "runtime_identity",
                KIND_STRING,
                f"{sys.implementation.name}:{actual}:{Path(sys.executable).resolve()}".encode(
                    "utf-8", "strict"
                ),
            ),
            ("verified_head_sha", KIND_STRING, observed_head.encode("ascii")),
            ("verified_head_tree", KIND_STRING, observed_tree.encode("ascii")),
            ("canonical_input_sha256", KIND_STRING, input_sha.encode("ascii")),
            (
                "task169_result_hashes",
                KIND_STRING,
                values["task169_result_hashes"].encode("utf-8"),
            ),
            (
                "task169_result_ids",
                KIND_STRING,
                values["task169_result_ids"].encode("utf-8"),
            ),
            ("identity_projection_sha256", KIND_STRING, identity.encode("ascii")),
            ("runner_identity", KIND_STRING, RUNNER_IDENTITY.encode("ascii")),
            ("command_identity", KIND_STRING, COMMAND_IDENTITY.encode("ascii")),
        ),
    )


def _blocked_observation(runtime_id: str) -> Task169RuntimeObservation:
    return Task169RuntimeObservation(
        runtime_id=runtime_id,
        actual_python_major_minor="",
        runtime_identity="",
        head_sha="",
        head_tree="",
        canonical_input_sha256="",
        task169_result_hashes=(),
        task169_result_ids=(),
        identity_projection_sha256="",
        runner_identity=RUNNER_IDENTITY,
        command_identity=COMMAND_IDENTITY,
        status="BLOCKED",
    )


def _run_runtime(
    executable: str,
    runtime_id: str,
    expected_runtime: str,
    input_bytes: bytes,
    input_value: Task169ParityInput,
) -> Task169RuntimeObservation:
    if not executable:
        return _blocked_observation(runtime_id)
    environment = dict(CHILD_ENVIRONMENT)
    environment["PATH"] = os.environ.get("PATH", "")
    root = _repository_root()
    if root is not None:
        environment["TASK169_REPOSITORY_ROOT"] = str(root)
    try:
        completed = subprocess.run(
            [executable, "-I", "-m", CHILD_MODULE, "--child", runtime_id],
            input=input_bytes,
            capture_output=True,
            env=environment,
            timeout=60,
            check=False,
        )
        if completed.returncode or completed.stderr:
            return _blocked_observation(runtime_id)
        namespace, fields = _parse_record(completed.stdout)
        if namespace != "TASK169_PARITY_CHILD_OUTPUT_V1" or tuple(fields) != _CHILD_OUTPUT_FIELDS:
            return _blocked_observation(runtime_id)
        actual = _string_field(fields, "actual_python_major_minor")
        observed_head = _string_field(fields, "verified_head_sha")
        observed_tree = _string_field(fields, "verified_head_tree")
        input_sha = _string_field(fields, "canonical_input_sha256")
        result_hashes = _string_field(fields, "task169_result_hashes")
        result_ids = _string_field(fields, "task169_result_ids")
        identity = _string_field(fields, "identity_projection_sha256")
        runner = _string_field(fields, "runner_identity")
        command = _string_field(fields, "command_identity")
        expected_input_sha, expected_identity = expected_digests(input_value)
        expected_runtime_identity = f"cpython:{expected_runtime}:{Path(executable).resolve()}"
        if (
            actual != expected_runtime
            or _string_field(fields, "runtime_identity") != expected_runtime_identity
            or observed_head != input_value.head_sha
            or observed_tree != input_value.head_tree
            or input_sha != expected_input_sha
            or identity != expected_identity
            or result_hashes != _pairs_text(input_value.task169_result_hashes)
            or result_ids != _pairs_text(input_value.task169_result_ids)
            or runner != RUNNER_IDENTITY
            or command != COMMAND_IDENTITY
        ):
            return _blocked_observation(runtime_id)
        return Task169RuntimeObservation(
            runtime_id=runtime_id,
            actual_python_major_minor=actual,
            runtime_identity=_string_field(fields, "runtime_identity"),
            head_sha=observed_head,
            head_tree=observed_tree,
            canonical_input_sha256=input_sha,
            task169_result_hashes=input_value.task169_result_hashes,
            task169_result_ids=input_value.task169_result_ids,
            identity_projection_sha256=identity,
            runner_identity=runner,
            command_identity=command,
            status="PASS",
        )
    except (OSError, UnicodeError, ValueError, struct.error, subprocess.SubprocessError):
        return _blocked_observation(runtime_id)
    except BaseException:
        return _blocked_observation(runtime_id)


def _observation_hash(value: Task169DualRuntimeObservation) -> str:
    def observation_text(item: Task169RuntimeObservation) -> str:
        fields = (
            item.runtime_id,
            item.actual_python_major_minor,
            item.runtime_identity,
            item.head_sha,
            item.head_tree,
            item.canonical_input_sha256,
            _pairs_text(item.task169_result_hashes),
            _pairs_text(item.task169_result_ids),
            item.identity_projection_sha256,
            item.runner_identity,
            item.command_identity,
            item.status,
        )
        return "\x1f".join(fields)

    fields = (
        ("python311", observation_text(value.python311)),
        ("python312", observation_text(value.python312)),
        ("status", value.status),
        ("evidence_refs", "\x1f".join(value.evidence_refs)),
    )
    return hashlib.sha256(
        frame_record(
            "TASK169_DUAL_RUNTIME_OBSERVATION_V1",
            tuple((name, KIND_STRING, item.encode("utf-8", "strict")) for name, item in fields),
        )
    ).hexdigest()


def observe_dual_runtime(
    *,
    input_value: Task169ParityInput,
    py311: str | None = None,
    py312: str | None = None,
) -> Task169DualRuntimeObservation:
    """Capture both actual runtimes; caller-supplied parity evidence is ignored."""

    first_path = (
        py311
        or os.environ.get("TASK169_PY311_EXECUTABLE")
        or os.environ.get("TASK164_PY311_EXECUTABLE", "")
    )
    second_path = (
        py312
        or os.environ.get("TASK169_PY312_EXECUTABLE")
        or os.environ.get("TASK164_PY312_EXECUTABLE", "")
    )
    first_id = "PYTHON_3_11"
    second_id = "PYTHON_3_12"
    if first_path and second_path and os.path.abspath(first_path) == os.path.abspath(second_path):
        first = _blocked_observation(first_id)
        second = _blocked_observation(second_id)
    else:
        input_bytes = _encode_input(input_value)
        first = _run_runtime(first_path, first_id, "3.11", input_bytes, input_value)
        second = _run_runtime(second_path, second_id, "3.12", input_bytes, input_value)
    status = (
        "PASS"
        if first.status == "PASS"
        and second.status == "PASS"
        and first.task169_result_hashes == second.task169_result_hashes
        and first.task169_result_ids == second.task169_result_ids
        and first.canonical_input_sha256 == second.canonical_input_sha256
        and first.identity_projection_sha256 == second.identity_projection_sha256
        else "BLOCKED"
    )
    preliminary = Task169DualRuntimeObservation(
        python311=first,
        python312=second,
        status=status,
        observation_hash="",
        evidence_refs=("TASK169_DUAL_RUNTIME_INTERNAL_OBSERVATION",),
    )
    return Task169DualRuntimeObservation(
        python311=first,
        python312=second,
        status=status,
        observation_hash=_observation_hash(preliminary),
        evidence_refs=preliminary.evidence_refs,
    )


def child_main() -> int:
    if (
        len(sys.argv) != 3
        or sys.argv[1] != "--child"
        or sys.argv[2]
        not in {
            "PYTHON_3_11",
            "PYTHON_3_12",
        }
    ):
        return 2
    expected_runtime = "3.11" if sys.argv[2] == "PYTHON_3_11" else "3.12"
    try:
        payload = sys.stdin.buffer.read(16 * 1024 * 1024)
        output = _child_payload(payload, expected_runtime)
        sys.stdout.buffer.write(output)
        return 0
    except BaseException:
        return 3


if __name__ == "__main__":
    raise SystemExit(child_main())


__all__ = [
    "COMMAND_IDENTITY",
    "PARITY_SCHEMA_VERSION",
    "RUNNER_IDENTITY",
    "Task169DualRuntimeObservation",
    "Task169ParityInput",
    "Task169RuntimeObservation",
    "expected_digests",
    "observe_dual_runtime",
    "repository_identity",
]
