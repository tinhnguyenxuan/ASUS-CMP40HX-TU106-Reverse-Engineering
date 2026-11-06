# T5_VERDICT.md

## T5 FINAL VERDICT — TU106 Display Fuse Provenance (NVIDIA RM + Nouveau)

### 1. Cross-driver confirmation of 0x021C04

| Driver | Function | File | Line | Register | Check | Result on CMP 40HX |
|--------|----------|------|------|----------|-------|-------------------|
| Nouveau | `pramin_init()` | `shadowramin.c` | 68 | `nvkm_rd32(device, 0x021c04)` | `addr & 0x00000001` | Bit 0 = 1 → display disabled → -ENODEV |
| NVIDIA RM | `gpuFuseSupportsDisplay_GM107()` | `kern_gpu_gm107.c` | 67–72 | `GPU_REG_RD32(pGpu, 0 + 0x21C04)` | `DATA == _ENABLE (0x0)` | DATA = 1 ≠ 0 → NV_ERR_NOT_SUPPORTED |

**Both drivers read the same register at the same MMIO offset (0x21C04) and agree: bit 0 = 1 means display disabled.**

### 2. Timing comparison

| Driver | When 0x021C04 is read | Relative to VBIOS/PDISP |
|--------|----------------------|------------------------|
| Nouveau | `pramin_init()` — BIOS source registration | **Before** PDISP and VBIOS parsing |
| NVIDIA RM | Display init path (`kern_disp.c:444`) | During display device initialization, after VBIOS parsed |

### 3. What IS proven (display disabled in current environment)

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Bit 0 of 0x021C04 = 1 on CMP 40HX | **PROVEN** | Live MMIO read = 0x00000001 |
| Nouveau would reject CMP 40HX BIOS | **PROVEN** | `pramin_init()` returns -ENODEV when bit 0 = 1 |
| NVIDIA RM blocks display init | **PROVEN** | `kern_disp.c:444` returns `NV_ERR_NOT_SUPPORTED` |
| Display is disabled in current environment | **PROVEN** | nvidia-smi: `Display Attached: No`, `Display Active: Disabled` |

### 4. What is NOT proven (hardware fuse vs other)

| Claim | Verdict | Reason |
|-------|---------|--------|
| 0x021C04 is raw OTP fuse | **UNPROVEN** | `tu102/dev_fuse.h` does not define 0x21C04; no OTP read path in source |
| 0x021C04 is hardware shadow/latch | **UNPROVEN** | No latch mechanism found; value persists but could be firmware-set |
| 0x021C04 is firmware-initialized | **UNPROVEN** | dmesg shows `FWSEC_COMPLETE_GSP_UNTOUCHED`; no writer found in kernel source |
| 0x021C04 is permanent/cannot change | **UNPROVEN** | No write test performed (prohibited by constraints) |
| SEC2/GSP sets 0x021C04 | **UNPROVEN** | No evidence of firmware writing this register |

### 5. DCB correction (from T5_DCB_CORRECTION.md)

| Error in T4 | Correction |
|-------------|------------|
| Type 0x06 = eDP | **0x06 = DisplayPort; 0x05 = eDP** |
| Type 0x0E has pointer | **0x0E = End of Line (table terminator)** |
| Type 0x0F has pointer | **0x0F = Skip Entry** |
| Pointers are memory addresses | **DCB pointers are VBIOS-relative offsets** |
| GeForce 268920/265590 have 7 connectors | **They have 5 real connectors** |

### 6. Mắt xích thiếu (missing link)

| Missing | Where to check |
|---------|----------------|
| OTP/eFuse read path to 0x021C04 | NVIDIA fuse controller documentation (not in open source) |
| Firmware/devinit code that sets 0x021C04 | GSP firmware binary, VBIOS init tables (not open) |
| Whether 0x021C04 is writable | MMIO write test (prohibited) |
| Whether value changes across reboots | Multiple live reads (read-only, possible) |

### 7. Proposed distinguishing test (read-only)

| Test | Procedure | Expected if OTP | Expected if shadow/latch | Expected if firmware |
|------|-----------|-----------------|-------------------------|---------------------|
| Reboot persistence | Read 0x021C04, warm reboot, read again | Same value | Same or different | May differ |
| Nearby register mirroring | Read 0x021C00–0x21CFF for mirror | No mirror | Nearby reg mirrors | No mirror |

### 8. Three propositions — status

| Proposition | Status | Evidence |
|-------------|--------|----------|
| Display is disabled in current environment | **PROVEN** | nvidia-smi, Nouveau -ENODEV, RM NV_ERR_NOT_SUPPORTED |
| Cause is at hardware level | **SUPPORTED** | Register is read-only (`R-I4R`), read before PDISP |
| Bit is raw OTP (permanent, unchangeable) | **UNPROVEN** | No OTP/fuse controller evidence |

**These three propositions are NOT equivalent.** Proving #1 does not prove #2 or #3.

## Ghi chú PONYTAIL

# ponytail: Nouveau and NVIDIA RM both read 0x021C04 and agree bit 0 = 1 = display disabled. Nouveau reads before PDISP; RM reads during display init. Source of 0x021C04 (OTP/shadow/firmware) is UNKNOWN. DCB type 0x06 = DisplayPort (not eDP). Three propositions (disabled/hardware/OTP) are distinct and must not be conflated.
