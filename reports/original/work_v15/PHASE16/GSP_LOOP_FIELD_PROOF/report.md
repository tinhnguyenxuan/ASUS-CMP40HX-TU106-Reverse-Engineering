# GSP_LOOP_FIELD_PROOF report — loop-carried index, field offsets, table identities

Subject: GSP NVUCODES header consumer at VA 0x0459C5E0 (file 0x59c620).
Binary: work_v15/outputs/gsp_tu10x.bin, sha256 0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b, size 22901632.
Method: static, offline, saved GSP binary only. /tmp/csvenv/bin/python3 capstone 5.0.7, RISCV64|RISCVC. No hardware, no writes, no keys, no bypass. Originals under GSP_DATAFLOW_FIX* and GSP_HEADER_CONSUMER* read only.

## 1. Basic-block boundaries (split at every proven branch target)

Rebuilt the CFG with leader-based basic blocks: every proven branch/jump/resolved-call target and every fallthrough-after-terminator starts a block. This splits overlapping blocks at every proven branch target, removes duplicated decode slots, and places each instruction in exactly one block.

- Raw walked blocks: 381 (with 122 overlaps, 693 duplicated slots in the prior worker).
- After split: **516 blocks, 2205 unique decoded instructions, 0 duplicated decode slots, 0 overlapping blocks** (checked PASS).
- Coverage: 2205 disassembly lines = 2205 expected block slots, 2205 unique VAs (checked PASS).
- Span: 0x459c5e0..0x459e950. Edges 884; 294 indirect call sites (20 unresolved, 5 out of exec range); callees not entered.
- This is a **traversed CFG (bounded, terminates)**, not a function-complete CFG: indirect calls are unresolved callee boundaries, not entered.

Critical split: block `0x459c6e8..0x459c714` previously contained `0x459c6fc` (a proven branch target AND loop header) in its middle. After split:
- `0x459c6e8` = [lui s9; mv s11,zero; mv s8,zero; addi s9,s9,0x790; addi s10,zero,0x18] (ends at 0x459c6f8, fallthrough to 0x459c6fc).
- `0x459c6fc` = [slli s4,s8,0x20; srli s4,s4,0x20; mul s2,s4,s10; add a4,s9,s2; lw a5,0x10(a4); andi a5,a5,4; beqz a5,0xe4] (loop header).

## 2. Loop-carried record index (s8)

Definitions / dominance / survival:

- s8 = 0 at `0x459c6f0 mv s8, zero` (entry block 0x459c6e8).
- s8 incremented by `0x459c7f8 addiw s8, s8, 1` on every path reaching the back-edge.
- Back-edge: `0x459c7fc bltu s8, a3 -> 0x459c6fc`.
- Loop bound a3 = `0x459c6d8 lw a3, -0x84(s0)` — loaded from the **stack frame** once before the loop; frame memory, value unknown statically.

Index state: s8 is an induction variable IV(0,1) — k on iteration k, starting at 0, step +1, bounded symbolically by 0 <= k < a3. Because a3 is a frame load (unknown concretely), the index is **bounded symbolically but unbounded concretely**; a per-record proof is sound only for index 0 (where s8 is the concrete 0 from entry).

Dominance nuance (reported honestly): block `0x459c7f8` has two predecessors (`0x459c6fc` beqz-taken and `0x459c7d0` fallthrough), so `0x459c6fc` is not a strict dominator of `0x459c7f8`; the dominator-based back-edge detector therefore flags other headers but not `0x459c6fc`. The loop is identified semantically via the `bltu` back-edge `0x459c7fc -> 0x459c6fc`. s8 still increments on every path reaching the back-edge, so the induction is sound.

## 3. Table bases s9 and s10; entry-seed comparison

- s9 = 0x4584790 via `0x459c6e8 lui s9,0x4584` / `0x459c6f4 addi s9,s9,0x790`.
- s10 = 24 via `0x459c6f8 addi s10, zero, 0x18`.
- Both defined in entry block 0x459c6e8; callee-saved s-regs; not modified in the loop body; no calls between definition and use on any loop path → they survive back-edges. Stable: s9 = 0x4584790, s10 = 24 throughout the loop. Defined-before-use holds.

Entry-seed comparison (seed must not be load-bearing without a proven caller contract):
- WITH entry seed (s9=0x4584790, s10=24 at block 0x459c5e0): fixpoint, 1 base-table access.
- WITHOUT seed: fixpoint, 1 base-table access — identical.
- Result: the s9/s10 seed is NOT load-bearing here because s9/s10/s8 are defined locally in the entry block 0x459c6e8, which is on the entry path to the loop. The flags+16 fact is locally grounded, not seeded.

## 4. Join precision loss

Abstract domain: flat per-register lattice {absent ⊥, concrete u64, unknown ⊤}; join = agree-or-unknown; height 2/register → monotone termination (2478 passes without seed, fixpoint; 2555 with seed, fixpoint; no cap hit).

At loop header block `0x459c6fc`: join(s8 = 0 [entry path], s8 = k [back-edge path]) = **unknown** once k != 0 → flat join loses precision; per-index symbolic accesses (flags+16 at index > 0) are not recovered.

Affine/relational derivation (sound for the address expression, not for concrete bytes): s8 = IV(0,1); s4 = IV (slli/srli 32 zero-extend); s2 = IV*24 (mul by s10=24); a4 = 0x4584790 + IV*24 (add s9). flags+16 load base = 0x4584790 + IV*24 + 16 — symbolically a table record, but IV unbounded (a3 unknown) → raw bytes cannot be verified for any k > 0.

