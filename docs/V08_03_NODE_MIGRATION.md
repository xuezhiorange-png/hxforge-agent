# V08-03 CI node migration (thermal partition)

Same pytest node IDs unless noted. Heavy nodes moved to dedicated files for shard scheduling.

| Original location | New location | `nodeid` |
|---|---|---|
| `test_v08_thermal_rating.py` | `test_v08_thermal_rating_closeout_heavy.py` | `tests/prototypes/test_v08_thermal_rating_closeout_heavy.py::test_v08_03_closeout_engineering_acceptance_or_engineering_blocked` |
| `test_v08_thermal_rating.py` | `test_v08_thermal_rating_independent_case_heavy.py` | `tests/prototypes/test_v08_thermal_rating_independent_case_heavy.py::test_v08_03_independent_case_input_delta` |
| `test_v08_thermal_rating.py` | (unchanged) | `tests/prototypes/test_v08_thermal_rating.py::test_v08_03_model_blocked_without_experimental_thermal_binding` |

| `test_v08_axial_rating_engine.py` | (split) | `tests/prototypes/test_v08_axial_rating_engine.py::test_330kw_outer_search_direction_and_n1_closeout` → `::test_330kw_outer_search_direction_on_isolated_n1` and `::test_330kw_closeout_one_candidate_energy_and_evidence` |

All other V08-03 prototype tests retain prior `nodeid` strings unless listed above. New CI diagnostic nodes (not part of 93 V08 obligations):

- `tests/ci/test_shard_progress_and_timeout.py::test_shard_progress_mark_running_persists_node`
- `tests/ci/test_shard_progress_and_timeout.py::test_run_test_shard_timeout_not_collection_error`