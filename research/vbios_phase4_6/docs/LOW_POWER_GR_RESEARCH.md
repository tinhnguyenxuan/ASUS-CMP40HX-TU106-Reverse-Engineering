# LOW POWER GR RESEARCH — Phase 5

> **Publication edition (V5):** This is a curated ROM/source-analysis extract from the supplied `vbiosrel6(2).zip`. Host telemetry, game tests, benchmark steps and Windows/Linux collectors are intentionally omitted. It is historical research, **not** new hardware verification. See [integrated report](../../../docs/TU106_VBIOS_PHASE4_6.md).


**Bảng:** P2 slot 32, envytools gọi là "LOW POWER GR". `ver=0x10, hlen=10, entry 5, count 5`,
extent `10 + 5*5 = 35` B, đóng chính xác lên slot 33 ở cả 3 ROM.

---

## 0. SỬA LỖI PHASE 4 — BIT 3, KHÔNG PHẢI BIT 27

Phase 4 viết "bit 27". Sai. Entry là **u32 little-endian**:

```
CMP    raw E7 FF FF FF 01  ->  u32 LE = 0xFFFFFFE7
GeForce raw EF FF FF FF 01 ->  u32 LE = 0xFFFFFFEF
XOR = 0x00000008  ->  bit 3
```

Đếm theo *vị trí byte* (`0xE7` vs `0xEF` ở byte thứ 4 tính từ trái) cho ra "bit 27/28" nếu
tính từ bit cao. Đếm theo **giá trị u32 little-endian** — cách đúng, vì đó là cách mọi
consumer đọc trường này — cho ra **bit 3**.

Đã sửa trong: `docs/TU106_POWER_THERMAL_REVERSE.md`, `docs/TU106_MULTI_ROM_SCHEMA_INFERENCE.md`,
`data/TU106_DECODED_FIELDS.csv`, `scripts/test_tu106_vbios.py`, và guard mới
`scripts/phase5/test_phase5.py::gr_mask_from_raw` (re-derive từ raw, assert không được là 27).

---

## 1. CẤU TRÚC

```
header 10 B : 10 0a 05 05 | 00 58 1b 01 00 01
                ^  ^  ^  ^   +4..+9 (6 B) — KHÔNG có tên
                |  |  |  entry_count = 5
                |  |  entry_size = 5
                |  header_size = 10
                version = 0x10

entry 5 B = u32 feature_mask (LE) + 1 byte thuộc tính
```

nvgpu (`bios.h:1187`) khai báo:

```c
struct nvgpu_bios_lpwr_gr_table_1x_header {
        u8 version, header_size, entry_size, entry_count, default_entry_idx;
        u16 idle_threshold_us;
        u8 adaptive_gr_multiplier;
};                                      /* 7 B */
struct nvgpu_bios_lpwr_gr_table_1x_entry { u32 feautre_mask; };   /* 4 B */
```

TU106: header **10** B (không 7), entry **5** B (không 4). ⇒ struct của nvgpu **không phủ**
bảng này. Không được áp nó rồi tuyên bố đã decode.

Header tail của TU106: `00 58 1b 01 00 01` — **giống hệt** ở cả 3 ROM. Không đặt tên.

---

## 2. NĂM ENTRY — DỮ LIỆU THẬT

| entry | CMP | 2060S | 2070 |
|---|---|---|---|
| 0 | `E7 FF FF FF` `01` | `EF FF FF FF` `01` | `EF FF FF FF` `01` |
| 1 | `E7 FF FF FF` `01` | `E7 FF FF FF` `01` | `E7 FF FF FF` `01` |
| 2 | `E6 FF FF FF` `00` | `E6 FF FF FF` `00` | `E6 FF FF FF` `00` |
| 3 | `E6 FF FF FF` `00` | `E6 FF FF FF` `00` | `E6 FF FF FF` `00` |
| 4 | `E5 FF FF FF` `00` | `E5 FF FF FF` `00` | `E5 FF FF FF` `00` |

Mask dạng u32: `0xFFFFFFE7`, `0xFFFFFFE6`, `0xFFFFFFE5`, `0xFFFFFFEF`.

**Khác biệt duy nhất giữa 3 ROM: entry 0, bit 3.** (CMP clear, cả hai GeForce set.)
Entry 1..4 giống hệt.

