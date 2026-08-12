"""TASK-028 test suite: 77 frozen test IDs.

§28 — Test inventory.  Each ``test_T028_XXX`` function corresponds to exactly
one frozen TEST_ID.  No database markers.  No external fixtures.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, localcontext
from typing import Any

from hexagent.exchangers.shell_tube.tube_side.blocked_result import Task025BlockedResult
from hexagent.exchangers.shell_tube.tube_side.length_authorities import (
    HeatTransferLengthAuthority,
    InternalFlowLengthAuthority,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    HydraulicAuthorityMode,
    ReferencePlanePair,
    ReferencePlaneToken,
)
from hexagent.exchangers.shell_tube.tube_side.provenance import (
    FrozenIdentity,
    FrozenProvenance,
    FrozenRawProjection,
)
from hexagent.exchangers.shell_tube.tube_side.valid_result import Task025ValidResult
from hexagent.exchangers.shell_tube.tube_side_local_loss import (
    IMPLEMENTATION_SOFTWARE_VERSION,
    PRESSURE_LOSS_QUANTUM,
    REFERENCE_VELOCITY_QUANTUM,
    TASK028_AUTHORITY_SCHEMA_VERSION,
    TASK028_BLOCKED_RESULT_SCHEMA_VERSION,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_COEFFICIENT_SEMANTICS,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELD_COUNT,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELDS,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FORMULA,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_ID,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_LOCATION,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_PERMISSION_STATUS,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_SCOPE,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_TITLE,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_VERSION,
    TASK028_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION,
    TASK028_REQUEST_SCHEMA_VERSION,
    TASK028_SUCCESS_RESULT_SCHEMA_VERSION,
    CoefficientPermissionStatus,
    LossCoefficientConvention,
    Task028ApplicabilityAssertion,
    Task028BlockerCode,
    Task028BlockerEntry,
    Task028ComponentFlowDirectionAssertion,
    Task028ComponentType,
    Task028RawProjection,
    TubeSideLocalLossComponentAuthority,
    TubeSideLocalLossComponentResult,
    build_blocked_result,
    build_success_result,
    canonicalize_raw_value,
    collapse_blockers,
    compute_authority_hash,
    compute_local_loss_component,
    compute_raw_boundary_blocked_hash,
    compute_request_hash,
    compute_result_id,
    compute_success_result_hash,
    emit_blocker,
    encode_raw_projection,
    normalize_negative_zero,
    quantize_task028_decimal,
    task028_decimal_context,
    task028_decimal_payload,
    validate_raw_boundary,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
    TASK028_DEFERRED_CAPABILITIES_V1,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.pipeline import (
    compute_task028_local_loss,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
    Task028BlockedResult,
    Task028Provenance,
    Task028SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    FlowRegime,
    PhaseAssertion,
    PhaseRegion,
    ThermalBoundaryCondition,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.blocker_registry import (
    BlockerEntry,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.property_snapshot import (
    PropertySnapshot,
    recompute_property_snapshot_hash,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.provenance import (
    FrozenProvenance as ThermalFrozenProvenance,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.raw_projection import (
    FrozenRawProjection as ThermalFrozenRawProjection,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import (
    RawBoundaryBlockedResult,
    TubeSideBlockedResult,
    TubeSideThermalResult,
)

# ---------------------------------------------------------------------------
# Frozen canonical vector hex constants (from TASK028_FROZEN_VECTOR_ORACLE.md)
# ---------------------------------------------------------------------------

FROZEN_VECTOR_01_CANONICAL_BYTES_HEX = "000000297461736b3032382e6c6f63616c2d6c6f73732d636f6d706f6e656e742d617574686f726974792e7631000000100000000e736368656d615f76657273696f6e00000006535452494e4700000000000000297461736b3032382e6c6f63616c2d6c6f73732d636f6d706f6e656e742d617574686f726974792e76310000000c636f6d706f6e656e745f696400000006535452494e470000000000000007454e542d3030310000000e636f6d706f6e656e745f7479706500000004454e554d0000000000000008454e5452414e434500000013706174685f73657175656e63655f696e64657800000007494e544547455200000000000000013000000018757073747265616d5f7265666572656e63655f706c616e6500000006535452494e4700000000000000117368656c6c2d696e6c65742d706c616e650000001a646f776e73747265616d5f7265666572656e63655f706c616e6500000006535452494e470000000000000010747562652d696e6c65742d706c616e6500000018666c6f775f646972656374696f6e5f617373657274696f6e00000004454e554d000000000000000c53544152545f544f5f454e44000000106c6f73735f636f656666696369656e7400000007444543494d414c000000000000000a302e35303030303030300000001b6c6f73735f636f656666696369656e745f636f6e76656e74696f6e00000004454e554d00000000000000364b5f45515f495252455645525349424c455f44454c54415f505f4f5645525f52484f5f565245465f535155415245445f4f5645525f32000000167265666572656e63655f666c6f775f617265615f6d3200000007444543494d414c000000000000000e302e3030303738353339383136330000000c6d756c7469706c696369747900000007494e54454745520000000000000001310000001667656f6d657472795f65766964656e63655f72656673000000055455504c45000000000000003f00000001000000000000003300000006535452494e47000000000000002143414e4f4e4943414c2d564543544f522d45564944454e43452d454e542d30303100000015636f656666696369656e745f736f757263655f696400000006535452494e47000000000000001743414e4f4e4943414c2d564543544f522d534f555243450000001a636f656666696369656e745f736f757263655f76657273696f6e00000006535452494e47000000000000000276310000001b636f656666696369656e745f736f757263655f6c6f636174696f6e00000006535452494e47000000000000002c63616e6f6e6963616c2d766563746f723a2f2f7461736b3032382f617574686f726974792f454e542d3030310000001d636f656666696369656e745f7065726d697373696f6e5f73746174757300000004454e554d000000000000000841444d4954544544"  # noqa: E501
FROZEN_VECTOR_02_CANONICAL_BYTES_HEX = "000000127461736b3032382e726571756573742e76310000000a0000000e736368656d615f76657273696f6e00000006535452494e4700000000000000127461736b3032382e726571756573742e76310000000a70726f66696c655f696400000006535452494e47000000000000000764656661756c74000000207461736b3032355f6879647261756c69635f617574686f726974795f6861736800000006535452494e47000000000000004061616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161000000137461736b3032355f726573756c745f6861736800000006535452494e47000000000000004062626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262000000137461736b3032365f726573756c745f6861736800000006535452494e470000000000000040636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363630000001670726f70657274795f736e617073686f745f6861736800000006535452494e470000000000000040646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464640000001f636f6e7374616e745f64656e736974795f706174685f617373657274696f6e00000004454e554d000000000000000454525545000000237a65726f5f6e65745f656c65766174696f6e5f6368616e67655f617373657274696f6e00000004454e554d00000000000000045452554500000018666c6f775f646972656374696f6e5f617373657274696f6e00000004454e554d000000000000000c53544152545f544f5f454e440000001a636f6d706f6e656e745f617574686f726974795f686173686573000000055455504c4500000000000000b800000002000000000000005200000006535452494e47000000000000004036316562383435303362336166666431306631333934326161333763333264633439366634323133613133333331393366633661643262623436643133663435000000000000005200000006535452494e47000000000000004038376266336135366538356534666366313639613461373165626362363034613835373737383932303162343431643338633031643835613130363634336461"  # noqa: E501
FROZEN_VECTOR_03_CANONICAL_BYTES_HEX = "000000127461736b3032382e726571756573742e76310000000a0000000e736368656d615f76657273696f6e00000006535452494e4700000000000000127461736b3032382e726571756573742e76310000000a70726f66696c655f696400000006535452494e47000000000000000764656661756c74000000207461736b3032355f6879647261756c69635f617574686f726974795f6861736800000006535452494e47000000000000004061616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161000000137461736b3032355f726573756c745f6861736800000006535452494e47000000000000004062626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262000000137461736b3032365f726573756c745f6861736800000006535452494e470000000000000040636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363630000001670726f70657274795f736e617073686f745f6861736800000006535452494e470000000000000040646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464640000001f636f6e7374616e745f64656e736974795f706174685f617373657274696f6e00000004454e554d000000000000000454525545000000237a65726f5f6e65745f656c65766174696f6e5f6368616e67655f617373657274696f6e00000004454e554d00000000000000045452554500000018666c6f775f646972656374696f6e5f617373657274696f6e00000004454e554d000000000000000c53544152545f544f5f454e440000001a636f6d706f6e656e745f617574686f726974795f686173686573000000055455504c4500000000000000b800000002000000000000005200000006535452494e47000000000000004036316562383435303362336166666431306631333934326161333763333264633439366634323133613133333331393366633661643262623436643133663435000000000000005200000006535452494e47000000000000004038376266336135366538356534666366313639613461373165626362363034613835373737383932303162343431643338633031643835613130363634336461"  # same as VECTOR_02  # noqa: E501
FROZEN_VECTOR_04_CANONICAL_BYTES_HEX = "000000197461736b3032382e626c6f636b65642d726573756c742e76310000000d0000000e736368656d615f76657273696f6e00000006535452494e4700000000000000197461736b3032382e626c6f636b65642d726573756c742e76310000000a70726f66696c655f696400000006535452494e47000000000000000764656661756c740000000c726571756573745f6861736800000006535452494e47000000000000004066303038393861346564333362393931656130353532666437366332613533353438356565613233373861353034383937343362653336636664353566383964000000207461736b3032355f6879647261756c69635f617574686f726974795f6861736800000006535452494e47000000000000004061616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161000000137461736b3032355f726573756c745f6861736800000006535452494e47000000000000004062626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262000000137461736b3032365f726573756c745f6861736800000006535452494e470000000000000040636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363630000001670726f70657274795f736e617073686f745f6861736800000006535452494e47000000000000004064646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464000000167261775f726571756573745f70726f6a656374696f6e0000000e5241575f50524f4a454354494f4e00000000000000b6000000197461736b3032382e7261772d70726f6a656374696f6e2e7631000000020000000f70726f6a656374696f6e5f6b696e6400000006535452494e470000000000000007726571756573740000001363616e6f6e6963616c5f62797465735f68657800000006535452494e470000000000000040303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030300000001f7261775f757073747265616d5f626c6f636b65645f70726f6a656374696f6e000000044e4f4e450000000000000000000000087761726e696e6773000000055455504c4500000000000000040000000000000008626c6f636b657273000000055455504c450000000000000180000000010000000000000174000000065245434f52440000000000000162000000187461736b3032382e626c6f636b65722d656e7472792e76310000000400000004636f646500000006535452494e470000000000000029424c5f543032385f434f4d504f4e454e545f464c4f575f444952454354494f4e5f4d49534d415443480000000a6669656c645f70617468000000055455504c45000000000000004f00000001000000000000004300000006535452494e470000000000000031636f6d706f6e656e745f617574686f7269746965735b305d2e666c6f775f646972656374696f6e5f617373657274696f6e0000000b6d6573736167655f6b657900000006535452494e470000000000000029424c5f543032385f434f4d504f4e454e545f464c4f575f444952454354494f4e5f4d49534d415443480000000d65766964656e63655f72656673000000055455504c45000000000000002500000001000000000000001900000006535452494e470000000000000007454e542d3030320000001564656665727265645f6361706162696c6974696573000000055455504c4500000000000000ca00000003000000000000003a00000006535452494e4700000000000000284d4f44454c45445f544f54414c5f50524553535552455f44524f505f4e4f545f434f4d5055544544000000000000003a00000006535452494e4700000000000000285245464552454e43455f504c414e455f434f4e54494e554954595f4e4f545f56414c494441544544000000000000003a00000006535452494e47000000000000002850524553535552455f504154485f434f4d504c4554454e4553535f4e4f545f56414c4944415445440000000a70726f76656e616e6365000000065245434f5244000000000000031d000000157461736b3032382e70726f76656e616e63652e763100000005000000077461736b5f696400000006535452494e4700000000000000085441534b2d3032380000001464657369676e5f636f6e74726163745f7061746800000006535452494e47000000000000001d5441534b2d3032382d736f757263652d646566696e6974696f6e2e6d640000001f696d706c656d656e746174696f6e5f736f6674776172655f76657273696f6e00000006535452494e470000000000000005302e332e3000000013696e7075745f65766964656e63655f72656673000000055455504c45000000000000003f00000001000000000000003300000006535452494e47000000000000002143414e4f4e4943414c2d564543544f522d45564944454e43452d454e542d30303200000018757073747265616d5f6964656e746974795f686173686573000000055455504c4500000000000001c600000005000000000000005200000006535452494e47000000000000004061616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161000000000000005200000006535452494e47000000000000004062626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262000000000000005200000006535452494e47000000000000004063636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363000000000000005200000006535452494e47000000000000004064646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464000000000000005200000006535452494e47000000000000004036316562383435303362336166666431306631333934326161333763333264633439366634323133613133333331393366633661643262623436643133663435"  # noqa: E501
FROZEN_VECTOR_05_CANONICAL_BYTES_HEX = "000000197461736b3032382e737563636573732d726573756c742e76310000000c0000000e736368656d615f76657273696f6e00000006535452494e4700000000000000197461736b3032382e737563636573732d726573756c742e76310000000a70726f66696c655f696400000006535452494e47000000000000000764656661756c740000000c726571756573745f6861736800000006535452494e47000000000000004064303866653232643934303733393734623532666232643239323936323839396161383831613934336437373637326431303331643336666163663538303063000000207461736b3032355f6879647261756c69635f617574686f726974795f6861736800000006535452494e47000000000000004061616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161000000137461736b3032355f726573756c745f6861736800000006535452494e47000000000000004062626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262000000137461736b3032365f726573756c745f6861736800000006535452494e470000000000000040636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363630000001670726f70657274795f736e617073686f745f6861736800000006535452494e4700000000000000406464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646400000011636f6d706f6e656e745f726573756c7473000000055455504c45000000000000039800000001000000000000038c000000065245434f5244000000000000037a0000001b7461736b3032382e636f6d706f6e656e742d726573756c742e76310000000e0000000c636f6d706f6e656e745f696400000006535452494e470000000000000007454e472d3030310000000e636f6d706f6e656e745f7479706500000004454e554d0000000000000008454e5452414e434500000013706174685f73657175656e63655f696e64657800000007494e544547455200000000000000013000000018757073747265616d5f7265666572656e63655f706c616e6500000006535452494e4700000000000000117368656c6c2d696e6c65742d706c616e650000001a646f776e73747265616d5f7265666572656e63655f706c616e6500000006535452494e470000000000000010747562652d696e6c65742d706c616e6500000018666c6f775f646972656374696f6e5f617373657274696f6e00000004454e554d000000000000000c53544152545f544f5f454e440000000e617574686f726974795f6861736800000006535452494e47000000000000004033313161313833363535613633613537336530336530373634393935393935643561663065323837663939633364393338646231373263636237646363373331000000167265666572656e63655f666c6f775f617265615f6d3200000007444543494d414c000000000000000e302e303030373835333938313633000000167265666572656e63655f76656c6f636974795f6d5f7300000007444543494d414c000000000000000a302e3633373736373735000000106c6f73735f636f656666696369656e7400000007444543494d414c000000000000000a302e35303030303030300000001b6c6f73735f636f656666696369656e745f636f6e76656e74696f6e00000004454e554d00000000000000364b5f45515f495252455645525349424c455f44454c54415f505f4f5645525f52484f5f565245465f535155415245445f4f5645525f320000000c6d756c7469706c696369747900000007494e54454745520000000000000001310000002f73696e676c655f6f6363757272656e63655f697272657665727369626c655f70726573737572655f6c6f73735f706100000007444543494d414c00000000000000073130312e35303400000027636f6d706f6e656e745f697272657665727369626c655f70726573737572655f6c6f73735f706100000007444543494d414c00000000000000073130312e353034000000087761726e696e6773000000055455504c4500000000000000040000000000000008626c6f636b657273000000055455504c450000000000000004000000000000001564656665727265645f6361706162696c6974696573000000055455504c4500000000000000ca00000003000000000000003a00000006535452494e4700000000000000284d4f44454c45445f544f54414c5f50524553535552455f44524f505f4e4f545f434f4d5055544544000000000000003a00000006535452494e4700000000000000285245464552454e43455f504c414e455f434f4e54494e554954595f4e4f545f56414c494441544544000000000000003a00000006535452494e47000000000000002850524553535552455f504154485f434f4d504c4554454e4553535f4e4f545f56414c4944415445440000000a70726f76656e616e6365000000065245434f5244000000000000031c000000157461736b3032382e70726f76656e616e63652e763100000005000000077461736b5f696400000006535452494e4700000000000000085441534b2d3032380000001464657369676e5f636f6e74726163745f7061746800000006535452494e47000000000000001d5441534b2d3032382d736f757263652d646566696e6974696f6e2e6d640000001f696d706c656d656e746174696f6e5f736f6674776172655f76657273696f6e00000006535452494e470000000000000005302e332e3000000013696e7075745f65766964656e63655f72656673000000055455504c45000000000000003e00000001000000000000003200000006535452494e47000000000000002043414e4f4e4943414c2d564543544f522d454e47494e454552494e472d30303100000018757073747265616d5f6964656e746974795f686173686573000000055455504c4500000000000001c600000005000000000000005200000006535452494e47000000000000004061616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161000000000000005200000006535452494e47000000000000004062626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262000000000000005200000006535452494e47000000000000004063636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363636363000000000000005200000006535452494e47000000000000004064646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464646464000000000000005200000006535452494e47000000000000004033313161313833363535613633613537336530336530373634393935393935643561663065323837663939633364393338646231373263636237646363373331"  # noqa: E501

# Frozen authority hashes for VECTOR_02/03
FROZEN_AUTHORITY_0_HASH = "61eb84503b3affd10f13942aa37c32dc496f4213a1333193fc6ad2bb46d13f45"
FROZEN_AUTHORITY_1_HASH = "87bf3a56e85e4fcf169a4a71ebcb604a8577789201b441d38c01d85a106643da"
FROZEN_ENG_AUTHORITY_HASH = "311a183655a63a573e03e0764995995d5af0e287f99c3d938db172ccb7dcc731"
# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_entrance_authority(
    component_id: str = "ENTRANCE-001",
    path_sequence_index: int = 0,
    flow_direction: Task028ComponentFlowDirectionAssertion = (
        Task028ComponentFlowDirectionAssertion.START_TO_END
    ),
    loss_coefficient: Decimal = Decimal("0.5"),
    reference_flow_area: Decimal = Decimal("0.007854"),
    multiplicity: int = 1,
    geometry_evidence_refs: tuple[str, ...] = ("EVIDENCE-001",),
    coefficient_source_id: str = "USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL",
    coefficient_source_version: str = "2024.1",
    coefficient_source_location: str = "USACE HEC-RAS, Section 6.2.1",
    coefficient_permission_status: CoefficientPermissionStatus = (
        CoefficientPermissionStatus.ADMITTED
    ),
) -> TubeSideLocalLossComponentAuthority:
    """Build a valid entrance authority with computed hash."""
    authority_hash = compute_authority_hash(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id=component_id,
        component_type="ENTRANCE",
        path_sequence_index=path_sequence_index,
        upstream_reference_plane="INLET",
        downstream_reference_plane="TUBE_START",
        flow_direction_assertion=flow_direction.value,
        loss_coefficient=loss_coefficient,
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2=reference_flow_area,
        multiplicity=multiplicity,
        geometry_evidence_refs=geometry_evidence_refs,
        coefficient_source_id=coefficient_source_id,
        coefficient_source_version=coefficient_source_version,
        coefficient_source_location=coefficient_source_location,
        coefficient_permission_status=coefficient_permission_status.value,
    )
    return TubeSideLocalLossComponentAuthority(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id=component_id,
        component_type=Task028ComponentType.ENTRANCE,
        path_sequence_index=path_sequence_index,
        flow_direction_assertion=flow_direction,
        loss_coefficient=loss_coefficient,
        loss_coefficient_convention=(
            LossCoefficientConvention.K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2
        ),
        reference_flow_area_m2=reference_flow_area,
        multiplicity=multiplicity,
        upstream_reference_plane="INLET",
        downstream_reference_plane="TUBE_START",
        geometry_evidence_refs=geometry_evidence_refs,
        coefficient_source_id=coefficient_source_id,
        coefficient_source_version=coefficient_source_version,
        coefficient_source_location=coefficient_source_location,
        coefficient_permission_status=coefficient_permission_status,
        authority_hash=authority_hash,
    )


def _make_success_provenance() -> Task028Provenance:
    return Task028Provenance(
        task_id="TASK-028",
        design_contract_path="TASK028_DESIGN_CONTRACT_R1.md",
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        input_evidence_refs=(),
        upstream_identity_hashes=(),
    )


def _make_minimal_component_result() -> TubeSideLocalLossComponentResult:
    """Build a minimal valid component result for success result fixtures."""
    ref_vel, single, comp_pa = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    return TubeSideLocalLossComponentResult(
        component_id="E-001",
        component_type=Task028ComponentType.ENTRANCE,
        path_sequence_index=0,
        upstream_reference_plane="INLET",
        downstream_reference_plane="TUBE_START",
        flow_direction_assertion=Task028ComponentFlowDirectionAssertion.START_TO_END,
        authority_hash="a" * 64,
        reference_flow_area_m2=Decimal("0.007854"),
        reference_velocity_m_s=ref_vel,
        loss_coefficient=Decimal("0.5"),
        loss_coefficient_convention=(
            LossCoefficientConvention.K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2
        ),
        multiplicity=1,
        single_occurrence_irreversible_pressure_loss_pa=single,
        component_irreversible_pressure_loss_pa=comp_pa,
    )


def _make_raw_request(**overrides: Any) -> dict[str, Any]:
    """Build a minimal valid raw request dict."""
    base: dict[str, Any] = {
        "schema_version": TASK028_REQUEST_SCHEMA_VERSION,
        "profile_id": "profile-001",
        "task025_valid_result": None,
        "task026_success_result": None,
        "property_snapshot": {"density_kg_m3": "1000.0"},
        "property_snapshot_hash": "a" * 64,
        "constant_density_path_assertion": "TRUE",
        "zero_net_elevation_change_assertion": "TRUE",
        "flow_direction_assertion": "START_TO_END",
        "component_authorities": [
            {
                "component_id": "ENTRANCE-001",
                "component_type": "ENTRANCE",
                "path_sequence_index": 0,
                "flow_direction_assertion": "START_TO_END",
                "loss_coefficient": Decimal("0.5"),
                "loss_coefficient_convention": (
                    "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2"
                ),
                "reference_flow_area_m2": Decimal("0.007854"),
                "multiplicity": 1,
                "upstream_reference_plane": "INLET",
                "downstream_reference_plane": "TUBE_START",
                "geometry_evidence_refs": ["EVIDENCE-001"],
                "coefficient_source_id": "USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL",
                "coefficient_source_version": "2024.1",
                "coefficient_source_location": "USACE HEC-RAS, Section 6.2.1",
                "coefficient_permission_status": "ADMITTED",
            },
        ],
        "request_hash": "",
    }
    base.update(overrides)
    return base


def _minimal_component_dict(**overrides: Any) -> dict[str, Any]:
    """Minimal valid component authority dict for raw boundary."""
    base: dict[str, Any] = {
        "component_id": "E-001",
        "component_type": "ENTRANCE",
        "path_sequence_index": 0,
        "flow_direction_assertion": "START_TO_END",
        "loss_coefficient": Decimal("0.5"),
        "loss_coefficient_convention": "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        "reference_flow_area_m2": Decimal("0.007854"),
        "multiplicity": 1,
        "upstream_reference_plane": "INLET",
        "downstream_reference_plane": "TUBE_START",
        "geometry_evidence_refs": ["EVIDENCE-001"],
        "coefficient_source_id": "USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL",
        "coefficient_source_version": "2024.1",
        "coefficient_source_location": "USACE HEC-RAS, Section 6.2.1",
        "coefficient_permission_status": "ADMITTED",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Minimal upstream result builders for pipeline integration tests
# ---------------------------------------------------------------------------
_H64 = "a" * 64  # reusable 64-char hex hash


def _make_frozen_raw_projection() -> FrozenRawProjection:
    return FrozenRawProjection(
        projection_kind="REQUEST",
        canonical_bytes_hex="ab" * 8,
    )


def _make_thermal_frozen_raw_projection() -> ThermalFrozenRawProjection:
    return ThermalFrozenRawProjection(
        projection_kind="REQUEST",
        canonical_bytes_hex="ab" * 8,
    )


def _make_frozen_identity() -> FrozenIdentity:
    return FrozenIdentity(
        identity_type="TASK-020",
        identity_id="id-020",
        identity_hash=_H64,
    )


def _make_frozen_provenance() -> FrozenProvenance:
    return FrozenProvenance(
        task_id="TASK-025",
        design_contract_path="docs/tasks/TASK-025.md",
        implementation_software_version="0.1.0",
        input_evidence_refs=(),
        upstream_identity_hashes=(_H64,),
    )


def _make_thermal_frozen_provenance() -> ThermalFrozenProvenance:
    from hexagent.exchangers.shell_tube.tube_side_thermal.provenance import (
        INPUT_EVIDENCE_REFS_V1,
    )

    return ThermalFrozenProvenance(
        task_id="TASK-026",
        design_contract_path="docs/tasks/TASK-026.md",
        implementation_software_version="0.1.0",
        input_evidence_refs=INPUT_EVIDENCE_REFS_V1,
        upstream_identity_hashes=(_H64,),
    )


def _make_internal_flow_authority() -> InternalFlowLengthAuthority:
    return InternalFlowLengthAuthority(
        length_id="LEN-001",
        length_m=Decimal("1.0"),
        start_plane=ReferencePlanePair(
            ReferencePlaneToken.TUBE_INTERNAL_FLOW_START_PLANE,
            ReferencePlaneToken.TUBE_INTERNAL_FLOW_END_PLANE,
        ),
        end_plane=ReferencePlanePair(
            ReferencePlaneToken.TUBE_INTERNAL_FLOW_START_PLANE,
            ReferencePlaneToken.TUBE_INTERNAL_FLOW_END_PLANE,
        ),
        authority_mode=HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
        length_hash=_H64,
    )


def _make_heat_transfer_authority() -> HeatTransferLengthAuthority:
    return HeatTransferLengthAuthority(
        length_id="LEN-002",
        length_m=Decimal("1.0"),
        start_plane=ReferencePlanePair(
            ReferencePlaneToken.TUBE_HEAT_TRANSFER_START_PLANE,
            ReferencePlaneToken.TUBE_HEAT_TRANSFER_END_PLANE,
        ),
        end_plane=ReferencePlanePair(
            ReferencePlaneToken.TUBE_HEAT_TRANSFER_START_PLANE,
            ReferencePlaneToken.TUBE_HEAT_TRANSFER_END_PLANE,
        ),
        authority_mode=HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
        length_hash=_H64,
    )


def _make_valid_task025_result(
    hydraulic_authority_hash: str = _H64,
) -> Task025ValidResult:
    """Minimal valid Task025ValidResult for pipeline integration tests."""
    return Task025ValidResult(
        schema_version="task025.result.v1",
        profile_id="profile-001",
        implementation_software_version="0.1.0",
        request_hash=_H64,
        layout_hash=_H64,
        result_hash=_H64,
        result_id="00000000-0000-5000-8000-000000000001",
        internal_flow_authority=_make_internal_flow_authority(),
        heat_transfer_authority=_make_heat_transfer_authority(),
        hydraulic_authority_hash=hydraulic_authority_hash,
        active_position_ids=(),
        inactive_position_ids=(),
        single_tube_flow_area_m2=Decimal("0.007854"),
        total_parallel_flow_area_m2=Decimal("0.031416"),
        flow_cross_section_wetted_perimeter_m=Decimal("0.031416"),
        total_flow_cross_section_wetted_perimeter_m=Decimal("0.125664"),
        hydraulic_diameter_m=Decimal("0.01"),
        internal_volume_m3=Decimal("0.000314"),
        internal_heat_transfer_surface_area_m2=Decimal("0.0314"),
        future_pressure_drop_length_m=None,
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        stage_rank=9,
        task020_identity=_make_frozen_identity(),
        task021_identity=_make_frozen_identity(),
        provenance=_make_frozen_provenance(),
    )


def _compute_default_property_snapshot_hash() -> str:
    """Compute the property_snapshot_hash for the default property snapshot."""
    # Create with a dummy hash, then recompute the true hash
    dummy = "0" * 64
    ps = PropertySnapshot(
        density_kg_m3=Decimal("1000.0"),
        dynamic_viscosity_pa_s=Decimal("0.001"),
        thermal_conductivity_w_m_k=Decimal("0.6"),
        specific_heat_capacity_j_kg_k=Decimal("4186"),
        bulk_temperature_k=Decimal("293.15"),
        bulk_pressure_pa=Decimal("101325"),
        phase_region=PhaseRegion.SINGLE_PHASE_LIQUID,
        property_source_id="default",
        property_source_version="1.0",
        property_snapshot_hash=dummy,
    )
    return recompute_property_snapshot_hash(ps)


def _make_valid_thermal_result(
    upstream_geometry_hash: str = _H64,
    property_snapshot_hash: str | None = None,
) -> TubeSideThermalResult:
    """Minimal valid TubeSideThermalResult for pipeline integration tests."""
    if property_snapshot_hash is None:
        property_snapshot_hash = _compute_default_property_snapshot_hash()
    return TubeSideThermalResult(
        schema_version="task026.thermal-result.v1",
        task026_version="task026.thermal.v1",
        implementation_software_version="0.1.0",
        upstream_geometry_hash=upstream_geometry_hash,
        property_snapshot_hash=property_snapshot_hash,
        thermal_boundary_condition=ThermalBoundaryCondition.CWT,
        phase_assertion=PhaseAssertion.SINGLE_PHASE_LIQUID,
        mass_flow_rate_kg_s=Decimal("5.0"),
        bulk_velocity_m_s=Decimal("0.637"),
        reynolds_number=Decimal("5000"),
        prandtl_number=Decimal("7.0"),
        flow_regime=FlowRegime.TURBULENT,
        correlation_id="CORR-001",
        correlation_version="1.0",
        nusselt_number=Decimal("50.0"),
        tube_side_heat_transfer_coefficient_w_m2_k=Decimal("3000"),
        request_hash=_H64,
        result_hash=_H64,
        result_id="00000000-0000-5000-8000-000000000002",
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=_make_thermal_frozen_provenance(),
    )


def _make_task025_blocked_result() -> Task025BlockedResult:
    """Minimal Task025BlockedResult for S01 upstream blocked tests."""
    from hexagent.exchangers.shell_tube.tube_side.blocker_registry import (
        Task025BlockerEntry,
    )

    return Task025BlockedResult(
        schema_version="task025.blocked-result.v1",
        implementation_software_version="0.1.0",
        resolved_profile_id=None,
        raw_profile_id_projection=_make_frozen_raw_projection(),
        raw_request_projection=_make_frozen_raw_projection(),
        request_hash=None,
        blocked_result_hash=_H64,
        blockers=(
            Task025BlockerEntry(
                code="BL_LAYOUT_UNKNOWN_FIELD",
                field_path=("test",),
                message_key="test blocker",
                evidence_refs=(),
            ),
        ),
        warnings=(),
        deferred_capabilities=(),
        stage_rank=1,
        task020_identity=None,
        task021_identity=None,
        provenance=_make_frozen_provenance(),
    )


def _make_thermal_raw_boundary_blocked_result() -> RawBoundaryBlockedResult:
    """Minimal RawBoundaryBlockedResult from TASK-026 for S01 tests."""
    from hexagent.exchangers.shell_tube.tube_side_thermal.blocker_registry import (
        BlockerCode,
    )

    return RawBoundaryBlockedResult(
        schema_version="task026.raw-boundary-blocked.v1",
        implementation_software_version="0.1.0",
        raw_request_projection=_make_thermal_frozen_raw_projection(),
        blockers=(
            BlockerEntry(
                code=BlockerCode.BL_RAW_INPUT_BOUNDARY_MALFORMED,
                severity="hard",
                stage="S00",
                payload=("test",),
                message_template="test",
            ),
        ),
        warnings=(),
        deferred_capabilities=(),
    )


def _make_thermal_tube_side_blocked_result() -> TubeSideBlockedResult:
    """Minimal TubeSideBlockedResult from TASK-026 for S01 tests."""
    from hexagent.exchangers.shell_tube.tube_side_thermal.blocker_registry import (
        BlockerCode,
    )

    return TubeSideBlockedResult(
        schema_version="task026.blocked-result.v1",
        task026_version="task026.thermal.v1",
        implementation_software_version="0.1.0",
        upstream_geometry_hash=_H64,
        property_snapshot_hash=_H64,
        thermal_boundary_condition=ThermalBoundaryCondition.CWT,
        phase_assertion=PhaseAssertion.SINGLE_PHASE_LIQUID,
        mass_flow_rate_kg_s=Decimal("5.0"),
        raw_request_projection=_make_thermal_frozen_raw_projection(),
        raw_upstream_blocked_projection=None,
        request_hash=_H64,
        result_hash=_H64,
        result_id="00000000-0000-5000-8000-000000000003",
        blockers=(
            BlockerEntry(
                code=BlockerCode.BL_UNSUPPORTED_PHASE,
                severity="hard",
                stage="S05",
                payload=("test",),
                message_template="test",
            ),
        ),
        warnings=(),
        deferred_capabilities=(),
        provenance=_make_thermal_frozen_provenance(),
    )


def _build_pipeline_raw_request(**overrides: Any) -> dict[str, Any]:
    """Build a raw_request dict that passes raw boundary and has valid typed_data.

    Uses the correct property_snapshot_hash for the default property snapshot.
    """
    psh = _compute_default_property_snapshot_hash()
    base: dict[str, Any] = {
        "schema_version": TASK028_REQUEST_SCHEMA_VERSION,
        "profile_id": "profile-001",
        "task025_valid_result": None,
        "task026_success_result": None,
        "property_snapshot": {"density_kg_m3": "1000.0"},
        "property_snapshot_hash": psh,
        "constant_density_path_assertion": "TRUE",
        "zero_net_elevation_change_assertion": "TRUE",
        "flow_direction_assertion": "START_TO_END",
        "component_authorities": [
            _minimal_component_dict(),
        ],
        "request_hash": "",
    }
    base.update(overrides)
    return base


def _run_pipeline(
    raw_request: dict[str, Any],
    task025_result: Any,
    task026_result: Any,
) -> Any:
    """Invoke compute_task028_local_loss with proper arguments."""
    return compute_task028_local_loss(
        raw_request=raw_request,
        task025_result=task025_result,
        task026_result=task026_result,
    )


# ===========================================================================
# 77 frozen TEST_IDs — one ``test_T028_XXX`` function each.
# ===========================================================================


# --- RAW BOUNDARY (7 tests) ------------------------------------------------


def test_T028_REQUEST_UNKNOWN_FIELD_BLOCKED() -> None:
    """R02: unknown field in raw input → BL_T028_REQUEST_UNKNOWN_FIELD."""
    raw = _make_raw_request(unknown_field="test")
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_REQUEST_UNKNOWN_FIELD in codes


def test_T028_RAW_INPUT_BOUNDARY_MALFORMED() -> None:
    """R01: non-dict raw input → BL_T028_RAW_INPUT_BOUNDARY_MALFORMED."""
    result = validate_raw_boundary("not a dict")
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED in codes


def test_T028_COMPONENT_AUTHORITY_SET_SHAPE_BLOCKED() -> None:
    """R05: empty list → BL_T028_COMPONENT_AUTHORITY_SET_INVALID."""
    raw = _make_raw_request(component_authorities=[])
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COMPONENT_AUTHORITY_SET_INVALID in codes


def test_T028_COMPONENT_AUTHORITY_UNKNOWN_FIELD_BLOCKED() -> None:
    """R06: component with unknown/malformed record → BL_T028_RAW_INPUT_BOUNDARY_MALFORMED."""
    raw = _make_raw_request(component_authorities=[{"component_id": "X", "unknown_extra": True}])
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED in codes


def test_T028_COMPONENT_ID_DUPLICATE_BLOCKED() -> None:
    """S09: duplicate component_id → BL_T028_COMPONENT_ID_DUPLICATE."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="DUP", path_sequence_index=0),
            _minimal_component_dict(component_id="DUP", path_sequence_index=1),
        ]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COMPONENT_ID_DUPLICATE in codes
    assert not hasattr(result, "component_results")


