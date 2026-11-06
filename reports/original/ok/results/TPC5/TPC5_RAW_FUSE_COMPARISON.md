# TPC5 — SO SÁNH FUSE GỐC VỚI RM EFFECTIVE MASK

**GPU:** NVIDIA CMP 40HX · TU106-100-A1 · `10DE:1F0B` · `0000:03:00.0`
**PMC_BOOT_0:** `0x166000A1` (đọc trực tiếp BAR0, 2026-11-06)
**Driver:** 615.78.08 · **GSP-RM:** 615.78.08
**Ngày:** 2026-11-06 · **chỉ đọc**, không ghi bất kỳ register nào

---

## 0. KẾT LUẬN

> **Dữ liệu fuse trong `fuse2.json` ĐÚNG 100%.** Đã xác minh lại bằng cách đọc trực tiếp BAR0 hôm nay — từng word khớp.
>
> **Và fuse khớp với hardware GR.** Phép đọc GR (`GPC_UNIT(g,0x2608)`) cho **17 TPC = 34 SM**, đúng bằng tổng fuse.
>
> Đây là **lần đầu** chuỗi fuse → hardware → RM mask được đóng kín cho card này.

---

## 1. Xác minh fuse gốc — đọc lại trực tiếp BAR0

Nguồn lưu: `04_PHASE15_EXTRACTS/FUSE/fuse2.json`, `base=0x21000`, `span=0x8000`.
**`fuse2.json` key là offset thập phân**, không phải hex — đây là nguồn nhầm lẫn phổ biến.

### 1.1 Bảng đối chứng: file lưu ↔ đọc trực tiếp hôm nay

| Register | Địa chỉ | `fuse2.json` | **Đọc trực tiếp** | Khớp |
|---|---|---|---|---|
| `STATUS_OPT_GPC` | `0x021C1C` | 56 = `0x38` | `0x00000038` | ✅ |
| `STATUS_OPT_TPC_GPC0` | `0x021C38` | 32 = `0x20` | `0x00000020` | ✅ |
| `STATUS_OPT_TPC_GPC1` | `0x021C3C` | 0 | `0x00000000` | ✅ |
| `STATUS_OPT_TPC_GPC2` | `0x021C40` | 0 | `0x00000000` | ✅ |
| `STATUS_OPT_TPC_GPC3` | `0x021C44` | 63 = `0x3F` | `0x0000003F` | ✅ |
| `STATUS_OPT_TPC_GPC4` | `0x021C48` | 63 = `0x3F` | `0x0000003F` | ✅ |
| `STATUS_OPT_TPC_GPC5` | `0x021C4C` | 63 = `0x3F` | `0x0000003F` | ✅ |
| `CTRL_OPT_TPC_GPC0..5` | `0x021838..4C` | 0 × 6 | `0x00000000` × 6 | ✅ |
| `STATUS_OPT_DISPLAY` | `0x021C04` | 1 | `0x00000001` | ✅ |
| `STATUS_OPT_FBIO` | `0x021C14` | 0 | `0x00000000` | ✅ |
| `STATUS_OPT_FBP` | `0x021D38` | 240 = `0xF0` | `0x000000F0` | ✅ |

**11/11 word khớp chính xác. Dữ liệu lưu là tin cậy.**

### 1.2 Hằng số poison

```
0xBADF5040   0xBADF1300   0xBADF1100
```
`stats`: 3072 word, 352 có dữ liệu, 2202 poison, 518 zero.

---

## 2. Giải mã bit — fuse tự nhất quán tuyệt đối

Quy ước: **bit = 1 nghĩa là BỊ TẮT** (disabled).

```
STATUS_OPT_GPC  0x021C1C = 0x38 = 0b00 111000   popcount=3
                              bit:  5 4 3  ->  GPC3, GPC4, GPC5 disabled

STATUS_OPT_TPC_GPC0 = 0x20 = 0b100000   bit 5  -> TPC5 disabled
STATUS_OPT_TPC_GPC1 = 0x00 = 0b000000   none
STATUS_OPT_TPC_GPC2 = 0x00 = 0b000000   none
STATUS_OPT_TPC_GPC3 = 0x3F = 0b111111   all 6
STATUS_OPT_TPC_GPC4 = 0x3F = 0b111111   all 6
STATUS_OPT_TPC_GPC5 = 0x3F = 0b111111   all 6
```

### 2.1 Kiểm chứng tính nhất quán (không thể là ngẫu nhiên)

TU106 có **3 GPC** (GPC0/1/2), không có GPC3/4/5.

| Quan sát | Ý nghĩa |
|---|---|
| `STATUS_OPT_GPC = 0x38` bật bit 3,4,5 | = **đúng 3 GPC không tồn tại trên TU106** |
| `GPC3/4/5` có TPC mask `0x3F` | = tắt cả 6 TPC của GPC không tồn tại |
| `GPC1/2` có TPC mask `0x00` | = không tắt gì, đủ 6 TPC |
| `GPC0` có TPC mask `0x20` | = **chỉ tắt TPC5** |

**Bốn quan sát độc lập cùng khớp một mô hình duy nhất.** Xác suất trùng hợp ngẫu nhiên coi như bằng 0.
Đây là bằng chứng **ngữ nghĩa bit đúng**, không phải suy từ "trùng số".

### 2.2 Số học đóng kín

```
TPC hiệu lực = GPC0:5 + GPC1:6 + GPC2:6 = 17 TPC
             = 17 × 2 SM = 34 SM
             = 34 × 64 CUDA = 2176 CUDA cores

TU106 đầy đủ = 3 × 6 = 18 TPC = 36 SM = 2304 CUDA
Chênh lệch   = 1 TPC = 2 SM = 128 CUDA cores
```

