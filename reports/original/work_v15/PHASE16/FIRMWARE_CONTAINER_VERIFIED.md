# FIRMWARE_CONTAINER_VERIFIED — ucodes_tu10x.bin (CMP40HX/TU106)

## Input (byte-verified, read-only)
- File: outputs/ucodes_tu10x.bin, size 8,837,632 B, SHA256 6027ab3736f733b5a06e6e61aaae957d1f990426a263849ebcfa8a49eeb4a5d0

## Layout proven byte-by-byte (struct, no external format source)
- Header @0x00 `<8sIIQ` = 24 B: magic `NVUCODES` (DECODED), version=1 (DECODED), numEntries=496 at 0x0c (DECODED, from header — not hardcoded), fingerprint64=0x8D1990AB6B98AE2B (raw DECODED; semantics per source = hash of filenames in index order, NOT a payload hash/signature; pairing with gsp.bin corroborated by literal match at gsp file offset 140152).
- Record table @0x18: 496 × `<IIQII` = 24 B each (actualSize u32, compressedSize u32, pData pointer64, flags u32, relOffset u32; source-corroborated via nvidia_bin_data_pvt.h lines 60-67). Table end 0x2E98 (11,928).
- Padding 0x2E98→0x2F00 = 104 B, all zero (DECODED).
- First payload @0x2F00 (slot 20: actualSize=122880, flags=4=BINDATA_FLAG_EXTERNAL, relOffset=0x2F00 — derived as min valid external relOffset, not hardcoded).

## Slot inventory (ALL 496, not the legacy 11)
- valid_marker4: 38 (marker==4, in bounds, aligned, no overlap/duplicate)
- zero: 458 (all fields 0)
- size-only: 0 ; marker!=4: 0 ; invalid/unresolved: 0

## Payloads & coverage
- 38 payloads, 0 overlaps, 0 duplicates. Covered 8,824,912 B; uncovered 12,720 B (= header+table 11,928 B + zero gaps 792 B).
- All 6 inter-payload/table gaps all-zero. Last payload (slot 493, @0x85E500 len 62720) ends exactly at EOF — no tail gap.
- Per-payload SHA256 + entropy in firmware_container_verified.json. Entropy alone does NOT imply AES/ISA/function (no IV, no magic, no producer/consumer source).

## Independent cross-check
- Scan of marker+offset in table region [0x18, 0x2F00): 38 hits, 38 confirmed against parsed records, 0 extra, 0 missing. Parse == scan.

## Field semantics
- DECODED: magic, version, numEntries, header size, record stride, actualSize, compressedSize, pData, flags (0x04 = BINDATA_FLAG_EXTERNAL per source line 57 — not an enum "present"), relOffset, padding/gap bytes.
- UNRESOLVED: fingerprint meaning now source-answered (filename-index hash, lines 105-110) and pairing corroborated by literal match in gsp.bin; record `unknown`/pData field (all 0 — pData is a runtime pointer, NULL for EXTERNAL static entries); payload ISA/load address; engine/ISA/name mapping (no generated mapping; no engine name assigned from index); producer/consumer.

## "11 blob" claim — REFUTED
- Legacy outputs/firmware_container_map.json infers header_size=496, stride=32, count=11 and makes blob10 run to EOF (size 7,575,296).
- Direct byte parse shows header=24 B, stride=24 B, count=496, 38 distinct payloads. blob10's span actually contains slots 37 + 150-156 + 449-493 = 28 payloads (tool-counted from payload offsets inside legacy extent [1262336, 10237632)) separated by zero gaps. EOF must not be used as a blob length when payloads follow.

## Status
- Container layout: DECODED (structure). Format semantics / ISA: UNKNOWN. Whole-GPU reverse engineering: NOT DONE.
