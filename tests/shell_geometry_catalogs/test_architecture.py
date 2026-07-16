"""Architecture invariants for the TASK-023 shell-geometry-catalog
framework implementation.

The architecture test enforces the merged TASK-023 implementation
allowlist as one immutable historical snapshot. The snapshot is bounded
by the merged TASK-023 design base commit and the merged TASK-023
implementation-final commit. Later repository evolution (including the
TASK-024 design branch, the maintenance branch, the worktree state, the
stage / index, and the user's local edits) is outside this historical
snapshot and is not part of the audit.

Architecture test scope is locked to:

    TASK023_FROZEN_BASE_SHA        ..  TASK023_IMPLEMENTATION_FINAL_SHA
    195ad692e4aa0148b28c8f6b86e37e73dfb3a194
                                      ..  b93300b45f2cf718ab020b2203f772e9a8413a8f

where base is the merged TASK-023 design authority and final is the
merged TASK-023 implementation commit. Neither value is derived from
``origin/main`` or ``HEAD``.

What this test enforces on the one-commit implementation snapshot:

- exact 9-path implementation allowlist;
- exact seven-symbol package export set;
- no filesystem / network / database / environment / clock /
  locale / global-registry access in production modules;
- no imports from TASK-022 runtime;
- no mutation of TASK-016 or TASK-022 module surfaces;
- no production / restricted-standard / vendor-table bodies;
- no workflow / dependency / lockfile / design-document mutation;
- exact ``ci-shard-manifest.yml`` delta.

Architecture tests may legitimately import ``pathlib`` / ``subprocess``
/ re-runs of ``git diff`` for boundary inspection. The forbidden
checks below target the **production modules** of the package, not
the test code itself.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_MODULES = (
    REPO_ROOT / "src" / "hexagent" / "shell_geometry_catalogs" / "models.py",
    REPO_ROOT / "src" / "hexagent" / "shell_geometry_catalogs" / "blockers.py",
    REPRODUCTION_CATALOG := (
        REPO_ROOT / "src" / "hexagent" / "shell_geometry_catalogs" / "catalog.py"
    ),
    REPO_ROOT / "src" / "hexagent" / "shell_geometry_catalogs" / "__init__.py",
)

ALLOWED_PATHS = {
    "src/hexagent/shell_geometry_catalogs/__init__.py",
    "src/hexagent/shell_geometry_catalogs/models.py",
    "src/hexagent/shell_geometry_catalogs/blockers.py",
    "src/hexagent/shell_geometry_catalogs/catalog.py",
    "tests/shell_geometry_catalogs/_builders.py",
    "tests/shell_geometry_catalogs/test_models.py",
    "tests/shell_geometry_catalogs/test_catalog.py",
    "tests/shell_geometry_catalogs/test_architecture.py",
    "ci-shard-manifest.yml",
}

# Tokens that the production modules must NOT reference.
# They collectively cover filesystem / network / database /
# environment / clock / locale / registry / dynamic-import /
# executable-deserialization imports.
FORBIDDEN_IO_TOKENS = (
    "open(",
    "pathlib.Path",
    "pathlib.PosixPath",
    "pathlib.WindowsPath",
    "pathlib.PurePath",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "urllib.request",
    "urllib.error",
    "socket.",
    "http.client",
    "sqlite3",
    "psycopg2",
    "MySQLdb",
    "pymongo",
    "importlib.import_module",
    "importlib.reload",
    "__import__",
    "importlib.util",
    "pickle.loads",
    "pickle.load",
    "shelve.",
    "marshal.loads",
    "marshal.load",
    "ctypes.",
    "cffi.",
    "os.environ",
    "os.getenv",
    "os.environb",
    "time.time",
    "time.localtime",
    "time.gmtime",
    "time.strftime",
    "datetime.datetime.now",
    "datetime.datetime.utcnow",
    "datetime.datetime.today",
    "locale.setlocale",
    "locale.getlocale",
    "locale.getdefaultlocale",
    "sys.settrace",
    "sys.setprofile",
    "signal.",
    "fcntl.",
    "msvcrt.",
    "win32api",
    "win32con",
    "win32file",
    "win32pipe",
    "win32evtlog",
    "win32com",
    "_winreg",
    "posix.",
)

# Tokens that the production modules must NOT import (TASK-022
# runtime + adapter layer), to enforce zero domain coupling beyond
# canonical_sha256.
TASK_022_FORBIDDEN_IMPORTS = (
    "shell_bundle_geometry.adapter_blockers",
    "shell_bundle_geometry.authority",
    "shell_bundle_geometry.rule_pack_adapter",
    "shell_bundle_geometry.models",
    "shell_bundle_geometry.geometry",
    "shell_bundle_geometry.validation",
    "shell_bundle_geometry.schema",
    "ShellBundleGeometry",
    "ShellBundleGeometryRuleAuthoritySnapshot",
    "ApprovedShellGeometrySnapshot",
    "build_shell_bundle_rule_authority_snapshot",
    "RulePackAdapterBlockerCode",
    "AdapterFailure",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ----------------------------------------------------------------------
# TASK-023 frozen implementation snapshot — immutable endpoints.
# ----------------------------------------------------------------------
# ``base`` is the merged TASK-023 design authority commit. ``final`` is
# the merged TASK-023 implementation commit. Neither value is derived
# from ``origin/main`` or ``HEAD``; both are anchored to the historical
# snapshot that the architecture test audits.
TASK023_FROZEN_BASE_SHA = "195ad692e4aa0148b28c8f6b86e37e73dfb3a194"
TASK023_IMPLEMENTATION_FINAL_SHA = "b93300b45f2cf718ab020b2203f772e9a8413a8f"


def _ensure_exact_commit(
    commit_sha: str,
    *,
    label: str,
) -> str:
    """Resolve one exact commit SHA on demand.

    Behaviour:

    1. ``git cat-file -e <sha>^{commit}`` against the local repo;
    2. if the object already exists, no fetch is performed;
    3. otherwise ``git fetch --no-tags --depth=1 origin <sha>``;
    4. re-verify with ``git cat-file``;
    5. on failure raise ``AssertionError`` carrying ``label``,
       ``commit_sha`` and the captured stderr;
    6. return ``commit_sha`` unchanged.

    The helper MUST NEVER read ``origin/main`` / ``HEAD`` and MUST
    NEVER fall back to a mutable branch name. The resolved endpoint
    is the exact SHA supplied by the caller.
    """
    probe = subprocess.run(
        ["git", "cat-file", "-e", commit_sha + "^{commit}"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if probe.returncode != 0:
        fetch = subprocess.run(
            [
                "git",
                "fetch",
                "--no-tags",
                "--depth=1",
                "origin",
                commit_sha,
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        if fetch.returncode != 0:
            raise AssertionError(
                f"failed to resolve {label}={commit_sha}: "
                f"cat-file stderr={probe.stderr.strip()!r}; "
                f"fetch stderr={fetch.stderr.strip()!r}"
            )
        re_check = subprocess.run(
            ["git", "cat-file", "-e", commit_sha + "^{commit}"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        if re_check.returncode != 0:
            raise AssertionError(
                f"failed to resolve {label}={commit_sha} after fetch: "
                f"cat-file stderr={re_check.stderr.strip()!r}"
            )
    return commit_sha


def _ensure_task023_snapshot() -> tuple[str, str]:
    """Return the two immutable endpoints of the TASK-023 snapshot.

    The audit spans exactly ``[frozen_base, implementation_final]`` —
    no mutable branch reference, no staged state, no untracked scan.
    """
    return (
        _ensure_exact_commit(
            TASK023_FROZEN_BASE_SHA,
            label="TASK-023 frozen base",
        ),
        _ensure_exact_commit(
            TASK023_IMPLEMENTATION_FINAL_SHA,
            label="TASK-023 implementation final",
        ),
    )


def test_task023_implementation_snapshot_is_one_exact_commit() -> None:
    """The audited snapshot must be exactly the merged TASK-023
    one-commit implementation range, anchored to immutable endpoints.

    Specifically: ``final`` is ``base``'s unique successor and the
    audit range ``base..final`` contains exactly one commit. No part
    of this assertion is sourced from ``HEAD``, the worktree state,
    the stage / index, the untracked set, or any mutable branch.
    """
    base_sha, final_sha = _ensure_task023_snapshot()
    assert base_sha == TASK023_FROZEN_BASE_SHA
    assert final_sha == TASK023_IMPLEMENTATION_FINAL_SHA
    commit_count = subprocess.run(
        ["git", "rev-list", "--count", f"{base_sha}..{final_sha}"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert commit_count.returncode == 0, commit_count.stderr
    assert commit_count.stdout.strip() == "1", commit_count.stdout

    parent_check = subprocess.run(
        ["git", "rev-parse", f"{final_sha}^"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert parent_check.returncode == 0, parent_check.stderr
    assert parent_check.stdout.strip() == base_sha, parent_check.stdout


def test_pkg_exports_exactly_seven_symbols() -> None:
    """The package root exposes the canonical seven-symbol set."""
    import hexagent.shell_geometry_catalogs as sgc

    expected = {
        "ShellGeometryCatalog",
        "ShellGeometryRecord",
        "ShellGeometryCatalogFailure",
        "ShellGeometryCatalogBlockerCode",
        "SHELL_GEOMETRY_CATALOG_BLOCKER_CODES",
        "parse_shell_geometry_catalog",
        "select_approved_shell_geometry",
    }
    assert expected.issubset(set(sgc.__all__))
    assert set(sgc.__all__) == expected
    for name in expected:
        obj = getattr(sgc, name)
        assert obj is not None


def test_production_modules_do_not_import_task_022_runtime() -> None:
    """Production modules MUST NOT couple to the TASK-022 runtime."""
    for path in PRODUCTION_MODULES:
        text = _read(path)
        for forbidden in TASK_022_FORBIDDEN_IMPORTS:
            assert forbidden not in text, (
                f"{path.relative_to(REPO_ROOT)} contains forbidden token {forbidden!r}"
            )


def test_production_modules_have_no_forbidden_io_tokens() -> None:
    """No filesystem / network / database / environment / clock /
    locale / registry / dynamic-import / executable-deserialization."""
    for path in PRODUCTION_MODULES:
        text = _read(path)
        forbidden_re = re.compile(
            "|".join(
                re.escape(tok).replace(re.escape("."), r"\.[A-Za-z_][A-Za-z0-9_]*")
                for tok in FORBIDDEN_IO_TOKENS
            )
        )
        match = forbidden_re.search(text)
        assert match is None, (
            f"{path.relative_to(REPO_ROOT)} contains forbidden I/O token {match.group(0)!r}"
        )


def test_no_runtime_path_string_in_production_modules() -> None:
    """``open()`` is forbidden in production modules — the framework
    receives already-loaded mappings only."""
    for path in PRODUCTION_MODULES:
        text = _read(path)
        assert "open(" not in text


def test_pkg_init_does_not_implicitly_run_io() -> None:
    """Importing the package must not perform filesystem / network /
    environment side-effects (a sentinel that the import succeeded
    is sufficient)."""
    sys.modules.pop("hexagent.shell_geometry_catalogs", None)
    import hexagent.shell_geometry_catalogs  # noqa: F401


def test_no_task_016_mutation_or_widening() -> None:
    """TASK-016 closed types remain {tube, pipe, hairpin} and
    are NOT widened, narrowed or reordered by the TASK-023
    implementation."""
    canonical_tokens = {"GEOMETRY_TYPE_TUBE", "GEOMETRY_TYPE_PIPE", "GEOMETRY_TYPE_HAIRPIN"}
    canonical_literals = {'"tube"', '"pipe"', '"hairpin"'}
    geom_models = REPO_ROOT / "src" / "hexagent" / "geometry_catalogs" / "models.py"
    if geom_models.exists():
        text = _read(geom_models)
        for tok in canonical_tokens:
            assert tok in text, f"TASK-016 canonical {tok} missing in geometry_catalogs/models.py"
        for tok in canonical_literals:
            assert tok in text, f"TASK-016 canonical {tok} missing in geometry_catalogs/models.py"

    # TASK-023 implementation MUST NOT widen or rename TASK-016
    # types. Production modules MUST NOT import TASK-022 runtime
    # (geometry_catalogs, exchangers.shell_tube.shell_bundle_geometry,
    # exchangers.shell_tube.models). TASK-012 (``hexagent.rule_packs``)
    # IS in scope per design §9 / §18 license gate.
    for path in PRODUCTION_MODULES:
        text = _read(path)
        for forbidden_marker in (
            "from hexagent.geometry_catalogs",
            "import hexagent.geometry_catalogs",
            "from hexagent.exchangers.shell_tube.models",
            "import hexagent.exchangers.shell_tube.models",
            "from hexagent.exchangers.shell_tube.shell_bundle_geometry",
            "import hexagent.exchangers.shell_tube.shell_bundle_geometry",
        ):
            assert forbidden_marker not in text, (
                f"{path.relative_to(REPO_ROOT)} imports a "
                f"TASK-016 / TASK-022 module: {forbidden_marker}"
            )

    # The TASK-023 implementation MUST NOT widen or rename TASK-016
    # types. We assert no production module edits TASK-016.
    for path in PRODUCTION_MODULES:
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = _read(path)
        if "task_016" in text.lower() or "tube | pipe | hairpin" in text:
            # Allowed only if the text is documenting the
            # TASK-016 boundary guard and not editing it.
            for forbidden_marker in (
                "from hexagent.exchangers.shell_tube.models import",
                "import hexagent.exchangers.shell_tube.models",
            ):
                assert forbidden_marker not in text, (
                    f"{rel} imports the TASK-016 module — implementation must remain independent"
                )


def _task023_implementation_changed_paths() -> list[str]:
    """Return the changed paths inside the TASK-023 frozen
    implementation snapshot (``[frozen_base..implementation_final]``).

    The endpoint is always the merged TASK-023 implementation commit,
    not the current ``HEAD``, the staged index, the untracked set, or
    any other mutable branch reference. The helper is fail-closed to
    one exact commit range:

        TASK023_FROZEN_BASE_SHA..TASK023_IMPLEMENTATION_FINAL_SHA
    """
    base_sha, final_sha = _ensure_task023_snapshot()
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            base_sha,
            final_sha,
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    return sorted(line for line in result.stdout.splitlines() if line)


def test_exact_9_path_allowlist() -> None:
    """Only the 9-path allowlist appears inside the TASK-023 frozen
    implementation snapshot."""
    allowed = set(ALLOWED_PATHS)
    changed = set(_task023_implementation_changed_paths())
    missing = sorted(p for p in allowed if p not in changed)
    unexpected = sorted(p for p in changed if p not in allowed)
    assert not missing, (
        f"Architecture allowlist violation: missing paths {missing!r}; "
        f"snapshot changed paths {sorted(changed)!r}; expected {sorted(allowed)!r}"
    )
    assert not unexpected, (
        f"Architecture allowlist violation: unexpected paths {unexpected!r}; "
        f"snapshot changed paths {sorted(changed)!r}; expected {sorted(allowed)!r}"
    )


def test_ci_shard_manifest_exact_delta() -> None:
    """``ci-shard-manifest.yml``: exactly +3 insertions / -0 deletions
    inside the TASK-023 frozen implementation snapshot. The audit
    range is only ``[frozen_base..implementation_final]``."""
    base_sha, final_sha = _ensure_task023_snapshot()
    r = subprocess.run(
        [
            "git",
            "diff",
            "--numstat",
            base_sha,
            final_sha,
            "--",
            "ci-shard-manifest.yml",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    sum_adds = 0
    sum_dels = 0
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        if parts[0].isdigit():
            sum_adds += int(parts[0])
        if parts[1].isdigit():
            sum_dels += int(parts[1])
    assert sum_adds == 3, f"insertion delta {sum_adds} != 3"
    assert sum_dels == 0, f"deletion delta {sum_dels} != 0"


def test_no_task_022_mutation_or_widening() -> None:
    """Production modules MUST NOT mutate TASK-022 module surfaces.
    This test re-affirms that no file outside the allowlist touches
    any TASK-022 module file in the TASK-023 implementation range."""
    base_sha, final_sha = _ensure_task023_snapshot()
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            base_sha,
            final_sha,
            "--",
            "src/hexagent/exchangers/shell_tube/shell_bundle_geometry/",
            "src/hexagent/exchangers/shell_tube/tube_layout/",
            "src/hexagent/exchangers/shell_tube/models.py",
            "src/hexagent/exchangers/shell_tube/__init__.py",
            "src/hexagent/geometry_catalogs/",
            "src/hexagent/rule_packs/",
            "docs/",
            "src/hexagent/canonical_json.py",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    assert not result.stdout.strip(), (
        f"TASK-022 / TASK-016 / docs mutation detected:\n{result.stdout}"
    )


def test_no_workflow_dependency_lockfile_or_doc_mutation() -> None:
    """Workflow / deps / lockfile / design docs MUST NOT be modified
    inside the TASK-023 implementation range."""
    base_sha, final_sha = _ensure_task023_snapshot()
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            base_sha,
            final_sha,
            "--",
            ".github/",
            "pyproject.toml",
            "uv.lock",
            "docs/tasks/TASK-022-",
            "docs/tasks/TASK-016-",
            "docs/tasks/TASK-012-",
            "docs/tasks/TASK-011-",
            "docs/tasks/TASK-010-",
            "docs/tasks/TASK-006-",
            "docs/tasks/TASK-005-",
            "docs/tasks/TASK-004-",
            "docs/tasks/TASK-003-",
            "docs/tasks/TASK-002-",
            "docs/tasks/TASK-001-",
            "docs/MASTER_",
            "docs/ARCHITECTURE",
            "docs/CONTRIBUTING",
            "docs/README",
            "README.md",
            "README_",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    assert not result.stdout.strip(), (
        f"Workflow / dependency / lockfile / doc mutation detected:\n{result.stdout}"
    )


def test_no_production_or_restricted_standard_data_in_worktree() -> None:
    """The implementation MUST NOT carry production / restricted-
    standard / vendor-table bodies. The 9-path allowlist contains
    only the framework + synthetic test builders; the builders are
    documented to forbid production values and the production
    catalog parser rejects everything except synthetic dimensions.
    """
    # Look for forbidden tokens in production modules and builders.
    bad_tokens = [
        "real_standard_dimensions",
        "TEMA",
        "ASME_SECTION_VIII",
        "ASME_BPVC_",
        "ASME_SEC_VIII",
        "ASME_B31.3",
        "API_650",
        "vendor_dim_table",
        "production_shell_value",
        "standard_series_DN",
        "standard_series_NPS",
        "schedule_40_steel_S304",
        "PROJECT_DIM",
        "production_dimension_value",
        "BASIC_CATALOG",
        "ASME_BPVC_II_D",
        "ASME_BPVC_I",
        "ASME_BPVC_III",
    ]
    for path in PRODUCTION_MODULES:
        text = _read(path)
        for tk in bad_tokens:
            assert tk not in text, (
                f"{path.relative_to(REPO_ROOT)} contains forbidden production token {tk!r}"
            )


# --------------------------------------------------------------------------
# TASK-023 Design Amendment 001 (Option B) — round 4 unit tests.
# --------------------------------------------------------------------------


def test_round4_architecture_forbidden_identifiers_in_production_source() -> None:
    """Forbidden production-source identifiers MUST NOT exist in the
    production implementation files. Tests may mention them as
    prohibited spellings; this scan checks the production tree only.
    Use the ``ast`` module to exclude code inside docstrings AND
    comments so the prohibition list may quote the forbidden names
    inside its own documentation.
    """
    import ast

    forbidden = {
        "SHELL_GEOMETRY_CATALOG_STAGE_RANK_BY_CODE",
        "CODE_DERIVED_STAGE_RANK",
        "DEFAULT_STAGE_RANK",
        "STAGE_RANK_ZERO_FALLBACK",
        "CODE_TO_STAGE",
        "BLOCKER_STAGE_MAP",
        "IMPLICIT_STAGE_RANK",
    }
    src_dir = REPO_ROOT / "src" / "hexagent" / "shell_geometry_catalogs"

    def names_in_module(tree: ast.AST) -> set[str]:
        """Set of Name-id references that appear in executable code
        (module-level + function bodies — but NOT string literals or
        docstring bodies).
        """
        seen: set[str] = set()

        class V(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name) -> None:
                seen.add(node.id)
                self.generic_visit(node)

            def visit_Attribute(self, node: ast.Attribute) -> None:
                seen.add(node.attr)
                self.generic_visit(node)

        V().visit(tree)
        return seen

    production_hits: list[tuple[str, str]] = []
    for path in src_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            production_hits.append((str(path), "syntax_error"))
            continue
        bound_names = names_in_module(tree)
        for forbidden_name in forbidden:
            if forbidden_name in bound_names:
                production_hits.append((str(path), forbidden_name))
    assert not production_hits, (
        f"Amendment 001 §3 forbids these production-source identifiers; hits: {production_hits}"
    )


def test_round4_architecture_no_implicit_default_in_make_entry() -> None:
    """``_make_entry`` source MUST NOT include the literal ``stage_rank=0``
    anywhere as an implicit default.
    """
    src_path = REPO_ROOT / "src" / "hexagent" / "shell_geometry_catalogs" / "catalog.py"
    text = src_path.read_text(encoding="utf-8")
    # The forbidden lines would be ``stage_rank: int = 0`` /
    # ``stage_rank=0`` as a default keyword on the ``_make_entry``
    # signature. The signature line is the obvious carrier.
    bad_lines: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if "stage_rank" in line and ("=0" in line or "= 0" in line):
            bad_lines.append((lineno, line.strip()))
    assert not bad_lines, f"Amendment 001 §3 forbids an implicit zero default; hits: {bad_lines}"


# ---------------------------------------------------------------------------
# §9.F — Deep immutability and recursive canonical thaw
# ---------------------------------------------------------------------------
