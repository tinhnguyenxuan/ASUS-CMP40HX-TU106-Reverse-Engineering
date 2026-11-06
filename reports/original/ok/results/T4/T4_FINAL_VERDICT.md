# T4_FINAL_VERDICT.md

## T4 FINAL VERDICT — CMP 40HX TU106 DISPLAYLESS CONFIGURATION & FUSE PROVENANCE

### 1. VBIOS Structural Validation (Nhánh A)

| Mục | Kết quả | Bý chứng |
|-----|---------|-----------|
| BIT checksum | PROVEN | Checksum byte 0x46, mod 256 = 0, tất cả 5 ROM |
| BIT token count | PROVEN | 17 tokens (không phải 6 như T3 sai) |
| Token U offset | PROVEN | CMP: 0x03CE → file 0x289CE; GeForce: 0x03A2 → file 0x289A2 |
| Token U NO_DISPLAY_SUBSYSTEM | SUPPORTED | CMP: DCF=0x02, bit1=1; GeForce: DCF=0x00, bit1=0 |
| BIOSDATA B length | PROVEN | 37 bytes (layout công khai 33 byte + 4 byte dự phòng) |
| B+32 byte | PROVEN | CMP=0x12 (bit1=1), GeForce=0x10 (bit1=0) |
| B+35 byte | PROVEN | 0x01 trên tất cả ROM |
| B+32 = Coproc Build | UNKNOWN | Giả thuyết, chưa có tài liệu NVIDIA xác nhận |
| DCB signature location | PROVEN | DCB+6 (không phải DCB+0) |
| DCB entry_count | PROVEN | CMP=0, GeForce=16 |
| DCB real connectors (GeForce) | PROVEN | 7 entries (0-6), entries 7-15 unused |
| DCB entry_count vs "16 connectors" | CORRECTED | 16 entries ≠ 16 connectors; chỉ 7 có pointer thực |

### 2. Fuse Provenance (Nhánh B)

| Câu hỏi | Verdict | Bý chứng |
|---------|---------|-----------|
| Driver đọc fuse 0x21C04? | SUPPORTED | kern_disp.c:444, kernel_gsp_tu102.c:651, g_gpu_nvoc.c:2097 |
| TU106 dùng GM107 fuse HAL? | SUPPORTED | g_gpu_nvoc.c:2097: TU106 → gpuFuseSupportsDisplay_GM107 |
| tu102/dev_fuse.h định nghĩa 0x21C04? | PROVEN (không) | Chỉ định nghĩa 0x2174C và 0x21378 |
| Fuse 0x21C04 live = 0x00000001 | PROVEN | Read-only MMIO read trên target |
| Fuse 0x21C04 là raw OTP? | UNKNOWN | Không có bằng chứng trực tiếp |
| Fuse 0x21C04 là shadow/latch? | UNKNOWN | Không thể phân biệt từ live read |
| Fuse 0x21C04 là firmware config? | UNKNOWN | GSP UNTOUCHED per dmesg |
| cmpunlocker thay đổi 0x21C04? | SUPPORTED (không) | T09: fuse vẫn = 1 sau unlock |

### 3. Display Policy Dependency (Nhánh C)

| Câu hỏi | Verdict | Bý chứng |
|---------|---------|-----------|
| Direct host consumer of fuse 0x21C04? | SUPPORTED | kern_disp.c:444 (display init blocked) |
| Firmware-adjacent consumer? | SUPPORTED | kernel_gsp_tu102.c:651 (VGA workspace) |
| BIT Token U consumer kernel? | UNKNOWN (không tìm thấy) | Không có mã trong source 615.78.08 |
| BIOSDATA B consumer kernel? | UNKNOWN (không tìm thấy) | Không có mã trong source 615.78.08 |
| SEC2 điều khiển trực tiếp display? | UNKNOWN | Không tìm thấy liên hệ trực tiếp |
| GSP firmware hash | PROVEN | 0c6124c11d59900a05ab5461e5fc7087fc6687a1badead49a7eeca6ed13eeb3b |

### 4. Bảng verdict tổng thể

| Câu hỏi | Verdict |
|---------|---------|
| CMP VBIOS có cờ NO_DISPLAY_SUBSYSTEM=1? | SUPPORTED |
| GeForce VBIOS có cờ NO_DISPLAY_SUBSYSTEM=0? | SUPPORTED |
| Driver gate display qua fuse 0x21C04? | SUPPORTED |
| Fuse 0x21C04 là raw OTP? | UNKNOWN |
| Display bị hard-fused vĩnh viễn? | UNKNOWN |
| SEC2 điều khiển trực tiếp display? | UNKNOWN |
| VBIOS modification có thể mở display? | UNKNOWN |
| DCB là nguồn duy nhất quyết định display? | SUPPORTED (không) — GeForce U=0 có DCB entries, CMP U=1 không có entries |
| Coproc Build tại B+32? | UNKNOWN |

### 5. Kết luận cuối cùng

1. **CMP 40HX VBIOS có cờ NO_DISPLAY_SUBSYSTEM=1** (BIT Token U, DCF=0x02). GeForce ROMs không có cờ này.

2. **CMP VBIOS DCB entry_count = 0** (không có connector entries). GeForce có 16 entries nhưng chỉ 7 entries thực (có pointer), 9 entries unused.

3. **Driver gate display qua fuse 0x21C04** (đọc bởi gpuFuseSupportsDisplay_GM107). Live read = 0x00000001 → host gate FALSE.

4. **Không thể kết luận "hard-fused vĩnh viễn"** vì nguồn 0x21C04 (OTP/shadow/firmware) là UNKNOWN. tu102/dev_fuse.h không định nghĩa thanh ghi này.

5. **SEC2 không được chứng minh có liên hệ trực tiếp với đường quyết định display.** SEC2 dùng trong cmpunlocker compute path, GSP UNTOUCHED.

6. **BIT Token U và BIOSDATA B không có consumer kernel** được xác định. Có thể được đọc bởi userspace driver.

### 6. File đầu ra T4

| File | Nội dung |
|------|----------|
| `results/T4/BIT_VALIDATED_ALL_ROMS.json` | Dữ liệu BIT + DCB parsed từ 5 ROM |
| `results/T4/BIOSDATA_B_LAYOUT.md` | Layout BIOSDATA v2 37 byte, B+32/B+35 phân tích |
| `results/T4/DCB_POINTER_VALIDATION.md` | DCB con trỏ, cấu trúc, entries |
| `results/T4/DISPLAY_FUSE_PROVENANCE.md` | Nguồn 0x21C04, phân loại UNKNOWN |
| `results/T4/DISPLAY_GATE_DEPENDENCY_GRAPH.md` | Đồ thị 4 gate, phân biệt độc lập/phụ thuộc |
| `results/T4/T4_FINAL_VERDICT.md` | Tổng kết verdict bảng |

### 7. Ràng buộc đã tuân thủ

- ❌ Không flash ROM
- ❌ Không ghi MMIO
- ❌ Không sửa OTP/RIR
- ❌ Không reset GPU
- ✅ Chỉ phân tích offline và đọc phần cứng read-only đã kiểm toán

## Ghi chú PONYTAIL

# ponytail: T4 hoàn tất. CMP có NO_DISPLAY_SUBSYSTEM=1, DCB entries=0. Fuse 0x21C04 live=1 (gate FALSE) nhưng nguồn UNKNOWN. 6 file đầu ra đã ghi.
