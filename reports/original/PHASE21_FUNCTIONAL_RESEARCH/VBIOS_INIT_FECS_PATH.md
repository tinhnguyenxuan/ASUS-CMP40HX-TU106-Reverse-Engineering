# VBIOS init FECS path — static command traversal

Input is the original 1 MiB ROM with SHA256 dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec. All script offsets below are relative to legacy-image base 0x28600; they are not GPU addresses. No ROM or MMIO command was executed.

## Entry and call edges

BIT I points to script table 0x4698. The first entry is script 0x7634, followed by zero terminator. Compiled envytools nvbios traversal enumerates:

`0x7634 -> 0x7639 -> 0x7644 -> 0x8a67 -> 0xca6e`

Individual CALL bytes at 0x7634, 0x763f, 0x764a and 0xc7f0 were checked directly against the original ROM. A related call at 0xc7f5 targets 0xca41. Tool log, executable/source/input hashes and invocation are in evidence/nvbios_script_provenance.json. The tool was built locally in /tmp; no install or device operation occurred.

This establishes a statically referenced command path and instruction boundary at 0xca6e (absolute ROM 0x3506e). Runtime execution remains conditional: the route includes condition0x26 and NOT at the parent, and condition0x33 near the relevant calls. It does not prove that this card evaluates those guards to the required states. Condition0x33 tests R[0xa00]&0x1ff00000==0; bit semantics are not assigned here.

The alternative 75 32 byte match at absolute 0x2b9e5 was not listed as a CONDITION instruction in this traversal. It remains an unproven byte candidate, not a second proven caller.

## Script 0xca6e

The bounded decoder consumes exactly through DONE at 0xcab2, independently checking lengths against the original ROM. It starts with CONDITION 0x32: R[0x409660]&0x10000==0x10000.

| Relative instruction | Encoded operation |
|---|---|
| 0xca70 | R[0x17e318] = (old & 0xffffffee) OR 0x10 |
| 0xca7d | R[0x17e21c] = (old & 0xfffffffe) OR 1 |
| 0xca8a | R[0x419b54] = 0xff |
| 0xca93 | R[0x419b68] = 3 |
| 0xca9c | R[0x419e20] = 0x10 |
| 0xcaa5 | POLL_NV_COND index0x51, parameter1 |
| 0xcaa8 | RESUME |
| 0xcaa9 | POLL_NV_COND index0x52, parameter1 |
| 0xcaac | RESUME |
| 0xcaad | POLL_NV_COND index0x53, parameter1 |

Conditions 0x51/52/53 test the corresponding 0x419b54/68 and 0x419e20 bits for zero. The stream includes RESUME commands; do not assume the first guard encloses every later operation without interpreter-state analysis. Exact register bit purposes, polling timeout units and effects remain unknown.

## Related script 0xca41

The bounded stream modifies 0x17e318 and 0x17e21c with corresponding bits clear, then encodes:

- 0xca5b: R[0x409658] = 0x00888888.
- 0xca64: R[0x40965c] = 0x002aaaaa.
- 0xca6d: DONE.

These are real ROM-encoded writes to the neighboring FECS feature cluster. They are NOT writes to speed selectors 0x409664 or 0x40966c. Their similar-looking repeated constants must not be conflated with the unlock payload. Exact meaning on TU106 remains unknown.

## Verification limits

The nvbios run completed script enumeration but also emitted compatibility and out-of-bounds read warnings while parsing other tables from the extracted 0xf400-byte legacy image. Thus this is not a clean full-ROM verification or evidence of complete devinit coverage. Evidence is confined to the inspected call edges, bounded streams and directly parsed condition records; the original ROM bytes remain authoritative. Five CALL encodings and two exact bounded streams are independently checked by tools/trace_init_condition50.py.

Next: identify TU106 consumers/field definitions for 0x409658/65c and FECS readout bit16; trace conditional execution semantics before claiming which writes occur on this board. Full display-init table traversal, reference-SKU comparison and original throughput selector writer are still outstanding.
