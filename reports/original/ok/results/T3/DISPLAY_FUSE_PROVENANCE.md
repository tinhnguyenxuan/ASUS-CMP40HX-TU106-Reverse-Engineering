# DISPLAY_FUSE_PROVENANCE.md

## Nguồn gốc của thanh ghi 0x21C04 trên TU106

### 1. Định nghĩa trong source driver 615.78.08

| File | Đường dẫn | Định nghĩa 0x21C04? |
|------|-----------|---------------------|
| src/common/inc/swref/published/turing/tu102/dev_fuse.h | .../turing/tu102/ | **KHÔNG** |
| src/common/inc/swref/published/maxwell/gm107/dev_fuse.h | .../maxwell/gm107/ | **CÓ**: NV_FUSE_STATUS_OPT_DISPLAY = 0x00021C04 |
| src/common/inc/swref/published/ampere/ga100/dev_fuse.h | .../ampere/ga100/ | **CÓ**: NV_FUSE_STATUS_OPT_DISPLAY = 0x00820C04 |

**TU106 (turing/tu102) KHÔNG định nghĩa 0x21C04** trong dev_fuse.h. Tuy nhiên, driver gán `gpuFuseSupportsDisplay_GM107` cho TU106 qua HAL dispatch (g_gpu_nvoc.c:2097-2100):

```
ChipHal: TU102 | TU104 | TU106 | TU116 | TU117 → gpuFuseSupportsDisplay_GM107
```

### 2. Triển khai gpuFuseSupportsDisplay_GM107

```c
// src/nvidia/src/kernel/gpu/arch/maxwell/kern_gpu_gm107.c:64-72
NvBool gpuFuseSupportsDisplay_GM107(OBJGPU *pGpu)
{
    return GPU_FLD_TEST_DRF_DEF(pGpu, _FUSE, _STATUS_OPT_DISPLAY, _DATA, _ENABLE);
}
```

Đọc từ `pGpu + NV_FUSE_STATUS_OPT_DISPLAY` = `primary_fuse_base + 0x21C04`, kiểm tra field DATA (bit 0) có bằng _ENABLE (0x00000000) hay không.

### 3. Live read trên target <REDACTED_LAB_IP>

| Thanh registros | Giá trị live | Ghi chú |
|-----------------|--------------|---------|
| 0x21C04 | 0x00000001 | DATA bit 0 = 1 ≠ ENABLE(0) → host gate FALSE |
| 0x0524 | 0x00000000 | Shadow/volatile, không phải OTP |
| 0x21378 | 0x00000000 | NVDEC_DISABLE (đã định nghĩa trong tu102/dev_fuse.h) |
| 0x2174C | 0x00000001 | SECURE_GSP_DEBUG_DIS (đã định nghĩa trong tu102/dev_fuse.h) |

### 4. Phân loại nguồn 0x21C04

| Nguồn giả định | Bý chứng ủng hộ | Bý chứng phản đối | Kết luận |
|---------------|-------------------|---------------------|----------|
| **Raw OTP** | Driver đọc qua fuse HAL; địa chỉ 0x21C04 trùng với gm107 | tu102/dev_fuse.h không định nghĩa; không có mã nạp OTP vào thanh ghi này | **UNKNOWN** |
| **Shadow/latch** | Giá trị 0x00000001 có thể là shadow sau khi firmware đọc OTP | Không có mã driver ghi vào 0x21C04; không thể phân biệt từ live read | **UNKNOWN** |
| **Firmware-originated** | SEC2/GSP có thể ghi giá trị này khi khởi tạo; GSP log có tham chiếu SEC2 | Không tìm thấy mã GSP ghi 0x21C04 trong kernel source | **UNKNOWN** |

### 5. Bý chứng từ dmesg (read-only)

```
kgspCmp40SanitizeSec2AfterExploit: CMP40_COMPUTE_UNLOCK_V534: NATIVE_CLEANUP_DMEM_PRESERVED_PASS
s_clearCmp40Sec2ExploitDmem: CMP40_COMPUTE_UNLOCK_V526: FULL_DMEM_ZERO_PASS [0x00000000,0x00010000)
kgspBootstrap_TU102: CMP40_COMPUTE_UNLOCK_V274: FWSEC_COMPLETE_GSP_UNTOUCHED idx=96
```

SEC2 được dùng trong cmpunlocker compute path, GSP được đánh dấu UNTOUCHED. Không có bằng chứng SEC2/GSP ghi vào 0x21C04.

### 6. Kết luận

**0x21C04 trên TU106 là UNKNOWN nguồn.** Không thể kết luận "raw OTP vĩnh viễn" vì:
1. tu102/dev_fuse.h không khai báo thanh ghi này
2. Không có mã driver/firmware ghi vào 0x21C04
3. Live read = 1 nhưng không phân biệt được OTP vs shadow vs firmware

Theo yêu cầu T3: **Việc tu102/dev_fuse.h không khai báo register không phải bằng chứng nó không thuộc fuse controller.** Tuy nhiên, cũng không có bằng chứng ngược lại.

## Ghi chú PONYTAIL

# ponytail: 0x21C04 live = 1 trên TU106, driver đọc qua gpuFuseSupportsDisplay_GM107. Nguồn (OTP/shadow/firmware) là UNKNOWN. Không kết luận "hard-fused vĩnh viễn" ohne bằng chứng OTP trực tiếp.
