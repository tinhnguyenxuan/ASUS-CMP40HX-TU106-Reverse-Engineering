# PHASE15/BLOCKERS.md — Các unknown bị BLOCKED có lý do cụ thể

Nguyên lý: không đánh dấu DONE chỉ vì đã đọc hết byte. Mục nào bị BLOCKED phải có lý do cụ thể và điều kiện để mở lại.

## 1. FUSE/OTP

| ID | Nội dung | Lý do BLOCKED | Điều kiện mở lại |
|---|---|---|---|
| U-FUSE-002 | fuse `+0x0718` 32 byte entropy cao, không phải hash PDI | Đã exhaustive search 455,689 + 12,883 lần hash trên ROM+GSP+uCodes+chính khối fuse → 0 khớp. Không có khoá/HMAC để đối chiếu. | Cần ROM TU106 khác hoặc source booter để đối chiếu |
| U-FUSE-001 | 152 word =1 — bản chất OTP cell hay enable flag | Không có dump fuse TU106/TU104 khác để đối chiếu pattern. Không có bitfield từ source. | Cần dump fuse chip khác hoặc bitfield từ source NVIDIA |
| U-FUSE-003 | fuse `+0x0000` = `0xC0040000`, strap mirror/chip config | Không có bitfield strap từ source TU106. | Cần dev_fuse.h TU106 hoặc Nouveau/envytools doc |
| U-FUSE-004 | fuse `+0x0D4..0x0F4` `0xFFFFFFFC/0xFFFFFF8F` (11 word) | Không rõ bit nào, không có bitfield. | Cần bitfield từ source |

## 2. GSP-RM

| ID | Nội dung | Lý do BLOCKED | Điều kiện mở lại |
|---|---|---|---|
| U-GSP-007 | Chỉ 56/186 entry có `name_ptr` trỏ đầu chuỗi thật; 130 entry `u64@+0x10` trỏ vào giữa dữ liệu | 4 giả thuyết bị bác bỏ (suffix merging: `_MIN` ambiguous 126 lần; offset pool chỉ 16/370; u16 không phải độ dài; u64 là tham số callback). Cần đọc hàm callback `jalr a5` để biết cách tra tên. | Cần disasm hàm callback (context +0x30) |
| U-GSP-006 | 7 tên (`RMClkVfOverride`, `OVERVOLTAGE_*`, `PERFORMANCE_CAP0`) không có entry trong bảng 340 | 0 u32/u64/entry-style ptr tro tới các tên này ở mọi offset. Có thể là bảng thứ hai chưa tìm. | Cần quét `.rodata` tìm bảng entry thứ hai hoặc hàm tra tên runtime |
|| U-GSP-004 | `RELIABILITY_NVVDD` id=204 trùng `VMIN_NVVDD_0` → id không duy nhất | `id` không phải khóa toàn cục, cần (module, id) cặp. | Cần disasm hàm consume policy để biết cách tra ||
|| U-GSP-008 | Caller của ham dispatch @0x04F575FC | 0 jal thang tiep den dispatcher; 0 auipc+jalr pair targeting; 2 lui khop nhung o trong khuong dispatch chinh | Can Ghidra headless call graph ||

## 3. Firmware

| ID | Nội dung | Lý do BLOCKED | Điều kiện mở lại |
|---|---|---|---|
| U-FW-001..004 | 4 blob entropy cao (7.998), không nén được | Không magic, không IV, không phân biệt AES vs nén từ dữ liệu. Không có khoá giải mã trong driver công khai. | Cần khoá giải mã hoặc mẫu plaintext-known |
| U-FW-013 | `blob[0]` không phải code Falcon (93.1% unknown) | Không phải code Falcon. Cần xác định đây là bảng gì trước khi disasm. | Cần xác định cấu trúc bảng dữ liệu |
| U-FW-012 | 24 byte khác blob[6]/blob[8] | Chưa biết là version/patch/checksum. | Cần so sánh build system hoặc source firmware |

## 4. VBIOS

| ID | Nội dung | Lý do BLOCKED | Điều kiện mở lại |
|---|---|---|---|
| U-VBIOS-001 | 5 field chưa biết trong key block (`sig`, `ver`, `f4`, `f8`, `flags`, `hash`) | `f4` không phải timestamp, hash không khớp vùng ROM (0/912). Không có ROM TU106 khác để đối chiếu. | Cần ROM TU106 khác |
| U-VBIOS-003 | 12 digest NPDS-0x70 | 0/1,365,939 phép thử khớp. Không biết hàm băm. | Cần hàm băm từ source hoặc mẫu known |

## 5. MMIO / Topology

| ID | Nội dung | Lý do BLOCKED | Điều kiện mở lại |
|---|---|---|---|
| U-MMIO-012 | Mã `0xBAD00100` (25 trang) và `0xFFFFFFFF` (72 trang) | `0xBAD00100` khác họ `0xBADFxxxx` (nửa thấp không phải mã lỗi). `0xFFFFFFFF` nằm trong BAR0 GPU → GPU tự trả về, chưa xác nhận ai. | Cần tài liệu mã trả về hoặc disasm handler MMIO |
| U-BAR3-001 | BAR3 (32 MB) chứa gì, tại sao host đọc được | 3 giả thuyết (page directory GMMU / bảng tra cứu SKU / bootstrap table) chưa được xác nhận. | Cần đối chiếu với source GMMU hoặc driver |
| U-BAR3-002 | BAR3 thiếu device ID `0x1F0B` (chỉ có `0x1F4F`×43, `0x1F4E`×2) | CMP 40HX nhận diện qua đường nào chưa rõ (fuse force ID? VBIOS override?). | Cần traces driver khởi tạo |

## 6. Memory

| ID | Nội dung | Lý do BLOCKED | Điều kiện mở lại |
|---|---|---|---|
| U-MEM-001 | 388.5 MiB carveout (Reserved 389 MiB − WPR2 0.5 MiB) | WPR2 chỉ 0.5 MiB, không đủ giải 388.5 MiB. Cần đọc register PFB carveout. | Cần đọc thêm register PFB (có thể nằm ngoài 52 register đã試) |

## 6b. Security

| ID | Nội dung | Lý do BLOCKED | Điều kiện mở lại |
|---|---|---|---|
| U-SEC-002 | PLM_FECS/RESET, ACR_CMD/STATUS, SEC2_STATUS poison `0xBADF5040` | Chỉ có giá trị từ boot log. Register poison khi đọc → không thể đọc trực tiếp. | Cần disasm boot code hoặc tài liệu PLM/ACR |

## 7. BLOCKED theo thao tác (không làm theo yêu cầu đề bài)

| Thao tác | Lý do |
|---|---|
| Sweep VF offset | **Cấm** (mục 7.C của đề bài Phase 15) — đã làm ở phiên v14, không lặp lại |
| Ghi BAR0/MMIO/OTP | **Cấm** (mục 7.E/F/G) — chỉ read-only |
| Flash/nạp VBIOS mới | **Cấm** (mục 7.H) |
| Reload driver / reboot | **Cấm** (mục 7.I/J) |
| Brute-force khoá | **Cấm** (mục 7.K) |
| Quét MMIO chưa xác nhận | **Cấm** (mục 7.L) |

---
**Ponytail:** mỗi BLOCKED có lý do cụ thể và điều kiện mở lại. Không BLOCKED speculative.
