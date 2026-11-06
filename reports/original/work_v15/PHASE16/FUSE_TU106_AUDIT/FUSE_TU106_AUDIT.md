# FUSE_TU106_AUDIT — archived TU106 fuse/OTP source-backed audit

GPU: CMP 40HX (TU106-100-A1), PCI 10DE:1F0B. Mode: offline read-only.
UTC: 2026-11-03T18:47:59Z

## Inputs (hash-verified, read-only)
| input | path | sha256 | bytes |
|---|---|---|---|
| archived fuse dump | RAW_DATA/fuse2.json | 0e770041019aa3e4ac25733429589867a03c5542e83bc89f6937878c6e5c4ecc | 55233 |
| UNKNOWN_DATABASE.json | PHASE16/UNKNOWN_DATABASE.json | 65241527facc6be3a6ae65edcd893b20f10a780162ee54506b816524076840b7 | 26429 |
| _(note)_ | input_hashes.json recorded 23192 B / sha256 600e9694…; on-disk file is now 26429 B / sha256 65241527facc6be3a6ae65edcd893b20f10a780162ee54506b816524076840b7 (updated after that snapshot). This audit hashes the on-disk file as-is and does not modify it. | | |
| source_evidence.json | PHASE16/FUSE_SOURCE/source_evidence.json | 5206d6ce8c26c34c4748794b4d1a9dc993aabcec2b989dde55218fde065ecf55 | 4362 |
| source turing/tu102/dev_fuse.h | /tmp/nvsrc/common/inc/swref/published/turing/tu102/dev_fuse.h | f96f637c14732564911cd3211409a11b5dacd0ef27c5ad3df56e5d715d9fa30d | 2150 |
| source maxwell/gm107/dev_fuse.h | /tmp/nvsrc/common/inc/swref/published/maxwell/gm107/dev_fuse.h | 1b83b306b0996758e85eecccb1afaec5ead026fd2fb9f4cae980f5f944b25c10 | 1658 |
| source local SOURCES nvidia_tu102_dev_fuse.h | /home/REDACTED_USER/codex-work/work_v15/PHASE16/SOURCES/nvidia_tu102_dev_fuse.h | f96f637c14732564911cd3211409a11b5dacd0ef27c5ad3df56e5d715d9fa30d | 2150 |
| source local SOURCES nvidia_gm107_dev_fuse.h | /home/REDACTED_USER/codex-work/work_v15/PHASE16/SOURCES/nvidia_gm107_dev_fuse.h | 1b83b306b0996758e85eecccb1afaec5ead026fd2fb9f4cae980f5f944b25c10 | 1658 |

## Dump geometry and classification
- base (aperture): 0x21000, declared span: 32768 bytes
- dumped words: 3072 (offsets 0x0..0x2FFC step 4, contiguous), dumped bytes: 12288
- declared span extent would reach 0x7FFF; only 0x0..0x2FFC is actually dumped (remainder not dumped).
- classification: DATA=352 ZERO=518 POISON=2202 (matches dump stats)
- poison declared: ['0xbadf1100', '0xbadf1300', '0xbadf5040']; in-window non-declared error-like value 0xBADF510C at offsets ['0x178', '0x2d4', '0x4a8', '0x4ac', '0x4b0', '0x578', '0xe08'] (classified DATA, not fixed poison)
- word==1: 152 words, first 0x110 last 0x1470
- last non-poison offset: 0x17FC (6140)

## Source definitions — architectural definition vs TU106 applicability
| offset | abs_addr | register | field | bits | source file | lines | source_hash | TU106_applicable |
|---|---|---|---|---|---|---|---|---|
| 0x378 | 0x21378 | NV_FUSE_OPT_NVDEC_DISABLE | NV_FUSE_OPT_NVDEC_DISABLE_DATA | 2:0 | common/inc/swref/published/turing/tu102/dev_fuse.h | 31,32,33 | f96f637c14732564 | True |
| 0x74C | 0x2174C | NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS | NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS_DATA | 0:0 | common/inc/swref/published/turing/tu102/dev_fuse.h | 26,27,28,29 | f96f637c14732564 | True |
| 0xC04 | 0x21C04 | NV_FUSE_STATUS_OPT_DISPLAY | NV_FUSE_STATUS_OPT_DISPLAY_DATA | 0:0 | common/inc/swref/published/maxwell/gm107/dev_fuse.h | 27,28,29 | 1b83b306b0996758 | False |

