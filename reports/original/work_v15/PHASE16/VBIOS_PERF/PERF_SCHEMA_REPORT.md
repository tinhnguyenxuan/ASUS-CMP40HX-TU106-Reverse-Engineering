PERF SCHEMA VERIFY REPORT — CMP40HX / TU106 VBIOS
==================================================

Input:  /home/REDACTED_USER/codex-work/work_v15/outputs/CMP40HX_ORIGINAL_1MB.bin
SHA256: dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec
Size:   1,048,576 B (1 MiB)
Script: perf_schema_verify.py  (stdlib only, read-only, no ROM writes)

Outputs:
  perf_schema_verified.json   — full machine-readable result
  run.log                     — concise run log
  PERF_SCHEMA_REPORT.md       — this file

---- 1. BIT P token (source: envytools/nvbios/bit.c, power.c) -----------------

BIT table header (bit.c lines 75-78):
  offset+6  uint16  version        = 0x0100
  offset+8  uint8   hlen           = 12   (header length)
  offset+9  uint8   rlen           = 6    (record stride)
  offset+10 uint8   entries        = 17

BIT table entry (bit.c lines 124-127, 6 bytes each):
  +0  uint8  type        — token ID (ASCII)
  +1  uint8  version     — token version
  +2  uint16 t_len       — length of token data (LE)
  +4  uint16 t_offset    — pointer to token data (LE)

Token 'P' (index 7): type='P'(0x50), version=2, t_len=224, t_offset=724 (0x02d4).
  Source: bit.c bit_types[] — { 'P', 2, envy_bios_parse_bit_P } /* Power v2 */
  P token data base = ptr_map(724) = 0x28600 + 724 = 0x288D4 (= PERF_OFF).
  P token data is read as 4-byte uint32 pointers (power.c print_bit_P, i+=4).

Slot capacity check:
  56 slots x 4 bytes = 224 bytes == t_len 224 bytes  →  FITS EXACTLY.
  All 56 slots lie within the real token length. No slot exceeds t_len.

Null vs imagebase (ptr_map):
  ptr == 0   → null slot (no table), 16 of 56 slots are null.
  ptr != 0   → file offset = ROM_IMG + ptr (+EFI_SZ if ptr >= LEGACY_SZ).
  Pointer 0 is never treated as imagebase; it means "absent".

---- 2. P2_tbls slot → table name (source: envytools/nvbios/power.c, ver 2) ----

power.c P2_tbls[] maps byte offset (slot_index × 4) → table name.
Offsets 0x00–0x98 (slots 0–38) have names; 0x9c+ are "UNKNOWN" in source.

