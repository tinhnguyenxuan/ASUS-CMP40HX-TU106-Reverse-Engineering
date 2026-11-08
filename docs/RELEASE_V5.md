# V5 — Curated TU106 VBIOS Phase 4–6 addition

Merged the **static VBIOS / firmware / driver research** portion of the user-supplied `vbiosrel6(2).zip` into the V4 public repository under `research/vbios_phase4_6/`, plus a consolidated [Vietnamese report](TU106_VBIOS_PHASE4_6.md).

Included: 11 curated research Markdown files, a new Phase 6 LPWR/PCIe index-chain note, three static CSV datasets (one filtered evidence worksheet), five read-only Python ROM tools/tests, and an input-source SHA-256 manifest. Source-local developer paths were converted to a configurable `CMP_ROM_DIR`/`./roms` default. The original source ZIP is not embedded.

**Explicitly excluded:** collectors (PowerShell/bash), host probes, Tensor/RT/game benchmarks, PresentMon/WPR logs, Windows instructions, practical gaming-test plans, runtime measurement matrices, ROM/VBIOS blobs, device data and executable binaries. Existing historical V4 archive contents were left intact; no past evidence was silently deleted.

The reports are historical author claims, not independent verification. Parser regression tests need ROMs legitimately supplied by the reader; no ROMs are shipped. The public package requires a final human privacy, copyright and security review before publication.
