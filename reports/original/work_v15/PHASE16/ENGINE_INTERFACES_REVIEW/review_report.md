ENGINE-INTERFACES REVIEW — CMP 40HX / TU106 (corrected, Phase 16 work_v15)
=====================================================================

Target: NVIDIA CMP 40HX, TU106-100-A1, PCI 10de:1f0b, subsystem 8804:1043, rev 0xA1
Board: CG161P REV 2.00 (ASUS DUAL-RTX2060S-O8G-EVO-V2, per archived BAO_CAO)
Output: /home/REDACTED_USER/codex-work/work_v15/PHASE16/ENGINE_INTERFACES_REVIEW/
Original: /home/REDACTED_USER/codex-work/PHASE16/ENGINE_INTERFACES/ — NOT modified, NOT overwritten.
Method: source-bounded re-audit against work_v15/PHASE16 reviewed artifacts + archived RAW_DATA
evidence. Every claim cites exact file + sha256 + line/offset. No hardware probe, no MMIO/PCI-config
write, no driver change, no tool install, no GPU operation, no source-file mutation, no new runtime
measurement. All MMIO/fuse/PCIe values below are ARCHIVED evidence.

Confidence levels: MEASURED, DECODED, CORROBORATED, INFERRED, UNKNOWN, BLOCKED, REJECTED,
UNRESOLVED_CONFLICT.

========================== 1. MATERIAL CONFLICT RESOLUTION ==========================

