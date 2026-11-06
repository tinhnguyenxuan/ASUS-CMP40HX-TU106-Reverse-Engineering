# SECURITY_ARCH_REVIEW — CMP40HX / TU106 (Phase 16)
# Corrected audit of the prior SECURITY_ARCH report (work_v15/PHASE16/SECURITY_ARCH/)
# Isolated output directory — prior artifacts untouched.

Scope: work_v15/PHASE16/SECURITY_ARCH/audit_prior_claims.json,
       work_v15/PHASE16/SECURITY_ARCH/assertions.log,
       work_v15/PHASE16/EVIDENCE_LEDGER.md,
       work_v15/PHASE16/MEMORY_PCIE/memory_pcie_verified.json,
       work_v15/PHASE16/MEMORY_PCIE/MEMORY_PCIE_REPORT.md,
       work_v15/PHASE16/fuse_source_coordinator_review.json,
       work_v15/SECURITY/security_architecture.md,
       work_v15/SECURITY/security_registers.json,
       work_v15/EVIDENCE_LEDGER.md.

Method: read-only correctness review of archived JSON/logs + public NVIDIA source
(tag 580.95.05). No hardware probe, no keys/firmware touched. No claim of
signature validity from metadata/logs alone.

Hashes of audited inputs (sha256):
  audit_prior_claims.json          ba8723d138d663043e1fdf35743b609be79558e82f0ec46af1735f5101d5d420
  assertions.log                   5772c1160dc8e431a7b37b379b1fe145872c81395c7691144be4efffc015ab7e
  security_architecture.md         cd054a0a0eb5669284894729cd57949ca5334c95de5afc9585e6dc9bc7ea34e7
  security_registers.json          a52f335a75b2176c4790f02198fa79faa448b58b1bd7f406f94085e6a9f129f9
  PHASE16/EVIDENCE_LEDGER.md       2c7e79d75ffa1890bb4ec6024c982e1fe6edd8348506c85dbca546cbd3160eb2
  root EVIDENCE_LEDGER.md          fc953c5c6dd0dd6e1c47d9e437416dd1eb4bfe961af37f3e8098b7f2a175a528
  memory_pcie_verified.json        cc2470730a0c6cdff9d8add0c7bf8d5b057b3c1d4cc315d488899511cbf04f39
  MEMORY_PCIE_REPORT.md            ac931c72c235a12b6ffe4bb4c1ad1b3b3138182b25d2da753443f801d49044bc
  fuse_source_coordinator_review.json  ea62cf75a343ef318af57a11b723452e3c7431c9a79c3184e9ab30d0d714ea3
  fuse_source_mapping.json         eccc36e513ff5148c69725558676fadae2a9b7454be2e756b120eca617a9e8d6
  dev_fb.h (tag 580.95.05)         extracted live from official GitHub source tree

Cross-check: security_registers.json hash a52f335a... matches the input hash
recorded inside memory_pcie_verified.json — provenance chain intact.

## 1. The critical error — WPR2 raw-encoding subtraction

### Raw inputs (BAR0 MMIO read, read-only mmap of resource0)
  Offset 0x1FA824 NV_PFB_PRI_MMU_WPR2_ADDR_LO  = 0x01F7E000
  Offset 0x1FA828 NV_PFB_PRI_MMU_WPR2_ADDR_HI  = 0x01FFEE00
Source: security_registers.json registers_read[] (DATA state), corroborated by
archived dmesg "... WPR=01ffee00:01f7e000" and mmio_audit.json.
Note: archived dmesg_facts.WPR2_lo = 0x1FFFFE00 and boot WPR=0:0x1FFFFE00 are
earlier boot-stage values (kgspExecuteBooterLoad), NOT the final MMIO state;
the final BAR0 pair 0x01F7E000/0x01FFEE00 matches dmesg "WPR=01ffee00:01f7e000"
exactly (100%).

### Source field mapping (applicable source checked)
Official Turing source, tag 580.95.05:
  src/common/inc/swref/published/turing/tu102/dev_fb.h
    #define NV_PFB_PRI_MMU_WPR2_ADDR_LO        0x001FA824 /* RW-4R */
    #define NV_PFB_PRI_MMU_WPR2_ADDR_LO_VAL    31:4          /* RWEVF */
    #define NV_PFB_PRI_MMU_WPR2_ADDR_HI        0x001FA828
    #define NV_PFB_PRI_MMU_WPR2_ADDR_HI_VAL    31:4
