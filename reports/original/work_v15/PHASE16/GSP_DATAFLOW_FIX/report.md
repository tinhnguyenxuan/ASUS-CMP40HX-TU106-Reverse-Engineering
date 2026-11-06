# GSP_DATAFLOW_FIX report — symbolic dataflow repair (offline, static)

## Precondition
`GSP_HEADER_CONSUMER_FOLLOWUP` is terminal: its `run.log` ends with `[done] fixpoint=True hit_cap=False`. That directory was only read, never written.

## Inputs and method
- Binary: `work_v15/outputs/gsp_tu10x.bin`, sha256 `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`, size 22901632.
- Interpreter: `/tmp/csvenv/bin/python3` (capstone 5.0.7; `/usr/bin/python3` on this host lacks capstone). Mode `RISCV64|RISCVC`. Offline.
- Script (new copy only): `work_v15/PHASE16/GSP_DATAFLOW_FIX/header_consumer_dataflow_fix.py`.
- Output dir (new only): `work_v15/PHASE16/GSP_DATAFLOW_FIX/`. Nothing under `GSP_HEADER_CONSUMER*` or `GSP_HEADER_CONSUMER_FOLLOWUP/` was modified. No hardware access, no device writes, no keys, no bypass.

## Repairs (root cause, in the shared functions)
1. **mem_size width**: `lhu` mapped to 1 byte → now 2 bytes (unsigned halfword load). `lb`/`lbu`/`sb` = 1, `lh`/`lhu`/`sh` = 2, `lw`/`sw` = 4, `ld`/`sd` = 8.
2. **Stores have no destination register**: `step_sym` no longer writes `sym[rd]` for stores (bits 11:7 are S-immediate bits, which could clobber an unrelated symbolic register). Store address uses the **S immediate**, not the load's I immediate.
3. **Memory effective address from pre-instruction state**: operands (`rs1` base, offset) are captured from `sym` **before** `step_sym` applies the transfer, so a load whose `rd` equals its base register no longer loses its EA, and stores never clobber.
4. **Symbolic seeds removed from global scope**: `s9 = TABLE_BASE_VA` and `s10 = TABLE_STRIDE` are seeded **only at the entry block** `0x459c5e0`. The old per-block global seed (every block starts with known s9/s10) and any unproven s7/s8 assumption seeds are gone — they were unsound (no dominance/call-preservation demonstration). Every table fact now comes from local definitions or the entry seed; the rest is reported unresolved.
5. **Call ABI clobbers**: calls clobber `ra` + caller-saved (`a0-a7`, `t0-t6`) and the result register; callee-saved `s0-s11` preserved (documented assumption).
6. **Abstract domain and termination**: flat per-register lattice `{absent ⊥, concrete u64, unknown ⊤}`, join = agree-or-⊤. Height 2 per register → monotone, finite, guaranteed termination; constants never grow (join of two distinct constants yields ⊤ immediately), so no widening is needed and nothing can cycle forever. Pass cap 200000 is a circuit breaker with an explicit termination diagnostic (`status=fixpoint`, `hit_cap=False`).
7. **Serializer null guard**: `va_to_file(tgt)` is never called with `tgt=None` (that made `seg_for` compare `int <= None` → TypeError and truncated `extended_disasm.txt` at `0x459c644`). Unresolved targets serialize as explicit null plus the `UNRESOLVED(target=null)` label; output coverage is validated against the CFG instruction count (see §7).
8. **Compressed instructions**: 16-bit transfers (`c.jal`/`c.j`/`c.jalr`/`c.jr`/`c.beqz`/`c.bnez`) are emitted as unresolved edges with `target=null`; compressed data ops are not precisely decoded. **None occur in this extent** (check PASS), so this is structural only.

## Termination
- passes 1612, cap 200000, `hit_cap=False`, `status=fixpoint`. CFG fixpoint was already reached (`fixpoint=True`); the symbolic dataflow fixpoint is now independently bounded and diagnosed.

## Corrected evidence

CFG: 381 blocks, 2205 unique decoded instructions (3898 block-instruction slots; the 693 extra slots are the 122 overlap duplicates — branch targets landing mid-block), 1015 edges, 294 indirect call sites (269 resolved in exec range, entered as callee boundaries only; 20 unresolved; 5 resolved out of exec range), span `0x459c5e0..0x459e94c`.

