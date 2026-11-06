# Phase 21 status report

Status: **IN_PROGRESS**. This report separates static firmware proof, historical saved runtime evidence, and missing current-target evidence.

## Static proof now established

- GSP 615.78.08 `RmDisableDisplay` lookup writes a value-derived latch at object offset `+0x334` in the recovered worker path.
- A downstream consumer at `0x04b20f54` reads `a1+0x334`; zero reaches output byte `1`, while nonzero reaches a diagnostic path and output byte `0`, after two other prerequisites.
- The `+0x737` prerequisite is cached by an initialization-time call through same-object slot `+0xb8`.
- The other prerequisite is consumer-local: pointer `a0+0x790`, then child byte `+0x88`; wider scans prove `+0x790` has offset collisions in unrelated object contexts.
- Additional `+0x334` accesses include record-copy propagation and unrelated-context candidates; they are not globally aliased by offset alone.
- Constructor paths install callbacks at `+0x158`, `+0x1b0`, and `+0x1c8`; the latter two predicates read selector `0x3814` and return the recovered bit tests. Exact field names remain unresolved.
- The diagnostic literal at `0x04b20fcc/0x04b20fd0` resolves to `0x05995528`, outside the currently mapped inner-ELF sections.

## Historical saved runtime evidence

The saved `nvidia-smi` query is timestamped `Tue Nov 3 08:30:53 2026` and identifies CMP 40HX, part `1F0B-100-A1`, BDF `00000000:03:00.0`, VBIOS `90.06.67.00.06`, GSP `615.78.08`, Display Attached `No`, Display Active `Disabled`. The saved BAR/resource readout has no timestamp or command metadata. These are historical inputs and are not current-state validation.

## Open requirements

- Fresh target read-only capture and effective registry/NVKV values.
- Runtime display capability/engine response and headless correctness tests.
- Exact proprietary class/result names, `+0xb8` slot writer/method identity, and selector `0x3814` source semantics.
- Revision-matched ROM and physical CG161P REV2 routing evidence.

All current static verifiers and provenance audits pass. No firmware patch, GPU write, reset, privileged operation, or exploit was performed.

## Fresh local environment check

A new bounded read-only collector run at `2026-11-04T12:23:24Z` found no local `10de:1f0b` device, no `/proc/driver/nvidia/version`, and no `nvidia-smi` executable. The result is saved as `evidence/local_inventory_2026-11-04.json` (SHA-256 `0eb199c375a01dc0965a196a1b8f2e3641efefc1f1c9944cbe19874fbfe8d14c`). This describes the local sandbox only and does not update the remote target state.
## Latest integrity audit (2026-11-04)

The complete static suite was rerun after the previous report: all Phase 21 Python tools compile, all evidence JSON files parse, and the display object, `+0x334`, `+0x790`, diagnostic-literal, and saved-runtime provenance verifiers pass. The firmware hash remains `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b`. This is an integrity result only; it does not add current-target runtime evidence.
The new bounded `+0xb8` inventory found 10,037 accesses across mapped sections, including stack/frame uses and unrelated object contexts. It confirms that offset-only scanning cannot recover the writer for the initialization object; `0x04b72790` remains the only established consumer-local load in that routine.
Exact-tag source recheck strengthens only the host-side result: 615.78.08 dispatch selects `gpuFuseSupportsDisplay_GM107` for TU106, while the retained local tree has no implementation body. The GSP accessor selector `0x3814` therefore remains semantically unresolved.
A provenance sweep found 11 retained copies of the saved BAR/resource display probe, all byte-identical. They represent one historical readout rather than independent observations; the files still lack timestamp and command metadata.
A fresh local read-only collector rerun at `2026-11-04T12:40:55Z` again found no `10de:1f0b` device, no NVIDIA proc driver, and no `nvidia-smi`. The rerun is saved as `evidence/local_inventory_2026-11-04_rerun.json`; it confirms the sandbox limitation and adds no target runtime evidence.
A cross-phase check also confirms that the older callback investigation does not resolve the proprietary method: the callback remains an indirect `*(context+0x30)` target with no in-window writer.
A unified evidence-layer matrix now ties the firmware, archived fuse, historical runtime and current-sandbox artifacts to their hashes and decision boundaries. It confirms that the remaining gap is specifically fresh target state and functional display validation, rather than missing static provenance.
The latest full integrity sweep passed all Python verifiers, all evidence JSON parsing, and the `IN_PROGRESS`/`complete=false` checkpoint invariant. This validates artifact consistency only; unresolved runtime and hardware requirements remain open.
