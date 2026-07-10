"""TASK-020 no-upstream-mutation guard test.

Asserts that the TASK-020 Slice A implementation does not modify any
frozen TASK-001..TASK-019 contract file. Pattern mirrors
``tests/validation_report/test_no_upstream_mutation.py``.

This test is run as part of the local pytest suite only. CI registration
is DEFERRED per the round's scope (per Charles's explicit "ci-shard-manifest.yml out of scope" instruction).
"""

from __future__ import annotations

from pathlib import Path


# 19 frozen contract files (per TASK-019 frozen design §9.1)
FROZEN_CONTRACT_PATHS: list[str] = [
    "docs/tasks/TASK-001-engineering-baseline.md",
    "docs/tasks/TASK-002-units-and-quantities.md",
    "docs/tasks/TASK-003-property-service.md",
    "docs/tasks/TASK-004-correlation-registry.md",
    "docs/tasks/TASK-005-correlation-registry.md",
    "docs/tasks/TASK-006-heat-balance.md",
    "docs/tasks/TASK-007-tube-annulus-correlations.md",
    "docs/tasks/TASK-007-double-pipe-correlations.md",
    "docs/tasks/TASK-008-double-pipe-rating.md",
    "docs/tasks/TASK-009-double-pipe-sizing.md",
    "docs/tasks/TASK-010-report-and-api.md",
    "docs/tasks/TASK-011-benchmark-case-governance.md",
    "docs/tasks/TASK-012-standards-rule-pack-license-boundary.md",
    "docs/tasks/TASK-013-material-cost-data-governance.md",
    "docs/tasks/TASK-014-immutable-case-revisions-persistence.md",
    "docs/tasks/TASK-015-ci-security-and-release-automation.md",
    "docs/tasks/TASK-015A-deterministic-test-environment-and-ci-sharding.md",
    "docs/tasks/TASK-016-approved-geometry-catalog.md",
    "docs/tasks/TASK-019-golden-cases-double-pipe-validation.md",
]


def test_no_frozen_task_doc_modified_by_this_module() -> None:
    """Verify that the TASK-020 implementation does not modify any
    frozen TASK-001..TASK-019 contract file.

    Implementation note: this is a **structural** test — it asserts
    that the new module files in this round do not import or
    reference any of the frozen contract paths as write targets.
    """
    import hexagent.exchangers.shell_tube as st
    from hexagent.exchangers.shell_tube import (
        authority,
        canonical,
        errors,
        models,
        schema,
        validation,
    )

    new_modules = [st, authority, canonical, errors, models, schema, validation]
    for module in new_modules:
        source_path = module.__file__
        assert source_path is not None
        with open(source_path, "r", encoding="utf-8") as fh:
            source = fh.read()
        for frozen_path in FROZEN_CONTRACT_PATHS:
            # The TASK-020 implementation may mention frozen
            # documents in comments / docstrings (for context), but
            # must not have any open() / write() / Path operations
            # that target them.
            assert (
                f'open("{frozen_path}"' not in source
                and f"open('{frozen_path}'" not in source
                and f'Path("{frozen_path}")' not in source
                and f"Path('{frozen_path}')" not in source
            ), f"module {module.__name__} references {frozen_path}"


def test_no_production_module_modification_outside_shell_tube() -> None:
    """The TASK-020 implementation must not modify any production
    module outside the ``src/hexagent/exchangers/shell_tube/``
    package."""
    import hexagent.exchangers.shell_tube as st
    from hexagent.exchangers.shell_tube import (
        authority,
        canonical,
        errors,
        models,
        schema,
        validation,
    )

    forbidden_module_targets = [
        "hexagent.case_revisions",
        "hexagent.validation_report",
        "hexagent.rule_packs",
        "hexagent.domain",
        "hexagent.core",
        "hexagent.application",
        "hexagent.canonical_json",
        "hexagent.api",
    ]

    new_modules = [st, authority, canonical, errors, models, schema, validation]
    for module in new_modules:
        source_path = module.__file__
        assert source_path is not None
        with open(source_path, "r", encoding="utf-8") as fh:
            source = fh.read()
        for forbidden in forbidden_module_targets:
            assert (
                f"from {forbidden} import" not in source
                and f"import {forbidden}" not in source
            ), f"module {module.__name__} imports {forbidden}"


def test_no_migrations_or_workflow_modification() -> None:
    """The TASK-020 implementation must not modify any migration,
    CI workflow, or dependency file.

    The test looks for actual write-patterns (``open(... 'w'/'a'/'x')``,
    ``Path(...).write_text``, ``Path(...).write_bytes``) targeting
    these files — not bare string mentions, which are allowed in
    docstrings and comments to describe what is out of scope.
    """
    import re

    import hexagent.exchangers.shell_tube as st
    from hexagent.exchangers.shell_tube import (
        authority,
        canonical,
        errors,
        models,
        schema,
        validation,
    )

    forbidden_file_targets = [
        "pyproject.toml",
        "ci-shard-manifest.yml",
        "alembic",
        "migrations",
    ]
    new_modules = [st, authority, canonical, errors, models, schema, validation]
    for module in new_modules:
        source_path = module.__file__
        assert source_path is not None
        with open(source_path, "r", encoding="utf-8") as fh:
            source = fh.read()
        for forbidden in forbidden_file_targets:
            # Look for actual file write patterns, not bare mentions.
            patterns = [
                rf'open\(\s*["\'][^"\']*{re.escape(forbidden)}[^"\']*["\']\s*,\s*["\'][wax]?["\']',
                rf'open\(\s*["\'][^"\']*{re.escape(forbidden)}[^"\']*["\']\s*,\s*mode\s*=',
                rf'Path\(\s*["\'][^"\']*{re.escape(forbidden)}[^"\']*["\']\s*\)\s*\.\s*write_',
                rf'Path\(\s*["\'][^"\']*{re.escape(forbidden)}[^"\']*["\']\s*\)\s*\.\s*unlink',
            ]
            for pattern in patterns:
                assert not re.search(pattern, source), (
                    f"module {module.__name__} has write-pattern "
                    f"to {forbidden}: pattern={pattern!r}"
                )