Slot | P2 byte offset | Table name (P2_tbls)     | Raw ptr  | Mapped file off | Status
-----|----------------|--------------------------|----------|-----------------|--------
  0  | 0x00           | PERFORMANCE              | 0x01ab55 | 0x054155        | non-null
  1  | 0x04           | MEMORY TIMINGS MAPPING   | 0x01b000 | 0x054600        | non-null
  2  | 0x08           | MEMORY TIMINGS           | 0x01bac4 | 0x0550c4        | non-null
  3  | 0x0c           | VOLTAGE                  | NULL     | —               | null
  4  | 0x10           | THERMAL                  | NULL     | —               | null
  5  | 0x14           | THERMAL DEVICES          | 0x01f123 | 0x058723        | non-null
  6  | 0x18           | THERMAL COOLERS          | NULL     | —               | null
  7  | 0x1c           | PERF SETTINGS SCRIPT     | NULL     | —               | null
  8  | 0x20           | VOLT MAPPING             | 0x01ce9c | 0x05649c        | non-null
  9  | 0x24           | VENTURA                  | NULL     | —               | null
 10  | 0x28           | POWER SENSE              | 0x01e3e0 | 0x0579e0        | non-null
 11  | 0x2c           | POWER BUDGET             | 0x01e892 | 0x057e92        | non-null
 12  | 0x30           | BOOST                    | NULL     | —               | null
 13  | 0x34           | CSTEP                    | NULL     | —               | null
 14  | 0x38           | POWER BASE CLOCK         | 0x01ad26 | 0x054326        | non-null
 15  | 0x3c           | POWER TOPOLOGY           | 0x01e53f | 0x057b3f        | non-null
 16  | 0x40           | POWER LEAKAGE            | 0x01ef61 | 0x058561        | non-null
 17  | 0x44           | PERF TEST SPEC           | 0x01aff2 | 0x0545f2        | non-null  ← slot 17
 18  | 0x48           | THERMAL CHANNEL          | 0x01f15d | 0x05875d        | non-null
 19  | 0x4c           | THERMAL ADJUSTMENT       | 0x01f206 | 0x058806        | non-null
 20  | 0x50           | THERMAL POLICY           | 0x01f079 | 0x058679        | non-null
 21  | 0x54           | PSTATE MEMORY CLK FREQ   | NULL     | —               | null
 22  | 0x58           | FAN COOLERS              | 0x01f224 | 0x058824        | non-null
 23  | 0x5c           | POWER FAN_MGMT           | 0x01f25e | 0x05885e        | non-null
 24  | 0x60           | DI/DT                    | NULL     | —               | null
 25  | 0x64           | FAN TEST                 | 0x01f2d0 | 0x0588d0        | non-null
 26  | 0x68           | VOLTAGE RAIL             | 0x004d7b | 0x02d37b        | non-null (legacy range)
 27  | 0x6c           | VOLTAGE DEVICE           | 0x004d17 | 0x02d317        | non-null (legacy range)
 28  | 0x70           | VOLTAGE POLICY           | 0x004d8e | 0x02d38e        | non-null (legacy range)
 29  | 0x74           | LOW POWER                | 0x01cc22 | 0x056222        | non-null
 30  | 0x78           | LOW POWER PCIe           | 0x01cc4b | 0x05624b        | non-null
 31  | 0x7c           | LOW POWER PCIe-PLATFORM  | 0x01cc8c | 0x05628c        | non-null
 32  | 0x80           | LOW POWER GR             | 0x01ccd1 | 0x0562d1        | non-null
 33  | 0x84           | LOW POWER MS             | 0x01ccf4 | 0x0562f4        | non-null
 34  | 0x8c           | LOW POWER DI             | 0x01cd46 | 0x056346        | non-null
 35  | 0x90           | LOW POWER GC6            | 0x01cd6d | 0x05636d        | non-null
 36  | 0x94           | LOW POWER PSI            | 0x01cddc | 0x0563dc        | non-null
 37  | 0x98           | THERM MONITOR            | 0x01f214 | 0x058814        | non-null
 38  | 0x9c           | OVERCLOCKING             | 0x01f2de | 0x0588de        | non-null
 39-48| 0x9c+          | UNKNOWN (not in P2_tbls) | various  | various         | non-null (10 slots)
 49-55| 0x9c+          | UNKNOWN                  | NULL     | —               | null

Total: 40 non-null, 16 null, 40 parsed with generic header shape.

---- 3. Slot 17 detail -------------------------------------------------------

raw_pointer: 0x01aff2 (110578)
mapped file offset: 0x0545f2 (345586)
P2_tbls name: "PERF TEST SPEC" (offset 0x44 = slot 17 × 4)
Source-correlated: NAME ONLY — P2_tbls gives the name, not the field schema.

Raw 32 bytes at 0x0545f2:
  10 0e 46 b7 09 28 6c 02 00 1d 5a 1e 1e 4b 11 1a 3c 21 0a 07 00 40 00 00 00 00 00 00 00 00 f7 72

Generic header interpretation (model cu, KHONG duoc nguon dich):
  ver = 0x10 (16), header_size = 14, entry_size = 70, count = 183
  size = 14 + 70 × 183 = 12,824 bytes
  extent: 0x0545f2 .. 0x05780a
  In bounds: YES

Schema confidence for slot 17: NAME_ONLY (source-correlated name, unknown fields).
The (ver/hdr/esz/cnt) reading is the OLD generic model — reviewer correctly flags
that it "co the khong phai cau truc ver/hdr/entry/count". No source in envytools
power.c/nvbios.c defines the PERF TEST SPEC field layout. Fields are UNKNOWN.

---- 4. Three other tables with source-backed names --------------------------

Slot 0 — PERFORMANCE (P2 offset 0x00)
  raw_ptr=0x01ab55 → file 0x054155
  Generic header: ver=0x60, hdr=10, esz=5, cnt=7, size=45
  Source support: nvbios.c PM_Mode table parsing (lines 1477-1554) reads the
  perf table at bios->power.perf.offset. For this BIOS version family, header
  fields are interpreted as version/hdr_len/entry_count/entry_len — NOT as a
  uniform (ver/hdr/esz/cnt) quad. The generic reading (5×7=35+10=45) happens to
  fit but field semantics are NOT established by source.
  Confidence: NAME_ONLY (source), fields UNKNOWN.

Slot 11 — POWER BUDGET (P2 offset 0x2c)
  raw_ptr=0x01e892 → file 0x057e92
  Generic header: ver=0x30, hdr=44, esz=66, cnt=20, size=1,364
  Source support: power.c declares envy_bios_parse_power_budget() but the
  field layout is not visible in the parsed portion of power.c reviewed.
  Confidence: NAME_ONLY (source), fields UNKNOWN.

