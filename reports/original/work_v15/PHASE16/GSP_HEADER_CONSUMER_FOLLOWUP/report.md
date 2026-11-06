# GSP_HEADER_CONSUMER_FOLLOWUP report — CMP40HX/TU106 (offline)

## Scope and method
- Binary: work_v15/outputs/gsp_tu10x.bin, sha256 0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b
- Rerunnable script: work_v15/PHASE16/GSP_HEADER_CONSUMER_FOLLOWUP/header_consumer_followup.py
  (/usr/bin/python3, stdlib + capstone 5.0.7, CS_ARCH_RISCV|CS_MODE_RISCV64|CS_MODE_RISCVC, offline).
- New output directory only: work_v15/PHASE16/GSP_HEADER_CONSUMER_FOLLOWUP/. Previous artifacts (PHASE16/GSP_HEADER_CONSUMER/) were NOT touched.
- No hardware, no GPU/config/model changes, no whole-GPU DONE, no other job artifacts touched.

## CFG (direct control flow only) — cap removed, fixpoint reached
- The previous run stopped at exactly 6000 instructions / 603 blocks because of a hard cap (MAX_INSNS). That cap is removed here (safety net 500000, not hit).
- A second defect in the previous run was a wrong B-type branch immediate (sign bit mishandled): e.g. `bltu s8,a3,-0x100` at 0x459c7fc correctly loops back to 0x459c6fc, the old code computed 0x459d6fc. All 340 branch/jal immediates were re-verified against capstone (0 mismatches).
- Result: direct-flow CFG walk drains the worklist -> FIXPOINT REACHED.
  - blocks: 381, decoded instructions: 3898 (all 32-bit; no 16-bit compressed instructions appear in this extent; the decoder still honors 2/4-byte RISC-V lengths)
  - span: VA 0x459c5e0 .. 0x459e94c (file 0x59c620 .. 0x59e98c)
  - edges: 1015; overlaps handled: 122 (branch targets landing mid-block, e.g. the loop back-edge 0x459c7fc -> 0x459c6fc which lies inside the setup block 0x459c6e8..0x459c714)
  - out-of-bounds targets: 0 (branch/fallthrough); 5 indirect-call targets resolved outside executable range (not walked)
  - first sequential ret (0x459cc2c) is NOT the function end; out-of-line error blocks reached by conditional branches extend beyond it.

## Indirect calls (JALR)
- 294 indirect call sites recorded as callee boundaries, NOT entered (function extent excludes callees).
  - resolved via adjacent auipc+jalr: 269 (e.g. 0x459c6b0 -> 0x5281930, 0x459c73c -> 0x55c04d8, 0x459c750 -> 0x45a5f44)
  - unresolved (jalr without resolvable auipc predecessor): 20 (e.g. jalr s2, jalr zero,t1, jalr a5)
  - resolved but outside executable range: 5
- `jal x0` (`j`) treated as a direct jump and followed; `jalr x0,0(ra)` treated as ret.

## ELF mapping (stdlib struct, parsed PT_LOAD; no section names hard-coded)
- VA = outer_file_offset + 0x03ffffc0 for data segments. Candidate VA 0x459c5e0 = file 0x59c620 (asserted).
- Magic "NVUCODES" at file 0x22370 / VA 0x4022330; fingerprint u64 0x8D1990AB6B98AE2B raw 2bae986bab90198d at file 0x22378 / VA 0x4022338 (asserted against firmware_container_source_verified.json).

## Record table at base 0x4584790 (file 0x5847d0)
- Discovered from the binary: `lui s9,0x4584 @0x459c6e8; addi s9,s9,0x790 @0x459c6f4` -> s9 = 0x4584790, read-only segment.
- Stride 24 (s10 = 0x18), index starts at 0 (s8 = 0). Loop bound = header count field = 496 (0x1f0).
- Table has 496 records, all within mapped bounds; rec0 is all zeros, recs 1..495 nonzero.

Field-access tracking (definitions/use chains + branch guards), confirmed against raw bytes:

