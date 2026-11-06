# VBIOS_VERSION_CONSUMER — CMP 40HX (TU106) ROM/T4/shadow, Phase 16 follow-up

Created: 2026-11-04 (session). Output dir: /home/REDACTED_USER/codex-work/work_v15/PHASE16/VBIOS_VERSION_CONSUMER
Follows job: vbios_v60_structure_v1 (completed). Left-unconfirmed item: `bios->info.version[0]` used by the
VBIOS parser dispatch. Mode: ponytail full (stdlib only, read-only, outputs confined to this dir).
No hardware, no ROM loading/flashing, no keys/signatures, no tool installs.

## 1. How envytools populates bios->info.version[0] — exactly two code paths

Source: /tmp/envytools/nvbios @ git f102b82381f3f11cee113d16374c87091db039d9 (blob hashes recorded in JSON,
all verified).

| Path | File:lines | What is written | Precondition / gating |
|---|---|---|---|
| BIT 'i' table | nvbios/info.c:49-52, `envy_bios_parse_bit_i` | `version[3]=data[t+0], version[2]=data[t+1], version[1]=data[t+2], **version[0]=data[t+3] (MAJOR)**, version[4]=data[t+4]` | BIT entry type=='i', version==2 (bit.c:50); t_len>=0x19 (info.c:31). Dispatched bit.c:136-146 from `envy_bios_parse_bit`, called via bios.c:237 inside `envy_bios_parse`. |
| BMP header | nvbios/nvbios.c:849-868 (write at 858), `parse_bios_version` | `version[0]=data[offset+3]` (major), called as `parse_bios_version(bios->bmp_offset + 10)` at nvbios.c:1078 -> reads `data[bmp_offset + 13]` | `bios->bmp_offset != 0 && bios->type == ENVY_BIOS_TYPE_NV04` (nvbios.c:1077). BMP offset located by `find_string("\xff\x7fNV\0")` (bios.c:229). **Overwrites** whatever BIT 'i' wrote. |

No other code path writes `info.version[0]` (grep-verified across nvbios/). The chipset-name switch at info.c:92
and the PM_Mode dispatch at nvbios.c:1491/1497/1505 only *consume* it.

## 2. Ground truth from raw images (exact offsets and bytes, byte-compared across all three)

Inputs (sha256 verified against prior records):

- rom: /home/REDACTED_USER/codex-work/cmp40hx_transfer/CMP40HX_ORIGINAL_1MB.bin.txt, 1,048,576 B,
  dc5395dd...009dec
- t4: /home/REDACTED_USER/codex-work/cmp40hx_transfer/cmp40hx_t4.bin.txt, 495,616 B,
  aa0ebd6d...40cfdb
- shadow: /tmp/v11chk/RAW_DATA/vbios_shadow.bin, 1,048,576 B,
  2715c0b1...c55b71 (contains two BIT tables: @0x1b0 and @0x791b0)

BIT table (bit.c:70-149), rom/t4 @0x287b0: sig `ff b8 42 49 54 00 00`, header version 0x0100, hlen=12,
rlen=6, entries=17, header checksum mod256 = 0 — fully valid per bit.c:98-103 and bit.c:82-94. All 17 entries
parsed; entry[16] is type 'i' version 2, t_len=0x68, stored t_offset=0x3f4.

