# Coordinator review — SECURITY_ARCH

Reviewed `REPORT.md`, all structured JSON outputs, `run_log.md`, `assertions.log`, and the current evidence ledger.

## Blocking correction required before reuse

- **WPR2 size/address calculation is wrong.** The report and `audit_prior_claims.json` subtract raw register encodings `0x01FFEE00 - 0x01F7E000 = 0x80E00` and call the result 515.5 KiB / 0.50 MiB. The source field is `VAL[31:4]` in 4 KiB units, so the decoded byte address is `(raw & 0xFFFFFFF0) << 8`, not the raw value. Correct exclusive range is `[0x1F7E00000, 0x1FFEE0000)`, size `0x80E0000 = 135,135,232 B = 128.875 MiB`. The raw pair may corroborate the archived boot log, but does not corroborate the report's size calculation. This agrees with accepted `E16-007` and the MEMORY_PCIE review.
- Consequently, claims that WPR2 is 0.50 MiB and that only 0.50 MiB of NVML reserved memory remains unexplained are invalid. Reconcile all derived security/boot-chain statements and leave carveout overlap/accounting unknown.
- `assertions.log` includes two earlier `[FAIL]` fuse-source assertions, followed by later all-pass runs. Do not summarize this file as 19/19 without identifying which final run produced the claim. Self-authored assertions do not validate semantic correctness; the WPR formula passed an assertion that encoded the same wrong formula.
- Revisit evidence levels for “authenticated/confirmed” privilege boundaries and “GPU firmware signed”: log strings and signature metadata are evidence of reported boot flow/metadata, not independent cryptographic verification. Distinguish archived log claims, source definitions, and independently observed facts.

Other useful results (boot log sequence, source provenance, two TU102 fuse definitions, SEC2 channel metadata, unknown retention) remain provisional until affected claims are corrected and cross-checked. No original artifacts were edited.