**Đúng bằng con số "128 CUDA cores còn thiếu" của đề bài.**

---

## 3. Đối chiếu với RM effective mask — KHỚP CHÍNH XÁC

| GPC | Fuse nói | RM effective mask | Khớp |
|---|---|---|---|
| GPC0 | TPC5 tắt → 5 TPC sống → bit 0..4 | **`0x1F`** | ✅ |
| GPC1 | không tắt TPC nào → 6 TPC → bit 0..5 | **`0x3F`** | ✅ |
| GPC2 | không tắt TPC nào → 6 TPC → bit 0..5 | **`0x3F`** | ✅ |

`0x1F` = `0b011111` = TPC0–TPC4 bật, **TPC5 tắt**.
`0x3F` = `0b111111` = cả 6 bật.

Tổng bit bật: `popcount(0x1F) + popcount(0x3F) + popcount(0x3F) = 5+6+6 = 17` = 17 TPC = **34 SM**.

> **Fuse, RM và hardware đều nói 17 TPC. Không có mâu thuẫn nào.**

Điều này khớp với chuỗi đã truy ở T8: `tpcMask[gpcId]` ← bitmap `s2+0x3E0` ← GSP static info ← `NV2080_CTRL_CMD_INTERNAL_STATIC_KGR_GET_FLOORSWEEPING_MASKS` (`0x20800A26`).

---

## 4. Đối chiếu với hardware GR — phép kiểm mạnh nhất

Đọc trực tiếp qua BAR0, read-only, địa chỉ từ nouveau `gf100.h` (đã kiểm toán).

### 4.1 `NV_PGRAPH` GPC count — `0x409604`

```
0x409604 = 0x08040003
  bits[5:0]  = 0b000011 = 3        -> gpc_nr = 3
  bits[27:24]= 0x8                -> physical GPC count encoded = 8
```

3 GPC đang hoạt động. Khớp `STATUS_OPT_GPC = 0x38`.

### 4.2 Số TPC mỗi GPC — `GPC_UNIT(g, 0x2608)`

Công thức nouveau: `GPC_UNIT(t,r) = 0x500000 + t*0x8000 + r`

| GPC | Địa chỉ | Raw | TPC count | Trạng thái |
|---|---|---|---|---|
| GPC0 | `0x502608` | `0x00040005` | **5** | LIVE |
| GPC1 | `0x50A608` | `0x00040006` | **6** | LIVE |
| GPC2 | `0x512608` | `0x00040006` | **6** | LIVE |
| GPC3 | `0x51A608` | `0xBADF2023` | — | **POISON** |
| GPC4 | `0x522608` | `0xBADF2024` | — | **POISON** |
| GPC5 | `0x52A608` | `0xBADF2025` | — | **POISON** |

**Tổng = 5 + 6 + 6 = 17 TPC = 34 SM.**

### 4.3 Cross-check độc lập — `GPC_UNIT(g, 0x0C50)`

| GPC | Raw |
|---|---|
| GPC0 | `0x00000007` |
| GPC1 | `0x00000007` |
| GPC2 | `0x00000007` |
| GPC3/4/5 | POISON |

Ba GPC sống trả về cùng giá trị `0x7`. Ba GPC không tồn tại trả poison. Nhất quán.

### 4.4 Nhất quán ở cấp GPC block — `GPC_UNIT(g, 0x0000)`

```
GPC0 0x500000 = 0x8700029F  LIVE
GPC1 0x508000 = 0x8700029F  LIVE
GPC2 0x510000 = 0x8700029F  LIVE
GPC3 0x518000 = 0xBADF2023  POISON
GPC4 0x520000 = 0xBADF2024  POISON
GPC5 0x528000 = 0xBADF2025  POISON
```

Ba GPC sống trả **cùng một giá trị** `0x8700029F` — block hoàn toàn giống nhau.

---

## 5. Ba nguồn độc lập, một kết quả

| Nguồn | Cách đo | Kết quả |
|---|---|---|
| **Fuse** | `STATUS_OPT_TPC_GPC0..2` | 5 + 6 + 6 = **17 TPC** |
| **RM effective mask** | `tpcMask[0..2]` | `0x1F`/`0x3F`/`0x3F` → **17 TPC** |
| **Hardware GR** | `GPC_UNIT(g,0x2608)` | 5 + 6 + 6 = **17 TPC** |

**Ba phương pháp hoàn toàn khác nhau, cùng ra 17 TPC = 34 SM = 2176 CUDA.**

Không còn chỗ cho sai số giải mã. Chuỗi fuse → GSP → RM → hardware **đóng kín**.

---

## 6. Điều dữ liệu này KHÔNG trả lời

| Câu hỏi | Trạng thái |
|---|---|
| TPC5 tắt vì lý do gì? | **CHƯA** — xem `TPC5_DEFECT_REGISTER_EVIDENCE.md` |
| TPC5 có transistor vật lý không? | **CHƯA** — cần phép đo khác |
| TPC5 có chạy được nếu bật? | **CHƯA** — chưa thử, không được thử |

§2–§5 chỉ chứng minh **cơ chế tắt hoạt động đúng và nhất quán**. Không chứng minh **lý do**.

---

## 7. Artifact

| File | Nội dung |
|---|---|
| `TPC5_RAW_FUSE_COMPARISON.md` | File này |
| `TPC5_DEFECT_REGISTER_EVIDENCE.md` | Truy register defect + 5 ứng viên |
| `TPC5_RECOVERABILITY_VERDICT.md` | Phân loại silicon + khả năng phục hồi |
| `tpc5_read.py`, `tpc5b.py`, `tpc5_gr.py`, `tpc5_tpc.py` | Script đọc read-only (trên target `/tmp/`) |
