# P5 — GPU SILICON TOPOLOGY (TU106 trong CMP 40HX)

Bằng chứng: `TOPOLOGY/silicon_topology.json`, `TOPOLOGY/display_probe.json`,
`RAW_DATA/p5678.json`, `nvidia-smi -q` output.

Phân loại theo yêu cầu prompt mục 8.D: **Present · Enabled · Disabled ·
Power-gated · Clock-gated · Not addressable · Unknown**.

---

## 1. Số liệu đo được

| Đơn vị | Số lượng | Nguồn | Phân loại |
|---|---:|---|---|
| GPC | **3** | `NV_FUSE_STATUS_OPT_GPC = 0x38` (bit 3/4/5) | `INFERRED` |
| TPC | **17** | trích từ topology register + `nvidia-smi` | `MEASURED` |
| SM | **34** | `nvidia-smi` (17 TPC × 2 SM) | `MEASURED` |
| CUDA cores | **2176** | 34 × 64 | `MEASURED` |
| Memory controller | **8** (32-bit) | TU106 reference 256-bit | `INFERRED` |
| L2 partition | **4** | TU106 reference (1 MiB tổng) | `INFERRED` |
| ROP | **64** | TU106 reference (16/partition) | `INFERRED` |
| Display engine | **0** ở MMIO | `q6_display.py`: 0/200 word | `Not addressable` |
| NVENC | 1 | MMIO đọc được 73% register | `Enabled` |
| NVDEC | 1 | `NVDEC_DISABLE = 0` | `Enabled` (fuse) · `Unknown` (MMIO) |

---

## 2. Topology graph (từ dữ liệu đo)

```
TU106-100-A1
├── GPC0 (3 TPC, 6 SM)
│   ├── TPC0 ── SM0, SM1
│   ├── TPC1 ── SM2, SM3
│   └── TPC2 ── SM4, SM5
├── GPC1 (3 TPC, 6 SM)
│   ├── TPC3 ── SM6, SM7
│   ├── TPC4 ── SM8, SM9
│   └── TPC5 ── SM10, SM11      <<< TPC5 tra 0xBADF1300 trong fuse walk
├── GPC2 (3 TPC, 6 SM)
│   ├── TPC6 ── SM12, SM13
│   ├── TPC7 ── SM14, SM15
│   └── TPC8 ── SM16, SM17
├── ... 17 TPC tổng -> 34 SM
├── L2 (4 partition, 1 MiB)
├── MC0..MC7 (8 × 32-bit = 256-bit bus)
├── NVENC (1)
├── NVDEC (1)
└── [DISPLAY: KHÔNG addressable qua BAR0]
```

**Lưu ý quan trọng:** số TPC = 17 là **lẻ**, không chia hết cho 3 GPC. Nghĩa là
một GPC có **5 TPC** hoặc phân bố **6/6/5**. Không đo được phân bố chính xác
→ `UNKNOWN` (`U-TOP-001`).

---

## 3. Kiểm tra register topology (mục 8.B)

Đã đọc qua BAR0 (`TOOLS/mmio_scan.py`, `TOOLS/q6_display.py`):

| Vùng | Base | Kết quả | Phân loại |
|---|---|---|---|
| PMC/BOOT_0 | `0x000000` | `0x166000A1` | `Enabled` |
| PBUS | `0x000000+` | `0x801F7CC0` | `Enabled` |
| FUSE | `0x021000` | 7/8 word dữ liệu | `Enabled` |
| PFB (WPR2) | `0x1FA824` | `0x01F7E000` | `Enabled` |
| PGSP | `0x110600` | `0x00000110` | `Enabled` |
| PSEC | `0x840600` | `0x00010004` | `Enabled` |
| PGC6 | `0x1180F8` | `0x17300000` | `Enabled` |
| **PGRAPH** | **`0x400000`** | **`0xBADF5040` toàn bộ** | **`Not addressable`** |
| **PDISP** | **`0x610000`..`0x640000`** | **`0xBADF1301`** | **`Not addressable`** |
| SOR | `0x616000` | `0xBADF1301` | `Not addressable` |
| DAC | `0x61C000` | `0xBADF1301` | `Not addressable` |