Notes: architectural definition = the register/field declared in the header. TU106 applicability = evidence that this field exists in THIS TU106 part. Only the two Turing/tu102 entries are marked applicable, and even those rest on tu102->TU10x family compatibility (coordinator-accepted), not a TU106-specific header. The gm107 DISPLAY entry is NOT applicable to TU106.

## Decoded words in this dump
| offset | abs_addr | raw_value | mapped register | field | bits | field_value | decoded_meaning | TU106_applicable | gap / applicability |
|---|---|---|---|---|---|---|---|---|---|
| 0x378 | 0x21378 | 0x00000000 | NV_FUSE_OPT_NVDEC_DISABLE | NV_FUSE_OPT_NVDEC_DISABLE_DATA | 2:0 | 0x00000000 | INIT (disable=0) | True | Turing tu102 header; accepted by coordinator as TU10x/TU106-applicable field source. No TU106-specific header in snapsho… |
| 0x74C | 0x2174C | 0x00000001 | NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS | NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS_DATA | 0:0 | 0x00000001 | YES | True | Turing tu102 header; accepted by coordinator as TU10x/TU106-applicable field source. Applicability rests on tu102->TU10x… |
| 0xC04 | 0x21C04 | 0x00000001 | NV_FUSE_STATUS_OPT_DISPLAY | NV_FUSE_STATUS_OPT_DISPLAY_DATA | 0:0 | 0x00000001 | value not in defined enum | False | MAXWELL gm107 only. Dump reads 1 at this offset, which is NOT in the defined enum {0}. Rejected for TU106: cannot import… |

- 0x378 NVDEC_DISABLE bits2:0 = 0: architectural decode only; disable==0 does NOT prove NVDEC enabled (consumer not established).
- 0x74C GSP_DEBUG_DIS bit0 = 1: architectural decode only.
- 0xC04 DISPLAY = 1: Maxwell-only source; value 1 outside defined enum {0}; NOT applicable to TU106 (see U-FUSE-009).

## PDI (U-FUSE-007, kept RESOLVED/CORROBORATED)
- fuse+0x344 = 0x40680BB5, fuse+0x348 = 0x72E259ED -> PDI = 0x0000000000000000, matches nvidia-smi -q (2 independent sources).

## Physical OTP / shadow / strap / status (provenance-limited)
- Physical OTP geometry: NOT established. 152 sparse one-words with gaps do not prove physical OTP readout (coordinator/E16-006). No OTP geometry source in snapshot.
- Strap: U-FUSE-003 0xC0040000 at fuse+0x0000 != NV_PMC_BOOT_0 (0x166000A1); no strap bitfield source — strap-mirror not established.
- Status/class fields decoded only where Turing source exists (0x378, 0x74C above).