Slot 20 — THERMAL POLICY (P2 offset 0x50)
  raw_ptr=0x01f079 → file 0x058679
  Generic header: ver=0x10, hdr=10, esz=40, cnt=4, size=170
  Source support: power.c declares envy_bios_parse_power_unk50() named
  "THERMAL POLICY" in P2_tbls, but field layout not established in reviewed source.
  Confidence: NAME_ONLY (source), fields UNKNOWN.

Note: All three above have P2_tbls names (source-correlated names), but NONE
have field-level schema confirmed by the locally reviewed source. The generic
(ver/hdr/esz/cnt) header is an inferred model, not source-backed.

---- 5. Overlap analysis (14 table-table overlaps from generic extents) ------

All 14 overlaps involve slot 17 (PERF TEST SPEC, extent 0x0545f2..0x05780a,
size 12,824 B), consistent with the overlap review finding.

Classification (based on generic extents only — schema unknown, so these are
inferred, not confirmed):

  overlap type      | count | basis
  ------------------|-------|--------------------------------------------------
  alias             | 0     | no two slots map to the same file offset
  containment       | 0     | no generic extent fully contains another
  partial overlap   | 14    | slot 17 extent overlaps 14 other table extents
  generic-model-art | 14    | all 14 are artifacts of the unverified (hdr+esz*cnt) model

Because slot 17's schema is UNKNOWN, its 12,824-byte extent may be wrong:
  - If the real PERF TEST SPEC table is smaller, most/all 14 overlaps vanish.
  - If the real table is larger, overlaps could increase.
  Conclusion: the 14 overlaps are GENERIC MODEL ARTIFACTS, not confirmed real
  firmware table overlaps. Do not label as "realtableoverlap".

---- 6. Schema confidence summary -------------------------------------------

Level             | Count | Meaning
------------------|-------|-----------------------------------------------
raw               | 40    | raw pointer + raw 32 bytes at target (measured)
source-correlated | 39    | 39 slots have P2_tbls names (slots 0-38); slot 39-48 have none
name_only         | 39    | name from source, field layout unknown
inferred          | 40    | generic (ver/hdr/esz/cnt) header reading — model, not source
unknown           | 40    | field-level schema for all 40 tables (no source parser reviewed)

Slot 17 specifically: raw=measured, name=source-correlated (PERF TEST SPEC),
fields=unknown, generic extent=inferred (unverified).

---- 7. Rejected hypotheses --------------------------------------------------

H1: "All BIT token data is a pointer list." → REJECTED as blanket assumption.
  The P token data IS 56 × 4-byte pointers (verified: t_len=224=56×4), but
  other BIT tokens (e.g. 'B', 'C', 'M', 'S') may have non-pointer data.
  bit.c treats each token's t_len/t_offset individually; only 'P' is iterated
  as 4-byte pointers in print_bit_P.

H2: "Every non-null PERF slot points to a table with (ver/hdr/esz/cnt) header."
  → REJECTED. The 4-byte pattern at each target happens to parse as
  (ver,hdr,esz,cnt) but this is the old generic model. nvbios.c PM_Mode parsing
  (slot 0) uses a different field layout. No source confirms uniform headers.

H3: "The 14 overlaps are real firmware table overlaps."
  → REJECTED as unproven. They are artifacts of the unverified generic extent
  model. Slot 17's true extent is unknown until its schema is established.

H4: "Slot naming can be inferred from version patterns (e.g. ver=0x10 = thermal)."
  → REJECTED. Version byte does not determine table identity; P2_tbls offset
  determines the name. Same version (0x10) appears across THERMAL, POWER LEAKAGE,
  FAN COOLERS, THERMAL CHANNEL, etc.

---- 8. Unknowns (explicit, not inferred) ------------------------------------

- Field-level schema for PERF TEST SPEC (slot 17) and all other 39 tables.
- Whether the generic (ver/hdr/esz/cnt) header matches any real table structure.
- The true extent of slot 17's table (and thus whether the 14 overlaps are real).
- Meaning of bytes 4+ in each 32-byte header sample (e.g. 09 28 6c 02 ... at slot 17).
- Why slots 26-28 point into legacy range (0x02d3xx) while others are in 0x05xxxxx.

---- 9. Reproduction ---------------------------------------------------------

  /usr/bin/python3 perf_schema_verify.py          # generate JSON + log
  /usr/bin/python3 perf_schema_verify.py demo     # self-check (7/7 PASS)
  sha256sum CMP40HX_ORIGINAL_1MB.bin              # verify input integrity

No ROM, checkpoint, or shared artifact was modified. Output is confined to
PHASE16/VBIOS_PERF/.