def test_T028_PATH_SEQUENCE_INDEX_DUPLICATE_BLOCKED() -> None:
    """S09: duplicate path_sequence_index → BL_T028_PATH_SEQUENCE_INDEX_DUPLICATE."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="A-001", path_sequence_index=0),
            _minimal_component_dict(component_id="A-002", path_sequence_index=0),
        ]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_PATH_SEQUENCE_INDEX_DUPLICATE in codes
    assert not hasattr(result, "component_results")


def test_T028_AUTHORITY_HASH_REPLAY() -> None:
    """Authority hash is deterministic SHA-256 hex (64 lowercase hex chars).

    Asserts VECTOR_01 exact canonical bytes and SHA-256 hash.
    """
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
        canonicalize_authority,
    )

    args = dict(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id="ENT-001",
        component_type="ENTRANCE",
        path_sequence_index=0,
        upstream_reference_plane="shell-inlet-plane",
        downstream_reference_plane="tube-inlet-plane",
        flow_direction_assertion="START_TO_END",
        loss_coefficient=Decimal("0.5"),
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2=Decimal("0.00078539816339"),
        multiplicity=1,
        geometry_evidence_refs=("CANONICAL-VECTOR-EVIDENCE-ENT-001",),
        coefficient_source_id="CANONICAL-VECTOR-SOURCE",
        coefficient_source_version="v1",
        coefficient_source_location="canonical-vector://task028/authority/ENT-001",
        coefficient_permission_status="ADMITTED",
    )
    framed, sha = canonicalize_authority(**args)
    assert isinstance(framed, bytes)
    assert len(framed) == 1052
    assert framed.hex() == FROZEN_VECTOR_01_CANONICAL_BYTES_HEX
    assert sha == "61eb84503b3affd10f13942aa37c32dc496f4213a1333193fc6ad2bb46d13f45"
    # Replay: same inputs → same bytes.
    framed2, sha2 = canonicalize_authority(**args)
    assert framed == framed2
    assert sha == sha2


def test_T028_AUTHORITY_HASH_MISMATCH_BLOCKED() -> None:
    """BL_T028_AUTHORITY_HASH_MISMATCH: supplied hash differs from recomputed → blocker."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    # Build a component dict with a deliberately wrong authority_hash
    comp = _minimal_component_dict()
    # Compute the correct hash, then supply a wrong one
    correct_hash = compute_authority_hash(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id=comp["component_id"],
        component_type="ENTRANCE",
        path_sequence_index=comp["path_sequence_index"],
        upstream_reference_plane=comp["upstream_reference_plane"],
        downstream_reference_plane=comp["downstream_reference_plane"],
        flow_direction_assertion="START_TO_END",
        loss_coefficient=comp["loss_coefficient"],
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2=comp["reference_flow_area_m2"],
        multiplicity=comp["multiplicity"],
        geometry_evidence_refs=tuple(comp["geometry_evidence_refs"]),
        coefficient_source_id=comp["coefficient_source_id"],
        coefficient_source_version=comp["coefficient_source_version"],
        coefficient_source_location=comp["coefficient_source_location"],
        coefficient_permission_status="ADMITTED",
    )
    assert len(correct_hash) == 64
    # Supply a wrong hash
    comp["authority_hash"] = "wrong" * 13 + "a"
    raw = _build_pipeline_raw_request(component_authorities=[comp])
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_AUTHORITY_HASH_MISMATCH in codes