VAL[31:4] is expressed in 4 KiB address units. Decoded byte address:
  decoded_byte_addr = (raw & 0xFFFFFFF0) << 8   [== (raw >> 4) << 12]
The low nibble of these address registers is 0, so masking is a no-op here
but the formula is required by the field definition.

### Decoded result (verified by verify_wpr.py, PASS)
  base = (0x01F7E000 & 0xFFFFFFF0) << 8 = 0x1F7E00000
  end  = (0x01FFEE00 & 0xFFFFFFF0) << 8 = 0x1FFEE0000   [exclusive]
  size = 0x1FFEE0000 - 0x1F7E00000 = 0x080E0000 = 135,135,232 bytes = 128.875 MiB
Fits within the 8 GiB FB (135,135,232 < 8,589,934,592).

### Erroneous prior path
The prior report subtracted raw encodings:
  0x01FFEE00 - 0x01F7E000 = 0x80E00 = 527,872 bytes ≈ 0.50 MiB (0.5034 MiB exactly)
This is INVALID: raw encodings are 4 KiB address units, not bytes. The field
must be extracted/shifted before subtraction. accepted E16-007 already states
this ("Subtracting the raw registers to claim a 0.50 MiB region is invalid")
and records base/end 0x1f7e00000/0x1ffee0000 via VAL[31:4] << 12. The prior
SECURITY_ARCH report nevertheless kept "WPR2 = 0.50 MiB" as SUPPORTED.

### Reconciliation with accepted E16-007 and the memory report
  E16-007: base 0x1f7e00000, end 0x1ffee0000, difference 128.875 MiB.
  MEMORY_PCIE_REPORT.md §8 (WPR, already corrected): base 0x1F7E00000,
  end 0x1FFEE0000, size 135135232 bytes (128.875 MiB), fits within 8 GiB FB,
  rule: do NOT default-subtract WPR2 from NVML Reserved 389 MiB (overlap unknown).
  This review: base/end/size identical to both above → RECONCILED.
  Candidate confirmed: [0x1F7E00000, 0x1FFEE0000), 0x80E0000 bytes, 128.875 MiB.

## 2. Every conclusion that depended on 0.50 MiB — corrected/retracted

### audit_prior_claims.json — SEC-WPR-03 (status SUPPORTED) → RETRACTED
  Claim: "WPR2 = 0.50 MiB (0x01F7E000..0x01FFEE00), not 457 MiB"
  Reason prior: "MMIO LO=0x01F7E000 HI=0x01FFEE00 -> size 0x80E00 = 515.5 KiB ≈ 0.50 MiB. Matches dmesg WPR pair 100%."
  Correction: status RETRACTED. The byte range quoted (0x01F7E000..0x01FFEE00)
  conflates raw MMIO encodings with byte addresses. Corrected decode:
  [0x1F7E00000, 0x1FFEE0000), size 0x080E0000 = 135,135,232 bytes = 128.875 MiB.
  Source ref: dev_fb.h tu102 VAL[31:4] 4 KiB units; decode (raw & 0xFFFFFFF0) << 8.
  dmesg corroboration is for the decoded pair WPR=01ffee00:01f7e000 applied to the
  field mapping, not for raw subtraction.
  Retraction recorded: prior "SUPPORTED" status and "0.50 MiB" figure are
  withdrawn; corrected figure 128.875 MiB.

