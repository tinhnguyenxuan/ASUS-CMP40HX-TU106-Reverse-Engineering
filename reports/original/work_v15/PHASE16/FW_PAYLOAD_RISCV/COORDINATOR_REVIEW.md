# Coordinator review — FW_PAYLOAD_RISCV

Reviewed completed job state/output, `FW_PAYLOAD_RISCV_REPORT.md`, and `payload_riscv_verified.json` (38 entries; 8 Falcon labels, 30 UNKNOWN; source/input hashes match the Phase16 container inventory).

- Correctly resolves prior Capstone availability contradiction: `capstone_available=true` was correct for `/usr/bin/python3`; real RISC-V decode was run. No RISC-V ISA is proven. This is not proof that no RISC-V code exists: scan is bounded to aligned candidate starts in first 512 bytes and bounded windows, with chosen thresholds. Retain UNKNOWN for unresolved spans and state scope of negative result.
- Source-struct rejects at offset 0 are evidence only about those candidate structs at offset 0, not a global rejection of all possible layouts.
- Eight Falcon classifications are medium-confidence bounded decode signatures. Several density values are only 0.136–0.389 and no authoritative engine/slot/role mapping is established. Treat these as likely Falcon code, not complete firmware identification or complete decode.
- Report's prose says high-entropy slots are “rejected as executable code” but elsewhere correctly says UNKNOWN. No decode heuristic proves arbitrary payloads are non-code. Prefer “no candidate met the bounded decode threshold; ISA/role UNKNOWN.”
- Engine names, descriptor instantiations, and the other 30 payloads remain unresolved. Consumer and engine-interface jobs may supply cross-references later.

Useful evidence is retained; do not promote heuristic absence to a global negative claim.

## Confirmed envydis argument-radix defect

Caller payload_riscv_analyze.py line123 passes str(skip)/str(limit), but /tmp/envytools/envydis/envydis.c lines94/97 parses both with sscanf `%x`. Thus decimal36 labeled offset0x24 actually requests tool skip0x36; decimal16 labeled0x10 actually requests skip0x16. Window limits are also wrong. Previously reported Falcon entry offsets and density/window evidence require recomputation with explicit hex strings and raw input/output offset checks. This does not affect Capstone RISC-V calls, but weakens Falcon-entry/coverage claims. Current deep worker uses hexadecimal formatting for full-span lengths; its heuristic primary entry is still not authoritative.
