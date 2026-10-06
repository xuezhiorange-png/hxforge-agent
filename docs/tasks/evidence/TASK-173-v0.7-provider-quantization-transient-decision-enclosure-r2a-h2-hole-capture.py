"""Capture the frozen H2 numerical-hole identities under the R2A runtime."""

from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from hexagent.canonical_json import canonical_sha256

HERE = Path(__file__).resolve().parent
LEGACY_CAPTURE = HERE / (
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-h2-hole-capture.py"
)
R2A_QUALIFICATION = HERE / (
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-qualification.py"
)
R2A_EVIDENCE = HERE / "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a.json"
R2A_OUTPUT = (
    HERE / "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-h2-hole.json"
)
RUNTIME_HEAD = "5bd19b1829f2fea7757c3efb3398e9aab17c8a3d"
RUNTIME_TREE = "64fc2c4b5e1776610aa8a5e39bf0666455648f73"


def _load_r2a_qualification() -> Any:
    module = runpy.run_path(str(R2A_QUALIFICATION), run_name="task173_r2a_h2_capture_library")
    original_builder = module["_build_candidate"]

    def build_candidate(label: str) -> Any:
        result = original_builder(label)
        module["_R2"]["_ACTIVE_RATING_REQUEST"][label] = result[4]
        return result

    module["_build_candidate"] = build_candidate
    namespace = SimpleNamespace()
    namespace.__dict__.update(module)
    return namespace


def main() -> None:
    capture = runpy.run_path(str(LEGACY_CAPTURE), run_name="task173_r2_h2_capture_library")
    overrides = {
        "RUNTIME_HEAD": RUNTIME_HEAD,
        "RUNTIME_TREE": RUNTIME_TREE,
        "QUALIFICATION_PATH": R2A_EVIDENCE,
        "QUALIFICATION_RUNNER_PATH": R2A_QUALIFICATION,
        "OUTPUT_PATH": R2A_OUTPUT,
        "_load_qualification_runner": _load_r2a_qualification,
    }
    capture.update(overrides)
    capture["_main"].__globals__.update(overrides)
    capture["_main"]()
    hole_document = json.loads(R2A_OUTPUT.read_text(encoding="utf-8"))
    hole_projection = {key: value for key, value in hole_document.items() if key != "evidence_hash"}
    # The H2 artifact binds the qualification matrix, not the mutable whole-file
    # digest, so the authority can bind the H2 artifact without a hash cycle.
    hole_projection.pop("parent_qualification_sha256", None)
    hole_document = dict(hole_projection)
    hole_document["evidence_hash"] = canonical_sha256(hole_projection)
    R2A_OUTPUT.write_text(json.dumps(hole_document, ensure_ascii=False, indent=2) + "\n")

    parent = json.loads(R2A_EVIDENCE.read_text(encoding="utf-8"))
    rebound_runner = _load_r2a_qualification()
    rebound_runner._check_committed_runtime()
    projection = rebound_runner.build_authority_projection()
    artifacts = projection["qualification_artifacts"]
    artifacts["h2_hole_evidence_path"] = str(R2A_OUTPUT.relative_to(Path.cwd()))
    artifacts["h2_hole_evidence_sha256"] = hashlib.sha256(R2A_OUTPUT.read_bytes()).hexdigest()
    artifacts["h2_hole_evidence_hash"] = hole_document["evidence_hash"]
    authority_hash = canonical_sha256(projection)
    parent["authority_candidate"]["projection"] = projection
    parent["authority_candidate"]["canonical_hash"] = authority_hash
    replay = parent["replay_verification"]
    replay["authority_hash"] = authority_hash
    replay["replay_verification_hash"] = canonical_sha256(
        {key: value for key, value in replay.items() if key != "replay_verification_hash"}
    )
    R2A_EVIDENCE.write_text(json.dumps(parent, ensure_ascii=False, indent=2) + "\n")
    print(f"R2A_FINAL_AUTHORITY_HASH={authority_hash}")
    print(f"R2A_H2_HOLE_EVIDENCE_HASH={hole_document['evidence_hash']}")


if __name__ == "__main__":
    main()
