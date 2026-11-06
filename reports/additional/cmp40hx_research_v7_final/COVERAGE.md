# COVERAGE DASHBOARD — CMP 40HX / TU106

Sinh bởi `TOOLS/build_db.py`. Dữ liệu máy đọc: `COVERAGE.json`.

**Nguyên tắc (mục 14):** không quy đổi các loại coverage khác nhau thành một
tỷ lệ chung. Mỗi subsystem đo bằng đơn vị của chính nó.

---

## 1. FUSE / OTP

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| Word đã dump | 3,072 | 3,072 (span 0x2000) | **100%** |
| Word có dữ liệu | 352 | 352 | **100%** |
| Word đã **phân loại nội dung** | 352 | 352 | **100%** |
| Word có **tên register** | 5 | 352 | **1.4%** |
| Word có **bitfield giải nghĩa** | 4 | 352 | **1.1%** |
| OTP cell xác định bản chất | 152 | 152 | **100%** |
| OTP cell biết **nghĩa từng bit** | 0 | 152 | **0%** |
| Cụm hash/chữ ký nhận dạng | 2 | 2 (nghi) | **100%** |
| Cụm hash/chữ ký **giải nghĩa** | 0 | 2 | **0%** |

**Nhận xét:** phân loại nội dung đạt 100%, nhưng **ý nghĩa** đạt 1.4%.
Đây là hai đơn vị khác nhau — không gộp.

---

## 2. MMIO / BAR0

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| Register trích từ source (5 kiến trúc) | 938 | — | — |
| **Register trích riêng turing** | **52** | — | — |
| Register đã **thử đọc** | 52 | 52 | **100%** |
| Register **đọc được** (không poison/zero) | 33 | 52 | **63.5%** |
| Register poison | 6 | 52 | 11.5% |
| Register zero | 13 | 52 | 25.0% |
| Bitfield định nghĩa (turing) | 211 | — | — |
| Bitfield **có giá trị đọc được** | ~40 | 211 | ~19% |
| Block nhận dạng | 18 nhóm | ~25 block | ~72% |
| Trang 64 KB đã chạm | 10 | 256 (16 MB BAR0) | 3.9% |

**Nhận xét:** 63.5% register turing đọc được là cao. Nhưng chỉ chạm **3.9%**
không gian BAR0 → **không** tuyên bố đã map hết MMIO.

---

## 3. VBIOS

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| Byte ROM đã **phân vùng** | 1,048,576 | 1,048,576 | **100%** |
| Image/container nhận dạng | 9 | 9 | **100%** |
| Bảng có cấu trúc **parse được** | 42 | — | — |
| Bảng **giải nghĩa đầy đủ field** | 3 (VFE, POWER, THERMAL) | 42 | **7.1%** |
| Record key block **parse được** | 38 | 38 | **100%** |
| Field key block **giải nghĩa** | 3/6 (sig, ver, hash) | 6 | **50%** |
| Digest NPDS-0x70 | 12 | 12 | 100% (đếm) |
| Digest **khớp vùng dữ liệu** | 0 | 12 | **0%** |

---

## 4. GSP-RM

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| Byte file | 22,901,632 | — | — |
| Section parse | 37 | 37 | **100%** |
| PT_LOAD map | 11 | 11 | **100%** |
| String trong `.rodata` liệt kê | 134,417 | — | — |
| Bảng descriptor tìm được | 60 | ? | — |
| **Entry descriptor có tên** | **340** | 340 | **100%** |
| Entry có **consumer xác định** | **0** | 340 | **0%** |
| Giá trị `f08` giải nghĩa | 0 | 16 | **0%** |
| Giá trị `f18` giải nghĩa | 0 | 13 | **0%** |
| Giá trị `f14` giải nghĩa | 0 | 340 | **0%** |
| Function inventory | **chưa làm** | ? | — |
| Call graph | **chưa làm** | ? | — |

**Nhận xét:** tên đạt 100%, nhưng **ngữ nghĩa đạt 0%**. Không tuyên bố đã
reverse GSP-RM.

---

