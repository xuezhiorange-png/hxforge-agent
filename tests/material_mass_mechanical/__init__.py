"""Tests for TASK-017 Slice A — MaterialSelector.

Tests are scoped to design §5.1 (MaterialSelector) only. Slice B
(MassCalculator), Slice C (allowable-stress-only check), and
Slice D (minimum-wall + straight-pipe-span checks) tests are NOT
included in this round per the slice authorization template
(docs/tasks/TASK-017-materials-mass-mechanical-implementation.md
§10) and the planning doc §6 test plan which scopes each test to
a single slice.

Each test must pass under Python 3.11 + 3.12 (project
``requires-python = ">=3.11"``); determinism is asserted via
``result_hash`` equality across two invocations.
"""
