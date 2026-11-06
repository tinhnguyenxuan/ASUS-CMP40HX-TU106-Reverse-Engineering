# GSP_PATH_FEASIBILITY — loop-header definition dominance audit

Subject: GSP NVUCODES header consumer at VA 0x0459c5e0 (file 0x59c620). Loop header 0x0459c6fc. Table base s9 = 0x4584790, stride s10 = 24, index s8.
Binary: /home/REDACTED_USER/codex-work/work_v15/outputs/gsp_tu10x.bin sha256 0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b. Method: offline static analysis only; saved GSP binary + disassembly/cfg.json; no hardware, firmware, MMIO, keys, bypass, brute force.
Script: gsp_path_feasibility.py (rerunnable; see run.log). Old outputs under GSP_LOOP_FIELD_PROOF are preserved (read-only).

## 1. Dominators recomputed from edges (not hardcoded)

Iterative dominator calculation over the final disassembly/cfg.json edge list (entry 0x459c5e0), 4 iterations to fixpoint:
- dom(0x459c6e8, 0x459c6fc) = **False** (matches the independent check cited in the reviews).
- header 0x459c6fc predecessors: {0x459c6e8, 0x459c7f8}.
- Block 0x459c6e8 (s9/s10/s8 definitions) has single predecessor 0x459c6d8 and single successor 0x459c6fc.
- Graph-theoretic non-domination exists because the header has a second predecessor, 0x459c7f8 (the back edge from 0x459c7fc bltu).

Graph non-domination is NOT, by itself, a feasible bypass. The interim review's avoiding path is examined next.

## 2. The interim-review avoiding path

Path (all 21 consecutive edges verified present in cfg.json — previous graph edges structurally sound on this path):
0x459c5e0 -> 0x459c64c -> 0x459c654 -> 0x459c664 -> 0x459c670 -> 0x459c680 -> 0x459c68c -> 0x459c6b4 -> 0x459c6bc -> 0x459c6d0 -> 0x459c6d8 -> 0x459c810 -> 0x459c824 -> 0x459c828 -> 0x459c844 -> 0x459c890 -> 0x459c898 -> 0x459c8a4 -> 0x459c8d8 -> 0x459c7d0 -> 0x459c7f8 -> 0x459c6fc

Trace from raw RISC-V instructions (branch immediates recomputed from raw words; capstone cross-check in prior job: 736/736 immediates match):

1. 0x459c680: `lw a1, -0x84(s0)`; 0x459c684: `addi a5, zero, 0x1f0`; 0x459c688: `bne a1, a5, +0x348 -> 0x459c9d0`. Staying on the path requires NOT taken → **C1: MEM(s0-0x84) == 496**. Reaching definition of a1: `lw a1, -0x84(s0)` @0x459c680.
2. 0x459c6b0: `auipc ra, 0xce5` / `jalr ra, ra, 0x284` → resolved PC-relative target 0x5281930 (in exec segment, callee not entered). Return value unknown.
3. 0x459c6b8: `beqz a0, +0x3b0 -> 0x459ca68`. Staying on path requires a0 != 0 (call1 return != 0).
4. 0x459c6cc: `jalr s2` — indirect call through the incoming function-pointer argument (same pointer as entry 0x459c648). Return value unknown.
5. 0x459c6d0: `sext.w s1, a0`; 0x459c6d4: `bnez s1, +0x3d4 -> 0x459caa8`. Staying on path requires call2 return == 0.
6. 0x459c6d8: `lw a3, -0x84(s0)`; 0x459c6e4: `beqz a3, +0x12c -> 0x459c810`. Taking the avoiding-path branch requires **C2: MEM(s0-0x84) == 0**. Reaching definition of a3: `lw a3, -0x84(s0)` @0x459c6d8.

Contradiction: C1 (MEM(s0-0x84) == 496) ∧ C2 (MEM(s0-0x84) == 0). Same frame slot; s0 is invariant (callee-saved, defined once at `addi s0, sp, 0x90` @0x459c600; no write to s0 on the path after the prologue). Scanning every block between the two loads (0x459c68c, 0x459c6b4, 0x459c6bc, 0x459c6d0): no visible store to -0x84(s0) — only `sd s4, -0x748(a5)` / `sd s2, -0x740(a5)` into the static 0x4397xx region. Two indirect calls intervene but no callee is entered and no side-effect summary exists; a hidden callee write MEM(s0-0x84)=0 is the only way the path could become feasible, and it is unevidenced.

**Verdict: the avoiding path is INFEASIBLE on the visible instruction stream** (explicit contradictory constraints + reaching definitions, not address comparison or intuition). Residual: unknown only under an unentered-callee frame-write assumption.

## 3. Consequence: every feasible entry->header visit passes the definition block

