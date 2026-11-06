ENGINE-INTERFACES RESEARCH REPORT — CMP 40HX / TU106
====================================================
Target: NVIDIA CMP 40HX, TU106-100-A1, PCI 10de:1f0b, subsystem 8804:1043, rev 0xA1
Scope: GR/FECS/GPCCS, FIFO/PBDMA, copy engines, PMU/SEC2/GSP, NVENC/NVDEC, display, PCIe/GMMU-facing paths
Method: source-bounded only. Local source snapshot /tmp/nvsrc + supplied archived evidence in /tmp.
        No hardware probe, no MMIO/PCI-config write, no driver change, no tool install, no GPU operation.
Outputs: PHASE16/ENGINE_INTERFACES/{inputs.json, findings.json, report.md, build_log.txt}

INPUT INVENTORY
---------------
inputs/inputs.json — sha256 + size for every cited source file (29) and every archived evidence file (207).
Key source files cited (all under /tmp/nvsrc):
  common/inc/swref/published/turing/tu102/dev_pbdma.h
  common/inc/swref/published/turing/tu102/dev_esched_pbdma.h
  common/inc/swref/published/turing/tu102/dev_gsp.h
  common/inc/swref/published/turing/tu102/dev_sec_pri.h
  common/inc/swref/published/turing/tu102/dev_ce_base.h
  common/inc/swref/published/turing/tu102/dev_pmc.h
  common/inc/swref/published/turing/tu102/dev_mmu.h
  common/inc/swref/published/turing/tu102/dev_vm.h
  common/inc/swref/published/turing/tu102/dev_bus.h
  common/inc/swref/published/turing/tu102/dev_falcon_v4.h
  common/inc/swref/published/turing/tu102/dev_ctrl.h
  common/inc/swref/published/turing/tu102/dev_fuse.h
  common/inc/swref/published/turing/tu102/dev_gsp_addendum.h
  common/inc/swref/published/turing/tu102/dev_nvdec_pri.h
  common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080fifo.h
  common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080gsp.h
  common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080ce.h
  common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080gr.h
  common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080pmu.h
  common/sdk/nvidia/inc/ctrl/ctrl208f/ctrl208fsec2.h
  common/sdk/nvidia/inc/ctrl/ctrl208f/ctrl208fpmu.h
  common/sdk/nvidia/inc/ctrl/ctrl0080/ctrl0080nvenc.h
  common/sdk/nvidia/inc/ctrl/ctrl0080/ctrl0080nvdec.h
  common/sdk/nvidia/inc/ctrl/ctrl0080/ctrl0080fifo.h
  common/sdk/nvidia/inc/class/cl90cdfecs.h
  common/sdk/nvidia/inc/class/cl90cdtypes.h
  nvidia/generated/g_chips2halspec_nvoc.h
  nvidia/generated/g_gpu_nvoc.h
  nvidia/src/kernel/gpu/gsp/cmp40_booter_load_610.h
Key archived evidence (all under /tmp):
  BAO_CAO_CMP40HX_TU106.md  (primary register/MMIO dump report)
  BAO_CAO_CMP40HX_03-11-2026.md, BAO_CAO_3_NHIEM_VU.md
  Plus firmware/ROM/bin dumps listed in inputs.json

SOURCE-SNAPSHOT FACTS (architectural)
--------------------------------------
1. TU106 IS architecturally recognized in this build:
   nvidia/generated/g_chips2halspec_nvoc.h DISPv0400 delete expression lists
   TU102 | TU104 | TU106 | TU116 | TU117.
2. There is NO tu106/ register directory. TU106 register namespaces come from
   common/inc/swref/published/turing/tu102/* (Turing-family, shared). Any
   TU106-specific override is absent; where I cite a register address it is
   either from the tu102 header (Turing-family shared) or from the archived
   BAR0 dump (BAO_CAO_CMP40HX_TU106.md), explicitly labelled.
3. The snapshot contains NO RM engine driver source (no fifo/pbdma/pmu/gsp/ce
   engine-init .c files). Only register namespaces (dev_*.h), RM ctrl/class
   control-interface headers (ctrl*/class*), and the cmp40 signed booter
   image header (cmp40_booter_load_610.h). RM engine programming logic is
   therefore NOT source-citable from this snapshot.
4. Engine driver dependencies named in source: RM, RPC (GSP via NV2080_CTRL_CMD_GSP_*),
   Falcon mailbox/doorbell/queue registers, PMC_ENABLE unit-enable bits, runlist.

SOURCE-BOUND RULES OBSERVED
---------------------------
- Do NOT infer operational status from capability/fuse values alone.
- Do NOT assert any engine <-> Falcon firmware-slot mapping (none is asserted in
  source; none is asserted here).