## 5. Field-offset accesses vs the BASE table 0x4584790 (stride 24, 496 records, rec0 = all-zeros sentinel)

No field accepted from offset alone. Per-access: VA, raw instruction, reaching base definition, guard.

| field | offset | confirmed accesses | status |
|-------|--------|-------------------|--------|
| flags | +16 | 1 | PROVEN at record index 0 (rec0 sentinel) |
| actualSize | +0 | 0 | UNKNOWN — 54 offset-matched insns, base unresolved, none reach BASE |
| compressedSize | +4 | 0 | UNKNOWN — 9 offset-matched insns, all base unresolved |
| pData | +8 | 0 | UNKNOWN — 44 offset-matched insns, base unresolved |
| relOffset | +20 | 0 | UNKNOWN — 5 offset-matched insns, all base unresolved |

Proven access (`flags +16`, index 0):
- `0x459c708 add a4, s9, s2` — record address; a4 defined here (def_base_va=0x459c708); s9=0x4584790, s2=s8*24=0 (s8=0 at entry).
- `0x459c70c lw a5, 0x10(a4)` — flags load at +0x10; EA = 0x4584790 + 0 = 0x4584790; index 0.
- raw bytes `00000000` at VA 0x45847a0, cross-verified at file offset 0x5847e0 (rec0 file 0x5847d0 + 16) → raw_verified=True.
- `0x459c710 andi a5, a5, 4` — mask &4; 0 & 4 = 0.
- `0x459c714 beqz a5, 0xe4 -> 0x459c7f8` — guard branch taken (flags==0); guard=0x459c714.
- All intra-block in 0x459c6fc → survives entry-only seeding; no unproven cross-block seed needed.

Branch conditions and load/store widths verified from raw bytes: 736 branch/jal/load/store immediates match capstone op_str, 0 mismatches (checked PASS). Width table correct (lhu=2; lb/lbu/sb=1; lh/lhu/sh=2; lw/sw=4; ld/sd=8) (checked PASS).

## 6. Table identities — never merged

- **s9-derived BASE table 0x4584790**: proven stable (above). Only flags+16 at index 0 reaches it.
- **s7-derived table**: s7 is never defined in this extent, so any s7 + index base is unresolved. Second flags load `0x459c718 add s2, s7, s2` / `0x459c71c lw a5, 0x10(s2)` → base s7 + index, unresolved. Reported separately, **never merged** with the BASE table. Verifier incomplete for this access (s7 undefined).

## 7. Unresolved indirect calls and ABI clobbers (preserved, not resolved)

- 294 indirect call sites: 269 resolved in exec range (callee boundaries only, not entered), 20 unresolved, 5 resolved out of exec range.
- Calls clobber ra + caller-saved (a0-a7, t0-t6) and result register; callee-saved s0-s11 preserved (documented assumption).
- Example preserved unresolved edge: `0x459c648 jalr s2 -> UNRESOLVED(target=null)`.
- No indirect call target is inferred; no callee is entered.

## 8. Precise missing links (why a complete proof is not possible)

1. **Loop bound a3 is unknown statically**: `a3 = lw a3, -0x84(s0)` at 0x459c6d8 loads from frame memory. Without the frame value, s8's range (0 <= k < a3) cannot be concretely bounded → no per-record proof for index > 0, and no raw-byte verification beyond index 0.
2. **s7 never defined**: the s7-derived table base and the `0x459c71c` second flags load are unresolvable within this extent.
3. **Descriptor names / engine**: UNKNOWN. `descriptor_table.json` (base 0x41a70b0, from gsp_summary.json) is a different table than 0x4584790; no binary/source cross-reference links its names to this table. No names/engine roles transferred (no xref).
4. **Strict-dominator header detection does not flag 0x459c6fc** (0x459c7f8 reachable via 0x459c7d0 without 0x459c6fc); the loop is identified semantically via the bltu back-edge. This is a CFG-traversal precision note, not a dataflow error.

## 9. Verdict

| item | verdict |
|------|---------|
| flags +16 at record index 0 via BASE 0x4584790 | PROVEN (0x459c70c, guard 0x459c714, raw 00000000, raw_verified=True) |
| flags +16 at index > 0 | UNKNOWN — index symbolic/unbounded; flat join loses precision |
| actualSize +0 | UNKNOWN — offset-matched, base unresolved, never reaches BASE |
| compressedSize +4 | UNKNOWN — 9 offset-matched, all base unresolved |
| pData +8 | UNKNOWN — offset-matched, base unresolved |
| relOffset +20 | UNKNOWN — 5 offset-matched, all base unresolved |
| s7 second flags load 0x459c71c | UNKNOWN — base s7 undefined, separate table, not merged |
| entry-seed dependence | NOT load-bearing (identical results with and without seed) |

Outputs (reproducible): `loop_field_proof.py` (rerunnable, self-checks, EXIT=0), `run.log`, `verified.json`, `table_accesses.json`, `records_dump.json`, `structured_evidence.json`, `input_hashes.json`, `disassembly/cfg.json`, `disassembly/extended_disasm.txt`. All under `work_v15/PHASE16/GSP_LOOP_FIELD_PROOF/`. Nothing under `GSP_DATAFLOW_FIX*` or `GSP_HEADER_CONSUMER*` was modified.
