# FALCON_DECODE_GAP — first undecodable span after the bootstrap prefix, 8 Falcon payload candidates

Slots: [20, 150, 156, 481, 484, 487, 490, 493]

Method: read-only inputs only. Verified each span against the NVUCODES container inventory
(sha256, offset, length), re-read gap bytes from the ORIGINAL container at absolute offset,
disassembled full span with envydis -m falcon (default variant), then re-disassembled the gap
window under every Falcon variant/mode the built envydis supports (default, fuc0, fuc3, fuc4, fuc5, fuc6).
No GPU/MMIO/flashing/keys/signatures/brute force. No source mutation. Original outputs preserved.

## Independently verified task facts
| slot | container_off | span_off | entry | prefix_end | gap_start | gap_bytes | gap_abs_off | abs_verified |
|------|---------------|----------|-------|------------|-----------|-----------|-------------|--------------|
| 20 | 0x002F00 | 0x000068 | 0x00002A | 0x000068 | 0x000068 | 3e74fe00 | 0x00002F68 | True |
| 150 | 0x161100 | 0x000034 | 0x000016 | 0x000034 | 0x000034 | 89000000 | 0x00161134 | True |
| 156 | 0x41A400 | 0x000034 | 0x000016 | 0x000034 | 0x000034 | 89000000 | 0x0041A434 | True |
| 481 | 0x7D2800 | 0x000037 | 0x000016 | 0x000037 | 0x000037 | 89000000 | 0x007D2837 | True |
| 484 | 0x7F5800 | 0x000037 | 0x000016 | 0x000037 | 0x000037 | 89000000 | 0x007F5837 | True |
| 487 | 0x81BF00 | 0x000037 | 0x000016 | 0x000037 | 0x000037 | 89000000 | 0x0081BF37 | True |
| 490 | 0x840000 | 0x000037 | 0x000016 | 0x000037 | 0x000037 | 89000000 | 0x00840037 | True |
| 493 | 0x85E500 | 0x000037 | 0x000016 | 0x000037 | 0x000037 | 89000000 | 0x0085E537 | True |

## Per-variant decode of the gap (first instruction at gap start)
`???`/unknown = not a valid Falcon instruction under that variant; a real mnemonic = valid syntax under that variant.
| slot | gap bytes | default | fuc0 | fuc3 | fuc4 | fuc5 | fuc6 |
|------|-----------|---------|------|------|------|------|------|
| 20 | 3e74fe00 | ??? | ??? | ??? | lbra | lbra | lbra |
| 150 | 89000000 | ??? | ??? | ??? | ??? | mov | mov |
| 156 | 89000000 | ??? | ??? | ??? | ??? | mov | mov |
| 481 | 89000000 | ??? | ??? | ??? | ??? | mov | mov |
| 484 | 89000000 | ??? | ??? | ??? | ??? | mov | mov |
| 487 | 89000000 | ??? | ??? | ??? | ??? | mov | mov |
| 490 | 89000000 | ??? | ??? | ??? | ??? | mov | mov |
| 493 | 89000000 | ??? | ??? | ??? | ??? | mov | mov |

## What the gap is, per variant
* slot 20 (gap @0x000068, bytes 3e74fe00):
  - -V default: UNKNOWN (undecodable opcode) @0 raw=3e text="??? b8 [unknown op length] [unknown instruction]"
  - -V fuc0: UNKNOWN (undecodable opcode) @0 raw=3e text="??? b8 [unknown op length] [unknown instruction]"
  - -V fuc3: UNKNOWN (undecodable opcode) @0 raw=3e text="??? b8 [unknown op length] [unknown instruction]"
  - -V fuc4: VALID lbra @0 raw=3e74fe00 text="lbra 0xfe74"
  - -V fuc5: VALID lbra @0 raw=3e74fe00 text="lbra 0xfe74"
  - -V fuc6: VALID lbra @0 raw=3e74fe00 text="lbra 0xfe74"
  - gap_abs_container_off=0x00002F68 re-read from container=3e74fe00 verified=True
* slot 150 (gap @0x000034, bytes 89000000):
  - -V default: UNKNOWN (undecodable opcode) @0 raw=89 text="??? b32 [unknown op length] [unknown instruction]"
  - -V fuc0: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc3: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc4: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc5: VALID mov @0 raw=89000000 text="mov $r9 0x0"
  - -V fuc6: VALID mov @0 raw=89000000 text="mov $r9 0x0"
  - gap_abs_container_off=0x00161134 re-read from container=89000000 verified=True
* slot 156 (gap @0x000034, bytes 89000000):
  - -V default: UNKNOWN (undecodable opcode) @0 raw=89 text="??? b32 [unknown op length] [unknown instruction]"
  - -V fuc0: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc3: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc4: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc5: VALID mov @0 raw=89000000 text="mov $r9 0x0"
  - -V fuc6: VALID mov @0 raw=89000000 text="mov $r9 0x0"
  - gap_abs_container_off=0x0041A434 re-read from container=89000000 verified=True
* slot 481 (gap @0x000037, bytes 89000000):
  - -V default: UNKNOWN (undecodable opcode) @0 raw=89 text="??? b32 [unknown op length] [unknown instruction]"
  - -V fuc0: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc3: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc4: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc5: VALID mov @0 raw=89000000 text="mov $r9 0x0"
  - -V fuc6: VALID mov @0 raw=89000000 text="mov $r9 0x0"
  - gap_abs_container_off=0x007D2837 re-read from container=89000000 verified=True