- Identify exact unavailability (missing descriptor instance / missing source tag)
  rather than claiming presence.
- Preserve raw offsets and data; mark each finding MEASURED / DECODED /
  CORROBORATED / INFERRED / UNKNOWN / BLOCKED.
- Verdict: WHOLE-GPU REVERSE ENGINEERING IS NOT COMPLETE.

SUBSYSTEM FINDINGS
==================

1) GR / FECS / GPCCS — status PARTIALLY_MEASURED
   Source support: TU106 in hal spec; PBDMA namespace (dev_esched_pbdma.h):
   NV_PBDMA base 0x00000000 mask 0x0001ffff, SIGNATURE(i)=0x10+i*8192,
   PB_HEADER(i)=0x84+i*8192, stride 8192/channel; NV_PPBDMA_SET_CHANNEL_INFO
   VEID/CHID bitfields (dev_pbdma.h). GR ctrl: NV2080_CTRL_CMD_GRP_* (ctrl2080gr.h).
   FECS: firmware-managed context-switch engine; cl90cdfecs.h exposes only
   NV_EVENT_BUFFER_FECS_CTXSWTAG_* event tags + record type 134/V2 — NO RM ctrl
   command interface for FECS programming.
   Runtime evidence (BAO_CAO_CMP40HX_TU106.md):
     NV_PMC_BOOT_0 0x0 = 0x166000A1 -> ARCH=1 Turing, IMPL=6 TU106, REV=6 A1  [MEASURED]
     gpc_nr 0x00409604 = 0x08040003 -> 3 GPC  [MEASURED]
     tpc_nr 0x00502608 = 0x00040005 -> 5 TPC in GPC0  [MEASURED]
     fuse+0x650 = 0x0004001F -> TPC mask bits0-4 = 5 enabled; matches tpc_nr [MEASURED+CORROBORATED]
     TPC map: GPC0 TPC5 returns 0xBADF1300 at all 3 offsets -> absent [MEASURED]
     17 live TPC x 2 = 34 SM / 2176 CUDA == cudaGetDeviceProperties() [CORROBORATED]
     PMC_ENABLE bit9(PGR)=0 when idle; GR woken by CUDA kernel [MEASURED]
     FECS region 0x409600-0x409700 shadow slots 0x40960C/0x409610/0x409634/0x40967C/0x409680
       accept writes but are NOT connected to topology (writing does not move tpc_nr) [MEASURED]
     FECS_SPEED_PLM 0x409650 = 0xFFFFFF8F == fuse mask copy [CORROBORATED]
   Exact unavailability:
     - No tu106 GR register header (tu102 shared only).
     - No FECS firmware binary / ucode descriptor / load address / Falcon slot in snapshot.
     - No engine<->FECS-firmware-slot mapping asserted anywhere (do not infer).
     - No GPCCS register header or control interface found.
     - No generated FIFO/GR channel descriptor instance or source tag in any dump.
   Unknown: GPCCS block; FECS ucode/slot; GR channel/runlist live state; whether fuse
   is the sole GR gate vs. additional strap/falcon gating.

2) FIFO / PBDMA — status ARCH_ONLY
   Source: NV_PBDMA registers + channel USERD target/addr fields (dev_esched_pbdma.h,
   dev_pbdma.h); PMC_ENABLE_PFIFO bit 8 (dev_pmc.h). RM ctrl:
   NV2080_CTRL_CMD_FIFO_GET_CHANNELS/GET_CHANNEL_MEM/GET_USERD_LOCATION/
   DISABLE_CHANNELS/START_RUNLIST/STOP_RUNLIST/OBJSCHED_* (ctrl2080fifo.h) and
   legacy NV0080_CTRL_CMD_FIFO_* (ctrl0080fifo.h).
   Runtime evidence: none beyond PMC_ENABLE PGR=0 idle (GR not feeding FIFO).
   Exact unavailability:
     - No tu106 FIFO/PBDMA header (tu102 shared only).
     - No generated FIFO/PBDMA channel descriptor instance or source tag in source or dumps.
     - No FIFO channel count, runlist state, or userdoorbell location observed.
   Unknown: PBDMA channel count; runlist/channel state; userdoorbell aperture.

