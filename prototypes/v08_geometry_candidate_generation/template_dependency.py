"""Task168 template dependency disclosure for V08-02 engineering audit."""

from __future__ import annotations

TASK168_TEMPLATE_DEPENDENCY_STATEMENT = (
    "V08-02 calls build_implementation_validation_task168_reference() only to obtain "
    "Task168 evaluation producer-chain templates (Task021–Task035 wiring). "
    "Discrete geometry dimensions are overwritten from V08-GENERAL-GEOMETRY-DISCRETE-SPACE-R1 "
    "before enumeration. Process-side mass flows and inlet temperatures are bound from "
    "V08SolverHandoffV1 with no silent defaults. Per-candidate shell bundle geometry uses "
    "the shell catalog record for that candidate; Task021 placement envelope is recomputed "
    "per candidate shell ID when VARIABLE_SHELL_TASK021_PLACEMENT_ENVELOPE_OPT_IN_R13 is set. "
    "Implementation-validation reference mass flow (20 kg/s) in the template is replaced "
    "before any candidate evaluation. Thermal rating and V07 acceptance conclusions from "
    "the template are not used (include_legacy_task162=False)."
)
