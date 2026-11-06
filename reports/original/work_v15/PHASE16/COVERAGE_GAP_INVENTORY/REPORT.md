CMP40HX / TU106 — Coverage/Gap Inventory (PHASE16)
=====================================================

Scope
-----
Offline, read-only evidence audit of the supplied cmp40hx_research_v15_final.tar.gz
archive and public NVIDIA/envytools sources. No new hardware access, no MMIO/OTP/
PCIe writes, no ROM flash/reload, no driver reload/reboot, no clock/voltage changes,
no exploit/bypass, no key extraction. No file under COORDINATION.json or
UNKNOWN_DATABASE.json was modified; no ongoing worker output was touched. All outputs
are isolated under work_v15/PHASE16/COVERAGE_GAP_INVENTORY/.

Completion rule (from COORDINATION.json)
----------------------------------------
The full CMP40HX/TU106 reverse-engineering objective remains UNPROVEN. Tests/PASS
counts, file presence, manifests, prose reports, and live worker state never establish
whole-GPU completion. Every workstream below is PARTIAL; none is VERIFIED as a whole.

Inventory files
---------------
- input_hashes.json   SHA-256 of all 41 evidence inputs inspected (archive, handoff,
                      coordination, ledger, both unknown-DB versions, audits, all
                      coordinator reviews).
- requirements.json   Hierarchical requirement-by-requirement matrix (11 workstreams,
                      45 requirements) with status, evidence level, exact evidence paths,
                      and gaps per requirement.
- matrix.json         Flat 45-row version of the same matrix.
- REPORT.md           This file.

Status key
----------
VERIFIED / PARTIAL / CONTRADICTED / MISSING (requirement status)
MEASURED / DECODED / CORROBORATED / INFERRED / UNKNOWN / BLOCKED (evidence level)

Workstream summary (11 workstreams, 45 requirements)
----------------------------------------------------
Workstream                          Req  VERIFIED PARTIAL CONTRADICTED MISSING  Overall
GSP-CALLBACK                          4       2       1         0        1      PARTIAL
FW-CONTAINER                          5       2       2         0        1      PARTIAL
FUSE-OTP                              5       1       2         0        2      PARTIAL
VBIOS                                 5       1       3         0        1      PARTIAL
MMIO-TOPOLOGY                         4       0       3         0        1      PARTIAL
MEMORY                                4       2       0         0        2      PARTIAL
PCIE                                  3       0       2         0        1      PARTIAL
SECURITY-ARCHITECTURE                 4       2       1         0        1      PARTIAL
GSP-FULL                              4       0       3         0        1      PARTIAL
ENGINE-INTERFACES                     3       0       1         0        2      PARTIAL
INTEGRATION                           4       0       1         2        1      PARTIAL
Total                                45       8      17         2       13

Key verified (raw-structure) findings
-------------------------------------
- GSP VA=file mapping: VA = file_offset + 0x3FFFFC0 (inner ELF offset 0x40), verified on
  6 mappings (loop, entry, JAL, callback, descriptor table, caller). Not global for
  NOBITS/every section. [EVIDENCE_LEDGER.md E16-002; CHECKPOINT.json]
- Callback path (observed window, raw bytes, 0 mismatches): helper 0x4f075ec via
  AUIPC/JALR at 0x4f57644/48; mv a1,a0 at 0x4f5764c; bnez a0 -> 0x4f575d4 at 0x4f57650;
  callback at 0x4f575e0 via jalr a5 where a5 = ld [s3+0x30], a2 = lhu [s0-0x88], a0 = s3.
  a1 retains the helper return on this path. The old a1=s4 claim is DISPROVED on this
  path. [gsp_callback_verified.json/.txt; gsp_callback_coordinator_review.json]
- Firmware container: NVUCODES ver=1 count=496@0x0c; 496 x 24-byte records; 38 payloads;
  no overlap/hash mismatch; coverage 8,824,912 + 11,928 + 792 = 8,837,632 = file size.
  Legacy "11 blobs" refuted (496 is count not header size; stride 24 not 32; blob10
  candidate is 183,808 B; its old extent holds 28 payloads, not 21). [firmware_container_verified.json;
  firmware_container_coordinator_review.json; firmware_audit.json]
- Fuse dump: 3072 words/12,288 B contiguous; 352 DATA / 518 ZERO / 2202 POISON / 152 ones;
  old 7,680-byte calculation wrong. PDI 0x0000000000000000 matches nvidia-smi (CORROBORATED).
  [fuse_audit.json; fuse_source_coordinator_review.json; U-FUSE-007]
