# T6_FLOORSWEEPING_PRODUCER.md

## Floorsweeping Producer — Source of TPC Mask Data

### 1. Data flow chain (fully traced in driver source)

```
GSP Firmware (615.78.08)
    │  RM Control: NV2080_CTRL_CMD_INTERNAL_STATIC_KGR_GET_FLOORSWEEPING_MASKS (0x20800a26)
    ▼
kernel_graphics.c:1264  → pRmApi->Control(..., 0x20800a26, ...)
    │  Result: floorsweepingMasks { gpcMask, tpcMask[], tpcCount[], physGpcMask, ... }
    ▼
kernel_graphics.c:1270  → pPrivate->staticInfo.floorsweepingMasks = result
    │
kernel_graphics_manager.c:377  → legacyKgraphicsStaticInfo.floorsweepingMasks = pKernelGraphicsStaticInfo->floorsweepingMasks
    │
kernel_graphics_manager.c:600-608  → kgrmgrGetLegacyTpcMask_IMPL(gpcId)
    │  Returns: legacyKgraphicsStaticInfo.floorsweepingMasks.tpcMask[gpcId]
    ▼
subdevice_ctrl_gpu_kernel.c:1897  → subdeviceCtrlCmdKGrGetTpcMask_IMPL returns tpcMask to host
```

### 2. floorsweepingMasks struct definition

**File:** `src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080internal.h` (lines 300-345)

```c
typedef struct NV2080_CTRL_GR_FS_INFO {
    NvU32   gpcMask;                                          // Bitmask of active GPCs
    NvU32   tpcMask[NV2080_CTRL_INTERNAL_GR_MAX_GPC];         // TPC mask per GPC
    NvU32   tpcCount[NV2080_CTRL_INTERNAL_GR_MAX_GPC];        // TPC count per GPC
    NvU32   physGpcMask;                                      // Physical GPC mask
    NvU32   physGfxGpcMask;                                   // Physical GFX GPC mask
    NvU32   numGfxTpc;                                        // Number of GFX TPCs
} NV2080_CTRL_GR_FS_INFO;
```

`NV2080_CTRL_INTERNAL_GR_MAX_GPC` = 8 (max GPCs supported)

### 3. Live values on CMP 40HX (TU106-100-A1)

| GPC | tpcMask | Interpretation |
|-----|---------|----------------|
| GPC0 | 0x1F | 5 TPCs active (bits 0-4), TPC5 (bit 5) disabled |
| GPC1 | 0x3F | 6 TPCs active (bits 0-5) |
| GPC2 | 0x3F | 6 TPCs active (bits 0-5) |
| **Total** | **17 TPCs** | **34 SMs** (expected 18 TPCs / 36 SMs for full TU106) |

### 4. Producer — where does the mask come from?

The floorsweepingMasks data originates from **GSP firmware** via RM control command 0x20800a26. The GSP firmware reads this from:

| Possible source layer | Evidence | Verdict |
|----------------------|----------|---------|
| Raw OTP fuse | No OTP read path found in driver source for TPC mask | UNKNOWN |
| Hardware fuse shadow/latch | No latch mechanism found for TPC mask | UNKNOWN |
| Firmware-initialized | GSP firmware contains the handler; firmware reads at boot | SUPPORTED (by elimination) |
| VBIOS-strapped | No VBIOS reference to TPC floorsweeping mask found | UNKNOWN |
| Strap/config pin | No strap reference found | UNKNOWN |

### 5. GSP firmware strings relevant to disable features

| String | ELF location | Likely meaning |
|--------|--------------|----------------|
| `RmDisableFwseclic` | `.rodata` | Firmware security license disable (possibly feature gating) |
| `RmDisableDisplay` | `.rodata` | Display subsystem disable |
| `RmDisableDispMacro` | `.rodata` | Display macro disable |
| `RmHulkDisableFeatures` | `.rodata` | HULK (Turing block) feature disable |

None of these strings directly reference TPC floorsweeping. The floorsweeping mask producer in GSP firmware is not identifiable from strings alone.

### 6. Gap in call graph

| Link | Status | Reason |
|------|--------|--------|
| RM → GSP: Control command 0x20800a26 | PROVEN | Driver source `kernel_graphics.c:1264` |
| GSP firmware handler for 0x20800a26 | BLOCKED | Handler is in stripped GSP ELF, not open source |
| GSP firmware → TPC mask source (OTP/fuse/strap) | BLOCKED | No strings or code paths visible in stripped ELF |

## Ghi chú PONYTAIL

# ponytail: Floorsweeping mask producer is GSP firmware via RM control 0x20800a26. The actual source within GSP (OTP/fuse/strap/firmware-init) cannot be determined from stripped ELF. Driver-side chain fully traced.
