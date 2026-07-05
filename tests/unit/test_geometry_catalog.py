"""TASK-016 geometry catalog manifest ownership shim.

The frozen TASK-016 behavior is covered by
``test_task016_geometry_catalog.py`` and
``test_task016_geometry_catalog_pipe_refs.py``. This module keeps the CI shard
manifest ownership complete for the generic geometry catalog test path.
"""

from __future__ import annotations

from hexagent.geometry_catalogs import GEOMETRY_TYPE_HAIRPIN, GEOMETRY_TYPE_PIPE, GEOMETRY_TYPE_TUBE


def test_geometry_catalog_type_literals_are_stable() -> None:
    assert GEOMETRY_TYPE_TUBE == "tube"
    assert GEOMETRY_TYPE_PIPE == "pipe"
    assert GEOMETRY_TYPE_HAIRPIN == "hairpin"
