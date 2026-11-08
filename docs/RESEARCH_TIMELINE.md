# Research timeline and reading order

This multi-author/multi-agent project includes overlapping subprojects, not one perfectly linear chain.

- **Early phases / v15–v20:** VBIOS, SEC2, MMIO/PCIe BARs, GSP, memory and security. Later reports explicitly retract some early Phase 15–18 claims (especially BAR3 redirection and security classifications). Source: [phase 15–20 handoff](../reports/original/BAO_CAO_TONG_HOP_PHASE15_20.md).
- **T00–T09:** Boardview, strap, PCI class, fuse values, VBIOS/DISPLAY, effective masks, GSP callback analysis and corrections. Begin with [raw phase index](../reports/original/ok/results/00_INDEX.md).
- **D1–D3:** Display RM, VBIOS, hardware and GSP object provenance. Read D3 after D1/D2 because it corrects several earlier identifications. [D3 verdict](../reports/original/ok/results/DISPLAY_D3/D3_FINAL_VERDICT.md).
- **TPC5 + T6–T8:** Effective 17 TPC/34 SM topology, FECS floorsweep responses and GSP dispatch analysis. T8 contains superseded interpretation; read [corrections](CRITICAL_CORRECTIONS.md).
- **November 5–6:** Independent TU106 topology measurements in some captures with driver `615.71.09` and other records with `615.78.08`; do not silently merge build-specific results. [Independent report](../reports/original/PHASE_TU106_FLOORSWEEP_INDEPENDENT/BAO_CAO_MOI_TPC_CMP40HX.md).
- **R1:** Candidate register/source audit, followed by a correction removing the unsupported `EN_SW_OVERRIDE` identity conclusion. [Register identity audit](../reports/original/ok/results/TPC5_R1/TPC5_OVERRIDE_REGISTER_IDENTITY.md).
- **November 6 live write experiment:** Read/write privilege and candidate override register write attempted without TPC5 recovery. [Original report](../reports/original/ok/results/TPC5_LIVE/EXPLOIT_LIVE_20261106.md).
- **Phase21:** Additional display, headless rendering and source-provenance work, including corrections to historical-vs-current target assumptions. [Reconciliation](../reports/original/PHASE21_FUNCTIONAL_RESEARCH/RUNTIME_RECONCILIATION_20261106.md).

All dates are as recorded in the supplied archive; no fresh hardware experiment was executed while preparing this release.

- **Nov 6 supplemental historic snapshots:** seven additional source tar archives dating to early Nov 2026. Earlier parsing/count claims are superseded or contested in follow-up reports; [V2 review](SOURCE_PACK_REVIEW_20261106.md) documents these without treating them as new live tests.

- **Nov 7 V3 historical supplementation:** source snapshots v6-v13 from early Nov 2026; 43 additional source versions with 1,035 manifest entries. Historical revisions only; see [V3 audit](V3_HISTORICAL_SNAPSHOTS_REVIEW.md).

- **2026-11-07 source curation V4:** seven additional older archives; 11 unique historical source revisions from v4/v5, no new hardware testing. See [V4 review](V4_ADDITIONAL_SOURCE_REVIEW.md).

- **2026-11-08, GitHub V5 integration:** independent Phase 4–6 TU106 VBIOS static analyses curated from `vbiosrel6(2).zip`. This is another *overlapping* research thread, not a post-V4 hardware experiment. [VBIOS Phase 4–6 report](TU106_VBIOS_PHASE4_6.md).

- **2026-11-08, V5 supplement (historical Phase 1–5):** previously omitted TU106 VBIOS field-reverse snapshots from `vbiosre`, `vbiosrel2`, `vbiosrel3`, and curated master report extracts from `vbiosrel4/5`. These are historical source revisions; later phases may correct earlier interpretation. [Reading order and corrections](TU106_VBIOS_PHASE1_5_HISTORY.md). No additional hardware measurements.
