# VBIOS FIELD REVERSE ENGINEERING — NVIDIA CMP 40HX / TU106

> **Bản lưu trữ lịch sử:** không phải kết luận cập nhật hay xác minh độc lập; xem [bảng đính chính và tiến triển Phase 1–6](../../../docs/TU106_VBIOS_PHASE1_5_HISTORY.md). Phép đo/test game thực tế đã lược khỏi bản xuất bản này.


**Phạm vi:** 3 ROM TU106 (1.047.040 B, `NVGI`)
**Môi trường:** đọc tĩnh, không flash, không MMIO write, không sửa driver.
**Script:** `scripts/tu106_vbios.py`, `scripts/export_fields.py`, `scripts/test_tu106_vbios.py`
**Dữ liệu:** `data/TU106_DECODED_FIELDS.csv` (1.275 dòng), `data/TU106_UNKNOWN_FIELDS.csv`
**Ngày:** 2026-11-07

Mọi kết luận dưới đây được gắn nhãn **PROVEN / STRONGLY SUPPORTED / HYPOTHESIS / UNKNOWN**.
Không có field nào được gọi là "RT lock", "unlock switch" hay "fuse override".

---

## 0. BA ROM VÀ ĐỊNH DANH

| | CMP 40HX | RTX 2060 SUPER | RTX 2070 |
|---|---|---|---|
| File | `TU106.rom` | `219827.rom` | `265590.rom` |
| SHA-256 (16) | `78435dca0ca0732b` | `ad231cef133f9385` | `560f2be1bee834c3` |
| PCI ID | `10DE:1F0B` | `10DE:1F06` | `10DE:1F07` |
| **Class code** | **`0x030200` 3D controller** | `0x030000` VGA | `0x030000` VGA |
| Kích thước | 1.047.040 | 1.047.040 | 1.047.040 |

`PCIR` đầu tiên ở `0x28770` (cả 3 ROM). Vendor/Device/Class **little-endian**, giống
layout config space. **PROVEN** (`scripts/tu106_vbios.py:Rom.pci`).

> Class code `0x030200` là dữ kiện ROM đầu tiên khẳng định CMP không có display engine:
> nó không khai báo mình là VGA controller. Đây là *khai báo*, không phải bằng chứng
> phần cứng bị fuse — xem mục 6.

---

## 1. PHƯƠNG PHÁP: SỰ THẬT ĐẾN TỪ SỐ HỌC, KHÔNG TỪ SUY ĐOÁN

Ba công cụ kiểm chứng được dùng xuyên suốt, mỗi cái đều **có thể fail**:

1. **Checksum BIT.** `sum(rom[base:base+hlen]) & 0xFF == 0`. Nếu offset gốc sai 1 byte,
   checksum fail ngay. Đây là cách phát hiện rằng `BIT` thật sự bắt đầu ở `0x287B0`
   (marker `FF B8` + `"BIT"`), **không phải** `0x287B2` như báo cáo trước ghi.
2. **Extent arithmetic.** Với một bảng có header `(ver, hlen, …)`, kích thước suy ra
   `hlen + count*(base + sub*subcount)` phải **rơi đúng** vào địa chỉ của một bảng P2
   khác. Đây là phép thử mạnh nhất: nó kiểm tra đồng thời offset, stride, count và
   chiều dài trường. Không có nó thì mọi "schema" chỉ là phỏng đoán.
3. **Đối chiếu spec độc lập.** Ví dụ POWER BASE CLOCK decode ra 1470/1650 MHz cho CMP
   và 2060S, 1410/1620 cho 2070 — khớp *chính xác* thông số công bố của ba card. Một
   parser sai offset không thể tình cờ khớp 3/3.

Các bảng trong báo cáo này chia làm 3 nhóm:

| Nhóm | Tiêu chí | Số bảng |
|---|---|---|
| **A. Decode đầy đủ** | có spec NVIDIA/envytools + extent khớp tuyệt đối | 4 (BIT, PERF v0x60, MEM CLOCK v0x11, MEM TWEAK v0x20, PBC v0x20) |
| **B. Chỉ có tên + vị trí** | extent không khớp, không có parser công khai | 35 |
| **C. Không xác định** | trường trong bảng nhóm A chưa có nghĩa | xem `TU106_UNKNOWN_FIELDS.csv` |

---

## 2. QUY TẮC CON TRỎ — SỬA LỖI CỦA BÁO CÁO TRƯỚC

```
file_offset = 0x28600 + raw                 nếu raw <  0xF400
file_offset = 0x28600 + raw + 0x11000       nếu raw >= 0xF400   (bỏ qua ảnh EFI)
```

`0x28600` = đầu ảnh legacy x86; `0x11000` = kích thước ảnh EFI nằm giữa.
**PROVEN**: 40/40 con trỏ P2 map vào vùng dữ liệu hợp lệ, và 5 bảng có extent khớp
tuyệt đối chỉ khi dùng đúng quy tắc này.

