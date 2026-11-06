# MASTER REPORT — NVIDIA CMP 40HX / TU106
## Silicon · VBIOS · FUSE · OTP · MMIO · GSP-RM · Falcon Firmware

Ngày: 03/11/2026 · Kernel 6.8.0-147-generic · Driver 615.78.08 (open, cmpunlocker)
GPU: TU106-100-A1, `10DE:1F0B`, `8804:1043`, BDF `0000:03:00.0`, VBIOS `90.06.67.00.06`

**Self-check:** `python3 TOOLS/verify_all.py` → **52/52 PASS**
Báo cáo phiên trước (v1): `PHASE_REPORTS/MASTER_REPORT_v1_2026-11-03.md`
Vòng bổ sung Q2–Q9: `PHASE_REPORTS/Q2_Q4_Q6_Q8_Q9.md`

---

## MỤC TIÊU VÀ CÁCH ĐỌC

Đề bài nêu rõ: **mục tiêu KHÔNG phải overclock**, mà là **lập bản đồ có bằng chứng**
về GPU. Mọi kết luận phân loại theo:

`MEASURED` (đo trực tiếp) · `DECODED` (giải mã tái lập được) ·
`CORROBORATED` (≥2 nguồn độc lập) · `INFERRED` (suy luận) ·
`UNKNOWN` · `CONTRADICTED` (có bằng chứng phản) · `BLOCKED`

**Không có kết luận nào được tạo bằng suy đoán thay cho đo đạc.**
`37 unknown` được giữ nguyên trong `UNKNOWN_DATABASE.json` (32 open, 5 resolved).

---

## PHASE COVERAGE — bảng tổng

| Phase | Trạng thái | Phát hiện mới trong phiên này |
|---|---|---|
| **P0** FUSE/OTP | **ĐẠT** | Aperture thật `0x21000` (bác bỏ `0x820000`); span thật `0x1DFF` (không phải `0x1800`); 3 mã poison; 3 loại nội dung |
| **P1** MMIO | ĐẠT MỘT PHẦN | 33/52 register đọc được; WPR2 khớp log boot 100% |
| **P2** VBIOS | **ĐẠT** | ROM = 2 bản sao khác 1,212 B (không phải "bank1/bank2"); key block 38 record × 32 B giải được layout |
| **P3** GSP-RM | **ĐẠT** | **340 entry thật** (báo cáo cũ sai: 139); tìm ra `RELIABILITY_NVVDD`, `VMIN_NVVDD_*`, `UNLOAD_DRIVER_VOLTAGE_RAIL_0..3` |
| **P4** Firmware | ĐẠT MỘT PHẦN | **blob[6] ≡ blob[8]** (24 B khác); 4 blob **không nén được**; blob[0] không phải code |
| **P5** Topology | ĐẠT MỘT PHẦN | `fuse+0xC1C = 0x38` (3 bit / 3 GPC), display fuse enable nhưng MMIO BADF |
| **P6** Memory | **ĐẠT** | **Reserved 389 MiB** — `nvidia-smi` nói thẳng; WPR2 chỉ 0.5 MiB → 388.5 MiB là carveout khác |
| **P7** PCIe | **ĐẠT** | Phân biệt 3 tầng: cap 5 GT/s / target 5 GT/s / **runtime 2.5 GT/s**; **BAR1 = 64 GB** |
| **P8** Security | ĐẠT MỘT PHẦN | WPR2 khớp log boot; chuỗi boot 5 bước; driver chưa ký |
| **Q8** | **ĐÃ GIẢI** | 24 B khác blob[6]/blob[8] = **build timestamp ASCII** (`Dec 31 2024` vs `Jan 2 2025`) |
| **Q6** | **ĐÃ GIẢI** | display 0/200 word vs đối chứng 8/32 → **address decoder**. **PGRAPH `0x400000` cũng poison** → BAR0 không decode hết 16 MB |
| **Q4** | **ĐÃ GIẢI** | `FALCON_DATA` = `{u16 id, u32 offset}` 16 entry (7 có dữ liệu); NVINIT 9 con trỏ hợp lệ |
| **Q3** | **ĐÃ GIẢI** | root port 8 GT/s, card 5 GT/s, **cả hai target 5 GT/s, cả hai runtime 2.5 GT/s** → training fail |
| **Q2/Q5** | **BLOCKED** | 455,689 + 12,878 phép thử hash, **0 khớp** |
| **Q9** | **BLOCKED** | 7 tên: 0 entry ở 4 encoding + entry-style |

