# Supplemental source packs — 2026-11-06 follow-up

**Purpose:** index and preserve seven historical tar archives, one handoff report, and two misnamed binary dumps received after the first repository export. All comparisons use **SHA-256 of actual file bytes**, not filenames. None of the archived scripts was executed.

## What was already included

- `cmp40hx_research_v15_final.tar.gz`: **157/157 members** already byte-identical to files indexed in the first project source ZIP. This is not a new 157-file research phase missing from the prior GitHub bundle.
- `cmp40hx_research_v14_final.tar.gz`: 137/138 files previously included; one alternate `MASTER_REPORT.md` differs byte-for-byte.
- `BAO_CAO_TONG_HOP_PHASE15_20.md`: already included (public version has redacted machine paths and internal IPs).
- `cmp40hx_t4.bin.txt` and `CMP40HX_ORIGINAL_1MB.bin.txt`: **actual binary VBIOS data**, not readable text. Both already existed by byte hash in the prior private archive. Public files show hashes, not raw bytes.

Across all seven tar archives, **36 unique content hashes not present in the original source manifest** were found: 10 Markdown reports, 13 original Python scripts, 13 JSON records. The public ZIP now includes these under `reports/additional/`, `scripts/additional/`, and `evidence/additional/`. A *second*, unmodified copy of every new unique file remains in the private archive, in addition to the original complete tarballs.

The attached packages are overlapping snapshots, not seven independent studies. See `manifests/SUPPLEMENTAL_SOURCE_INVENTORY.csv` for **all 497 tar entries plus 3 standalone uploads**, showing which canonical file represents each hash, including duplicate references.

## Historically useful extra material

- **VBIOS mapping and override:** the new Nov 3 report documents RAM-loaded VBIOS override experiments, VFE fields, checksum segmentation, PERF pointers and the 1 MB container's internal layout. Source: [Nov 3 report](../reports/additional/cmp40hx_3tasks/BAO_CAO_CMP40HX_03-11-2026.md).
- **Follow-up parsing corrections:** payload offset/stride corrections, live T4 testing, scripts for perf and VFE, and IBVL experiments. Source: [three-task report](../reports/additional/cmp40hx_3tasks/BAO_CAO_3_NHIEM_VU.md).
- **NV3/NV4:** additional source-referenced work on IBSN/IBVL, firmware descriptors, and GSP registry; preserves intermediate digest search output and assumptions. Source: [NV3/NV4 report](../reports/additional/cmp40hx_nv3_nv4/BAO_CAO_NV3_NV4.md).
- **Older master's ledger and hypothesis tracking:** v2/v3 snapshots document measurement provenance, top-1905-MHz hypotheses, coverage reports, and state from before later TPC5 and display-specific research. See [v2 evidence ledger](../reports/additional/cmp40hx_research_v2/EVIDENCE_LEDGER.md), [v2 hypothesis matrix](../reports/additional/cmp40hx_research_v2/HYPOTHESIS_MATRIX.md), [v14 alternate master](../reports/additional/cmp40hx_research_v14_final/MASTER_REPORT.md).

## Corrections and contradictions to read before using older scripts

| Topic | Conflict / interpretation | How to use the sources |
|---|---|---|
| VFE structure | The initial Nov 3 report describes a 24-byte VFE slot. The later `BAO_CAO_3_NHIEM_VU.md` explicitly reports a **25-byte** `VFE_VAR` stride and an earlier payload-offset error. | Keep the original claim for history; use the later correction for any tentative parser, but verify against source bytes and the script version. |
| IBSN / IBVL | The three-task report describes **15 blobs of 32 bytes** in its digest analysis, while the later NV3/NV4 report describes **12 candidate 32-byte digests** under another structural interpretation. | These counts **must not be conflated** as one confirmed list; preserve both offsets, scripts and definitions pending direct reproduction. |
| BAR3 redirection | Phase 15–18 claimed a GPU physical-address read/write redirection. Phase 19 readback directly **contradicted** the host primitive. | Cite [Phase 15–20 corrected synthesis](../reports/original/BAO_CAO_TONG_HOP_PHASE15_20.md); do not present BAR3 arbitrary GPU-PA access as proven. |
| `cmpunlocker` and clocks | Some snapshots report 1905 MHz after removing a module, but Phase 19–20 associates this with persistent state and distinguishes a low-clock stock capture. | Context and power/driver state matter. This is not proof of a universal 300 MHz hardware limit or universal 1905 MHz maximum. |
| SEC2 ROP | One Phase 15–20 handoff refers to a possible ROP chain. | **Do not present an unexecuted chain as a confirmed working exploit**; its own report says the firmware was not fully disassembled. |
| R1 `EN_SW_OVERRIDE` | `0x021040` accepted a direct BAR0 write but did not enable TPC5; its semantic identity was never established. | Current overall verdict remains [no confirmed TPC5 recovery](FINAL_VERDICT.md). |
| Security language | “3 critical vulnerabilities” in older notes largely means root-accessible features on an unlocked/test host. | Do not report CVEs or privilege escalation without an actual lower-privilege threat model. |

The **final TPC5/display outcome is unchanged** by these source packs. Their value is historical byte-exact provenance, raw VBIOS/GSP analytical context, reproducibility tools and documenting mistakes. No tool has been re-run and none of the archived claims was independently verified on a physical GPU in this packaging session.

## Publication boundaries

- The public bundle includes **script source and raw JSON as uploaded, with only minimal machine-identifier redaction**. Their behaviour is not audited or certified safe. Some scripts write MMIO or mutate GPU/driver state; do not execute without authorization, code review and a hardware recovery plan.
- The complete original tarballs, and the `.bin.txt` files containing actual VBIOS bytes, are **private-only**. The tarballs include NVIDIA firmware/GSP and other copyrighted/proprietary blobs.
- Automated secret search is incomplete by design; **manual review is required** before pushing the public archive to GitHub.
- The original SHA-256 hashes are listed in [package SHA inventory](../manifests/SUPPLEMENTAL_UPLOAD_HASHES.csv); canonical membership and any edits to public copies are recorded in [entry manifest](../manifests/SUPPLEMENTAL_SOURCE_INVENTORY.csv).

## Later V3 follow-up

The eight additional v6-v13 snapshots arrived after V2 and were processed in V3. The authoritative [V3 review](V3_HISTORICAL_SNAPSHOTS_REVIEW.md) and [V3 member inventory](../manifests/V3_HISTORICAL_SOURCE_INVENTORY.csv) cover them; they do not alter the original V2 source counts.