**Lỗi trong báo cáo trước:** `vbios_parser.py` (work_v15) đặt `BIT_OFF = 0x287B0` nhưng
đọc header tại `+8/+9/+10` của **0x287B2**, cho ra `hdr=17, stride=70, count=50` — vô
nghĩa. Đúng phải là `hlen=12, rlen=6, count=17` tại base `0x287B0`. Parser mới đọc
`version` như **u16** tại `+6` (= `0x0100`) theo `envytools/nvbios/bit.c:75-78`, không
phải u8.

---

## 3. BIT — 17 TOKEN, GIỐNG HỆT Ở CẢ 3 ROM

`base = 0x287B0`, `ver=0x0100`, `hlen=12`, `rlen=6`, `count=17`, checksum = 0.

Entry 6 byte: `{u8 type, u8 ver, u16 t_len, u16 t_offset}` — `t_offset` **tương đối với
`0x28600`**, không phải tuyệt đối. **PROVEN**.

| Token | CMP ver/len | GeForce ver/len | Ghi chú |
|---|---|---|---|
| `2` i2c | v1 / 4 | v1 / 4 | giống |
| `B` BIOSDATA | v2 / 37 | v2 / 37 | khác nội dung (build id) |
| `C` clock | v2 / **44** | v2 / **28** | CMP dài hơn 16 B ⇒ nguồn gốc mọi dịch offset |
| `D` DID | v1 / 4 | v1 / 4 | |
| `I` NVINIT | v1 / 36 | v1 / 36 | script điều kiện (mục 5) |
| `M` mem | v2 / 29 | v2 / 29 | |
| `N` NOP | v0 / 0 | v0 / 0 | |
| `P` power/perf | v2 / **224** | v2 / **196** | 56 vs 49 slot u32 |
| `S` string | v2 / 24 | v2 / 24 | |
| `T` TMDS | v1 / 2 | v1 / 2 | **CMP = `00 00`** |
| `U` display | v1 / 5 | v1 / 5 | **CMP: ptr=0, flags=0x02** |
| `V` vstrap | v1 / 6 | v1 / 6 | |
| `x` MXM | v1 / 8 | v1 / 8 | |
| `d` DP | v1 / 2 | v1 / 2 | **CMP = `00 00`** |
| `p` falcon | v2 / 4 | v2 / 4 | trỏ bảng firmware PMU |
| `u` UEFI | v1 / 13 | v1 / 13 | |
| `i` info | v2 / 104 | v2 / 104 | ngày build |

### 3.1 Token `p` — firmware (liên quan FECS/PMU)

`envytools/nvbios/bit.c` khai báo `{'p', 2, envy_bios_parse_bit_p}` = **Falcon Ucode**;
`p.c:envy_bios_parse_p_falcon_ucode()` đọc `{ver, hlen, rlen, entriesnum,
desc_ver, desc_size}` rồi mỗi entry `{u8 application_id, u8 target_id, u32 desc_ptr}`.
`application_id` = `PRE_OS` / `DEVINIT`; `target_id` = `PMU` (`p.c` enum
`ENVY_BIOS_FALCON_UCODE_APPLICATION_ID_*`).

TU106: `p` v2 dài 4 byte = **một u32 pointer** tới bảng FALCON UCODE. Đây là đường
duy nhất trong ROM trỏ tới microcode PMU/FECS/GPCCS mà **không** nằm trong NPDS. Field
schema của bảng đích chưa decode (nhóm B) — thiếu `desc_size` để tính stride.

---

## 4. PERFORMANCE P2 — HOÀN CHỈNH (ưu tiên số 1)

### 4.1 Directory

`BIT 'P'` v2 = mảng u32 con trỏ, `t_len/4` slot.

- CMP: 224 B = **56 slot**, 40 non-null
- GeForce: 196 B = **49 slot**, 40 non-null

40 slot non-null ở **cả ba** ROM, cùng bộ số hiệu. Tên slot lấy từ
`envytools/nvbios/power.c` `P2_tbls[]` (offset byte = slot*4). **PROVEN.**

| slot | tên (envytools) | CMP | 2060S / 2070 |
|---|---|---|---|
| 0 | PERFORMANCE | `0x54155` | `0x53755` / `0x53655` |
| 1 | MEMORY TIMINGS MAPPING | `0x54600` | `0x53c00` / `0x53b00` |
| 2 | MEMORY TIMINGS | `0x550c4` | `0x546c4` / `0x545c4` |
| 5 | THERMAL DEVICES | `0x58723` | `0x57d23` / `0x57c23` |
| 8 | VOLT MAPPING | `0x5649c` | `0x55a9c` / `0x5599c` |
| 10 | POWER SENSE | `0x579e0` | `0x56fe0` / `0x56ee0` |
| 11 | POWER BUDGET | `0x57e92` | `0x57492` / `0x57392` |
| 14 | **POWER BASE CLOCK** | `0x54326` | `0x53926` / `0x53826` |
| 15 | POWER TOPOLOGY | `0x57b3f` | `0x5713f` / `0x5703f` |
| 17 | PERF TEST SPEC | `0x545f2` | `0x53bf2` / `0x53af2` |
| 20 | THERMAL POLICY | `0x58679` | `0x57c79` / `0x57b79` |
| 29 | LOW POWER | `0x56222` | `0x55822` / `0x55722` |
| 32 | LOW POWER GR | `0x562d1` | `0x558d1` / `0x557d1` |

