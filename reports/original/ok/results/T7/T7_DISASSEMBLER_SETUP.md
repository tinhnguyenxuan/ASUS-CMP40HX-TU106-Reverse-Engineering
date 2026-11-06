# T7_DISASSEMBLER_SETUP.md

## T7 Phase A — Disassembler Setup & Verification

### 1. Firmware identity verification

| Artifact | Path | SHA-256 | Status |
|----------|------|---------|--------|
| Wrapper (from target) | `/home/REDACTED_USER/.hermes/cache/scratch/gsp/gsp_tu10x_615.78.08.bin` | `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b` | **MATCHES** T6-reported hash |
| Inner ELF (extracted) | `.../gsp_tu10x_615.78.08_inner.elf` | `cd83bb04d32a29c2daee20b58cd8cbbc67849f8e7c122ee9f87994eb4a2cfe85` | Derived from wrapper at file offset 0x40, length 22,901,568 |

Extraction: `dd if=gsp_tu10x_615.78.08.bin bs=1 skip=64 count=22901608`

Original source on target `<REDACTED_LAB_IP>`:
- `/lib/firmware/nvidia/615.78.08/gsp_tu10x.bin`, size 22,901,632
- Confirmed by `modinfo nvidia` → `firmware: nvidia/615.78.08/gsp_tu10x.bin`
- `nvidia-smi -q` → `GSP Firmware Version: 615.78.08`

### 2. Toolchain actually used

| Tool | Path | Version/capability |
|------|------|--------------------|
| llvm-objdump | `/usr/lib/llvm-18/bin/llvm-objdump` | Supports `riscv32` / `riscv64` |
| llvm-readelf | `/usr/lib/llvm-18/bin/llvm-readelf` | ELF64 RISC-V headers |
| Capstone | `python3 -c "import capstone"` on `/usr/bin/python3` | 5.0.7 (available but not needed — llvm-objdump resolved everything) |

`riscv64-linux-gnu-objdump` is NOT installed and no root access to install it. **Not required** — LLVM 18 ships RISC-V support natively.

Invocation used throughout:
```
/usr/lib/llvm-18/bin/llvm-objdump -d --triple=riscv64 \
  --start-address=0xADDR --stop-address=0xADDR gsp_tu10x_615.78.08_inner.elf
```

### 3. ISA validation — sanity disassembly of `.bootstrap`

`.bootstrap` vaddr 0x4009000, file offset 0x9000, size 0x74, flags AX. Disassembly first 8 instructions:

```
4009000: 9b 02 10 00   addiw  t0, zero, 0x1
4009004: 93 92 12 03   slli   t0, t0, 0x31
4009008: 93 82 12 00   addi   t0, t0, 0x1
400900c: 93 92 c2 00   slli   t0, t0, 0xc
4009010: 93 82 02 a0   addi   t0, t0, -0x600
4009014: 83 a2 02 00   lw     t0, 0x0(t0)
4009018: 93 d2 42 01   srli   t0, t0, 0x14
400901c: 93 f2 f2 1f   andi   t0, t0, 0x1ff
```

**Validation results:**

| Check | Observation | Verdict |
|-------|-------------|---------|
| Instruction width | Mixed 4-byte and 2-byte (compressed) — ELF flag `RVC` set | CORRECT |
| Immediate synthesis | `addiw t0,zero,1` / `slli t0,t0,0x31` / `addi t0,t0,1` = well-known 64-bit constant idiom | CORRECT |
| Control flow | `beq`/`bne` branch targets land on instruction boundaries (0x4009058, 0x4009060, 0x4009070) | CORRECT |
| Chip-ID decode | `andi t0,t0,0x1ff` then compares against 0x162/0x164/0x165/0x166/0x167/0x168/0x170 | CORRECT — these are NVIDIA chip IDs (0x162=TU102, 0x164=TU104, 0x166=TU106, 0x167=TU107, 0x168=TU116, 0x170=GA100) |
| Semantics | Code reads a fuse/memory word, shifts right 20, masks 9 bits, dispatches per chip ID | PLAUSIBLE and consistent with a GSP bootloader chip-detect |