C1 — fuse+0x650 raw 0x0004001F as "TPC mask / 5 enabled topology"
  Original claim: fuse+0x650 = 0x0004001F is a named TPC mask, bits0-4 = 5 TPC enabled,
  corroborating tpc_nr=5 / 17 TPC / 34 SM (original report §1 GR #9-13, MEASURED+CORROBORATED).
  Conflict: SECURITY_ARCH/audit_prior_claims.json SEC-FUSE-05 = REJECTED. dev_fuse.h tu102
  (sha f96f637c..., local copy SOURCES/nvidia_tu102_dev_fuse.h identical) defines only 2
  registers: NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS 0x0002174C (lines 26-29) and
  NV_FUSE_OPT_NVDEC_DISABLE 0x00021378 (lines 31-33). Offset 0x21650 is NOT defined; no source
  bitfield; INFERRED only. FUSE_TU106_AUDIT keeps it UNKNOWN and rejects popcount->topology
  inference (U-FUSE-005 at fuse+0xC1C: popcount 3 == GPC count but rejected). Grep of
  /tmp/nvsrc common/ + nvidia/ found NO gpc_nr/tpc_nr/TPC_UNIT/FECS_SPEED_PLM/0x21650
  definition anywhere; no consumer identified.
  Evidence for raw word: BAO_CAO_CMP40HX_TU106.md §3.4/§5.1 lines 79-81, 168 (sha aa43bb2d...);
  fuse2.json base 0x21000 regs[1616] (byte 0x650) = 0x0004001F (sha 0e770041...), independent
  re-read of the archived dump.
  Disposition: RETRACT the named "TPC mask" semantics and the "5 enabled / corroborated topology"
  correlation. Raw word 0x0004001F at fuse base 0x21000+0x650 remains MEASURED (two archived
  reads agree). No TU106-applicable source definition + no consumer => fuse<->topology semantics
  UNKNOWN. 0x1F == 5 (tpc_nr) is a value coincidence, not sourced correlation; do not cite as
  corroboration.
  New status: raw MEASURED = 0x0004001F; semantics UNKNOWN.

C2 — fuse+0xC04 / display "not masked"
  Original claim: fuse+0xC04 = 0, display not fuse-masked (original §6 Display).
  Conflict: RAW_DATA/fuse2.json + FUSE_TU106_AUDIT show raw value 1 at fuse base 0x21000 + 0xC04
  (regs[3076] = 1). BAO_CAO §4.1 lines 131-136 (archived) claims NV_FUSE_OPT_DISPLAY (0x021C04) =
  0x00000000 read-only, 0x021C00 = 0x021C08 = 0. TWO ARCHIVED SOURCES DISAGREE =>
  UNRESOLVED_CONFLICT; both listed, none selected.
  Only DISPLAY definition anywhere in the snapshot: Maxwell GM107
  NV_FUSE_STATUS_OPT_DISPLAY 0x00021C04 bit 0:0, only defined value ENABLE = 0x0
  (dev_fuse.h gm107 lines 27-29, sha 1b83b306...; same {0}-only enum in ga100/gb100/t234 at
  other addresses). tu106_applicable = false. Observed value 1 is outside the defined enum {0};
  cannot import Maxwell to TU106. U-FUSE-009 stays OPEN/UNKNOWN.
  Disposition: RETRACT "display not masked / fuse=0 means not disabled". No causal inference
  between fuse value and display absence. U-FUSE-009 OPEN/UNKNOWN.
  New status: raw UNRESOLVED_CONFLICT (fuse2.json=1 vs BAO_CAO=0); field semantics UNKNOWN.

C3 — BAR1 capacity: 8 GiB vs 64 GiB window
  Original claim: BAR1 = 8 GiB (ReBAR enabled) (original §7 PCIe #7; traced to archived BAO_CAO
  §6 line 190 "BAR1: 8 GiB"). Conflated BAR1 aperture with VRAM size.
  Evidence BAR1 = 64 GiB: resource range 0x381000000000..0x381FFFFFFFFF =
  68,719,476,736 bytes = 65536 MiB = 64 GiB, flags 0x0014220C (MEMORY_PCIE_REPORT.md §2,
  raw PCIE/pcie_map.json); lspci Region 1 at 381000000000 64-bit prefetchable [size=64G]
  (RAW_DATA/p5678.json); ReBAR cap [bb0] BAR1 current 64GB supported 64MB..256GB
  (RAW_DATA/q3_pcie.txt); NVML BAR1 Total 65536 MiB / Used 2 / Free 65534 (MEMORY_PCIE §8).
  Evidence VRAM = 8 GiB separately: Total 8192 MiB / Reserved 389 MiB / Used 0 / Free 7804 MiB
  (MEMORY_PCIE §8, smq memory_registers.json; 1 MiB delta unresolved); cuda totalGlobalMem
  7803 MB after GSP/PMT reserve (BAO_CAO §3.3 line 71).
  Disposition: CORRECT — BAR1 aperture/window = 64 GiB (ReBAR); VRAM framebuffer total = 8 GiB,
  separate quantity. Do not claim BAR1 = 8 GiB. ReBAR fuse-vs-strap remains UNKNOWN.
  New status: BAR1 64 GiB window MEASURED (archived resource range + NVML); VRAM 8 GiB MEASURED
  separately; no conflation.

C4 — display "hardware physically absent"
  Original claim: display block physically absent, not fuse-masked, not decoded into BAR0 on any
  path incl. PRAMIN (original §6 status MEASURED_ABSENT).
  Conflict: poison/zero reads are limited to exact sampled offsets/pages; they prove nothing
  about block presence on every BAR0/PRAMIN path, BAR decode, clock/power gating, or board
  causes.
  Evidence (exact sampled offsets/pages, archived): DISP base 0x610000 / control 0x610010 /
  head 0x612300 / SOR 0x616000 / DAC 0x61C110 all = 0xBADF1301; PRAMIN+0x1E0200 = 0x8E0200 =
  0xBADF1100 (BAO_CAO §4 lines 110-117); q6.json PDISP zones 0x610000/0x611000/0x612000/
  0x616000/0x61C000/0x620000/0x640000 all read 0xBADF1301; scan 0x600000-0x700000 step 0x1000
  = 0/256 pages live, step 0x100 = 0 pages (BAO_CAO §4 lines 119-120); page_inventory.csv
  pages 1536-1570 (0x600000-0x622000) all POISON; tu06.json full BAR0: POISON 3253 / DATA 287 /
  ZERO 355 / MIXED 201 of 4096 pages; 0x700000-0x87FFFF reads zero = mapped but uninitialized
  (third state, distinct from poison, BAO_CAO §4 line 121).
  Disposition: LIMIT conclusion to exact sampled offsets/pages: no display decode observed at the
  sampled offsets and no live page in scanned 0x600000-0x700000 (archived). Do NOT conclude the
  silicon block is physically absent; do not claim absence on every BAR0/PRAMIN path
  (PRAMIN+0x1E0200 is one sampled address only). Preserve UNKNOWN: block presence, BAR decode,
  clock/power gating, board causes (die binning vs strapping). Driver state (card1 0 connectors,
  Display Active Disabled) is archived driver observation, not silicon proof.
  New status: MEASURED at sampled offsets (poison/zero) + UNKNOWN for physical presence /
  BAR decode / clock & power gating / board causes. Replaces MEASURED_ABSENT.

C5 — topology 3 GPC / 17 TPC / 34 SM and register field mappings
  Original claim: 3 GPC / 17 TPC / 34 SM with mapped register fields; fuse popcount 0x1F=5
  corroborates TPC count.
  Conflict: no source definition for gpc_nr/tpc_nr/TPC_UNIT anywhere in /tmp/nvsrc snapshot
  (grep empty). SEC-FUSE-05 rejected fuse field name; popcount->topology rejected by
  FUSE_TU106_AUDIT. Counts must trace to exact archived raw values only; register bitfield
  semantics UNKNOWN.
  Evidence (exact, archived): gpc_nr 0x00409604 = 0x08040003 => 3 GPC (BAO_CAO §3.1 line 43);
  tpc_nr 0x00502608 = 0x00040005 => 5 TPC in GPC0 (§3.1 line 44); TPC map GPC0 TPC0-4 LIVE,
  TPC5 = 0xBADF1300 at all 3 offsets (0x010/0x100/0x400), GPC1/GPC2 all LIVE per archive =>
  17 TPC (§3.2 lines 47-59); 17 TPC x 2 = 34 SM = 2176 CUDA, cudaGetDeviceProperties
  multiProcessorCount=34, cores 2176, clock 1650 MHz (§3.3 lines 63-72) — CORROBORATED by two
  independent archived methods. Pitfall: first idle tpc_nr read gave 13 TPC (PMC_ENABLE bit9
  PGR=0); GR must be woken by CUDA kernel (§3.5, §11 pitfall 1). tpc_nr writes read-only;
  fuse+0x524 unstable (0x1F before unlock, 0x00 after), not a reference (§3.5, §11 pitfall 5).
  BAO_CAO §10 line 315 (archived) states die config 3 x (5,6,6) = 17 TPC — archived claim, not
  source-verified field decode.
  Source applicability: no gpc_nr/tpc_nr/TPC_UNIT definition in snapshot; tu102 headers are
  Turing-family shared with no tu106 override dir; g_chips2halspec_nvoc.h recognizes TU106 only
  in the DISPv0400 hal delete expression (lines 140-141).
  Disposition: REPLACE "mapped register fields" with raw register values MEASURED at exact
  addresses with file/hash/line (above). Topology counts reported as archive-measured (3 GPC;
  GPC0 = 5 TPC live + TPC5 poison; 17 TPC total per archive map; 34 SM CUDA-corroborated).
  Register field names/bitfields = UNKNOWN. Fuse popcount correlation RETRACTED.
  Reconciled with prior topology review (was UNKNOWN): raw values now evidenced, field semantics
  remain UNKNOWN.
  New status: raw topology values MEASURED/CORROBORATED as listed; register field mapping
  UNKNOWN; fuse-correlated claim RETRACTED.

C6 — archived vs new runtime work; g_chips2halspec_nvoc.h; Turing/TU102 limits
  Conflict: coordinator review requires distinguishing archived config/resource files and archived
  tool output from new hardware measurements. No new probe occurred for this job.
  Evidence: g_chips2halspec_nvoc.h lines 140-141 (sha 194204fd..., /tmp/nvsrc snapshot only,
  not in work_v15 SOURCES): "delete DISPv0400 & ~(TU102 | TU104 | TU106 | TU116 | TU117);"
  — TU106 architectural recognition in hal spec ONLY. No tu106/ register directory exists; all
  TU106 register namespaces come from tu102 Turing-family shared headers; applicability rests on
  family compatibility, not a TU106-specific definition. All MMIO/fuse/PCIe values in this review
  are archived (BAO_CAO measurement 02/11/2026; RAW_DATA dumps; q3_pcie.txt; p5678.json;
  q6.json; tu06.json; bar3_hot.bin). Historical XVE 0x88004 probe-write killed the PCIe link
  permanently (full power-off to recover) — archived event with warning (BAO_CAO §6 lines
  207-219), not performed by this review.
  Disposition: label every archived measurement/tool output as archived; never describe as new
  runtime work.

========================== 2. FUSE WORD AUDIT (exact offsets, source, applicability) ==

  fuse+0x650 (abs 0x21650): raw 0x0004001F [BAO_CAO §3.4/§5.1; fuse2.json regs[1616]]
    source definition: NONE in dev_fuse.h tu102 (only 0x21378 line 31, 0x2174C line 26)
    consumer: none identified; semantics UNKNOWN; name/semantics RETRACTED
  fuse+0xC04 (abs 0x21C04): raw 1 [fuse2.json regs[3076]] vs raw 0 [BAO_CAO §4.1 line 134]
    source definition: NV_FUSE_STATUS_OPT_DISPLAY 0x00021C04 bit 0:0, only value ENABLE=0,
    maxwell/gm107/dev_fuse.h lines 27-29; tu106_applicable = false
    semantics UNKNOWN; observed 1 outside enum {0}; UNRESOLVED_CONFLICT; U-FUSE-009 OPEN
  fuse+0x74C (abs 0x2174C): raw 1 => NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS bit0 YES
    source dev_fuse.h tu102 lines 26-29; tu106_applicable = true; SUPPORTED (SEC-FUSE-02)
  fuse+0x378 (abs 0x21378): raw 0 => NV_FUSE_OPT_NVDEC_DISABLE bits 2:0 INIT=0
    source dev_fuse.h tu102 lines 31-33; tu106_applicable = true; SUPPORTED (SEC-FUSE-01)

========================== 3. PER-SUBSYSTEM: ARCHITECTURE vs OBSERVED ==

GR / FECS / GPCCS — PARTIALLY_MEASURED (corrected per C1/C5)
  Architecture: TU106 in hal spec (g_chips2halspec_nvoc.h DISPv0400 list, architectural only);
  PBDMA/FECS/GPR ctrl namespaces from tu102 Turing-family shared headers; no tu106 override dir;
  no RM engine driver source; no FECS firmware/descriptor/slot; no engine<->slot mapping.
  Observed: NV_PMC_BOOT_0 = 0x166000A1 (ARCH=1 Turing, IMPL=6 TU106, REV=6 A1); gpc_nr
  0x00409604 = 0x08040003 (3 GPC); tpc_nr 0x00502608 = 0x00040005 (5 TPC in GPC0); GPC0 TPC5
  poison 0xBADF1300 at 3 offsets; 17 TPC x 2 = 34 SM / 2176 CUDA corroborated by cuda
  runtime; PMC_ENABLE PGR=0 idle (first idle tpc_nr read 13 TPC — pitfall); FECS shadow slots
  writable but not connected to topology.
  Unknowns: GPCCS block; FECS ucode/slot; GR channel/runlist state; fuse as sole GR gate vs
  strap/falcon gating; fuse+0x650 semantics.

FIFO / PBDMA — ARCH_ONLY (unchanged, no conflict). CE — ARCH_ONLY (unchanged).
PMU / SEC2 / GSP — PARTIALLY_MEASURED (unchanged; cmpunlocker SEC2 claim = archived runtime
evidence for unlock path only, not structural engine<->slot fact). NVENC / NVDEC — ARCH_ONLY.

Display — MEASURED_AT_SAMPLED_OFFSETS / PRESENCE_UNKNOWN (corrected per C2/C4)
  Architecture: DISPv0400 includes TU106 in hal spec only; no tu106 display register header;
  only DISPLAY fuse source is Maxwell gm107 (not TU106-applicable).
  Observed (exact offsets, archived): all DISP/SOR/DAC registers and sampled PRAMIN offset
  0x8E0200 return poison; scan 0x600000-0x700000 step 0x1000 = 0/256 live pages; q6.json PDISP
  zones all 0xBADF1301. Driver: card1 0 connectors.
  Unknown (preserved): physical block presence, BAR decode, clock/power gating, board causes,
  fuse+0xC04 state (UNRESOLVED_CONFLICT/UNKNOWN).

PCIe / GMMU-facing paths — PARTIALLY_MEASURED (corrected per C3/C6)
  Observed (archived): LnkCap/LnkSta 2.5GT/s x16 downgraded, LnkCap2 2.5GT/s only; BAR1 resource
  range 0x381000000000..0x381FFFFFFFFF = 64 GiB flags 0x0014220C; ReBAR [bb0] BAR1 current
  64GB supported 64MB..256GB; NVML BAR1 Total 65536 MiB; VRAM total 8192 MiB separate; XVE
  0x88000 = 0x1F0B10DE, XVE 0x88008 = 0x030200A1, XP 0x118000-08 = 0x00001000/0/0.
  Unknown: GMMU page-table hierarchy; ReBAR fuse-vs-strap; link beyond Gen1 x16.

========================== 4. ARCHIVED vs NEW ==

All MMIO/fuse/PCIe values are ARCHIVED (BAO_CAO_CMP40HX_TU106.md measurement 02/11/2026;
RAW_DATA/fuse2.json, q6.json, p5678.json, tu06.json, q3_pcie.txt, bar3_hot.bin). No new
hardware probe, measurement, or write performed by this review. Historical XVE 0x88004
probe-write is an archived event (link killed, full power-off recovery), with a never-probe
warning retained.

g_chips2halspec_nvoc.h (sha 194204fd..., external /tmp/nvsrc snapshot only): TU106 listed in
DISPv0400 hal delete expression lines 140-141 = architectural recognition only. No tu106/
register directory; tu102 headers are Turing-family shared; applicability to TU106 rests on
family compatibility, not a TU106-specific definition.

========================== 5. VERDICT ==

WHOLE-GPU REVERSE ENGINEERING IS NOT COMPLETE. This review covers corrected engine-interface
findings only, in new output under work_v15/PHASE16/ENGINE_INTERFACES_REVIEW/. The original
report under PHASE16/ENGINE_INTERFACES/ was not overwritten.

Preserved unknowns: topology register field semantics; fuse/OTP semantics beyond measured words;
VBIOS tables; GSP function inventory; MMIO outside listed namespaces; display physical presence/
BAR decode/clock & power gating; board-level causes; ReBAR fuse-vs-strap.

Unresolved conflicts (listed, not resolved): fuse+0xC04 raw = 1 (fuse2.json) vs = 0 (BAO_CAO);
no convenient interpretation selected.

========================== 6. DELIVERABLES ==

review_findings.json   machine-readable corrected findings (this report in structured form)
review_report.md       this human-readable report
source_manifest.json   source + archived-evidence manifest with sha256/size/role/label
validation_log.md      validation checks and results

========================== 7. CONSTRAINTS HONORED ==

- No hardware probe, no MMIO/PCI-config write, no driver change, no tool install, no GPU op.
- No source-file mutation; original ENGINE_INTERFACES/ untouched.
- No new runtime measurement; all values archived and labeled.
- Conflicts listed and marked UNRESOLVED_CONFLICT rather than resolved by convenience.
- Per-subsystem architecture (source) vs observed device status retained.
- Whole-GPU incomplete verdict preserved.