### security_architecture.md — §2.2, §2.3, §6.1
  §2.2 table row "NV_PFB_PRI_MMU_WPR2_ADDR_HI | 0x1FA828 | 0x01FFEE00 | 0.50 MiB (vùng WPR2)" → size column corrected to 128.875 MiB with decoded range note.
  §2.3 line "WPR2 = 515.5 KiB (0.50 MiB) — không phải 457 MiB (xem mục 6.1)" → corrected to "WPR2 = 128.875 MiB (0x080E0000 bytes), decoded from VAL[31:4]; not 457 MiB".
  §6.1 row "WPR2 | MMIO + dmesg | 0.50 MiB (515.5 KiB) | 0x01F7E000..0x01FFEE00 — khớp dmesg 100%" → corrected to decoded [0x1F7E00000, 0x1FFEE0000), 128.875 MiB; dmesg match confirmed at field level.
  §6.1 paragraph "Kích thước WPR2 = 0x01FFEE00 - 0x01F7E000 = 0x80E00 = 515.5 KiB ≈ 0.50 MiB." → replaced with decoded subtraction 0x1FFEE0000 - 0x1F7E00000 = 0x080E0000 = 128.875 MiB.
  §6.1 conclusion "388.5 MiB vẫn là carveout chưa giải (U-MEM-001 vẫn mở)" → the WPR2-size-based reserved-memory commentary changes: WPR2 (128.875 MiB) is no longer treated as negligible vs 389 MiB Reserved; overlap between WPR2 and NVML Reserved 389 MiB remains UNKNOWN (per memory report rule). The claim "388.5 MiB still unresolved carveout" derived partly from WPR2=0.5 MiB is retracted in its WPR2-dependent form; status of U-MEM-001 = UNKNOWN pending overlap analysis. Genuine facts preserved: NVML Total 8192/Reserved 389/Used 0/Free 7804 MiB, delta 1 MiB unexplained.

### assertions.log — historical failures
  Run 1 (lines 1-27): [FAIL] NVDEC_DISABLE at 0x21378 line 31; [FAIL] GSP_DEBUG_DIS at 0x2174C line 26. Result FAILURES.
  Run 2 (lines 28-50): ALL PASS after source re-checked (dev_fuse tu102 defines 2 registers).
  Run 3 (lines 51-73): ALL PASS (repeat).
  Explanation of why self-consistent assertions missed the semantic WPR formula error:
  The assertions only checked surface consistency — "WPR2 MMIO LO=0x01f7e000", "WPR2 MMIO HI=0x01ffee00", "WPR2 size = 0x80E00", "WPR2 matches dmesg pair". Each is true in isolation: the raw register values are exactly those, their raw difference is exactly 0x80E00, and the dmesg pair textually matches. No assertion applied the source field mapping (VAL[31:4] 4 KiB units → byte decode) because the assertions were written against raw MMIO values, not decoded byte addresses. Self-consistency among raw values cannot detect that the *formula* (raw subtraction vs field-extracted subtraction) is semantically wrong. An assertion checking `decode(HI) - decode(LO) == 0x080E0000` or cross-checking against E16-007 would have caught it. This is a specification/semantics gap, not a data gap: all inputs were correct; the interpretation of VAL as raw bytes instead of 4 KiB units was wrong.

### MEMORY_PCIE_REPORT.md §8 WPR
  Already corrected in source (validated formula, base/end/size 128.875 MiB,
  no default subtraction from Reserved). No change needed; corroborated by this
  review.

### EVIDENCE_LEDGER.md
  Root ledger §VÒNG P8 (lines 403-406) lists WPR0/WPR1/WPR2/WPR2-alt as MEASURED
  byte ranges derived from raw BAR0 values (e.g. WPR2 = 0x01F78200..0x01F7E000,
  WPR2 alt = 0x01FFEE00..0x1FFFFFF0) — these are raw-offset interpretations,
  not field-decoded byte ranges. PHASE16/EVIDENCE_LEDGER.md E16-007 already
  rejects raw subtraction. Both ledgers are retained as-is here with a note:
  WPR ranges listed there are raw MMIO observations; their byte-address meaning
  requires the VAL[31:4] decode applied in this review. No overwrite of either
  ledger file (isolated output directory).

### fuse_source_coordinator_review.json
  Does not depend on WPR2/0.50 MiB (fuse OTP geometry, 0xBADF510C offsets,
  semantic proposal rejections U-FUSE-001/005/009/013). No change needed;
  status partial_accepted_semantic_proposals_require_correction preserved.

## 3. GPU firmware signed/authenticated boot — evidence label audit

Distinguishing archived dmesg statements, source metadata, and independent
cryptographic verification. No signature validity claimed from metadata/logs
alone.

