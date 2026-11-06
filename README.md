# NVIDIA CMP 40HX / TU106-100-A1 — Reverse Engineering Evidence

**Community research archive · November 2026 · No confirmed SM or display unlock**

This repository preserves technical reports, original research scripts and selected raw evidence from a multi-phase investigation of the NVIDIA **CMP 40HX (TU106-100-A1, PCI ID `10DE:1F0B`)**. It is intended to save future researchers the time spent repeating unproductive experiments. **A successful recovery of the disabled GPC0/TPC5, or a native physical display output, has NOT been demonstrated.**

> **Start here:** [Final verdict](docs/FINAL_VERDICT.md) · [Evidence matrix](docs/EVIDENCE_MATRIX.md) · [Corrections and false leads](docs/CRITICAL_CORRECTIONS.md) · [How to reproduce safely](docs/REPRODUCIBILITY.md) · [Vietnamese README](README.vi.md)

## The two original goals

**1. Recover 128 CUDA cores / 2 SM.** This card exposes **17 TPC / 34 SM / 2,176 CUDA cores**, compared with 18 TPC / 36 SM / 2,304 CUDA cores for the full TU106 configuration. The active mask of physical GPC0 was reported as `0x1F`, while GPC1 and GPC2 reported `0x3F`. BAR0 `0x021C38 = 0x20` indicates bit 5 disabled in the effective TPC fuse/status view; the hardware GR count at `0x502608` stayed at 5 TPC. The inaccessible TPC5 returned `0xBADF1300` (`FECS_PRI_FLOORSWEEP`). These observations do **not** prove that its silicon is functional or that a safe override exists.

**2. Restore physical display output.** The project records `STATUS_OPT_DISPLAY` at BAR0 `0x021C04 = 1`, related RM source paths, a VBIOS `NO_DISPLAY_SUBSYSTEM` flag, and DCB observations. No reproducible native video output from the CMP 40HX has been demonstrated. Games or headless GPU workloads working via another adapter are **not** evidence of display-engine restoration.

## The final live TPC5 experiment

The November 6 write experiment reports that an authorized root operator could write BAR0, and the candidate address `0x021040` read back as 1 after writing 1. However, an attempted write of bit 5 to `0x021838` immediately read back as 0; `0x021C38` remained `0x20` and the GR topology stayed at 5 TPC. The tested sequence **did not restore TPC5**. This does not establish that every possible host/firmware/boot-time route has been ruled out, nor that `0x021040` is definitely `EN_SW_OVERRIDE` on TU106.

The original write-test report is preserved as a **historical first-party report**, not adopted verbatim as a security finding: [TPC5 live experiment](reports/original/ok/results/TPC5_LIVE/EXPLOIT_LIVE_20261106.md). It labels root loading an unsigned module a "critical vulnerability"; this is better interpreted as an explicitly permitted privileged operation on the documented host configuration, **not an unprivileged privilege-escalation exploit**.

## Navigation

| Read this | Purpose |
|---|---|
| [Final verdict](docs/FINAL_VERDICT.md) | What is known and still unknown |
| [Evidence matrix](docs/EVIDENCE_MATRIX.md) | Values, addresses, source paths, confidence |
| [Critical corrections](docs/CRITICAL_CORRECTIONS.md) | Mistakes found across phases, retained rather than hidden |
| [Failed approaches](docs/KNOWN_FAILED_APPROACHES.md) | Tested routes that did not work |
| [Research timeline](docs/RESEARCH_TIMELINE.md) | How different phases relate |
| [Raw reports](reports/original/) | Preserved source markdown, including historical versions |
| [Original scripts](scripts/original/) | Original Python / shell / C code: **not automatically run or audited** |
| [Raw evidence](evidence/original/) | Selected logs, disassembly excerpts, JSON and CSV |
| [Complete source manifest](manifests/SOURCE_INVENTORY.csv) | Every file in the original ZIP, including missing / private-only items |
| [Publication audit](docs/PUBLICATION_AND_SECURITY.md) | What was excluded and why |

## Archive policy

The **GitHub ZIP** includes every eligible unique text report and script that passed automated publication checks, plus many small-to-medium raw evidence files. Byte-identical duplicates are represented once, with an explicit source-to-canonical map in the manifest. Original file paths after the `codex-work/` prefix remain embedded in the new category paths. Paths, private-network IPs and device UUIDs were automatically redacted in published copies where detected; the manifest records redaction types. **Original bytes remain unchanged in the separate COMPLETE RESEARCH ARCHIVE**, which is **private by default** and should not be pushed blindly to GitHub.

Firmware blobs, VBIOS dumps, third-party source snapshots, boardview CAD, photographs, very large generated machine JSON and full disassembly corpora are excluded from the public ZIP by default pending rights/privacy review. Their names and SHA-256 checksums remain in the inventory. This preserves provenance without silently publishing copyrighted or identifiable material.

## Important safety notice

Some archived scripts interact with BAR/MMIO, kernel modules, driver IOCTLs, firmware or hardware. **They are evidence, not supported one-click utilities. Do not run them without code review, suitable hardware, backups and a recovery plan.** No archived research script was executed during packaging. Never blindly attempt register writes or irreversible fuse/RIR operations.

See [references](docs/REFERENCES.md) for externally maintained context. No license is granted over third-party code or proprietary firmware by inclusion in the private archive. Research scripts require an explicit permission/licensing decision by their author before redistribution.

## Follow-up historical source packs (V2)

**Ten newly supplied files were reviewed (seven tar snapshots plus a handoff and two misnamed binaries).** The 157-file v15 tar was already represented in V1; only **36 SHA-256-new textual items** were added. Read [V2 supplemental review](docs/SOURCE_PACK_REVIEW_20261106.md), [Vietnamese explanation](docs/SOURCE_PACK_REVIEW_20261106.vi.md), and [supplemental inventory](manifests/SUPPLEMENTAL_SOURCE_INVENTORY.csv). The original tarballs are preserved in the **private** archive, not committed to GitHub.

## V3: historical v6-v13 snapshots

Added **43 distinct historic source files** from 8 more tarball snapshots, with all 1,035 member occurrences indexed by SHA-256. Start with [V3 review](docs/V3_HISTORICAL_SNAPSHOTS_REVIEW.md) or [Vietnamese V3 review](docs/V3_HISTORICAL_SNAPSHOTS_REVIEW.vi.md). Individual card serial/PDI identifiers were scrubbed from public copies, but raw versions are available only in the private archive. **V3 remains a manual-review candidate, not an independently verified release.**

## V4: early v4-v5 source snapshots

Added **11 distinct early report, script and JSON revisions** from 7 additional tarballs. See [V4 source review](docs/V4_ADDITIONAL_SOURCE_REVIEW.md), [Vietnamese review](docs/V4_ADDITIONAL_SOURCE_REVIEW.vi.md), and [member manifest](manifests/V4_SOURCE_INVENTORY.csv). All original tarballs are preserved in the **private companion archive**; do not publish that private archive.
