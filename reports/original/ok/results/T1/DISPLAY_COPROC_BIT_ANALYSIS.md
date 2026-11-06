# DISPLAY_COPROC_BIT_ANALYSIS.md

## Ket qua kiem toan BIT_BIOSDATA Module Map và cơ chế display

### 1. BIT_BIOSDATA Module Map External 0 bit 1 (Coproc Build)

**Không thể xác minh.** Lý do:
- Không tìm thấy chữ ký "BITB" (BIOS Information Table) trong stock hoặc T4 VBIOS.
- Không có cấu trúc BIT chuẩn của NVIDIA để parse.
- Do đó không có "Module Map External" để kiểm tra bit 1 (Coproc Build).

### 2. SEC2 và Coprocessor

SEC2 (Secure Execution Coprocessor) là Falcon-based coprocessor của NVIDIA GPU. Dựa trên dmesg:

```
kgspCmp40SanitizeSec2AfterExploit: CMP40_COMPUTE_UNLOCK_V534: NATIVE_CLEANUP_DMEM_PRESERVED_PASS
s_clearCmp40Sec2ExploitDmem: CMP40_COMPUTE_UNLOCK_V526: FULL_DMEM_ZERO_PASS [0x00000000,0x00010000)
kgspBootstrap_TU102: CMP40_COMPUTE_UNLOCK_V274: FWSEC_COMPLETE_GSP_UNTOUCHED idx=96
```

- SEC2 được driver nvidia sử dụng trong quá trình khởi tạo CMP 40HX.
- SEC2 DMEM được zeroed sau exploit cmpunlocker.
- GSP được đánh dấu `UNTOUCHED` — không bị modify bởi SEC2.
- **Không có bằng chứng** SEC2 điều khiển trực tiếp display output (DP/DVI).

### 3. Fuse status 0x21C04

| Thanh ghi | Giá trị live | Nghĩa |
|---|---|---|
| 0x21C04 | 0x00000001 | Host gate FALSE (DATA=1 ≠ ENABLE encoding 0) |
| 0x0524 | 0x00000000 | Shadow/volatile, không phải OTP |
| 0x21C1C | 0x00000038 | Không đổi sau reboot |
| 0x21378 | 0x00000000 | Không đổi |
| 0x2174C | 0x00000001 | Không đổi |

**Kết luận:** Fuse display (0x21C04) không bị cmpunlocker tác động. Giá trị 1 ở 0x21C04 làm host gate thành FALSE → display không thể được enable qua đường host register.

### 4. GSP RmDisableDisplay

- GSP firmware 615.78.08 được load từ `gsp_tu10x.bin`.
- Dmesg cho thấy `FWSEC_COMPLETE_GSP_UNTOUCHED` — GSP không bị modify.
- Không có bằng chứng `RmDisableDisplay` được gọi hoặc bypass được.
- SEC2 exploit trong cmpunlocker chỉ phục hồi compute (SS0/SS1), không ảnh hưởng display.

### 5. PDISP / SOR trạng thái

Từ nvidia-smi và dmesg trước đó:
- `Display Attached: No`
- `Display Active: Disabled`
- `card0-DP-1 connected` thuộc card khác (04:00.0), không phải CMP 40HX (03:00.0)
- CMP 40HX "has no normal display outputs" (theo cmpunlocker compatibility.md)

### 6. Đối chiếu: VBIOS → fuse → GSP → PDISP

| Bước | Bý chứng | Kết luận |
|---|---|---|
| VBIOS stock có DCB | Có (2 DCB, version 170, 0 entries) | Không thể kết luận có display output |
| VBIOS t4 bị cắt | Bỏ hết vùng display-critical | T4 không dùng được cho CMP 40HX |
| Fuse 0x21C04 = 1 | Live read on target | Host gate FALSE, display bị khóa |
| GSP 615.78.08 | Loaded, UNTOUCHED | Không có RmDisableDisplay bypass |
| SEC2 | Embedded in ucodes_tu10x.bin, dùng trong cmpunlocker | Chỉ phục hồi compute, không mở display |
| PDISP/SOR | Display Attached: No, Display Active: Disabled | CMP 40HX không có display output 정상 |

**Kết luận tổng thể:** Không có bằng chứng VBIOS modification có thể thay đổi fuse 0x21C04. SEC2 là Falcon coprocessor dùng trong cmpunlocker compute path, không liên quan trực tiếp đến display. GSP không bị modify. Display của CMP 40HX bị khóa ở mức fuse/hardware, không phải VBIOS hay SEC2.

## Ghi chú PONYTAIL

# ponytail: No BITB header found → cannot verify Coproc Build bit. SEC2 is Falcon coproc used in cmpunlocker compute path only, not display. Fuse 0x21C04=1 → host gate FALSE. GSP UNTOUCHED. VBIOS DCB version 170 with 0 entries → no valid display config. Display locked at fuse/hardware level, not VBIOS/SEC2.
