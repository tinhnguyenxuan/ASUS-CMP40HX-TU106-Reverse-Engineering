# FALCON_RADIX_RECHECK — envydis argument-radix recheck of the 8 Falcon candidate probes

## Radix defect (confirmed)
Caller `PHASE16/FW_PAYLOAD_RISCV/payload_riscv_analyze.py:123` passed `str(skip)/str(limit)` (decimal strings) to `envydis -d/-l`, but `/tmp/envytools/envydis/envydis.c:94,97` parses both with `sscanf "%x"`. Decimal 36 ("36") was interpreted as skip 0x36=54; decimal 16 ("16") as skip 0x16=22; limit 150 ("150") as 0x150=336. The report labels ("0x24" slot 20, "0x10" others) were the hex of the decimal strings, not the actual skips. Capstone RISC-V calls are unaffected.

## Recompute method
Each of the 8 candidate spans was re-read from the verified container (sha256 re-checked) and probed with envydis using EXPLICIT hexadecimal arguments so `int(argv, 16)` equals the intended value:
  slot 20:  skip intended 36 -> argv "24"; other 7: skip intended 16 -> argv "10"; limit 150 -> argv "96".
A full-span baseline probe (skip 0, limit = size) was also run per slot to exhibit the linear sweep.
For every probe: requested skip/limit vs actual skip/limit, envydis first output address, first instruction raw bytes vs the original payload slice, and the complete envydis raw-output stream vs the payload slice.

## Probe results (requested vs actual vs byte-grounded)

| slot | probe | req skip | req limit | argv skip | argv limit | actual skip | actual limit | first addr | first raw | first match | stream consumed | stream match |
|------|-------|----------|-----------|-----------|------------|-------------|--------------|------------|-----------|-------------|-----------------|--------------|
| 20 | prior_best_recompute | 36 | 150 | 24 | 96 | 36(0x24) | 150(0x96) | 0x0 | af | True | 150 | True |
| 20 | full_span_baseline | 0 | 122880 | 0 | 1e000 | 0(0x0) | 122880(0x1E000) | 0x0 | - | False | 122880 | None |
| 150 | prior_best_recompute | 16 | 150 | 10 | 96 | 16(0x10) | 150(0x96) | 0x0 | f932 | True | 150 | True |
| 150 | full_span_baseline | 0 | 571136 | 0 | 8b700 | 0(0x0) | 571136(0x8B700) | 0x0 | - | False | 571136 | None |
| 156 | prior_best_recompute | 16 | 150 | 10 | 96 | 16(0x10) | 150(0x96) | 0x0 | f932 | True | 150 | True |
| 156 | full_span_baseline | 0 | 539136 | 0 | 83a00 | 0(0x0) | 539136(0x83A00) | 0x0 | - | False | 539136 | None |
| 481 | prior_best_recompute | 16 | 150 | 10 | 96 | 16(0x10) | 150(0x96) | 0x0 | f932 | True | 150 | True |
| 481 | full_span_baseline | 0 | 143360 | 0 | 23000 | 0(0x0) | 143360(0x23000) | 0x0 | - | False | 143360 | None |
| 484 | prior_best_recompute | 16 | 150 | 10 | 96 | 16(0x10) | 150(0x96) | 0x0 | f932 | True | 150 | True |
| 484 | full_span_baseline | 0 | 157440 | 0 | 26700 | 0(0x0) | 157440(0x26700) | 0x0 | - | False | 157440 | None |
| 487 | prior_best_recompute | 16 | 150 | 10 | 96 | 16(0x10) | 150(0x96) | 0x0 | f932 | True | 150 | True |
| 487 | full_span_baseline | 0 | 147712 | 0 | 24100 | 0(0x0) | 147712(0x24100) | 0x0 | - | False | 147712 | None |
| 490 | prior_best_recompute | 16 | 150 | 10 | 96 | 16(0x10) | 150(0x96) | 0x0 | f932 | True | 150 | True |
| 490 | full_span_baseline | 0 | 124160 | 0 | 1e500 | 0(0x0) | 124160(0x1E500) | 0x0 | - | False | 124160 | None |
| 493 | prior_best_recompute | 16 | 150 | 10 | 96 | 16(0x10) | 150(0x96) | 0x0 | f932 | True | 150 | True |
| 493 | full_span_baseline | 0 | 62720 | 0 | f500 | 0(0x0) | 62720(0xF500) | 0x0 | - | False | 62720 | None |