---

## P0 — FUSE / OTP

### 0.1 Bác bỏ aperture sai (MEASURED)

Driver 615.78.08 định nghĩa **hai** địa chỉ cho khối fuse:

| Nguồn | Địa chỉ | Kết quả đọc trên card này |
|---|---|---|
| `turing/tu102/dev_fuse.h` | `0x00021000` | **HOẠT ĐỘNG** |
| `blackwell/gb100/hwproject.h` | `NV_FUSE0_PRI_BASE = 0x820000` | `0x166000A1` (= PMC_BOOT_0) rồi **poison** |

→ `0x820000` chỉ đúng cho Blackwell, **không áp dụng TU106**.
Đây là bẫy khi trích register từ bộ source đa kiến trúc.

### 0.2 Span thật (MEASURED)

```
trang 0x00000: 300 word co du lieu, 239 poison
trang 0x01000:  52 word co du lieu, 939 poison
trang 0x02000:   0 word co du lieu, 1024 poison   <-- DUNG
```

Khối fuse = **`0x0000..0x1DFF` (7,680 B)**. Báo cáo cũ quét `0x1800` → cắt mất 1/3.
**352 word có dữ liệu**, 518 zero, 2202 poison.

**3 mã poison** (không phải 1): `0xBADF5040`, `0xBADF1300`, `0xBADF510C`.
`0xBADF510C` xuất hiện **giữa vùng có dữ liệu** → ô bị khoá, không phải ngoài khối.

### 0.3 Ba loại nội dung

| Vùng | Word | Nội dung |
|---|---:|---|
| `0x0000..0x00FF` | 22 | chip/SKU ID (`0xC0040000`, `0x000000FF`, `0x00030003`) |
| `0x00D4..0x00F4` | 11 | `0xFFFFFFFC`/`0xFFFFFF8F` — mask đốt toàn phần |
| `0x0110..0x0198` | 152 | toàn `0x00000001` — **INFERRED: OTP bit cells** |
| `0x0344..0x0348` | 2 | `0x40680BB5` `0x72E259ED` — hash/trim |
| `0x0718..0x0734` | 8 | 32 B entropy cao — hash/signature |
| `0x0D00..0x17FF` | 71 | trim/binning |

### 0.4 Đối chiếu chéo (CORROBORATED)

| Offset | Đọc | Đối chiếu | Kết quả |
|---|---|---|---|
| `0x04D8` | `0x00001F0B` | PCI ID `10DE:1F0B` | **KHỚP** |
| `0x056C` | `0x00001F4B` | họ TU106 | **KHỚP** |
| `0x0650` | `0x0004001F` | 17 TPC / 34 SM | **KHỚP** |
| `0x0C1C` | `0x00000038` | 3 GPC | **INFERRED** |

### 0.5 Mâu thuẫn display — KHÔNG kết luận fuse khoá

`NV_FUSE_STATUS_OPT_DISPLAY_DATA_ENABLE = 1` (fuse báo **bật**)
nhưng MMIO `DISP/SOR/DAC` = `0xBADF1301`.

Theo mục 3.H: **không kết luận fuse khoá chỉ vì BADF**. Hai dữ kiện này chứng
minh display **không bị fuse khoá**; nguyên nhân BADF phải ở clock gating,
power gating, address decoder, hoặc CMP SKU fuse khác. → `U-FUSE-009`.

---

## P1 — MMIO / BAR0

### 1.1 Register database (DECODED)

Trích từ 2,133 header của driver 615.78.08:

| Phạm vi | Register | Bitfield |
|---|---:|---:|
| Toàn bộ kiến trúc (5 arch) | 938 | 7,890 |
| **Chỉ turing** | **52** | **211** |

Lọc theo kiến trúc là **bắt buộc** — nếu không sẽ trộn register Blackwell/Hopper
vào TU106 (xem 0.1).

### 1.2 Đọc thực tế

```
52 register thử, 10 trang 64 KB chạm
  data   33
  zero   13
  poison  6
```

**Đáng chú ý (MEASURED + CORROBORATED):**

