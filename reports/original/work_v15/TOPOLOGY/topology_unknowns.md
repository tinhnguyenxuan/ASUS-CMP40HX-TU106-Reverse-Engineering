# TOPOLOGY UNKNOWNS — mâu thuẫn và vùng chưa hiểu

Theo prompt mục 8.D và 8.F. Không mục nào ở đây được phép "làm tròn" thành
kết luận.

---

## TU-01 — Phân bố TPC trên 3 GPC

**Quan sát:** 17 TPC, 3 GPC. 17 không chia hết cho 3.

**Giả thuyết:**
- (a) 6/6/5 — một GPC thiếu 1 TPC
- (b) 6/6/5 nhưng GPC nào thiếu chưa biết
- (c) Có GPC thứ 4 bị disable hoàn toàn, 17 TPC chia 6/6/5 cho 3 GPC còn lại
- (d) `NV_FUSE_STATUS_OPT_GPC = 0x38` không phải mask 3 GPC

**Ủng hộ (a)/(b):** TU106 reference có 18 TPC (6/GPC), card này 17 → cắt 1.
**Chống:** không đo được ranh giới GPC qua MMIO (PGRAPH poison).

**Trạng thái:** `UNKNOWN` · **Ưu tiên:** P1
**Cách giải:** tìm register GPC bitmap khác trong `dev_top*.h` (chưa có trong
source công khai Linux), hoặc dump fuse từ card TU106 khác để so.

---

## TU-02 — `NV_FUSE_STATUS_OPT_GPC = 0x38` nghĩa là gì

**Quan sát:** `0x38 = 0b00111000` tại `fuse+0xC1C`.

**Giả thuyết:**
- (a) bit 3/4/5 = 3 GPC enabled
- (b) là **giá trị đếm** (56?) không phải mask
- (c) mask cho 8 vị trí, bật 3

**Ủng hộ (a)/(c):** `nvidia-smi` báo `Product Architecture: Turing`, 34 SM khớp
3 GPC × ~11-12 SM.
**Chống:** không có bitfield documented trong header công khai.

**Trạng thái:** `INFERRED` · **Ưu tiên:** P1
**Cách giải:** đối chiếu `0x38` với mask của card TU106 36-SM (nếu có dump).

---

## TU-03 — Báo cáo cũ ghi "GPC0 TPC5 trả poison" — SAI INDEXING

**Quan sát:** báo cáo phiên trước ghi GPC0 có TPC5.

**Mâu thuẫn:** nếu 3 GPC có 6 TPC/GPC thì TPC0..5 thuộc GPC0. Nhưng card này
**17 TPC**, có thể GPC0 chỉ 5 TPC → TPC5 thuộc **GPC1**.

**Trạng thái:** `CONTRADICTED` (kết luận cũ sai)
**Cách giải:** cần TU-01 trước.

---

## TU-04 — L2 / memory controller / ROP: 0% đo trực tiếp

**Quan sát:** mọi thông số L2 (4 partition, 1 MiB), MC (8×32-bit), ROP (64)
đều **suy từ tài liệu TU106**, không có phép đo nào trên card này.

**Vì sao chưa đo:** `NV_PLTC_BASE` và `NV_PFB_*` (ngoài WPR2) trả poison →
ngoài cửa sổ BAR0 được decode (xem `U-MMIO-ADDRDEC`).

**Trạng thái:** `UNKNOWN` · **Ưu tiên:** P2
**Cách giải:** tìm aperture thật cho PLTC trong `dev_ltc*.h`; hoặc đọc qua
sideband (không có quyền).

---

## TU-05 — Display: 0 addressable nhưng fuse báo enable

**Quan sát:**
- `NV_FUSE_STATUS_OPT_DISPLAY_DATA_ENABLE = 1`
- MMIO `0x610000..0x640000`: **0/200 word** dữ liệu
- Đối chứng PBUS/FUSE: **8/32** word có dữ liệu

**Ba khả năng (không chọn cái nào khi chưa đủ bằng chứng):**
1. CMP SKU không nối display vào fabric — `nvidia-smi` báo `Display Active: Disabled`
2. Address decoder chỉ map một phần BAR0 — **đã chứng minh** có hiện tượng này (PGRAPH)
3. Display power-gate hoàn toàn, cần đánh thức

**Trạng thái:** `Not addressable` (đo được) + `UNKNOWN` (nguyên nhân)
**Ưu tiên:** P2 · **Cấm:** không kết luận "cắt vật lý" (mục 8.F)

---

## TU-06 — PGRAPH poison: BAR0 không decode toàn bộ 16 MB

**Quan sát:** `NV_PGRAPH_BASE = 0x400000` trả `0xBADF5040` toàn bộ 16 word.
Trong khi `0x0` (PBUS) và `0x21000` (FUSE) đọc tốt.

**Ý nghĩa:** đây là **phát hiện làm thay đổi mô hình** — không thể dùng
"poison ⇒ block không tồn tại". Poison có thể chỉ là "ngoài cửa sổ decode".

**Trạng thái:** `DECODED` (quan sát) + `UNKNOWN` (bản đồ aperture)
**Ưu tiên:** P1
**Cách giải:** quét từng 64 KB của 16 MB BAR0, ghi lại trang nào có dữ liệu →
lập **bản đồ aperture được decode**. Read-only, an toàn.

---

## TU-07 — Số GPC lẻ và NVENC/NVDEC

**Quan sát:** 17 TPC lẻ, 1 NVENC, 1 NVDEC. TU106 reference: NVENC nằm ở GPC nào?
Nếu 17 TPC lẻ thì NVENC chiếm chỗ 1 TPC?

**Trạng thái:** `UNKNOWN` · **Ưu tiên:** P3
**Cách giải:** không khả thi qua MMIO hiện tại; cần die shot hoặc tài liệu NVIDIA.

---

## Tổng hợp

| ID | Trạng thái | Ưu tiên | Có thể giải read-only? |
|---|---|---|---|
| TU-01 | UNKNOWN | P1 | Không (cần dump card khác) |
| TU-02 | INFERRED | P1 | Không |
| TU-03 | CONTRADICTED | — | Đã sửa |
| TU-04 | UNKNOWN | P2 | Có (tìm aperture PLTC) |
| TU-05 | Not addressable + UNKNOWN | P2 | Không kết luận được |
| TU-06 | DECODED + UNKNOWN | P1 | **Có — quét 16 MB, read-only** |
| TU-07 | UNKNOWN | P3 | Không |
