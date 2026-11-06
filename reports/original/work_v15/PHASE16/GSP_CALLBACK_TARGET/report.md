# GSP_CALLBACK_TARGET — PHASE16 callback-target investigation

Scope: function candidate VA 0x04F5733C (file 0xF5737C), end-exclusive 0x04F57A00
(file 0xF57A40), from gsp_scan.json. Read-only, offline; no hardware, no keys,
no bypass, no new tools; only stdlib + capstone via /usr/bin/python3.
The live header consumer at 0x0459C5E0 was NOT touched (separate worker).
All outputs live under /home/REDACTED_USER/codex-work/work_v15/PHASE16/GSP_CALLBACK_TARGET/.
Existing jobs and artifacts were not modified.

## Inputs (hashes in input_hashes.json)

- source binary: outputs/gsp_tu10x.bin, 22901632 bytes,
  sha256 0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b
- PHASE16/gsp_callback_verified.json/.txt, gsp_callback_coordinator_review.json,
  REVIEW_NOTES.md, gsp_scan.json, gsp_local_disassembly.txt, gsp_callback_verify.py

## Mapping (inner ELF0x40)

Inner ELF64-LE header at file offset 0x40, parsed with struct only.
SHF_ALLOC section mapping with +0x40 header bias; empirically verified constant
delta VA = file_offset + 0x3FFFFC0 on 6 key VAs (loop, candidate entry,
callback, caller, helper, entry[0]). All 12 mapped raw bytes match the
verified disassembly byte-for-byte (file order).

## Verified fixed edges

- Caller: auipc ra,5 (raw 97000500) @ 0x04F06C18/file 0xF06C58 +
  jalr ra,ra,0x724 (raw e7804072) @ 0x04F06C1C/file 0xF06C5C
  -> computed target 0x04F5733C: VERIFIED.
- Helper: auipc ra,0xfffb0 (raw 9700fbff) @ 0x04F57644 +
  jalr ra,ra,-0x58 (raw e78080fa) @ 0x04F57648 -> target 0x04F075EC: VERIFIED.

## Function window 0x04F5733C..0x04F57A00 (433 instructions, section[28] text)

36 call sites: 33 direct auipc+jalr (all EXTERNAL to the function), 3 indirect
jalr (targets UNKNOWN from static bytes): 0x04F573E8 (vtable chain via s3+0x20),
0x04F575E0 (the callback via *(s3+0x30)), 0x04F57850.

## Context derivation (function input)

Entry args copied to saved regs: a0->s5 @0x04F5736C, a1->s4 @0x04F57378,
a2->s8 @0x04F57394, a3->s1 @0x04F57390. s0 = sp+0xe0 frame @0x04F57368.
s3 (the context pointer loaded at the callback via ld a5, 0x30(s3)) is NOT an
argument: it is the return value of the internal auipc+jalr call at
0x04F5739C/0x04F573A0 (computed target 0x05281930, external).

## Memory writes / vtable init to context+0x30

Stores enumerated: 48 stores, 42 loads. 14 static pointer constants formed by
lui/addi/ori and stored (e.g. 0x4F56FC88 at a0+0x110 @0x04F57414;
0x4F6303E4 at (s3+1)+0x470 @0x04F57420; ...). NO store to *(s3+0x30) exists
anywhere in 0x04F5733C..0x04F57A00. The context+0x30 callback-pointer slot is
written by a callee outside this window (context allocator call @0x04F5739C/3A0
callee, or the s3+0x20 indirect-init chain) — unproven statically.

Indirect pointer chain evidenced in-function:
ld a5, 0x20(s3) @0x04F573D4 (raw 83b70902); ld a5, 0(a5) @0x04F573DC (raw
83b70700); jalr a5 @0x04F573E8 (raw e7800700) — target UNKNOWN indirect.

## Callback call site 0x04F575E0 (raw e7800700, jalr a5)

ld a5, 0x30(s3) @0x04F575D4 (raw 83b70903); lhu a2, -0x88(s0) @0x04F575D8
(raw 035684f7); mv a0, s3 @0x04F575DC (raw 13850900); jalr a5 @0x04F575E0.

Two CFG predecessors into the callback block (enter at 0x04F575D4, fall-through
into the call):

1. First entry via j @0x04F575D0 (fall-through). a1 def mv a1,s4 @0x04F575A4 is
   KILLED by the external auipc+jalr wrapper call @0x04F575AC/0x04F575B0
   (computed target 0x04F4B500); no a1 rewrite before 0x04F575E0 ->
   a1 at call = CALL-CLOBBERED, UNKNOWN statically.
2. Loop back-edge via bnez a0,-0x7c @0x04F57650 taken (helper call
   @0x04F57644/48 -> mv a1,a0 @0x04F5764C -> bnez). a1 at call = helper return
   (PROVEN on this path), no intervening call.

Register facts at the call:
- a0 = s3 (context): PROVEN on both paths (mv a0,s3 @0x04F575DC, no write
  between def and call).
- a1: PATH-SENSITIVE — first entry UNKNOWN (clobbered), back-edge helper return
  PROVEN. a1 == s4 at the call is FALSE; do not revive a1=s4. The mv a1,s4
  instances (@0x04F57378 arg copy, @0x04F575A4 / @0x04F5761C helper argument,
  @0x04F57654 post-call fallthrough) are not the live def at 0x04F575E0 on all
  paths.
- a2 = lhu a2, -0x88(s0) @0x04F575D8: PROVEN straight-line; slot holds entry
  f00 u16 (written by sh a7,-0x88(s0) @0x04F57630 of the prior iteration).
  First-iteration initializing store is not dominated in this function.

Helper mutation of a2 source: helper @0x04F075EC is called with
a0=s5, a1=s4, a2=s0-0xe0 (caller sp = frame base), and its inner call passes
(a1=sp, a2=0x150) — a span covering slot s0-0x88 (sp+0x58). Helper mutation of
the a2 source slot (and thus of next iteration's a2) is NOT excluded statically.

## Candidate static targets vs proven assignments for *(s3+0x30)

- Candidate static targets: the 14 lui/addi/ori-formed pointers stored in-function
  (full list in gsp_callback_target_report.json, pointer_constants).
- Proven assignments to *(s3+0x30): NONE.
- Callback target: kept explicit as UNKNOWN indirect (jalr a5, a5 = *(s3+0x30));
  value not derivable from static bytes. No semantic names assigned to any
  target; no source correlation beyond exact byte support.

## Unknowns (explicit)

1. Callback target via *(s3+0x30): indirect, unresolved.
2. Writer of context+0x30: outside this function window.
3. a1 at callback on first-entry path: call-clobbered by wrapper call @0x04F575AC/5B0.
4. Initial value of stack slot s0-0x88 before first loop iteration.
5. Helper 0x04F075EC effect on stack slot s0-0x88 (a2 source): not excluded.

## Artifacts

- gsp_callback_target_analyze.py — the analysis script (this run)
- gsp_callback_target_report.json — full machine report
- run.log — execution log (exit 0)
- input_hashes.json — input/source hashes

## Verification

Script exit code 0; all 12 mapping sanity raw-byte checks matched; capstone
5.0.7 under /usr/bin/python3; disassembly window matches gsp_local_disassembly.txt.