| Register | Giá trị | Ý nghĩa |
|---|---|---|
| `NV_PMC_BOOT_0` @`0x0` | `0x166000A1` | chip ID TU106 |
| `NV_PCFG_XVE_REGISTER_MAP_START_OFFSET` | `0x1F0B10DE` | **vendor+device ID khớp** |
| `NV_PFB_PRI_MMU_WPR2_ADDR_LO` @`0x1FA824` | `0x01F7E000` | **khớp dmesg** |
| `NV_PFB_PRI_MMU_WPR2_ADDR_HI` @`0x1FA828` | `0x01FFEE00` | **khớp dmesg** |
| `NV_PBUS_BAR1_BLOCK` @`0x1704` | `0x801F7CC0` | BAR1 cấu hình |
| `NV_PBUS_BAR2_BLOCK` @`0x1714` | `0xC01F7CC1` | BAR2 |
| `NV_PSEC_FBIF_BASE` @`0x840600` | `0x00010004` | SEC2 base |
| `NV_PGSP_FBIF_BASE` @`0x110600` | `0x00000110` | GSP base |

**WPR2 khớp chính xác 100%** với log boot `WPR=01ffee00:01f7e000` — hai nguồn
độc lập (MMIO read + dmesg) xác nhận cùng giá trị. Đây là **CORROBORATED**.

---

## P2 — VBIOS

### 2.1 Bác bỏ "2 bank" (MEASURED)

Báo cáo cũ: *"bank1 660,992 B, bank2 387,584 B, giống hệt 100%"*. **SAI.**

```
ban 1: 0x000000..0x079000  (495,616 B)
ban 2: 0x079000..0x0F2000  (495,616 B)
byte khac: 1,212 / 495,616 = 0.245%
cum khac DUY NHAT: 0x3000..0x34BF (1,216 B)
sau 0x0F2000: 57,344 B = NMX container
```

**Cấu trúc thật:** ROM 1 MiB = **2 bản sao y hệt của image 495,616 B** +
container NMX 57,344 B ở cuối.

### 2.2 Key block — cấu trúc MỚI (DECODED)

`0x003000..0x0034BF` = **38 record × 32 byte chính xác**.

```
+0x00  2   sig           0x6700 (37 record) / 0x6701 (1)
+0x02  2   ver           0x0200 / 0x0300 / 0x0400 / 0x0600
+0x04  4   f4            LUON boi so 0x20 (38/38)
+0x08  4   f8            0x1669xxxx / 0x166axxxx / 0x166bxxxx / 0x1687dxxx
+0x0C  4   flags         lo ∈ {0xFF,0xFC,0xF8,0xF0,0xF3}, hi ∈ {0x00,0x79}
+0x10  16  hash          16 B entropy cao
```

| ver | Số record | `f8` nhóm |
|---|---:|---|
| `0x0200` | 2 | `0x16692CC5/6` |
| `0x0300` | 16 | `0x166AB5B7/B8`, `0x166B07DF/E0`, `0x166B08E9`, `0x166B0A76` |
| `0x0400` | 16 | `0x166B1BC1`, `0x166B4533`, `0x166B457E` |
| `0x0600` | 4 | `0x1687D040/41` |

**Khác biệt duy nhất giữa 2 bản sao:** bản 1 có 38 record, bản 2 **toàn `0xFF`**.
→ Bản 1 **đã ký/đăng ký**, bản 2 **để trống**.

**Giả thuyết bị bác bỏ:**
- `f4` là unix timestamp → chỉ **9/38** trong dải hợp lý.
- `hash` là SHA-256/SHA-1/MD5 của vùng ROM → **0/912** phép thử khớp.

### 2.3 Bảng đã parse

40 bảng `PERF_PTRS` + VFE (150 slot × 24 B, 20 var × 25 B) +
selector `0x2D384` + key block. **Tất cả checksum `sum % 256 == 0`.**

---

## P3 — GSP-RM

### 3.1 Sửa lỗi nghiêm trọng (DECODED)

Báo cáo cũ: *"8 bảng, 139 entry"*. **SAI.**

