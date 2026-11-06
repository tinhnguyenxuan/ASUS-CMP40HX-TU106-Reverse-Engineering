# System-info NVKV callback connection

Input: project GSP 615.78.08, SHA256 `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`. Addresses are inner-ELF VAs. Evidence: `evidence/gsp_nvkv_callback.json`, reproduced with `tools/trace_nvkv_callback.py`. This is offline static dataflow, with no device operations.

## Concrete callback use

The prior adjacent direct-call scan did not find a call to registry key handler 0x054f4f98 because this handler is passed as an argument:

| Site | Observed arguments/transfer |
|---|---|
| 0x054f9fd0 | Receives buffer pointer in a0 and byte length in a1; saves them in s5/s6 |
| 0x054fa058–068 | Forms a0=0x054f4f98 using LUI/ADDI, with intervening writes to other registers |
| 0x054fa05c | a1=buffer pointer |
| 0x054fa060 | a3=stack context at s0-0x1b8 |
| 0x054fa064 | a2=low-32-bit byte length shifted right by 3 |
| 0x054fa06c/070 | Calls helper 0x04678290 |

The helper retains a0 in s5 and invokes it through JALR at 0x046783b8, 0x0467845c, 0x04678500 and 0x0467852c. It passes an extracted index in a0, key in a1, stack value descriptor in a2 and unchanged caller context in a3. These register assignments connect the wrapper to the registry handler and its typed setter calls. This is a callback invocation connection, not evidence of a persistent function-pointer registration table.

The wrapper first initializes its context and, after decoding, checks both the decoder return and a context status word: s0-0x5c equals context+0x15c. This is the same offset to which the registry handler writes numeric 0x1f on observed malformed-value paths. Thus the handler's return-to-continue convention and separate context status have a concrete downstream consumer.

## Descriptor semantics

The preexisting local `nvkv.h` declares `NVKVValue` with data pointer at +0, 32-bit valueCount at +8, 32-bit valueType at +0xc and decodeIndex at +0x10. Its U8/U32/U64 type values are 0/2/3. The helper constructs precisely these fields in observed cases. The U32 literal `0x0000000200000001` in the registry handler is therefore count=1 and type=2, rather than an unexplained magic value.

The wire header extraction at 0x04678334–364 gives key bits 15:0, index bits 27:16, opcode bits 31:28 and upper 32-bit immediate/count. The six raw dispatch-table words at VA 0x04091524 map opcodes as follows:

| Opcode | Local header definition | Firmware target |
|---|---|---|
| 0 | IMM32 | 0x0467850c |
| 1 | SEQ32 | 0x0467848c |
| 2 | SEQ64 | 0x046783f8 |
| 3 | ARRAY8 | 0x046783d0 |
| 4 | ARRAY32 | 0x0467837c |
| 5 | ARRAY64 | 0x04678468 |

For example, IMM32 stores the upper header word in a stack slot, sets descriptor count/type to 1/2, and invokes the callback with a pointer to that slot. ARRAY8 checks buffer bounds, sets count to the upper header word and type to 0, then supplies a payload pointer (or null for zero count). This explains why the descriptor pointer cannot automatically be treated as an enduring pointer into the input buffer.

After each inspected invocation, a nonzero callback return continues traversal; zero takes the ordinary zero-status return path. This resolves the earlier unknown return convention: handler return 1 means continue decoding, not proof of setter success. Buffer bounds and unsupported opcode paths are handled separately. The full parser is extracted, but this report does not claim a comprehensive audit of every sequence/index edge case.

The local header supports the semantic names above and is snapshotted with its hash. Retrieval of its exact official 615.78.08 web page failed in this turn; exact-source provenance for this file remains unverified. The raw field extraction, callback assignments and dispatch-table values are independently observable in the hashed firmware.

## Earlier packet consumer

At 0x054fa2e4, an enclosing packet consumer obtains an input pointer from a global context, reads the first word, masks to 24 bits and compares against 0x10001. Its ordinary path later reads byte length from packet+4, sets a0=packet+0x28, and tail-transfers at 0x054fa3dc to 0x054f9fd0. The official 615.78.08 GMCAPI table now resolves command 0x10001 as `GMCAPI_CMD_GSP_INIT`; the host source sends its encoded system-info and registry NVKV stream through that command. See `HOST_REGISTRY_PRODUCER.md`. The enclosing firmware function still has additional preconditions and paths not exhaustively audited here.

## What remains

The configuration list now has a concrete upstream callback/decoder/wrapper connection, and official host source identifies the producer and GSP_INIT transport. Still unresolved: the running driver's supplied names/values, `osPackageRegistry()` input coverage, read-wrapper fallback source, object field +0x334 and live display-IP responses. No effective RmDisableDisplay value, display capability bypass or restoration has been proved.

Verification: eight independent raw checks cover callback-address formation, direct transfers, four indirect calls and six dispatch-table entries; three bounded windows decode without gaps. This evidence expands dataflow coverage; it is not a GPU runtime test.