| insn | field | offset | index | record VA | raw bytes read | guard branch |
|------|-------|--------|-------|-----------|----------------|--------------|
| 0x459c70c `lw a5,0x10(a4)` | flags | +16 | 0 (concrete) | 0x4584790 (file 0x5847d0) | 00000000 (value 0) | 0x459c714 `beqz a5` (skip if flags==0) |
| 0x459c70c `lw a5,0x10(a4)` | flags | +16 | symbolic (loop) | table + index*24 + 16 | — | 0x459c714 `beqz a5` |
| 0x459c8a8 `lw a3,0(a4)` | actualSize | +0 | 0 (concrete) | 0x4584790 (file 0x5847d0) | 00000000 (value 0) | 0x459c8ac `beq a2,a3` |
| 0x459c8e0 `ld a5,8(s4)` | pData | +8 | 0 (concrete) | 0x4584790 (file 0x5847d0) | 0000000000000000 (value 0) | 0x459c8e4 `beqz a5` |

- The loop-carried index makes `a4 = s9 + index*24` (BASE_IDX24) on each iteration, so flags+16 is also read symbolically for every index; concrete evidence is record index 0.
- actualSize+0, pData+8 reads at index 0 both return 0 because rec0 is the all-zeros sentinel.

### Fields NOT confirmed for the 0x4584790 table
- compressedSize (+4) and relOffset (+20): offset-4/offset-20 loads exist in the CFG (e.g. `lw a5,4(s2)` @0x459c7f0/0x459dcf0/0x459dd24; `lw a5,0x14(s2)` @0x459c7d0/0x459c890), but their base registers (s2/s3/a0/...) could not be resolved by the bounded symbolic dataflow to the 0x4584790 table base (they may reference the parallel s7-based table, stack, or other pointers). Per the "no table-semantics assumption" rule, they are NOT attributed to the 0x4584790 table. See table_accesses.json `xref_scan` for the complete offset-indexed cross-check (237 field-offset load/store insns enumerated with base register and tag).

## Record contents (validated against the firmware container binary, not assumed)
- rec0 = all zeros (sentinel). Nonzero records example:
  - idx1: actualSize=364 compressedSize=177 pData=0x45846d8 flags=0x9 relOffset=0
  - idx2: actualSize=364 compressedSize=177 pData=0x4584620 flags=0x9 relOffset=0
  - idx3: actualSize=302848 compressedSize=138840 pData=0x45627c8 flags=0x9 relOffset=0
  - idx494: actualSize=656 compressedSize=114 pData=0x43b7148 flags=0x9 relOffset=0
  - idx495: actualSize=192 compressedSize=192 pData=0x4070bc8 flags=0x0 relOffset=0
- pData pointers fall inside the mapped (read-only) segment for 457 nonzero records; none are executable. flags distribution: 0x9 x214, 0x8 x182, 0x0 x62, 0xc x21, 0xd x17, ... Flag bit meaning (EXTERNAL/REFERENCED) is NOT assumed — no source for it.

## Descriptor names / engine mapping
- UNKNOWN. descriptor_table.json (base 0x41a70b0, from gsp_summary.json) is a DIFFERENT table than 0x4584790 (discovered via s9), and there is no binary/source cross-reference linking its names (UTIL_DOMAIN_GROUP0, PERF_CF_CONTROLLER_*, ...) to this table. No engine mapping is derivable from the binary.

## Limits / incomplete evidence
- The symbolic dataflow pass cap (200000) was hit, so a few live-in base registers could not be resolved (this is why compressedSize+4/relOffset+20 are unconfirmed above).
- Indirect call targets are treated as callee boundaries and not entered (20 unresolved, 5 out-of-exec).
- Table semantics (EXTERNAL/REFERENCED flags, engine per slot) are not assumed beyond the binary.

## Outputs (all in PHASE16/GSP_HEADER_CONSUMER_FOLLOWUP/)
- header_consumer_followup.py — rerunnable script (self-check asserts: magic/fingerprint/mapping, immediate-vs-capstone match, RISC-V machine)
- run.log, verified.json — structured machine-checkable results
- disassembly/cfg.json — blocks, edges, calls, overlaps, fixpoint
- disassembly/extended_disasm.txt — full listing with per-instruction table-access annotations
- table_accesses.json — deduplicated BASE-table field accesses + xref_scan cross-check
- records_dump.json — all 496 records parsed from the binary
