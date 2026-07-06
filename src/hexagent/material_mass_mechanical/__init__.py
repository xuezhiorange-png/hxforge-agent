"""TASK-017 material / mass / preliminary mechanical application layer.

Implements the TASK-017 frozen design contract
(docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md,
Frozen Contract Authority Commit SHA
``6ed5b7dc7d8df163796eacb838afcf5702a4c53a``,
Frozen Contract Authority Base SHA
``fbb05ae71f21e6cfd4d1041afb5958c863166248``) as a read-only
consumer of the TASK-013 frozen material / cost governance records.

Slice A (this module): MaterialSelector only.
Slices B / C / D / Closeout are NOT YET IMPLEMENTED.

The TASK-017 application layer NEVER modifies TASK-013 records,
NEVER introduces pressure-drop / C4 / cost / new-solver logic,
and NEVER bypasses the TASK-013 closed-set enums.
"""