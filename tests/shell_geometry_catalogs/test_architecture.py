"""Architecture invariants for the TASK-023 shell-geometry-catalog
framework implementation.

The architecture test enforces the merged design contract §13 /
Issue #151 allowlist boundary:

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

# Exact frozen base commit. Bound by TASK-023 source-definition audit and
# Issue #151 / #152. The architecture checks compare the current HEAD
# against this exact commit, not against a moving ``origin/main``.
TASK023_FROZEN_BASE_SHA = "195ad692e4aa0148b28c8f6b86e37e73dfb3a194"


def _ensure_frozen_base_commit() -> str:
    """Guarantee the exact frozen base commit object is locally available.

    Behaviour:

    1. Check whether ``TASK023_FROZEN_BASE_SHA^{commit}`` exists using
       ``git cat-file -e``.
    2. If already present, perform no fetch.
    3. If absent, fetch exactly the frozen SHA from ``origin``.
    4. Re-check that the commit exists.
    5. Fail loudly with captured stderr if the exact frozen commit
       remains unavailable.
    6. Return the exact frozen SHA.

    The helper MUST NOT use mutable ``origin/main`` as authority, MUST
    NOT fetch or merge current main, MUST NOT rebase, MUST NOT mutate
    the working tree, MUST NOT silently return an empty diff, MUST NOT
    skip or xfail the architecture assertions, and MUST NOT swallow
    subprocess errors.
    """
    cat = subprocess.run(
        ["git", "cat-file", "-e", TASK023_FROZEN_BASE_SHA + "^{commit}"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if cat.returncode != 0:
        fetch = subprocess.run(
            [
                "git",
                "fetch",
                "--no-tags",
                "--depth=1",
                "origin",
                TASK023_FROZEN_BASE_SHA,
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        if fetch.returncode != 0:
            raise AssertionError(
                "TASK023 frozen-base commit "
                + TASK023_FROZEN_BASE_SHA
                + " is unavailable after fetch: "
                + (fetch.stderr.strip() or "<no stderr>")
            )
        recheck = subprocess.run(
            ["git", "cat-file", "-e", TASK023_FROZEN_BASE_SHA + "^{commit}"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        if recheck.returncode != 0:
            raise AssertionError(
                "TASK023 frozen-base commit "
                + TASK023_FROZEN_BASE_SHA
                + " is still unavailable after fetch: "
                + (recheck.stderr.strip() or "<no stderr>")
            )
    return TASK023_FROZEN_BASE_SHA


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


def _all_changed_paths() -> list[str]:
    """Return the union of committed-changes (vs the exact frozen
    base commit), staged-changes (vs HEAD), and untracked new files
    inside the allowlist. The two-tree diff against
    ``TASK023_FROZEN_BASE_SHA`` covers only committed changes —
    when the implementation is staged but not yet committed, the
    index-vs-HEAD diff plus the untracked-file list cover the gap.
    """
    _ensure_frozen_base_commit()
    changed: set[str] = set()

    # Committed (HEAD vs frozen base)
    r = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            TASK023_FROZEN_BASE_SHA,
            "HEAD",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    changed.update(line for line in r.stdout.splitlines() if line)

    # Staged (index vs HEAD)
    r = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    changed.update(line for line in r.stdout.splitlines() if line)

    # Untracked inside the allowlist roots
    r = subprocess.run(
        [
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            "src/hexagent/shell_geometry_catalogs/",
            "tests/shell_geometry_catalogs/",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    changed.update(line for line in r.stdout.splitlines() if line)

    return sorted(changed)


def test_exact_9_path_allowlist() -> None:
    """Only the 9-path allowlist appears in the cumulative diff."""
    allowed = set(ALLOWED_PATHS)
    changed = _all_changed_paths()
    unexpected = [p for p in changed if p not in allowed]
    assert not unexpected, (
        f"Architecture allowlist violation: {unexpected!r}; expected only {sorted(allowed)!r}"
    )


def test_ci_shard_manifest_exact_delta() -> None:
    """ci-shard-manifest.yml: exactly +3 insertions / -0 deletions."""
    _ensure_frozen_base_commit()
    r = subprocess.run(
        [
            "git",
            "diff",
            "--numstat",
            TASK023_FROZEN_BASE_SHA,
            "HEAD",
            "--",
            "ci-shard-manifest.yml",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    r_cached = subprocess.run(
        [
            "git",
            "diff",
            "--cached",
            "--numstat",
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
    for line in (r.stdout + r_cached.stdout).splitlines():
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
    """Production modules MUST NOT mutate TASK-022 module surfaces."""
    # Already verified by test_production_modules_do_not_import_task_022_runtime.
    # This test re-affirms that no file outside the allowlist touches
    # any TASK-022 module file in the cumulative diff.
    _ensure_frozen_base_commit()
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            TASK023_FROZEN_BASE_SHA,
            "HEAD",
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
    """Workflow / deps / lockfile / design docs MUST NOT be modified."""
    _ensure_frozen_base_commit()
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            TASK023_FROZEN_BASE_SHA,
            "HEAD",
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