## 5. FIRMWARE

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| Blob phân loại | 11 | 11 | **100%** |
| Blob **xác định bản chất nội dung** | 2 (blob 0 data, 6≡8) | 11 | **18%** |
| Blob **disasm thành code** | **0** | 11 | **0%** |
| Blob phân biệt nén vs mã hoá | **không phân biệt được** | 4 | **0%** |
| Entry directory giải mã | 11 | 11 | 100% |
| Load address xác định | 0 | 11 | **0%** |
| Engine mapping | 0 | 11 | **0%** |

---

## 6. TOPOLOGY

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| TPC/SM xác nhận bằng đo | 17 / 34 | 17 / 34 | **100%** |
| GPC xác nhận | 3 (từ `fuse+0xC1C`) | 3 | **INFERRED** |
| ROP đếm được | **0** | ? | 0% |
| L2 partition đếm được | **0** | ? | 0% |
| Đơn vị phân loại trạng thái (mục 8.D) | 9 | — | — |
| Đơn vị trạng thái **UNKNOWN** | 4 (ROP, L2, scheduler, crossbar) | 9 | 44% |

---

## 7. MEMORY

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| Tổng VRAM xác định | 8192 MiB | 8192 MiB | **100%** |
| Reserved xác định | 389 MiB | 389 MiB | **100%** |
| Reserved **giải thích được** | 0.5 MiB (WPR2) | 389 MiB | **0.13%** |
| Memory partition | **0** | ? | 0% |
| L2 partitioning | **0** | ? | 0% |
| Page table / MMU | **0** | ? | 0% |

---

## 8. PCIe

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| BAR xác định | 4 (0,1,3,5) | 6 | 67% |
| Trạng thái 3 tầng phân biệt | **có** | — | — |
| Link training nguyên nhân | biết `RETRAIN_FAIL 1101` | — | — |
| Strap PCIe | **0** | ? | 0% |

---

## 9. SECURITY

| Đơn vị đo | Đã làm | Tổng | % |
|---|---:|---:|---:|
| WPR region xác định | **4** (WPR0/WPR1/WPR2/WPR2-alt) | ? | — |
| Boot sequence bước | **5** (đã xác nhận bằng dmesg) | ? | — |
| Trust boundary vẽ được | **6 tầng** (host/driver/GSP-RM/FWSEC/SEC2/silicon) | — | — |
| Security register (fuse) | 1 (`SECURE_GSP_DEBUG_DIS`) | ? | — |
| **Security register (MMIO)** | **17 đọc được** (10 DATA, 2 zero, 5 poison) | ? | — |
| WPR có giá trị LO+HI | **4/4** | ? | — |
| PLM register đọc được | **0** (poison — chỉ có boot log) | 2 | **0%** |
| ACR register đọc được | **0** (poison) | 3 | **0%** |
| SEC2 DMEM dọn sạch | **64 KB xác nhận** | ? | — |
| Confidential Computing | **TẮT** (0 MiB) | ? | — |
| IOMMU cô lập DMA | **group 31 riêng** | ? | — |

### 9.1 Giá trị WPR đo được (SECURITY/p8_wpr.json)

| Region | LO | HI | Kích thước |
|---|---|---|---|
| WPR0 | `0x001001C0` | `0x1FFFF000` | ~511.0 MB |
| WPR1 | `0x00000000` | `0x08000880` | ~128.0 MB |
| WPR2 | `0x01F78200` | `0x01F7E000` | 23.75 KB |
| WPR2 alt | `0x01FFEE00` | `0x1FFFFFF0` | ~480.0 MB |

**Lưu ý mâu thuẫn `U-SEC-001`:** `WPR2_LO @0x1FA820 = 0x01F78200` nhưng dmesg báo
`wpr2_lo = 0x1FFFFE00`. Ngược lại `WPR2_HI @0x1FA824 = 0x01F7E000` **trùng chính xác**
với dòng `INPLACE_STOCK_BOOTER_AFTER_UNLOCK_PASS WPR=01ffee00:01f7e000`.

---

## 10. UNKNOWN tracking

| Chỉ số | Giá trị |
|---|---:|
| Tổng unknown ghi nhận | **42** |
| Open | **33** |
| Resolved | **9** |
| Bị bác bỏ (CONTRADICTED) | 8 kết luận cũ |
| BLOCKED có lý do | 6 |

Phân bố: FUSE 13 · MMIO 6 · FIRMWARE 6 · GSP 5 · VBIOS 3 · TOPOLOGY 1 · MEMORY 1 · **SECURITY 2**
