# Critical corrections / superseded claims

This is essential reading before treating older files as conclusions. We deliberately **retain** superseded reports to preserve traceability.

1. **GSP T8 bitmap provenance:** the `+0x3E0` bitmap enumerated by helper `0x04C853B4`, including dataflow that wrote `physGpcMask` at struct offset `+0x204`, was wrongly called the "single source of truth" for `tpcMask[]`. Struct offset `+0x204` is **physGpcMask**, not `tpcMask[0]`. Slot `+0x130` is called with an output pointer to `tpcMask[0]`, but its concrete function target was not determined. Slot `+0x200` was mislabelled a TPC index though the observed output field is GPC-related. See historical [T8](../reports/original/ok/results/T8/T8_VERDICT.md) and corrective [R1](../reports/original/ok/results/TPC5_R1/TPC_MASK_SOURCE.md). **Do not re-use T8's "single source" claim.**

2. **R1's hard gate at `0x021040`:** R1 called it `FUSE_EN_SW_OVERRIDE` and concluded that its zero value definitively closed the path. Its **register identity was never validated for TU106**. Subsequent live experiments found it accepts a write to 1, but *writeability is not register identity*. Similarly, `0x021A40–0x021ABC` being a zero-filled aperture does not validate the inferred `RECONFIG_OVERRIDE` label. See [R1 register audit](../reports/original/ok/results/TPC5_R1/TPC5_OVERRIDE_REGISTER_IDENTITY.md) and [live test](../reports/original/ok/results/TPC5_LIVE/EXPLOIT_LIVE_20261106.md).

3. **Ampere-to-Turing address mapping:** matching a few `STATUS_OPT` registers via `Ampere_address − 0x7FF000` does not establish a mapping for unrelated fuse banks. Another candidate used `−0x800000`. Both need independent TU106 evidence; identical zeros and poison patterns alone are inadequate.

4. **GSP grep zero hits:** scanning disassembly for the literal `0x021C38` or `0x021A40` does not prove that GSP never reads a fuse. Register addresses may be assembled, table-driven or accessed indirectly. **No literal hit ≠ proof of absence**.

5. **`+0x6EA` as display gate:** D1/D2 writer/read subsets had object identity collisions; D3 resolved that a simple offset match was not enough. Do not identify display state solely from `+0x6EA`. See [D3](../reports/original/ok/results/DISPLAY_D3/D3_FINAL_VERDICT.md).

6. **PCI BAR3 GPU PA arbitrary read/write:** early Phase 15–18 claimed BAR3 redirection; Phase 19–20 testing contradicted it. See [phase 15–20 reconciliation](../reports/original/BAO_CAO_TONG_HOP_PHASE15_20.md).

7. **"Three CRITICAL vulnerabilities" from root execution:** the final original `TPC5_LIVE` report uses this phrase. The described scenario already requires authorized root on a host configured with unsigned modules permitted, Secure Boot off and no lockdown. That confirms **powerful privileges by configuration**, not a demonstrated unprivileged privilege escalation. BAR0 access also does not prove a driver vulnerability. Keep the observations; do not copy its CVSS-style conclusions without a separate threat model.

8. **"Hardware latch confirmed / no host software path":** `0x021838` bouncing in one test, while GR topology stays unchanged, is meaningful negative experimental evidence. It does **not** prove a unique hardware latch mechanism or rule out all boot-time, firmware or privileged software mechanisms. The supported statement is **this tested sequence failed**.

9. **`0x0210D4..0x0210F4` "writable fuses":** the live report explicitly corrects an early misreading. Disparate write values led to a common readback side effect, and reboot restored 9/9 readouts. These are **not verified writable fuse fields**. Do not reproduce blind writes. See [live test](../reports/original/ok/results/TPC5_LIVE/EXPLOIT_LIVE_20261106.md).

10. **Mixing snapshots:** Phase21 and TU106 independent captures include differences in driver/GSP versions, dates and availability of a remote GPU. Keep their capture provenance; the sandbox lacking a GPU on one day did not mean the remote target lacked one.

The raw files are preserved even when a finding is retracted. New readers should always cite the latest supported *evidence*, not the strongest language found in an old report.

11. **VFE parsing and IBSN/IBVL revision history:** the early Nov 3 report and later three-task audit use different byte-stride/payload offsets. The three-task and NV3/NV4 reports also report different counts of candidate 32-byte digest/blob data. These are not interchangeable facts; compare scripts, offsets, and definitions before reusing derived output. See [V2 supplemental review](SOURCE_PACK_REVIEW_20261106.md).

12. **Renamed binary `*.bin.txt` is still binary:** the two standalone sources include byte-level VBIOS data. Do not treat them as harmless text eligible for public source publication.

13. **V6-v13 self-checks and security claims are historical source assertions.** Statements like `155/155 PASS` are not reexecuted or independently verified during packaging. Security/lockdown/driver and BAR3 claims require specific experimental provenance; later corrections supersede the older conclusions. See [V3 audit](V3_HISTORICAL_SNAPSHOTS_REVIEW.md).
14. **Device fingerprinting in V2 public:** the V2 publication candidate contained per-card serial and PDI values. V3 masks known values in public text and regenerates public hashes, while preserving original raw text in the private archive. Zero PDI in public is an intentional placeholder.

15. **V4/V5 historical self-check results:** `55/55 PASS` and GSP Q1 consumer claims are statements in old research sources, not retested or proven by this archive-curation step. Later TPC5, BAR3 and callback corrections still apply; consult [V4 review](V4_ADDITIONAL_SOURCE_REVIEW.md).