## Revisit: U-FUSE-001..006, U-FUSE-008..012, U-FUSE-009
| id | address | observed | mapped_source | recommendation |
|---|---|---|---|---|
| U-FUSE-001 | 0x021000+0x0110..0x0198 | 152 words == 1 with gaps (0x11C=0, 0x124=0); values: {'0x110': '0x00000001', '0x114': '0x0 | none (TU106) | KEEP OPEN — UNKNOWN (soften from categorical 'not physical OTP'). Gap: No Turing/TU106 dev_fuse.h definition at this offset; no consuming code identif |
| U-FUSE-002 | 0x021000+0x0718..0x0734 | 8 contiguous words = 32 bytes high entropy: {'0x718': '0x57C095DC', '0x71c': '0x839CF28E', | none (TU106) | KEEP OPEN — BLOCKED/UNKNOWN. Gap: no TU106 reference image/kernel to compare against; no hash input material beyond the block itself. |
| U-FUSE-003 | 0x021000+0x0000 | 0xC0040000 | none (TU106) | KEEP OPEN — UNKNOWN. Gap: no TU106 strap/boot-0 fuse definition; cannot name the bits. |
| U-FUSE-004 | 0x021000+0x00D4..0x00F4 | 11 words: {'0xd4': '0xFFFFFFFC', '0xd8': '0xFFFFFF8F', '0xdc': '0xFFFFFF8F', '0xe0': '0xFF | none (TU106) | KEEP OPEN — INFERRED/UNKNOWN. Gap: no bitfield source defining which bits are set. |
| U-FUSE-005 | 0x021000+0x0C1C | 0x00000038 (popcount 3: bits 3,4,5) | none (TU106) | KEEP OPEN — UNKNOWN. Gap: no Turing/TU106 dev_fuse.h definition at 0x0C1C; do not decode as GPC mask. |
| U-FUSE-006 | 0x021000+0x0178,0x02D4,0x04A8,0x04AC,0x04B0,0x0578,0x0E08 | 0xBADF510C at all 7 offsets; NOT in declared poison set {0xBADF5040, 0xBADF1300, 0xBADF110 | none (TU106) | KEEP OPEN — UNKNOWN. Gap: no definition/consumer for 0xBADF510C; do not treat as physical OTP-erase evidence. |
| U-FUSE-008 | 0x021000+0x0100..0x0240 | 155 words, values ['0x00000000', '0x00000001', '0x00000003', '0x00000004', '0x00000005', ' | none (TU106) | KEEP OPEN — UNKNOWN. Gap: no source definition; semantic identity of the values unknown. |
| U-FUSE-009 | 0x021000+0x0C04 | 0x00000001 | NV_FUSE_STATUS_OPT_DISPLAY (NOT TU106-applicable: MAXWELL gm107 only. Dump reads 1 at this offset, which is NO) | REOPEN — OPEN/UNKNOWN, INSUFFICIENT_EVIDENCE. Gap: no Turing/TU106 dev_fuse.h definition at 0x0C04; observed value 1 contradicts the only available (M |
| U-FUSE-010 | 0x021000+0x0520 | 0x16480000 | none (TU106) | KEEP OPEN — UNKNOWN. Gap: no Turing/TU106 definition at 0x0520. |
| U-FUSE-011 | 0x021000+0x0D38 | 0x000000F0 | none (TU106) | KEEP OPEN — UNKNOWN. Gap: no Turing/TU106 definition at 0x0D38. |
| U-FUSE-012 | 0x021000+0x0DC8..0x0DD0 | 0x00000007 x3 | none (TU106) | KEEP OPEN — UNKNOWN. Gap: no Turing/TU106 definition at 0x0DC8..0x0DD0. |

### Revisit detail
- **U-FUSE-001** (0x021000+0x0110..0x0198): Sparse all-bit0 words with gaps. Consistent with an enable-flag ARRAY (inferred), but coordinator rejection stands: sparse ones do NOT rule out physical OTP readout. No source definition, no second TU106 dump for comparison.
  -> KEEP OPEN — UNKNOWN (soften from categorical 'not physical OTP'). Gap: No Turing/TU106 dev_fuse.h definition at this offset; no consuming code identified in the /tmp/nvsrc snapshot. no TU106 fuse-array definition.
- **U-FUSE-002** (0x021000+0x0718..0x0734): No structure, no magic, no IV. Finite hash trials (455,689 + 12,883) returned 0 matches; no key/HMAC material available. Per constraints: no cryptographic identification from 32-byte length, no brute force.
  -> KEEP OPEN — BLOCKED/UNKNOWN. Gap: no TU106 reference image/kernel to compare against; no hash input material beyond the block itself.
- **U-FUSE-003** (0x021000+0x0000): 0xC0040000 != NV_PMC_BOOT_0 (0x166000A1). Strap-mirror hypothesis unproven: no strap bitfield definition in snapshot.
  -> KEEP OPEN — UNKNOWN. Gap: no TU106 strap/boot-0 fuse definition; cannot name the bits.
- **U-FUSE-004** (0x021000+0x00D4..0x00F4): All-high words (0xFFFFFFFC / 0xFFFFFF8F). Inferred marker only; bit meaning unknown.
  -> KEEP OPEN — INFERRED/UNKNOWN. Gap: no bitfield source defining which bits are set.
- **U-FUSE-005** (0x021000+0x0C1C): Popcount == 3 matches the known TU106 GPC count, but coordinator rejects popcount/mask inference: GPC count is topology knowledge, not a fuse bitfield. No bitfield source.
  -> KEEP OPEN — UNKNOWN. Gap: no Turing/TU106 dev_fuse.h definition at 0x0C1C; do not decode as GPC mask.
- **U-FUSE-006** (0x021000+0x0178,0x02D4,0x04A8,0x04AC,0x04B0,0x0578,0x0E08): In-window error-like value, independently re-matched against the raw dump. Not declared poison; not proof that a physical OTP block is erased (fixed-poison assumption rejected).
  -> KEEP OPEN — UNKNOWN. Gap: no definition/consumer for 0xBADF510C; do not treat as physical OTP-erase evidence.
- **U-FUSE-008** (0x021000+0x0100..0x0240): Small integer values 1..7. Version/counter/index hypotheses unproven.
  -> KEEP OPEN — UNKNOWN. Gap: no source definition; semantic identity of the values unknown.
- **U-FUSE-009** (0x021000+0x0C04): Only source is MAXWELL gm107 NV_FUSE_STATUS_OPT_DISPLAY, which defines DATA_ENABLE=0 only. The dump reads 1 — outside the defined enum. Cannot import Maxwell to TU106; no Turing/TU106 field source. Previous DECODED/resolved status is NOT supported.
  -> REOPEN — OPEN/UNKNOWN, INSUFFICIENT_EVIDENCE. Gap: no Turing/TU106 dev_fuse.h definition at 0x0C04; observed value 1 contradicts the only available (Maxwell) enum.
- **U-FUSE-010** (0x021000+0x0520): Trim/clock-setting hypotheses unproven; no source definition.
  -> KEEP OPEN — UNKNOWN. Gap: no Turing/TU106 definition at 0x0520.
- **U-FUSE-011** (0x021000+0x0D38): Binning/grade hypothesis unproven; no source definition.
  -> KEEP OPEN — UNKNOWN. Gap: no Turing/TU106 definition at 0x0D38.
- **U-FUSE-012** (0x021000+0x0DC8..0x0DD0): Count/version hypothesis unproven; no source definition.
  -> KEEP OPEN — UNKNOWN. Gap: no Turing/TU106 definition at 0x0DC8..0x0DD0.

## Kept items (no change to global DB)
- **U-FUSE-007**: RESOLVED / CORROBORATED (keep) — PDI 0x0000000000000000 at fuse+0x344/0x348 matches nvidia-smi -q (2 independent sources).
- **U-FUSE-013**: RESOLVED / DECODED (keep, narrowed) — 0x820000 is outside the 0x21000 fuse dump. 'GB100-only' is too narrow (GA100 also publishes 0x820000); applicability to TU106 not established — preserve as not-applicable-to-TU106-fuse-aperture.

## Recommendation list (this audit only; UNKNOWN_DATABASE.json NOT modified)
- OPEN (11): U-FUSE-001, U-FUSE-002, U-FUSE-003, U-FUSE-004, U-FUSE-005, U-FUSE-006, U-FUSE-008, U-FUSE-009, U-FUSE-010, U-FUSE-011, U-FUSE-012
- RESOLVED (2): U-FUSE-007, U-FUSE-013
- NEWLY DECODED (TU106-applicable source): offsets ['0x378', '0x74c'] (0x378 NVDEC_DISABLE=0, 0x74C GSP_DEBUG_DIS=1)
- SOURCE EXISTS BUT NOT TU106-APPLICABLE: offset 0xC04 (Maxwell gm107 DISPLAY; value 1 outside enum) — feeds U-FUSE-009 reopen.

## Rejected assumptions (not revived)
- Sparse-bit/ones => physical OTP cell readout (rejected by coordinator; sparse ones do not prove geometry).
- GPC popcount/mask: popcount(0x38)==3 == TU106 GPC count is NOT a fuse bitfield (coordinator rejection).
- Maxwell display import: gm107 NV_FUSE_STATUS_OPT_DISPLAY DATA_ENABLE=0 cannot be imported to TU106; dump reads 1 (outside enum).
- Fixed poison: 0xBADF510C is not in the declared poison set; not proof of physical OTP erasure.
- Crypto identification from 32-byte length: not attempted (constraint).
- Topology inference from popcount: not attempted (constraint).

## Reproduction
Run: /usr/bin/python3 PHASE16/FUSE_TU106_AUDIT/fuse_tu106_audit.py  (from work_v15)
Outputs: fuse_tu106_audit_report.json, FUSE_TU106_AUDIT.md, fuse_tu106_audit_run.log

## Exact gap statement
Every dumped offset not listed in 'Decoded words' has no Turing/TU106 dev_fuse.h definition and no identified consuming code in the /tmp/nvsrc snapshot; each remains UNKNOWN with the gap: 'no Turing/TU106 fuse field definition at this offset; no consuming code identified.' Physical OTP geometry, strap meaning, and crypto/hash meaning of the +0x718 block remain unsupported.
