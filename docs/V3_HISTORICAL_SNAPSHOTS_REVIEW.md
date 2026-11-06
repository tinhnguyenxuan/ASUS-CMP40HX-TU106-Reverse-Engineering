# Historical snapshot pack review — versions v6 through v13

**Date:** 2026-11-07. **Scope:** Eight user-provided tar.gz archives from older CMP 40HX research snapshots. **No bundled scripts executed. No GPU access or MMIO writes performed during packaging.**

## Byte-level result

- **8 archives, 1,035 regular-file occurrences**.
- **977 entries** already represented by an identical original SHA-256 in V1/V2.
- **15 entries** duplicate new material elsewhere in this eight-pack upload batch.
- **43 genuinely new content hashes:** 16 Markdown reports, 8 scripts, 19 JSON/evidence objects. These original text items are now in the public package with identifier scrubbing; exact original bytes are retained in the private companion archive.
- All **8 tar.gz files themselves** are preserved byte-for-byte in the private archive. Multiple snapshots legitimately have the same filenames but different contents; none is overwritten.

Use [V3 file-by-file map](../manifests/V3_HISTORICAL_SOURCE_INVENTORY.csv) for every entry (original hash and canonical public path), and [V3 package hashes](../manifests/V3_HISTORICAL_UPLOAD_HASHES.csv) to check original tarballs. The package filenames are not independent discoveries; most data is shared across snapshots.

## Why keep the 43 historical versions?

The repeated `MASTER_REPORT.md`, `CHECKPOINT.json`, `TOOLS/verify_all.py`, `COVERAGE.md`, `UNKNOWN_DATABASE.json`, and `DISCOVERIES.json` preserve the evolution of assumptions, supporting experiments, and self-check coverage. These are **dated historic versions**, not new hardware tests or a validated way to unlock TU106 GPC0/TPC5.

Notable additions:

- [v6 master report](../reports/additional/cmp40hx_research_v6/MASTER_REPORT.md) and [v13 master report](../reports/additional/cmp40hx_research_v13_final/MASTER_REPORT.md) bookend the evolving cross-phase conclusions.
- [v7 security architecture](../reports/additional/cmp40hx_research_v7_final/SECURITY/security_architecture.md), [v7 trust boundaries](../reports/additional/cmp40hx_research_v7_final/SECURITY/trust_boundaries.md), and revised [v11 security architecture](../reports/additional/cmp40hx_research_v11_final/SECURITY/security_architecture.md) record WPR, FWSEC, SEC2 and the privileged host/driver boundary.
- [v13 verification script](../scripts/additional/cmp40hx_research_v13_final/TOOLS/verify_all.py) is kept as **historical source**; its `155/155 PASS` claim in source is **not independently executed or validated by this packaging process**, and the script may require a complete original snapshot directory with binary data.
- [v8 discovery log](../evidence/additional/cmp40hx_research_v8_final/DISCOVERIES.json) and the [v13 checkpoint](../evidence/additional/cmp40hx_research_v13_final/CHECKPOINT.json) help reconstruct chronology.

## Evidence interpretation and corrections

Treat snapshot conclusions as *claims made at that time*, not final verified facts. Later work in the baseline repository **rejected host BAR3 arbitrary-GPU-PA redirection**, corrected some display/BIT and GSP/floorsweep inferences, and produced a **negative live TPC5 experiment** with register writes that did not restore GR topology. New v6–v13 snapshots **do not supersede** [final verdict](FINAL_VERDICT.md) or [corrections](CRITICAL_CORRECTIONS.md).

The 2026-11-03 v13 master report includes unique per-card serial/PDI values and internal lab network addresses. The *public* text has been scrubbed; **original unredacted bytes are intentionally preserved in private storage only**. In addition, earlier public V2 documents with the same per-card IDs were scrubbed in V3. When reproducing an experiment, recover your own device IDs; zeroed PDI values are **redaction placeholders, not measured zeros**.

**Publishing warning:** the public scripts are archived for independent source review, **not audited for safe execution**. Some historical scripts may write GPU registers or modify low-level state; do not run without code review and a tested recovery method. The private archive contains firmware and binary VBIOS data; do not upload it publicly without an appropriate rights/security review. Automated scrubbing cannot certify the repository safe for release: perform manual review before pushing to GitHub.
