# GSP configuration value sources — bounded dataflow

Exact input: saved 615.78.08 GSP SHA256 0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b. Script tools/trace_config_helpers.py independently checks raw call/store encodings, ELF section mappings and fully decoded bounded windows. Output: evidence/gsp_config_helpers.json. No runtime action or patch was performed.

## Wrapper and lookup path

0x045e130c receives the name pointer in a1 and caller-supplied output pointer in a2. It saves them and calls 0x054eca80. A zero result is returned directly; a nonzero result restores saved arguments and tail-transfers to 0x045cc178. The initial call target and fallback target are independently resolved from raw AUIPC/JALR immediates.

0x054eca80 preserves output a2 in s2 and name a1 in s1. It checks a runtime initialization byte at VA 0x0439686c; the zero-byte path includes diagnostic/trap handling, so it must not be discarded when reasoning about initialization. Its ordinary lookup at 0x054ecac0 invokes 0x054dd7ec with name in a0 and type discriminator 1 in a1.

0x054dd7ec is a typed, case-insensitive name lookup in a linked list:

| Field | Offset | Direct observations |
|---|---|---|
| List head global | VA 0x04396ae8 | Loaded into t3; zero head follows not-found exit |
| Next-node pointer | node+0 | Loaded when type/name mismatches |
| Type discriminator | node+0x18 | Compared against incoming a1 |
| NUL-terminated name | node+0x19 | Bytewise comparison; ASCII A–Z folded by +0x20 |

The comparison loops and termination branches support the lookup description, without requiring an external symbol name. Unknown node allocation/registration and list initialization prevent recovering runtime key contents from these windows.

## Proven output writes

For a non-null type-1 result, 0x054ecacc loads a 32-bit word at node+0x10. At 0x054ecad0 it stores that word through saved output pointer s2, then returns a0=0.

If type 1 is absent, the helper tries type discriminator 2. A result is accepted only when the unsigned length at node+0x14 is greater than 3. It then loads a pointer from node+8, reads the first 32-bit word there and rejoins the same output-store path. Do not infer a full blob schema or authorize arbitrary memory access from this read sequence.

Missing or too-short entries return numeric 0x3e; null name/output paths return 0x1f. The saved NVIDIA nvstatuscodes.h maps these numbers to INVALID_REGISTRY_KEY and INVALID_ARGUMENT respectively. This corroborates registry/configuration interpretation; no original function symbol was recovered. The wrapper then attempts its fallback on any nonzero result, so a missing local key does not establish the final effective value.

## Fallback output path

0x045cc178 checks input pointers and an object byte at a0+0x6c3, derives a string length, invokes helpers and checks returned statuses. In its observed zero-status success path, 0x045cc29c loads a stack word at s0-0x5c and 0x045cc2a0 stores it through saved output pointer s3. The helpers providing that stack word and their transport/source remain unresolved. Do not label this as a specific RPC or host-supplied registry value without further tracing.

## File state versus effective configuration

The firmware file has zero bytes at both the list-head pointer and initialization byte. This proves file initialization only. It cannot establish a missing key, default value, initialized list, fuse value or final RmDisableDisplay state on the running card. Static metadata is insufficient to evaluate these runtime branches.

This locates a software configuration input path for the two display-name callers. It is separate from the host display-fuse capability predicate. Neither changing a configuration name nor finding an output-store path proves that display hardware, heads, PHY or PCB routes can be restored.

Remaining: list root writers/registration, fallback data source, effective key values, caller reachability/object identities, and the relation between object field +0x334 and final display engine capability reporting.

## List-head writer located

A bounded direct-store scan found a candidate at 0x054f4718; manual inspection and an independent raw store check confirm this sequence:

- 0x054f470c sets a5=0x04397000.
- 0x054f4710 loads the old head from a5-0x518.
- 0x054f4714 initializes node type byte at s3+0x18 to zero.
- 0x054f4718 stores s3 into the head global at 0x04396ae8.
- 0x054f471c writes the old head into node+0; 0x054f4720 returns the new node through a pointer held in s4.

This establishes a concrete linked-list insertion sequence and mutable runtime storage for the configuration list. It does not establish a host-accessible writer, the final type/name/value, callers or any effective setting on the card. Root-store scan coverage is narrow and cannot exclude other writers. Raw context is in evidence/config_root_store_candidates.json and the independently mapped helper extraction. Node allocation and final key population remain open.

Follow-up: `GSP_CONFIG_POPULATION.md` now traces constructor inputs, two generic integer setters and a concrete initialization-byte writer. Original configuration ingestion, live key values, fallback source and display object identity remain unresolved.