**Conclusion: the disassembler is decoding the correct ISA. Instruction boundaries are self-consistent across a control-flow-dense region, and the decoded chip-ID table matches known NVIDIA values.**

### 4. Correction of T6's addressing error

T6 claimed `0x01042478`, `0x01042620`, `0x01042248` were "within .tu10x_text (0x04007000–0x04008414)".

**This was wrong.** Verified against the real section map:

| Address | Inside any mapped section? | Actual outcome |
|---------|---------------------------|----------------|
| 0x01042478 | NO | Not mapped by any section header. Falls inside no LOAD segment |
| 0x01042620 | NO | Not mapped |
| 0x01042248 | NO | Not mapped |

These were byte fragments misread from the `.manifest` section at file 0x12220 and are **not code addresses**. T6's interpretation of `.manifest` as a dispatch table is retracted.

By contrast, the three "old research" addresses from prior firmware analysis DO map:

| Address | Section | Offset within section |
|---------|---------|----------------------|
| 0x04BB6C90 | `.section_task_rm_elf_text_instance` (vaddr 0x4588000, size 0x1039000) | +0x62EC90 |
| 0x04BC63C4 | same | +0x63E3C4 |
| 0x04BBDD1C | same | +0x635D1C |

All three are real code, and 0x04BC682C (the handler found in T7) is within 0x448 bytes of 0x04BC63C4 — strong confirmation that the prior research was in the right neighborhood.

### 5. Real section layout (corrected, from `llvm-readelf -SW`)

| Section | Vaddr | File off | Size | Flag |
|---------|-------|----------|------|------|
| .ga100_data | 0x4001000 | 0x1000 | 0x1170 | WA |
| .tu10x_data | 0x4003000 | 0x3000 | 0x1170 | WA |
| .ga100_text | 0x4005000 | 0x5000 | 0x1414 | AX |
| .tu10x_text | 0x4007000 | 0x7000 | 0x1414 | AX |
| .bootstrap | 0x4009000 | 0x9000 | 0x74 | AX |
| .section_task_init_elf_text_instance | 0x4018000 | 0x18000 | 0x4000 | AX |
| **.section_task_rm_elf_rodata_instance** | **0x401d000** | **0x1d000** | **0x1e4000** | A |
| **.section_task_rm_elf_data_instance** | **0x4201000** | **0x201000** | **0x387000** | WA |
| **.section_task_rm_elf_text_instance** | **0x4588000** | **0x588000** | **0x1039000** | AX |

The RM task — the component owning all control handlers — is 17,010,688 bytes of code at 0x4588000–0x55C1000. T6 never looked here.

### 6. Program headers (relevant LOAD)

| Type | File offset | Vaddr | FileSiz | Flags |
|------|-------------|-------|---------|-------|
| LOAD | 0x000000 | 0x04000000 | 0x013010 | RWE |
| LOAD | 0x588000 | 0x4588000 | 0x1039000 | E |
| LOAD | 0x1d000 | 0x401d000 | 0x1e4000 | R |
| LOAD | 0x201000 | 0x4201000 | 0x387000 | RW |
| LOAD | 0x018000 | 0x4018000 | 0x004000 | E |

Entry point: **0x4009000** (.bootstrap), which dispatches to the per-chip init at -0x58 or -0x68 from `auipc`.

## Ghi chú PONYTAIL

# ponytail: llvm-objdump-18 has native riscv64, no install needed. Validated ISA on .bootstrap chip-ID dispatch (0x162..0x170 = NVIDIA chip IDs) — 2-byte RVC + 4-byte, branches land on boundaries. T6's 0x01042478/0x01042620/0x01042248 are NOT in any section; retracted. Real RM code is .section_task_rm_elf_text_instance at 0x4588000..0x55C1000.