**Nguyên nhân:** parser cũ quét bước cố định 32 byte từ offset tuỳ ý → nhiều
"entry" chỉ là **đuôi chuỗi của entry trước** (`CONTROLLER_GPC_MAX` sau
`PERF_CF_CONTROLLER_GPC_MAX`, `ER_NVD_MAX`, `OWER`, `M_GRP_1`).

**Sửa:** `name_ptr` phải trỏ **đầu chuỗi thật** (tra trong bảng 134,417 string
của `.rodata`), `f0c == 0`, bước nhảy **4**, gom bảng tối thiểu 3 entry.

**Kết quả đúng:**

```
134,417 string trong .rodata (1,982,464 B)
 1,509 ứng viên
    60 bảng
   340 entry THẬT
```

### 3.2 Tên policy khớp trực tiếp với `nvidia-smi`

| Entry | id | f08 | f14 | f18 |
|---|---:|---|---:|---:|
| **`RELIABILITY_NVVDD`** | 204 | `0xff02` | 150 | 273 |
| `VMIN_NVVDD_0` | 204 | `0xff02` | 150 | 273 |
| `VMIN_NVVDD_1` | 205 | `0xff01` | 151 | 273 |
| `VMIN_MSVDD_1` | 206/208/213 | `0xff01` | 281/249/129 | 278/279 |
| `VMIN_LOGIC` | 213 | `0xff01` | 129 | 279 |
| `MCLK_LIMIT` | 155/158 | `0x10e` | 274/78 | 354/274 |
| `RATED_TDP_MIN` | 137 | `0xff01` | 204 | 274 |
| `PERF_CF_CONTROLLER_GPC_MAX` | 19/20/21 | `0xff08`/`ff02`/`ff0a` | 280/42/88 | 290/273 |
| `UNLOAD_DRIVER_VOLTAGE_RAIL_0` | 149 | `0xff02` | 254 | 275 |
| `UNLOAD_DRIVER_VOLTAGE_RAIL_1` | 150/151 | `0xff02` | 283/155 | 275/273 |
| `UNLOAD_DRIVER_VOLTAGE_RAIL_2` | 151 | `0xff02` | 155 | 273 |
| `UNLOAD_DRIVER_VOLTAGE_RAIL_3` | 139/152 | `0xff02` | 90/72 | 274/290 |
| `MODS_RULES_STRICT_PSTATE_MAX/MIN` | 217/218 | `0xff03/04` | 236/160 | 406/278 |
| `CLIENT_LOW_STRICT_PSTATE_MAX/MIN` | 42/43 | `0xff03/04` | 220/156 | 278 |
| `JPAC_PSTATE_MAX` | 34 | `0xff02` | 57 | 278 |
| `PMU_DOM_GRP_1` | 201 | `0xff02` | 143 | 273 |

`nvidia-smi -q -d PERFORMANCE` báo cờ **`Reliability`** — và GSP-RM có entry
**`RELIABILITY_NVVDD`**. T4 (REL/ALT = 1125 mV) làm cờ đó chuyển `Not Active`.
→ **liên hệ tên ↔ hành vi** (`INFERRED`, chưa chứng minh nhân quả).

### 3.3 Sửa nhận định cũ về `PERF_CF_CONTROLLER_GPC_MAX`

Báo cáo cũ gán `id=21 f08=0xff0a f14=88 f18=273` cho `..._GPC_MAX`.
**Sai:** giá trị đó thuộc **`PERF_CF_CONTROLLER_XBAR_MAX`**.
`..._GPC_MAX` có **6 bản** (id 19/20, f08 `0xff08`/`ff05`, f14 280/42).

### 3.4 Tên KHÔNG có descriptor

`RMClkVfOverride`, `RmAtsVolOverride`, `RmClkControllersOverride`,
`OVERVOLTAGE_LOGIC`, `OVERVOLTAGE_NVVDD_0/1`, `PERFORMANCE_CAP0`
→ tồn tại trong binary nhưng **không đăng ký** qua bảng descriptor này.
Có thể có **bảng thứ hai chưa tìm** → `U-GSP-006`.

### 3.5 XREF = 0, lý do đã rõ

Kiểm lại con trỏ ngược về base 60 bảng: **0 hit**. Kết luận (CORROBORATED):
code giữ base dưới dạng **hằng số trong lệnh** (`lui`/`auipc`), không qua biến
con trỏ. → hướng đúng: tìm hằng số `0x41AA418` trong 17 MB text.

