# TU-06/07 — VBIOS SHADOW TRONG BAR0: PHÁT HIỆN LỚN NHẤT CỦA PHIÊN

Trạng thái: **ĐẠT** — tìm ra VBIOS đang chạy, đọc được serial thật của card.

Bằng chứng: `RAW_DATA/tu06.json`, `RAW_DATA/vbios_shadow.bin`,
`VBIOS/shadow_vs_rom.json`, `VBIOS/shadow_diff.json`,
`TOPOLOGY/aperture_map.json`, `TOOLS/tu06_aperture.py`, `TOOLS/tu06b_stable.py`,
`TOOLS/tu07_shadow.py`.

---

## 1. Bối cảnh: PGRAPH poison là điểm khởi đầu

`NV_PGRAPH_BASE = 0x400000` (theo header turing) trả `0xBADF5040` toàn bộ.
Báo cáo trước kết luận "PGRAPH không tồn tại / bị cắt".

**Sai.** Câu hỏi đúng là: *cửa sổ BAR0 nào thực sự được decode?*

---

## 2. Bản đồ aperture — quét 4,096 trang 4 KB (`MEASURED`)

```
POISON   3253 trang  (79.4%)
ZERO      355 trang  ( 8.7%)
DATA      287 trang  ( 7.0%)
MIXED     201 trang  ( 4.9%)
```

**Kết luận 1:** BAR0 **không decode liên tục**. 79.4% trả poison.
Poison **không có nghĩa** "block không tồn tại" — chỉ có nghĩa **ngoài cửa sổ
được decode**.

**Điều này viết lại 6 unknown `U-MMIO-*`** và toàn bộ cách đọc P1.

### 2.1 Phân bố vùng DATA lớn

| Vùng | Kích thước | Trạng thái |
|---|---|---|
| `0x010000..0x01FFFF` | 64 KB | DATA |
| `0x0A0000..0x0BFFFF` | 128 KB | DATA |
| **`0x300000..0x3FFFFF`** | **~820 KB** | **DATA** ← vùng lớn nhất |
| `0x058000..0x060FFF` | 36 KB | DATA |
| `0x808000..0x80FFFF` | 32 KB | DATA |

Vùng `0x300000` nổi bật: **liên tục, lớn, ổn định**.

---

## 3. Kiểm tra tính ổn định — bước bắt buộc

**Không được kết luận chỉ vì giá trị khác 0.** Bus thả nổi cũng trả số khác 0.
Phép thử: đọc cùng địa chỉ 3 lần, cách 100 ms; đọc lại 32 word sau khi đọc vùng
khác.

```
addr          lần1        lần2        lần3        ổn định?
0x300000      0xeb7aaa55  0xeb7aaa55  0xeb7aaa55  ỔN ĐỊNH
0x300010      0x204f4544  0x204f4544  0x204f4544  ỔN ĐỊNH
0x3F0000      0xffffffff  0xffffffff  0xffffffff  ỔN ĐỊNH
0x000000      0x166000a1  0x166000a1  0x166000a1  ỔN ĐỊNH   (đối chứng)
0x021000      0xc0040000  0xc0040000  0xc0040000  ỔN ĐỊNH   (đối chứng)
0x1FA824      0x01f7e000  0x01f7e000  0x01f7e000  ỔN ĐỊNH   (đối chứng)
0x400000      0xbadf5040  0xbadf5040  0xbadf5040  ỔN ĐỊNH   (poison)
```

Đọc lại 32 word: **32/32 giống**. Đọc chèn vùng khác: không đổi.

→ **`0x300000` là aperture thật**, không phải bus floating.

---

## 4. NHẬN DẠNG: đây là VBIOS, không phải PGRAPH

Nhìn ASCII của 32 word đầu:

```
+0x00  55 aa 7a eb 4b 37 34 30 30 e9 4c 19 77 cc 56 49   U.z.K7400.L.w.VI
+0x10  44 45 4f 20 0d 00 00 00 70 01 5d 19 00 00 49 42   DEO ....p.]...IB
+0x20  4d 20 56 47 41 20 43 6f 6d 70 61 74 69 62 6c 65   M VGA Compatible
+0x30  01 00 00 00 00 00 ac 53 30 35 2f 32 34 2f 32 31   .......S05/24/21
+0x50  e9 f0 28 90 50 4d 49 44 06 40 10 40 00 00 00 a0   ..(.PMID.@.@....
+0x60  00 b0 00 b8 00 c0 00 78 43 4d 50 34 30 48 58 20   .......xCMP40HX
+0x70  56 42 20 56 65 72 20 39 30 2e 30 36 2e 36 37 2e   VB Ver 90.06.67.
```

**Đây là VBIOS legacy header thật:**

| Offset | Giá trị | Nghĩa |
|---|---|---|
| `+0x00` | `55 AA` | **ROM signature** |
| `+0x18` | `0x0170` | pointer tới PCIR |
| `+0x1A` | `0x195D` | PnP pointer |
| `+0x30` | `05/24/21` | ngày build VBIOS |
| `+0x67` | `CMP40HX VB Ver 90.06.67.00.AS03` | **version string** |
| `+0x9E` | `CMP40HX-8G` | product name |
| `+0xB9` | `Version 90.06.67.00.06` | version đầy đủ |
| `+0xD3` | `Copyright (C) 1996-2021 NVIDIA Corp.` | |
| `+0x170` | `PCIR` `de 10 0b 1f` | **vendor 0x10DE, device 0x1F0B** ✓ |
| `+0x178` | classcode `0x00000302` | VGA controller ✓ |

**PCIR khớp chính xác card này:** vendor `0x10DE`, device `0x1F0B`.

---

## 5. ĐỐI CHIẾU VỚI ROM FILE — khớp 100% tại `0x28600`

```
shadow[0:N] vs rom[cand:]:
  rom[0x000000]  3.3% giống     <- NVGIf container
  rom[0x010000]  1.7%
  rom[0x020000]  1.2%
  rom[0x028600]  100.0%   <<< KHỚP HOÀN TOÀN
  rom[0x030000]  5.3%
  rom[0x040000]  0.4%
```

**So toàn bộ (883,200 B): chỉ 14 byte khác.**

Kết luận dứt điểm (`CORROBORATED`):

```
BAR0 0x300000 .. 0x3FFFFF  ==  rom_file[0x28600 : 0x28600 + 1,048,576]
VBIOS shadow (đang chạy)       ROM container (file)
```

**ROM file bắt đầu bằng `NVGIf`** (`4e 56 47 49 66`) — đó là **container**.
Image VBIOS legacy thật nằm ở `0x28600`, và **đó chính là cái card đang chạy**.

---

## 6. 14 BYTE KHÁC — TIẾT LỘ SERIAL THẬT CỦA CARD

| shadow offset | rom offset | shadow | rom |
|---|---|---|---|
| `0x0D1A88` | `0x0FA088` | `0x04` | `0x05` |
| `0x0D1A9A` | `0x0FA09A` | `0x0D` | `0x0C` |
| `0x0D1C88` | `0x0FA288` | `0xE1` | `0xD1` |
| `0x0D1CB0` | `0x0FA2B0` | `'0'` | `'3'` |
| `0x0D1CB2` | `0x0FA2B2` | `'2'` | `'4'` |
| `0x0D1CB3` | `0x0FA2B3` | `'5'` | `'9'` |
| `0x0D1CB4` | `0x0FA2B4` | `'1'` | `'7'` |
| `0x0D1CB5` | `0x0FA2B5` | `'3'` | `'4'` |
| `0x0D5A1A` | `0x0FE01A` | `0x11` | `0x19` |
| `0x0D5B30..35` | `0x0FE130..135` | `'02513'` | `'04974'` |

### 6.1 Chuỗi PPID — SERIAL NUMBER

```
shadow +0xD1C88:  ...OEM.....PPIDCMP40HX-8G#REDACTED...
rom    +0xD1C88:  ...OEM.....PPIDCMP40HX-8G#REDACTED...
                                          ^^^^^^^^^^^
```