* slot 484 (gap @0x000037, bytes 89000000):
  - -V default: UNKNOWN (undecodable opcode) @0 raw=89 text="??? b32 [unknown op length] [unknown instruction]"
  - -V fuc0: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc3: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc4: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc5: VALID mov @0 raw=89000000 text="mov $r9 0x0"
  - -V fuc6: VALID mov @0 raw=89000000 text="mov $r9 0x0"
  - gap_abs_container_off=0x007F5837 re-read from container=89000000 verified=True
* slot 487 (gap @0x000037, bytes 89000000):
  - -V default: UNKNOWN (undecodable opcode) @0 raw=89 text="??? b32 [unknown op length] [unknown instruction]"
  - -V fuc0: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc3: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc4: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc5: VALID mov @0 raw=89000000 text="mov $r9 0x0"
  - -V fuc6: VALID mov @0 raw=89000000 text="mov $r9 0x0"
  - gap_abs_container_off=0x0081BF37 re-read from container=89000000 verified=True
* slot 490 (gap @0x000037, bytes 89000000):
  - -V default: UNKNOWN (undecodable opcode) @0 raw=89 text="??? b32 [unknown op length] [unknown instruction]"
  - -V fuc0: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc3: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc4: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc5: VALID mov @0 raw=89000000 text="mov $r9 0x0"
  - -V fuc6: VALID mov @0 raw=89000000 text="mov $r9 0x0"
  - gap_abs_container_off=0x00840037 re-read from container=89000000 verified=True
* slot 493 (gap @0x000037, bytes 89000000):
  - -V default: UNKNOWN (undecodable opcode) @0 raw=89 text="??? b32 [unknown op length] [unknown instruction]"
  - -V fuc0: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc3: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc4: UNKNOWN (undecodable opcode) @0 raw=890000 text="??? b32 $r0 $r0 0x0 [unknown: 09 00 00] [unknown instruction]"
  - -V fuc5: VALID mov @0 raw=89000000 text="mov $r9 0x0"
  - -V fuc6: VALID mov @0 raw=89000000 text="mov $r9 0x0"
  - gap_abs_container_off=0x0085E537 re-read from container=89000000 verified=True

## Entry / mode identification (saved payload / manifest / header fields)
* head16 (first 16 bytes of each span) is a fixed template across the 8 payloads:
  - slot 20: d0c0ff0000fe0400bda47e10fe00f802  (u32 LE 00FFC0D0 0004FE00 107EA4BD 02F800FE)
  - slot 150: d0005e0000fe0400bda47e105e00f802  (u32 LE 005E00D0 0004FE00 107EA4BD 02F8005E)
  - slot 156: d0005e0000fe0400bda47e105e00f802  (u32 LE 005E00D0 0004FE00 107EA4BD 02F8005E)
  - slot 481: d000f00000fe0400bda47e10fb00f802  (u32 LE 00F000D0 0004FE00 107EA4BD 02F800FB)
  - slot 484: d000f00000fe0400bda47e10fb00f802  (u32 LE 00F000D0 0004FE00 107EA4BD 02F800FB)
  - slot 487: d000f00000fe0400bda47e10fb00f802  (u32 LE 00F000D0 0004FE00 107EA4BD 02F800FB)
  - slot 490: d000f00000fe0400bda47e10fd00f802  (u32 LE 00F000D0 0004FE00 107EA4BD 02F800FD)
  - slot 493: d000790000fe0400bda47e10fd00f802  (u32 LE 007900D0 0004FE00 107EA4BD 02F800FD)
* No head16 word is a Falcon version/mode field; no version or mode string found in the first 64 bytes.
* No manifest file was located/consulted that identifies true entry or Falcon mode. container header (NVUCODES, ver=1, count=496) gives no per-payload mode.
* Therefore the true Falcon ISA version/mode for these payloads is NOT established by any available field.

## Conclusion (bounded negative result)
* gap_is_variant_dependent: True
* default_fuc0_fuc3: gap bytes are UNKNOWN opcodes under default (no -V; behaves as fuc0/fuc3 for 0x3e/0x89 lead bytes)
* fuc4_plus_slot20: slot 20 gap 3e74fe00 decodes as lbra 0xfe74 (valid long branch; control-flow / format boundary) under fuc4, fuc5, fuc6
* fuc5_plus_others: slots 150/156/481/484/487/490/493 gap 89000000 decodes as mov $r9, 0x0 (valid register init) under fuc5, fuc6; followed by valid ld in same variant
* bytes_after_gap: following bytes decode as valid insns (xcld for slot 20; ld for others) under the same newer variants, consistent with code continuation rather than random padding
* no_mode_field: no payload head16/manifest/header field identifies the true Falcon entry version/mode; head16 is a fixed template; no manifest consulted/found
* verdict: BOUNDED NEGATIVE: the gap cannot be definitively classified as unsupported-opcode/data/padding/branch-boundary without the true Falcon ISA version. It is UNKNOWN under fuc0/fuc3/default, a valid branch under fuc4+, and a valid code continuation under fuc5+. Missing evidence: the Falcon version/mode for these payloads.

## What is NOT claimed
* The decoded bootstrap prefix is NOT claimed to be all executable code.
* Other regions are NOT claimed to be data.
* Valid syntax under fuc4+/fuc5+ is NOT treated as proof of code; it is syntax-valid under those variants only, and the true variant is unknown.
* No engine/GSP-vs-SEC2 role is inferred from slot number or entropy.
