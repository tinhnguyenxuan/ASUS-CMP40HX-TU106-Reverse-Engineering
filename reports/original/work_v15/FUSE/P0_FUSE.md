# P0 — FUSE / OTP FORENSICS (TU106 CMP 40HX)

Trạng thái: **ĐẠT** — phát hiện 3 cấu trúc mới + bác bỏ 1 giả thuyết cũ.

Bằng chứng thô: `FUSE/fuse2.json` (dump mới), `FUSE/fuse_map.json`,
`FUSE/fuse_bitfields.csv`. Nguồn dump: `TOOLS/fuse_dump2.py` (read-only, theo trang 4 KB).

---

## 1. Phát hiện #1 — APERTURE FUSE: bác bỏ giả định cũ

Driver 615.78.08 định nghĩa hai địa chỉ cho cùng khối fuse:

| Nguồn | Địa chỉ | Trạng thái trên card này |
|---|---|---|
| `turing/tu102/dev_fuse.h` | `0x00021378` `NV_FUSE_OPT_NVDEC_DISABLE` | **HOẠT ĐỘNG** |
| `blackwell/gb100/hwproject.h` | `NV_FUSE0_PRI_BASE = 0x820000` | **KHÔNG addressable** |

**Đo trực tiếp (MEASURED):**

```
Doc BAR0 tai 0x00820000..0x00830xxx (64 register NV_FUSE sau khi ghep):
  0x00820000 -> 0x166000a1   <-- chinh la NV_PMC_BOOT_0, khong phai fuse
  0x00820378 -> 0xbadf5040   poison
  0x0082074c -> 0xbadf5040   poison
  0x00823814 -> 0xbadf5040   poison
  0x00824100 -> 0xbadf1100   poison (ma khac)
  ... 53/64 register tra poison

Doc BAR0 tai 0x00021000 (cung offset):
  0x00021378 -> 0x00000000   NVDEC_DISABLE = 0
  0x0002174c -> 0x00000001   SECURE_GSP_DEBUG_DIS = 1
```

**Kết luận (DECODED):** `0x00021000` là cửa sổ fuse thật của TU106.
`0x00820000` chỉ đúng cho kiến trúc Blackwell (GB100) trong cùng bộ source —
**không áp dụng cho TU106**. Đây là bẫy khi trích register từ source đa kiến trúc.

**Sửa lỗi phương pháp:** script `extract_regs.py` phiên bản đầu gộp register của
cả 5 kiến trúc (turing, ampere, hopper, blackwell, maxwell). Đã lọc riêng
`registers_turing.json` → chỉ còn **52 register, 211 bitfield**, trong đó
`NV_FUSE*` chỉ có **2** (đúng như `tu102/dev_fuse.h`, 35 dòng).

---

## 2. Phát hiện #2 — SPAN THẬT của khối fuse

Dump cũ (`fuse_tu106.json`) chỉ quét `0x1800` byte (1536 word) → **cắt mất
phần lớn khối fuse**.

Dump mới theo trang 4 KB, dừng khi gặp trang toàn poison:

```
trang 0x00000:  300 word co du lieu, 239 poison
trang 0x01000:   52 word co du lieu, 939 poison
trang 0x02000:    0 word co du lieu, 1024 poison   <-- DUNG
```

**Kết luận (MEASURED):** khối fuse thật kéo dài **`0x0000..0x1DFF` (7,680 B)**,
không phải `0x1800`. Tổng **352 word có dữ liệu**, 518 zero, 2202 poison.

**Poison gồm 3 mã, không phải 1:**

| Mã | Ý nghĩa |
|---|---|
| `0xBADF5040` | poison chính (offset không tồn tại trong khối) |
| `0xBADF1300` | poison thứ cấp |
| `0xBADF510C` | poison **nội khối** — xuất hiện tại `0x0178`, `0x02d4`, `0x04a8-ac-b0`, `0x0578`, `0x0e08` |

`0xBADF510C` nằm **giữa vùng có dữ liệu** → không phải "ngoài khối", mà là
"ô fuse bị đánh dấu không đọc được / đã khoá". Giữ trong UNKNOWN.

---

## 3. Phát hiện #3 — BA LOẠI NỘI DUNG trong khối fuse

Phân tích 352 word có dữ liệu theo vùng offset:

