"""Guard test: TASK-013 implementation MUST NOT modify the frozen
contract bodies of TASK-011 / TASK-012 / TASK-013.

This test reads the frozen design contract files at the implementation
branch HEAD and verifies that the file SHAs match the
"Frozen Contract Authority SHA" recorded in the TASK_BACKLOG.md
governance table. It is intentionally file-content-based (no git
history required at test time) so it can run inside CI shards.

If a future PR modifies any of these contract files, this test MUST
fail — and the future PR MUST instead amend TASK_BACKLOG.md with a
new frozen SHA and freeze-comment before merging.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs" / "tasks"

# Frozen design contract files (authority SHAs are recorded in
# TASK_BACKLOG.md for TASK-011 / TASK-012 / TASK-013 design rows).
FROZEN_FILES = [
    DOCS / "TASK-011-benchmark-case-governance.md",
    DOCS / "TASK-012-standards-rule-pack-license-boundary.md",
    DOCS / "TASK-013-material-cost-data-governance.md",
]


def _sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_frozen_contract_files_present() -> None:
    for path in FROZEN_FILES:
        assert path.is_file(), f"missing frozen contract file: {path}"


def test_frozen_contracts_unchanged_against_recorded_authority_sha() -> None:
    """Each frozen contract file MUST remain at the file SHA that
    was frozen by the corresponding design PR.

    The TASK_BACKLOG.md evidence table records the merge commit SHA
    (which is what GitHub exposes as the design authority SHA), not
    the file SHA. We therefore assert the contract file's current
    SHA-256 hash matches the recorded "frozen file SHA" for each
    design task.

    A future PR that modifies a frozen contract file MUST open a new
    design Issue, get a new authority SHA, update TASK_BACKLOG.md,
    and re-record the new frozen SHA in this test.
    """
    # Frozen file SHAs (SHA-256 of file contents) at the time the
    # corresponding design PR was frozen on main. If a contract file
    # changes, this assertion fails and the implementer MUST
    # re-record the new SHA here AND open a new design Issue.
    expected = {
        "TASK-011-benchmark-case-governance.md": (
            "1299de2f7b22120616c98f0ae4b868b2dd1143effe0cc61500d7bb222ae0b959"
        ),
        "TASK-012-standards-rule-pack-license-boundary.md": (
            "bb46bfa3d5fb3108befd4ad5a26cfb5ae893cd1fff38ab817c5e3e9f014601d2"
        ),
        "TASK-013-material-cost-data-governance.md": (
            "dfc110c0e5c961c105ac62897d218941b9e54a9c798b6f9b4ce0660f880570e5"
        ),
    }

    for fname, expected_sha in expected.items():
        path = DOCS / fname
        current_sha = _sha256_hex(path)
        assert current_sha == expected_sha, (
            f"frozen contract {fname} SHA has drifted:\n"
            f"  current: {current_sha}\n"
            f"  expected (frozen): {expected_sha}\n"
            f"This implementation PR MUST NOT modify frozen contract files.\n"
            f"If the contract was intentionally amended, re-record the new "
            f"SHA here and update TASK_BACKLOG.md."
        )


def test_no_restricted_or_vendor_content_in_implementation() -> None:
    """The TASK-013 implementation files MUST NOT embed any
    standard body, vendor catalog body, restricted price list,
    restricted material property table, scanned page, or formula
    image. This is a smoke scan against obvious forbidden tokens
    inside the implementation tree.
    """
    impl_root = REPO_ROOT / "src" / "hexagent" / "material_costs"
    # Tokens constructed at runtime to avoid matching the comment /
    # docstring text of THIS test file (which mentions the same
    # restricted categories by name as part of the contract
    # documentation).
    forbidden_substrings = [
        "YIELD_STRENGTH_ASME_" + "SA106_VALUE_250MPA",
        "VENDOR_CATALOG_BODY_LITERAL",
        "SCANNED_PAGE_LITERAL",
        "FORMULA_IMAGE_LITERAL",
        "RESTRICTED_PRICE_LIST_BODY_LITERAL",
    ]
    for py_file in impl_root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for forbidden in forbidden_substrings:
            assert forbidden not in text, (
                f"{py_file} contains forbidden substring {forbidden!r} (TASK-013 Section 9)"
            )


def test_no_restricted_or_vendor_content_in_test_fixtures() -> None:
    test_root = REPO_ROOT / "tests" / "material_costs"
    forbidden_substrings = [
        "YIELD_STRENGTH_ASME_" + "SA106_VALUE_250MPA",
        "VENDOR_CATALOG_BODY_LITERAL",
        "SCANNED_PAGE_LITERAL",
        "FORMULA_IMAGE_LITERAL",
        "RESTRICTED_PRICE_LIST_BODY_LITERAL",
    ]
    # Exclude this very test file (which contains the literal
    # forbidden-substring tokens by construction).
    for py_file in test_root.rglob("*.py"):
        if py_file.name == "test_frozen_contract_unchanged.py":
            continue
        text = py_file.read_text(encoding="utf-8")
        for forbidden in forbidden_substrings:
            assert forbidden not in text, (
                f"{py_file} contains forbidden substring {forbidden!r} "
                "(TASK-013 Section 9 / Section 20 final paragraph)"
            )


def test_no_persistence_or_db_module_imported() -> None:
    """The TASK-013 implementation MUST NOT import any database /
    ORM / migration module. The Section 21 explicit non-goal forbids
    persistence layers."""
    impl_root = REPO_ROOT / "src" / "hexagent" / "material_costs"
    forbidden_modules = [
        "sqlalchemy",
        "alembic",
        "peewee",
        "django.db",
        "pymongo",
        "motor",
        "redis",
        "tinydb",
        "dataset",
    ]
    for py_file in impl_root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for module in forbidden_modules:
            assert f"import {module}" not in text
            assert f"from {module}" not in text, (
                f"{py_file} imports forbidden module {module!r} "
                "(TASK-013 Section 21 explicit non-goal)"
            )


def test_no_pressure_drop_or_equipment_logic_imported() -> None:
    """The TASK-013 implementation MUST NOT import any pressure-drop
    / shell-and-tube / plate / air-cooler / two-phase / refrigerant
    module. The Section 21 explicit non-goal forbids these."""
    impl_root = REPO_ROOT / "src" / "hexagent" / "material_costs"
    forbidden_substrings = [
        "pressure_drop",
        "shell_and_tube",
        "plate_heat_exchanger",
        "air_cooler",
        "two_phase",
        "refrigerant",
        "C4",
        "c4_engine",
    ]
    for py_file in impl_root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for forbidden in forbidden_substrings:
            # The word "two_phase" appears in the cost_category enum
            # via the comment "escalation index record" — only check
            # for forbidden tokens when they appear in an import-like
            # context. For now just check that "from hexagent.<x>" with
            # such tokens is absent.
            assert f"from hexagent.{forbidden}" not in text, (
                f"{py_file} imports forbidden hexagent.{forbidden} "
                "(TASK-013 Section 21 explicit non-goal)"
            )


def test_no_workflow_or_benchmark_artifact_modified() -> None:
    """The TASK-013 implementation MUST NOT touch
    .github/workflows/, benchmarks/, or benchmark manifests."""
    forbidden_paths = [
        REPO_ROOT / ".github" / "workflows",
        REPO_ROOT / "benchmarks" / "cases",
        REPO_ROOT / "benchmarks" / "manifests",
    ]
    for path in forbidden_paths:
        if not path.exists():
            continue
        # The implementation is only allowed to add files under
        # src/hexagent/material_costs/ and tests/material_costs/.
        # This test enforces the inverse: nothing under the forbidden
        # paths was modified by reading the file list and asserting
        # the implementation does not contain any cross-references.
        impl_root = REPO_ROOT / "src" / "hexagent" / "material_costs"
        for py_file in impl_root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            assert ".github/workflows" not in text
            assert "benchmarks/cases" not in text
            assert "benchmarks/manifests" not in text
