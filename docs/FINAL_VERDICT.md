# Final verdict — CMP 40HX / TU106-100-A1

**Outcome: no confirmed native display restoration; no confirmed GPC0/TPC5 restoration.** Do not interpret this as a proof of impossibility.

## GPC0/TPC5

- **MEASURED:** on the investigated sample, `STATUS_OPT_TPC_GPC0 @ 0x021C38 = 0x00000020`; RM masks `0x1F/0x3F/0x3F`; hardware GR per-GPC count `5/6/6`. Effective total is **17 TPC, 34 SM, 2,176 CUDA cores**.
- **OBSERVED:** reads from candidate GPC0/TPC5 TPC-unit addresses returned `0xBADF1300`, decoded in the reports as `FECS_PRI_FLOORSWEEP`. This identifies the observed aperture behavior, not the physical health of a disabled block.
- **TESTED AND FAILED (reported 2026-11-06):** privileged BAR0 access; write `1` to `0x021040` and bit 5 to `0x021838`. The latter read back as zero, fuse/status remained `0x20`, GR remained 5 TPC. There is **no confirmed recovery**.
- **UNKNOWN:** which register, if any, enables TU106 software override; whether the effective disabled bit originates from irreversibly programmed OTP, shadow state or another mechanism; whether TPC5 is physically functional; whether any pre-init route can enable it.
- **DO NOT INFER:** `0x021040` accepting a write proves it is `FUSE_EN_SW_OVERRIDE`; the bounce proves all possible host-side mechanisms are blocked; or comparison to GA100/170HX determines TU106 behavior.

Primary references: [TPC5 live experiment](../reports/original/ok/results/TPC5_LIVE/EXPLOIT_LIVE_20261106.md), [fuse evidence](../reports/original/ok/results/TPC5/TPC5_RAW_FUSE_COMPARISON.md), [override identity correction](../reports/original/ok/results/TPC5_R1/TPC5_OVERRIDE_REGISTER_IDENTITY.md), [recoverability report](../reports/original/ok/results/TPC5/TPC5_RECOVERABILITY_VERDICT.md).

## Display

- **MEASURED / REPORTED:** `STATUS_OPT_DISPLAY @ 0x021C04 = 1` on the studied sample; source-level RM policy checks and VBIOS `NO_DISPLAY_SUBSYSTEM`/DCB paths documented.
- **NOT ACHIEVED:** native monitor/display output driven directly by this CMP GPU. Output through a second adapter and game/compute functions must not be conflated with physical display restoration.
- **UNKNOWN:** complete initialization gates, requirements of display engines, and physical viability of all board routing/configuration.

Primary references: [D1](../reports/original/ok/results/DISPLAY_D1/D1_FINAL_VERDICT.md), [D3](../reports/original/ok/results/DISPLAY_D3/D3_FINAL_VERDICT.md), [PCB analysis](../reports/original/ok/results/T01/PCB_DISPLAY_REPORT.md).

## Scope and chronology caveats

The archive joins different captures and phases, including driver/GSP `615.71.09` and `615.78.08`, host operating environments, intermediate theories and corrected follow-ups. Results tied to particular dates/builds should never be silently merged as one simultaneous state. This final verdict is a conservative synthesis of supplied materials, **not new testing**.
