from __future__ import annotations

from pathlib import Path

import pytest

from hexagent.benchmark_cases.validation import validate_corpus


@pytest.mark.benchmark
def test_task011_approved_benchmark_corpus_validates() -> None:
    validate_corpus(Path.cwd())