## What the bug actually did (prior phase, for contrast)
* slot 20: reported entry "+0x24"; caller passed decimal 36; envydis skipped 0x36=54 (mid-stream). Byte-re-derived real bring-up start: 0x2A (deep worker).
* slots 150/156/481/484/487/490/493: reported entry "+0x10"; caller passed decimal 16; envydis skipped 0x16=22 — which happens to equal the byte-re-derived bootstrap start 0x16, so the bug masked itself there; the label "0x10" was still wrong (actual skip 0x16).

## Byte-grounding verdict
Every prior_best_recompute probe's envydis raw-output stream matches the original payload slice byte-for-byte (`stream_match = true`), and the first instruction bytes match the slice at the computed file offset (`first_raw_match = true`). This grounds the disassembly in the actual payload bytes. It does NOT make any candidate a verified true entry: syntax-valid linear sweep is not verified code/entry.

## CFG audit of the deep worker primary-entry model (bounded window 0x200 from each entry)
| slot | entry | regions | gap bytes | terminators | fallthrough-after-terminator (unsound) | calls | branch targets | mid-region block split |
|------|-------|---------|-----------|-------------|----------------------------------------|-------|----------------|------------------------|
| 20 | 0x0002A | 11 | 402 | 1 | 1 | 1 | 0 | 0 |
| 150 | 0x00016 | 48 | 256 | 20 | 7 | 2 | 0 | 0 |
| 156 | 0x00016 | 50 | 255 | 19 | 5 | 2 | 0 | 0 |
| 481 | 0x00016 | 29 | 289 | 1 | 1 | 2 | 0 | 0 |
| 484 | 0x00016 | 29 | 289 | 1 | 1 | 2 | 0 | 0 |
| 487 | 0x00016 | 29 | 286 | 1 | 1 | 2 | 0 | 0 |
| 490 | 0x00016 | 27 | 299 | 1 | 1 | 1 | 0 | 0 |
| 493 | 0x00016 | 29 | 292 | 2 | 1 | 1 | 0 | 0 |

Findings:
* The deep worker adds a fallthrough edge (`off + size`) after EVERY instruction, including `ret`/`exit`/unconditional `bra`. Terminators with a following insn in the same region were found above, so those fallthrough edges are unsound: no fallthrough after an unconditional branch/ret/exit.
* `call` targets are register-indirect (`call $r1`, target UNKNOWN). The deep worker merges the call-target edge with fallthrough reachability; the ABI return edge (fallthrough to the next insn) and the call-target edge are distinct and must be tracked separately.
* Branch targets landing mid-decoded-region (not at a region start) require block splitting; the deep worker's region-start-only reachability cannot represent them. Affected targets are listed in the JSON.

## Orphan regions / low coverage — not density-as-proof
The deep worker reports code coverage of 11.4%–27.9% per payload with thousands of orphan region starts (4517 for slot 20 down to 1672 for slot 493), region sizes mostly 2–8 bytes, and 4-byte invalid-decode gaps interleaved throughout. That is consistent with embedded table(s)/codelet(s), not executable code. Decode density is not proof of code, and individual region entries are not classified as code (role UNKNOWN).

## Conclusion
* Entry: UNKNOWN (bounded candidate only). No incoming branch/call target or descriptor cross-reference lands on any candidate offset; engine/call targets unresolved. Retain UNKNOWN rather than promoting a linear-sweep offset to a true entry.
* Engine role: UNKNOWN — absent direct crossrefs to GSP/SEC2/MMIO addresses, no engine<->slot mapping is established and none is inferred.
* Prior Falcon entry labels (+0x24 slot 20, +0x10 others) are invalidated by the radix defect and require the explicit-hex recomputation above; they are not used for any positive claim.

## Files
* `falcon_radix_recheck.py` — this script (rerun command in header).
* `falcon_radix_recheck.json` — full structured results (probes + CFG audit).
* `run.log` — execution log with per-probe requested/actual/byte-compare lines.
* `input_hashes.json` — input hashes for reproduction.

## Constraints honoured
Read-only inputs only; stdlib + already-built envydis; no GPU, no hardware writes, no signature/key work, no new tools. Old/live scripts under PHASE16/FW_PAYLOAD_RISCV and PHASE16/FALCON_PAYLOAD_DEEP are untouched; this directory is isolated and new.
