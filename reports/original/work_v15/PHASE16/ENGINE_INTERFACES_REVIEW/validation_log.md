VALIDATION LOG — ENGINE_INTERFACES_REVIEW (PHASE16 work_v15)
============================================================

Output dir: /home/REDACTED_USER/codex-work/work_v15/PHASE16/ENGINE_INTERFACES_REVIEW/
Files: review_findings.json, review_report.md, source_manifest.json, validation_log.md

1. JSON validity
   - review_findings.json: parses as valid JSON (json.load round-trip OK), 38777 bytes.
   - source_manifest.json: parses as valid JSON (write_file lint: ok), 9168 bytes.

2. Source-hash cross-checks (re-hashed on disk, all match)
   - /tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_fuse.h
     = f96f637c14732564911cd3211409a11b5dacd0ef27c5ad3df56e5d715d9fa30d (matches inputs.json and local SOURCES copy)
   - /tmp/nvsrc/common/inc/swref/published/maxwell/gm107/dev_fuse.h
     = 1b83b306b0996758e85eecccb1afaec5ead026fd2fb9f4cae980f5f944b25c10 (matches local SOURCES copy)
   - /tmp/nvsrc/nvidia/generated/g_chips2halspec_nvoc.h
     = 194204fd4b24bf97fccd27da61ae80ac532b74e328cc90c12d0c24512656f140 (matches inputs.json)
   - /tmp/BAO_CAO_CMP40HX_TU106.md = aa43bb2dd7fe83b9c2c889539a6e2cf9dba5f0832ce9d2abc94317f9daedb64e (matches inputs.json)
   - RAW_DATA/fuse2.json = 0e770041019aa3e4ac25733429589867a03c5542e83bc89f6937878c6e5c4ecc (matches FUSE_TU106_AUDIT inputs.dump.sha256)
   - RAW_DATA/q6.json = 6cf3874c4fde19292769f04b5dab261563e878584fdaf348a15133a5693d41cf
   - RAW_DATA/p5678.json = d004107aae6356cb7849c2ac77f3504aaac38393214ad70419e523f7eefca165
   - RAW_DATA/tu06.json = a872f2ce4fb2bd1f069127d04bd937f28d324c0023841e49c97cd8490276d5ca
   - RAW_DATA/q3_pcie.txt = 6b5aa7450b8e1d4ee9d48236d2c332922302c06fcd754ff362ea7d29f2744bce
   - RAW_DATA/bar3_hot.bin = 956c7b3ef2322c5ad5603f0cbc7f7defefa0bfb5678c276c0d91854099712d9c
   - work_v15/PHASE16/SOURCES/nvidia_tu102_dev_fuse.h = f96f637c... (identical to /tmp/nvsrc tu102 dev_fuse.h)
   - work_v15/PHASE16/SOURCES/nvidia_gm107_dev_fuse.h = 1b83b306... (identical to /tmp/nvsrc gm107 dev_fuse.h)

3. Raw fuse values re-verified from RAW_DATA/fuse2.json (base 0x21000)
   - regs[1616] (byte offset 0x650) = 0x0004001F  -> confirms BAO_CAO §3.4/§5.1 fuse+0x650 claim (raw value only; semantics UNKNOWN)
   - regs[3076] (byte offset 0xC04) = 0x00000001  -> CONFLICTS with BAO_CAO §4.1 claim of 0x00000000; UNRESOLVED_CONFLICT, both listed
   - regs[1868] (0x74C) = 1; regs[888] (0x378) = 0  -> consistent with SEC-FUSE-02/SEC-FUSE-01 SUPPORTED

4. Topology raw values trace to BAO_CAO_CMP40HX_TU106.md
   - gpc_nr 0x00409604 = 0x08040003 (3 GPC), line 43
   - tpc_nr 0x00502608 = 0x00040005 (5 TPC in GPC0), line 44
   - TPC map GPC0: TPC0-4 LIVE, TPC5 = 0xBADF1300 at 3 offsets (lines 47-59); GPC1/GPC2 all LIVE per archive
   - cudaGetDeviceProperties: multiProcessorCount=34, cores=2176 (§3.3 lines 63-72) -> CORROBORATED
   - No gpc_nr/tpc_nr/TPC_UNIT source definition found in /tmp/nvsrc (grep common/ + nvidia/) -> field semantics UNKNOWN

5. BAR1 correction verified
   - MEMORY_PCIE_REPORT.md §2: BAR1 range 0x381000000000..0x381FFFFFFFFF = 64 GiB, flags 0x0014220C
   - p5678.json Region 1 size=64G; q3_pcie.txt ReBAR BAR1 current 64GB supported 64MB..256GB; NVML BAR1 Total 65536 MiB
   - VRAM total 8192 MiB separate (smq memory_registers.json; BAO_CAO §3.3 totalGlobalMem 7803 MB after reserve)

6. Display evidence limited to exact sampled offsets/pages
   - BAO_CAO §4 lines 110-121; q6.json PDISP zones all 0xBADF1301; page_inventory.csv pages 1536-1570 POISON
   - No claim of physical silicon absence; block presence / BAR decode / clock-power gating / board causes = UNKNOWN

7. g_chips2halspec_nvoc.h applicability
   - Lines 140-141: DISPv0400 delete expression lists TU106 (architectural recognition only)
   - No tu106/ register directory in snapshot; tu102 headers = Turing-family shared; applicability = family compatibility, not TU106-specific definition
   - File exists only in /tmp/nvsrc snapshot (external), not in work_v15 SOURCES — cited as such

8. Archived vs new labeling
   - Every MMIO/fuse/PCIe value labeled archived (BAO_CAO measurement 02/11/2026; RAW_DATA dumps; q3_pcie.txt; p5678.json; q6.json; tu06.json; bar3_hot.bin)
   - Historical XVE 0x88004 probe-write (link killed, full power-off recovery) labeled archived event with warning; NOT performed by this review

9. Constraints honored
   - No hardware probe, no MMIO/PCI-config write, no driver change, no tool install, no GPU operation
   - No source-file mutation; original /home/REDACTED_USER/codex-work/PHASE16/ENGINE_INTERFACES/ untouched (not overwritten)
   - No new runtime measurement performed
   - Evidence conflicts listed and marked UNRESOLVED_CONFLICT; no convenient interpretation selected

10. Open / unresolved items (preserved, not resolved by convenience)
   - fuse+0x650 semantics UNKNOWN (no source definition, no consumer)
   - fuse+0xC04 UNRESOLVED_CONFLICT (1 vs 0); U-FUSE-009 OPEN
   - Display physical presence, BAR decode, clock/power gating, board causes UNKNOWN
   - Topology register field semantics UNKNOWN (no source definition)
   - ReBAR fuse-vs-strap UNKNOWN; GMMU page-table hierarchy UNKNOWN
   - Whole-GPU reverse engineering NOT COMPLETE (verdict preserved)

11. Regression / consistency
   - review_findings.json consistent with source_manifest.json and review_report.md on all cited hashes, offsets, and status labels.
   - No file under /tmp/nvsrc or /tmp/RAW_DATA evidence was modified; only reads and sha256.
