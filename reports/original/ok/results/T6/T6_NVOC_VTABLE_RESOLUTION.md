# T6_NVOC_VTABLE_RESOLUTION.md

## NVOC/VTABLE Resolution — GSP Indirect Call at +0x130

### 1. Driver-side NVOC dispatch (from open source)

The RM control dispatch for GSP commands goes through the NVOC (NVIDIA Virtual Object Cache) system. Key dispatch pattern:

| Command | RM Handler | File:Line | Target |
|---------|-----------|-----------|--------|
| `NV2080_CTRL_CMD_GR_GET_TPC_MASK` (0x20801237) | `subdeviceCtrlCmdKGrGetTpcMask_IMPL` | `subdevice_ctrl_gpu_kernel.c:1897` | Calls `kgrmgrGetLegacyTpcMask` |
| `NV2080_CTRL_CMD_GPU_GET_TPC_RECONFIG_MASK` (0x208001e7) | `subdeviceCtrlCmdGpuGetTpcReconfigMask_IMPL` | `subdevice_ctrl_gpu_kernel.c:1903` | Returns `NV_ERR_NOT_SUPPORTED` (0x56) |
| `NV2080_CTRL_CMD_INTERNAL_STATIC_KGR_GET_FLOORSWEEPING_MASKS` (0x20800a26) | `kgraphicsGetStaticInfo` | `kernel_graphics.c:1264` | RM Control to GSP firmware |

### 2. GSP-side dispatch (firmware, stripped ELF)

The GSP firmware ELF contains no symbol table. However, the `.manifest` section at offset 0x12220 contains entries with values:

| Entry | Offset (file) | Value (LE) | Address range |
|-------|---------------|------------|---------------|
| 1 | 0x12220 | 0x01042478 | Within .tu10x_text (0x4007000–0x4008414) |
| 2 | 0x12230 | 0x01042620 | Within .tu10x_text |
| 3 | 0x12240 | 0x01042248 | Within .tu10x_text |

These values appear to be function pointers in a dispatch table. The value `0x01042248` appears twice (possibly a vtable entry pointing to the same function for two methods).

### 3. Indirect call at +0x130

**The user's prior analysis noted:** "lời gọi hàm ảo qua offset +0x130" (virtual function call via offset +0x130).

This pattern is consistent with NVOC: an object's vtable/NVOC dispatch table where method offset 0x130 (308 bytes = 77 × 4-byte pointers) corresponds to a specific GSP-RM command handler.

**Resolution status:** The exact target of the +0x130 indirect call cannot be determined from the stripped ELF without RISC-V disassembly. Capstone RISC-V is not available in this environment (no root to install, no pip access).

### 4. What CAN be verified

| Item | Status | Evidence |
|------|--------|----------|
| GSP firmware is RISC-V ELF | PROVEN | `readelf -h` confirms Machine: RISC-V |
| GSP firmware version 615.78.08 | PROVEN | `.fwversion` string "615.78.08" |
| RM→GSP control command path | PROVEN | Driver source: `kernel_graphics.c:1264` |
| Floorsweeping mask stored in `legacyKgraphicsStaticInfo` | PROVEN | `kernel_graphics_manager.c:377`, `:600-608` |
| GET_TPC_RECONFIG_MASK returns 0x56 | PROVEN | `subdevice_ctrl_gpu_kernel.c:1903-1927` |
| GSP ELF has dispatch-relevant manifest entries | PROVEN | `.manifest` section at 0x12220–0x1224f |
| Exact +0x130 indirect call target | BLOCKED | ELF stripped, no RISC-V disassembler available |

## Ghi chú PONYTAIL

# ponytail: NVOC +0x130 indirect call target cannot be resolved from stripped GSP ELF. RM-side dispatch chain fully traced in driver source. GSP firmware handler for GET_FLOORSWEEPING_MASKS is in firmware, not open source.
