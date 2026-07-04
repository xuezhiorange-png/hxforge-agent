"""Module entry point for ``python -m hexagent.rule_packs``.

Currently this module simply dispatches to the validator CLI under
``hexagent.rule_packs.validate``. The default action is validation of a
rule-pack directory supplied as the first positional argument.

Example::

    python -m hexagent.rule_packs rule_packs/internal_seed --strict
"""

from __future__ import annotations

import sys

from hexagent.rule_packs.validate import main as _validate_main

if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(_validate_main(sys.argv[1:]))
