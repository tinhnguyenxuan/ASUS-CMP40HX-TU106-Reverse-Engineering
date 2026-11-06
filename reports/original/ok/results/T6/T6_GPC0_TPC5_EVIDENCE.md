# T6_GPC0_TPC5_EVIDENCE.md

## GPC0/TPC5 — Evidence for Missing TPC5

### 1. Direct evidence from live system

| Source | Value | Interpretation |
|--------|-------|----------------|
| nvidia-smi topology | GPC0=0x1F, GPC1=0x3F, GPC2=0x3F | GPC0 has 5 TPCs, GPC1/GPC2 have 6 |
| `kgrmgrGetLegacyTpcMask_IMPL` | Returns `floorsweepingMasks.tpcMask[gpcId]` | Mask comes from GSP via RM control 0x20800a26 |
| TU106-100-A1 spec | 3 GPC × 6 TPC = 18 TPC | Full chip would have 18 TPCs / 36 SMs |
| Current effective | 17 TPCs / 34 SMs | 1 TPC missing (GPC0/TPC5) |

### 2. Where TPC5 disablement is decided

| Layer | Decision point | Evidence |
|-------|---------------|----------|
| GSP firmware | Floorsweeping at boot | RM control 0x20800a26 returns masks from GSP |
| Driver | Reads mask from GSP result | `kernel_graphics.c:1264-1270` |
| OTP/fuse | Not defined for TPC mask | `tu102/dev_fuse.h` has no TPC fuse definition |
| VBIOS | No floorsweeping table found | No VBIOS reference to TPC disable mask |
| Host software | Cannot override | GET_TPC_RECONFIG_MASK returns 0x56 |

### 3. Call graph for GPC0/TPC5 disable decision

```
Host query (nvidia-smi)
    │
    ▼
subdeviceCtrlCmdKGrGetTpcMask_IMPL
    [subdevice_ctrl_gpu_kernel.c:1897]
    │
    ▼
kgrmgrGetLegacyTpcMask_IMPL
    [kernel_graphics_manager.c:600-608]
    │  Returns legacyKgraphicsStaticInfo.floorsweepingMasks.tpcMask[gpcId]
    │  For GPC0: returns 0x1F (TPC5 bit clear)
    ▼
legacyKgraphicsStaticInfo.floorsweepingMasks
    [kernel_graphics_manager.c:377]
    │  Copied from pKernelGraphicsStaticInfo->floorsweepingMasks
    ▼
pPrivate->staticInfo.floorsweepingMasks
    [kernel_graphics.c:1270]
    │  Populated by RM Control NV2080_CTRL_CMD_INTERNAL_STATIC_KGR_GET_FLOORSWEEPING_MASKS (0x20800a26)
    ▼
GSP Firmware (615.78.08)
    │  Handler for 0x20800a26 is in stripped GSP ELF
    │  Cannot determine if source is OTP, fuse, strap, or firmware-init
```

### 4. What we CANNOT conclude

| Claim | Status | Missing evidence |
|-------|--------|------------------|
| TPC5 is hard-fused (OTP) | UNKNOWN | No TPC fuse in tu102/dev_fuse.h |
| TPC5 is strap-disabled | UNKNOWN | No strap reference found |
| TPC5 is firmware-decided | SUPPORTED (by elimination) | GSP returns mask; no other source found |
| TPC5 can be re-enabled | NOT SUPPORTED | GET_TPC_RECONFIG_MASK returns 0x56 |
| TPC5 is physically absent | NOT SUPPORTED | TU106-100-A1 has 6 TPCs/GPC |

## Ghi chú PONYTAIL

# ponytail: GPC0/TPC5 disable decision originates from GSP firmware via RM control 0x20800a26. Cannot determine if source is OTP/fuse/strap from stripped ELF. Host cannot re-enable (0x56). Physical vs logical: no remapping evidence.
