# FW_PAYLOAD_RISCV_REPORT — PHASE16 continuation (CMP40HX / TU106 ucode container)

## 1. Scope and constraints (honoured)
- Read-only inputs only: `outputs/ucodes_tu10x.bin` (8,837,632 B, sha256 `6027ab37...eb4a5d`) and `PHASE16/FW_PAYLOAD_ISA/payload_isa_verified.json` (38 external payloads). Prior outputs under `PHASE16/FW_PAYLOAD_ISA/` are preserved untouched.
- Source correlation only against `/tmp/nvsrc` headers (copies + manifest in `PHASE16/SOURCES/`): `bin_data_pvt.h` (BINDATA_UCODES_BIN_HEADER / BINDATA_STORAGE_PVT), `bin_data.h` (BINDATA_LABEL — per-label index, NOT a global slot index), `rmRiscvUcode.h` (RM_RISCV_UCODE_DESC, versions 1-5 documented), `rmflcnbl.h` (RM_FLCN_BL_IMG_HEADER; code/data offsets multiples of 256). No generated firmware descriptor instance exists in the snapshot (only `RM_RISCV_UCODE_DESC *pGspRmBootUcodeDesc` declaration).
- No tool installation. stdlib Python 3 + already-installed capstone + already-built envydis. No GPU, no MMIO, no keys/signature handling, no bruteforce, no checksum/version consumer calls.
- No ISA claimed from entropy; no encryption/AES inference anywhere. Entropy ≈ 8.0 is treated as "no ISA structure detected", not as ciphertext.
- Code-start is never selected by longest prefix alone: entry candidates are scored on valid-prefix length, decode density, control-transfer plausibility and ISA markers together; all candidates and their signals are reported per payload.
- All new outputs under `PHASE16/FW_PAYLOAD_RISCV/`: `payload_riscv_analyze.py`, `payload_riscv_verified.json` (raw results), `FW_PAYLOAD_RISCV_REPORT.md`, `run.log`, `work/` (extracted payload spans for envydis).

## 2. Discrepancy correction — capstone availability
`payload_isa_verified.json` states `"capstone_available": true`; `FW_PAYLOAD_ISA_REPORT.md` states "Capstone unavailable in /usr/bin/python3". The report statement was WRONG; the JSON was correct.

Verified against the live `/usr/bin/python3` (Python 3.12.3):
- `import capstone` succeeds; version **5.0.7**, module `/home/REDACTED_USER/.local/lib/python3.12/site-packages/capstone/__init__.py`.
- Actual decode probe with `CS_ARCH_RISCV | CS_MODE_RISCV64 | CS_MODE_RISCVC` on bytes `130a0000 000a0000 130b0000 67800080 02a43823 80a02083` produced:
  `0x1000 mv s4, zero` / `0x1004 c.addi4spn s0, sp, 0x110` / `0x1006 c.unimp` / `0x1008 mv s6, zero` / `0x100c jalr zero, ra, -0x800` / `0x1010 c.fsdsp ft0, 8(sp)` / `0x1012 c.fld fa4, 0x40(a4)` / `0x1014 c.fsd fs0, 0(s1)`.
- Bounded RISC-V disassembly below was therefore performed for real (not structural guesswork). The prior report's "not disassembled because capstone missing" conclusion is invalidated; see §5.

## 3. Method — bounded disassembly, multiple signals
For each of the 38 payload spans (read from the container at record offset/length):
1. Source-struct tests at payload offset 0: `RM_RISCV_UCODE_DESC` (92 B, 23 u32; version must be 1-5; every offset+size pair must fit the span) and `RM_FLCN_BL_IMG_HEADER` (16 B; codeSize/dataSize != 0, offsets 256-aligned, ranges inside span).
2. Capstone RISC-V scan: entry candidates at 4-byte-aligned offsets 0..min(512, size); at each, disassemble up to 512 B window; record consecutive valid-instruction prefix (count + bytes), density (prefix bytes / window), and control-transfer plausibility (direct branch/jump targets 4-aligned and landing inside the decoded region; ≥40% of direct control transfers in-range, or a ≥16-instruction straight-line stream). Top 6 candidates kept per payload; score = 0.4·prefix + 0.4·density + 0.2·CF. Proof bar for "RISC-V code": prefix ≥ 10 insns AND density ≥ 0.70 AND CF plausible. Never longest-prefix alone.
3. Falcon via envydis (`-m falcon`) for payloads whose 32-byte header starts with `d0` (the `d0 XX XX 00 00 fe 04 00 bd a4 7e 10` family seen in inventory): same entry scan, proof bar prefix ≥ 8 insns AND Falcon special-register markers (`$xcbase`, `$xtargets`, `exit`, `bra`, `call`, `mov $`).

## 4. Results — proven per-payload ISA/role vs unknowns

