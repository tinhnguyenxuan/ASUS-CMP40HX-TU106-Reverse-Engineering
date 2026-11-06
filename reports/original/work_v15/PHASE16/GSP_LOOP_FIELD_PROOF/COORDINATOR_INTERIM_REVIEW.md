# Interim coordinator audit (job still running)

The current generated CFG has 516 nonoverlapping blocks and 2205 unique decoded instructions. Seed-present and seed-absent runs both retain one local `flags+16` access, but this does not prove all record iterations.

The machine evidence currently hardcodes `s9_defined_in_entry_block=true`, `s10_defined_in_entry_block=true`, and `s8_defined_in_entry_block=true`. Independent inspection of its own `disassembly/cfg.json` places these definitions (0x459C6E8..0x459C6F8) in block 0x459C6E8, while the entry is block 0x459C5E0. These booleans are false as written.

An independent dominator calculation over the report's edge list finds block 0x459C6E8 does **not** dominate block 0x459C6FC. A CFG path avoiding the definition block is: 0x459C5E0 -> 0x459C64C -> 0x459C654 -> 0x459C664 -> 0x459C670 -> 0x459C680 -> 0x459C68C -> 0x459C6B4 -> 0x459C6BC -> 0x459C6D0 -> 0x459C6D8 -> 0x459C810 -> 0x459C824 -> 0x459C828 -> 0x459C844 -> 0x459C890 -> 0x459C898 -> 0x459C8A4 -> 0x459C8D8 -> 0x459C7D0 -> 0x459C7F8 -> 0x459C6FC. Whether this path is feasible under actual branch predicates is still open, but the current CFG alone cannot prove dominance. Do not accept loop-universal base or index claims from hardcoded booleans.

The intra-block chain from 0x459C6E8 to 0x459C70C remains a candidate path-specific `flags+16` fact and is independently supported by raw instructions. Final job output must be checked again after worker completes.