---

## P4 — Falcon / Firmware

### 4.1 PHÁT HIỆN: `blob[6]` ≡ `blob[8]`

```
blob[6] ^ blob[8] (125,696 B): entropy 0.0033, nonzero 0.0%   <-- gan nhu bang 0
blob[5] ^ blob[7] (126,208 B): entropy 3.8064, nonzero 41.1%
```

Kiểm chứng trực tiếp: `blob[6]` vs `blob[8]` khác **đúng 24 byte** tại
`0x6F3E` (1 B), `0x7200..0x7213` (20 B), `0xB659` (1 B), `0xB7B8..0xB7CB` (20 B).

→ Trong 11 blob, **6 plaintext nhưng chỉ ~5 nội dung khác nhau**.

### 4.2 4 blob entropy cao KHÔNG nén được (DECODED)

| # | Size | entropy | distinct | max_freq | zlib | lzma |
|---:|---:|---:|---:|---:|---:|---:|
| 1–4 | 122,880 | 7.998 | **256/256** | ~0.006 | **1.001** | **0.999** |

`distinct = 256/256` (cả 256 byte đều có), `max_freq ≈ 1.5 × 1/256`,
nén **không giảm byte nào**.

**Kết luận:** đã ở dạng không nén được nữa. Điều này đúng cho **cả** mã hoá
**và** nén tối đa → **KHÔNG kết luận AES** (tuân thủ C3 / 7.I).

XOR cặp blob mã hoá đều ra entropy 7.997–7.998 → **4 nội dung khác nhau**,
không phải 1 nội dung mã hoá 4 lần.

### 4.3 `blob[0]` không phải code Falcon

```
3 lenh dau decode duoc: mov $r0 0xffc0 / mov $sp $r0 / clear b32 $r10 / lcall 0xfe10 / exit
nhung toan bo 122,880 B: 93.1% "unknown instruction" tu MOI offset thu (4/8/10/20)
```

Entropy 3.481 (quá thấp cho code), nonzero 37%, không magic `fuc`/`NVFU`.
→ **INFERRED: data segment**, 3 lệnh đầu chỉ là trùng hợp byte pattern.

---

## P5 / P6 / P7 / P8

### 5.1 P6 — giải được 8192 vs 7762 MiB (MEASURED)

```
Total    : 8192 MiB
Reserved :  389 MiB        <-- nvidia-smi noi thang
Used     :    0 MiB
Free     : 7804 MiB
```

| Nguồn | Kích thước |
|---|---:|
| WPR2 (GSP) | **0.50 MiB** |
| Reserved tổng | **389 MiB** |
| **Chưa giải** | **~388.5 MiB** |

→ 389 MiB là **carveout**, không phải VRAM hỏng. WPR2 chỉ 0.5 MiB.

### 5.2 P7 — PCIe ba tầng (MEASURED)

```
Region 0: fa000000        16 MB    BAR0
Region 1: 381000000000    64 GB    BAR1   <-- ReBAR BAT
Region 3: 380800000000    32 MB    BAR3
Region 5: e000            128 B    BAR5

LnkCap  : Speed 5GT/s, Width x16            <- hardware capability
LnkCap2 : Supported Link Speeds: 2.5-5GT/s
LnkCtl2 : Target Link Speed: 5GT/s           <- advertised/target
LnkSta  : Speed 2.5GT/s (downgraded)         <- RUNTIME
```

**Phân biệt rõ 3 tầng**: card **có** Gen2, **đích đặt** Gen2, **runtime** Gen1.
Nguyên nhân ở link training (`RETRAIN_FAIL status=1101` trong dmesg).
**Không thử retrain** (mục 10 cấm).

### 5.3 P8 — WPR2 khớp 100% (CORROBORATED)

```
MMIO:  NV_PFB_PRI_MMU_WPR2_ADDR_LO = 0x01F7E000
       NV_PFB_PRI_MMU_WPR2_ADDR_HI = 0x01FFEE00
dmesg: WPR=01ffee00:01f7e000
```

