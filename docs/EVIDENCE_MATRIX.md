# Evidence matrix

| Claim / observation | Evidence class | Recorded value | Original report |
|---|---|---|---|
| GPU identity | Reported live | CMP 40HX; TU106-100-A1; `10DE:1F0B` | [Independent topology](../reports/original/PHASE_TU106_FLOORSWEEP_INDEPENDENT/BAO_CAO_MOI_TPC_CMP40HX.md) |
| Effective TPC fuse status | Measured | `BAR0 0x021C38 = 0x20` | [TPC5 raw fuse](../reports/original/ok/results/TPC5/TPC5_RAW_FUSE_COMPARISON.md) |
| GPC active TPC masks | RM-reported | GPC0 `0x1F`, GPC1/2 `0x3F` | [Independent topology](../reports/original/PHASE_TU106_FLOORSWEEP_INDEPENDENT/BAO_CAO_MOI_TPC_CMP40HX.md) |
| GR topology | Reported live | `0x502608 = 0x00040005`, other GPCs 6/6 | [TPC5 raw fuse](../reports/original/ok/results/TPC5/TPC5_RAW_FUSE_COMPARISON.md) |
| FECS PRI access response | Reported live | candidate TPC5 `0xBADF1300` | [Defect vs floorsweep](../reports/original/ok/results/TPC5/TPC5_DEFECT_REGISTER_EVIDENCE.md) |
| Display gate | Measured/reverse engineered | `BAR0 0x021C04 = 1` | [D1 fuse analysis](../reports/original/ok/results/DISPLAY_D1/D1_FUSE_021C04_PRODUCER.md) |
| Display VBIOS policy | Parsed / inferred | `NO_DISPLAY_SUBSYSTEM=1`; DCB empty | [D1 VBIOS analysis](../reports/original/ok/results/DISPLAY_D1/D1_VBIOS_DISPLAY_POLICY.md) |
| TPC5 direct MMIO test | Reported live | `0x021040` sticky 1, `0x021838` write bounced, status and GR unchanged | [Live experiment](../reports/original/ok/results/TPC5_LIVE/EXPLOIT_LIVE_20261106.md) |
| Actual EN_SW_OVERRIDE identity on TU106 | **UNKNOWN** | Candidate `0x021040` not definitively identified | [R1 correction](../reports/original/ok/results/TPC5_R1/TPC5_OVERRIDE_REGISTER_IDENTITY.md) |
| `0x021A40` as RECONFIG_OVERRIDE | **UNKNOWN** | 128 B read as zero; semantic mapping not established | [R1 correction](../reports/original/ok/results/TPC5_R1/TPC5_OVERRIDE_REGISTER_IDENTITY.md) |
| TPC5 silicon health | **UNKNOWN** | No valid active TPC5 functional test | [Recoverability](../reports/original/ok/results/TPC5/TPC5_RECOVERABILITY_VERDICT.md) |
| Physical display works | **NOT OBSERVED** | No native output from target BDF proven | [D3](../reports/original/ok/results/DISPLAY_D3/D3_FINAL_VERDICT.md) |

Status vocabulary: **MEASURED** (value reported from a particular test), **CODE-TRACED** (instruction/source-derived), **INFERRED** (interpretation), **TESTED-FAILED** (specified route did not work), **UNKNOWN** (no proven determination), **SUPERSEDED** (historical theory corrected later). A live report does not automatically establish all of its *interpretations*.
