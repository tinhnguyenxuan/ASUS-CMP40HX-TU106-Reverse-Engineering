# VBIOS_BIT_PCIR_COMPARISON.md

## Ket qua kiem toan VBIOS stock vs t4

### 1. Thông tin cơ bản

| Thuộc tính | Stock (CMP40HX_ORIGINAL_1MB.bin) | T4 (cmp40hx_t4_derivative.bin) |
|---|---|---|
| Kích thước | 1,048,576 bytes (1 MB) | 495,616 bytes (~484 KB) |
| SHA-256 | dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec | aa0ebd6d74326bb4630c473caeb6a5ae2bf55598b80a38d41a65ffee0b40cfdb |
| Magic | NVGI | NVGI |
| Header size | 870 (0x366) | 870 (0x366) |
| Header version | 0x8024 | 0x8024 |

### 2. T4 là ROM bị cắt (TRUNCATED)

- T4 kết thúc tại offset 0x79000.
- Stock có NVGI tiếp theo tại 0x79000 → T4 bị cắt đúng ranh giới NVGI.
- Thiếu 552,960 bytes (0x87000 bytes) từ 0x79000 đến 0x100000.
- Vùng thiếu có 86% byte khác 0 (dữ liệu thực, không phải padding).

### 3. PCIR entries

| Offset | Vendor | Device | Length | Rev | Class | Trong T4? |
|---|---|---|---|---|---|---|
| 0x28770 | 0x10DE | 0x1F0B | 24 | 0x0000 | 02037a | Có |
| 0x36F69 | 0x1074 | 0x3D66 | 21316 | 0x0874 | 663d52 | Có |
| 0x37A1C | 0x10DE | 0x1F0B | 28 | 0x0003 | 000088 | Có |
| 0x53059 | 0xF9A6 | 0x0BF4 | 20558 | 0x5344 | a6f9f4 | Có |
| 0xA1770 | 0x10DE | 0x1F0B | 24 | 0x0000 | 02037a | **Không** (trong vùng bị cắt) |
| 0xAFF69 | 0x1074 | 0x3D66 | 21316 | 0x0874 | 663d52 | **Không** (trong vùng bị cắt) |
| 0xB0A1C | 0x10DE | 0x1F0B | 28 | 0x0003 | 000088 | **Không** (trong vùng bị cắt) |
| 0xCC059 | 0xF9A6 | 0x0BF4 | 20558 | 0x5344 | a6f9f4 | **Không** (trong vùng bị cắt) |

**Device ID chính:** 0x1F0B (TU106 / CMP 40HX) — xuất hiện 4 lần trong stock, 2 lần trong T4.

### 4. DCB (Display Configuration Block)

| Vị trí | Stock | T4 | Ghi chú |
|---|---|---|---|
| 0x2d9b2 | DCB signature 0x4EDCBDCB ✓ | DCB signature 0x4EDCBDCB ✓ | Version 170 (0xAA), header=75, entry_count=0, entry_size=0 |
| 0xa69b2 | DCB signature 0x4EDCBDCB ✓ | **BỎ THIẾU** (vùng bị cắt) | Tương tự version 170 |

**Lưu ý:** DCB version 170 (0xAA) là không chuẩn (NVIDIA thường dùng 0x10, 0x20, 0x30, 0x41...). entry_count=0 và entry_size=0 cho thấy đây có thể là DCB placeholder hoặc định dạng tùy chỉnh. Không thể kết luận đây là bảng display cấu hình đầy đủ.

### 5. Chuỗi "CONNECTOR" — SAI NHẬN

Chuỗi tại 0x2cbd3 và 0xa5bd3 decode thành ASCII: **"CONNECT THE PCIe POWER CABLE(S)"** — đây là thông báo cắm cáp ngắt nguồn PCIe, **KHÔNG phải bảng connector/table cấu hình display**. Không nên dùng làm bằng chứng về cổng display.

### 6. BIT Header

- Không tìm thấy chữ ký "BITB" (BIOS Information Table) trong stock hoặc T4.
- Không tìm thấy cấu trúc BIT chuẩn của NVIDIA.
- Chuỗi "NVIDIA" xuất hiện ở nhiều vị trí (0x286eb, 0x2d4d6, 0x2d4ea, 0x76ac1, 0x76ec7, ...) — đây là các chuỗi bản quyền/phiên bản, **không phải BIT header**.

### 7. 19 byte khác nhau trong vùng chung

Tất cả 7 vùng khác nhau nằm sau PCIR tại 0x53059 (offset 0x5669C–0x566BE và 0x767FF):

| Offset | Stock | T4 | Vùng |
|---|---|---|---|
| 0x5669C-0x5669E | 70 76 82 | 40 54 89 | Sau PCIR 0x53059 |
| 0x566A0-0x566A2 | 70 76 82 | 40 54 89 | Sau PCIR 0x53059 |
| 0x566A4-0x566A6 | 70 76 82 | 40 54 89 | Sau PCIR 0x53059 |
| 0x566B4-0x566B6 | B0 83 85 | 40 54 89 | Sau PCIR 0x53059 |
| 0x566B8-0x566BA | B0 83 85 | 40 54 89 | Sau PCIR 0x53059 |
| 0x566BC-0x566BE | B0 83 85 | 40 54 89 | Sau PCIR 0x53059 |
| 0x767FF | 33 | E5 | Sau PCIR 0x53059 |

**Phân loại:** Không thể xác định section/table/chức năng chính xác vì không có BIT header và DCB entry_count=0. **Không được gọi là "connector config" hay "display config"** — chỉ là byte khác nhau ở vị trí chưa xác định.

### 8. Đánh giá T4 vs TU106

- T4 (Tesla T4) dùng GPU TU104, **không phải TU106**.
- PCIR trong T4 vẫn giữ Device 0x1F0B (TU106) ở các entry đầu — có thể là VBIOS đã được sửa device ID hoặc là entry chung.
- Vùng bị cắt của T4 chứa toàn bộ bảng display-critical (DCB thứ 2, CONNECTOR string thứ 2, và dữ liệu từ 0x79000-0x100000).
- **Kết luận:** T4 không phải là VBIOS tương thích với CMP 40HX TU106. Là ROM bị cắt từ một source khác, không thể dùng để restore display cho CMP 40HX.

## Ghi chú PONYTAIL

# ponytail: T4 is truncated at 0x79000 (NVGI boundary), missing 552KB including 2nd DCB and all upper PCIR entries. "CONNECTOR" strings are ASCII power cable warnings, not tables. No BITB header found. DCB version 170 is non-standard with 0 entries. 19 byte diffs unclassified. T4 (TU104) is not compatible with CMP TU106.