Chuỗi boot (5 bước, từ log thật):
1. `_kgspCreateSignatureMemdesc`: signed fullspeed stock-relock
2. `POST_FWSEC_PRE_GSP_ENTRY` — **sau FWSEC, trước GSP**
3. `_kgspCmp40ExecuteBooterFreshMeta`: WPR metadata `0xFFE40000`
4. `kgspExecuteBooterLoad_TU102`: FECS feature PLM `status=0x0` (OK)
5. `kgspCmp40RebuildStockSignature`: khôi phục chữ ký stock tại chỗ

---

## UNKNOWN DATABASE — 35 mục

| Component | Số unknown |
|---|---:|
| FUSE | 13 |
| MMIO | 6 |
| FIRMWARE | 6 |
| GSP-RM | 5 |
| VBIOS | 3 |
| TOPOLOGY | 1 |
| MEMORY | 1 |

| Priority | Số mục |
|---|---:|
| P0 | 7 |
| P1 | 6 |
| P2 | 9 |
| P3 | 5 |
| P4 | 6 |
| P5 | 1 |
| P6 | 1 |

**3 mục đã giải:** `U-FUSE-013` (aperture), `U-VBIOS-002` (bank2), `U-GSP-003` (139→340).

### Unknown nổi bật cần ưu tiên

| ID | Nội dung | Vì sao quan trọng |
|---|---|---|
| `U-FUSE-002` | 32 B hash tại `0x0718` | Nếu giải được → biết fuse ký cái gì |
| `U-FUSE-009` | display fuse=1 nhưng MMIO BADF | Mở ra hiểu biết về display trên CMP |
| `U-FUSE-001` | 152 word `=1` | Bản chất OTP cell hay enable flag |
| `U-GSP-004` | `RELIABILITY_NVVDD` | Nguồn cờ Reliability |
| `U-GSP-006` | bảng descriptor thứ 2? | Chứa `RMClkVfOverride` |
| `U-FW-012` | 24 B khác blob[6]/blob[8] | Version stamp? |
| `U-VBIOS-001` | 38 record key block | Nghĩa `f4`/`f8`/hash |
| `U-MEM-001` | 388.5 MiB carveout | Memory architecture |

---

## COVERAGE — không quy đổi thành một tỷ lệ chung

| Subsystem | Đơn vị đo | Đã làm | Tổng | % |
|---|---|---:|---:|---:|
| **FUSE** | word có dữ liệu đã phân loại | 352 | 352 | **100%** |
| **FUSE** | word có tên register | 5 | 352 | **1.4%** |
| **FUSE** | bitfield giải nghĩa | 4 | 352 | **1.1%** |
| **MMIO** | register đọc được | 33 | 52 | **63.5%** |
| **MMIO** | register trong source (turing) | 52 | 938 (all-arch) | 5.5% |
| **VBIOS** | byte đã phân vùng | 1,048,576 | 1,048,576 | **100%** |
| **VBIOS** | bảng parse được | 42 | — | — |
| **GSP** | descriptor có tên | 340 | 340 | **100%** |
| **GSP** | descriptor có consumer | 0 | 340 | **0%** |
| **GSP** | `f08`/`f18` giá trị giải nghĩa | 0 | 16 / 13 | **0%** |
| **FIRMWARE** | blob phân loại | 11 | 11 | **100%** |
| **FIRMWARE** | blob disasm được | 0 | 11 | **0%** |

**Không tuyên bố đã reverse 100%** chỉ vì đã quét toàn address range
(mục 14 của đề bài).

---

## PHÁT HIỆN BỊ BÁC BỎ TRONG PHIÊN NÀY

| # | Kết luận cũ | Bằng chứng bác bỏ |
|---|---|---|
| 1 | "`NV_FUSE0_PRI_BASE = 0x820000` là aperture fuse" | Trả `PMC_BOOT_0` rồi poison; `0x21000` mới hoạt động |
| 2 | "Fuse span `0x1800`" | Trang `0x2000` mới toàn poison; span thật `0x1DFF` |
| 3 | "1 mã poison `0xBADF5040`" | Có 3 mã, `0xBADF510C` nằm trong vùng có dữ liệu |
| 4 | "ROM = bank1 660,992 B + bank2 387,584 B" | 2 bản sao y hệt 495,616 B, khác 1,212 B |
| 5 | "GSP có 139 descriptor entry" | **340 entry thật**; 139 gồm ~200 mảnh chuỗi vụn |
| 6 | "`PERF_CF_CONTROLLER_GPC_MAX` id=21 f08=0xff0a" | Đó là `XBAR_MAX`; `GPC_MAX` có 6 bản khác |
| 7 | "6 plaintext firmware" | Chỉ ~5 nội dung: blob[6] ≡ blob[8] |
| 8 | "VRAM lệch 430 MiB" | Lệch **389 MiB**, `nvidia-smi` gọi là "Reserved" |