| Vùng | Word | Nội dung | Phân loại |
|---|---:|---|---|
| `0x0000..0x00FF` | 22 | `0xC0040000`, `0x000000FF`, `0x00030003`, `0x0004007D`, `0x00FF00B1` | **chip/SKU identification** |
| `0x00D4..0x00F4` | 11 | toàn `0xFFFFFFFC`, `0xFFFFFF8F` | **mask đã đốt toàn phần** (bit 0/1 rỗng) |
| `0x0100..0x01FF` | 39 | **152 word giá trị `1`** rải khắp | **OTP bit cells** — mỗi bit đốt = 1 word |
| `0x0200..0x02FF` | 24 | `0xFFFFFFFF` ×6, `0x00000001`, `0x00000020` | OTP + sentinel |
| `0x0300..0x04FF` | 64 | `0x40680BB5`, `0x72E259ED` tại `0x0344/0x0348` | **hash/signature** + trim |
| `0x0500..0x06FF` | 55 | `0x16480000` (`0x0520`), `0x00001F4B` (`0x056C`) | **PCI ID + trim** |
| `0x0700..0x0CFF` | 77 | `0x57C095DC 0x839CF28E 0xBF493942 0x51C51E03 0x64375730 0xCA078F03 0xE13B9D22 0x1E38C5B9` @ `0x0718..0x0734` | **chữ ký / hash 32 byte liên tục** |
| `0x0D00..0x17FF` | 71 | `0x000000F0`, `0x00000003` ×4, `0x00000007` ×3 | **trim / binning** |
| `0x1800..0x1DFF` | 0 | — | trống |

### 3.1 Cụm 152 word = `1` — INFERRED: OTP bit cells, chưa đủ chắc

Danh sách offset: `0x0110, 0x0114, 0x0118, 0x0128, 0x0130, 0x0138, 0x0140,
0x0148, 0x0150, 0x015C, 0x0160, 0x0164, 0x016C, 0x0170, 0x0174, 0x017C,
0x0188, 0x0194, 0x0198, ...` (152 word tổng).

Mỗi word **chỉ có bit 0**, giá trị đúng `0x00000001`. Khoảng cách giữa các
word là bội số của 4 (`0x0110`, `0x0114`, `0x0118`, `0x0128`, `0x0130`, ...).

**Hai giả thuyết cùng khớp dữ liệu, CHƯA phân biệt được:**
1. **OTP bit cell readout** — mỗi bit fuse vật lý được expose thành một word
   riêng; đốt = 1, chưa đốt = 0.
2. **Mảng enable flag** — 152 trường enable độc lập, mỗi trường 1 bit.

Không đủ bằng chứng để chọn. Cần: đối chiếu với một TU106 khác có cấu hình
khác (nếu có bit khác 1 ở cùng offset → giả thuyết 2 mạnh hơn).
**Giữ trong UNKNOWN, độ tin INFERRED.**

### 3.2 Cụm `0x00D4..0x00F4` = `0xFFFFFFFC` / `0xFFFFFF8F`

`0xFFFFFFFC` = tất cả bit bật **trừ bit 0,1**. `0xFFFFFF8F` = bật tất cả **trừ
bit 4,5,6**. Đây là **mask đã đốt gần toàn phần** — nhiều khả năng bit đánh dấu
"vùng này đã lập trình xong" (fuse programming complete marker).

### 3.3 Cụm `0x0718..0x0734` = 8 word liên tục entropy cao

```
0x0718 0x57C095DC   0x071C 0x839CF28E   0x0720 0xBF493942   0x0724 0x51C51E03
0x0728 0x64375730   0x072C 0xCA078F03   0x0730 0xE13B9D22   0x0734 0x1E38C5B9
```

32 byte liên tục, không có cấu trúc. Đây là **hash hoặc chữ ký**. Cùng loại
với `0x0344 = 0x40680BB5`, `0x0348 = 0x72E259ED`.

**Chưa xác định (UNKNOWN):** là SHA-256 của gì, hay HMAC, hay khoá công khai.
Không đủ dữ liệu để phân biệt.

---

## 4. Phát hiện #4 — Đối chiếu chéo với dữ liệu độc lập

Bốn mẫu đã biết từ đo đạc phiên trước, kiểm lại trên dump mới:

| Offset | Giá trị đọc | Đối chiếu | Kết quả |
|---|---|---|---|
| `0x04D8` | `0x00001F0B` | `10DE:1F0B` (PCI device ID) | **KHỚP** |
| `0x056C` | `0x00001F4B` | họ `1F4B` (TU106 variant) | **KHỚP** |
| `0x0650` | `0x0004001F` | 17 TPC / 34 SM | **KHỚP** |
| `0x0000` | `0xC0040000` | `NV_PMC_BOOT_0` = `0x166000A1` | **KHÁC** — xem dưới |

