# GSP display configuration references — bounded static proof

Input: project GSP 615.78.08, SHA256 0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b. Reproduce with tools/gsp_name_xrefs.py after firmware_capability_inventory.py. Addresses below are inner-ELF virtual addresses, not file offsets. Mappings come from the freshly parsed inner ELF sections.

## Why the earlier search missed the references

Name addresses are commonly formed by LUI followed by ADDI with an intervening instruction. The previous adjacent-pair scan deliberately did not cover that case. Extending to at most 16 straight-line 32-bit instructions, stopping at control transfers, unknown/compressed instructions or source-register clobber, finds 38 local name-address computations from 1425 candidate LUI seeds. Candidate boundaries are halfword-aligned and not all proven by an enclosing CFG, so the global count is not a count of reachable gates.

Raw bytes and disassembly for every match are in evidence/gsp_name_xrefs.json. The two display sites below were inspected manually, including following branches and callee entry. They are stronger evidence than string names alone; runtime reachability remains unproved.

## RmDisableDisplay site A

- String file offset 0x9e968, mapped VA 0x0409e928.
- 0x04840368: LUI a1,0x409f; 0x0484036c: a2=s0-0x3c; 0x04840370: ADDI a1,a1,-0x6d8. This computes exactly the string VA in a1 and a stack-relative pointer in a2.
- Adjacent AUIPC/JALR at 0x04840374/378 resolves from raw immediates to helper 0x045e130c, return register ra.
- Return a0 is sign-extended to 32 bits; nonzero branches from 0x04840380 to 0x048403d4. This path performs additional byte tests; it is not simply the same as reading a value of 1.
- On zero return, word at s0-0x3c is read and compared with 1. Equality branches from 0x0484038c to 0x048403fc. That block makes another call and sets a0=0 before joining the epilogue path.
- Other paths can invoke a function pointer loaded from s1+0x1c8. Its identity and return meaning have not been recovered.

## RmDisableDisplay site B

- String file offset 0xb3078, mapped VA 0x040b3038.
- 0x04b300c0/0x04b300c8 computes the string into a1; a2=s0-0x3c, a0=s1 before the call.
- AUIPC/JALR at 0x04b300d0/d4 resolves to the same helper 0x045e130c.
- Nonzero return branches at 0x04b300dc to 0x04b300ec, bypassing the word-value test.
- On zero return, word at s0-0x3c is compared with 1; equality branches at 0x04b300e8 to 0x04b30138.
- At 0x04b30138, that value (a5=1 along the equality edge) is stored to s3+0x334, then execution rejoins 0x04b300ec. Follow-up raw decoding proves s3 is the worker's second argument. In the same worker, `RMRunFub == 1` stores byte 1 at +0x328 and a nonzero `RMFubUseCaseMask < 0x2000` stores a word at +0x32c. Thus +0x334 is specifically the second argument's cached/latching field populated from `RmDisableDisplay == 1`; the original object/class name remains unknown. See `GSP_DISPLAY_OBJECT_FIELDS.md`.

## Helper 0x045e130c

Entry checks a1 and a2 for null. It saves the name-like pointer and output-like pointer, calls another helper, and on a nonzero result tail-transfers elsewhere with the saved arguments. This is consistent with a configuration-read wrapper and fallback, but the exact API name, error enumeration, value source and fallback semantics are not yet proven. In particular zero return cannot yet be labeled NV_OK solely from the common convention. Subsequent uses prove that the callers conditionally inspect a word at the supplied stack pointer; writes to that word still need callee tracing.

## What this changes and what remains open

There are concrete GSP code references and value-dependent branches for RmDisableDisplay in this binary. That is separate evidence from the host display-fuse gate and empty VBIOS routing. It does not establish the configuration value on the target, a reachable bypass, a default, a user-writable registry control, or any surviving display/PHY hardware. RmProfilerFeature, RmProfilerControl and SEC2 configuration names also have local xrefs in the saved output; their downstream decisions remain to be traced.

Follow-up also recovers a downstream boolean gate at 0x04b20f54: after two other prerequisites, a zero +0x334 field produces output byte 1 and a nonzero field produces output byte 0. The source-level result name remains unknown. Next: recover the original class/type and gate prerequisite identities, then connect the decision to a captured display-IP response. No GPU operation, privileged firmware invocation or patch was performed.

Follow-up: helper tracing now identifies a typed case-insensitive linked-list lookup and concrete output writes in the primary and fallback paths. The previously unresolved question whether a word is written through the supplied output pointer is resolved for these observed success paths. See GSP_CONFIG_VALUE_SOURCES.md; effective runtime value, original symbols and fallback transport remain unknown.
