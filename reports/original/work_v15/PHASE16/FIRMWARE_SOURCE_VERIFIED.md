# FIRMWARE_SOURCE_VERIFIED — ucodes_tu10x.bin vs NVIDIA bindata source (CMP40HX/TU106)

## Re-run
/usr/bin/python3 firmware_container_source_verify.py   (cwd work_v15/PHASE16)
stdout/stderr/exitcode -> firmware_container_source_verify_run.log (exit_code 0)

## Inputs (read-only, no GPU/config/model/binary modification)
- outputs/ucodes_tu10x.bin: 8,837,632 B, SHA256 6027ab3736f733b5a06e6e61aaae957d1f990426a263849ebcfa8a49eeb4a5d0
- outputs/gsp_tu10x.bin: 22,901,632 B
- PHASE16/SOURCES/nvidia_bin_data_pvt.h: copied from /tmp/nvsrc/nvidia/src/kernel/core/bin_data_pvt.h, SHA256 0a46eff1c9db21f4b19d23d42c75d411685755f98f08b76247ace36a4fe1691a; official path https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/main/src/nvidia/src/kernel/core/bin_data_pvt.h (exact driver tag not established — do not claim byte-identical to current main)
- PHASE16/SOURCES/nvidia_bin_data.h: SHA256 9103cb8ab21ed3906eac3b1248409f4392a8d968b4fc15631be3854b24c4a50e; official URL in manifest.json

## Source semantics (nvidia_bin_data_pvt.h, preserved copy lines)
- BINDATA_FLAG_COMPRESSED 0x01, REFERENCED 0x02, EXTERNAL 0x04, EXTERNAL_VMWARE 0x08, HEAP_ALLOCATED 0x10 (lines 55-59)
- BINDATA_STORAGE_PVT { actualSize u32; compressedSize u32; pData const void* (pointer64); flags u32; relOffset u32 } = struct <IIQII, 24 B (lines 60-67). pData is the runtime raw-data pointer; NULL in the static table is expected for EXTERNAL entries (data fetched via bindataRegisterExternalUcodesBin callback).
- BINDATA_UCODES_BIN_HEADER { magic NvU64 = 0x5345444F4355564E ('NVUCODES' LE bytes); version NvU32 = 1; numEntries NvU32; fingerprint NvU64 } = struct <8sIIQ, 24 B (lines 84-114)
- numEntries (line 103): number of possible bindata files this driver release can have, known at build time, each file has a unique index; "This value is also embedded inside the appropriate gsp.bin"
- fingerprint (line 113): hash of all possible filenames in index order; "This value is also embedded inside the appropriate gsp.bin"; if files added/removed, pairing ucodes.bin <-> gsp.bin is broken. NOT a payload hash and NOT a payload signature.
- BINDATA_LABEL (nvidia_bin_data.h lines 42-110) and the global file slot are two index spaces; must not be conflated.

## Decoded from source + raw (CORROBORATED)
- Header @0x00 <8sIIQ: magic NVUCODES (DECODED), version=1 (DECODED), numEntries=496 at 0x0c (DECODED, from header), fingerprint64=0x8D1990AB6B98AE2B (raw DECODED; meaning = filename-index hash per source).
- Record table @0x18: 496 x <IIQII = 24 B each: actualSize u32, compressedSize u32, pData pointer64, flags u32, relOffset u32. Table end 0x2E98 (11,928). NOT <QQII with an independent 8-byte length.
- Record classes (all 496): zero 458 (all fields 0), external 38 (flags=0x04 = BINDATA_FLAG_EXTERNAL). flags distribution: 0x0 x458, 0x4 x38. pData = 0 everywhere; compressedSize = 0 everywhere. No compressed records observed -> none processed; no consumer identified, flagged unsupported if flags other than {0, 4} appear.
- first_payload = 0x2F00 DERIVED from min valid external relOffset (slot 20), NOT hardcoded. Padding 0x2E98->0x2F00 = 104 B, all zero.
- 38 payloads, 0 overlaps, 0 duplicates. Covered 8,824,912 B; uncovered 12,720 B (header+table 11,928 B + zero gaps 792 B). Last payload (slot 493, @0x85E500, len 62,720) ends exactly at EOF.
- Cross-check vs previous artifact firmware_container_verified.json: all 38 payload (slot, offset, length, sha256) identical — tool-computed, 0 mismatches.

## Field meanings: source vs unknown
- DECODED (source-backed): magic, version, numEntries, header size, record stride, actualSize, compressedSize, pData, flags (0x04 = BINDATA_FLAG_EXTERNAL), relOffset, padding/gap bytes, fingerprint value.
- Source-answered but not yet paired-proven: fingerprint = filename-index hash (source lines 105-110); numEntries = build-time possible-file count (source line 103).
- UNRESOLVED: payload ISA/load address, engine/ISA/name mapping (no generated index->engine mapping available; no engine name assigned from index), producer/consumer evidence for pData population.

## GSP pairing search (outputs/gsp_tu10x.bin)
- fingerprint64 LE bytes: 2b ae 98 6b ab 90 19 8d (0x8D1990AB6B98AE2B); numEntries LE bytes: f0 01 00 00 (496)
- Literal hits: 1 at file offset 140152 (0x223F8), section .section_task_rm_elf_rodata_instance (index 24), section VA 67248952 (0x40223B8), global VA 1073881912 (0x400223B8, derived base 0x40000000 + file_offset - 64)
- Raw context (bounded, file offset 140128-140184): 1e28140a00000000 0000ff0000ff0000 4e5655434f444553 2bae986bab90198d 010410400001040001041040000100005555555555555555 — magic "NVUCODES" immediately precedes the fingerprint, so gsp.bin embeds the ucodes header magic + fingerprint together.
- Adjacent numEntries<->fingerprint pairs: 0 (no hard pairing layout claimed).
- Pairing conclusion: literal fingerprint match in gsp.bin -> ucodes.bin <-> gsp.bin pairing corroborated at fingerprint level (same fingerprint embedded). No engine/ISA/name assigned from index.
- No mismatch conclusion drawn; compiler may construct constants when no literal exists (not applicable here since match exists).

## Status
- Container format: CORROBORATED (source definition matched to raw bytes: header <8sIIQ, records <IIQII, flags=4=EXTERNAL, numEntries/fingerprint semantics).
- engine/ISA/name mapping: NOT SOLVED (no generated mapping; not inferred from entropy).
- Whole-GPU reverse engineering: NOT DONE.