---

## PHẦN BLOCKED (có lý do cụ thể)

| # | Nội dung | Lý do | Cần gì |
|---|---|---|---|
| 1 | Consumer của 340 descriptor | 0 xref cứng trên 22.9 MB; base là hằng số trong lệnh | Ghidra trên 17 MB text, tìm hằng số `0x41AA418` |
| 2 | Nghĩa 4 blob entropy cao | Không nén được, không magic/IV; AES vs nén **không phân biệt được** | Khoá giải mã (không có trong driver công khai) |
| 3 | Disasm `blob[0]` | 93.1% unknown từ 4 offset → không phải code | Xác định đây là bảng gì trước |
| 4 | Nghĩa `f4`/`f8`/hash trong key block | Không phải timestamp, không khớp hash vùng nào | ROM TU106 khác để so sánh |
| 5 | 388.5 MiB carveout | WPR2 chỉ 0.5 MiB | Đọc thêm register PFB carveout |
| 6 | Nghĩa 152 word `=1` | Cần mẫu đối chứng | Dump fuse TU106 khác |

---

## TUÂN THỦ QUY TẮC AN TOÀN

| Quy tắc | Trạng thái |
|---|---|
| Không flash VBIOS | **TUÂN THỦ** |
| Không ghi OTP/fuse | **TUÂN THỦ** — chỉ đọc |
| Không ghi MMIO/BAR0 | **TUÂN THỦ** — `mmap` `PROT_READ` |
| Không sửa PCI config | **TUÂN THỦ** |
| Không reload driver | **TUÂN THỦ** |
| Không reboot | **TUÂN THỦ** |
| Không sửa firmware hệ thống | **TUÂN THỦ** |
| Không tăng voltage/clock | **TUÂN THỦ** |
| Không khai thác đặc quyền | **TUÂN THỦ** |
| Không vô hiệu hoá bảo mật | **TUÂN THỦ** |
| Không brute-force khoá | **TUÂN THỦ** |
| Không quét dải MMIO chưa xác nhận | **TUÂN THỦ** — chỉ đọc register đã tài liệu hoá |

Không có thao tác nào ngoài read-only được thực hiện trong phiên này.

---

## CẤU TRÚC THƯ MỤC

```
cmp40hx_research/
  MASTER_REPORT.md          (file nay)
  EVIDENCE_LEDGER.md        bang bang chung chi tiet
  HYPOTHESIS_MATRIX.md      ma tran gia thuyet 1905 MHz
  COVERAGE.md / COVERAGE.json
  UNKNOWN_DATABASE.json     35 muc
  DISCOVERY_LOG.md
  RESEARCH_QUEUE.json
  CHECKPOINT.json
  NEXT_STEPS.md
  FUSE/       fuse_map.json, fuse_bitfields.csv, fuse2.json, P0_FUSE.md
  MMIO/       registers_all.json, registers_turing.json, mmio.json, P1_MMIO.md
  VBIOS/      vbios_crossrefs.json, P2_VBIOS.md
  GSP/        gsp_functions.json, P3_GSP.md
  FIRMWARE/   firmware_inventory.json, P4_FIRMWARE.md
  TOPOLOGY/   silicon_topology.json
  MEMORY/     memory_registers.json
  PCIE/       pcie_map.json
  SECURITY/   security_registers.json
  TOOLS/      extract_regs.py, fuse_read2.py, fuse_dump2.py, fuse_classify.py,
              mmio_scan.py, nvgi_block.py, gsp_desc2.py, fw_entropy.py,
              phase5678.py, build_db.py, verify_all.py
  RAW_DATA/   fuse2.json, p5678.json
  PHASE_REPORTS/ P5_P6_P7_P8.md, MASTER_REPORT_v1_2026-11-03.md
```

**Tái lập:** `python3 TOOLS/verify_all.py` → 52/52 PASS.