| slot | offset | size | entropy | header32 | proven ISA/role | confidence | entry | basis |
|------|--------|------|---------|----------|-----------------|------------|-------|-------|
| 20 | 0x002F00 | 122,880 | 3.4807 | d0c0ff00... | **Falcon code** | medium | +0x24 | envydis prefix 17 insns, density 0.136, Falcon `$xcbase`/`$xtargets` markers |
| 493 | 0x85E500 | 62,720 | 2.4236 | d0007900... | **Falcon code** | medium | +0x10 | envydis prefix 11, density 0.371, Falcon markers |
| 487 | 0x81BF00 | 147,712 | 2.7862 | d000f000... | **Falcon code** | medium | +0x10 | envydis prefix 11, density 0.389, Falcon markers |
| 490 | 0x840000 | 124,160 | 3.7980 | d000f000... | **Falcon code** | medium | +0x10 | envydis prefix 11, density 0.371, Falcon markers |
| 481 | 0x7D2800 | 143,360 | 4.1983 | d000f000... | **Falcon code** | medium | +0x10 | envydis prefix 11, density 0.389, Falcon markers |
| 484 | 0x7F5800 | 157,440 | 4.5950 | d000f000... | **Falcon code** | medium | +0x10 | envydis prefix 11, density 0.389, Falcon markers |
| 150 | 0x161100 | 571,136 | 4.8686 | d0005e00... | **Falcon code** | medium | +0x10 | envydis prefix 10, density 0.357, Falcon markers |
| 156 | 0x41A400 | 539,136 | 4.8136 | d0005e00... | **Falcon code** | medium | +0x10 | envydis prefix 10, density 0.341, Falcon markers |

All 8 share the `d0*` container header (`d0 XX XX 00 00 fe 04 00 bd a4 7e 10 XX 00 f8 02 ...`); entry points lie right after the 16-byte header prefix, never inside the header itself. This matches Phase-3 Falcon identification for 20/487/490/493 and extends it to 150/156/481/484. `RM_FLCN_BL_IMG_HEADER@0` is rejected for all of them (codeOffset+codeSize beyond payload / not 256-aligned), so they are Falcon *code blobs*, not the RM_FLCN_BL_IMG_HEADER-wrapped image.

UNKNOWN (30 payloads, full evidence in `payload_riscv_verified.json`):
- Slots 21, 22, 23, 24, 151, 152, 153, 154, 452, 453, 456, 459, 460, 464, 465, 468, 469, 473, 474, 477, 478: entropy 7.998–8.000, no ISA structure. **Rejected as executable code; no encryption claim made** (entropy alone does not prove ciphertext). Capstone RISC-V scan: best prefixes short (8–24 insns), density 0.04–0.11, no control-flow plausibility anywhere.
- Slots 32, 33, 34, 35, 36, 37: offset-table-shaped headers (`00000000 28000000 01000000 …` / slot 37 `…32000000`). **Rejected as RM_RISCV_UCODE_DESC at offset 0**: version field = 0, outside the documented 1-5 set (rmRiscvUcode.h); no candidate start met the RISC-V proof bar (best densities 0.04–0.09; CF occasionally plausible on ≤22 insn fragments but not on a sustained decode). Engine identity UNKNOWN; header bytes and table offsets preserved as evidence.
- Slots 449, 461, 470: `d0007900…` headers, entropy ~5.8; envydis best prefix only 6 insns (+0x70, below the 8-insn proof bar) though Falcon markers appear; capstone RISC-V fragments short, no CF. UNKNOWN — Falcon-leaning bytes, below proof threshold.

**RISC-V code: proven nowhere.** Every payload was scanned with real `CS_ARCH_RISCV | CS_MODE_RISCV64 | CS_MODE_RISCVC`; no span showed a sustained, control-flow-plausible decode. RISC-v-like prefix bytes occur (RISC-V's dense opcode space decodes random 4-byte streams syntactically), but none formed code by the CF/density signals.

Source-struct results (all 38 payloads): `RM_RISCV_UCODE_DESC@0` rejected on `version=0` (table-shaped headers) or version outside 1-5 (`d0*` headers decode to e.g. 0x00ffc0d0 / 6160592 / 15728848); `RM_FLCN_BL_IMG_HEADER@0` rejected on codeSize==0 / range beyond payload / non-256-aligned offsets. BINDATA_LABEL was not used as a global slot index. No generated descriptor instance exists in the snapshot; that remains unavailable, not inferred.

## 5. What changed vs Phase 3
- capstone 5.0.7 IS present under `/usr/bin/python3`; the "Capstone unavailable" statement in `FW_PAYLOAD_ISA_REPORT.md` is retracted. `payload_isa_verified.json`'s `capstone_available=true` stands correct.
- RISC-V decoding actually performed (`CS_ARCH_RISCV | CS_MODE_RISCV64 | CS_MODE_RISCVC`) on all 38 spans; result: no RISC-V code proven.
- Falcon coverage extended from 4 to 8 payloads: 150 and 156 (previously "offset-table / UNKNOWN", actually `d0005e00` Falcon headers) and 481/484 (low-entropy `d000f000` candidates not selected in Phase 3) now proven Falcon code at +0x10.
- Phase-3 Falcon entries re-verified identically: 20 (+0x24), 493/487/490 (+0x10).

## 6. Files produced (PHASE16/FW_PAYLOAD_RISCV/)
- `payload_riscv_analyze.py` — rerunnable script; command: `/usr/bin/python3 payload_riscv_analyze.py  (cwd: PHASE16/FW_PAYLOAD_RISCV)`
- `payload_riscv_verified.json` — raw per-payload results (headers, entropy, struct-test failures, capstone scan candidates + scores, envydis entries, verdicts)
- `FW_PAYLOAD_RISCV_REPORT.md` — this report
- `run.log` — execution log incl. capstone version/probe and per-payload verdicts
- `work/` — extracted payload spans used by envydis (regenerable by the script)

## 7. Input hashes (read-only, verified)
- `outputs/ucodes_tu10x.bin`: sha256 `6027ab3736f733b5a06e6e61aaae957d1f990426a263849ebcfa8a49eeb4a5d`, 8,837,632 B
- `PHASE16/FW_PAYLOAD_ISA/payload_isa_verified.json`: source of the 38-record inventory (not modified)
- Source hashes recorded in `payload_riscv_verified.json` (`source_refs`) from `/tmp/nvsrc` snapshot files.
