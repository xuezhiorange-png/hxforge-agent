"""End-to-end test for the in-repo seed rule-pack.

Verifies that the committed seed rule-pack at ``rule_packs/internal_seed/``
passes validation. This guards against accidental breakage of the seed.
"""

from __future__ import annotations

from pathlib import Path

from hexagent.rule_packs.validation import validate_rule_pack


def test_seed_rule_pack_passes_validation() -> None:
    # Resolve the seed rule-pack relative to the repo root (this file's
    # grandparent) so the test works from any working directory.
    repo_root = Path(__file__).resolve().parents[2]
    seed = repo_root / "rule_packs" / "internal_seed"
    report = validate_rule_pack(seed)
    assert report["status"] == "ok", report["errors"]
    assert report["rule_count"] == 2
