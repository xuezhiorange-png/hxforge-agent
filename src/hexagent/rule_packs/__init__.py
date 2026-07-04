"""Rule-pack runtime package for TASK-012.

This package implements the TASK-012 frozen design contract:
docs/tasks/TASK-012-standards-rule-pack-license-boundary.md
(review Head 28b6330f8c5221d75f101f6810157d81a428f446).

It provides:

* Schema models and validation for rule-pack manifests and rule artifacts
  (Section 7).
* License boundary enforcement (Section 4.1 / 4.2 / 5 / 6 / 16).
* Provenance graph validation (Section 11).
* A canonical-JSON-backed loader for rule-pack artifacts.
* A validator CLI exposed as ``python -m hexagent.rule_packs.validate``.

The shared canonical JSON helper ``hexagent.canonical_json`` is the single
source of truth for canonical JSON behavior across TASK-011 benchmark cases
and TASK-012 rule-packs. This package MUST NOT introduce a parallel
canonical module.
"""

from __future__ import annotations

from hexagent.rule_packs.errors import RulePackError, RulePackValidationError

__all__ = ["RulePackError", "RulePackValidationError"]
