# Coordinator review — Phase 16

The full CMP40HX/TU106 reverse-engineering objective remains active. Hermes
implements research tasks; Codex checks actual files and evidence before accepting
their conclusions. A returned MCP reply is not proof that the described work exists.

## Accepted observations

- `hermes_regression.log` contains 18 executed tests, `OK`, `EXIT_CODE=0`.
  This validates the tested decoder/mapping cases, not whole-GPU semantics.
- The original archive manifest covers 157 files and matched the supplied v15
  extraction at intake. The original archive and baseline binaries are preserved.
- Legacy clean-extraction verifier emitted 161 PASS lines, not 162. Many checks
  concern saved JSON, report wording, or constants; they do not establish semantics.

## GSP_AUDIT.md / CHECKPOINT.json: not accepted as fully verified

1. The reported `a1=s4` at the callback omits the later helper-return path and
   backward branch. The local instruction window must cover the helper call,
   `mv a1,a0`, and the edge back to the callback. Reaching definitions must follow
   the actual CFG, including intervening calls and caller-saved registers.
2. Some raw bytes are transcribed as word values rather than file byte order.
   Every instruction row must preserve the bytes read from the source binary.
3. Entry 0's `f10` and WPR LO addresses were copied with missing zero digits.
   Use generated hexadecimal values rather than editing numbers by hand.
4. The `f18` two-byte layout is observed; names such as group/subtype require
   evidence from consuming code and are not established by a histogram.
5. `scratch/phase16_repro.py` is not an independent correctness oracle:
   its `file=off-0x3ffffc0` expression is incorrect for a value already supplied as
   a file offset, and its WPR mask `0xFFFFF` covers 20 bits instead of the 28-bit
   `VAL[31:4]` field. These affect emitted metadata and decoded addresses.

## New callback verifier: review gates

The first saved `gsp_callback_verify.py` omitted the embedded ELF base when
reading program/section headers and offsets, and compared a section name to a
formatted section identifier. It also treated a linear instruction prefix as a
CFG reaching-definition analysis. Hermes has been given these exact defects to
fix; file existence alone must not be taken as a successful verifier run.

Acceptance requires successful execution with `/usr/bin/python3`, saved raw
disassembly and JSON, agreement between ELF section/program mappings where both
cover a byte, and explicit unknowns for any unresolved predecessor/callback target.

## Subsequent investigations

- Firmware: test the hypothesis that header word `0x0c=496` is an entry count,
  not a header byte size. Check a 24-byte header followed by 496 24-byte records:
  candidate length at record+0 and marker/file offset at +16/+20. This is a
  hypothesis to verify across the entire container, not a specification yet.
- Fuse: use NVIDIA's published Turing TU102 `dev_fuse.h` for documented fields
  at `0x2174c` and `0x21378`. Availability of two definitions does not decode
  the remaining dump or prove physical OTP geometry.
- Memory: validate `VAL[31:4] << 12`, upper-bound interpretation, and allocation
  overlap before attributing the reported NVML Reserved memory.
- Keep explicit coverage for VBIOS, MMIO, topology, memory, PCIe, security
  architecture, and the wider GSP firmware; see `COORDINATION.json`.

NVIDIA source used for the fuse follow-up:
https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/main/src/common/inc/swref/published/turing/tu102/dev_fuse.h