3) Copy engines (CE) — status ARCH_ONLY
   Source: dev_ce_base.h NV_CE_BASE_GRCE_CONFIG SHARED_LCE bits3:0 + SHARED bit30;
   PCE2LCE_CONFIG PCE_ASSIGNED_LCE_NONE 0xf. RM ctrl: CE_GET_CAPS/ALL_CAPS,
   GET_PCE_LCE_MASK/SET_PCE_LCE_CONFIG/UPDATE_PCE_LCE_MAPPINGS, GET_DECOMP_LCE_MASK
   (ctrl2080ce.h). PMC_ENABLE_CE0 bit6 / CE1 bit7 / CE2 bit21 (dev_pmc.h).
   Exact unavailability:
     - dev_ce_base.h exposes config bitfields only; NO CE register base address header.
     - No CE instance count, PCE/LCE mask, or CE state in any dump.
     - No copy-engine firmware/descriptor.
   Unknown: CE count; PCE/LCE configuration; CE operational status (PMC CE bits not read).

4) PMU / SEC2 / GSP — status PARTIALLY_MEASURED
   Source:
     GSP: NV_PGSP base 0x110000 mask 0x113fff; FALCON_MAILBOX0 0x110040;
       FALCON_ENGINE 0x1103c0 (RESET bit0); MAILBOX(i)=0x110804+i*4;
       QUEUE_HEAD/TAIL(i)=0x110c00/0x110c04+i*8; MSGQ 0x110c80; EMEMC/D 0x110ac0;
       FBIF base 0x110600 (dev_gsp.h, dev_gsp_addendum.h).
     SEC2: NV_PSEC base 0x840000 mask 0x843fff; FALCON_ENGINE 0x8403c0;
       MAILBOX(i)=0x840804+i*4; FBIF 0x840600 (dev_sec_pri.h, dev_sec_addendum.h).
     Generic Falcon (dev_falcon_v4.h): CPUCTL 0x100 (STARTCPU bit1, HALTED bit4),
       BOOTVEC 0x104, HWCFG 0x108 (HWCFG2_RISCV bit10), MAILBOX0/1 0x40/0x44, OS 0x80, RM 0x84.
     RM ctrl: GSP_GET_FEATURES/GSP_CORE_TEST (ctrl2080gsp.h); PMU/SEC2 ECC only
     (ctrl208fpmu.h/ctrl208fsec2.h — control plane, not PMU register block).
     cmp40_booter_load_610.h: cmp40Booter610_IMAGE_PROD = NVIDIA-signed booter 610.57.04,
       source archive SHA256 619d7b5ce1f79c3211afdbf87d02b2174d268b10d005c5b8f994be22299be681.
       Used ONLY for the cmp40 unlock transaction; GSP launch/suspend/resume/unload use
       the driver's native Booter archive.
   Runtime evidence:
     cmpunlocker: kflcnWaitForHalt_HAL on KernelSec2; s_executeBooterUcode_TU102 runs the
     signed booter in SEC2 while SEC2 is halted (RESET_PLM=0xff). FECS selector written by
     firmware inside SEC2, not by host. dmesg: FECS=0xffffff8f SS0=0x88888888 SS1=0x8,
     WPR2=0:0x1ffffe00, RESET_PLM=0xff, ACR_TOKEN=0xc2. [MEASURED]
   Exact unavailability:
     - GSP firmware binary (gsp_tu10x.bin) absent from snapshot -> no GSP ucode/descriptor/load address.
     - No engine<->Falcon-slot mapping for GSP/SEC2/PMU asserted in source (do not infer).
     - No GSP queue head/tail or mailbox values observed in dumps.
     - PMU register block not separately defined/observed (only PMU ECC ctrl commands).
   Unknown: GSP residency/RPC state; SEC2 mailbox contents; PMU register state.
   Note: the cmpunlocker SEC2 claim is runtime evidence for the unlock path only, not a
   structural engine<->slot assignment.

5) NVENC / NVDEC — status ARCH_ONLY
   Source: NV_PNVDEC(dev)=0x00830000+dev*16384 (0x00830000-0x00833fff) (dev_nvdec_pri.h).
   RM ctrl: NVENC_GET_CAPS/MSENC_GET_CAPS (ctrl0080nvenc.h); NVDEC_GET_CAPS/BSP_GET_CAPS
   (ctrl0080nvdec.h). g_gpu_nvoc.h references GPU_MAX_MSENCS/GPU_MAX_NVDECS.
   Exact unavailability:
     - No NVENC register header at all.
     - No NVENC/NVDEC instance count, capability, or state in any dump.
     - No video-codec firmware/descriptor.
     - NVDEC base formula known but dev index/range not instantiated for this TU106.
   Unknown: NVENC presence/count; NVDEC instance count/state; video-codec status.