**Critical provenance observation (verified against raw bytes, not assumed):** in rom/t4 the BIT `t_offset`
fields are stored relative to 0x28600 (legacy x86 image base), not as absolute file offsets:
- entry[1] 'B' -> 0x28600+0x23e = 0x2883e (matches prior gap analysis: 'B' starts at 0x2883e)
- entry[7] 'P' -> 0x28600+0x2d4 = 0x288d4 (matches prior report's P-directory location)
- entry[16] 'i' -> 0x28600+0x3f4 = 0x289f4; table end 0x289f4+0x68 = 0x28a5c (matches prior report)

Stock envytools reads `t_offset` absolutely (bit.c:132, info.c uses bit->t_offset directly), so on rom/t4 it
reads the 'i' table at file offset 0x3f4 instead of 0x289f4.

| Image | Read basis | Offset read | Raw version bytes (+0..+4) | bios->info.version[0] |
|---|---|---|---|---|
| rom | stock envytools (absolute) | 0x3f4+3 = 0x3f7 | cf 00 d9 00 00 | **0x00** |
| rom | ROM-layout-intended (0x28600+t_off) | 0x289f4+3 = 0x289f7 | 00 67 06 90 06 | **0x90** |
| t4 | identical to rom in this region | same as rom | same | same |
| shadow | stock (shadow image base = 0x00000, self-consistent) | 0x3f4+3 = 0x3f7 | 00 67 06 90 06 | **0x90** |
| shadow | intended-location read | 0x289f4 | e4 f9 82 fe 4f | 0xfe (garbage — shadow's own layout places the 'i' table at 0x3f4) |

**Established version[0]: 0x90 for rom/t4** (BIT 'i' info.c:49-52 at 0x289f4). Bytes `00 67 06 90 06` decode as
version[0..4] = 90.06.67.00.06 — exactly the VBIOS string quoted in the handoff. It is therefore **confirmed as
the BIT 'i' major version**, not an incidental string, provided the offset base (0x28600) is applied. Stock
envytools on rom/t4 yields 0x00 purely because of the relative-vs-absolute t_offset mismatch; that is a parser
artifact on this image, not a second version.

**BMP path inactive in all three images:** no `\xff\x7fNV\0` signature anywhere, so `parse_bios_version`
(nvbios.c:1078) is never called; `info.version[]` comes only from BIT 'i'.

## 3. PM_Mode consumer branches evaluated against the established version and table 0x60

Target table: PERFORMANCE table whose header version byte is 0x60, at ROM 0x54155 (BIT 'P' directory entry 0x00
-> u32 0x001ab55). Raw header (byte-identical rom == t4; shadow-equivalent offset 0x2bb55 matches; shadow file
at 0x54155 is 0xFF-filled, a different image region):

`60 0a 05 07 06 0a 01 07 ...` -> table version byte = 0x60.

Dispatch (nvbios.c:1491-1528, keys on `bios->info.version[0]`, the BIOS major — NOT the table version byte):

| BIOS major | Branch taken | Table v0x60 handling | Fields consumed? |
|---|---|---|---|
| 0x90 (established) | nvbios.c:1527 `else` -> `printf("Unknown PM major version 90")` | none | No — only `printcmd(start, header_length>0?header_length:10)` hex dump |
| 0x00 (stock-envytools artifact on rom/t4) | nvbios.c:1497 `version[0] < 0x70` | schema reads version=data[start+0]=0x60, hdr=0x0a, entry_count=0x05, mode_info_length=0x07, extra_data_count=0x06, extra_data_length=0x0a, entry_length=53; table version 0x60 matches no per-entry sub-schema (0x12/0x13/0x15, 0x21-0x24, 0x25, 0x30/0x35, 0x40-0x50) -> "Version unknown" | No field adoption; entry_length=53 is generic and NOT adopted as a v60 section bound |
| (hypothetical) 0x4 | nvbios.c:1491 | old schema | n/a — precondition not met |
| (hypothetical) (major & 0xf0) <= 0x80 | nvbios.c:1505 subentry model (case 0x50 / default) | no case 0x60 | n/a — precondition not met |

Separately, table **ID 0x60** in power.c:107 P2_tbls = "DI/DT" -> `power->unk60.offset`, parsed by its own
`envy_bios_parse_power_unk60` (power.c:1605-1621) with an independent version byte at offset+0. It does not
consume `bios->info.version[0]`. `power->perf.offset` is sourced from the BIT 'P' table via parse_at (power.c:130-193)
or from BMP (nvbios.c:1095, only when bmpver>=0x527 — inactive here).

## 4. Conclusion

- `bios->info.version[0]` is populated by exactly two envytools paths: BIT 'i' (info.c:49-52) and BMP
  (nvbios.c:858, called at 1078). BMP is absent from all three images, so BIT 'i' alone decides.
- Established: **version[0] = 0x90** for rom/t4 (BIT 'i' at 0x289f4; bytes 00 67 06 90 06 = "90.06.67.00.06",
  confirming the handoff string). Stock envytools reads 0x00 on rom/t4 due to a relative-vs-absolute
  t_offset mismatch on this image (documented, not silently adopted). Shadow stock reads 0x90.
- PM_Mode dispatch vs table 0x60 (PERFORMANCE v0x60 @ 0x54155): with version[0]=0x90 the dispatch falls to
  "Unknown PM major version 90" (nvbios.c:1527) and consumes no table field; with the 0x00 artifact it enters
  the <0x70 branch but table version byte 0x60 matches no sub-schema. **No PM_Mode consumer branch adopts
  table version 0x60.**
- No section bounds, entry stride, or extent for the v60 table are adopted in any case. PERFORMANCE v60 remains
  OPAQUE; unknown fields preserved. This agrees with and closes out the open item from VBIOS_V60_STRUCTURE.

## 5. Outputs (this dir)

- `vbios_version_consumer.py` — analysis script (stdlib, read-only, 39 assert-based self-checks, all pass)
- `VBIOS_VERSION_CONSUMER.json` — machine-readable results with raw offsets, bytes, source hashes
- `run.log` — execution log (script stdout, exit 0)
- `output_hashes.json` — sha256 of every file in this directory

All prior artifacts under work_v15/PHASE16/ and elsewhere are preserved untouched.
