# Coordinator final review

Job `falcon_cfg_rebuild_v1` completed with runner exit code 0. Accept explicit-hex envydis invocation, span hashes, byte-matched decoded output, and the corrected treatment of conditional/unconditional transfers and indirect calls within decoded instructions. Candidate entries and engine roles remain UNKNOWN.

The traversal is severely bounded by decode gaps. Independently inspected final `machine.json`: the sole reachable block for slot 20 ends at 0x68, followed immediately by invalid bytes `3e74fe00`; slots 150/156 end at 0x34, and slots 481/484/487/490/493 at 0x37, all followed by invalid bytes `89000000`. Each has `unresolved_edge_count=0`, yet no terminal control-flow instruction explains stopping before the gap. The stop is an unresolved decode continuation and must be counted/labeled. The 30–62 reachable bytes measure only the decoded prefix from an unproven candidate anchor, not the full executable extent.

The thousands of other linearly decoded blocks are not proven reachable. Their `unreachable` label is relative to this truncated traversal, not proof that the bytes are data/noncode. Full-span linear byte coverage is a disassembler accounting result, not complete Falcon CFG. Follow up on the repeated decode-gap bytes, possible format/ISA-mode boundaries, and authentic entry metadata without inferring engine roles from slot IDs.
