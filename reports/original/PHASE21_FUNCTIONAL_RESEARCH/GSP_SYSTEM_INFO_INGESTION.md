# GSP system-info registry ingestion

Input: project GSP 615.78.08, SHA256 `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`. Addresses are inner-ELF VAs. This extends the earlier generic setter work with an independently corroborated input protocol and concrete dispatch branches. No device operation was performed.

## Protocol identity and dispatch

The [official NVIDIA 615.78.08 system-info header](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/interface/gmcapi/gmcapi_system_info.h) describes CPU-to-GSP system-info keys for passing a registry name followed by a typed value. Its four constants match the recovered firmware comparisons:

| Key | Header meaning | Observed local path |
|---|---|---|
| 0x3070 | REGKEY_NAME | Branch 0x054f506c → 0x054f5fd4 |
| 0x3071 | REGKEY_VALUE_U32 | Equality falls through 0x054f5174 → 0x054f5178 |
| 0x3072 | REGKEY_VALUE_STRING | Branch 0x054f5078 → 0x054f5f60 |
| 0x3073 | REGKEY_VALUE_BINARY | Equality falls through 0x054f5080 → 0x054f5084 |

The parser candidate begins at 0x054f4f98. It saves incoming a1 as the key, a2 as the value-descriptor pointer (s3), and a3 as the context pointer (s4). Other key groups use indirect jump tables. The registry cases above are selected by direct comparisons; the table is therefore supported by branch encodings and local dataflow rather than constant/string co-occurrence alone. The firmware routine has no recovered original symbol. `GSP_NVKV_CALLBACK.md` establishes its callback reachability, while `HOST_REGISTRY_PRODUCER.md` identifies the host `GSP_INIT` transport.

## Name/value pairing state

The name path requires incoming a0 to be zero, a nonzero word at descriptor+8 and zero word at descriptor+0xc. It passes descriptor+0's pointer and that length to helper 0x052757e4, with destination context+0x10 and size argument 0x100. It then checks the byte at context+0x110: zero is changed to 1, while nonzero enters diagnostic/error handling.

The U32 path checks the doubleword at descriptor+8 against literal 0x0000000200000001, reads a word through the pointer at descriptor+0, and requires context+0x110 to be nonzero. It clears that byte and calls the initialization integer setter 0x054f4a5c with context+0x10 as name and the read word as value. This setter sets the configuration initialization byte at 0x0439686c and populates the typed linked list used by the configuration reader.

The string/binary paths require incoming a0=0, descriptor+8 nonzero and descriptor+0xc zero; both require and clear the pending-name byte. They set the configuration initialization byte to 1, pass context+0x10 as name, descriptor+0's pointer as data, and descriptor+8 as length to the respective setters. The descriptor's complete public type layout has not been recovered; the raw packed U32 check is not assigned invented field names.

In these three value cases the parser sets its own return to 1 after the setter call without testing the setter's returned status. Thus observing a recognized key or return 1 would not alone establish successful storage. Earlier error handling can write numeric 0x1f to context+0x15c. The meaning of the parser's return convention is not established.

## Previously unexplained constructor calls

0x054f4c64 is in the type-2 setter at 0x054f4b50. It looks up discriminator 2, creates a node if absent, and otherwise releases/replaces existing external data via helpers. The successful allocation path stores the new data pointer at node+8, type 2 at +0x18 and input length at +0x14, then invokes a copy-like helper with the input data and length. The setter later returns zero without inspecting that copy helper's result. Allocation failure returns numeric 0x51. This concretely supplies the type-2 nodes whose first four bytes can be consumed by the integer-read fallback described in GSP_CONFIG_VALUE_SOURCES.md.

0x054f4f44 is in the type-3 setter at 0x054f4e18. Its success path stores type 3, input length and a new data pointer; it passes length minus one to a copy-like helper, then explicitly writes a NUL byte at new_data+(length-1). This is consistent with the official string key's routing to this setter. These bounded windows do not prove all caller length constraints or full allocator/copy semantics.

## Evidence and remaining limits

`tools/trace_config_population.py` now emits 19 independent raw store checks, nine raw call/branch checks and seven fully decoded bounded windows in `evidence/gsp_config_population.json`. It records 16 adjacent AUIPC/JALR candidates across the constructor/setter/wrapper/parser targets; these are not a complete reachable call graph. No adjacent direct-call candidate to the parser entry was found by this narrow scan; indirect registration remains possible.

The local header is snapshotted and hashed in the source manifest. Only the relevant registry key declarations, direction comment and length limit were corroborated against the official tagged web source on 2026-11-04; the whole local source tree is not treated as pristine stock source.

This identifies a concrete system-info ingestion path to the configuration list. Official host source now proves that its packaged registry entries are appended to the system-info NVKV stream and sent with `GSP_INIT`. It does not prove that the running driver supplies RmDisableDisplay, that the fallback reader shares this transport, or that any display engine or PHY can be restored. Retain separate audits of live registry values, fuse support, display object identity and target capability responses.

Follow-up: GSP_NVKV_CALLBACK.md resolves callback use and descriptor/return semantics. The registry handler receives NVKV key index in a0, not an established status value; its return 1 tells the decoder to continue. The packed U32 check is count=1/type=2. A concrete wrapper supplies the handler pointer and input buffer to the decoder; full transport/host production is still open.
