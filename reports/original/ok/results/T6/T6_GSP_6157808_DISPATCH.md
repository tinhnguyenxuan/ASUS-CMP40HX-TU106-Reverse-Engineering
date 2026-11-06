# T6_GSP_6157808_DISPATCH.md

## GSP Firmware 615.78.08 — Dispatch Table Analysis

### 1. GSP Firmware Identification

| Property | Value | Source |
|----------|-------|--------|
| File | `/lib/firmware/nvidia/615.78.08/gsp_tu10x.bin` | Target <REDACTED_LAB_IP> |
| Local copy | `/home/REDACTED_USER/.hermes/cache/scratch/gsp/gsp_tu10x_615.78.08.bin` | SCP from target |
| Inner ELF | `/home/REDACTED_USER/.hermes/cache/scratch/gsp/gsp_tu10x_615.78.08_inner.elf` | Extracted at offset 0x40 |
| Size | 22,901,632 bytes | `ls -la` |
| SHA-256 | `0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b` | `sha256sum` |
| ELF Type | ELF64, EXEC, RISC-V, soft-float ABI | `readelf -h` |
| Entry point | 0x4009000 | `readelf -h` |
| Compiler | NVRISCV GCC 12.2.0-2024.03.01 | `.comment` section |
| Firmware version string | `615.78.08` | `.fwversion` at offset 0x15d3e2c |

### 2. ELF Section Layout (inner ELF)

| Section | Address | Offset | Size | Flags |
|---------|---------|--------|------|-------|
| .ga100_data | 0x4001000 | 0x1000 | 0x1170 | WA |
| .tu10x_data | 0x4003000 | 0x3000 | 0x1170 | WA |
| .ga100_text | 0x4005000 | 0x5000 | 0x1414 | AX |
| .tu10x_text | 0x4007000 | 0x7000 | 0x1414 | AX |
| .bootstrap | 0x4009000 | 0x9000 | 0x74 | AX |
| .manifest | 0x4012150 | 0x12150 | 0xeb0 | WA |
| .section_tas* (various) | 0x4014000+ | various | various | WA/AX |
| .header | 0x4013000 | 0x13000 | 0x10 | A |

### 3. Dispatch-relevant strings found in GSP ELF

| String | Location context | Relevance |
|--------|-----------------|-----------|
| `RmDisableFwseclic` | `.rodata` | FW security license disable |
| `RmDisableDisplay` | `.rodata` | Display disable |
| `RmDisableDispMacro` | `.rodata` | Display macro disable |
| `RmHulkDisableFeatures` | `.rodata` | HULK feature disable |
| `GPC1`..`GPC5` | `.rodata` | GPC identifiers |
| `GPCCLIENT_T1_0`..`GPCCLIENT_T1_18` | `.rodata` | TPC client names (19 entries) |
| `GR_UNIT_TYPE_GPC`, `GR_UNIT_TYPE_TPC` | `.rodata` | GR unit types |
| `NV2080_CTRL_PMGR_*` | `.rodata` | RM control command constants |
| `NV2080_CTRL_CLK_*` | `.rodata` | RM control command constants |

### 4. .manifest section — dispatch/cmd table candidate

At file offset 0x12220–0x1224f, the manifest contains 16-byte entries. Three consecutive entries:

| Offset (file) | Raw bytes (LE) | Interpretation |
|---------------|----------------|----------------|
| 0x12220 | `00004000 00000000 78240104 00000000` | Entry: ptr=0x4000, value=0x01042478 |
| 0x12230 | `20260104 00000000 00000000 00000000` | Entry: value=0x01042620 |
| 0x12240 | `02000000 00000000 48220104 48220104` | Entry: count=2, func1=0x01042248, func2=0x01042248 |

These values (`0x01042478`, `0x01042620`, `0x01042248`) fall within the .tu10x_text section range (0x4007000–0x4008414). They may be handler function addresses or command IDs in a dispatch table.

**Note:** Without a symbol table (ELF is stripped), these cannot be mapped to function names. RISC-V disassembly requires capstone which is not available in this environment.

### 5. RM control command chain (from driver source)

| Step | Component | File:Line | Detail |
|------|-----------|-----------|--------|
| 1 | `kgraphicsGetStaticInfo` → RM Control | `kernel_graphics.c:1264` | Calls `NV2080_CTRL_CMD_INTERNAL_STATIC_KGR_GET_FLOORSWEEPING_MASKS` (0x20800a26) |
| 2 | Result stored | `kernel_graphics.c:1270` | `pPrivate->staticInfo.floorsweepingMasks` |
| 3 | Copied to legacy static info | `kernel_graphics_manager.c:377` | `legacyKgraphicsStaticInfo.floorsweepingMasks = pKernelGraphicsStaticInfo->floorsweepingMasks` |
| 4 | TPC mask read | `kernel_graphics_manager.c:600-608` | `kgrmgrGetLegacyTpcMask_IMPL` returns `legacyKgraphicsStaticInfo.floorsweepingMasks.tpcMask[gpcId]` |
| 5 | Host consumer | `subdevice_ctrl_gpu_kernel.c:1897` | `subdeviceCtrlCmdGpuGetTpcReconfigMask_IMPL` calls `kgrmgrGetLegacyTpcMask` |

### 6. GSP dispatch gap

The RM control command `NV2080_CTRL_CMD_INTERNAL_STATIC_KGR_GET_FLOORSWEEPING_MASKS` (0x20800a26) is issued from `kernel_graphics.c`. The handler for this command is NOT found in the open kernel source — it is handled by GSP firmware. The dispatch from RM to GSP goes through the GSP-RM interface (not visible in open source).

## Ghi chú PONYTAIL

# ponytail: GSP ELF 615.78.08 extracted from /lib/firmware/nvidia/615.78.08/gsp_tu10x.bin. SHA-256: 0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b. ELF is stripped (no symtab). RM→GSP dispatch for GET_FLOORSWEEPING_MASKS goes through firmware; handler not visible in open source.