6) Display — status MEASURED_ABSENT
   Source support: DISPv0400 for TU106 present in hal spec (g_chips2halspec_nvoc.h).
   No tu106 display register header in snapshot.
   Runtime evidence (BAO_CAO_CMP40HX_TU106.md):
     DISP base 0x610000 / control 0x610010 / head 0x612300 / SOR 0x616000 / DAC 0x61C110
       all = 0xBADF1301 (poison = address does not exist) [MEASURED]
     PRAMIN+0x1E0200 = 0x8E0200 = 0xBADF1100 (does not exist) [MEASURED]
     scan 0x600000-0x700000 step 0x1000 -> 0/256 pages live [MEASURED]
     scan step 0x100 -> 0 pages [MEASURED]
     0x700000-0x87FFFF reads zero -> mapped but uninitialized (third state, distinct from poison) [MEASURED]
     NV_FUSE_OPT_DISPLAY 0x021C04 = 0 (read-only, NOT masked) yet block absent on all paths [MEASURED]
     Driver: Display Active Disabled / Attached No / card1 -> 0 connectors [MEASURED]
   Conclusion: display block is NOT decoded into BAR0 on any path (incl. PRAMIN) — hardware
   absent, NOT fuse-masked. Fuse=0 does NOT imply presence.
   Exact unavailability: no tu106 display reg header; no encoder/head state observable.
   Unknown: whether absence is die-feature (TU106-100-A1 binning) vs board strapping.

7) PCIe / GMMU-facing paths — status PARTIALLY_MEASURED
   Source: dev_bus.h NV_PBUS_VBIOS_SCRATCH/SW_SCRATCH = 0x1400+i*4; dev_mmu.h PDE/PTE
   format (aperture VID/SYS, size, address shift 0xc, PDE size 8, valid/privilege/RO/encrypted);
   dev_vm.h header present but NOT cross-referenced to live registers; ctrl2080bif.h BIF
   commands present.
   Runtime evidence:
     PCIe LnkCap/LnkSta 2.5GT/s x16 [MEASURED]
     LnkCap2 advertises 2.5GT/s only (Gen1); Gen2 was driver-side retrain via cmpunlocker
     (CMP40_PCIE_GEN2_V2), not fuse/hardware [MEASURED]
     BAR1 8 GiB (ReBAR enabled) [MEASURED]
     XVE 0x88000 = 0x1F0B10DE (Device ID mirror, read-only) [MEASURED]
     XVE 0x88008 = 0x030200A1 (class 0x0302 + rev A1) [MEASURED]
     XVE 0x88004 = 0x00100507 partially writable; probe bit-flip write KILLED PCIe link
     permanently (full power-off required) -> XVE 0x88000 and 0x118000 treated READ-ONLY [MEASURED]
     XP 0x118000/0x118004/0x118008 = 0x00001000/0/0 [MEASURED]
     fuse+0x4D8=0x1F0B (Device ID), fuse+0x56C=0x1F4B (Device ID secondary) [MEASURED]
   Exact unavailability:
     - No tu106 PCIe/BIF register header.
     - No GMMU/VM page-table contents or VM fault state in dumps.
     - dev_vm.h present but not cross-referenced to live MMIO.
   Unknown: GMMU page-table hierarchy; ReBAR fuse-vs-strap; link beyond Gen1 x16.

CROSS-CUTTING / VERDICT
------------------------
- Capability/fuse values are never used alone to claim operational status.
  Display: fuse=0 (not masked) but block absent -> proves fuse/absence are independent.
  GR: fuse TPC mask matches live tpc_nr, but that match is corroborated by direct
  register reads, not assumed from fuse.
- No engine <-> Falcon firmware-slot mapping is asserted anywhere in this report;
  none exists in source.
- cmpunlocker SEC2 unlock is runtime evidence only (RM->SEC2 RPC executing a NVIDIA-
  signed booter in halted SEC2). It does not imply other engines are programmable.
- Exact unavailability summary:
  * No tu106/ register directory; namespaces are TU102/Turing-family shared.
  * No RM engine driver source in snapshot.
  * No GSP firmware, FECS ucode, CE firmware, or video-codec firmware/descriptor.
  * No generated channel/descriptor instance or source tag for FIFO/PBDMA, CE, NVENC, NVDEC.
  * No engine<->Falcon slot mapping asserted anywhere.
- WHOLE-GPU REVERSE ENGINEERING IS NOT COMPLETE. Topology beyond GPC/TPC, fuse/OTP
  semantics beyond measured words, VBIOS tables, GSP function inventory, and MMIO outside
  the listed namespaces remain UNKNOWN unless separately evidenced.

REPRODUCIBILITY
---------------
Reproduce inputs/inputs.json:
  cd /tmp && for f in <each listed file>; do sha256sum "$f"; done  (compare to inputs.json)
Cite a register header line:
  grep -n "NV_PBDMA" /tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_esched_pbdma.h
All archived-evidence values are quoted verbatim from BAO_CAO_CMP40HX_TU106.md
(sha256 aa43bb2dd7fe... see inputs.json).
