#!/usr/bin/env python3
"""Legacy alias — delegates to V08_03_330KW terminal/mesh closeout runner."""
# ruff: noqa: E402, E501

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "run_v08_03_330kw_terminal_mesh_closeout.py"
    runpy.run_path(str(target), run_name="__main__")
