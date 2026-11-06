# Firmware provenance and capability-string inventory

Reproduce from workspace root: `python3 PHASE21_FUNCTIONAL_RESEARCH/tools/firmware_capability_inventory.py`. This reads binary files only. It parses bounded ELF64 little-endian section headers, records SHA256 and extracts the actual outer `.fwversion` section. An independent `readelf -p .fwversion` result is saved for the project GSP binary.

| File | Bytes | fwversion | SHA256 |
|---|---:|---|---|
| work_v15/outputs/gsp_tu10x.bin | 22901632 | 615.78.08 | 0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b |
| /tmp/gsp_firmware/gsp-570.144.bin | 28542040 | 570.144 | 3052aee2872182a14d8d7c069e3a14fe4642405894b24692c4aca4101dfb1809 |
| /tmp/gsp_firmware/gsp-535.113.01.bin | 23750944 | 535.113.01 | be2c3bb39cee2c4bd6680dce9eb75b26105c576e5aaf2c82f59d11a79f103749 |

The project GSP contains an inner ELF at file offset 0x40. Section address mappings are recorded directly, not imported from old JSON. File/version labeling is now independently confirmed; installation/loading of these bytes on the target is still unverified. Metadata is identification evidence, not a signature authentication result. Cross-version offsets must not be transferred without a function/content match.

## Direct string observations in 615.78.08

| String | File offset | What is established |
|---|---|---|
| RmDisableDisplay | 0x9e968, 0xb3078 | Two distinct string locations; no proven consumer |
| RmForceGridDisplayless | 0x8a320, 0xb4bd8, 0xc6348, 0x1c0878, 0x1fa338 | Multiple occurrences, not one function entry |
| RmProfilerFeature | 0x135888 | Name exists; permissions/capability semantics unproven |
| RmProfilerControl | 0x1358a0 | Name exists; no profiling support proved |
| RmDisableSec2 | 0x1bbd20 | Name exists; cannot call a string |
| RmDisableSec2Load | 0x1bbd68 | Distinct name; no runtime bypass proved |

The full filtered inventory contains 37 printable NUL-terminated strings, with file offsets and mapped section VAs. This is a heuristic filter, not a complete capability/function inventory. Duplicated names do not establish duplicate executable gates, registry defaults or active policy.

A bounded scan for adjacent 32-bit AUIPC/LUI plus ADDI/ADDIW address materializations found zero exact references to these string starts. It examined halfword-aligned syntax candidates in executable sections, without a CFG. An independent raw aligned/un-aligned 64-bit pointer-value search in non-executable mapped sections also found no candidates. Neither negative search excludes consumers: compressed operations, nonadjacent definitions, offsets within strings, relocations, 32-bit/relative tables and indirection are not covered. No absence-of-interface claim follows.

## Next useful analysis

Recover registry/name lookup table storage and relative-pointer conventions on this exact binary; then follow the lookup result into branches or bitmasks. Prioritize the two RmDisableDisplay strings and exact display-fuse consumer rather than security-looking names alone. Preserve GSP and SEC2 identities separately: the local SEC2 image is not proved to be the Booter or ISA used by current GSP. Do not execute prior exploitation scripts to resolve provenance.

Follow-up: bounded nonadjacent LUI/ADDI tracing now recovers local code references, including both RmDisableDisplay strings. The previous zero adjacent-reference result remains true only for its narrower coverage. See GSP_DISPLAY_CONFIG_DATAFLOW.md and evidence/gsp_name_xrefs.json.