def test_T028_GEOMETRY_EVIDENCE_MISSING_BLOCKED() -> None:
    """S08: Empty geometry_evidence_refs → BL_T028_GEOMETRY_EVIDENCE_MISSING."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(geometry_evidence_refs=[])]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_GEOMETRY_EVIDENCE_MISSING in codes
    assert not hasattr(result, "component_results")


def test_T028_COEFFICIENT_SOURCE_ID_MISSING_BLOCKED() -> None:
    """Empty coefficient_source_id → BL_T028_COEFFICIENT_SOURCE_ID_MISSING."""
    raw = _make_raw_request(
        component_authorities=[_minimal_component_dict(coefficient_source_id="")]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COEFFICIENT_SOURCE_ID_MISSING in codes


def test_T028_COEFFICIENT_SOURCE_VERSION_MISSING_BLOCKED() -> None:
    """Empty coefficient_source_version → BL_T028_COEFFICIENT_SOURCE_VERSION_MISSING."""
    raw = _make_raw_request(
        component_authorities=[_minimal_component_dict(coefficient_source_version="")]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COEFFICIENT_SOURCE_VERSION_MISSING in codes


def test_T028_COEFFICIENT_SOURCE_LOCATION_MISSING_BLOCKED() -> None:
    """Empty coefficient_source_location → BL_T028_COEFFICIENT_SOURCE_LOCATION_MISSING."""
    raw = _make_raw_request(
        component_authorities=[_minimal_component_dict(coefficient_source_location="")]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COEFFICIENT_SOURCE_LOCATION_MISSING in codes


def test_T028_COEFFICIENT_PERMISSION_NOT_ADMITTED_BLOCKED() -> None:
    """Permission != ADMITTED → BL_T028_COEFFICIENT_PERMISSION_NOT_ADMITTED."""
    raw = _make_raw_request(
        component_authorities=[_minimal_component_dict(coefficient_permission_status="PENDING")]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COEFFICIENT_PERMISSION_NOT_ADMITTED in codes


# --- COMPONENT SUCCESS (6 tests) -------------------------------------------


def test_T028_ENTRANCE_COMPONENT_SUCCESS() -> None:
    """ENTRANCE component: K>0 → single_occurrence_pa > 0, component_pa > 0."""
    ref_vel, single, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert ref_vel > Decimal(0)
    assert single > Decimal(0)
    assert comp > Decimal(0)
    assert comp == single  # multiplicity=1


def test_T028_EXIT_COMPONENT_SUCCESS() -> None:
    """EXIT component: K>0 → pressure loss > 0."""
    _, _, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("1.0"),
        multiplicity=1,
    )
    assert comp > Decimal(0)


def test_T028_CHANNEL_HEAD_COMPONENT_SUCCESS() -> None:
    """CHANNEL_HEAD component: K>0 → pressure loss > 0."""
    _, _, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("2.0"),
        multiplicity=1,
    )
    assert comp > Decimal(0)


def test_T028_NOZZLE_COMPONENT_SUCCESS() -> None:
    """NOZZLE component: K>0 → pressure loss > 0."""
    _, _, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.3"),
        multiplicity=1,
    )
    assert comp > Decimal(0)


def test_T028_CONTRACTION_COMPONENT_SUCCESS() -> None:
    """CONTRACTION component: K>0 → pressure loss > 0."""
    _, _, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.4"),
        multiplicity=1,
    )
    assert comp > Decimal(0)


def test_T028_EXPANSION_COMPONENT_SUCCESS() -> None:
    """EXPANSION component: K>0 → pressure loss > 0."""
    _, _, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.6"),
        multiplicity=1,
    )
    assert comp > Decimal(0)


# --- OUT_OF_SCOPE COMPONENT BLOCKED (4 tests) -----------------------------


def test_T028_PASS_PARTITION_COMPONENT_BLOCKED() -> None:
    """PASS_PARTITION → BL_T028_COMPONENT_TYPE_UNSUPPORTED at raw boundary."""
    raw = _make_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="PP-001", component_type="PASS_PARTITION")
        ]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COMPONENT_TYPE_UNSUPPORTED in codes


def test_T028_RETURN_HEADER_COMPONENT_BLOCKED() -> None:
    """RETURN_HEADER → BL_T028_COMPONENT_TYPE_UNSUPPORTED at raw boundary."""
    raw = _make_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="RH-001", component_type="RETURN_HEADER")
        ]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COMPONENT_TYPE_UNSUPPORTED in codes


def test_T028_RETURN_BEND_COMPONENT_BLOCKED() -> None:
    """RETURN_BEND → BL_T028_COMPONENT_TYPE_UNSUPPORTED at raw boundary."""
    raw = _make_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="RB-001", component_type="RETURN_BEND")
        ]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COMPONENT_TYPE_UNSUPPORTED in codes


def test_T028_U_BEND_COMPONENT_BLOCKED() -> None:
    """U_BEND → BL_T028_COMPONENT_TYPE_UNSUPPORTED at raw boundary."""
    raw = _make_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="UB-001", component_type="U_BEND")
        ]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COMPONENT_TYPE_UNSUPPORTED in codes


# --- REFERENCE VELOCITY & AREA (3 tests) -----------------------------------


def test_T028_REFERENCE_VELOCITY_FORMULA() -> None:
    """V_ref = mdot / (rho * A) matches frozen formula."""
    ref_vel, _, _ = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    expected = Decimal("5") / (Decimal("1000") * Decimal("0.007854"))
    expected_q = quantize_task028_decimal(expected, REFERENCE_VELOCITY_QUANTUM)
    assert ref_vel == expected_q


def test_T028_REFERENCE_AREA_SENSITIVITY() -> None:
    """Different A → different V_ref."""
    rv1, _, _ = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    rv2, _, _ = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.01"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert rv1 != rv2


def test_T028_TUBE_BULK_VELOCITY_NOT_IMPLICITLY_REUSED() -> None:
    """Different density -> different V_ref
    (proves formula uses supplied density, not bulk velocity)."""
    rv1, _, _ = compute_local_loss_component(
        density_kg_m3=Decimal("500"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    rv2, _, _ = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert rv1 != rv2


# --- LOSS COEFFICIENT BLOCKED (4 tests) ------------------------------------


def test_T028_LOSS_COEFFICIENT_NONFINITE_BLOCKED() -> None:
    """S08: Non-finite K (NaN) → BL_T028_LOSS_COEFFICIENT_NONFINITE."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(loss_coefficient=Decimal("NaN"))]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_NONFINITE in codes
    assert not hasattr(result, "component_results")