Table at `0x4584790` (stride 24, 496 records from header count `0x1f0`):

| field | offset | confirmed accesses | status |
|---|---|---|---|
| flags | +16 | 1 | proven at record index 0 (rec0 sentinel) |
| actualSize | +0 | 0 | offset-matched insns exist, base unresolved |
| compressedSize | +4 | 0 | 9 offset-matched insns, all base unresolved |
| pData | +8 | 0 | offset-matched insns exist, base unresolved |
| relOffset | +20 | 0 | 5 offset-matched insns, all base unresolved |

Note: the older worker attributed `actualSize+0` and `pData+8` at index 0, but only via the now-removed unproven global `s9`/`s10` seeds. Those attributions are dropped; the insns remain enumerated in `table_accesses.json` `xref_scan` with unresolved bases. **Fewer confirmed accesses is not evidence that fields are unused.**

### Mandatory known-positive recovery: `0x459c708` → `0x459c70c` → `0x459c710` → `0x459c714`
Recovered with raw bytes and reaching definitions:

| item | evidence |
|---|---|
| `0x459c708 add a4, s9, s2` | record address computed; `a4` defined here (`def_base_va=0x459c708`) |
| `s9` definition | `0x459c6e8 lui s9,0x4584`; `0x459c6f4 addi s9,s9,0x790` → `0x4584790` |
| `s2` definition | `0x459c704 mul s2, s4, s10`; `s4 = 0` (zero-extend of `s8` via `slli`/`srli 32` at `0x459c6fc`/`0x459c700`); `s8 = 0` (`0x459c6f0 mv s8, zero`); `s10 = 24` (`0x459c6f8 addi s10, zero, 0x18`) |
| `0x459c70c lw a5, 0x10(a4)` | flags load at `+0x10`; EA `0x4584790 + 0 = 0x4584790`, index 0; raw bytes `00000000` (value 0) read at VA `0x45847a0` |
| raw bytes cross-check | identical bytes read at file offset `0x5847e0` (rec0 file `0x5847d0` + 16): `00000000` → `raw_verified=True` |
| `0x459c710 andi a5, a5, 4` | mask `& 4` on the loaded flags; `0 & 4 = 0` |
| `0x459c714 beqz a5, 0xe4` | guard branch taken (flags==0) → `0x459c7f8`; recorded as `guard=0x459c714` |

All of the above is intra-block in `0x459c6e8`, so it survives entry-only seeding (no unproven cross-block seed needed).

### Second flags load: `0x459c71c lw a5, 0x10(s2)` — table bases NOT merged
`0x459c718 add s2, s7, s2` makes `s2` depend on `s7`, which is never defined in this extent (no `s7` seed — deliberately unproven). The base is therefore **unresolved**: the insn appears in `xref_scan` (`tag=unresolved`, `base_reg=s2`, `offset=16`, `field=flags`) and is **absent** from the BASE-table `table_accesses`. It is reported separately from the `0x4584790` table and **not merged**. Verifier incomplete for this access: `s7` is not defined here, so neither its bytes nor any field semantics can be attributed.

## Serialization defect (fixed)
`extended_disasm.txt` previously ended at `0x459c644`, just before the unresolved `jalr` at `0x459c648`: the serializer called `va_to_file(tgt)` unguarded for `call_indirect` (`tgt=None`), and `seg_for` compared `int <= None` → TypeError. Fixed: targets are guarded before mapping/formatting, and `0x459c648` now serializes as:

```
0x0459c648 file=0x59c688 000900e7 size=4 jalr       s2 -> UNRESOLVED(target=null)
```

Coverage validation: disasm instruction lines = 3898 = expected block slots; unique VAs = 2205 = decoded instruction count → `coverage_ok=True`.

## Records (read from the binary, not assumed)
496 records at `0x4584790` (stride 24), all in bounds: 495 nonzero, 1 zero (`rec0` = all-zeros sentinel). `rec0.flags = 0`, matching the proven flags-load value above (cross-check PASS).

**Internal vs external**: these 495 nonzero records belong to the **internal** table at `0x4584790`. They are distinct from the external NVUCODES archive (496 slots / 38 external payloads); equal record stride alone does not establish identical contents or storage occupancy. No conflation is made.