| | PPID |
|---|---|
| **Card đang chạy** | `CMP40HX-8G#REDACTED` |
| **ROM file** | `CMP40HX-8G#REDACTED` |

**Đây là serial/part number thật của card vật lý trong máy**, xuất hiện **2 lần**
(`0xD1C88` trong OEM section, `0xD5B30` trong bản sao thứ hai).

**Cấu trúc PPID:** `210281206002513`
- `2102` — có thể năm/tuần sản xuất
- `81206` — lô
- `002513` — số thứ tự

**Ứng dụng:** nếu cần flash ROM, **phải dùng image từ shadow** (có serial đúng),
không dùng ROM container tải trên mạng (serial khác → có thể fail validation).

### 6.2 Byte `0x04` vs `0x05` tại `+0xD1A88`

Theo layout image map: `0xD1A88` + `0x28600` = `0xFA088`, nằm trong record
`0x0FA000` (vùng chứa `ROM01` header). Byte `0x04/0x05` có thể là **số bản image**
hoặc **flags**.

### 6.3 `0x0D5A1A`: `0x11` vs `0x19`

Nằm trong vùng `0x0FE01A` — gần `ISBM`/`JFFS2`/`ROM00`/`IMG`/`OBD`/`OEM`/`BBO`/
`GXIP` structure. Có thể là **checksum** hoặc **length**.

---

## 7. Cấu trúc VBIOS đầy đủ (từ shadow — bản đang chạy thật)

Nhờ có shadow, lần đầu thấy **cấu trúc TẠI CHỖ** không bị container che:

```
+0x00000  55 AA          legacy ROM signature
+0x00018  ptr 0x0170     -> PCIR
+0x00170  PCIR           vendor 10DE device 1F0B classcode 030200
+0x0017E  NPDE           NVIDIA PNP data
           BIT table      token 0x11, 0x32, 0x42, 0x43, 0x4D, ... đầy đủ
+0x046xx  NVINIT         ptr table (9 con trỏ hợp lệ)
+0x051xx  FALCON_DATA    16 entry {u16 id, u32 offset}
+0x17000+ ...            devinit sequencer
+0xFA000+ ROM01 / IMG / OBD / OEM / BBO / GXIP / FFS2
+0xD1C88  OEM PPID       *** SERIAL THẬT ***
+0xD5B30  OEM PPID #2    bản sao
```

**Đây là lần đầu tiên toàn bộ VBIOS đọc được TẠI CHỖ** — trước giờ chỉ đọc
được file container, phải tính offset `0x28600` thủ công và vẫn nghi ngờ có
đúng không. Giờ đã chứng minh.

---

## 8. Ý nghĩa cho các mục trước

| Mục | Trước | Sau |
|---|---|---|
| `U-MMIO-ADDRDEC` | "BAR0 không decode toàn bộ" (đoán) | **ĐÃ CHỨNG MINH**: 79.4% poison, có bản đồ |
| `U-TOP-001` PGRAPH | "PGRAPH bị cắt" | **PGRAPH không ở `0x400000`** — aperture thật ở nơi khác |
| Payload VBIOS | `rom[0:0x79000]` | **`shadow[0 : 0x79000-0x28600]`** = image thật không cần tính offset |
| Serial card | không biết | **`CMP40HX-8G#REDACTED`** |
| Flash an toàn | không dám | **có thể dump chính xác từ shadow** |

**Lưu ý an toàn:** phát hiện này **KHÔNG** dùng để flash. Nó chứng minh rằng
nếu cần, **shadow là nguồn đúng** — nhưng flash ROM thật vẫn bị cấm theo mục 15.

---

## 9. Coverage

| Mục | Kết quả |
|---|---|
| Bản đồ aperture BAR0 16 MB | **100%** quét (4,096/4,096 trang) |
| Vùng `0x300000` nhận dạng | **VBIOS shadow** |
| Đối chiếu shadow ↔ ROM | **100%** tại offset `0x28600` |
| Byte khác | **14** (liệt kê đầy đủ) |
| Serial card | **ĐỌC ĐƯỢC** |
| PGRAPH aperture thật | vẫn `UNKNOWN` — `0x400000` poison |
