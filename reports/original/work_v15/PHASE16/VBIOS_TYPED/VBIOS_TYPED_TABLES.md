# VBIOS_TYPED_TABLES.md — CMP40HX/TU106 typed table verification (PHASE16/VBIOS_TYPED/)

Offline, read-only. ROM: `/tmp/CMP40HX_ORIGINAL_1MB.bin` (1,048,576 B,
sha256 `dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec`,
matches the v15 handoff). Schemas taken strictly from envytools source:
`/tmp/envytools/nvbios/power.c` (sha256 `6f4d9d06...02c8a6`),
`/tmp/envytools/nvbios/bit.c` (`ad7475b6...87f335`),
`/tmp/envytools/nvbios/nvbios.c` (`7e9f739b...14f36907f`).
No ROM writes, no tuning, no tuning-related claims.

## Files produced (PHASE16/VBIOS_TYPED/, checkpoint chung không bị sửa)
- `typed_table_verify.py` — verification tool (stdlib only; assert self-check runs on every invocation)
- `typed_tables_verified.json` — machine-readable result: raw header/entries/fields, every unknown byte with raw value, source filename/hash/function/line per table
- `run.log` — execution log (exit 0, all asserts passed)
- `VBIOS_TYPED_TABLES.md` — this report

## Decode result (version branch chosen from the actual ROM version byte)

| Slot | Table (P2_tbls name, power.c:82-103) | File offset | ROM version | Source branch | Source function (line) | Status | Typed extent |
|----:|---|---|---|---|---|---|---|
| 17 | PERF TEST SPEC (P2 off 0x44) | 0x545f2 | 0x10 | 0x10 only | envy_bios_parse_power_unk44 (power.c:1188) | decoded | 0x545f2–0x54600, len 14 |
| 5 | THERMAL DEVICES (P2 off 0x14) | 0x58723 | 0x10 | 0x10 | envy_bios_parse_power_therm_devices (power.c:239) | decoded | 0x58723–0x5875d, len 58 (hlen 4 + 18 entries × rlen 3) |
| 20 | THERMAL POLICY (P2 off 0x50) | 0x58679 | 0x10 | 0x10 | envy_bios_parse_power_unk50 (power.c:1334) | decoded | 0x58679–0x58723, len 170 (hlen 10 + 4 entries × rlen 40) |
| 11 | POWER BUDGET (P2 off 0x2c) | 0x57e92 | 0x30 | 0x10/0x20/0x30 | envy_bios_parse_power_budget (power.c:644) | decoded | 0x57e92–0x583e6, len 1364 (hlen 44 + 20 entries × rlen 66; cap_entry at +0x0a per 0x30 branch) |
| 0 | PERFORMANCE (P2 off 0x00) | 0x054155 | 0x60 | — | none (offset only: nvbios.c:1095 le16 BMP+148; hex dump nvbios.c:1477) | UNSUPPORTED | not derivable — no source field schema |

4/5 tables decoded with real source schema (≥3 required: slots 17, 5, 20, 11). PERF slot 0 = UNSUPPORTED: envytools source has no PERF table field parser, only the offset capture and a print-time hex dump, so no field semantics are claimed and no generic header is substituted to satisfy a table count.

## What was actually decoded (source-real fields only)

- **Slot 17 (len 14):** version@+0 = 0x10, hlen@+1 = 14. Source (power.c:1200): "it doesn't appear as if this table has entries at all" → 0 entries. Bytes offset+2..+13 (12 bytes: `46 b7 09 28 6c 02 00 1d 5a 1e 1e 4b`) kept unknown, raw preserved, not interpreted. Critically: offset+2 = 0x46 (70) and offset+3 = 0xb7 (183) are **not** entry_size/count for this parser — the source reads only version@+0 and hlen@+1 and never reads offset+2/+3.
- **Slot 5 (len 58):** header version/hlen/rlen/entriesnum = 0x10/4/3/18; 18 entries × (class_id, i2c_device, flags), entry offset = table+hlen+i×rlen (power.c:262), i in [0,18). entry 0: class_id 0x01 (GPU per therm_class_types, power.c:234-237), i2c 0, flags 0.
- **Slot 20 (len 170):** header 0x10/10/40/4; 4 entries × (mode, t0, t1, t2, interval_us, down_off, up_off); entry 0: mode 1, t0/t1/t2 2848 (/32 = 89 °C), interval 200 µs, down_off 0, up_off -32 (/32 = -1 °C). Print path only handles mode==1 (power.c:1392).
- **Slot 11 (len 1364):** header 0x30/44/66/20, cap_entry@+0x0a = 2 (0x30 branch, power.c:673); 20 entries × (min, avg, peak, unkn12), rlen≠6 path (power.c:688-691); entry 0: min 20000 mW, avg 5001000, peak 5001000, unkn12 1.

All unknown bytes inside each typed extent are listed in `typed_tables_verified.json` with raw hex (e.g. slot 17: 12 unknown bytes at 0x545f4; slot 20 has per-entry undecoded gaps inside the 40-byte records; slot 11 header bytes +4..+9 and +0x0b..+0x2b undecoded).

## Overlap reassessment — the 14-overlap premise is corrected

The prior generic model computed slot 17 extent as esz=70 × cnt=183 = 12824 bytes (0x545f2–0x05780a), reading raw byte offset+2 (70) and offset+3 (183) as entry_size/count. That model is **not** the source parser: `envy_bios_parse_power_unk44` (power.c:1188, case 0x10) reads version@+0 and hlen@+1 only, hlen=14, so the source-typed extent is **0x545f2–0x54600 (len 14)**, which ends exactly where the next slot (slot 1) table region starts (0x054600 per the prior pointer mapping; slot 20's extent likewise ends at 0x58723 = slot 5's start).

Conclusion: the 14 generic-model overlaps involving slot 17 are artifacts of the unverified generic `hdr + esz*cnt` size, not real table overlaps. Slot 17's extent is adjacent to slot 1, not overlapping it. No real overlap is proven for any of these tables.

**Explicit scope statement (per instructions): only 4 tables have real source-schema decode here (slots 17, 5, 20, 11); PERF is UNSUPPORTED. This is not a decode of 40 tables — most BIT P slots remain name_only/unknown, and no generic header is used to inflate coverage.**

## Validation performed (before decode, per requirement)
- ROM sha256 verified against expected value (assert, would fail otherwise).
- Every read bounds-checked against file size; version byte read first, then the matching source branch selected; unsupported version → UNSUPPORTED, no decode.
- Entry index bounds: entries iterate `i in [0, entriesnum)`; each entry field read bounds-checked; out-of-range reads surface as unknown rather than fabricating values.
- No `assert 7/7 then PASS` semantics: every field value comes from actual ROM bytes at the source-specified offsets.

Run evidence: `run.log` (exit 0, self-check asserts all passed). JSON: `typed_tables_verified.json`. Tool: `typed_table_verify.py`.
