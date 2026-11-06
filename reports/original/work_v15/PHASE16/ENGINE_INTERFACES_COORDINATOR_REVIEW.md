# Coordinator review — ENGINE_INTERFACES

Artifact location: `/home/REDACTED_USER/codex-work/PHASE16/ENGINE_INTERFACES/` (Hermes runner wrote this relative to workspace root). Reviewed its `report.md`, `findings.json`, and input manifest against current reviewed Phase16 evidence.

## Material conflicts: do not integrate the report's GPU-specific conclusions yet

- **Fuse +0x650:** report calls `0x0004001F` a TPC mask, says five enabled, and correlates it to TPC counts. `SECURITY_ARCH/audit_prior_claims.json` SEC-FUSE-05 explicitly rejected this semantic name because no TU106/TU102 source field exists. Current `FUSE_TU106_AUDIT` retains it UNKNOWN and rejects popcount-to-topology inference. Remove/retract the named mask and any “corroborated” count unless an exact TU106-applicable source definition and consumer are produced.
- **Fuse +0xC04/display:** report says raw fuse value 0 means display is “not masked.” `RAW_DATA/fuse2.json` and `FUSE_TU106_AUDIT/fuse_tu106_audit_report.json` show raw value **1**. The only found DISPLAY definition is Maxwell GM107 and not TU106-applicable; U-FUSE-009 remains OPEN/UNKNOWN. Do not infer display fuse state or causation.
- **BAR1 capacity:** report says BAR1 is 8 GiB. `MEMORY_PCIE` decoded endpoint BAR1 resource window and NVML BAR1 as **64 GiB**; VRAM total is separately 8 GiB. Reconcile the distinction and cite raw resource range.
- **Display “hardware absent”:** poison at sampled offsets/pages supports those reads being unavailable/poison in the archived aperture data. It does not establish the silicon block is physically absent or prove absence on every BAR0/PRAMIN path. Report only the exact sampled ranges/strides and preserve board/clock/decode/topology causes as UNKNOWN.
- **Topology:** GPC/TPC/SM/ROP mapping was previously UNKNOWN. The new report's “3 GPC, 17 TPC, 34 SM” must be traced to exact archived raw values and TU106-applicable field definitions; a reported `gpc_nr`/`tpc_nr` or `cudaGetDeviceProperties` summary alone is not enough to label register bitfields. Do not revive fuse-popcount inference.
- **PCIe evidence:** distinguish archived config/resource files and archived tool output from new hardware measurements. No new probe occurred for this job; don't describe historical writes as performed by this audit.

The source inventory and source-bounded register/control namespace survey are useful. Keep these separate from unsupported applicability, operational, or topology claims. No files in the original output directory were changed.