Slot null ở cả 3: 3 (VOLTAGE), 4 (THERMAL), 6, 7, 9, 12 (BOOST), 13 (CSTEP),
21, 24 (DI/DT).

### 4.2 Header — schema v0x60

```
+0x00 u8  version        = 0x60
+0x01 u8  header_len     = 0x0a  (10)
+0x02 u8  base_entry_sz  = 0x05  (5 byte / entry)
+0x03 u8  entry_count    = 0x07  (7 entry)
+0x04 u8  sub_entry_sz   = 0x06  (6 byte / domain record)
+0x05 u8  sub_entry_cnt  = 0x0a  (10 domain record / entry)
+0x06..0x09                = 01 07 00 01  (không giải mã được — UNKNOWN)
```

**Bằng chứng PROVEN:** `10 + 7*(5 + 6*10) = 465 = 0x1D1`, và

```
0x54155 + 0x1D1 = 0x54326 = POWER BASE CLOCK   (CMP)
0x53755 + 0x1D1 = 0x53926 = POWER BASE CLOCK   (2060S)
0x53655 + 0x1D1 = 0x53826 = POWER BASE CLOCK   (2070)
```

Rơi đúng vào bảng kế tiếp ở **cả ba ROM**. Đây là toàn bộ nội dung bảng: 465 byte,
không phải 45 byte như mô hình `hdr+esz*cnt` trước đó. **Mô hình 45 byte là sai và đã
bị loại bỏ** (`work_v15/PHASE16/VBIOS_PERF/PERF_SCHEMA_REPORT.md` §4 ghi
"generic header: ver=0x60, hdr=10, esz=5, cnt=7, size=45").

Vì sao 45 xuất hiện: nó đúng phần *đầu* (`10 + 7*5`), nhưng bỏ mất 10 domain record
của mỗi entry. Đó chính là lý do 4 byte lệch bị nhìn thấy mà không giải thích được.

### 4.3 Entry (5 byte base)

```
+0 u8 pstate        0xFF = SKIP ENTRY
+1 u8 unknown       (00 / 08 / 0c)
+2 u8 unknown       (00 / 01 / 04)
+3 u8 unknown       (00 / 01 / 02)
+4 u8 = 0xFF (hằng số ở cả 3 ROM)
```

`0xFF = SKIP` lấy từ **NVIDIA Virtual P-state Table Specification**
("A value of 0xff indicates SKIP ENTRY"), áp dụng cho bảng cùng họ.
**STRONGLY SUPPORTED** cho perf v0x60 (cùng quy ước, khác bảng).

### 4.4 Domain record (6 byte, ×10)

```
+0 u16 freq      bits[13:0] = tần số; bits[15:14] = flag
+2 u16 limit     cùng đơn vị, bits[15:14] = cờ loại giới hạn
+4 u16 aux       MHz với domain bộ nhớ; chưa rõ đơn vị với domain khác
```

Cơ sở mask `0x3FFF` + 2 bit cờ: **nouveau** `nvkm/subdev/bios/perf.c`
`nvbios_perfSp()` case 0x40: `freq = (rd16(data+0) & 0x3fff) * 1000`. Đây là tiền lệ
trực tiếp cho định dạng u16-có-cờ trong họ bảng performance. **STRONGLY SUPPORTED**
(mask lấy từ v0x40, không phải v0x60 — v0x60 không có trong mainline).

### 4.5 Toàn bộ dữ liệu — 7 entry × 10 domain

Cột = `freq` (bits 13:0). CMP / 2060S / 2070 (2060S và 2070 giống nhau 100% ở entry 0).

| entry | pstate | dom0 | dom1 | dom2 | dom3 | **dom4** | dom5 | dom6 | **dom7** | dom8 | dom9 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| e0 CMP | 0x07 | 645 | 600 | 405 | 630 | **27** | 555 | 540 | **27** | 1 | 540 |
| e0 2060S | 0x07 | 645 | 600 | 405 | 630 | **202** | 555 | 540 | **1080** | 1 | 540 |
| e1 CMP | 0xFF | – | – | – | – | – | – | – | – | – | – |
| e1 2060S | 0x0A | 645 | 600 | 810 | 630 | 405 | 555 | 540 | 1080 | 2 | 540 |
| e2 | 0xFF | – | – | – | – | – | – | – | – | – | – |
| e3 CMP | 0x0C | 645 | 855 | 5001 | 855 | **27** | 555 | 540 | **27** | 1 | 705 |
| e3 2060S | 0x0C | 645 | 855 | 5001 | 855 | 540 | 555 | 540 | 1080 | 3 | 705 |
| e4 CMP | 0xFF | – | – | – | – | – | – | – | – | – | – |
| e4 2060S | 0x0D | 645 | 855 | 6801 | 855 | 540 | 555 | 540 | 1080 | 3 | 705 |
| e5 | 0xFF | – | – | – | – | – | – | – | – | – | – |
| e6 CMP | 0x0F | 645 | 855 | **7001** | 855 | **27** | 555 | 540 | **27** | 1 | 705 |
| e6 2060S | 0x0F | 645 | 855 | **7001** | 855 | 540 | 555 | 540 | 1080 | 3 | 705 |