- Graph-reachability from entry without 0x459c6e8 reaches the header only via the infeasible route above; 0x459c7f8 is likewise reachable from entry without the header only via that same infeasible route (entry -> ... -> 0x459c6d8 -> 0x459c810 -> ... -> 0x459c7d0 -> 0x459c7f8, requiring MEM(s0-0x84) == 0 while reaching 0x459c6d8 requires == 496).
- Therefore every FEASIBLE first visit to header 0x459c6fc passes through definition block 0x459c6e8.

Definitions (actual block VAs, all inside block 0x459c6e8 — NOT entry block 0x459c5e0):
- s9 = 0x4584790: `lui s9, 0x4584` @0x459c6e8; `addi s9, s9, 0x790` @0x459c6f4.
- s10 = 24: `addi s10, zero, 0x18` @0x459c6f8.
- s8 = 0: `mv s8, zero` @0x459c6f0.

Full-CFG scan (516 blocks): **zero other writes to s9/s10/s8 anywhere in the walked extent**. s8 is incremented only by `addiw s8, s8, 1` @0x459c7f8 on the back edge.

Per-visit state:
- Visit 1 (via 0x459c6e8): s9 = 0x4584790, s10 = 24, s8 = 0 — table-base definitions hold.
- Visits k ≥ 2 via back edge 0x459c7fc -> 0x459c6fc: s9/s10 survive (callee-saved; calls clobber caller-saved only); s8 = k (IV(0,1), step +1, bound a3 = frame load unknown statically).

Conclusion: the table-base definitions (s9/s10) hold on every FEASIBLE header visit despite graph dom() = False, because the only graph route around 0x459c6e8 is infeasible and 0x459c7f8 cannot be first reached without a prior header visit. The index claim s8 == 0 holds only on visit 1; s8 == k otherwise (loop-universal s8-0 claim remains unknown/false for k > 0).

## 4. flags+16 access — path-specific, not universal

Access `0x459c70c lw a5, 0x10(a4)` (record address `0x459c708 add a4, s9, s2`), inside header block 0x459c6fc:
- On visit 0: s8 = 0 → a4 = 0x4584790 → EA = 0x4584790 + 16 → raw bytes `00000000` at VA 0x45847a0 (file 0x5847e0), verified → **PROVEN for flags+16 at record index 0** (guard `0x459c714 beqz a5` taken).
- On visit k > 0: s8 = k symbolic → EA = 0x4584790 + 24k + 16, raw bytes unverifiable → UNKNOWN.
- This is a path-specific (first-visit-path) proof through definition block 0x459c6e8, not a universal proof.

## 5. Indirect-call fallthrough soundness

Three indirect calls lie on the path:
- 0x459c648 `jalr s2` — through the incoming function-pointer argument; target unresolved; callee not entered.
- 0x459c6b0 `auipc ra, 0xce5` + `jalr ra, ra, 0x284` — PC-relative target 0x5281930 (exec-range, unentered).
- 0x459c6cc `jalr s2` — same function-pointer argument; unresolved.

All are recorded as unresolved callee + fallthrough kept (call-may-return over-approximation). No callee target is inferred; none is entered. Fallthrough edges after terminators are structurally present in cfg.json and all 21 consecutive path edges verified — the graph edges are sound; what fails is branch-predicate feasibility, not edge existence.

## 6. Corrections vs prior artifacts (documented only; old outputs preserved)

- structured_evidence.json hardcodes `s9_defined_in_entry_block = true` (and s10/s8 peers) with entry = 0x459c5e0: **false as written**. The definitions live in block 0x459c6e8, which dominates no claim by itself but lies on every feasible entry→header path; the substance (definitions reach the header on every feasible first visit) is restored by the infeasibility of the avoiding path.
- `dom(0x459c6e8, header) = False` is graph-correct; the avoiding-path evidence cited for it is infeasible, so graph non-domination does not demonstrate a feasible bypass of the definition block.

## 7. Verdict

| question | answer |
|---|---|
| dom(0x459c6e8, 0x459c6fc) from edges | False |
| interim-review avoiding path feasible? | **Infeasible** — MEM(s0-0x84) must be both 496 (0x459c688 fallthrough) and 0 (0x459c6e4 beqz-taken); same slot, s0 invariant, no visible intervening store |
| every FEASIBLE first header visit passes 0x459c6e8? | Yes |
| table-base definitions (s9/s10) hold on every feasible visit? | Yes (visit 1 via def block; later via survival) |
| s8 == 0 on every visit? | No — s8 = IV(0,1), 0 only on visit 1 |
| flags+16 at index 0? | Proven (0x459c70c, raw 00000000 verified) — path-specific |
| flags+16 at index > 0 / other fields? | Unknown |

Outputs (reproducible): gsp_path_feasibility.py, gsp_path_feasibility.json, run.log, input_hashes.json. All under PHASE16/GSP_PATH_FEASIBILITY. Nothing under GSP_LOOP_FIELD_PROOF was modified.
