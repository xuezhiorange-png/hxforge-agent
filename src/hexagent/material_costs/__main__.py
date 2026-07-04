"""Module entry point for ``python -m hexagent.material_costs``.

Dispatches to the validator CLI under
:mod:`hexagent.material_costs.validate`. The default action is
validation of a catalog directory supplied as the first positional
argument.

Example::

    python -m hexagent.material_costs rule_packs/material_cost_seed --strict
"""

from __future__ import annotations

import sys

from hexagent.material_costs.validate import main as _validate_main

if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(_validate_main(sys.argv[1:]))