(`–` = entry `0xFF` với toàn bộ domain = 0. Test
`test_tu106_vbios.py` assert các entry skip phải zero — chống đọc nhầm record unused.)

### 4.6 Domain #2 = BỘ NHỚ — PROVEN

Ba giá trị ở dom2: **5001 / 6801 / 7001**, còn `aux` = **1250 / 1700 / 1750**.
`aux * 4 = 5000 / 6800 / 7000` MT/s ⇒ 10 / 13,6 / 14 Gbps. Đúng GDDR6 14 Gbps của cả
ba card. `envytools power.c` cũng dùng đúng quy ước "u16 × 4 = MHz" cho bảng clock
(`case 0x20: bce->clock[j] = clock * 4`). **PROVEN.**

### 4.7 BỐN BYTE KHÁC BIỆT — TRẢ LỜI TRỰC TIẾP

Yêu cầu đặt ra 4 offset `+0x27, +0x29, +0x2A, +0x2B`. Đo thực tế: vùng ±0x0F..0x2C
của cả ba ROM, **5 byte** khác (thêm `+0x28`), và `+0x26` giống nhau:

| offset | CMP | 2060S | 2070 | thuộc |
|---|---|---|---|---|
| `+0x26` | `00` | `00` | `00` | dom4 `freq` high byte |
| **`+0x27`** | `1B` | `CA` | `CA` | dom4 `freq` low byte |
| `+0x28` | `00` | `00` | `00` | dom4 `limit` high |
| **`+0x29`** | `1B` | `CA` | `CA` | dom4 `limit` low |
| **`+0x2A`** | `C0` | `80` | `80` | dom4 `limit` flag bits 15:14 |
| **`+0x2B`** | `06` | `32` | `32` | dom4 `aux` low byte |

Nghĩa giải mã được:

| | dom4 `freq` | dom4 `limit` | dom4 `aux` |
|---|---|---|---|
| CMP 40HX | **27 MHz** | 27, flags `0b11` | 6 |
| RTX 2060S / 2070 | 202 MHz | 202, flags `0b10` | 50 |

Và cùng hiện tượng ở **dom7** (`+0x39..+0x3D`, `+0x3E`), nơi GeForce có **1080 MHz**
còn CMP có **27 MHz**.

**27 MHz = tần số thạch anh tham chiếu của card.** Đây là giá trị "park/bypass":
domain bị giữ ở clock tham chiếu thay vì chạy theo PLL.

**Điều KHÔNG thể kết luận:** dom4/dom7 là domain nào. NVIDIA không công bố enum clock
domain cho Turing; nouveau không có parser v0x60. Vì thế **không** được gọi đây là
"RT lock" hay "graphics limiter". Lý do phản chứng: nếu dom4/dom7 là GPC (graphics
core) thì CMP sẽ chạy graphics ở 27 MHz — card không thể xuất hình. Vậy dom4/dom7
**không phải** domain graphics. Xem mục 8 để biết phép đo phân biệt.

### 4.8 CMP THIẾU 2 P-STATE — PROVEN

| | pstate có dữ liệu |
|---|---|
| CMP 40HX | `0x07`, `0x0C`, `0x0F` — **3 entry** |
| RTX 2060S / 2070 | `0x07`, `0x0A`, `0x0C`, `0x0D`, `0x0F` — **5 entry** |

CMP đánh `0xFF` (skip) cho entry `0x0A` và `0x0D`. Entry `0x0D` ở GeForce là trạng thái
bộ nhớ **6801 MT/s (13,6 Gbps)**; entry `0x0A` là trạng thái bộ nhớ thấp (810 MT/s).
Entry cao nhất (`0x0F`, 7001 MT/s) **vẫn còn** ở CMP ⇒ **trần bộ nhớ không bị cắt**.
Hệ quả thực tế: CMP có ít bậc chuyển P-state hơn (chuyển mức thô hơn), không mất đỉnh.

---

## 5. POWER BASE CLOCK v0x20 — CLOCK THẬT, VÀ ĐÂY LÀ KẾT LUẬN QUAN TRỌNG NHẤT

Decode theo `envytools/nvbios/power.c:envy_bios_parse_power_base_clock()` case `0x20`:

```
+0 ver=0x20  +1 hlen=19  +2 rlen=1  +3 entries=17  +4 secount=4  +5 selen=10
entry stride = 1 + 10*4 = 41
clock[j] = u16(entry + 1 + j*10 + 2) * 4     [MHz]
```

**Extent: `19 + 17*41 = 716` byte**, kết thúc đúng `PERF TEST SPEC` (slot 17) ở cả 3 ROM.

| ROM | entry 0 | entry 2 | thông số công bố |
|---|---|---|---|
| **CMP 40HX** | **1468 MHz** | **1648 MHz** | 1470 / 1650 |
| **RTX 2060S** | **1468 MHz** | **1648 MHz** | 1470 / 1650 |
| **RTX 2070** | **1408 MHz** | **1620 MHz** | 1410 / 1620 |

