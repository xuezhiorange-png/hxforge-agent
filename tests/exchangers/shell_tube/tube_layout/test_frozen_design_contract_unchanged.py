from __future__ import annotations

import hashlib
from pathlib import Path

DESIGN_PATH = Path("docs/tasks/TASK-021-shell-and-tube-tube-layout-and-count.md")
EXPECTED_GIT_BLOB_SHA1 = "f310ebe1966f948849ed95cee809d70b2b0b04fd"


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def test_frozen_design_contract_present_and_unchanged() -> None:
    data = DESIGN_PATH.read_bytes()
    assert _git_blob_sha1(data) == EXPECTED_GIT_BLOB_SHA1
    text = data.decode("utf-8")
    assert "## 16. Implementation slicing" in text
    assert "TASK022_THROUGH_TASK039_UNALLOCATED" in text
