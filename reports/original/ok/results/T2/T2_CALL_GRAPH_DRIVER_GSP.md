# T2_CALL_GRAPH_DRIVER_GSP.md

## CALL GRAPH DRIVER VÀ GSP — PHÂN BIẾN GATE ĐỘC LẬP / PHỤ THUỘC / CHƯA BIẁT

### 1. gpuFuseSupportsDisplay_HAL — HAL assignment cho TU106

Từ `src/nvidia/generated/g_gpu_nvoc.c` (dòng 2097-2115):

```
ChipHal: TU102 | TU104 | TU106 | TU116 | TU117 → gpuFuseSupportsDisplay_GM107
ChipHal: GA102 | GA103 | GA104 | GA106 | GA107 | AD102 | AD103 | AD104 | AD106 | AD107 → gpuFuseSupportsDisplay_GA100
ChipHal: GB20B | GB20C | T234D | T239D | T264D → gpuFuseSupportsDisplay_e661f0 (return NV_TRUE)
ChipHal: GB10B | GB10C | GB202 | GB203 | GB205 | GB206 | GB207 → gpuFuseSupportsDisplay_GB100
else → gpuFuseSupportsDisplay_d69453 (return NV_FALSE)
```

**TU106 dùng `gpuFuseSupportsDisplay_GM107`** (từ `src/nvidia/src/kernel/gpu/arch/maxwell/kern_gpu_gm107.c`, dòng 64-72):

```c
NvBool gpuFuseSupportsDisplay_GM107(OBJGPU *pGpu)
{
    return GPU_FLD_TEST_DRF_DEF(pGpu, _FUSE, _STATUS_OPT_DISPLAY, _DATA, _ENABLE);
}
```

Đọc từ `NV_FUSE_STATUS_OPT_DISPLAY = 0x00021C04` (đã định nghĩa trong `src/common/inc/swref/published/maxwell/gm107/dev_fuse.h`).

**Quan trọng:** `src/common/inc/swref/published/turing/tu102/dev_fuse.h` **KHÔNG định nghĩa** `NV_FUSE_STATUS_OPT_DISPLAY` tại 0x21C04. Nó chỉ định nghĩa:
- `NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS = 0x0002174C`
- `NV_FUSE_OPT_NVDEC_DISABLE = 0x00021378`

Do đó, TU106 tái dụng định nghĩa fuse từ Maxwell (gm107) cho cờ display. Đây là **sự khác biệt kiến trúc** — fuse address 0x21C04 trên TU106 có thể không có ý nghĩa OTP tương tự như trên Maxwell.

### 2. Các consumer của gpuFuseSupportsDisplay_HAL

| File | Dòng | Mã | Ý nghĩa |
|------|------|-----|---------|
| `src/nvidia/src/kernel/gpu/disp/kern_disp.c` | 444 | `if (!gpuFuseSupportsDisplay_HAL(pGpu)) return NV_ERR_NOT_SUPPORTED;` | Khởi tạo display bị chặn nếu fuse không enable |
| `src/nvidia/src/kernel/gpu/gsp/arch/turing/kernel_gsp_tu102.c` | 1361 | `if (gpuFuseSupportsDisplay_HAL(pGpu) && kdispGetVgaWorkspaceBase(...))` | VGA workspace layout chỉ tính khi fuse enable |

### 3. KernelDisplay presence check

`src/nvidia/src/kernel/gpu/disp/disp_objs.c` dòng 95:
```c
// Check display is enabled (i.e. not displayless)
pKernelDisplay = GPU_GET_KERNEL_DISPLAY(pGpu);
if (pKernelDisplay == NULL)
{
    return NV_ERR_NOT_SUPPORTED;
}
```

`src/nvidia/src/kernel/gpu/gpu.c` dòng 1929-1945:
- `gpuIsGridDisplaylessClassSupported()` trả về `NV_FALSE` nếu `KernelDisplay != NULL` (hai lớp loại trừ nhau)
- `NVA083_GRID_DISPLAYLESS` chỉ hỗ trợ trên GRID board không có display engine

`src/nvidia/src/kernel/gpu/arch/turing/kern_gpu_tu102.c` dòng 195:
- TU106 có **cả** `GPU_CHILD_PRESENT(KernelDisplay, 1)` **và** `GPU_CHILD_PRESENT(OBJGRIDDISPLAYLESS, 1)`

### 4. Phân loại gate

| Gate | Loại | Nguồn | Thành phần |
|------|------|-------|------------|
| Fuse 0x21C04 DATA bit | Độc lập | `gpuFuseSupportsDisplay_HAL()` → `kern_disp.c:444`, `kernel_gsp_tu102.c:1361` | VGA workspace + display init |
| KernelDisplay != NULL | Phụ thuộc fuse | `disp_objs.c:95` | Display API init |
| OBJGRIDDISPLAYLESS vs KernelDisplay | Loại trừ nhau | `gpu.c:1945` | Class DB mutual exclusion |
| BIT token U (NO_DISPLAY_SUBSYSTEM=1) | Chưa biết | Không tìm thấy consumer trong driver source | Không có mã driver đọc BIT token U trực tiếp |
| DCB entry_count=0 | Không được dùng | Không tìm thấy consumer trong driver source | Driver không parse DCB từ VBIOS |

### 5. Dữ liệu chưa biết (UNKNOWN)

1. **BIT token U consumer:** Không có mã driver trong `open-gpu-kernel-modules-615.78.08` đọc trực tiếp BIT token U (tag 0x55) từ VBIOS. Không rõ cờ NO_DISPLAY_SUBSYSTEM trong BIT có ảnh hưởng đến driver hay không.
2. **DCB consumer:** Không có mã driver parse DCB từ VBIOS image. DCB có thể được đọc bởi userspace (nvidia-settings, X driver) không phải kernel module.
3. **Fuse 0x21C04 trên TU106:** `tu102/dev_fuse.h` không định nghĩa fuse này. Địa chỉ được tái dụng từ gm107. Không rõ 0x21C04 trên TU106 là raw OTP, shadow/latch, hay firmware config.
4. **GSP RmDisableDisplay:** Không tìm thấy mã `RmDisableDisplay` trong kernel module source. Có thể nằm trong GSP firmware (không có source).

## Ghi chú PONYTAIL

# ponytail: TU106 tái dụng gpuFuseSupportsDisplay_GM107 (đọc fuse 0x21C04) nhưng tu102/dev_fuse.h không định nghĩa fuse này. Hai consumer kernel: kern_disp.c:444 và kernel_gsp_tu102.c:1361. Không tìm thấy consumer cho BIT token U hay DCB trong kernel source. Fuse 0x21C04 trên TU106 là UNKNOWN (OTP/shadow/firmware).