Sai lệch 2 MHz là do lượng tử hoá `/4` (367×4 = 1468; GPU-Z hiển thị 1470).

Mức bằng chứng, tách đôi cho chính xác:
- **Giá trị** trong ROM: **PROVEN** (đọc trực tiếp u16×4, offset xác định bởi extent khớp).
- **Nhãn "entry 0 = base, entry 2 = boost"**: **STRONGLY SUPPORTED** — suy ra từ việc
  4/4 giá trị khớp cặp base/boost công bố của hai card khác nhau (2060S 1470/1650,
  2070 1410/1620). Không có spec NVIDIA đặt tên cho từng entry.
- **Entry 3..9**: decode theo layout envytools v0x20 cho ra giá trị vô nghĩa
  (vd `133412`). Nghĩa là layout sub-record của các entry đó **khác** giả định của
  envytools → schema các entry này **UNKNOWN**, không dùng.

> **KẾT LUẬN: CMP 40HX khai báo trong VBIOS đúng base/boost clock của RTX 2060 SUPER.
> Không có giới hạn xung graphics nào trong ROM.**

Đây là phản chứng trực tiếp cho giả thuyết "VBIOS bóp xung CMP". Nếu FPS thấp hơn
2060S, nguyên nhân **không** phải clock trong ROM.

Khác biệt duy nhất ở bảng này giữa CMP và GeForce: byte `+0x09, +0x0A`
(CMP `FF FF`, GeForce `03 09`) — và 2070 khác `BE 6F` vs `82 60` ở clock slot của entry
`0x0F`. Ý nghĩa `03 09` chưa xác định (có thể là index entry cho VRHOT/rated-TDP theo
`power.c` v0x20 `+0x0C..+0x0F` = vrhot/max_batt/unk15/unk16). **UNKNOWN**.

---

## 6. MEMORY: CLOCK TABLE v0x11 + TWEAK TABLE v0x20

### 6.1 MEMORY TIMINGS MAPPING = NVIDIA Memory Clock Table v0x11

```
+0 ver=0x11  +1 hlen=26  +2 base=60  +3 strap=33  +4 strap_cnt=10  +5 entries=7
entry = 60 + 33*10 = 390 B ;  extent = 26 + 7*390 = 2756 B
```
`0x54600 + 2756 = 0x550C4` = MEM TIMINGS ✔ (và đúng cho cả 3 ROM). **PROVEN.**

So với spec NVIDIA (`MemoryClockTable`, ver 0x11, hdr 26, base **20**, strap **26**):
TU106 dùng base **60** và strap **33** — bản Turing mở rộng. Spec chỉ công bố phần lõi
`Min/Max Frequency [13:0] = MHz`; phần mở rộng chưa có tài liệu.

7 dải tần số (giống nhau 3 ROM ở mức MHz):

| # | min–max (MHz) | rw0 | rw1 |
|---|---|---|---|
| 0 | 0–540 | `0x7002054d` | `0x4f004402` |
| 1 | 541–1249 | `0x004e274d` | `0x4f88e804` |
| 2 | 2005–4699 | `0xf4201040` | `0xff44e405` |
| 3 | 4700–5500 | `0xf4201040` | `0xff44e405` |
| 4 | 5501–6300 | `0xf4201040` | `0xff44e405` |
| 5 | 6301–6700 | `0xf4201040` | `0xff44e405` |
| 6 | 6701–16383 (**CMP/2060S**) / 6701–9000 (**2070**) | `0xf4201040` | `0xff44e405` |

Ghi chú: dải 2 bắt đầu 2005 chứ không phải 1250 — có lỗ hổng thật trong bảng, giống
nhau ở cả 3 ROM (không phải lỗi parser: max của dải 1 = 1249, max dải 2 = 4699 khớp
liền mạch với dải 3). **PROVEN (đo), UNKNOWN (ý nghĩa lỗ hổng).**

### 6.2 MEMORY TIMINGS = NVIDIA Memory Tweak Table v0x20

```
+0 ver=0x20  +1 hlen=6  +2 base=74  +3 ext=12  +4 ext_cnt=0  +5 entries=60
extent = 6 + 60*74 = 4446 B
```
`0x550C4 + 4446 = 0x56222` = LOW POWER (slot 29) ✔. **PROVEN.**
(Spec NVIDIA ghi base **76**; TU106 dùng **74** — chênh 2 byte, và số học extent xác
nhận 74 là đúng cho ROM này.)

Field decode theo spec `MemoryTweakTable` (CONFIG0..CONFIG4):

| field | CONFIG | bits |
|---|---|---|
| RC | 0 | [7:0] |
| RFC | 0 | [16:8] |
| RAS | 0 | [23:17] |
| RP | 0 | [30:24] |
| CL | 1 | [6:0] |
| WL | 1 | [13:7] |
| RD_RCD / WR_RCD | 1 | [19:14] / [25:20] |
| RPRE / WPRE / CDLR / WR | 2 | [3:0] / [7:4] / [14:8] / [22:16] |
| FAW | 3 | [16:9] |
| CCDL / CCDS | 3 | [27:24] / [31:28] |
| REFRESH | 4 | [14:3] |
| RRD | 4 | [20:15] |