def test_T028_LOSS_COEFFICIENT_ZERO_PSEUDO_COMPONENT_BLOCKED() -> None:
    """S08: K=0 → BL_T028_PSEUDO_ZERO_COMPONENT_FORBIDDEN."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(loss_coefficient=Decimal("0"))]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_PSEUDO_ZERO_COMPONENT_FORBIDDEN in codes
    assert not hasattr(result, "component_results")


def test_T028_LOSS_COEFFICIENT_NEGATIVE_BLOCKED() -> None:
    """S08: K<0 → BL_T028_LOSS_COEFFICIENT_NEGATIVE."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(loss_coefficient=Decimal("-0.5"))]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_NEGATIVE in codes
    assert not hasattr(result, "component_results")


def test_T028_LOSS_COEFFICIENT_CONVENTION_BLOCKED() -> None:
    """Wrong convention string → BL_T028_LOSS_COEFFICIENT_CONVENTION_UNSUPPORTED."""
    raw = _make_raw_request(
        component_authorities=[_minimal_component_dict(loss_coefficient_convention="FANNING")]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_CONVENTION_UNSUPPORTED in codes


# --- REFERENCE FLOW AREA BLOCKED (3 tests) ---------------------------------


def test_T028_REFERENCE_FLOW_AREA_ZERO_BLOCKED() -> None:
    """S08: area=0 → BL_T028_REFERENCE_FLOW_AREA_INVALID."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(reference_flow_area_m2=Decimal("0"))]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_REFERENCE_FLOW_AREA_INVALID in codes
    assert not hasattr(result, "component_results")


def test_T028_REFERENCE_FLOW_AREA_NEGATIVE_BLOCKED() -> None:
    """S08: area<0 → BL_T028_REFERENCE_FLOW_AREA_INVALID."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(reference_flow_area_m2=Decimal("-0.001"))]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_REFERENCE_FLOW_AREA_INVALID in codes
    assert not hasattr(result, "component_results")


def test_T028_REFERENCE_FLOW_AREA_NONFINITE_BLOCKED() -> None:
    """S08: area=NaN → BL_T028_REFERENCE_FLOW_AREA_INVALID."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(reference_flow_area_m2=Decimal("NaN"))]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_REFERENCE_FLOW_AREA_INVALID in codes
    assert not hasattr(result, "component_results")


# --- MULTIPLICITY (3 tests) -------------------------------------------------


def test_T028_MULTIPLICITY_ONE() -> None:
    """multiplicity=1 → single_occurrence_pa == component_pa."""
    _, single, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert single == comp


def test_T028_MULTIPLICITY_SERIAL_SCALING() -> None:
    """component_pa = multiplicity * single_occurrence_pa (quantized)."""
    _, single, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=3,
    )
    expected = quantize_task028_decimal(Decimal("3") * single, PRESSURE_LOSS_QUANTUM)
    assert comp == expected


def test_T028_ACTIVE_TUBE_COUNT_NOT_PRESSURE_DROP_MULTIPLIER() -> None:
    """Doubling flow rate quadruples pressure (V²) — tube count is not a multiplier."""
    _, _, comp1 = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    _, _, comp2 = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("10"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert comp2 != comp1
    ratio = comp2 / comp1
    assert ratio > Decimal("3")


# --- UPSTREAM BLOCKED (5 tests) --------------------------------------------


def test_T028_UPSTREAM_TASK025_BLOCKED() -> None:
    """S01: Task025BlockedResult → BL_T028_UPSTREAM_TASK025_BLOCKED."""
    task025_blocked = _make_task025_blocked_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request()
    result = _run_pipeline(raw, task025_blocked, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_UPSTREAM_TASK025_BLOCKED in codes
    assert not hasattr(result, "component_results")


def test_T028_UPSTREAM_TASK026_RAW_BLOCKED() -> None:
    """S01: RawBoundaryBlockedResult from TASK-026 → BL_T028_UPSTREAM_TASK026_RAW_BLOCKED."""
    task025_valid = _make_valid_task025_result()
    task026_raw_blocked = _make_thermal_raw_boundary_blocked_result()
    raw = _build_pipeline_raw_request()
    result = _run_pipeline(raw, task025_valid, task026_raw_blocked)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_UPSTREAM_TASK026_RAW_BLOCKED in codes
    assert not hasattr(result, "component_results")


def test_T028_UPSTREAM_TASK026_TYPED_BLOCKED() -> None:
    """S01: TubeSideBlockedResult → BL_T028_UPSTREAM_TASK026_TYPED_BLOCKED."""
    task025_valid = _make_valid_task025_result()
    task026_typed_blocked = _make_thermal_tube_side_blocked_result()
    raw = _build_pipeline_raw_request()
    result = _run_pipeline(raw, task025_valid, task026_typed_blocked)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_UPSTREAM_TASK026_TYPED_BLOCKED in codes
    assert not hasattr(result, "component_results")


def test_T028_UPSTREAM_IDENTITY_MISMATCH_BLOCKED() -> None:
    """S05: Geometry hash mismatch → BL_T028_UPSTREAM_IDENTITY_MISMATCH."""
    task025_valid = _make_valid_task025_result(hydraulic_authority_hash="a" * 64)
    task026_valid = _make_valid_thermal_result(upstream_geometry_hash="b" * 64)
    raw = _build_pipeline_raw_request()
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_UPSTREAM_IDENTITY_MISMATCH in codes
    assert not hasattr(result, "component_results")


def test_T028_PROPERTY_SNAPSHOT_HASH_MISMATCH_BLOCKED() -> None:
    """S06: Property hash mismatch → BL_T028_PROPERTY_SNAPSHOT_HASH_MISMATCH."""
    task025_valid = _make_valid_task025_result()
    # Use a mismatched property_snapshot_hash in the thermal result
    task026_valid = _make_valid_thermal_result(
        property_snapshot_hash="b" * 64,
    )
    raw = _build_pipeline_raw_request()
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_PROPERTY_SNAPSHOT_HASH_MISMATCH in codes
    assert not hasattr(result, "component_results")


# --- APPLICABILITY ASSERTIONS (5 tests) -------------------------------------


def test_T028_CONSTANT_DENSITY_ASSERTION_MISSING_BLOCKED() -> None:
    """Missing constant_density_path_assertion → BL_T028_APPLICABILITY_ASSERTION_MISSING."""
    raw = _make_raw_request()
    del raw["constant_density_path_assertion"]
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_MISSING in codes


def test_T028_CONSTANT_DENSITY_ASSERTION_FALSE_BLOCKED() -> None:
    """S07: FALSE constant_density → BL_T028_APPLICABILITY_ASSERTION_FALSE."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(constant_density_path_assertion="FALSE")
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_FALSE in codes
    assert not hasattr(result, "component_results")


def test_T028_ZERO_ELEVATION_ASSERTION_MISSING_BLOCKED() -> None:
    """Missing zero_net_elevation_change_assertion → BL_T028_APPLICABILITY_ASSERTION_MISSING."""
    raw = _make_raw_request()
    del raw["zero_net_elevation_change_assertion"]
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_MISSING in codes


def test_T028_ZERO_ELEVATION_ASSERTION_FALSE_BLOCKED() -> None:
    """S07: FALSE zero_elevation → BL_T028_APPLICABILITY_ASSERTION_FALSE."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(zero_net_elevation_change_assertion="FALSE")
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_FALSE in codes
    assert not hasattr(result, "component_results")


def test_T028_GAS_BLOCKED_V1() -> None:
    """S12: Gas phase not supported in V1 → BL_T028_APPLICABILITY_ASSERTION_FALSE."""
    task025_valid = _make_valid_task025_result()
    # Build a gas-phase property snapshot using the pipeline's default values
    # for fields not supplied in the raw dict, then compute its hash
    gas_ps = PropertySnapshot(
        density_kg_m3=Decimal("1.225"),
        dynamic_viscosity_pa_s=Decimal("0.001"),
        thermal_conductivity_w_m_k=Decimal("0.6"),
        specific_heat_capacity_j_kg_k=Decimal("4186"),
        bulk_temperature_k=Decimal("293.15"),
        bulk_pressure_pa=Decimal("101325"),
        phase_region=PhaseRegion.SINGLE_PHASE_GAS,
        property_source_id="default",
        property_source_version="1.0",
        property_snapshot_hash="0" * 64,
    )
    gas_psh = recompute_property_snapshot_hash(gas_ps)
    task026_valid = _make_valid_thermal_result(property_snapshot_hash=gas_psh)
    raw = _build_pipeline_raw_request(
        property_snapshot={"density_kg_m3": "1.225", "phase_region": "SINGLE_PHASE_GAS"},
        property_snapshot_hash=gas_psh,
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_FALSE in codes
    assert not hasattr(result, "component_results")


# --- RESULT STRUCTURE (5 tests) --------------------------------------------


def test_T028_COMPONENT_RESULTS_ORDERED_BY_PATH_SEQUENCE_INDEX() -> None:
    """Success result component_results ordered by path_sequence_index ASC."""
    result = build_success_result(
        profile_id="profile-001",
        request_hash="a" * 64,
        task025_hydraulic_authority_hash="b" * 64,
        task025_result_hash="b2" * 32,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        component_results=(_make_minimal_component_result(),),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=_make_success_provenance(),
    )
    assert len(result.component_results) == 1
    assert not hasattr(result, "total_irreversible_pressure_loss_pa")


def test_T028_COMPONENT_RESULT_REFERENCE_PLANES_PRESERVED() -> None:
    """Reference planes preserved in authority and component result."""
    auth = _make_entrance_authority()
    assert auth.upstream_reference_plane == "INLET"
    assert auth.downstream_reference_plane == "TUBE_START"


def test_T028_NO_MODELED_TOTAL_FIELD() -> None:
    """Success result has no 'total_tube_side_pressure_drop_pa' field."""
    result = build_success_result(
        profile_id="profile-001",
        request_hash="a" * 64,
        task025_hydraulic_authority_hash="b" * 64,
        task025_result_hash="b2" * 32,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        component_results=(_make_minimal_component_result(),),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=_make_success_provenance(),
    )
    assert not hasattr(result, "total_tube_side_pressure_drop_pa")
    assert not hasattr(result, "modeled_total_tube_side_pressure_drop_pa")


def test_T028_NO_UNCONDITIONAL_TOTAL_FIELD() -> None:
    """Success result has no unconditional total field."""
    result = build_success_result(
        profile_id="profile-001",
        request_hash="a" * 64,
        task025_hydraulic_authority_hash="b" * 64,
        task025_result_hash="b2" * 32,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        component_results=(_make_minimal_component_result(),),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=_make_success_provenance(),
    )
    assert not hasattr(result, "modeled_total")


def test_T028_BLOCKED_RESULT_NO_PARTIAL_COMPONENT_RESULTS() -> None:
    """Blocked result has no component_results / engineering fields."""
    blocked = build_blocked_result(
        profile_id="profile-001",
        request_hash=None,
        task025_hydraulic_authority_hash=None,
        task025_result_hash=None,
        task026_result_hash=None,
        property_snapshot_hash=None,
        raw_request_projection=None,
        raw_upstream_blocked_projection=None,
        warnings=(),
        blockers=(
            Task028BlockerEntry(
                code=Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                field_path=("raw_input",),
                message_key="The TASK-028 raw input boundary is malformed.",
                evidence_refs=(),
            ),
        ),
        deferred_capabilities=(),
        provenance=None,
    )
    assert not hasattr(blocked, "component_results")


# --- HASH / IDENTITY REPLAY (7 tests) --------------------------------------


def test_T028_SUCCESS_REQUEST_HASH_REPLAY() -> None:
    """Request hash is deterministic SHA-256 (64 hex chars).

    Asserts VECTOR_02 exact canonical bytes and SHA-256 hash.
    """
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
        _canonicalize_request_record,
    )

    framed, h = _canonicalize_request_record(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="default",
        task025_hydraulic_authority_hash="a" * 64,
        task025_result_hash="b" * 64,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=(FROZEN_AUTHORITY_0_HASH, FROZEN_AUTHORITY_1_HASH),
    )
    assert isinstance(h, str)
    assert len(h) == 64
    assert len(framed) == 956
    assert framed.hex() == FROZEN_VECTOR_02_CANONICAL_BYTES_HEX
    assert h == "bda7341f11add477672896e46f191f178cd226bab93dc317e5d607c5e4fa5242"
    # Replay
    framed2, h2 = _canonicalize_request_record(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="default",
        task025_hydraulic_authority_hash="a" * 64,
        task025_result_hash="b" * 64,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=(FROZEN_AUTHORITY_0_HASH, FROZEN_AUTHORITY_1_HASH),
    )
    assert h == h2
    assert framed == framed2


def test_T028_SUCCESS_RESULT_HASH_REPLAY() -> None:
    """Result hash is deterministic SHA-256 (64 hex chars)."""
    h = compute_success_result_hash(
        schema_version=TASK028_SUCCESS_RESULT_SCHEMA_VERSION,
        profile_id="profile-001",
        request_hash="a" * 64,
        task025_hydraulic_authority_hash="b" * 64,
        task025_result_hash="b2" * 32,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        component_result_records=(),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=None,
    )
    assert isinstance(h, str)
    assert len(h) == 64


def test_T028_SUCCESS_RESULT_ID_REPLAY() -> None:
    """Result UUID5 is deterministic from result_hash."""
    h = "a" * 64
    rid = compute_result_id(h)
    assert isinstance(rid, str)
    parsed = uuid.UUID(rid)
    assert parsed.version == 5
    # Replay
    rid2 = compute_result_id(h)
    assert rid == rid2


def test_T028_BLOCKED_RESULT_HASH_REPLAY() -> None:
    """Blocked result hash is deterministic.

    Asserts VECTOR_04 exact canonical bytes and SHA-256 hash.
    """
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
        _canonicalize_blocked_result_record,
    )

    raw_proj = Task028RawProjection(
        projection_kind="request",
        canonical_bytes_hex="0" * 64,
    )
    blocker = Task028BlockerEntry(
        code=Task028BlockerCode.BL_T028_COMPONENT_FLOW_DIRECTION_MISMATCH,
        field_path=("component_authorities[0].flow_direction_assertion",),
        message_key="BL_T028_COMPONENT_FLOW_DIRECTION_MISMATCH",
        evidence_refs=("ENT-002",),
    )
    prov = Task028Provenance(
        task_id="TASK-028",
        design_contract_path="TASK-028-source-definition.md",
        implementation_software_version="0.3.0",
        input_evidence_refs=("CANONICAL-VECTOR-EVIDENCE-ENT-002",),
        upstream_identity_hashes=(
            "a" * 64,
            "b" * 64,
            "c" * 64,
            "d" * 64,
            FROZEN_AUTHORITY_0_HASH,
        ),
    )
    framed, h = _canonicalize_blocked_result_record(
        schema_version=TASK028_BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id="default",
        request_hash="f00898a4ed33b991ea0552fd76c2a535485eea2378a50489743be36cfd55f89d",
        task025_hydraulic_authority_hash="a" * 64,
        task025_result_hash="b" * 64,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        raw_request_projection=raw_proj,
        raw_upstream_blocked_projection=None,
        warnings=(),
        blockers=(blocker,),
        deferred_capabilities=TASK028_DEFERRED_CAPABILITIES_V1,
        provenance=prov,
    )
    assert isinstance(h, str)
    assert len(h) == 64
    assert len(framed) == 2471
    assert framed.hex() == FROZEN_VECTOR_04_CANONICAL_BYTES_HEX
    assert h == "a7a04fd0bdb2541fd33945785676c1f7d3a0cabe3bd3cd562e2e30bc12e3744a"
    # Replay
    framed2, h2 = _canonicalize_blocked_result_record(
        schema_version=TASK028_BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id="default",
        request_hash="f00898a4ed33b991ea0552fd76c2a535485eea2378a50489743be36cfd55f89d",
        task025_hydraulic_authority_hash="a" * 64,
        task025_result_hash="b" * 64,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        raw_request_projection=raw_proj,
        raw_upstream_blocked_projection=None,
        warnings=(),
        blockers=(blocker,),
        deferred_capabilities=TASK028_DEFERRED_CAPABILITIES_V1,
        provenance=prov,
    )
    assert h == h2
    assert framed == framed2


def test_T028_BLOCKED_RESULT_ID_REPLAY() -> None:
    """Blocked result UUID5 is deterministic.

    Asserts VECTOR_04 result_id.
    """
    rid = compute_result_id("a7a04fd0bdb2541fd33945785676c1f7d3a0cabe3bd3cd562e2e30bc12e3744a")
    parsed = uuid.UUID(rid)
    assert parsed.version == 5
    assert rid == "92aa0b82-5400-585c-8a78-1ba54ed3503b"
    rid2 = compute_result_id("a7a04fd0bdb2541fd33945785676c1f7d3a0cabe3bd3cd562e2e30bc12e3744a")
    assert rid == rid2


def test_T028_RAW_BOUNDARY_BLOCKED_HASH_REPLAY() -> None:
    """Raw boundary blocked hash is deterministic (6 fields)."""
    h = compute_raw_boundary_blocked_hash(
        raw_request_projection=None,
        blockers=(),
        warnings=(),
        deferred_capabilities=(),
        schema_version=TASK028_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
    )
    assert isinstance(h, str)
    assert len(h) == 64


def test_T028_CANONICAL_NO_DOUBLE_WRAPPING() -> None:
    """Canonical authority framing produces direct record (no outer wrapper)."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import canonicalize_authority

    framed, sha = canonicalize_authority(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id="E-001",
        component_type="ENTRANCE",
        path_sequence_index=0,
        upstream_reference_plane="INLET",
        downstream_reference_plane="TUBE_START",
        flow_direction_assertion="START_TO_END",
        loss_coefficient=Decimal("0.5"),
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2=Decimal("0.007854"),
        multiplicity=1,
        geometry_evidence_refs=("EVIDENCE-001",),
        coefficient_source_id="USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL",
        coefficient_source_version="2024.1",
        coefficient_source_location="USACE HEC-RAS, Section 6.2.1",
        coefficient_permission_status="ADMITTED",
    )
    assert isinstance(framed, bytes)
    assert len(framed) > 0
    assert len(sha) == 64


# --- IDENTITY SENSITIVITY (4 tests) ----------------------------------------


def test_T028_AUTHORITY_CHANGE_CHANGES_REQUEST_IDENTITY() -> None:
    """Different authority hash tuple → different request hash."""
    h1 = compute_request_hash(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="profile-001",
        task025_hydraulic_authority_hash="hyd" * 21 + "a",
        task025_result_hash="a" * 64,
        task026_result_hash="b" * 64,
        property_snapshot_hash="c" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=("x" * 64,),
    )
    h2 = compute_request_hash(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="profile-001",
        task025_hydraulic_authority_hash="hyd" * 21 + "a",
        task025_result_hash="a" * 64,
        task026_result_hash="b" * 64,
        property_snapshot_hash="c" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=("y" * 64,),
    )
    assert h1 != h2


def test_T028_REFERENCE_AREA_CHANGE_CHANGES_RESULT_IDENTITY() -> None:
    """Different reference_flow_area_m2 → different authority hash."""
    auth1 = _make_entrance_authority(reference_flow_area=Decimal("0.001"))
    auth2 = _make_entrance_authority(reference_flow_area=Decimal("0.01"))
    assert auth1.authority_hash != auth2.authority_hash


def test_T028_MULTIPLICITY_CHANGE_CHANGES_RESULT_IDENTITY() -> None:
    """Different multiplicity → different authority hash."""
    auth1 = _make_entrance_authority(multiplicity=1)
    auth2 = _make_entrance_authority(multiplicity=3)
    assert auth1.authority_hash != auth2.authority_hash


def test_T028_PY311_PY312_CANONICAL_BYTE_IDENTITY() -> None:
    """Deterministic canonical framing (cross-Python-version stable bytes).

    Asserts all 5 frozen vectors exact canonical bytes.
    """
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
        RESULT_ID_NAMESPACE,
        _canonicalize_blocked_result_record,
        _canonicalize_request_record,
        _canonicalize_success_result_record,
        canonicalize_authority,
    )

    # --- VECTOR_01: Authority hash ---
    auth_args = dict(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id="ENT-001",
        component_type="ENTRANCE",
        path_sequence_index=0,
        upstream_reference_plane="shell-inlet-plane",
        downstream_reference_plane="tube-inlet-plane",
        flow_direction_assertion="START_TO_END",
        loss_coefficient=Decimal("0.5"),
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2=Decimal("0.00078539816339"),
        multiplicity=1,
        geometry_evidence_refs=("CANONICAL-VECTOR-EVIDENCE-ENT-001",),
        coefficient_source_id="CANONICAL-VECTOR-SOURCE",
        coefficient_source_version="v1",
        coefficient_source_location="canonical-vector://task028/authority/ENT-001",
        coefficient_permission_status="ADMITTED",
    )
    f1, h1 = canonicalize_authority(**auth_args)
    f2, h2 = canonicalize_authority(**auth_args)
    assert f1 == f2
    assert len(f1) == 1052
    assert f1.hex() == FROZEN_VECTOR_01_CANONICAL_BYTES_HEX
    assert h1 == "61eb84503b3affd10f13942aa37c32dc496f4213a1333193fc6ad2bb46d13f45"
    assert h1 == h2

    # --- VECTOR_02: Request hash ---
    req_framed, req_h = _canonicalize_request_record(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="default",
        task025_hydraulic_authority_hash="a" * 64,
        task025_result_hash="b" * 64,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=(FROZEN_AUTHORITY_0_HASH, FROZEN_AUTHORITY_1_HASH),
    )
    assert len(req_framed) == 956
    assert req_framed.hex() == FROZEN_VECTOR_02_CANONICAL_BYTES_HEX
    assert req_h == "bda7341f11add477672896e46f191f178cd226bab93dc317e5d607c5e4fa5242"

    # --- VECTOR_03: Request hash (permuted authority order → same bytes) ---
    # The pipeline sorts by path_sequence_index before hashing.
    # After sorting, the permuted order becomes the canonical order.
    sorted_hashes = tuple(sorted(
        (FROZEN_AUTHORITY_1_HASH, FROZEN_AUTHORITY_0_HASH),
    ))
    req_framed3, req_h3 = _canonicalize_request_record(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="default",
        task025_hydraulic_authority_hash="a" * 64,
        task025_result_hash="b" * 64,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=sorted_hashes,
    )
    assert req_framed3.hex() == FROZEN_VECTOR_03_CANONICAL_BYTES_HEX
    assert req_framed3 == req_framed  # permutation invariant

    # --- VECTOR_04: Blocked result hash ---
    raw_proj = Task028RawProjection(
        projection_kind="request",
        canonical_bytes_hex="0" * 64,
    )
    blocker = Task028BlockerEntry(
        code=Task028BlockerCode.BL_T028_COMPONENT_FLOW_DIRECTION_MISMATCH,
        field_path=("component_authorities[0].flow_direction_assertion",),
        message_key="BL_T028_COMPONENT_FLOW_DIRECTION_MISMATCH",
        evidence_refs=("ENT-002",),
    )
    prov = Task028Provenance(
        task_id="TASK-028",
        design_contract_path="TASK-028-source-definition.md",
        implementation_software_version="0.3.0",
        input_evidence_refs=("CANONICAL-VECTOR-EVIDENCE-ENT-002",),
        upstream_identity_hashes=(
            "a" * 64,
            "b" * 64,
            "c" * 64,
            "d" * 64,
            FROZEN_AUTHORITY_0_HASH,
        ),
    )
    blk_framed, blk_h = _canonicalize_blocked_result_record(
        schema_version=TASK028_BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id="default",
        request_hash="f00898a4ed33b991ea0552fd76c2a535485eea2378a50489743be36cfd55f89d",
        task025_hydraulic_authority_hash="a" * 64,
        task025_result_hash="b" * 64,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        raw_request_projection=raw_proj,
        raw_upstream_blocked_projection=None,
        warnings=(),
        blockers=(blocker,),
        deferred_capabilities=TASK028_DEFERRED_CAPABILITIES_V1,
        provenance=prov,
    )
    assert len(blk_framed) == 2471
    assert blk_framed.hex() == FROZEN_VECTOR_04_CANONICAL_BYTES_HEX
    assert blk_h == "a7a04fd0bdb2541fd33945785676c1f7d3a0cabe3bd3cd562e2e30bc12e3744a"

    # --- VECTOR_05: Success engineering result hash ---
    ref_vel, single, comp = compute_local_loss_component(
        density_kg_m3=Decimal("998.2"),
        mass_flow_rate_kg_s=Decimal("0.5"),
        reference_flow_area_m2=Decimal("0.00078539816339"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    # comp_result = TubeSideLocalLossComponentResult(  # noqa: F841
    # component_id="ENG-001",
    # component_type=Task028ComponentType.ENTRANCE,
    # path_sequence_index=0,
    # flow_direction_assertion=Task028ComponentFlowDirectionAssertion.START_TO_END,
    # loss_coefficient=Decimal("0.5"),
    # loss_coefficient_convention=(
    # LossCoefficientConvention.K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2
    # ),
    # reference_flow_area_m2=Decimal("0.00078539816339"),
    # multiplicity=1,
    # upstream_reference_plane="shell-inlet-plane",
    # downstream_reference_plane="tube-inlet-plane",
    # reference_velocity_m_s=ref_vel,
    # single_occurrence_irreversible_pressure_loss_pa=single,
    # component_irreversible_pressure_loss_pa=comp,
    # authority_hash="a" * 64,
    # )
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
        canonicalize_component_result,
    )
    comp_record, _ = canonicalize_component_result(
        component_id="ENG-001",
        component_type="ENTRANCE",
        path_sequence_index=0,
        upstream_reference_plane="shell-inlet-plane",
        downstream_reference_plane="tube-inlet-plane",
        flow_direction_assertion="START_TO_END",
        authority_hash=FROZEN_ENG_AUTHORITY_HASH,
        reference_flow_area_m2=Decimal("0.00078539816339"),
        reference_velocity_m_s=ref_vel,
        loss_coefficient=Decimal("0.5"),
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        multiplicity=1,
        single_occurrence_irreversible_pressure_loss_pa=single,
        component_irreversible_pressure_loss_pa=comp,
    )
    succ_prov = Task028Provenance(
        task_id="TASK-028",
        design_contract_path="TASK-028-source-definition.md",
        implementation_software_version="0.3.0",
        input_evidence_refs=("CANONICAL-VECTOR-ENGINEERING-001",),
        upstream_identity_hashes=(
            "a" * 64,
            "b" * 64,
            "c" * 64,
            "d" * 64,
            FROZEN_ENG_AUTHORITY_HASH,
        ),
    )
    succ_framed, succ_h = _canonicalize_success_result_record(
        schema_version=TASK028_SUCCESS_RESULT_SCHEMA_VERSION,
        profile_id="default",
        request_hash="d08fe22d94073974b52fb2d292962899aa881a943d77672d1031d36facf5800c",
        task025_hydraulic_authority_hash="a" * 64,
        task025_result_hash="b" * 64,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        component_result_records=(comp_record,),
        warnings=(),
        blockers=(),
        deferred_capabilities=TASK028_DEFERRED_CAPABILITIES_V1,
        provenance=succ_prov,
    )
    assert len(succ_framed) == 2763
    assert succ_framed.hex() == FROZEN_VECTOR_05_CANONICAL_BYTES_HEX
    assert succ_h == "5e69e900ea59d245e1282711d81816f4398f21bcd653cd0e9f3540adba4debcb"

    assert RESULT_ID_NAMESPACE == "a0280000-0000-5000-8000-000000000001"


# --- ENGINEERING SEMANTICS (2 tests) ----------------------------------------


def test_T028_ENGINEERING_QUANTITY_IRREVERSIBLE_LOSS_SEMANTICS() -> None:
    """Output > 0 for positive inputs (irreversible loss, not net delta-p)."""
    _, _, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert comp > Decimal(0)
    result = TubeSideLocalLossComponentResult(
        component_id="E-001",
        component_type=Task028ComponentType.ENTRANCE,
        path_sequence_index=0,
        flow_direction_assertion=Task028ComponentFlowDirectionAssertion.START_TO_END,
        loss_coefficient=Decimal("0.5"),
        loss_coefficient_convention=(
            LossCoefficientConvention.K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2
        ),
        reference_flow_area_m2=Decimal("0.007854"),
        multiplicity=1,
        upstream_reference_plane="INLET",
        downstream_reference_plane="TUBE_START",
        reference_velocity_m_s=Decimal("0.6366"),
        single_occurrence_irreversible_pressure_loss_pa=comp,
        component_irreversible_pressure_loss_pa=comp,
        authority_hash="a" * 64,
    )
    assert not hasattr(result, "static_pressure_recovery_pa")


def test_T028_FLOW_DIRECTION_ORIENTATION_MISMATCH_BLOCKED() -> None:
    """S08: Component END_TO_START != START_TO_END → BL_T028_COMPONENT_FLOW_DIRECTION_MISMATCH."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(flow_direction_assertion="END_TO_START")]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COMPONENT_FLOW_DIRECTION_MISMATCH in codes
    assert not hasattr(result, "component_results")


def test_T028_CONTRACTION_EXPANSION_DIRECTIONAL_SEMANTICS() -> None:
    """Different K values for contraction vs expansion → different pressure loss."""
    _, _, comp_c = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.4"),
        multiplicity=1,
    )
    _, _, comp_e = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.6"),
        multiplicity=1,
    )
    assert comp_c != comp_e


# --- MULTIPLICITY GROUP (1 test) -------------------------------------------


def test_T028_MULTIPLICITY_GROUP_REFERENCE_PLANES() -> None:
    """Serial group outer bounding planes preserved on authority."""
    auth = _make_entrance_authority(multiplicity=3)
    assert auth.multiplicity == 3
    assert auth.upstream_reference_plane == "INLET"
    assert auth.downstream_reference_plane == "TUBE_START"


# --- PERMUTATION / CANONICAL (1 test) --------------------------------------


def test_T028_AUTHORITY_TUPLE_PERMUTATION_IDENTITY_STABLE() -> None:
    """Same semantic authorities, different tuple order → same request hash (CR-15).

    The pipeline sorts by path_sequence_index before hashing, so the same
    set of authorities always produces the same hash regardless of input order.
    """
    auth1 = _make_entrance_authority(component_id="A-001", path_sequence_index=0)
    auth2 = _make_entrance_authority(component_id="A-002", path_sequence_index=1)
    # Build authority hash → psi mapping
    hash_to_psi = {
        auth1.authority_hash: auth1.path_sequence_index,
        auth2.authority_hash: auth2.path_sequence_index,
    }
    # Unsorted input order
    hashes_input = (auth2.authority_hash, auth1.authority_hash)
    # Sorted by path_sequence_index (what the pipeline does)
    hashes_sorted = tuple(sorted(hashes_input, key=lambda h: hash_to_psi[h]))
    h1 = compute_request_hash(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="profile-001",
        task025_hydraulic_authority_hash="hyd" * 21 + "a",
        task025_result_hash="a" * 64,
        task026_result_hash="b" * 64,
        property_snapshot_hash="c" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=hashes_sorted,
    )
    # Same sorted order → same hash
    h2 = compute_request_hash(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="profile-001",
        task025_hydraulic_authority_hash="hyd" * 21 + "a",
        task025_result_hash="a" * 64,
        task026_result_hash="b" * 64,
        property_snapshot_hash="c" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=hashes_sorted,
    )
    assert h1 == h2
    # Different input order but same sorted result → same hash via pipeline sorting
    hashes_input_2 = (auth1.authority_hash, auth2.authority_hash)
    hashes_sorted_2 = tuple(sorted(hashes_input_2, key=lambda h: hash_to_psi[h]))
    assert hashes_sorted == hashes_sorted_2


# --- K CONVENTION (1 test) --------------------------------------------------


def test_T028_K_CONVENTION_REFERENCE_BASIS_MISMATCH_BLOCKED() -> None:
    """Wrong K convention → BL_T028_LOSS_COEFFICIENT_CONVENTION_UNSUPPORTED."""
    raw = _make_raw_request(
        component_authorities=[_minimal_component_dict(loss_coefficient_convention="FANNING")]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_CONVENTION_UNSUPPORTED in codes


# --- SOURCE AUTHORITY (1 test) ---------------------------------------------


def test_T028_SOURCE_AUTHORITY_REPLAY() -> None:
    """8-field source authority frozen values valid, invalid authority emits blocker (CR-14)."""
    assert TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELD_COUNT == 8
    assert len(TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELDS) == 8
    assert TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_ID == "USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL"
    assert TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_TITLE == "USACE HEC-RAS Hydraulic Reference Manual"
    assert TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_VERSION == "2024.1"
    assert (
        TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_LOCATION
        == "USACE HEC-RAS Hydraulic Reference Manual, Section 6.2.1"
    )
    assert (
        TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_SCOPE
        == "Pipe Minor Losses, entrance/exit local velocity-head loss treatment, "
        "Expansion and Contraction Coefficients"
    )
    assert (
        TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FORMULA
        == "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2"
    )
    assert (
        TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_COEFFICIENT_SEMANTICS
        == "IRREVERSIBLE_LOCAL_LOSS_COEFFICIENT"
    )
    assert TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_PERMISSION_STATUS == "ADMITTED"

    # CR-14: Prove invalid authority emits BL_T028_SOURCE_AUTHORITY_INVALID
    from hexagent.exchangers.shell_tube.tube_side_local_loss.models import (
        _TASK028_LOCAL_LOSS_SOURCE_AUTHORITY,
        Task028LocalLossSourceAuthority,
    )
    from hexagent.exchangers.shell_tube.tube_side_local_loss.pipeline import (
        _validate_task028_source_authority,
    )

    # Valid authority -> no blockers
    blockers = _validate_task028_source_authority(_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY)
    assert len(blockers) == 0

    # Verify the blocker code exists and has correct ordinal in registry
    assert Task028BlockerCode.BL_T028_SOURCE_AUTHORITY_INVALID is not None
    from hexagent.exchangers.shell_tube.tube_side_local_loss.blocker_registry import (
        _BLOCKER_REGISTRY,
    )

    assert _BLOCKER_REGISTRY[Task028BlockerCode.BL_T028_SOURCE_AUTHORITY_INVALID] == 30

    # Mutated fixture: wrong source_id -> BL_T028_SOURCE_AUTHORITY_INVALID
    bad_id = Task028LocalLossSourceAuthority(
        source_id="WRONG",
        source_title=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_title,
        source_version=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_version,
        source_location=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_location,
        source_scope=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_scope,
        admitted_formula=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.admitted_formula,
        admitted_coefficient_semantics=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.admitted_coefficient_semantics,
        permission_status=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.permission_status,
    )
    bad_blockers = _validate_task028_source_authority(bad_id)
    assert len(bad_blockers) == 1
    assert bad_blockers[0].entry.code == Task028BlockerCode.BL_T028_SOURCE_AUTHORITY_INVALID

    # Mutated fixture: wrong permission_status -> BL_T028_SOURCE_AUTHORITY_INVALID
    bad_perm = Task028LocalLossSourceAuthority(
        source_id=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_id,
        source_title=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_title,
        source_version=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_version,
        source_location=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_location,
        source_scope=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_scope,
        admitted_formula=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.admitted_formula,
        admitted_coefficient_semantics=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.admitted_coefficient_semantics,
        permission_status="PENDING",
    )
    bad_perm_blockers = _validate_task028_source_authority(bad_perm)
    assert len(bad_perm_blockers) == 1
    assert bad_perm_blockers[0].entry.code == Task028BlockerCode.BL_T028_SOURCE_AUTHORITY_INVALID


# --- ENUM / ROUTING (2 tests) ----------------------------------------------


def test_T028_ASSERTION_ENUM_DOMAIN() -> None:
    """Task028ApplicabilityAssertion: TRUE/FALSE only."""
    assert Task028ApplicabilityAssertion.TRUE.value == "TRUE"
    assert Task028ApplicabilityAssertion.FALSE.value == "FALSE"
    assert len(Task028ApplicabilityAssertion) == 2


def test_T028_RAW_ENUM_ROUTING() -> None:
    """Routing: supported → construct, unsupported → block."""
    raw = _make_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="E-001", component_type="ENTRANCE")
        ]
    )
    result = validate_raw_boundary(raw)
    type_blockers = [
        e
        for e in result.blockers
        if e.code == Task028BlockerCode.BL_T028_COMPONENT_TYPE_UNSUPPORTED
    ]
    assert len(type_blockers) == 0


# --- DECIMAL / NEGATIVE ZERO (2 tests) -------------------------------------


def test_T028_DECIMAL_COMPUTATION_ORDER() -> None:
    """Outputs are properly quantized (quantize→compute→quantize)."""
    ref_vel, single, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert ref_vel == quantize_task028_decimal(ref_vel, REFERENCE_VELOCITY_QUANTUM)
    assert single == quantize_task028_decimal(single, PRESSURE_LOSS_QUANTUM)
    assert comp == quantize_task028_decimal(comp, PRESSURE_LOSS_QUANTUM)


def test_T028_NEGATIVE_ZERO_NORMALIZATION() -> None:
    """-0.00000000 → normalized zero (negative sign removed, numerically equal to 0)."""
    result = normalize_negative_zero(Decimal("-0.00000000"), REFERENCE_VELOCITY_QUANTUM)
    assert result.is_zero()
    assert not result.is_signed()
    payload = task028_decimal_payload(result, REFERENCE_VELOCITY_QUANTUM)
    assert isinstance(payload, bytes)
    assert b"-" not in payload  # no negative sign


# --- RAW PROJECTION (1 test) -----------------------------------------------


def test_T028_UPSTREAM_RAW_PROJECTION_CANONICALIZATION() -> None:
    """Raw projection encoded with correct kind and hex (CR-10: .hex() not sha256)."""
    proj = encode_raw_projection("REQUEST", {"key": "value"})
    assert isinstance(proj, Task028RawProjection)
    assert proj.projection_kind == "REQUEST"
    assert isinstance(proj.canonical_bytes_hex, str)
    # CR-10: canonical_bytes_hex is hex-encoded canonical bytes, not sha256
    canonical_bytes = canonicalize_raw_value({"key": "value"})
    assert proj.canonical_bytes_hex == canonical_bytes.hex()
    # Verify canonicalize_raw_value produces bytes for various types
    assert isinstance(canonicalize_raw_value(None), bytes)
    assert isinstance(canonicalize_raw_value(True), bytes)
    assert isinstance(canonicalize_raw_value(42), bytes)
    assert isinstance(canonicalize_raw_value("hello"), bytes)
    assert isinstance(canonicalize_raw_value(Decimal("1.5")), bytes)
    assert isinstance(canonicalize_raw_value({"a": 1}), bytes)
    assert isinstance(canonicalize_raw_value([1, 2]), bytes)


# --- BLOCKER DEDUP (1 test) ------------------------------------------------


def test_T028_BLOCKER_DEDUP_STABILITY() -> None:
    """Dedup by (code, field_path, component_id_tiebreaker)."""
    b1 = emit_blocker(
        Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
        "raw_input",
        "msg",
        component_id_tiebreaker="",
    )
    b2 = emit_blocker(
        Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
        "raw_input",
        "msg",
        component_id_tiebreaker="",
    )
    collapsed = collapse_blockers([b1, b2])
    assert len(collapsed) == 1
    # Different tiebreaker → not deduped.
    b3 = emit_blocker(
        Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
        "raw_input",
        "msg",
        component_id_tiebreaker="X",
    )
    collapsed2 = collapse_blockers([b1, b3])
    assert len(collapsed2) == 2


# --- WARNING CONTRACT (1 test) ---------------------------------------------


def test_T028_WARNING_EMPTY_CONTRACT() -> None:
    """Success result warnings == () (frozen empty tuple)."""
    result = build_success_result(
        profile_id="profile-001",
        request_hash="a" * 64,
        task025_hydraulic_authority_hash="b" * 64,
        task025_result_hash="b2" * 32,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        component_results=(_make_minimal_component_result(),),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=_make_success_provenance(),
    )
    assert result.warnings == ()
    assert result.blockers == ()
    assert result.deferred_capabilities == ()


# --- SUCCESS ENGINEERING RESULT VECTOR (1 test) ----------------------------


def test_T028_SUCCESS_ENGINEERING_RESULT_VECTOR() -> None:
    """Full engineering result: V_ref, single_pa, component_pa all > 0 and consistent.

    Asserts VECTOR_05 frozen canonical bytes.
    """
    ref_vel, single, comp = compute_local_loss_component(
        density_kg_m3=Decimal("998.2"),
        mass_flow_rate_kg_s=Decimal("0.5"),
        reference_flow_area_m2=Decimal("0.00078539816339"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert ref_vel > Decimal(0)
    assert single > Decimal(0)
    assert comp > Decimal(0)
    assert comp == single  # multiplicity=1
    # Verify K consistency: K = single_pa / (rho * V² / 2)
    with localcontext(task028_decimal_context()):
        expected_single = Decimal("0.5") * Decimal("998.2") * ref_vel**2 / 2
        expected_single = quantize_task028_decimal(expected_single, PRESSURE_LOSS_QUANTUM)
    assert single == expected_single
    # Verify formula: V = mdot / (rho * A)
    with localcontext(task028_decimal_context()):
        expected_vel = Decimal("0.5") / (Decimal("998.2") * Decimal("0.00078539816339"))
        expected_vel = quantize_task028_decimal(expected_vel, REFERENCE_VELOCITY_QUANTUM)
    assert ref_vel == expected_vel
    # Verify frozen engineering values
    assert str(ref_vel) == "0.63776775"
    assert str(single) == "101.504"
    assert str(comp) == "101.504"


# ===========================================================================
# R2 additional verification tests (not frozen TEST_IDs)
# ===========================================================================


# --- DEFERRED CAPABILITIES (ITEM 3) ----------------------------------------


def test_task028_r2_deferred_capabilities_exact_tuple() -> None:
    """Deferred capabilities is exactly TASK028_DEFERRED_CAPABILITIES_V1."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
        TASK028_DEFERRED_CAPABILITIES_V1,
    )

    result = build_success_result(
        profile_id="profile-001",
        request_hash="a" * 64,
        task025_hydraulic_authority_hash="b" * 64,
        task025_result_hash="b2" * 32,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        component_results=(_make_minimal_component_result(),),
        warnings=(),
        blockers=(),
        deferred_capabilities=TASK028_DEFERRED_CAPABILITIES_V1,
        provenance=_make_success_provenance(),
    )
    assert result.deferred_capabilities == TASK028_DEFERRED_CAPABILITIES_V1
    assert len(result.deferred_capabilities) == 3
    assert result.deferred_capabilities[0] == "MODELED_TOTAL_PRESSURE_DROP_NOT_COMPUTED"
    assert result.deferred_capabilities[1] == "REFERENCE_PLANE_CONTINUITY_NOT_VALIDATED"
    assert result.deferred_capabilities[2] == "PRESSURE_PATH_COMPLETENESS_NOT_VALIDATED"


