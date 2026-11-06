# WPR2 Endpoint Semantics — Reproducible Source Search Log

Goal: determine whether WPR2_ADDR_HI is an inclusive end, exclusive end, last page address, or another bound, using offline source + archived files only. No network, no GPU/hardware access, no writes to original artifacts.

## Environment
- Work tree: /home/REDACTED_USER/codex-work/work_v15
- Saved source tree: /tmp/nvsrc (subdirs: common/, nvidia/, nvidia-modeset/)
- Saved source tree self-declared version: /tmp/nvsrc/common/inc/nvUnixVersion.h -> NV_VERSION_STRING "615.78.08" (sha256 27e9b418975dc7b388836924d35492ee922373944a5fa346b93cd394200c7474)
- Target GPU (from archived artifacts): TU106 [CMP 40HX] 0000:03:00.0; archived sources map the same PFB MMU WPR2 register block as turing tu102 (0x1FA824/0x1FA828).

## Archived artifacts read (read-only)
- /home/REDACTED_USER/codex-work/work_v15/PHASE16/EVIDENCE_LEDGER.md — section "E16-007 — WPR registers require field extraction": raw LO 0x01f7e000, HI 0x01ffee00, VAL[31:4] << 12 => 0x1f7e00000 / 0x1ffee0000, difference 128.875 MiB; raw subtraction invalid; "precise upper-bound interpretation require the memory follow-up"; source URL cited (raw.githubusercontent .../580.95.05/.../tu102/dev_fb.h) treated as external, NOT verified against /tmp/nvsrc.
- /home/REDACTED_USER/codex-work/work_v15/PHASE16/SECURITY_ARCH_REVIEW/REPORT.md + corrected_claims.json + verify_wpr.py/log: same decode; prior review labels HI exclusive with no independent consumer proof (this is the open item).
- /home/REDACTED_USER/codex-work/work_v15/PHASE16/MEMORY_PCIE/MEMORY_PCIE_REPORT.md §8 + memory_pcie_verified.json: WPR2 corrected base/end/size; rule: do NOT subtract WPR2 from NVML Reserved 389 MiB; WPR2/Reserved overlap = UNKNOWN.
- /home/REDACTED_USER/codex-work/work_v15/PHASE16/JOBS/wpr_endpoint_semantics_v1/task.txt: this task statement (output.log empty, state.json stage=running — left untouched).

## Searches performed (all offline, read-only)
1. grep -rn "WPR2_ADDR_HI|WPR2_ADDR_LO" /tmp/nvsrc
   -> hits ONLY in swref published headers:
      - common/inc/swref/published/turing/tu102/dev_fb.h lines 39-44
      - common/inc/swref/published/hopper/gh100/dev_fb.h lines 43-52
      - common/inc/swref/published/blackwell/gb100/dev_hubmmu_base.h lines 91-96
   -> NO .c/.cpp consumer reads these registers in the saved tree.
2. grep -rn "WPR2|wpr2|Wpr2" /tmp/nvsrc/nvidia --include=*.c --include=*.cpp
   -> no implementation file; only rmlsfm.h / flcnretval.h defines (unrelated light-secure WPR, not PFB MMU WPR2_ADDR).
3. grep -rn "GetWprRegionInfo|wprRegionInfo|wpr2End|wpr2Start" /tmp/nvsrc
   -> common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080fb.h (interface struct + doc comment)
   -> nvidia/generated/g_subdevice_nvoc.h (declaration subdeviceCtrlCmdFbGetWprRegionInfo_IMPL only; body NOT in saved tree)
4. grep -rn "gspFwWprEnd|gspFwWprStart" /tmp/nvsrc
   -> nvidia/arch/nvalloc/common/inc/gsp/gsp_fw_wpr_meta.h only (+ _v1.h)
5. grep -rn "RmGspWprEndMargin|GspWprEndMargin" /tmp/nvsrc/nvidia
   -> nvidia/interface/nvrm_registry.h only
6. grep -rn -i "wpr" /tmp/nvsrc/nvidia-modeset
   -> no WPR2 endpoint-relevant hits
7. grep -rn "WITHIN_EXCLUSIVE|WITHIN_INCLUSIVE|NV_EMPTY_EXCLUSIVE|NV_EMPTY_INCLUSIVE" /tmp/nvsrc/nvidia/arch/nvalloc/common/inc/nvrangetypes.h
   -> generic range macros only (codebase convention, not WPR-specific)

## Files cited (sha256)
- ctrl2080fb.h          9e9783e9c6b57078226dce4c181a1a3136d73cea2593fec70a122033d8788ce0
- dev_fb.h (turing)     8c824a870e88874e95b22b463e70a6e1c08ff765ab1731746b98ef28e952c6a9
- dev_fb.h (hopper)     d1b0dfdeb0345ac0f8e7ae01af863e56587f43e35c9da732898f02c67b08f0eb
- dev_hubmmu_base.h     2b2e42622f32331573ba0da0d3c445c1cabb8dbf6ce3ccbc7b506b6db62f4b70
- gsp_fw_wpr_meta.h     f3b615a6d87b557ddab986b6ba6a5209901f09edcf0e5b9c983e0d8112538fc5
- nvrangetypes.h        84e8f17a5e82d9ce86c350aec7df95d7d711e7dfae7b2670a464f3b88fc017ac
- nvrm_registry.h       8de487f1f624a628d2c5efffc9d25de2669ac5764f7420cd09da6c53aab1556f
- nvUnixVersion.h       27e9b418975dc7b388836924d35492ee922373944a5fa346b93cd394200c7474

## Result
No consumer code in saved source; best evidence is authoritative comments / ABI contract + GSP metadata layout (see findings.json). Consumer-proof dimension: NOT ESTABLISHED. Upper-bound reading: exclusive end (supported by comments, not proven by consumer).
