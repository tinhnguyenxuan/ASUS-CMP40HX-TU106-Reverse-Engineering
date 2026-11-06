# Phase 16 evidence ledger

Scope: supplied CMP40HX/TU106 archives and binaries plus public NVIDIA sources.
These are offline observations; no new GPU measurement is implied.
The whole-GPU objective remains unproven.

## E16-001 — Original source provenance

- Archive: `../../cmp40hx_transfer/cmp40hx_research_v15_final.tar.gz`.
- SHA256: `323c96e5bf7d5512ae3e55f6040afa81373c7ab44d1f059165c536fbd2c51a45`.
- Evidence: `source_manifest.json`, `archive_audit.json`; 157 archived files
  matched the intake extraction. `legacy_verify_clean.log` records 161 PASS,
  not 162. This count does not establish semantic coverage.
- Level: DECODED archive/file consistency.

## E16-002 — GSP VA/file mapping and descriptor names

- Binary: `../outputs/gsp_tu10x.bin`, SHA256
  `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`.
- Embedded ELF starts at file `0x40`. Within the audited code/rodata sections,
  VA−file offset is `0x03ffffc0`; this is not a global mapping for NOBITS or
  every section in the file.
- Descriptor VA `0x041a70b0` maps to file `0x1a70f0`. All 186 entries in this
  loop's table resolve bounded ASCII strings using the correct mapping.
- Evidence: `elf_map.json`, `descriptor_table.json`, `gsp_summary.json`,
  `gsp_callback_verified.json`; section/segment agreement regression cases.
- Level: DECODED layout/mapping. Policy meanings still require consumers.

## E16-003 — Observed helper-return path into callback

- `0x04f57644/48` (file `0xf57684/88`) contains AUIPC/JALR targeting
  `0x04f075ec`.
- `0x04f5764c` (file `0xf5768c`, raw `93050500`) copies `a0` into `a1`.
- `0x04f57650` (file `0xf57690`, raw `e31205f8`) branches on nonzero `a0`
  to `0x04f575d4`, which loads the callback from `s3+0x30`, loads `a2` from
  stack `s0-0x88`, sets `a0=s3`, then calls at `0x04f575e0`.
- On this taken-branch path, `a1` retains the nonzero helper return. There is
  no intervening call. This disproves the old report's `a1=s4` argument claim
  for this path. It does not prove all predecessors of the containing function.
- Helper mutation of the temporary descriptor, callback identity, and the
  returned object's semantics remain UNKNOWN.
- Evidence: `gsp_callback_verified.txt/.json`,
  `gsp_callback_coordinator_review.json`; 84 instruction rows compared to the
  original bytes with no mismatch. The older Markdown report contradicts this
  evidence and is not accepted as the final semantic report.
- Reproduce: `/usr/bin/python3 -B PHASE16/gsp_callback_verify.py` from `work_v15`.
- Level: DECODED, path-scoped.

## E16-004 — Firmware container has 38 payload intervals

- Binary: `../outputs/ucodes_tu10x.bin`, SHA256
  `6027ab3736f733b5a06e6e61aaae957d1f990426a263849ebcfa8a49eeb4a5d0`;
  unchanged from the source archive.
- All 496 candidate table records and all 38 payload hashes were checked
  against the binary. No overlap/hash mismatch. Payload bytes total 8,824,912;
  table/header 11,928; padding 792; sum equals file size 8,837,632.
- The old last blob at `0x134300` was assigned 7,575,296 bytes to EOF.
  The actual payload beginning there has 183,808 bytes; the old extent contains
  28 distinct payloads. The worker report's approximation of 21 is incorrect.
- Evidence: `firmware_container_verified.json`,
  `firmware_container_coordinator_review.json`, `firmware_container_verify_run.log`.
- Reproduce: `/usr/bin/python3 -B PHASE16/firmware_container_verify.py`.
- Level: DECODED raw intervals and hashes. The first parser's generic input
  validation and field semantics need the source-backed follow-up.

## E16-005 — Source definitions found for container semantics

- `SOURCES/nvidia_bin_data_pvt.h` defines `BINDATA_UCODES_BIN_HEADER` and
  `BINDATA_STORAGE_PVT`. The latter separates `actualSize`/`compressedSize`
  (32 bits each), `pData`, `flags`, and `relOffset`; the first 64 bits must not
  be assigned an independent length meaning merely because the upper half is zero.
- The source names flag `0x04` as EXTERNAL and describes `numEntries` and the
  filename-list fingerprint. A complete binary/source cross-check is assigned
  to `JOBS/fw_source_v1`; payload engine/ISA names are not established yet.
- Local snapshot hashes, original paths, official URLs, and release-provenance
  limitations are in `SOURCES/manifest.json`. The exact local driver tag is unknown.
- Official corresponding source:
  https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/main/src/nvidia/src/kernel/core/bin_data_pvt.h
- Level: CORROBORATED source definitions; binary application under review.

## E16-006 — Fuse observations are not physical OTP geometry

- `fuse_audit.json` recomputes the archived dump as 3,072 words/12,288 bytes,
  with declared classification 352 data, 518 zero, 2,202 poison and 152 ones.
  Requested span, dumped span, last nonpoison observation, and physical aperture
  are different concepts. In particular, the old 7,680-byte calculation is wrong.
- The declared poison set does not settle the semantics of all error-like
  values such as `0xbadf510c`; these require separate classification/evidence.
- Neither sparse ones nor unsuccessful finite hash trials prove OTP geometry
  or exclude every possible hash interpretation of the block at `+0x718`.
- Source-mapped per-word audit and unknown proposals are assigned to
  `JOBS/fuse_semantics_v1`.
- Level: DECODED archived counts; physical semantics UNKNOWN.

## E16-007 — WPR registers require field extraction

- `mmio_audit.json` records raw LO `0x01f7e000`, HI `0x01ffee00` and applies
  `VAL[31:4] << 12`, yielding `0x1f7e00000` and `0x1ffee0000`.
- Decoded bound difference is 128.875 MiB. Subtracting the raw registers to
  claim a 0.50 MiB region is invalid. Allocation overlap with NVML Reserved
  and precise upper-bound interpretation require the memory follow-up.
- The scratch repro's 20-bit mask is incorrect for a 28-bit `VAL[31:4]` field.
- Official corresponding Turing source:
  https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/580.95.05/src/common/inc/swref/published/turing/tu102/dev_fb.h
- Level: source-defined extraction and DECODED arithmetic; allocation UNKNOWN.

## E16-008 — BAR0 denominator is incomplete

- The saved corrected page classes sum to 4,047, while the 16 MiB/4 KiB span
  has 4,096 pages. Forty-nine pages remain unclassified.
- The reported approximately 81% poison fraction used the classified subset;
  it must not be presented as an exhaustive whole-aperture fraction.
- Evidence: `mmio_audit.json`, `../TOPOLOGY/aperture_map.json`.
- Level: DECODED arithmetic over archived summaries, not fresh measurements.
