# VBIOS_V60_STRUCTURE — CMP 40HX (TU106) ROM/T4/shadow, Phase 16 follow-up

Created: 2026-11-03T19:20:00.481275+00:00 UTC
Output dir: /home/REDACTED_USER/codex-work/work_v15/PHASE16/VBIOS_V60_STRUCTURE
Follows job: vbios_full_token_audit_v1 (completed)
Mode: ponytail full (stdlib only, read-only, outputs confined to this dir)

## 1. structural_facts.gaps[0] — resolved

### Root cause
The prior audit stored gaps[0] as span `[0x287bc, 0x28832)` length 118 with the note
"between BIT entries end (0x28822) and 2 target (0x28832)". The span and the note
disagree: the span starts at the BIT *header* end (0x287bc) but the note describes
the gap from the BIT *entries* end (0x28822). The stored span wrongly absorbed the
102-byte BIT entry array `[0x287bc, 0x28822)` as if it were a gap.

### Derivation from raw fields (verified against the ROM image)
- BIT signature `ff b8 42 49 54 00 00` at `0x287b0` (envytools bios.c:198).
- BIT header: `[0x287b0, 0x287bc)` = 12 bytes. Raw: `ff b8 42 49 54 00 00 01 0c 06 11 46`.
  - version u16@+6 = 0x0100, hlen u8@+8 = 12, rlen u8@+9 = 6, entriesnum u8@+10 = 17,
    checksum mod 256 = 0 (bit.c:70-92).
- BIT entries: `[0x287bc, 0x28822)` = 17 × 6 = 102 bytes (part of the BIT table, NOT a gap).
- BIT table span: `[0x287b0, 0x28822)` = 114 bytes.
- First non-null target: token `2` (idx 0), t_len=4, t_offset=0x0232 → mapped `0x28832`
  (0x28600 + t_offset). `'2'` table span `[0x28832, 0x28836)` = 4 bytes, all zero.

### Corrected gaps[0]
- Old (inconsistent): span `[0x287bc, 0x28832)`, len 118 — absorbs the entries region; REJECTED.
- Corrected: span `[0x28822, 0x28832)`, len 16 — true intervening bytes between BIT entries
  end (0x28822) and the `2` target (0x28832).

### True intervening bytes at [0x28822, 0x28832)
`00 00 5c 04 58 46 be 68 f7 72 30 e8 00 00 00 00`
Preserved raw, not interpreted (no schema).

### Context gaps (unchanged from prior audit, re-verified)
- gap[1] `[0x28836, 0x2883e)`, len 8: `00 00 00 00 00 00 00 00` (between `2` extent end and `B` start).
- trailing after last target `'i'` ends at 0x28a5c: uncharted bytes, no end claimed.

## 2. PERFORMANCE v0x60 at ROM 0x54155

### Target and pointer
- BIT P token (slot 0, power.c:82-103 P2_tbls "PERFORMANCE") directory u32 at `0x288d4` = `0x1ab55`.
- Mapped target = `0x39600 + 0x1ab55 = 0x54155`. Version byte at target = `0x60` (v60).

### Raw header (32 bytes), byte-identical across ROM/T4/shadow
`60 0a 05 07 06 0a 01 07 00 01 07 00 00 00 ff 85 02 2c 41 a1 00 58 02 1c 02 96 00 95 01 95 41 65`
- Shadow equivalent offset: `0x54155 - 0x28600 = 0x2bb55`; `shadow[0x2bb55] == rom[0x54155]`.
- T4 is the ROM prefix at this offset; no image-specific variation.

### Source consumer (independent evidence)
- `/tmp/envytools/nvbios/nvbios.c` PM_Mode perf block (lines 1477-1554) consumes
  `bios->power.perf.offset` (power.c:76).
- Dispatch key: `bios->info.version[0]` (BIOS major version), set at nvbios.c:858 from
  `data[bmp_offset + 13]` (parse_bios_version called at nvbios.c:1078). The BIOS major
  version is not established from the VBIOS artifacts in scope (nvbios_fields.json lists
  an *expected* "90." prefix — treated as expectation, not confirmed).
- Dispatch branches: BIOS major == 0x4 (nvbios.c:1491); BIOS major < 0x70 (nvbios.c:1497);
  (BIOS major & 0xf0) <= 0x80 with table-version sub-case 0x50 / default (nvbios.c:1505).