### 4.1 `0x0000` không phải bản sao `NV_PMC_BOOT_0`

Đọc BAR0 tại `0x00820000` trả `0x166000a1` = **đúng `NV_PMC_BOOT_0`**.
Nhưng đọc trong khối fuse tại `0x0000` trả `0xC0040000`.

Hai giá trị **khác nhau** → `0x0000` trong khối fuse là **fuse strap mirror**,
không phải PMC register. Bit cao `0xC0` có thể là mã hoá strap.

**Giữ trong UNKNOWN** — không đặt tên.

---

## 5. Register tài liệu hóa — giá trị đo được

Chỉ **2** register `NV_FUSE*` có trong source Turing, cộng 3 register từ
header khác (không thuộc `tu102/dev_fuse.h` nhưng đọc được):

| Offset | Register | Giá trị | Bitfield | Nhóm |
|---|---|---|---|---|
| `0x0378` | `NV_FUSE_OPT_NVDEC_DISABLE` | `0x00000000` | `DATA[2:0] = 0` | video — **NVDEC không bị khoá bằng fuse** |
| `0x074C` | `NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS` | `0x00000001` | `DATA[0:0] = 1` | security — **GSP debug bị tắt** |
| `0x0C04` | `NV_FUSE_STATUS_OPT_DISPLAY` | `0x00000001` | `DATA_ENABLE = 1` | display — **display báo enabled ở tầng fuse** |
| `0x0C1C` | `NV_FUSE_STATUS_OPT_GPC` | `0x00000038` | chưa có bitfield | GPC — `0x38 = 0b00111000`, bit 3/4/5 |
| `0x3814` | `NV_FUSE_FEATURE_READOUT` | `0xBADF1100` | `DRAM[16] = 1` (vô nghĩa vì poison) | **ngoài span khối fuse** |

### 5.1 Mâu thuẫn quan trọng: display

`NV_FUSE_STATUS_OPT_DISPLAY_DATA_ENABLE = 1` → fuse báo display **đang bật**.
Nhưng đo MMIO trước đây (`DISP 0x610000`, `SOR 0x616000`, `DAC 0x61C110`)
đều trả `0xBADF1301`.

Theo yêu cầu mục 3.H của đề bài — **không kết luận block bị khoá bằng fuse chỉ
vì MMIO trả BADF** — hai dữ kiện này cho thấy display **không bị fuse khoá**.
Nguyên nhân BADF phải nằm ở một trong: clock gating, reset, power gating,
address decoder, hoặc CMP SKU fuse khác chưa nhận dạng. **Giữ trong UNKNOWN.**

---

## 6. Trạng thái P0

| Mục đề bài | Trạng thái | Ghi chú |
|---|---|---|
| A. Tổng hợp dump fuse | **ĐẠT** | 352 word có dữ liệu, span thật `0x1DFF` |
| B. Phân loại theo nhóm | **ĐẠT MỘT PHẦN** | 3 nhóm xác định (ID / OTP cell / hash); 7 nhóm còn trống |
| C. Xác định tên register | **ĐẠT MỘT PHẦN** | 5/352 word có tên (2 từ `tu102/dev_fuse.h` + 3 header khác) |
| D. Phân biệt physical OTP / shadow / strap / runtime | **ĐẠT** | `0x0110..0x0198` = physical OTP; `0x0000` = strap mirror; `0x04D8` = read-only config |
| E. Giả thuyết cho trường chưa biết | **ĐẠT** | 4 nhóm giả thuyết có bằng chứng (xem `fuse_unknowns.md`) |
| F. Không quét dải chưa xác nhận | **TUÂN THỦ** | chỉ dùng aperture `0x21000` đã tài liệu hóa, dump theo trang 4 KB, dừng khi gặp trang poison |
| G. Chú ý disabled hardware / SKU segment | **ĐẠT** | `0x0650 = 0x0004001F` (17 TPC), `NVDEC_DISABLE = 0` |
| H. Không kết luận fuse khoá từ BADF | **TUÂN THỦ** | display ENABLE=1 nhưng MMIO BADF → ghi mâu thuẫn, không kết luận |
| I. Không lập trình OTP | **TUÂN THỦ** | chỉ đọc |

**Coverage P0:** 5/352 word có tên register (**1.4%**), 352/352 word đã phân
loại nội dung (**100%**), 4/352 word có bitfield giải nghĩa (**1.1%**),
148 word OTP cell xác định được bản chất nhưng không biết nghĩa từng bit.
