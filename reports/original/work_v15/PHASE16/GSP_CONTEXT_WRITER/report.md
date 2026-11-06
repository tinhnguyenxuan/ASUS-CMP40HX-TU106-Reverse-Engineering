# GSP_CONTEXT_WRITER — PHASE16 context+0x30 writer investigation

Question: value at *(s3 + 0x30) for the callback `jalr a5` @ VA 0x04F575E0,
and which code writes context+0x30. Read-only, offline, /usr/bin/python3 + capstone.

## Verdict
context+0x30 value at the callback jalr: **UNKNOWN** — not provable from saved bytes.
Exact failed link: no store to *(s3 + 0x30) exists in-window, directly or via any
provable s3 alias; s3 is the return of the external callee at 0x05281930, whose
+0x30 store (if any) is outside this function window and is not resolved statically.

## Inputs
- binary: /home/REDACTED_USER/codex-work/work_v15/outputs/gsp_tu10x.bin (22901632 bytes, sha256 0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b)
- prior report GSP_CALLBACK_TARGET read for context only; not modified.

## Mapping validation (self-verified from raw bytes)
- Inner ELF64-LE header at file offset 0x40; e_machine = RISC-V (243).
- Operative VA->file offset: file_off = VA - 0x3ffffc0 (operative va-0x3ffffc0), verified against 12 raw-byte triples (all match).
- Function window 0x4f5733c..0x4f57a00 (433 insns): backing section 28 (exec=1);
  section name could not be resolved reliably from the synthetic shstrtab parse, so no name is asserted; va/offset/size/flags are validated by the 12 raw-byte triples above.
- Prior report said section[28]; this parse confirms section index 28 (exec=1) as the window backing. Earlier elf_map.json disagreeing entries come from a different, un-verified parse and were not used.

## Call-target verification (raw bytes)
- caller auipc ra,imm=80 @0x04F06C18 + jalr ra,ra,0x724 @0x04F06C1C -> 0x4f5733c: VERIFIED (window entry)
- internal call auipc ra,imm=810(0x32a) @0x04F5739C + jalr ra,ra,0x594 @0x04F573A0 -> 0x5281930 (claimed 0x5281930): VERIFIED
- internal call target 0x5281930 is in executable section: True (backing sec28 sec28)
- helper auipc ra,imm=-80 @0x04F57644 + jalr ra,ra,-0x58 @0x04F57648 -> 0x4f075ec: VERIFIED

## Callee trace @ 0x05281930
- target backing: sec28 (exec=True) — callee bytes ARE present in the saved binary
- callee insns disassembled: 4096 (linear, bounded); first ret at 0x5281c48; rets found: 20 (capped=True)
  (linear scan crosses into subsequent functions after the first rets; rets after the first belong to following code, not this callee.)
- callee stores total: 173; stores whose immediate is exactly +0x30: 9 (all within the bounded linear scan; base registers are sp/a5/s1 — none provably the returned context pointer, so none is a provable *(context+0x30) write)
- a0 (return register) last definition before first ret: 0x5281bfc mv a0, zero — i.e. the linearly-first return path returns 0 (failure path); other return paths exist but are not provably the context-return path from a bounded linear scan.
- callee external (auipc+jalr) calls: 87 (targets listed in machine JSON)

## Forward slice of s3 (context base) across 0x04F5733C..0x04F57A00
- s3 established as context base: mv s3, a0 @0x04F573AC (return of internal call).
- s3 is written once before the callback region (mv s3, a0 @0x04F573AC); later writes to
  s3 (@0x04F57768/0x04F579ac) lie after the callback; x19 is callee-saved, preserved across calls.
- s3 expression at ld a5, 0x30(s3) @0x04F575D4: unknown (conservative CFG join).
  s3 is established as context base at mv s3, a0 @0x04F573AC (call1 return) and is
  never redefined before the callback region; every intra-window branch/jump target is
  post-anchor, and the null-return path (beqz a0 @0x04F573A8) exits to 0x04F57938, past
  the callback — so on every feasible reaching path s3 = call1 return. The conservative
  join reports unknown only because loop-head meets (e.g. bnez s2,-8 @0x04F57514) absorb
  an uninitialized seed; no feasible path carries a non-context s3 to the callback.
- stores enumerated: 90 (loads 42); ctx-based: 17; absolute-address: 0; unknown base: 31
- direct stores *(s3 + 0x30): 0; aliased stores *(s3_alias + off == 0x30): 0.
  Direct-store counting alone is insufficient when aliases exist; the slice above
  classifies every store by its address expression instead of merely counting.
- Context field / pointer-constant initialization (stores at s3+0x470..0x4d8 etc.)
  IS performed by this function — initialization, not allocation. Allocation is the
  callee return (outside this window). context+0x30 itself is NOT initialized here.

## Callback block (0x04F575D4 .. 0x04F575E0)
- ld a5, 0x30(s3) @0x04F575D4 (raw 83b70903); lhu a2, -0x88(s0) @0x04F575D8 (raw 035684f7);
- mv a0, s3 @0x04F575DC (raw 13850900); jalr a5 @0x04F575E0 (raw e7800700).
- a0 = s3 PROVEN on all paths (mv a0, s3; no write between def and call).
- a1 PATH-SENSITIVE: first entry — mv a1, s4 @0x04F575A4 is killed by the external
  wrapper call @0x04F575AC/0x04F575B0; no a1 rewrite before the jalr -> a1 UNKNOWN at call.
  a1 == s4 is FALSE; do not revive it.
- Back-edge — helper @0x04F57644/0x04F57648 -> 0x04F075EC, mv a1, a0 @0x04F5764C,
  bnez a0 -> callback block: a1 = helper return, PROVEN on that path, no intervening call.
- a2 = lhu a2, -0x88(s0) @0x04F575D8 straight-line; slot s0 - 0x88 written by
  sh a7, -0x88(s0) @0x04F57630 on the prior iteration; helper @0x04F075EC is called with
  a2 = s0 - 0xe0 and its inner pass uses (sp, 0x150), which covers s0 - 0x88 — helper
  mutation of the a2 source slot is not excluded statically (caveat retained).

## Indirect calls (byte-grounded; targets UNKNOWN statically)
- 0x04F573E8: ld a5, 0x20(s3); ld a5, 0(a5); jalr a5 — vtable chain via s3 + 0x20.
- 0x04F575E0: ld a5, 0x30(s3); jalr a5 — the callback via s3 + 0x30 (this investigation).
- 0x04F57850: indirect jalr — target unknown from static bytes.
- No vtable/store initialization of s3 + 0x30 observed in-window.

## Boundaries
- NVUCODES header consumer at 0x0459C5E0: NOT touched (separate worker).
- No semantic engine names assigned; no source correlation beyond exact byte support.
- No hardware, keys, signatures, bypass, or brute force. Static analysis only.

## Evidence needed to resolve UNKNOWN
- The callee 0x05281930 epilogue: does it store the callback pointer to
  *(returned_context + 0x30) before returning (a0 = context)? See callee store list
  in gsp_context_writer.json.
- Resolution of the s3 + 0x20 indirect-init chain (0x04F573E8) or a runtime context dump.

## Artifacts
- gsp_context_writer.py — executable reproducible script (this run)
- gsp_context_writer.json — full machine report
- report.md — this concise report
- input_hashes.json — input hashes
- run.log — execution log