- **No branch handles table version byte 0x60** — no `case 0x60` exists. If the BIOS major
  is 0x9x, none of the three branches match ("Unknown PM major version"); only a header
  hex-dump occurs.

### Adopted extent
**None.** PERFORMANCE v60 remains OPAQUE.

### Failed hypothesis
- Generic `hlen + esz*cnt` = `0x0a + 0x05*0x07 = 45 bytes`, extent `[0x54155, 0x54182)`.
  Status: FAILED / explicitly rejected (prior audit). Not re-adopted: no v60 schema in
  envytools; raw bytes continue non-zero past 0x54182 (`0x2b` at 0x54182), so 45 bytes is
  not a real section boundary (zeros only begin around 0x541a5).

### Conditional hypotheses (documented, NOT adopted — preconditions unestablished)
| Branch (source) | Precondition | Computed extent | Status |
|---|---|---|---|
| nvbios.c:1491 (BIOS major == 0x4) | info.version[0] == 0x4 | [0x54155, 0x54182) len 45 | unadopted — precondition not established; v60 not handled |
| nvbios.c:1497 (BIOS major < 0x70) | info.version[0] < 0x70 | [0x54155, 0x541d8) len 67 | unadopted — precondition not established; generic hdr+esz*count-style model |
| nvbios.c:1505 default subentry | (info.version[0]&0xf0) <= 0x80 AND ver != 0x50 | [0x54155, 0x54184) len 47 | unadopted — precondition not established; no case 0x60 |
| nvbios.c:1512 case 0x50 | table version == 0x50 | [0x54155, 0x54196) len 65 | FAILED — table version byte is 0x60, not 0x50 |

None is adopted because `bios->info.version[0]` is unconfirmed and no branch special-cases table
version 0x60. Unknown fields are preserved; no section boundary or entry stride is established.

## 3. Additional BIT packed tokens
bit.c `bit_types[]` (lines 39-68) registers parsers only for token `P` (v1, v2) and `N` (NOP, v0).
No source parser exists for packed tokens `B,C,D,I,M,S,T,U,V,x,d,p,u,i`. No additional BIT
packed token is considered — no direct source/schema evidence available (as required).

## 4. Conclusion
- gaps[0] inconsistency resolved: corrected span `[0x28822, 0x28832)` len 16; intervening bytes
  recorded; old span `[0x287bc, 0x28832)` len 118 rejected (absorbed the entries region).
- PERFORMANCE v60 at ROM 0x54155: OPAQUE — no source-backed v60 schema; no section bounds or
  stride adopted; failed and conditional hypotheses documented; unknown fields preserved.
- No full VBIOS decoding claimed from this inventory.

## 5. Outputs (this dir)
- `vbios_v60_structure.py` — analysis script (stdlib, read-only, self-check assertions)
- `VBIOS_V60_STRUCTURE.json` — machine-readable results with raw offsets and hashes
- `run.log` — execution log
- `output_hashes.json` — output file hashes

## 6. Input and source hashes (verified against prior audit records)
Inputs:
- rom:  CMP40HX_ORIGINAL_1MB.bin  1,048,576 B  sha256=dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec  matches_prior=true
- t4:   cmp40hx_t4.bin             495,616 B   sha256=aa0ebd6d74326bb4630c473caeb6a5ae2bf55598b80a38d41a65ffee0b40cfdb  matches_prior=true
- shadow: vbios_shadow.bin        1,048,576 B  sha256=2715c0b106931b540b5ef6660201919e9297f3f5cdc61432d9a16352c55b717a  matches_prior=true

Source (envytools git f102b82381f3f11cee113d16374c87091db039d9):
- bit.c:    ad7475b67203275e1fe05ac8c910ce2ad431eacb930ca3a858e085dceb87f335
- power.c:  6f4d9d065dd37d8ea49ec3f7a7aeedd2723b13a1c223bc90e90de5be1802c8a6
- nvbios.c: 7e9f739bf8e4b45f168e90b4d6b07c0c0d039a2bdb76f753b38069714f36907f
- bios.c:   1a87fa1eab4712e120771ef9af0d5df2c81ee7a69dbf43cd38415d6bcdf09ac8

No hardware, ROM loading/flashing, keys, signatures, or tool installs. All prior artifacts preserved untouched.
