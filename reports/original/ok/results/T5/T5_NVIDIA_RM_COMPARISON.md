# T5_NVIDIA_RM_COMPARISON.md

## NVIDIA RM Display Gate Comparison — Driver 615.78.08

### 1. Fuse read implementation

**File:** `src/nvidia/src/kernel/gpu/arch/maxwell/kern_gpu_gm107.c` (open-gpu-kernel-modules 615.78.08)
**Function:** `gpuFuseSupportsDisplay_GM107()`

```c
/*!
 * @brief Read fuse for display supported status.
 *        Some chips not marked displayless do not support display
 */
NvBool
gpuFuseSupportsDisplay_GM107(OBJGPU *pGpu)
{
    return GPU_FLD_TEST_DRF_DEF(pGpu, _FUSE, _STATUS_OPT_DISPLAY, _DATA, _ENABLE);
}
```

### 2. HAL dispatch — TU106 uses GM107 implementation

**File:** `src/nvidia/generated/g_gpu_nvoc.c` (lines 2094–2100)

```c
// gpuFuseSupportsDisplay -- halified (5 hals) body
if (( ((chipHal_HalVarIdx >> 5) == 1UL) && ((1UL << (chipHal_HalVarIdx & 0x1f)) & 0x000003e0UL) ))
/* ChipHal: TU102 | TU104 | TU106 | TU116 | TU117 */
{
    pThis->__gpuFuseSupportsDisplay__ = &gpuFuseSupportsDisplay_GM107;
}
```

**TU106 → `gpuFuseSupportsDisplay_GM107()`** (confirmed)

### 3. Fuse base address — critical finding

**File:** `src/nvidia/generated/g_gpu_nvoc.h` (line 5828)

```c
static inline NvU32 gpuGetPrimaryFuseBaseAddr_b2b553(struct OBJGPU *pGpu)
{
    return 0;
}
```

**For TU106, `gpuGetPrimaryFuseBaseAddr_HAL()` returns 0.**

This means `GPU_REG_RD32(pGpu, 0 + NV_FUSE_STATUS_OPT_DISPLAY)` =
`GPU_REG_RD32(pGpu, 0x21C04)` — the fuse register is at **absolute MMIO offset 0x21C04** from the register BAR base, not at `fuse_base + 0x21C04` where `fuse_base ≠ 0`.

### 4. Register definition (MAXWELL only — NOT Turing)

**File:** `src/common/inc/swref/published/maxwell/gm107/dev_fuse.h`

```c
#define NV_FUSE_STATUS_OPT_DISPLAY                                                                  0x00021C04 /* R-I4R */
#define NV_FUSE_STATUS_OPT_DISPLAY_DATA                                                                    0:0 /* R-IVF */
#define NV_FUSE_STATUS_OPT_DISPLAY_DATA_ENABLE                                                      0x00000000 /* R---V */
```

**`tu102/dev_fuse.h` does NOT define `NV_FUSE_STATUS_OPT_DISPLAY`.** It only defines:
- `NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS = 0x0002174C`
- `NV_FUSE_OPT_NVDEC_DISABLE = 0x00021378`

### 5. Consumers of gpuFuseSupportsDisplay_HAL

| # | File | Line | Code | Effect |
|---|------|------|------|--------|
| 1 | `src/nvidia/src/kernel/gpu/disp/kern_disp.c` | 444 | `if (!gpuFuseSupportsDisplay_HAL(pGpu)) return NV_ERR_NOT_SUPPORTED;` | Blocks display init |
| 2 | `src/nvidia/src/kernel/gpu/gsp/arch/turing/kernel_gsp_tu102.c` | 651 | `if (gpuFuseSupportsDisplay_HAL(pGpu) && kdispGetVgaWorkspaceBase(...))` | Skips VGA workspace layout |

### 6. Comparison with Nouveau

| Aspect | Nouveau | NVIDIA RM 615.78.08 |
|--------|---------|---------------------|
| Register read | `nvkm_rd32(device, 0x021c04)` | `GPU_REG_RD32(pGpu, 0 + 0x21C04)` |
| Check | `addr & 0x00000001` | `FLD_TEST_DRF_DEF(_DATA, _ENABLE)` (bit 0 == 0) |
| Effect | `return ERR_PTR(-ENODEV)` | `return NV_ERR_NOT_SUPPORTED` |
| Timing | Before PDISP/VBIOS parse | During display init |
| GPU family | GM100+ (Turing included) | TU102/TU104/TU106/TU116/TU117 |

### 7. Key difference: bit polarity

| Driver | Check | Display disabled when |
|--------|-------|----------------------|
| Nouveau | `addr & 0x00000001` | Bit 0 == 1 |
| NVIDIA RM | `DATA == _ENABLE` where `_ENABLE = 0x00000000` | Bit 0 == 0 |

**Wait — this is contradictory!** Nouveau checks bit 0 == 1 for disabled. NVIDIA RM checks DATA == 0x00000000 (ENABLE) for enabled. Let me re-examine:

- Nouveau: `if (addr & 0x00000001)` → if bit 0 IS set → display disabled → return -ENODEV
- NVIDIA RM: `GPU_FLD_TEST_DRF_DEF(_DATA, _ENABLE)` where `_ENABLE = 0x00000000` → if DATA == 0 → display enabled → return TRUE

So:
- Bit 0 = 0 → Nouveau: display enabled; RM: display enabled
- Bit 0 = 1 → Nouveau: display disabled; RM: display disabled (DATA ≠ ENABLE)

Both drivers agree: **bit 0 = 1 means display disabled.**

### 8. Live read on target <REDACTED_LAB_IP>

| Register | Value | Interpretation |
|----------|-------|----------------|
| 0x21C04 | 0x00000001 | Bit 0 = 1 → display disabled (both Nouveau and RM agree) |

## Ghi chú PONYTAIL

# ponytail: NVIDIA RM uses same register 0x021C04 as Nouveau. TU106 fuse base = 0, so read at absolute MMIO 0x21C04. Both drivers agree: bit 0 = 1 = display disabled. tu102/dev_fuse.h does NOT define this register (only gm107 does).