Strap 0 (14 Gbps): CL=24, WL=5, RC=78, RFC=210, RAS=52, RP=26, RD_RCD=26, WR=27,
FAW=16. Đây là timing GDDR6 hợp lý cho 1750 MHz. **PROVEN (decode), HYPOTHESIS (strap
nào đang dùng — xem 6.3).**

### 6.3 KHÁC BIỆT TIMING CMP vs GeForce

CMP khác 2060S/2070 ở strap 12–17:

| strap | field | CMP | 2060S/2070 |
|---|---|---|---|
| 14 | RFC | 148 | 180 |
| 14 | RAS | 37 | 42 |
| 14 | FAW | 16 | 24 |
| 14 | CL | 20 | 22 |
| 15 | RFC | 126 | 150 |
| 15 | FAW | 16 | 20 |
| 12–17 | REFRESH | **6** | **4** |
| 46+ | toàn bộ | có dữ liệu | **2070 = 0** (strap không dùng) |

CMP dùng timing **chặt hơn** (số nhỏ hơn) ở nhóm strap này và REFRESH cao hơn.
Không kết luận được đây là tốt hay xấu: (a) không biết strap nào được chọn khi chạy
14 Gbps, (b) timing chặt hơn có thể là bin bộ nhớ khác hoặc hiệu chỉnh cho board CMP.
**HYPOTHESIS.** Đây là khác biệt *có khả năng* ảnh hưởng bandwidth/latency, cần đo
(xem `GRAPHICS_RT_PERFORMANCE_INVESTIGATION.md` mục 5).

---

## 7. CÁC BẢNG POWER/THERMAL: CÁI GÌ GIỐNG, CÁI GÌ KHÁC

So sánh **theo cấu trúc** (con trỏ P2), không theo file offset:

| slot | bảng | CMP vs 2060S | ghi chú |
|---|---|---|---|
| 5 | THERMAL DEVICES | **giống 100%** (58/58) | |
| 10 | POWER SENSE | **giống 100%** (351/351) | |
| 15 | POWER TOPOLOGY | **giống 100%** (851/851) | không chứa SM/TPC count đọc được |
| 18 | THERMAL CHANNEL | **giống 100%** | |
| 31 | LOW POWER PCIe-PLATFORM | **giống 100%** | |
| 8 | VOLT MAPPING | giống 100% (2060S), 96% (2070) | |
| 11 | POWER BUDGET | 1739/1743 | khác `+0x20`: CMP `FF` vs `0E`; `+0xB2`: `B0AD` vs `48E8` |
| 14 | POWER BASE CLOCK | 714/716 | `+0x09,+0x0A` = `FF FF` vs `03 09` |
| 20 | THERMAL POLICY | 168/170 | `+0x04`: CMP `FF` vs `02`; `+0x07`: 2070 `00` |
| 22 | FAN COOLERS | 52/58 | |
| 23 | POWER FAN_MGMT | 86/114 | |
| 30 | LOW POWER PCIe | 60/65 | |
| 32 | LOW POWER GR | 34/35 | 1 u16 khác `0xE7FF` vs `0xEFFF` |
| 38 | OVERCLOCKING | 20/26 | |

**Đọc được từ số liệu này:**

- **POWER SENSE và POWER TOPOLOGY giống tuyệt đối** ⇒ cảm biến công suất và topology
  nguồn không phải nguồn gốc khác biệt hiệu năng.
- **THERMAL POLICY của CMP có `0xFF` ở byte +4** — cùng kiểu "xoá trắng" như token `T`,
  `d`, `U`. Nhiều khả năng CMP không có vòng điều khiển quạt/thermal đầy đủ (card mining
  chạy quạt ngoài). **STRONGLY SUPPORTED** (pattern 0xFF lặp lại ở 3 bảng khác nhau).
- **POWER BUDGET gần như giống** ⇒ TDP *không* đọc được trực tiếp từ bảng này ở dạng
  dễ thấy; khác biệt 4 byte không đủ để nói 175 W vs 185 W. Field schema của POWER
  BUDGET v0x30 vẫn **UNKNOWN** (xem dưới).

`envytools` có parser cho POWER BUDGET (v0x10/0x20/0x30: `min/avg/peak` mW, `cap_entry`),
THERMAL POLICY (`mode, t0/t1/t2 /32 °C, interval, down/up offset`) và POWER BASE CLOCK.
Nhưng **extent test không khớp** cho POWER BUDGET (44 + 20*66 = 1364 ≠ bảng kế tiếp) và
POWER TOPOLOGY (6 + 15*(22+20*27) vượt xa). Nghĩa là các header byte `+2..+5` của hai
bảng này **không** theo cùng quy ước `base/ext/count` ⇒ không được áp schema envytools
một cách mù quáng. Giữ **UNKNOWN**.

---

## 8. DISPLAY: VÌ SAO CMP KHÔNG CÓ, VÀ PHÂN BIỆT VỚI FUSE

### 8.1 Dữ liệu ROM