### 2.1 Bit nào được đặt tên

nvgpu chỉ đặt tên **hai** bit:

```c
#define NV_VBIOS_LPWR_GR_FEATURE_MASK_GR_MASK       GENMASK(0,0)   /* bit 0  */
#define NV_VBIOS_LPWR_GR_FEATURE_MASK_GR_RPPG_MASK  GENMASK(4,4)   /* bit 4  */
```

Đọc được: bit 0 **bật** ở mọi entry, mọi card. Bit 4 **tắt** ở mọi entry, mọi card.

⇒ Trong 5 entry này, hai bit có tên **không phân biệt gì**. Bit **duy nhất** khác nhau là
bit 3 — và bit 3 **không có tên** trong bất kỳ header công khai nào.

### 2.2 Bit 3 — những gì biết và không biết

| | |
|---|---|
| **Biết** | Là bit 3 của u32 LE, entry 0, bảng LOW POWER GR. CMP = 0, GeForce = 1. |
| **Biết** | `RPPG` (bit 4) là "Runtime Power/Performance Gating"-họ feature theo tên nvgpu. Bit 3 nằm **cạnh** nó. |
| **Biết** | Bảng tên "LOW POWER GR" ⇒ đây là feature của **graphics engine**, không phải display hay PCIe. |
| **Không biết** | Bit 3 bật/tắt cái gì. Không có enum, không có consumer, không có mô tả. |

**Giả thuyết có cơ sở (HYPOTHESIS):** các bit liền nhau trong một feature mask thường là các
feature gating cùng họ. Bit 3 nằm giữa bit 0 (GR) và bit 4 (RPPG). Nếu bit 4 = "cho phép
RPPG khi idle", bit 3 có thể là một cổng gating khác (ví dụ một dạng clock gating hoặc
power gating mức SM/TPC). **Nhưng đây là suy đoán theo vị trí, không phải bằng chứng.**

Điều **được phép nói:** CMP **không bật** một feature bit mà cả hai GeForce đều bật.
Điều **không** được nói: "CMP bị tắt RPPG" (sai — bit 4 tắt ở cả 3), "CMP bị throttle"
(không có telemetry), "bit 3 là RT lock" (không có cơ sở).

### 2.3 Byte thứ 5 (thuộc tính)

Entry 0 và 1 có `0x01`, entry 2..4 có `0x00`. **Giống nhau ở cả 3 ROM** ⇒ không phân biệt SKU.
Có thể là "entry này active" hoặc một index; **UNKNOWN**.

---

## 3. BẢNG NÀY ĐƯỢC AI DÙNG

Tra ba nguồn:

| nguồn | kết quả |
|---|---|
| `nvgpu` `bios.h` | có struct header/entry (7 B / 4 B) — **không khớp** TU106 |
| `nvgpu` `*.c` | **0 hit** — không có ai parse bảng này trong nguồn mở |
| `open-gpu-kernel-modules` `gpu/vbios/` | không có lpwr parser |
| nouveau `subdev/bios/` | không có file lpwr |
| `envytools/nvbios/` | chỉ có **tên** slot 32 trong `P2_tbls[]`, không có parser |

⇒ Consumer thật là **PMU firmware** hoặc **GSP-RM**, cả hai đóng.

**Điều này quan trọng:** không có nghĩa bảng vô dụng. Nghĩa là: mọi phát biểu về *tác động*
của bit 3 đều phải qua phép đo, không thể qua đọc source.

---

## 6. KẾT LUẬN

1. Sửa lỗi Phase 4: **bit 3**, không phải bit 27. Có guard tự động.
2. Bảng cấu trúc: header 10 B, 5 entry × 5 B, extent 35 B đóng chính xác.
3. **Chỉ một bit khác nhau giữa 3 ROM: entry 0 bit 3** (CMP clear, GeForce set).
4. Hai bit **có tên** (0 GR, 4 RPPG) **không** phân biệt gì — chúng giống nhau ở cả 3 card.
5. Bit 3 **không có tên** và **không có consumer công khai**. Mọi diễn giải là HYPOTHESIS.
6. Cách kiểm chứng rẻ nhất: thêm một ROM (CMP thứ hai hoặc GeForce khác hãng).
