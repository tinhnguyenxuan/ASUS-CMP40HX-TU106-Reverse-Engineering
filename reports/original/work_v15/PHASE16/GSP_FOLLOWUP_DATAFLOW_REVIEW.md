# Provisional dataflow code review

Current worker is live; do not edit its script or restart it. Inspected GSP_HEADER_CONSUMER_FOLLOWUP/header_consumer_followup.py lines300-395.

Three concrete issues require correction before accepting table accesses:
- mem_size maps lhu to1 byte; unsigned halfword load is2 bytes.
- step_sym handles store using f[rd], but RISC-V stores have no destination register; bits11:7 are immediate bits. This can clobber an unrelated symbolic register. Also store address uses S immediate, not load's I immediate.
- The loop calls step_sym before recovering memory base. If load destination equals base register, its old address value is already lost. Capture operands from pre-instruction state, then transfer state.

Further review needed: call ABI clobbers, compressed-instruction transfer handling, join monotonicity/convergence, sign extension/truncation and loop widening. Current run.log reaches CFG fixed point, then enters symbolic dataflow; that does not prove dataflow has converged. Retain raw CFG evidence separately; table-access semantics unaccepted pending corrected final analysis.

## Observed non-convergence diagnostic

Latest run.log reports pops50000..650000 with work=1 and processed=381; preceding re-add event reports changed=[] for block0x459cb28. This is concrete evidence that empty/no-change rescheduling or nonmonotone join may prevent termination. Review queue scheduling against abstract-state equality, treating absent vs unknown consistently, and require a finite lattice/widening plus explicit bounded-analysis status. Worker remains live; no restart initiated.

## Worker revision observed

Current script replaces interblock worklist with within-block single pass. Termination improves, but this reduces dataflow scope. Every block is seeded s9=TABLE_BASE and s10=24 without demonstrated dominance/call-preservation; some blocks may belong to other function paths. lhu width and pre-state load/store defects persist. Require corrected transfer semantics and justified reaching definitions; do not interpret fewer recovered accesses as evidence fields are never used.

## Revised run observations

run.log now reports table accesses0, despite known flags loads in the verified candidate. Thus within-block analysis currently fails to recover known positive accesses;0 is not negative evidence. Internal table dump reports496 records/495nonzero/1zero at0x4584790. Keep this distinct from external NVUCODES archive496slots/38external; same record stride alone does not establish identical contents/storage state. cfg.json was emitted, extended_disasm.txt only2119B at observation; serialization/final completion still pending.

Serialization defect: extended_disasm.txt ends at0x459c644, immediately before unresolved jalr at0x459c648. Serializer calls va_to_file(tgt) unguarded for call_indirect; tgt=None. seg_for compares integer<=None, causing TypeError. Guard unresolved targets before mapping/formatting; serialize explicit null plus unresolved label. Validate complete output coverage against CFG instruction count. This is a static code-path diagnosis, not a new successful run.
