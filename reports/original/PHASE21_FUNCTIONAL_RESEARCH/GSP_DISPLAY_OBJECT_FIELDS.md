# GSP display configuration object fields

Input: project GSP 615.78.08, SHA256 `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`. Reproduce the raw checks with `tools/verify_display_object_fields.py`; machine-readable output is `evidence/display_object_fields.json`.

## Resolved dataflow

The worker begins at VA 0x04b30030. At 0x04b30050 it copies its second argument (`a1`) into `s3`, so every later `s3+offset` store in this function targets that same caller-supplied object.

The worker reads three adjacent configuration names and conditionally populates three adjacent object fields:

| Configuration input | Accepted condition in this worker | Object store |
|---|---:|---:|
| `RMRunFub` | read succeeds and value equals 1 | byte 1 at +0x328 |
| `RMFubUseCaseMask` | read succeeds, value is nonzero, value is below 0x2000 | word value at +0x32c |
| `RmDisableDisplay` | read succeeds and value equals 1 | word 1 at +0x334 |

This resolves the local meaning of +0x334: it is a cached or latched `RmDisableDisplay`-derived field in the worker's second argument. It is not merely an unrelated store near the name reference. The instruction evidence still does not recover the proprietary source-level field name or the class/type of the enclosing object.

## Wrapper and dispatch evidence

VA 0x04b301b8 is a wrapper that preserves the same two arguments, directly calls the worker, then invokes a function pointer loaded from offset +0x280 of the second argument. The wrapper address has one literal occurrence in the saved image, at file offset 0x33e90 inside the inner ELF read-only data section, amid other function addresses. This supports function-table dispatch, but it does not by itself identify the table's source-level class.

## Downstream consumer

A separate function at 0x04b20f54 receives the same-shaped object in `a1`. After two other byte prerequisites, 0x04b20f80 loads the word at `a1+0x334`. A zero field falls through and writes byte 1 to the caller-provided output; a nonzero field branches to a diagnostic path and writes byte 0. Therefore the cached field is not only populated: it actively vetoes a boolean capability/result exposed by this consumer.

The consumer is installed at function slot +0x158 in three explicit object-table construction paths (address constructors at 0x05571a18, 0x05571b28 and 0x05572800). If the first prerequisite is false, it calls a fallback through function slot `a0+0x1b0` and copies that return byte to the output. The other prerequisites are a byte at `*(a0+0x790)+0x88` and a byte at `a0+0x737`.

The +0x737 prerequisite now has a concrete writer. During an earlier initialization path, 0x04b72790 loads a function pointer from slot +0xb8 of the same object, calls it with that object as `a0`, and 0x04b7279c stores its returned byte at object offset +0x737. Therefore this prerequisite is a cached HAL/virtual-method result rather than a literal or direct read of `RmDisableDisplay`. The method identity and the +0x790 child pointer remain unresolved.

## Site A and concrete HAL predicates

The other `RmDisableDisplay` consumer at 0x04840310 now connects to the same structure. A successfully read value of 1 bypasses its normal indirect predicate and returns byte zero. Otherwise the normal path calls slot +0x1c8 of its second argument. If the configuration read fails, the choice also depends on object bytes +0x6dd, +0x737, +0x6d0 and +0x4f80. Thus site A is a second software gate, not merely an independent name lookup.

The recovered HAL-table constructor installs target 0x04b19ea4 at +0x1b0 and target 0x04b1a018 at +0x1c8. Both call an accessor from second-argument slot +0x108 with selector/offset 0x3814:

| HAL slot | Concrete target | Returned predicate |
|---|---:|---|
| +0x1b0 | 0x04b19ea4 | `(word & 0x000c0000) != 0` |
| +0x1c8 | 0x04b1a018 | `(word >> 27) & 1` |

Local historical prose calls 0x3814 `NV_FUSE_FEATURE_READOUT`, but the retained exact-tag NVIDIA headers do not define this selector or its bits. Therefore the raw selector and masks above are proved; their source-level field names and physical register aperture remain unknown. In particular, an archived host read returning a poison value at fuse offset 0x3814 cannot be substituted for the firmware accessor result.

The wider local source snapshot explains the origin of that historical label but does not close the TU106 gap. GA100 defines absolute `NV_FUSE_FEATURE_READOUT` at 0x00823814, while GB100 defines `NV_FUSE_ZB_FEATURE_READOUT` at selector 0x3814; both published headers name only bit 16 as `ECC_DRAM`. Neither header is TU106-applicable and neither defines bits 18:19 or 27. The firmware's +0x108 accessor is itself a trampoline through second-argument slot +0x320, so static code does not establish that selector 0x3814 is a direct BAR0 or host-visible fuse offset. Cross-generation names are therefore retained only as analogies.

The argument roles are strongly consistent with `a0` being a GPU-like object and `a1` being its HAL/configuration object: the latter owns `RMRunFub`, `RMFubUseCaseMask`, and `RmDisableDisplay` fields, while official 615.78.08 `OBJGPU` source exposes `pHal` and a `gpuFuseSupportsDisplay` HAL method. This is a source-correlated inference, not a recovered symbol: the proprietary firmware layout and current open-source NVOC layout cannot be equated by offset alone. In particular, the +0x1b0 fallback has not yet been proved to be `gpuFuseSupportsDisplay` on this exact image.

## Consequence and boundary

The firmware has a concrete software-policy latch driven by the value 1 for `RmDisableDisplay`; both recovered consumers can force a boolean result off, while the ordinary paths depend on additional cached state and two concrete 0x3814-derived HAL predicates. That does not prove the effective target value, that either function ran, that clearing the field enables an engine, or that PDISP/heads/SOR/PHY and board routes exist. Remaining static gaps are the +0xb8 producer, +0x790 child field, exact 0x3814 field definitions and source-level result names; the decisive runtime step remains a read-only capture of the effective registry and display capability responses.

