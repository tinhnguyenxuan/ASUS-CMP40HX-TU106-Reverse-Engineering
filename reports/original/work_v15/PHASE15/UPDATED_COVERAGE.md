# PHASE15/UPDATED_COVERAGE.md — Cập nhật coverage sau Phase 15

Nguyên tắc: không quy đổi các loại coverage khác nhau thành một tỷ lệ chung. Mỗi subsystem đo bằng đơn vị của chính nó.

## 1. FUSE / OTP

| Đơn vị đo | Đã làm | Tổng | % | Ghi chú P15 |
|---|---:|---:|---:|---|
| Word đã dump | 3,072 | 3,072 | 100% | span 0x1DFF |
| Word có dữ liệu | 352 | 352 | 100% | |
| Word đã phân loại nội dung | 352 | 352 | 100% | data/zero/poison |
| Word có **tên register** | 5 | 352 | **1.4%** | NVDEC_DISABLE, SECURE_GSP_DEBUG_DIS, DISPLAY_DATA_ENABLE, PCI ID, họ TU106, TPC/SM, GPC |
| Word có **bitfield giải nghĩa** | 3 | 352 | **0.9%** | 3 register trong dev_fuse.h tu102 |
| OTP cell biết bản chất | 0 | 152 | **0%** | 152 word =1 = INFERRED enable flag |
| Cụm hash/chữ ký giải nghĩa | 0 | 2 | **0%** | PDI (giải), +0x0718 (chưa giải) |

## 2. MMIO / BAR0

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| Register turing đã thử đọc | 52 | 52 | 100% |
| Register đọc được | 33 | 52 | 63.5% |
| Register poison | 6 | 52 | 11.5% |
| Trang 64 KB đã chạm | 10 | 256 | 3.9% |
| Block nhận dạng | 18 | ~25 | ~72% |

## 3. VBIOS

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| Byte ROM đã phân vùng | 1,048,576 | 1,048,576 | 100% |
| Bảng có cấu trúc parse được | 42 | — | — |
| Bảng giải nghĩa đầy đủ field | 3 | 42 | 7.1% |
| Field UNKNOWN trong key block | 5 | 6 | 83% layout, 17% nghĩa |
| Digest NPDS-0x70 khớp vùng | 0 | 12 | 0% |

## 4. GSP-RM

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| Entry descriptor có tên | 340 | 340 | 100% |
| Entry có consumer xác định | 1 | 340 | **0.3%** (dispatcher @0x04F575FC) |
| Entry có tên hàm callback | 0 | 340 | 0% |
| Giá trị f08/f14/f18 giải nghĩa | 0 | 16/340/13 | 0% |
| Function inventory | 0 | ? | Chưa làm |
| Call graph | 0 | ? | Chưa làm |

## 5. Firmware

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| Blob phân loại | 11 | 11 | 100% |
| Blob xác định bản chất nội dung | 3 | 11 | 27% |
| Blob disasm thành code | 0 | 11 | 0% |
| Load address xác định | 0 | 11 | 0% |
| Engine mapping | 0 | 11 | 0% |

## 6. Topology

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| TPC/SM xác nhận bằng đo | 17/34 | 17/34 | 100% |
| GPC xác nhận | 3 | 3 | INFERRED (fuse 0xC1C) |
| ROP/L2/scheduler/crossbar | 0 | 4 | 0% UNKNOWN |

## 7. Memory

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| Reserved giải thích được | 0.5 MiB (WPR2) | 389 MiB | 0.13% |
| Carveout chưa giải | 0 | 388.5 MiB | UNKNOWN |

## 8. Security

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| WPR region | 1 (WPR2) | 1 | 100% |
| WPR khớp dmesg | 100% | — | CORROBORATED |
| PLM/ACR/SEC2 register đọc được | 0 | ~10 | 0% (poison, chỉ có log) |
| Boot sequence bước | 5 | 5 | 100% |

## 9. Unknown tracking (từ UNKNOWN_DATABASE.json, nguồn sự thật)

| Component | Open | Resolved | Tổng |
|---|---:|---:|---:|
| FUSE | 10 | 3 | 13 |
| MMIO | 5 | 1 | 6 |
| FIRMWARE | 6 | 0 | 6 |
| GSP-RM | 5 | 0 | 5 |
| VBIOS | 2 | 1 | 3 |
| TOPOLOGY | 1 | 0 | 1 |
| MEMORY | 1 | 0 | 1 |
| SECURITY | 1 | 1 | 2 |
| BAR3 | 2 | 0 | 2 |
| **TỔNG** | **35** | **10** | **45** |

**Sửa mâu thuẫn v14:** MASTER_REPORT.md cũ ghi "37 unknown (32 open, 5 resolved)" — **SAI**. CHECKPOINT.json cũ ghi "40/31/9" — **SAI**. Nguồn sự thật: UNKNOWN_DATABASE.json = 45 items (35 open, 10 resolved).

---
**Ponytail:** coverage đo bằng đơn vị subsystem, không gộp thành tỷ lệ chung.