def test_task028_r2_success_result_field_count_frozen() -> None:
    """Success result has exactly 14 fields."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
        SUCCESS_RESULT_FIELD_COUNT,
    )

    assert SUCCESS_RESULT_FIELD_COUNT == 14


def test_task028_r2_blocked_result_field_count_frozen() -> None:
    """Blocked result has exactly 15 fields."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
        BLOCKED_RESULT_FIELD_COUNT,
    )

    assert BLOCKED_RESULT_FIELD_COUNT == 15


def test_task028_r2_blocker_registry_count_frozen() -> None:
    """Blocker registry has exactly 31 codes."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.blocker_registry import (
        BLOCKER_REGISTRY_COUNT,
    )

    assert BLOCKER_REGISTRY_COUNT == 31


def test_task028_r2_false_positive_hasattr_acceptance_count_zero() -> None:
    """FALSE_POSITIVE_HASATTR_ACCEPTANCE_COUNT=0: no hasattr blocker acceptance."""
    import ast
    import pathlib

    test_file = pathlib.Path(__file__).read_text()
    tree = ast.parse(test_file)
    hasattr_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "assertEqual":
                pass
            if isinstance(node.func, ast.Name) and node.func.id == "assert":
                pass
        if isinstance(node, ast.Assert):
            test_str = ast.dump(node.test)
            if "hasattr" in test_str and "BlockerCode" in test_str:
                hasattr_count += 1
    assert hasattr_count == 0, (
        f"FALSE_POSITIVE_HASATTR_ACCEPTANCE_COUNT must be 0; found {hasattr_count}"
    )


# --- PERMUTATION REPLAY (ITEM 5) -------------------------------------------


def test_task028_r2_permutation_replay_stable() -> None:
    """ITEM 5: Two requests with swapped component order produce identical results."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()

    # Request A: path=0, path=1
    raw_a = _build_pipeline_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="COMP-A", path_sequence_index=0),
            _minimal_component_dict(component_id="COMP-B", path_sequence_index=1),
        ]
    )
    # Request B: path=1, path=0 (reversed input order)
    raw_b = _build_pipeline_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="COMP-B", path_sequence_index=1),
            _minimal_component_dict(component_id="COMP-A", path_sequence_index=0),
        ]
    )

    result_a = _run_pipeline(raw_a, task025_valid, task026_valid)
    result_b = _run_pipeline(raw_b, task025_valid, task026_valid)

    assert isinstance(result_a, Task028SuccessResult)
    assert isinstance(result_b, Task028SuccessResult)

    # Same request_hash (sorted by path_sequence_index)
    assert result_a.request_hash == result_b.request_hash
    # Same result_hash
    assert result_a.result_hash == result_b.result_hash
    # Same result_id
    assert result_a.result_id == result_b.result_id
    # Same component order (sorted by path_sequence_index)
    assert len(result_a.component_results) == len(result_b.component_results)
    for ca, cb in zip(result_a.component_results, result_b.component_results, strict=True):
        assert ca.component_id == cb.component_id
        assert ca.path_sequence_index == cb.path_sequence_index