| | CMP | 2060S | 2070 |
|---|---|---|---|
| class code | `0x030200` (3D) | `0x030000` (VGA) | `0x030000` |
| token `U` ptr | **`0x0000`** | `0x4E8F` | `0x4E8F` |
| token `U` flags | **`0x02`** | `0x00` | `0x00` |
| token `T` (TMDS) | **`00 00`** | `7B 51` / `8B 51` | |
| token `d` (DP) | **`00 00`** | `1B 67` / `2B 67` | |
| DCB `entry_count` | **0** | 16 (8 connector dùng) | 16 (5 connector dùng) |

DCB entries (type byte, `0x0F` = slot trống):

```
2060S: 66 62 72 52 7F 7F 8F 32 | 0F ×8      -> 8 connector
2070 : 66 62 72 52 0F 0F 0F 32 | 0F ×8      -> 5 connector (4 DP + HDMI)
CMP  : (count = 0, không có entry)
```

### 8.2 Kết luận có bằng chứng

- CMP **không có** script display (con trỏ = 0), **không có** bảng connector (count = 0),
  **không có** tham số TMDS/DP. Đây không phải "cờ bị tắt" mà là **dữ liệu không tồn tại**.
  **PROVEN.**
- Điều này **không** chứng minh display bị fuse-disable. Hai cơ chế khác nhau:
  ROM thiếu cấu hình (những gì thấy được) vs phần cứng bị khoá (cần đọc fuse/strap).
- Theo hướng phần cứng: PCB của CMP không có cổng ra và (theo tài liệu cộng đồng
  `cmp.wiki`) các lane PCIe 4–15 không gắn tụ AC — tức board được thiết kế lại, không
  chỉ đổi ROM. Không có bằng chứng nào cho thấy chép DCB từ GeForce sang sẽ hoạt động.

### 8.3 KHÔNG đề xuất

Không flash chéo, không chép bảng display, không sửa `U`/DCB. Không có bằng chứng phần
cứng tương thích, và bảng display của 2060S/2070 còn khác nhau giữa chính chúng.

---

## 9. FECS / GPCCS / GSP VÀ CÁC REGISTER ĐƯỢC NÊU

### 9.1 Register address trong ROM

| address | xuất hiện ở | trạng thái |
|---|---|---|
| `0x409658`, `0x40965C` | token `I` (NVINIT) — FECS write liền kề condition-50 | **literal có mặt trong script** |
| `0x409660` | token `I`, condition record 50 đọc bit16, mask `0x10000` | **literal + phép test**, không phải phép ghi |
| `0x409664` | FECS_SPEED0 / SS0 | literal, không có phép ghi vô điều kiện |
| `0x40966C` | FECS_SPEED1 / SS1 | literal |
| `0x021C38` | không có trong ROM | đọc live: `STATUS_OPT_TPC_GPC0 = 0x20` |
| `0x021040` | không có trong ROM | đọc live: ghi được = 1, sticky |

Nguồn: `CMP40HX_INDEPENDENT_REVIEW/input/ASTRA_CMP40HX_HANDOFF/05_PHASE21_EXTRACTS/
VBIOS_DISPLAY_ANALYSIS.md` và `EVIDENCE_LEDGER.md` (E21-020) — công trình trước của
chính dự án này.

Phân biệt bắt buộc:

- **literal trong script** ≠ **lệnh được mã hoá** ≠ **đường thực thi có điều kiện**
  ≠ **phép ghi đã quan sát**.
- `0x409660` chỉ được **đọc** trong condition-50 (`FECS readout bit16 == 1`). Không có
  phép ghi. Một condition record không phải unlock, không phải selector write.
- `0x021C38` / `0x021040` **không** nằm trong ROM. Chúng chỉ tồn tại như địa chỉ thanh
  ghi đọc/ghi từ host.

### 9.2 Ai quyết định số SM/TPC đang hoạt động

Thứ tự bằng chứng hiện có:

1. `0x021C38 = 0x20` (bit5) trên card thật ⇒ TPC5 trong GPC0 bị tắt. **Đo trực tiếp.**
2. Ghi `CTRL_OPT_TPC_GPC0 |= 0x20` từ ring-0, BAR0 trực tiếp, sau khi đã bật
   `0x021040 = 1` ⇒ **giá trị bounce**. ⇒ chốt ở hardware, không phải quyền.
   **Đo trực tiếp** (`results/TPC5_LIVE/EXPLOIT_LIVE_20261106.md`).
3. Vì vậy thứ tự quyết định là: **fuse/strap (hardware latch) → GSP/SEC2 init →
   driver đọc trạng thái**. VBIOS không phải nơi chứa topology. ROM cũng không có bảng
   SM/TPC count nào decode được (POWER TOPOLOGY giống hệt 3 card, 851/851 byte).

⇒ Trong ROM **không** có trường nào cấu hình SM/TPC. **PROVEN (rom-side absence)**.

### 9.3 GSP/SEC2 và hiệu năng compute

Nguồn cộng đồng độc lập (`Cyridd/cmpunlocker`, đúng PCI ID `10de:1f0b`):

- Không có khoá FP32/FP16 toàn cục: FP32 qua cuBLASLt/OpenCL/Vulkan ≈ 8,3–9 TFLOPS
  **trước và sau** unlock.
