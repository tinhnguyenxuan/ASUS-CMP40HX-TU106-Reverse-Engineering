# Compute selector evidence — scope and generation audit

Target: supplied TU106-100-A1 / CG161P REV2 / VBIOS 90.06.67.00.06, current driver and state not freshly measured. All analysis here is offline.

## TU106 evidence

The saved cmp40hx patch names FECS 0x409664 and 0x40966c as SM-speed overrides and uses 0x88888888 and 8. The secondary Phase19/20 report contrasts these with stock zeros and attributes failed persistence to GSP. These observations do not recover per-bit semantics or the original writer, and runtime observations still require raw trace corroboration.

An independent ROM parse now finds a FECS readout condition, not a selector write:

| Item | Direct ROM value |
|---|---|
| BIT I data | relative 0x293, absolute 0x28893 |
| Condition-table pointer | BIT I +6 -> relative 0x469c, absolute 0x2cc9c |
| Record index | 50 (0x32), stride 12 |
| Record absolute offset | 0x2cef4 |
| Register/mask/expected | 0x409660 / 0x00010000 / 0x00010000 |
| Predicate | (R[0x409660] & 0x10000) == 0x10000 |

Reproduce with tools/vbios_fecs_condition.py. Input ROM and saved envytools parser source hashes, raw record and bounds are in evidence/vbios_fecs_condition.json. This grounds a VBIOS condition-table relationship to the FECS feature-readout cluster. It does not establish bit16's function, a throughput divisor or any write to 0x409664/66c.

The same raw readout address occurs in a second ROM bank at 0xa5ef4. That is within the same file, not an independent card comparison. Byte pairs 75 32 occur at 0x2b9e5 and 0x3506e in the legacy image; 0x75 is the saved parser's CONDITION opcode. These are candidates only until script-entry and instruction boundaries are proven. Do not call either site a reachable init branch from the byte match alone.

## What the Ampere source does and does not establish

The preexisting local /tmp/gpu-unlock documentation describes eight instruction-class speed fields and one additional field on GA102. Its source constants locate those registers at 0x82381c/0x823820 and their PLM at 0x823804, different from the CMP40HX FECS cluster. It explicitly describes some divisor interpretations as unconfirmed. Its BF16-focused workload claims and pre-driver reset flow therefore cannot establish TU106 bit meanings, support, reset behavior or successful unlock.

Research origin: https://github.com/Zagitta/gpu-unlock . Consult the exact saved source hashes when comparing a mutable upstream repository. No build, install, firmware payload generator or device action from that project was run.

The repeated override pattern is compatible with a family of instruction-issue-rate controls; exact TU106 assignment and encoding remain UNKNOWN. It must not be reinterpreted as one nibble per SM/TPC. The number of nibbles is insufficient topology evidence. Runtime override/readout values are not raw physical OTP cells.

## Discriminating hypotheses

- Protection rejection: a host write may never commit. Requires recognized protection/error status and immediate readback, not a later sample alone.
- Initialization/reset rewrite: an actual state transition may reapply a configured value. Requires timestamps and an identified transition/writer.
- Firmware writer: a firmware store linked to the selector and source policy must be recovered; the old summary's attribution to GSP is not that proof.
- Readout/override interaction: effective execution may depend on another source when override enables are clear. Requires matched TU106 field definitions or validated execution/selector comparisons.

The current prompt prohibits automatic state-changing MMIO/firmware experiments. Static consumers, existing raw traces and bounded correctness captures are the next evidence paths. Exact selector restoration on this specific card remains unproved in this phase.

Follow-up: VBIOS_INIT_FECS_PATH.md establishes a static path from the actual BIT I entry to condition50 at relative 0xca6e (absolute0x3506e), with guarded command streams and separate neighboring FECS writes at 0x409658/65c. Earlier statements that both CONDITION-50 byte matches lacked boundaries are superseded for this one site. Runtime guard results and exact field meanings remain unknown.

## Same-family source corroboration

TURING_EXTERNAL_CORROBORATION.md adds a revision-pinned third-party Turing access-site review and an operator-reported TU106 GeForce result. Actual code uses the FECS cluster despite different inherited header constants. This strengthens address-family comparison only; exact bit semantics and restoration on CMP40HX remain unproved.