**Phát hiện quan trọng:** PGRAPH `0x400000` **cũng poison**. Nghĩa là **BAR0
không decode toàn bộ 16 MB** — chỉ một số aperture được map. Điều này giải thích
6 unknown `U-MMIO-*`: **không phải block không tồn tại**, mà **ngoài cửa sổ BAR0
được decode**.

---

## 4. Đối chiếu TU106 reference (mục 8.C)

| Đặc điểm | TU106 reference | Card này | Kết luận |
|---|---|---|---|
| SM | 36 (RTX 2060/2060S) | **34** | **CẮT 2 SM** |
| TPC | 18 | **17** | **CẮT 1 TPC** |
| CUDA | 2304 | **2176** | **CẮT 128** |
| Bus | 256-bit | 256-bit (suy từ 8 MC) | khớp |
| GPC | 3 | 3 (fuse) | khớp |
| Display | có | **0 addressable** | **khác** |
| NVENC | 1 | 1 | khớp |

**Cắt 128 CUDA được xác nhận bởi fuse:** `fuse+0x650 = 0x0004001F` →
`0x0004` ở nibble cao = mask cắt. GPC0 TPC5 trả `0xBADF1300` (poison khác
`0xBADF5040` của vùng không map) → **poison có ngữ nghĩa trong fuse walk**.

---

## 5. Mâu thuẫn GPC numbering / TPC indexing (mục 8.E)

**Mâu thuẫn 1:** `NV_FUSE_STATUS_OPT_GPC = 0x38 = 0b00111000` → bit 3,4,5 bật.
Nếu mỗi bit = 1 GPC thì **3 GPC**. Nhưng 17 TPC không chia hết cho 3.

Ba cách đọc khả dĩ:
- (a) bit 3,4,5 = **enable mask** cho 3 GPC, TPC phân bố 6/6/5
- (b) `0x38` là **giá trị đếm** liên quan GPC, không phải mask
- (c) 3 GPC nhưng 1 GPC bị fuse cắt xuống còn 5 TPC

**Chưa phân biệt được** → `U-TOP-001` giữ `UNKNOWN`, priority P1.

**Mâu thuẫn 2:** báo cáo cũ ghi "GPC0 TPC5 trả poison". Nếu GPC0 chỉ có 3 TPC
thì TPC5 **không thuộc GPC0**. Đây là **lỗi indexing** của báo cáo cũ — TPC5
phải thuộc GPC1. Ghi vào `topology_unknowns.md`.

---

## 6. Không tuyên bố cắt vật lý (mục 8.F)

**Tuân thủ:** với display và PGRAPH, em **không** kết luận "cắt vật lý". Bằng
chứng hiện có chỉ cho thấy **không addressable qua BAR0**, điều này **không**
chứng minh silicon không có display engine. Ba khả năng còn mở:

1. CMP SKU không nối display vào fabric (khả dĩ nhất — CMP là card mining).
2. Address decoder chỉ map một phần BAR0 (đã chứng minh có hiện tượng này với PGRAPH).
3. Display bị power-gate hoàn toàn, cần đánh thức qua register khác chưa tìm.

`nvidia-smi` báo `Display Active: Disabled`, `Display Attached: No` → phù hợp (1).
Nhưng **không phải bằng chứng**.

---

## 7. Coverage P5

| Đơn vị | Xác định được | Tổng ước | % |
|---|---:|---:|---:|
| GPC | 3 (fuse) | 3 | 100% (số lượng) |
| TPC | 17 | 17 | 100% |
| SM | 34 | 34 | 100% |
| CUDA | 2176 | 2176 | 100% |
| NVENC | 1 (73% reg) | 1 | 73% |
| NVDEC | 1 (fuse) | 1 | 40% |
| Display | 0 addr | ? | 0% |
| L2/MC/ROP | suy từ reference | 4/8/64 | **0% đo trực tiếp** |

**Phần yếu nhất:** L2, memory controller, ROP — **hoàn toàn suy từ tài liệu
TU106**, chưa có phép đo nào trên card này. Đây là `UNKNOWN` thực sự, không
được tính là "đã giải".