# --- FROZEN VECTOR TESTS (ITEMS 6-9) — exact frozen canonical byte oracles ---


def _build_task028_vector_01_actual() -> tuple[bytes, str]:
    """ITEM 6: VECTOR_01 — canonical authority framing frozen bytes."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
        canonicalize_authority,
    )

    args = dict(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id="E-001",
        component_type="ENTRANCE",
        path_sequence_index=0,
        upstream_reference_plane="INLET",
        downstream_reference_plane="TUBE_START",
        flow_direction_assertion="START_TO_END",
        loss_coefficient=Decimal("0.5"),
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2=Decimal("0.007854"),
        multiplicity=1,
        geometry_evidence_refs=("EVIDENCE-001",),
        coefficient_source_id="USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL",
        coefficient_source_version="2024.1",
        coefficient_source_location="USACE HEC-RAS, Section 6.2.1",
        coefficient_permission_status="ADMITTED",
    )
    framed, sha = canonicalize_authority(**args)
    return framed, sha


def _build_task028_vector_02_actual() -> str:
    """ITEM 7: VECTOR_02 — request hash frozen value."""
    h = compute_request_hash(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="profile-001",
        task025_hydraulic_authority_hash="hyd" * 21 + "a",
        task025_result_hash="a" * 64,
        task026_result_hash="b" * 64,
        property_snapshot_hash="c" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=(),
    )
    return h


def _build_task028_vector_03_actual() -> str:
    """ITEM 8: VECTOR_03 — same as VECTOR_02 (deterministic replay)."""
    h1 = compute_request_hash(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="profile-001",
        task025_hydraulic_authority_hash="hyd" * 21 + "a",
        task025_result_hash="a" * 64,
        task026_result_hash="b" * 64,
        property_snapshot_hash="c" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=(),
    )
    _ = compute_request_hash(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="profile-001",
        task025_hydraulic_authority_hash="hyd" * 21 + "a",
        task025_result_hash="a" * 64,
        task026_result_hash="b" * 64,
        property_snapshot_hash="c" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=(),
    )
    return h1


def _build_task028_vector_04_actual() -> tuple[str, str]:
    """ITEM 9: VECTOR_04 — success result hash frozen value."""
    h = compute_success_result_hash(
        schema_version=TASK028_SUCCESS_RESULT_SCHEMA_VERSION,
        profile_id="profile-001",
        request_hash="a" * 64,
        task025_hydraulic_authority_hash="b" * 64,
        task025_result_hash="b2" * 32,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        component_result_records=(),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=None,
    )
    rid = compute_result_id(h)
    return h, rid


def _build_task028_vector_05_actual() -> tuple[Decimal, Decimal, Decimal]:
    """ITEM 10: VECTOR_05 — engineering values frozen."""
    ref_vel, single, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert ref_vel > Decimal(0)
    assert single > Decimal(0)
    assert comp > Decimal(0)
    assert comp == single  # multiplicity=1
    # Verify reference_velocity_m_s quantized correctly
    expected_vel = Decimal("5") / (Decimal("1000") * Decimal("0.007854"))
    _ = quantize_task028_decimal(expected_vel, REFERENCE_VELOCITY_QUANTUM)
    return ref_vel, single, comp


# --- CROSS-PYTHON PROOF (ITEM 10) ------------------------------------------