### Genuinely supported (archived dmesg statements — MEASURED as log content, not as cryptographic proof)
  dmesg lines from security_registers.json boot_log:
    [4.754233] NVRM: GPU0 _kgspCreateSignatureMemdesc: CMP40_COMPUTE_UNLOCK_V526:
      signed fullspeed stock-relock WPR-down commit ...
    [4.891986] NVRM: GPU0 kgspCmp40RebuildStockSignature: CMP40_COMPUTE_UNLOCK_V132:
      restored stock signature in-place phys=0xffe40000 backing=0xfa00 advertised=0x1000
    [4.891957] NVRM: GPU0 kgspExecuteBooterLoad_TU102: CMP40_COMPUTE_UNLOCK_V526:
      SIGNED_FULLSPEED_STOCK_RELOCK_WPR_DOWN_PASS
  These establish that the driver LOGGED signature-related events and an
  in-place restore. Label: MEASURED (log content). They do NOT constitute
  independent cryptographic verification of a signature.

### Source metadata (not a signature verification)
  cmp40_booter_load_610.h (source archive 610.57.04) contains SIG_DBG/SIG_PROD
  signature metadata (16 B each). Label: source metadata — documents that
  signature slots exist in source. Does not prove any particular firmware image
  was signed or that a signature validates.

### Independent cryptographic verification
  None present in the audited inputs. No hash of a firmware signature blob
  against an embedded key, no certificate chain verification, no signature
  algorithm check over the firmware bytes was performed or is claimed.
  Label: UNKNOWN / NOT PERFORMED.

### Conclusion on firmware signing (corrected)
  The claim "GPU firmware is signed and signature is restored in-place" (SEC-SB-02,
  status MEASURED) is partially supported: "signature-related events logged and
  in-place restore logged" is MEASURED from dmesg; "firmware is signed / signature
  valid" is NOT independently verified → status becomes MEASURED (log statements)
  + UNVERIFIED (cryptographic validity). Do not claim signature validity merely
  from metadata or logs. Secure Boot state of the GPU itself remains UNKNOWN;
  host Secure Boot is OFF (driver taint, MEASURED).

## 4. Privilege boundaries

  PLM: FECS_PLM=0xFFFFFF8F, RESET_PLM=0x000000FF, plm_before/after/restored
  =0xFFFFFF8F, SS0=0x88888888, SS1=0x00000008, ACR_TOKEN=0xC2 — all MEASURED
  from dmesg only. BAR0 PLM registers 0x1FA840/0x1FA844 read 0xBADF5040 (poison,
  outside BAR0 decode window) → real PLM register values not readable via MMIO.
  Falcon privilege level actual: UNKNOWN. SEC2 DMEM zeroed after use
  [0x00000000,0x00010000) 64 KB — MEASURED from dmesg FULL_DMEM_ZERO_PASS.
  DMA mask 47-bit, IOMMU group 31 (dedicated), BAR1 64 GiB — MEASURED, active
  isolation boundary. Confidential Computing: OFF (nvidia-smi Total/Used/Free
  0 MiB) — MEASURED.

## 5. Preserved, corrected, and unknown (machine-readable corrected claims below)

  Preserved genuine facts: dev_fuse.h tu102 defines exactly 2 fuse registers
  (NV_FUSE_OPT_NVDEC_DISABLE 0x21378 bits 2:0; NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS
  0x2174C bit 0); WPR2 registers at 0x1FA824/0x1FA828 exist and match dmesg
  pair at field level; raw MMIO LO=0x01F7E000 HI=0x01FFEE00; 8 unknown MMIO
  offsets (0x1FA800/04/10/14/20/2C/30) unnamed in source; PLM registers poison;
  driver Linux unsigned (module verification failed taint); CC off; firmware
  signature events logged but cryptographic validity unverified.

  Corrected/retracted: SEC-WPR-03 0.50 MiB → 128.875 MiB; WPR byte-range rows
  in security_architecture.md §2.2/§2.3/§6.1; reserved-memory commentary
  "388.5 MiB carveout" WPR2-dependent portion retracted (overlap UNKNOWN).

  Unknowns kept: WPR2 vs NVML Reserved overlap; WPR2_lo stage value 0x1FFFFE00
  vs final MMIO value applicability; GPU Secure Boot state; firmware signature
  cryptographic validity; Falcon actual privilege level; 0xBADF510C fuse
  semantics; fuse physical OTP geometry.

## 6. Machine-readable corrected claims
See corrected_claims.json in this directory.

## 7. Reproducible script/log
verify_wpr.py + verify_wpr.log in this directory. Run:
  python3 verify_wpr.py   # prints PASS and all decode values
