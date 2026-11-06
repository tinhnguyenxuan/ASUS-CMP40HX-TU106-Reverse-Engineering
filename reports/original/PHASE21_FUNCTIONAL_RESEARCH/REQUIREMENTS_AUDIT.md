# Latest evidence boundary — 2026-11-06

This update supersedes historical missing-runtime statements below: retained target captures prove bounded FP32, WMMA, cuBLAS SGEMM and EGL/OpenGL ES shader pixel correctness on BDF0000:03:00.0 with driver/GSP615.71.09. CUPTI metadata discovery alone passed, not profiling counters. A2026-11-05 RM capture reports instruction speed-select pairs; it is cached API output, not raw OTP. Reconciliation, source hashes and unresolved limits are in RUNTIME_RECONCILIATION_20261106.md and CUDA_RUNTIME_RESULTS.json. Fresh execution in the current sandbox remains unavailable. The original scope remains incomplete.

New PCB photographs and a reference-board report exist under CMP40HX_INDEPENDENT_REVIEW; these still need independent image/netlist authentication and exact-board correspondence before closing routing requirements. Earlier statements that no material exists describe the older inventory, not current filesystem presence.

# Scope audit — objective remains incomplete

This audit is against prompt.txt, not against artifact presence. No row is marked complete merely because a file exists.

| Prompt area | Evidence now available | Unfinished requirement and next evidence |
|---|---|---|
| 1 CUDA capability | Public research lead; local missing-device result | Fresh target enumeration and correctness/library/profiling results. Public findings permit deferring redundant benchmarking, not asserting current target state. |
| 2 Compute restriction | Hashed third-party patch; selector constants and Booter predicate | Exact selector bit mapping, original initializer, matched FECS/GPCCS/SEC2 consumers and raw Phase19/20 traces. State-changing exploit execution requires approved proposal under sections 2/9. |
| 3 Display | Direct DCB/CCB/connector decode; official host preinit gate and TU106 dispatch | Current gate inputs/results, GSP backend dataflow, heads/SOR/PHY/clock discovery, package/PCB evidence. |
| 4 Headless rendering | Safe BDF-bound inventory collector | Actual EGL/OpenGL/Vulkan image correctness, CUDA/GL interoperability, KMS CRTC enumeration on target. |
| 5 Fuse | Saved raw subset with hashes; archived display predicate evaluation | Physical-vs-shadow origin, more function masks, trusted revision-matched reference dumps, full TU106 consumer semantics. |
| 6 Cross-SKU VBIOS | Original vs local derivative display tables | Genuine independent GeForce/Tesla TU106 ROM with provenance; devinit/display loading paths and structured full comparison. |
| 7 GSP gates | Official host source decisions; GSP 615.78.08 identity and string leads | Name lookup consumer recovery, branch inputs, RPC backend, exact firmware functions/CFG and target statuses. |
| 8 Feasibility | All named functions have evidence-limited matrix rows | Current vs stock evidence and justified restoration classification per function. UNKNOWN rows remain unresolved, not completed findings. |
| 9 Safety/reproducibility | Offline scripts and saved input hashes; bounded query collector | Repeatable target capture and firmware/board-state provenance. No changed-state experiment is currently specified or authorized. |
| 10 Deliverables | All 14 named files plus evidence/tools/plan | Their existence does not fulfill unfinished research above. Checkpoint retains IN_PROGRESS. |

Current limiting inputs: restricted SSH socket creation; fresh target logs unavailable; raw Phase19/20 files not retrieved; independent reference ROM and PCB material absent. Offline source/dataflow work remains possible, so the goal is not at an overall impasse.

Follow-up evidence for area 7: system-info registry ingestion now has matched official key definitions, raw-verified firmware dispatch/setters, concrete NVKV callback reachability, and an official host producer through `GSP_INIT` (GSP_SYSTEM_INFO_INGESTION.md, GSP_NVKV_CALLBACK.md, HOST_REGISTRY_PRODUCER.md). Effective target configuration, the fallback provider, display object identity and physical capability remain open.

Additional area-7 progress: the system-info handler is now connected through a concrete NVKV callback and packet payload wrapper, including descriptor semantics and status consumption. This is bounded static proof; host payloads, runtime reachability and capability restoration remain unverified.

Host-producer follow-up: official 615.78.08 source now connects global and per-device registry entries, in that order, to the system-info NVKV stream and `GSP_INIT` command 0x10001. Archived textual inputs contain no explicit RmDisableDisplay key. Effective live registry values, the read fallback, display object identity and hardware capability remain open.

Object-field follow-up: the site-B worker's second argument is now traced to adjacent cached configuration fields. A successful value of 1 for `RmDisableDisplay` conditionally stores word 1 at +0x334; neighboring fields are populated from `RMRunFub` and `RMFubUseCaseMask`. A separate consumer returns boolean 0 when +0x334 is nonzero after two other prerequisites. The source-level class/result, execution on the target and effective value remain open, so this does not satisfy display-silicon or functional-display requirements.

## Audit update (E21-017)

The GSP display-gate row now has stronger bounded static evidence: the `RmDisableDisplay` worker field flow, downstream boolean veto, `+0xb8` cached virtual-method result, `+0x790` consumer-local child-pointer test, record-copy classification, diagnostic-literal mapping boundary, and hash-checked scanners are documented. These facts improve area 7 and reproducibility, but do not close runtime target state, exact proprietary names, selector semantics, physical display capability, or functional display/headless requirements.

Saved runtime artifacts were separately provenance-audited. The timestamped `nvidia-smi` text and untimestamped resource readout remain historical inputs; neither is treated as a fresh target capture.
## Target-capture execution package

`TARGET_CAPTURE_CHECKLIST.md` now maps each unresolved requirement to a bounded read-only command set and acceptance metadata. It is a collection procedure, not runtime evidence; current rows remain open until the target package exists.
The machine-readable companion `evidence/requirement_matrix.json` currently has 10 rows; five remain unresolved because they require current target or independent hardware evidence.
ROM inventory follow-up: 27 retained 1MiB-class files reduce to 16 unique hashes, but none has authenticated source metadata; tuning/patch filenames prevent treating them as independent reference ROMs. Cross-SKU requirement remains open.
ROM byte-distance follow-up confirms retained variants are small-delta tuning/patch artifacts or truncated copies relative to the saved original; this still does not satisfy the independent reference-ROM requirement.
Raw-data inventory follow-up found 54 retained files but only five unique hashes, all repeated checkpoint copies. No additional independent Phase19/20 capture with stronger provenance was recovered.
`evidence/blocker_register.json` now records the five unresolved requirements and the exact evidence needed to close each one. All five remain OPEN because current-target or authenticated hardware evidence is absent.