- Cái bị giới hạn là trạng thái init bảo vệ trong GSP/SEC2 → đường **Tensor Core
  WMMA** (1,1 → 72 TFLOPS fp16), INT8 `dp4a` (1 → 34 TOPS).
- Patch ghi `SS0 = 0x88888888`, `SS1 = 0x00000008`, `FECS_PLM = 0xFFFFFF8F` trong
  pha privileged của SEC2 Booter.
- **"The community unlock does not touch the VBIOS at all"** (cmp170hx docs) —
  `nvflash`/SPI/ROM không xuất hiện trong tool.

⇒ Chuỗi VBIOS → driver → trạng thái GPU → hiệu năng **không** đi qua bất kỳ field ROM
nào. Nó đi qua **runtime register state do SEC2/GSP đặt**.

---

## 10. NHỮNG GÌ ĐÃ GIẢI MÃ THÊM (so với baseline)

| # | Field | Trước | Bây giờ | Mức |
|---|---|---|---|---|
| 1 | BIT base offset | `0x287B2`, hdr/stride/count sai | `0x287B0`, `hlen=12, rlen=6, cnt=17`, checksum pass | PROVEN |
| 2 | BIT version | u8 | u16 tại `+6` = `0x0100` | PROVEN |
| 3 | PERF v0x60 extent | "45 byte" (sai) | **465 byte**, `hdr+cnt*(base+sub*subcnt)` | PROVEN |
| 4 | PERF v0x60 base entry | không biết | 5 byte, `pstate` + 4 byte chưa rõ | PROVEN shape |
| 5 | PERF v0x60 domain record | không biết | 6 byte × 10; u16 `freq` (13:0 + 2 cờ), u16 `limit`, u16 `aux` | PROVEN shape |
| 6 | Domain #2 | không biết | **bộ nhớ**: `freq` = MT/s, `aux` = MHz, `×4` | PROVEN |
| 7 | 4 byte lệch | "có thể là RT lock" | dom4/dom7 của entry 0: CMP 27 MHz vs 202/1080 MHz | PROVEN (vị trí+giá trị) |
| 8 | P-state bị thiếu | không biết | CMP skip `0x0A` và `0x0D` | PROVEN |
| 9 | **Base/boost clock** | không có | **CMP 1468/1648 = 2060S; 2070 1408/1620** | **PROVEN** |
| 10 | MEM CLOCK v0x11 extent | không biết | 2756 B, base 60, strap 33×10, 7 entry | PROVEN |
| 11 | MEM TWEAK v0x20 extent | không biết | 4446 B, base 74, 60 entry; decode CL/RFC/RAS/RP… | PROVEN |
| 12 | DCB connector count | 0 / 16 | 0 / 8 / 5 (đếm theo type ≠ `0x0F`) | PROVEN |
| 13 | Class code | — | CMP `0x030200` vs GeForce `0x030000` | PROVEN |
| 14 | Power/thermal tables | "chưa rõ" | POWER SENSE/TOPOLOGY/THERMAL DEVICES **giống 100%**; THERMAL POLICY CMP `0xFF` | PROVEN |

---

## 11. CÂU HỎI CHƯA GIẢI ĐƯỢC

1. **Clock domain enumeration của Turing.** dom0..dom9 là domain nào? Chỉ dom2 = bộ
   nhớ là chứng minh được. Không có tài liệu NVIDIA, không có parser v0x60 ở nouveau.
2. **Nghĩa của dom4/dom7 = 27 MHz.** 27 MHz = thạch anh tham chiếu ⇒ "park", nhưng
   *domain nào* bị park thì chưa biết.
3. **4 byte base entry `+1..+4`** (`00 00 00 FF` / `08 04 02 FF` / `0c 04 02 FF`).
4. **4 byte header `+6..+9`** = `01 07 00 01` (giống cả 3 ROM, không rõ nghĩa).
5. **Cờ `0x4000/0x8000/0xC000`** trên trường `limit` — nouveau mask bỏ chứ không đặt tên.
6. **POWER BUDGET v0x30**: header không theo quy ước `base/ext/count`; TDP 175/185 W
   không đọc được trực tiếp.
7. **`0x03 09` ở POWER BASE CLOCK `+0x09/+0x0A`** (GeForce) vs `FF FF` (CMP).
8. **Strap bộ nhớ nào đang hoạt động** ở 14 Gbps, và timing CMP chặt hơn có ảnh hưởng
   gì.
9. **Bảng FALCON UCODE (`p` token)** — schema entry chưa decode được vì thiếu
   `desc_size` nhất quán.

Chi tiết từng trường: `data/TU106_UNKNOWN_FIELDS.csv`.

---

## 12. TÁI LẬP

```bash
cd TU106_VBIOS_RE
python3 scripts/test_tu106_vbios.py   /path/to/roms    # assert toàn bộ
python3 scripts/export_fields.py      /path/to/roms    # data/*.csv
python3 scripts/tu106_vbios.py dump    /path/to/roms/TU106.rom
python3 scripts/tu106_vbios.py compare /path/to/roms/TU106.rom /path/to/roms/219827.rom
```

ROM gốc **không** nằm trong repo (xem `.gitignore`). Không script nào mở file ở chế độ
ghi.
