# T5_FUSE_PRODUCER_EVIDENCE.md

## Fuse Producer Evidence — Source of 0x021C04 on TU106

### 1. Register definition gap

| Header file | Path | Defines 0x21C04? | Defines what? |
|-------------|------|-----------------|---------------|
| `src/common/inc/swref/published/turing/tu102/dev_fuse.h` | .../turing/tu102/ | **NO** | 0x2174C (SECURE_GSP_DEBUG_DIS), 0x21378 (NVDEC_DISABLE) |
| `src/common/inc/swref/published/maxwell/gm107/dev_fuse.h` | .../maxwell/gm107/ | **YES** | 0x21C04 (STATUS_OPT_DISPLAY) |
| `src/common/inc/swref/published/ampere/ga100/dev_fuse.h` | .../ampere/ga100/ | **YES** | 0x820C04 (STATUS_OPT_DISPLAY) |

**tu102/dev_fuse.h does not declare 0x21C04.** This does NOT prove the register doesn't exist — it only proves NVIDIA didn't publish a named definition for Turing.

### 2. MMIO read path (confirmed)

| Component | Address | Source |
|-----------|---------|--------|
| Register BAR base | 0 (for TU106, `gpuGetPrimaryFuseBaseAddr_b2b553` returns 0) | g_gpu_nvoc.h:5828 |
| Register offset | 0x21C04 | gm107/dev_fuse.h:27 |
| Absolute MMIO address | 0x21C04 | Computed: 0 + 0x21C04 |
| Read function | `GPU_REG_RD32(pGpu, 0x21C04)` | kern_gpu_gm107.c:71 |

### 3. What we searched for (and did NOT find)

| Search | Result |
|--------|--------|
| Code that writes 0x21C04 in kernel source | Not found |
| Code that initializes 0x21C04 from OTP in kernel source | Not found |
| tu102/dev_fuse.h definition of 0x21C04 | Not present |
| GSP firmware code reading/writing 0x21C04 | Not found in kernel source |
| SEC2 firmware reference to 0x21C04 | Not found |
| Nouveau producer of 0x021c04 | Nouveau only READS it; no writer found |

### 4. Producer hypotheses (all UNVERIFIED)

| Hypothesis | Evidence for | Evidence against | Verdict |
|------------|-------------|-------------------|---------|
| **Raw OTP fuse** | Register is read-only (`R-I4R` per gm107 header); matches pattern of fuse status registers | No OTP read path found in source; tu102/dev_fuse.h doesn't define it | UNKNOWN |
| **Hardware shadow/latch** | Value persists across reboots (live read = 1 consistently) | No latch mechanism found in source | UNKNOWN |
| **Firmware-initialized** | SEC2/GSP could set it during early init | dmesg shows `FWSEC_COMPLETE_GSP_UNTOUCHED`; no writer found | UNKNOWN |
| **Strap/config pin** | No evidence | No strap reference to 0x21C04 | UNKNOWN |

### 5. Mắt xích thiếu (missing link)

| Missing evidence | Where to check |
|-----------------|----------------|
| OTP/eFuse array read path to status register | NVIDIA GPU fuse controller documentation (not in open source) |
| Firmware/devinit code that sets 0x21C04 at boot | GSP firmware binary (not open source), VBIOS init tables |
| Whether 0x21C04 is writable from host | Would require MMIO write test (prohibited by constraints) |
| Whether 0x21C04 changes across reboots | Requires multiple live reads (possible, read-only) |

### 6. Proposed distinguishing test (read-only)

```
Test: Read 0x21C04 before and after warm reboot
Expected if OTP: Same value both times (OTP is permanent)
Expected if shadow/latch: May differ if latch is reset
Expected if firmware: May differ if firmware re-initializes

Test: Read 0x21C04 value, compare with fuse shadow register if any exists at nearby offsets (0x21C00–0x21CFF)
Expected if shadow: A nearby register mirrors 0x21C04
```

### 7. What we CANNOT conclude

| Claim | Status | Reason |
|-------|--------|--------|
| "0x21C04 is raw OTP" | UNPROVEN | No OTP read path in source |
| "0x21C04 is permanent hardware fuse" | UNPROVEN | No latch/fuse controller documentation |
| "0x21C04 is set by firmware" | UNPROVEN | No firmware writer found |
| "0x21C04 cannot be changed" | UNPROVEN | No write test performed (and prohibited) |

## Ghi chú PONYTAIL

# ponytail: 0x21C04 producer is UNKNOWN. tu102/dev_fuse.h doesn't define it (only gm107 does). No writer found in kernel source. Nouveau and RM both only READ it. Cannot conclude OTP/shadow/firmware without additional evidence. Proposed: read-only test comparing value before/after warm reboot.
