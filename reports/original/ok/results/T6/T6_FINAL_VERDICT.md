# T6_FINAL_VERDICT.md

## T6 FINAL VERDICT — TU106 GSP Floorsweeping Producer & Missing TPC5

### 1. GSP firmware identification (PROVEN)

| Property | Value | Source |
|----------|-------|--------|
| Firmware file | `/lib/firmware/nvidia/615.78.08/gsp_tu10x.bin` | Target |
| Local copy | `gsp_tu10x_615.78.08.bin` | SCP from target |
| Inner ELF | `gsp_tu10x_615.78.08_inner.elf` | Extracted at offset 0x40 |
| SHA-256 | `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b` | `sha256sum` |
| ELF type | ELF64 EXEC RISC-V soft-float | `readelf -h` |
| Version string | `615.78.08` | `.fwversion` at 0x15d3e2c |
| Entry point | 0x4009000 | `readelf -h` |
| Compiler | NVRISCV GCC 12.2.0-2024.03.01 | `.comment` section |

### 2. Mask producer chain (PROVEN on RM side, BLOCKED on GSP side)

| Step | Component | Status | Evidence |
|------|-----------|--------|----------|
| RM Control: 0x20800a26 | `kernel_graphics.c:1264` | PROVEN | `pRmApi->Control(NV2080_CTRL_CMD_INTERNAL_STATIC_KGR_GET_FLOORSWEEPING_MASKS)` |
| Result storage | `kernel_graphics.c:1270` | PROVEN | `pPrivate->staticInfo.floorsweepingMasks` |
| Copy to legacy | `kernel_graphics_manager.c:377` | PROVEN | `legacyKgraphicsStaticInfo.floorsweepingMasks` |
| TPC mask read | `kernel_graphics_manager.c:600-608` | PROVEN | `tpcMask[gpcId]` |
| GSP handler for 0x20800a26 | GSP firmware ELF | BLOCKED | Stripped ELF, no symbol table, no RISC-V disassembler |
| GSP firmware mask source | OTP/fuse/strap/firmware-init | UNKNOWN | Not identifiable from stripped ELF |

### 3. Mask layer verdicts

| Layer | Verdict | Evidence |
|-------|---------|----------|
| Physical TPC presence | 18 TPCs (3 GPC × 6 TPC) | TU106-100-A1 spec |
| Disabled/defective (floorswept) | GPC0/TPC5 disabled | Mask 0x1F vs 0x3F |
| Fuse/OPT mask | UNKNOWN | `tu102/dev_fuse.h` has no TPC fuse |
| Reconfig mask | NOT SUPPORTED | GET_TPC_RECONFIG_MASK returns 0x56 |
| Effective active mask | 17 TPCs (34 SMs) | nvidia-smi topology |

### 4. GPC0/TPC5 specific

| Question | Answer | Evidence |
|----------|--------|----------|
| Is TPC5 physically present? | YES | TU106-100-A1 has 6 TPCs/GPC |
| Is TPC5 disabled? | YES | GPC0 mask = 0x1F (bit 5 clear) |
| Who decided? | GSP firmware | RM control 0x20800a26 returns mask from GSP |
| Can host re-enable? | NO | GET_TPC_RECONFIG_MASK returns 0x56 |
| Is it fuse-disabled? | UNKNOWN | No TPC fuse definition in tu102/dev_fuse.h |
| Is it strap-disabled? | UNKNOWN | No strap reference found |

### 5. Three propositions — status

| Proposition | Status | Evidence |
|-------------|--------|----------|
| GPC0/TPC5 is missing from effective topology | PROVEN | nvidia-smi: 17 TPCs vs 18 expected |
| Decision originates from GSP firmware | SUPPORTED | RM control chain traces to GSP via 0x20800a26 |
| Source is raw OTP/hardware fuse | UNKNOWN | No TPC fuse in tu102/dev_fuse.h; stripped ELF blocks analysis |

### 6. Gọi hàm ảo tại offset +0x130

**Status:** BLOCKED. The GSP ELF is stripped (no .symtab). RISC-V disassembly requires capstone which is not available in this environment (no root, no pip install). The .manifest section contains dispatch-relevant entries at offsets 0x12220–0x1224f with values 0x01042478, 0x01042620, 0x01042248, but these cannot be mapped to function names without disassembly.

### 7. Mắt xích thiếu (missing links)

| Missing link | Where to check | Method |
|--------------|----------------|--------|
| GSP handler for RM control 0x20800a26 | GSP ELF `.tu10x_text` section | RISC-V disassembly (capstone or objdump-riscv) |
| TPC mask source within GSP (OTP/fuse/strap) | GSP firmware boot code | RISC-V disassembly + string xref |
| Whether GET_TPC_RECONFIG_MASK could work on different GSP version | Different GSP ELF | Compare dispatch tables across versions |

## Ghi chú PONYTAIL

# ponytail: GPC0/TPC5 disable decision comes from GSP firmware via RM control 0x20800a26. Fuse/strap source UNKNOWN (stripped ELF blocks analysis). Host cannot re-enable (0x56). Three propositions distinct: missing=PROVEN, GSP-origin=SUPPORTED, OTP-fuse=UNKNOWN.