- VBIOS: ROM sha256 dc5395dd...; T4 495,616 B; 19-byte diffs = 6 float32 microvolt fields
  + checksum byte; 8-bit additive checksum reproduced; payload = rom[0:0x79000]; shadow
  @0x300000 matches rom[0x28600:] except 14 bytes (PPID serial). [vbios_audit.json;
  EVIDENCE_LEDGER.md work_v15 E01-E09]
- WPR: raw LO 0x01f7e000 / HI 0x01ffee00; VAL[31:4]<<12 -> LO 0x1F7E00000 / HI
  0x1FFEE0000; decoded bound difference 128.875 MiB. Raw-register subtraction (0.5 MiB)
  invalidated. [mmio_audit.json; E16-007; WPR endpoint review]
- No encryption inferred from entropy (4 high-entropy blobs, 7.998; AES vs compression
  not distinguished). No exploit/bypass work (safety_compliance all readonly). [E09;
  CHECKPOINT.json]

Key contradictions (must be corrected before integration)
---------------------------------------------------------
1. 162/162 PASS claim vs archive_audit.json: 161 PASS lines, 0 FAIL. Test count never
   established semantic coverage. [archive_audit.json]
2. Unknown DB counts diverge: work_v15 version 35 open/10 resolved vs PHASE16 version
   36 open/9 resolved; U-GSP-008 missing from database. [both UNKNOWN_DATABASE.json;
   unknown_audit.json]
3. Callback a1=s4 claim disproved by raw callback evidence; older Markdown report not
   accepted as final semantic report. [gsp_callback_coordinator_review.json]
4. ENGINE_INTERFACES report claims rejected: fuse+0x650 "TPC mask" (no TU106 source
   field), display fuse=0 (RAW_DATA/fuse2.json shows fuse+0xC04=1), BAR1=8 GiB
   (MEMORY_PCIE decoded 64 GiB window), "display hardware absent" (poison != absence),
   topology 3/17/34 un-sourced. [ENGINE_INTERFACES_COORDINATOR_REVIEW.md]
5. MMIO 52/52 register-match claim not accepted (constants/enums mixed into address
   namespace). [mmio_namespace_coordinator_review.json]

Preserved unresolved gaps (deliberately NOT closed)
---------------------------------------------------
- Firmware payload/engine mapping: 30/38 payloads UNKNOWN; 8 Falcon labels medium-confidence
  only; ISA/load metadata unidentified; blob6/8 differ by 2 timestamp windows + 2 unexplained
  bytes; encryption vs compression unproven (explicitly not inferred).
- GSP caller/callback/CFG/dataflow: callback target *(s3+0x30) unresolved; predecessors not
  exhaustive; a0/a1/a2 last definitions partial; CFG capped at 6,000 instructions / 603 blocks,
  not fixpoint; indirect targets unknown; symbolic dataflow defects uncorrected (lhu width,
  store has no destination, S-immediate address, operand capture order).
- Fuse semantics: physical OTP cell geometry unknown; +0x718 opaque 32-byte block hash-blocked
  (0 matches across 455,689 + 12,883 trials); ~3,070 fuse words unmapped; topology mask
  inference rejected; fuse+0x0C04 display meaning TU106-unestablished.
- VBIOS unsupported schemas: version-0x60 tables unsupported; key block/certificate table
  (U-VBIOS-001) and NPDS 0x70 digest list (U-VBIOS-003) meanings unknown; NVGIf #2 nature
  unknown; general BIT parser missing (inherited Turing pointer formula not general); slot17
  header shape valid but semantics unknown.
- MMIO sampling: 0.390625% byte coverage (4 u32 per 4 KiB page); 49 unclassified pages; poison
  vs physical absence vs decode window vs gating vs privilege unresolved.
- Topology: GPC/TPC/SM/ROP/L2 not reconstructed from raw values; archived 3/17/34 un-sourced;
  L2TLB/L2 conflation warned.
- Memory allocation: GMMU/BAR3 undecoded; 430 MiB VRAM gap (8192 physical vs 7762 available)
  unexplained; WPR2 (528 KB) cannot explain it; WPR/NVML Reserved overlap unknown; HI bound
  exclusivity unproven.
- PCIe: capability/runtime link decode incomplete; advertised vs accessible BAR span not
  distinguished (BAR1 64 GiB vs 8 GiB VRAM unreconciled).
- Security architecture: PLM/ACR/SEC2 roles and privilege boundaries uncorroborated; signature
  validity unverified; historical dmesg = log assertions only.

Next concrete offline research actions (read-only, no hardware)
--------------------------------------------------------------
NA-1 GSP-CALLBACK: fix gsp_callback_verify.py ELF base/section handling; re-run with
  /usr/bin/python3; enumerate all callback predecessors and last defs of a0/a1/a2 on all
  paths; resolve *(s3+0x30) callback target. Do not restart live worker PID 1650946.
  Evidence: gsp_callback_verify.py, gsp_callback_verified.json, gsp_tu10x.bin,
  REVIEW_NOTES.md.
