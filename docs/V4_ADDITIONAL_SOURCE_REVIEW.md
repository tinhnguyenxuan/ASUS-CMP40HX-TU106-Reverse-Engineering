# V4 supplemental source audit: early v4 and v5 snapshots

**Scope:** Seven newly uploaded `.tar.gz` research archives. No source scripts were executed, no hardware accessed, and no new GPU-unlock claim has been experimentally verified by this packaging process.

## SHA-256 reconciliation

- Seven archives contain **618 regular-file occurrences**.
- **605 occurrences** already match exact raw source hashes recorded in V1–V3.
- **2 occurrences** are duplicates of new files elsewhere in this batch.
- **11 new unique original-byte files**: **2 Markdown**, **4 Python scripts**, **5 JSON files**.
- The **11 new files are from versions v4 and v5 only**. The v2 / v3 copies and v6 / v7 / original reuploads introduce no new source content.
- The seven whole original tarballs are preserved **byte-for-byte in the private archive**, even when source contents already exist elsewhere. Nothing with a colliding filename is overwritten.

The complete [V4 member inventory](../manifests/V4_SOURCE_INVENTORY.csv) contains all 618 records, including original SHA-256, status, new paths and privacy transformations. [Archive checksum list](../manifests/V4_UPLOAD_ARCHIVES_SHA256.csv) covers all seven original tarballs.

## What is new?

The main historical additions are the [v4 GSP Q1 consumer report](../reports/additional/cmp40hx_research_v4/GSP/Q1_CONSUMER.md), [v4 master report](../reports/additional/cmp40hx_research_v4/MASTER_REPORT.md), `TOOLS/build_db.py` for v4 and v5, `TOOLS/verify_all.py` for v4 and v5, plus early checkpoint / coverage / unknown-database JSON versions. These document the evolution of the research rather than prove a working TPC5 or display unlock.

The master report's claimed **55/55 PASS** is an author-reported historical self-test, not a test that was rerun here. Similarly, the v4 report's conclusions must be interpreted in light of subsequent corrections and negative live TPC5 testing. See [final verdict](FINAL_VERDICT.md), [failed approaches](KNOWN_FAILED_APPROACHES.md), and [critical corrections](CRITICAL_CORRECTIONS.md).

**Important:** public source text is curated, but not guaranteed legally or operationally safe to publish or run. Some historical scripts may access firmware, system devices, driver interfaces or MMIO when executed; they are retained as research evidence, not endorsed ready-to-run tools. A separate private archive preserves original bytes, potentially restricted binary blobs and historical device metadata. Do not publish the private archive itself.