## Uncertainty and unresolved edges (honest, not silence)
- 20 indirect call targets unresolved (e.g. `jalr s2` at `0x459c648`, `jalr ra,ra,0x284` at `0x459c6b0`); 5 resolved targets out of exec range; callees are callee boundaries, not entered (scope: direct-flow CFG only).
- The `s7`-based second flags load at `0x459c71c`: base `s7` undefined → unresolved, verifier incomplete.
- Loop-carried index is **not summarized**: at back-edge targets, join collapses differing concrete indices to `unknown`; per-index symbolic accesses (e.g. `flags+16` at index > 0) are not recovered and are not claimed.
- `compressedSize +4` and `relOffset +20`: offset-matching loads/stores exist but no base resolves to `0x4584790` → **not confirmed**. 0 confirmed accesses is not negative evidence.
- Descriptor names / engine mapping: UNKNOWN. `descriptor_table.json` (base `0x41a70b0`, from `gsp_summary.json`) is a different table than `0x4584790`; no binary/source cross-reference links its names to this table.

## Review observations addressed
| GSP_FOLLOWUP_DATAFLOW_REVIEW.md observation | handling |
|---|---|
| `lhu` mapped to 1 byte | fixed: `lhu` = 2 (check PASS) |
| Store writes `f[rd]` (no rd; S immediate) | fixed: stores write no register; S immediate for address (check PASS) |
| Load EA lost when `rd == base` | fixed: pre-state capture (check PASS with synthetic `lw a0,0(a0)`) |
| Non-convergence / empty rescheduling | monotone agree-or-⊤ join, flat lattice, explicit pass-cap diagnostic; `status=fixpoint`, `hit_cap=False` |
| Unproven global `s9`/`s10` seeds | removed; entry-only seeding; assumption list empty |
| `table accesses 0` ≠ negative evidence | `xref_scan` enumerates all 237 field-offset load/store insns with bases; unresolved ones listed, not attributed |
| Internal 495 nonzero vs external 38 payload occupancy | kept distinct (records section above) |
| Serialization TypeError at `0x459c644`/`0x459c648` | null guard + `UNRESOLVED(target=null)`; coverage validated against CFG insn count |
| `0x459c70c` vs `0x459c71c` table bases not merged | recovered separately; `0x459c71c` unresolved, not in BASE accesses |

## Focused semantic checks (all PASS)
immediates-vs-capstone (1275 branch/jal/load/store insns, 0 mismatches), no-compressed-in-extent, `mem_size` width table (`lhu=2`), store writes no rd, load EA from pre-state when `rd` overwrites base, known-positive chain `0x459c708`→`0x459c714`, second flags load separate/unresolved/not merged, `compressedSize`+`relOffset` present-but-unresolved, dataflow termination, `rec0.flags == access value`, disasm coverage vs CFG insn count.

## Outputs (all under `work_v15/PHASE16/GSP_DATAFLOW_FIX/`)
- `header_consumer_dataflow_fix.py` — rerunnable repaired script (self-checks run on every invocation; EXIT=0)
- `run.log` — full execution trace including checks
- `verified.json` — machine-checkable results (inputs, ELF, CFG, dataflow/termination, table field status, serialization coverage, checks, limits, verdict)
- `disassembly/cfg.json` — blocks, edges, calls, overlaps, fixpoint
- `disassembly/extended_disasm.txt` — full listing with TABLE_ACCESS annotations and `UNRESOLVED(target=null)` indirect edges
- `table_accesses.json` — proven BASE-table accesses + `xref_scan` (all field-offset insns, resolved or unresolved)
- `records_dump.json` — all 496 records parsed from raw bytes

Verdict: CFG complete and terminated; dataflow terminated within the pass cap with an explicit diagnostic; only `flags +16` at record index 0 is proven for the `0x4584790` table; `compressedSize`, `relOffset`, `actualSize`, `pData` are offset-present but base-unresolved (not attributed); the `s7`-based flags load at `0x459c71c` is explicitly incomplete. Nothing is fabricated: every access above names its VA, file offset, raw bytes, reaching definition, and guard branch, or is labeled unresolved/incomplete.
