# FALCON_CFG_REBUILD — repaired Falcon payload CFG, 8 candidate slots

Slots: [20, 150, 156, 481, 484, 487, 490, 493]

## Method (read-only, offline)
- Spans re-read from outputs/ucodes_tu10x.bin at VERIFIED container offsets/lengths; sha256 re-checked.
- envydis (-m falcon) run on the FULL span per slot with EXPLICIT HEXADECIMAL -d/-l arguments
  (envydis parses both with sscanf "%x"; the prior phase passed decimal strings and corrupted skip/limit).
- Every decoded instruction raw bytes verified against the payload slice before CFG use;
  exact invalid/undecodable spans recorded.
- Falcon ISA semantics enforced: ret/exit are terminators with no fallthrough;
  bra <cond>/bra $pN imm = conditional branch (target + fallthrough);
  bra imm (no cond) = unconditional branch (target, no fallthrough);
  bra $rN = register-indirect jump (target UNKNOWN, no fallthrough);
  call imm = direct call (target + return continuation);
  call $rN = register-indirect call: call-target UNKNOWN tracked SEPARATELY from the
  ABI return-continuation edge; target never inferred from $r1.
- Basic blocks split whenever a proven direct target lands inside a decoded region.
- Reachability via finite worklist from the bounded candidate entry; every unresolved edge
  carries a reason. Linear-sweep-only regions are not reachable code.

## Entry status
- All 8 slots: entry = UNKNOWN. No incoming branch/call target or descriptor cross-reference
  was established for any candidate offset (FALCON_PAYLOAD_DEEP cross-reference analysis: all
  immediates unmatched). Candidate entries (byte-re-derived: slot 20 = 0x2A, others = 0x16)
  are bounded traversal anchors only, not proven true entries.
- Engine/role: UNKNOWN — not inferred from slot number, size, entropy, or decode density.

## Per-slot results
| slot | span_off | size | entry | valid_insns | invalid_spans | invalid_bytes | blocks | reachable_blocks | reachable_bytes | unreachable_blocks | calls | unresolved_edges |
|------|----------|------|-------|-------------|---------------|----------------|--------|------------------|-----------------|--------------------|-------|------------------|
| 20 | 0x00002F00 | 122880 | UNKNOWN | 6767 | 4519 | 103056 | 4618 | 1 | 62 | 4617 | 0 | 0 |
| 150 | 0x00161100 | 571136 | UNKNOWN | 54835 | 33233 | 411628 | 35550 | 1 | 30 | 35549 | 0 | 0 |
| 156 | 0x0041A400 | 539136 | UNKNOWN | 51469 | 30800 | 389551 | 32910 | 1 | 30 | 32909 | 0 | 0 |
| 481 | 0x007D2800 | 143360 | UNKNOWN | 7921 | 5495 | 119803 | 5790 | 1 | 33 | 5789 | 0 | 0 |
| 484 | 0x007F5800 | 157440 | UNKNOWN | 9483 | 6626 | 129192 | 6948 | 1 | 33 | 6947 | 0 | 0 |
| 487 | 0x0081BF00 | 147712 | UNKNOWN | 5745 | 3836 | 130848 | 3973 | 1 | 33 | 3972 | 0 | 0 |
| 490 | 0x00840000 | 124160 | UNKNOWN | 6218 | 4323 | 105698 | 4446 | 1 | 33 | 4445 | 0 | 0 |
| 493 | 0x0085E500 | 62720 | UNKNOWN | 2680 | 1674 | 54979 | 1770 | 1 | 33 | 1769 | 0 | 0 |

## Limits
- full-span linear decode IS established for every candidate (no decode window); CFG reachability is bounded by the (unproven) candidate entry
- indirect call/jump targets (call $rN, bra $rN) are statically UNKNOWN
- direct branch/call immediates are ambiguous absolute-vs-relative; resolved only when one interpretation lands on a valid decoded instruction start
- true entry, engine identity, and indirect targets remain UNKNOWN

## Files
- falcon_cfg_rebuild.py — this script (rerun command in header).
- machine.json — full machine-readable results (per-slot blocks, edges, reachability, invalid spans).
- FALCON_CFG_REBUILD_REPORT.md — this report.
- run.log — execution log with byte-verification and unresolved-edge lines.
- input_hashes.json — input hashes for reproduction.
- spans/cand_NNNN.bin — read-only span copies from the verified container.

## Constraints honoured
Read-only inputs only; stdlib + already-built envydis; no GPU, no hardware writes, no signature/key work, no bypass, no brute force, no exploit work. Old/live scripts under PHASE16/FW_PAYLOAD_RISCV and PHASE16/FALCON_PAYLOAD_DEEP are untouched; this directory is isolated and new.