NA-2 GSP-FULL: remove 6,000-instruction cap in GSP_HEADER_CONSUMER_FOLLOWUP; run to fixpoint;
  correct dataflow defects; poll existing live worker, no duplicate dispatch.
  Evidence: header_consumer_followup.py, run.log, GSP_FOLLOWUP_DATAFLOW_REVIEW.md.
NA-3 FW-CONTAINER: apply SOURCES/nvidia_bin_data_pvt.h (BINDATA_STORAGE_PVT fields) to all
  38 payloads; disassemble plaintext payloads with capstone RISCV64+RISCVC on /usr/bin/python3
  (capstone 5.0.7 confirmed); record high-entropy blobs as UNKNOWN.
  Evidence: firmware_container_verified.json, SOURCES/manifest.json, payload_isa_verified.json.
NA-4 FUSE-OTP: source-map all 3,072 fuse words against SOURCES/nvidia_tu102_dev_fuse.h
  (fields 0x2174c, 0x21378); classify +0x718 block; obtain second TU106/TU104 fuse dump;
  document hash trials as blocked.
  Evidence: fuse_audit.json, fuse_source_coordinator_review.json, fuse2.json,
  UNKNOWN_DATABASE.json U-FUSE-002/U-FUSE-005.
NA-5 VBIOS: write general BIT parser (not inherited Turing formula); decode slot17 and
  power/perf tables via envytools nvbios source (hashes in vbios_perf_schema_coordinator_review.json);
  resolve U-VBIOS-001/U-VBIOS-003 and NVGIf #2.
  Evidence: vbios_audit.json, vbios_typed/vbios_perf coordinator reviews, SOURCES/manifest.json.
NA-6 MMIO-TOPOLOGY: full-page classification beyond 4-u32 sampling; reconcile 49 unclassified
  pages; map bitfields from dev_top/dev_gr headers; reconstruct GPC/TPC/SM/ROP/L2 only from
  traced raw values.
  Evidence: mmio_audit.json, mmio_topology/vbios coordinator reviews, page_inventory.csv,
  aperture_map.json.
NA-7 MEMORY/PCIE: decode GMMU/BAR3 structures (bar3_hot.bin, bar3_entries.csv); verify WPR HI
  exclusivity from implementation; reconcile BAR1 64 GiB vs 8 GiB VRAM via raw resource
  ranges; explain 430 MiB VRAM gap without raw-register subtraction.
  Evidence: mmio_audit.json, memory_pcie_verified.json, bar3_hot.bin, U-MEM-001/U-BAR3-001/002.
NA-8 SECURITY-ARCHITECTURE: source-corroborate PLM/ACR/SEC2 roles/privilege boundaries;
  record signature validity unverified; treat dmesg as log assertions only.
  Evidence: SECURITY_ARCH/REPORT.md, boot_chain.json, SECURITY_ARCH_REVIEW_COORDINATOR.md,
  findings_lossless.json.
NA-9 INTEGRATION: reconcile UNKNOWN_DATABASE versions (35/10 vs 36/9), add U-GSP-008; add
  reproduction commands to ledger entries lacking them; correct 162->161 PASS citations;
  maintain this inventory as work continues.
  Evidence: both UNKNOWN_DATABASE.json, unknown_audit.json, EVIDENCE_LEDGER.md, archive_audit.json.

Required missing source/data
----------------------------
- NVIDIA open-gpu-kernel-modules Turing headers for TU106: dev_top.h, dev_gr.h, dev_fb.h
  (SOURCES/ currently holds only nvidia_tu102_dev_fuse.h, nvidia_gm107_dev_fuse.h,
  bin_data_pvt.h, bin_data.h).
- Exact driver release tag for source provenance (SOURCES/manifest.json: "exact driver tag
  not established").
- Second TU106/TU104 fuse dump for fuse-word cross-comparison (none available).
- GSP-RM source/consumer documentation for descriptor-table semantics (name_ptr union,
  f08/f18 fields) and RPC/engine register-access interfaces.
- VBIOS key block/certificate format spec and NPDS type-0x70 digest-list semantics source.
- envytools nvbios source (/tmp/envytools/nvbios/bit.c, power.c, nvbios.c) already
  snapshotted with SHA-256 recorded — available input, not missing.

Files not changed
-----------------
COORDINATION.json, UNKNOWN_DATABASE.json (both versions), EVIDENCE_LEDGER.md, and all
ongoing worker outputs (GSP_HEADER_CONSUMER_FOLLOWUP, FW_PAYLOAD_DEEP, mmio
reconciliation, engine interfaces) were read only and not modified.