Official source correlation: NVIDIA's exact-tag generated `OBJGPU` header declares `pHal` and `gpuFuseSupportsDisplay`, including GM107/TU-generation variants: <https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/generated/g_gpu_nvoc.h>. This supports the architectural hypothesis only; all claims about addresses and branches above come from the hashed local firmware.

## Follow-up: additional `+0x334` propagation sites

A bounded Capstone/RISC-V scan of the same firmware found additional direct accesses beyond the previously documented worker and `0x04b20f54` consumer. The strongest dataflow evidence is:

- `0x0460b600`: `lw a3,0x1ac(s2)` followed by `sw a3,0x334(s1)`. In the surrounding initialization/copy loop, adjacent fields `s2+0x19c`, `+0x1a0`, `+0x1a4` are copied to `s1+0x328`, `+0x32c`, `+0x330`, and pointer fields continue at `+0x338` onward. This is a structure-to-structure propagation of the `+0x334` slot; the source object's class name is not recovered.
- `0x04616fa4` followed by `0x04616fb4`: `lw a4,0x334(s2)` then `sw a4,0x168(s1)`. The surrounding routine copies a larger configuration record, including `s2+0x328` to `s1+0x15c`, `+0x32c` to `+0x160`, and pointer fields from `+0x338` onward. This identifies `+0x168` as a transported copy in that record, not as the original latch location.
- `0x0485ed5c`: `lbu a4,0x334(a1)` gates a larger operation before it reads `a1+0x344` and dispatches through `a1+0x120`; this is an additional byte-level veto/read site.
- `0x0487c338`: `lbu a5,0x334(s9)` is checked immediately after another policy byte and before the operation's dispatch path. This is another consumer of a propagated configuration object.
- `0x04894e70`/`0x04894e78`: a separate state counter at a derived object base increments `+0x334`; because the base is `s1+0x1000`, this is not proven to be the same object as the `RmDisableDisplay` worker's second argument and is recorded as an unresolved alias candidate only.

These sites strengthen the conclusion that `+0x334` participates in a broader copied configuration/state record. They do not identify the proprietary class names, prove runtime execution, or show that every `+0x334` access aliases the `RmDisableDisplay` latch.

## Copy-routine clarification

The routine beginning at `0x0460b548` has a generic record-copy shape: its prologue moves `a1` into `s1` and `a0` into `s2`, then copies source fields from `s2` into destination `s1`. The sequence at `0x0460b5b4`–`0x0460b600` copies a contiguous configuration block (`+0x188` through `+0x1ac` into destination `+0x314` through `+0x334`) and then copies pointer fields beginning at `+0x1b0` into destination `+0x338`. Therefore `0x0460b600` is best classified as a serializer/record-copy write, not an independent direct producer of the `RmDisableDisplay` value. The source object identity and the caller's semantic type remain unresolved.

Direct-call xref scanning found callers of the surrounding helper at `0x0460e924` and `0x04efefc4` for a related entry (`0x0460b20c`), but no statically encoded direct call to the copy body itself; function-pointer dispatch remains possible. This does not establish runtime reachability.

## `+0xb8` producer follow-up

The initialization routine containing `0x04b72790` starts at `0x04b72688` and keeps its main object in `s1`. At `0x04b72790` it loads a function pointer from `s1+0xb8`, passes `s1` as `a0`, and stores the returned byte at `s1+0x737` at `0x04b7279c`. The surrounding sequence calls several other virtual/function-pointer methods on the same object before and after this call, then consumes fields such as `+0x6dd`. Static inspection confirms this is an initialization-time cached virtual-method result, but no direct writer of the `+0xb8` slot or source-level method name is exposed in the retained symbols. The exact predicate represented by `+0x737` therefore remains unresolved.

## `+0x790` prerequisite clarification

At `0x04b20f68` the consumer loads a pointer from `a0+0x790` and then tests byte `+0x88` of that child at `0x04b20f70`. The child pointer is consumed directly and is not derived from `a1` (the configuration record carrying `+0x334`). Static evidence therefore separates this prerequisite from the `RmDisableDisplay` field: its child allocation/producer and semantic name remain unresolved.

## Function-table constructor check for `+0x790`

The recovered constructor paths at `0x05571918` and related shared code explicitly install the known callback slots (`+0x158`, `+0x1b0`, `+0x1c8`) but do not show a nearby `sd ...,+0x790` assignment. A firmware-wide raw store scan finds no `+0x790` store in those constructor windows. Therefore the `+0x790` child is likely populated by a separate base-object initializer or inherited/embedded object setup; its provenance cannot be tied to the recovered display callback table from static evidence alone.

## Offset-collision check for `+0x790`

A wider raw scan shows that `+0x790` is not globally one semantic field. For example, `0x0462ec60` loads a pointer from `s1+0x790` and then walks child-relative offsets, while `0x049852b4` stores a 32-bit bitmask to `t1+0x790`. These accesses use different object contexts and demonstrate why the `a0+0x790` child in `0x04b20f54` cannot be named from offset alone. The consumer-local interpretation remains: it loads a pointer and tests child byte `+0x88`; its producer is unresolved.

## Diagnostic-string boundary

The veto branch at `0x04b20fcc` forms a literal pointer with `lui 0x5995` plus `addi 0x528`. That resulting VA is outside the mapped inner-ELF sections recorded by the current firmware inventory, so the diagnostic string cannot be decoded from the retained mapped bytes without an additional relocation/container mapping. The branch is therefore documented as diagnostic/error handling only; no message text or semantic result name is inferred.
