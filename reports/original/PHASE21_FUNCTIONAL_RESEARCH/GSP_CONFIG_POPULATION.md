# GSP configuration population — bounded static evidence

Input: saved GSP 615.78.08, SHA256 `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`. All addresses are inner-ELF VAs. Reproduce with `tools/trace_config_population.py` using Capstone; machine-readable raw instructions, section-derived file offsets and window hashes are in `evidence/gsp_config_population.json`.

## Node construction at 0x054f465c

The routine receives an output-pointer address in a0 and a name pointer in a1. On its ordinary non-null-name path it clears the output pointer, saves the name in s2 and the output address in s4. It counts bytes to the NUL terminator. For nonempty names, the observed length including the terminator is compared unsigned against 0x100; larger values branch into diagnostic/error handling. The empty-name path uses length 1 and allocation-size argument 0x21.

The routine passes the name length plus 0x20 to helper 0x05281930. Its return is retained in s3; a null return leads to numeric status 0x51. Subsequent calls pass `(node, 0, 0x20)` to 0x05275ffc and `(node+0x19, length, name, length)` to 0x052754d4. These arguments are consistent with allocation, zero initialization and bounded name copying, but the helpers' complete implementations have not been verified here. The final call's zero return enters cleanup and numeric status 0x40, rather than inserting the node.

On the insertion path, instructions explicitly initialize node+0x18 to zero, read the previous list head at 0x04396ae8, set the head to the new node, place the old head in node+0 and return the node through the saved output address. This expands the previously established insertion sequence to its name/size inputs. It does not identify the original source of those names.

## Integer setter at 0x054f482c

The routine rejects null a0 with numeric status 0x1f. Otherwise it preserves incoming a0 as the name and a1 as a 32-bit value in s2, then invokes the previously decoded lookup 0x054dd7ec with discriminator 1.

| Path | Observed writes |
|---|---|
| Existing type-1 node found | 0x054f4878 stores s2 to node+0x10; returns zero |
| No type-1 node found | Calls constructor 0x054f465c at 0x054f48bc using the saved name and a stack output slot |
| Constructor returns zero | 0x054f48d4 sets node+0x18 to 1; 0x054f48dc writes value at +0x10; 0x054f48e0 writes length 4 at +0x14 |
| Constructor returns nonzero | Propagates status through diagnostic handling without taking those success stores |

This connects a concrete writer to the same node fields consumed by the display-name configuration reader. The writer is generic: no specific `RmDisableDisplay` value or caller is established by this window.

## Second setter and guarded wrapper

At 0x054f4a5c, the code additionally writes 1 to the initialization byte at VA 0x0439686c before its null-name check. It performs a type-1 lookup and the same existing-node value update. Its successful creation path at 0x054f4b00 sets type 1, the input value and length 4. This provides an explicit initialization-byte writer, although the full initialization lifecycle and its caller remain unresolved.

At 0x054f4910, the ordinary path checks bytes at 0x04396ae0 and 0x0439686c, then tail-transfers to the first integer setter with original a1 as name and original a2 as value. Other paths include diagnostics, traps and a numeric 0x56 return. These checks must be retained when reasoning about reachability; locating a generic setter does not establish that an external host can invoke it.

## Verification and limits

The tool independently checks the raw opcode, store width, register operands and signed displacement for 11 stores. Four bounded instruction windows decode without gaps. A halfword-aligned executable-section scan finds four adjacent AUIPC/JALR candidates targeting the constructor and one targeting the first setter. Only the two constructor calls and wrapper tail-transfer inside the inspected windows are explained here; the remaining candidates need enclosing CFG/dataflow analysis. The scan does not cover indirect calls, separated address-building instructions or all control-flow forms, and its candidates are not automatically reachable call sites.

No GPU operations occurred. No original firmware symbols were recovered. Effective key values, upstream configuration ingestion, synchronization, fallback transport, display object identity and display hardware availability remain unknown. Next: inspect constructor candidates at 0x054f4c64 and 0x054f4f44, then recover callers of the initialization setter and wrapper to locate configuration ingestion.

Follow-up: GSP_SYSTEM_INFO_INGESTION.md resolves the remaining constructor candidates as type-2/type-3 setters and connects registry system-info dispatch to the initialization setter. Evidence extraction now includes 19 raw stores, nine raw control checks and seven windows. Earlier counts above describe the initial extraction.
