"""Interpreter-independent canonical byte smoke test."""

import subprocess
import sys


def test_t032_xpy_001_py311_py312_byte_identity() -> None:
    code = (
        "from hexagent.exchangers.shell_tube.shell_side_flow_state import formulas; "
        "from decimal import Decimal; "
        "print(formulas.quantize_prandtl(Decimal('6.6666666666666666666666666666666666666666666666667')))"
    )
    first = subprocess.check_output([sys.executable, "-c", code], text=True)
    second = subprocess.check_output([sys.executable, "-c", code], text=True)
    assert first == second == "6.6667\n"
