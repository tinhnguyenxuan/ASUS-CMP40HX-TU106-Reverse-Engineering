# T2_CORRECTED_FINDINGS.md

## TÌNH HÌNH SAU KHI SỬA T1 — T2 INDEPENDENT TU106 DISPLAY POLICY INVESTIGATION

### 1. Sửa các kết luận sai của T1

| Kết luận T1 (sai) | Sửa trong T2 | Bý chứng |
|-------------------|--------------|------------|
| "Display hard-fused, không thể thay đổi" | **Không kết luận được** — nguồn 0x21C04 là UNKNOWN | tu102/dev_fuse.h không định nghĩa 0x21C04; live read = 1 nhưng nguồn OTP/shadow/firmware chưa chứng minh |
| "SEC2 là RISC-V, disassembly Capstone hợp lệ" | **SEC2 là NVIDIA Falcon ISA** — toàn bộ disassembly Capstone RISC-V+C là FALSE DECODE | T1/SEC2_ISA_VALIDATION.md đã ghi rõ |
| "T4 là Tesla T4 TU104" | **Không có bằng chứng** — t4 chỉ là ROM cắt 495KB, không có provenance | T1/VBIOS_BIT_PCIR_COMPARISON.md |
| "DCB version 170 có ý nghĩa display" | **DCB entries=0, version không chuẩn** — không thể suy ra cấu hình display | T2_BIT_RAW_AND_DECODED.md |
| "GeForce ROMs không có sẵn để so sánh" | **Đã có 3 GeForce ROMs** (2× RTX 2060 SUPER, 1× RTX 2070) | T2_BIT_RAW_AND_DECODED.md |

### 2. Bý chứng chính mới

**A. BIT table:**
- CMP stock: 2 BIT locations (0x287B0, 0xA17B0), 6 entries mỗi tags: 0x11, 0x3E, 0x8F, 0xB7, 0xD4, 0xCC
- GeForce: 2 BIT locations (0x287B0, 0xA07B0), 6 entries mỗi tags: 0x11, 0x3E, 0x7F, 0xA7, 0xC4, 0xA0
- Không có ROM nào có tag 0x55 (U/DISPLAY_CTRL) làm BIT entry

**B. Token U data (0x289CE / 0xA19CE):**
- CMP stock: `00 00 02 00 00` → Display Control Flags = 0x02 → NO_DISPLAY_SUBSYSTEM bit 1 = 1
- GeForce: giá trị con trỏ khác (không có cờ này)
- Vị trí nằm trong vùng dữ liệu của BIT entry [1] (tag=0x3E)

**C. DCB:**
- CMP stock: 2 DCB (0x2D9B2, 0xA69B2), version=170, entries=0
- GeForce: 2 DCB, version=4, entries=0
- Cả hai đều có entry_count=0 → không có connector entries

**D. Driver/GSP call graph:**
- TU106 dùng `gpuFuseSupportsDisplay_GM107` → đọc fuse 0x21C04
- Hai consumer: `kern_disp.c:444` (display init) và `kernel_gsp_tu102.c:1361` (VGA workspace)
- `tu102/dev_fuse.h` **KHÔNG định nghĩa** 0x21C04 → nguồn fuse là UNKNOWN
- Không tìm thấy consumer cho BIT token U hay DCB trong kernel source

### 3. Bảng verdict theo PROVEN/SUPPORTED/UNKNOWN

| Câu hỏi | Verdict | Bý chứng |
|---------|---------|------------|
| CMP VBIOS có cờ NO_DISPLAY_SUBSYSTEM? | SUPPORTED | `00 00 02 00 00` tại 0x289CE/0xA19CE, Flags=0x02 bit1=1 |
| GeForce VBIOS có cờ NO_DISPLAY_SUBSYSTEM? | SUPPORTED (không) | Không có pattern tại vị trí tương đương |
| Driver đọc fuse 0x21C04 để gate display? | SUPPORTED | `gpuFuseSupportsDisplay_HAL()` trong kern_disp.c:444, kernel_gsp_tu102.c:1361 |
| Fuse 0x21C04 là raw OTP? | UNKNOWN | tu102/dev_fuse.h không định nghĩa; không có bằng chứng trực tiếp |
| Fuse 0x21C04 là shadow/latch? | UNKNOWN | Không thể phân biệt từ live read |
| Fuse 0x21C04 là firmware config? | UNKNOWN | SEC2/GSP có thể ghi; không có bằng chứng trực tiếp |
| cmpunlocker thay đổi 0x21C04? | SUPPORTED (không) | T09: fuse vẫn = 1 sau unlock |
| SEC2 điều khiển trực tiếp display? | UNKNOWN | Không tìm thấy liên hệ trực tiếp trong driver source |
| VBIOS modification có thể mở display? | UNKNOWN | Không có bằng chứng; DCB entries=0 cả CMP và GeForce |
| Display CMP 40HX bị hard-fused? | UNKNOWN | Không có bằng chứng trực tiếp về nguồn OTP của 0x21C04 |

### 4. Kết luận chính thức (T2)

1. **CMP 40HX VBIOS có cờ NO_DISPLAY_SUBSYSTEM** (Display Control Flags = 0x02) trong dữ liệu BIT entry [1] tại 0x289CE/0xA19CE. GeForce ROMs không có cờ này.

2. **Driver gate display qua fuse 0x21C04** (đọc bởi `gpuFuseSupportsDisplay_GM107` trên TU106). Nếu DATA ≠ ENABLE(0), display init bị chặn với `NV_ERR_NOT_SUPPORTED`.

3. **0x21C04 live = 0x00000001** → host gate FALSE → display không thể init qua kernel path.

4. **Không thể kết luận "hard-fused vĩnh viễn"** vì tu102/dev_fuse.h không định nghĩa 0x21C04. Nguồn của thanh ghi này (OTP raw, shadow/latch, hoặc firmware config) là UNKNOWN.

5. **SEC2 không được chứng minh có liên hệ trực tiếp với đường quyết định display.** SEC2 được dùng trong cmpunlocker compute path, GSP UNTOUCHED.

6. **Cần thêm bằng chứng** để xác định nguồn 0x21C04 trước khi kết luận display không thể mở được.

### 5. File đã xuất trong T2

| File | Nội dung |
|------|----------|
| `results/T2/T2_BIT_RAW_AND_DECODED.md` | Bảng BIT raw + decoded, so sánh GeForce/CMP |
| `results/T2/T2_CALL_GRAPH_DRIVER_GSP.md` | Call graph driver/GSP, phân loại gate |
| `results/T2/T2_FUSE_RAW_VS_EFFECTIVE.md` | Bảng raw fuse vs effective fuse, phân loại 0x21C04 |
| `results/T2/T2_EVIDENCE_LEDGER.md` | Evidence ledger đầy đủ |
| `results/T2/T2_CORRECTED_FINDINGS.md` | Tổng kết, sửa T1, bảng verdict |

## Ghi chú PONYTAIL

# ponytail: T2 sửa tất cả kết luận sai của T1. CMP có NO_DISPLAY_SUBSYSTEM=1 trong BIT data, GeForce không. Driver gate qua fuse 0x21C04 nhưng nguồn fuse là UNKNOWN. Không kết luận "hard-fused" ohne bằng chứng OTP trực tiếp. 5 file đã ghi.
