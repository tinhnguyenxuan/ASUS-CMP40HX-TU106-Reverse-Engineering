# T2_FUSE_RAW_VS_EFFECTIVE.md

## BẢNG RAW FUSE vs EFFECTIVE FUSE — 0x21C04 trên CMP 40HX

### 1. Live fuse reads từ target <REDACTED_LAB_IP>

| Thanh ghi | Giá trị live | Ghi chú |
|-----------|--------------|---------|
| 0x21C04 | 0x00000001 | Host gate FALSE (DATA=1 ≠ ENABLE encoding 0) |
| 0x0524 | 0x00000000 | Shadow/volatile, không phải OTP |
| 0x21C1C | 0x00000038 | Không đổi sau reboot |
| 0x21378 | 0x00000000 | NVDEC_DISABLE (đã định nghĩa trong tu102/dev_fuse.h) |
| 0x2174C | 0x00000001 | SECURE_GSP_DEBUG_DIS (đã định nghĩa trong tu102/dev_fuse.h) |

### 2. Định nghĩa fuse trong tu102/dev_fuse.h

Chỉ có 2 fuse được định nghĩa cho Turing (tu102):

| Định nghĩa | Địa chỉ | Bits | Mô tả |
|------------|---------|------|-------|
| NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS | 0x0002174C | 0:0 | GSP debug disable |
| NV_FUSE_OPT_NVDEC_DISABLE | 0x00021378 | 2:0 | NVDEC disable |

**0x21C04 (NV_FUSE_STATUS_OPT_DISPLAY) KHÔNG được định nghĩa trong tu102/dev_fuse.h.** Nó chỉ xuất hiện trong gm107/dev_fuse.h (Maxwell) và ga100/dev_fuse.h (Ampere).

### 3. Raw fuse vs Effective fuse

| Hạng | Raw fuse (OTP) | Effective fuse (sau shadow/latch/firmware) |
|------|----------------|--------------------------------------------|
| 0x21C04 | UNKNOWN (không đọc được trực tiếp OTP) | 0x00000001 (live read qua MMIO) |
| 0x0524 | UNKNOWN | 0x00000000 (shadow/volatile, thay đổi sau reboot) |
| 0x21378 | UNKNOWN | 0x00000000 |
| 0x2174C | UNKNOWN | 0x00000001 |

### 4. Bý chứng về nguồn 0x21C04

1. **Driver đọc 0x21C04** qua `gpuFuseSupportsDisplay_GM107()` trên TU106 (HAL dispatch).
2. **tu102/dev_fuse.h không định nghĩa 0x21C04** → không phải fuse OTP chuẩn của Turing.
3. **Live read 0x21C04 = 0x00000001** → thanh ghi này tồn tại và có thể đọc được.
4. **Không có bằng chứng** 0x21C04 là raw OTP bit. Có thể là:
   - Raw OTP fuse bit (khả năng cao nếu NVIDIA reuse địa chỉ từ Maxwell)
   - Shadow register (được firmware set sau khi đọc OTP)
   - Firmware config (GSP/SEC2 ghi giá trị này khi khởi tạo)
5. **cmpunlocker không thay đổi 0x21C04** (xác thực từ T09: fuse không đổi sau unlock).

### 5. Phân loại

| Câu hỏi | Phân loại | Bý chứng |
|---------|-----------|------------|
| 0x21C04 là raw OTP? | UNKNOWN | tu102/dev_fuse.h không định nghĩa; live read = 1 nhưng không chứng minh nguồn OTP |
| 0x21C04 là shadow/latch? | UNKNOWN | Không có mã driver ghi vào 0x21C04; không thể phân biệt shadow vs OTP từ live read |
| 0x21C04 là firmware config? | UNKNOWN | SEC2/GSP có thể ghi giá trị này; không có bằng chứng trực tiếp |
| cmpunlocker thay đổi 0x21C04? | SUPPORTED (không thay đổi) | T09: fuse vẫn = 1 sau unlock |
| 0x21C04 gate display? | SUPPORTED | `gpuFuseSupportsDisplay_HAL()` đọc 0x21C04, nếu ≠ ENABLE(0) → trả về NOT_SUPPORTED |

## Ghi chú PONYTAIL

# ponytail: 0x21C04 live = 1 trên TU106, nhưng tu102/dev_fuse.h không định nghĩa fuse này. Nguồn (OTP/shadow/firmware) là UNKNOWN. Driver đọc thanh ghi này để gate display init. Không thể kết luận "hard-fused vĩnh viễn" ohne bằng chứng trực tiếp về nguồn OTP.
