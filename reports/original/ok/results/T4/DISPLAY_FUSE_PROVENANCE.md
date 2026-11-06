# DISPLAY_FUSE_PROVENANCE.md

## Nguồn gốc của thanh ghi 0x21C04 trên TU106

### 1. Định nghĩa trong source driver 615.78.08

| File | Đường dẫn | Định nghĩa 0x21C04? |
|------|-----------|---------------------|
| src/common/inc/swref/published/turing/tu102/dev_fuse.h | .../turing/tu102/ | **KHÔNG** |
| src/common/inc/swref/published/maxwell/gm107/dev_fuse.h | .../maxwell/gm107/ | **CÓ**: `NV_FUSE_STATUS_OPT_DISPLAY = 0x00021C04` |

`tu102/dev_fuse.h` chỉ định nghĩa 2 fuse:
- `NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS = 0x0002174C`
- `NV_FUSE_OPT_NVDEC_DISABLE = 0x00021378`

**0x21C04 KHÔNG được định nghĩa trong tu102/dev_fuse.h.** Nó chỉ xuất hiện trong gm107 (Maxwell) và t23x/ga100 (Ampere+).

### 2. Đọc fuse qua HAL dispatch

`g_gpu_nvoc.c:2097` (HAL assignment):
```
ChipHal: TU102 | TU104 | TU106 | TU116 | TU117 → gpuFuseSupportsDisplay_GM107
```

TU106 tái dụng hàm đọc fuse của GM107 (Maxwell):

```c
// src/nvidia/src/kernel/gpu/arch/maxwell/kern_gpu_gm107.c:64-72
NvBool gpuFuseSupportsDisplay_GM107(OBJGPU *pGpu)
{
    return GPU_FLD_TEST_DRF_DEF(pGpu, _FUSE, _STATUS_OPT_DISPLAY, _DATA, _ENABLE);
}
```

`GPU_FLD_TEST_DRF_DEF` đọc thanh ghi qua MMIO tại `fuse_base + 0x21C04`, kiểm tra field DATA (bit 0) có bằng `_ENABLE = 0x00000000` hay không.

### 3. Live read trên target <REDACTED_LAB_IP>

| Thanh ghi | Giá trị live | Ghi chú |
|-----------|--------------|---------|
| 0x21C04 | 0x00000001 | DATA bit 0 = 1 ≠ ENABLE(0) → host gate FALSE |
| 0x0524 | 0x00000000 | Shadow/volatile, không phải OTP |
| 0x21378 | 0x00000000 | NVDEC_DISABLE (đã định nghĩa trong tu102/dev_fuse.h) |
| 0x2174C | 0x00000001 | SECURE_GSP_DEBUG_DIS (đã định nghĩa trong tu102/dev_fuse.h) |

### 4. Phân loại nguồn 0x21C04

| Nguồn giả định | Bý chứng ủng hộ | Bý chứng phản đối | Kết luận |
|---------------|-------------------|---------------------|----------|
| **Raw OTP** | Driver đọc qua fuse HAL; địa chỉ trùng gm107 | tu102/dev_fuse.h không định nghĩa; không có mã nạp OTP | **UNKNOWN** |
| **Shadow/latch** | Giá trị 0x00000001 có thể là shadow | Không có mã driver ghi vào 0x21C04; không thể phân biệt từ live read | **UNKNOWN** |
| **Firmware-originated** | SEC2/GSP có thể ghi khi khởi tạo | Không tìm thấy mã ghi 0x21C04 trong kernel source | **UNKNOWN** |

### 5. Bý chứng từ dmesg (read-only)

```
kgspCmp40SanitizeSec2AfterExploit: CMP40_COMPUTE_UNLOCK_V534: NATIVE_CLEANUP_DMEM_PRESERVED_PASS
s_clearCmp40Sec2ExploitDmem: CMP40_COMPUTE_UNLOCK_V526: FULL_DMEM_ZERO_PASS [0x00000000,0x00010000)
kgspBootstrap_TU102: CMP40_COMPUTE_UNLOCK_V274: FWSEC_COMPLETE_GSP_UNTOUCHED idx=96
```

SEC2 dùng trong cmpunlocker compute path, GSP UNTOUCHED. Không có bằng chứng SEC2/GSP ghi vào 0x21C04.

### 6. GSP firmware (dùng cho đối chiếu)

| Firmware | SHA-256 | Kích thước |
|----------|---------|------------|
| gsp_tu10x.bin | 0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b | 22,901,632 bytes |
| gsp_ga10x.bin | a20100cafd5a85e22b3e13188339730c6ced94bd5f654984dd2ed274ed58d584 | 27,043,992 bytes |
| ucodes_tu10x.bin | 6027ab3736f733b5a06e6e61aaae957d1f990426a263849ebcfa8a49eeb4a5d0 | 8,837,632 bytes |

### 7. Kết luận

**0x21C04 trên TU106 là UNKNOWN nguồn.** Không thể kết luận "raw OTP vĩnh viễn" vì:
1. tu102/dev_fuse.h không khai báo thanh ghi này
2. Không có mã driver/firmware ghi vào 0x21C04 trong source có sẵn
3. Live read = 0x00000001 nhưng không phân biệt được OTP vs shadow vs firmware

Theo yêu cầu T3: **Việc tu102/dev_fuse.h không khai báo register không phải bằng chứng nó không thuộc fuse controller.** Tuy nhiên, cũng không có bằng chứng ngược lại.

## Ghi chú PONYTAIL

# ponytail: 0x21C04 live=1 trên TU106, driver đọc qua gpuFuseSupportsDisplay_GM107. Nguồn là UNKNOWN. Không kết luận "hard-fused vĩnh viễn" ohne bằng chứng OTP trực tiếp.
