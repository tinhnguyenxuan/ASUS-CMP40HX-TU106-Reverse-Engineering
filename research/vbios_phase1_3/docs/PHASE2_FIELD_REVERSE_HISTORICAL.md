# VBIOS FIELD REVERSE ENGINEERING — NVIDIA CMP 40HX / TU106

> **Bản lưu trữ lịch sử:** không phải kết luận cập nhật hay xác minh độc lập; xem [bảng đính chính và tiến triển Phase 1–6](../../../docs/TU106_VBIOS_PHASE1_5_HISTORY.md). Phép đo/test game thực tế đã lược khỏi bản xuất bản này.


**Phạm vi:** 3 ROM TU106 (1.047.040 B, `NVGI`)
**Môi trường:** đọc tĩnh, không flash, không MMIO write, không sửa driver.
**Script:** `scripts/tu106_vbios.py`, `scripts/export_fields.py`, `scripts/test_tu106_vbios.py`
**Dữ liệu:** `data/TU106_DECODED_FIELDS.csv` (1.526 dòng), `data/TU106_UNKNOWN_FIELDS.csv` (11 dòng)
**Ngày:** 2026-11-07 · **bản 2** — sửa 2 lỗi parser, thay suy luận bằng schema NVIDIA chính thức

Mọi kết luận gắn nhãn **PROVEN / STRONGLY SUPPORTED / HYPOTHESIS / UNKNOWN**.
Xem §11 cho danh sách những gì **bị hạ mức** so với bản 1.

---

## 0. BA ROM VÀ ĐỊNH DANH

| | CMP 40HX | RTX 2060 SUPER | RTX 2070 |
|---|---|---|---|
| File | `TU106.rom` | `219827.rom` | `265590.rom` |
| SHA-256 (16) | `78435dca0ca0732b` | `ad231cef133f9385` | `560f2be1bee834c3` |
| PCI ID | `10DE:1F0B` | `10DE:1F06` | `10DE:1F07` |
| Class code | `0x030200` 3D controller | `0x030000` VGA | `0x030000` VGA |
| **Image 0 (legacy)** | **`0xF400`** | **`0xEC00`** | **`0xEC00`** |
| Image 1 (EFI) | `0x11000` | `0x11000` | `0x11000` |

Mỗi ROM có **4 PCIR** (2 bank × legacy+EFI) tại cùng bộ offset trong cả ba ROM.
`image_len` = **PCIR+0x10**, đơn vị 512 B.

> **Sửa lỗi (bản 2):** bản 1 đọc `PCIR+0x0A` — đó là *structure length* (`0x18`/`0x1C`),
> không phải image length — rồi nhân 512 ra `0x3000`. Đúng phải là `+0x10`.
> `test_tu106_vbios.py::regression_pcir_image_len` kiểm lại **trực tiếp từ byte thô**.

---

## 1. QUY TẮC CON TRỎ — KHÔNG CÒN HẰNG SỐ

```
image0_base = ROM.find(FF B8 "BIT") & ~0x1FF          = 0x28600
legacy_len  = PCIR#0 (+0x10) * 512                    (0xF400 hoặc 0xEC00)
efi_len     = PCIR#1 (+0x10) * 512                    = 0x11000

file = image0_base + raw                  nếu raw <  legacy_len
file = image0_base + raw + efi_len        nếu raw >= legacy_len
```

Bản 1 hardcode `LEGACY_SZ = 0xF400`, `EFI_SZ = 0x11000`. Với hai ROM GeForce legacy thật
là `0xEC00` ⇒ ngưỡng chuyển nhánh lệch 2 KiB. Trong 3 ROM này **không con trỏ nào rơi
vào `0xEC00..0xF400`** nên kết quả không đổi — nhưng đó là may, không phải đúng.
Test hiện kiểm cả hai phía ngưỡng:

```python
assert Rom.ptr(r["RTX2060S"], 0xEC00) == 0x28600 + 0xEC00 + 0x11000
assert Rom.ptr(r["CMP40HX"],  0xF3FF) == 0x28600 + 0xF3FF
```

---

## 2. BIT — 17 TOKEN

`base = 0x287B0` (marker `FF B8` + `"BIT"`), `ver=0x0100` (u16 tại +6),
`hlen=12`, `rlen=6`, `count=17`, checksum = 0.

Entry 6 byte: `{u8 type, u8 ver, u16 t_len, u16 t_offset}`; `t_offset` tương đối với
`image0_base`. **PROVEN** (`envytools/nvbios/bit.c:75-78` + checksum).

| Token | CMP | GeForce | ghi chú |
|---|---|---|---|
| `C` clock | v2 / **44** | v2 / **28** | CMP dài hơn 16 B ⇒ nguồn gốc mọi dịch offset |
| `P` power/P2 | v2 / **224** (56 slot) | v2 / **196** (49 slot) | 40 slot non-null ở cả 3 |
| `T` TMDS | `00 00` | `7B 51` / `8B 51` | CMP rỗng |
| `U` display | ptr `0x0000`, flags `0x02` | ptr `0x4E8F`, flags `0x00` | CMP không có script |
| `d` DP | `00 00` | `1B 67` / `2B 67` | CMP rỗng |
| `p` falcon | v2 / 4 | v2 / 4 | u32 → bảng FALCON UCODE (PMU) |
| `i` info | v2 / 104 | v2 / 104 | ngày build |
| còn lại | `2 B D I M N S V x u` | giống | |

---

## 3. PERFORMANCE v0x60 — SCHEMA NVIDIA CHÍNH THỨC

Bản 1 suy schema từ số học. Bản 2 tìm được **định nghĩa chính thức**:

> `NVIDIA/nvgpu` → `include/nvgpu/bios.h`
> (mirror `OE4T/linux-nvgpu`, `patches-rel-36`, `drivers/gpu/nvgpu/include/nvgpu/bios.h`)

```c
#define VBIOS_PSTATE_TABLE_VERSION_6X       0x60U
#define VBIOS_PSTATE_HEADER_6X_SIZE_10      (10U)
#define VBIOS_PSTATE_BASE_ENTRY_6X_SIZE_5   0x5U
#define VBIOS_PSTATE_CLOCK_ENTRY_6X_COUNT   10U
#define VBIOS_PSTATE_CLOCK_ENTRY_6X_SIZE_6  6U

struct vbios_pstate_header_6x {
    u8 version; u8 header_size; u8 base_entry_size; u8 base_entry_count;
    u8 clock_entry_size; u8 clock_entry_count;
    u8 flags0; u8 initial_pstate; u8 cpi_support_level; u8 cpi_features;
};
struct vbios_pstate_entry_6x {
    u8 pstate_level; u8 flags0; u8 lpwr_entry_idx; u8 pcie_idx; u8 nvlink_idx;
    struct vbios_pstate_entry_clock_6x nvgpu_clockEntry[PERF_CLK_DOMAINS_IDX_MAX];
};
struct vbios_pstate_entry_clock_6x { u16 param0; u32 param1; };
```

Đúng bảng ở P2 slot 0. Số học bản 1 (`465 = 10 + 7*(5 + 6*10)`) trùng khớp **chính xác**
schema này ⇒ hình dạng giờ là PROVEN theo nguồn, không chỉ theo số học.

### 3.1 Header — giá trị thực

| off | field | CMP | 2060S | 2070 |
|---|---|---|---|---|
| +0 | version | `0x60` | `0x60` | `0x60` |
| +1 | header_size | 10 | 10 | 10 |
| +2 | base_entry_size | 5 | 5 | 5 |
| +3 | base_entry_count | 7 | 7 | 7 |
| +4 | clock_entry_size | 6 | 6 | 6 |
| +5 | clock_entry_count | 10 | 10 | 10 |
| +6 | flags0 | `0x01` | `0x01` | `0x01` |
| +7 | initial_pstate | `0x07` | `0x07` | `0x07` |
| +8 | cpi_support_level | `0x00` | `0x00` | `0x00` |
| +9 | cpi_features | `0x01` | `0x01` | `0x01` |

`flags0` bit0 = `PSTATES_REQUIRED` (bật), bit1 = `ARBITER_LOCK` (tắt).

**Extent:** `10 + 7*(5 + 6*10) = 465 = 0x1D1` → kết thúc đúng `POWER BASE CLOCK` ở cả ba
ROM (`0x54155+0x1D1 = 0x54326`, …). **PROVEN.**

> **Sửa (bản 2):** 4 byte `+6..+9` mà bản 1 gọi là "unknown tail" thực ra là
> `flags0 / initial_pstate / cpi_support_level / cpi_features`.

### 3.2 Base entry 5 byte

| off | field | ý nghĩa |
|---|---|---|
| +0 | `pstate_level` | `0xFF` = `VBIOS_PERFLEVEL_SKIP_ENTRY` |
| +1 | `flags0` | `PSTATE_CAP[1:0]`, `CUDA_NOT_SAFE[2]`, `OVOC[3]`, `DECREASE_THRESHOLD[4]` |
| +2 | `lpwr_entry_idx` | index vào bảng LOW POWER |
| +3 | `pcie_idx` | index vào bảng cấu hình PCIe |
| +4 | `nvlink_idx` | `0xFF` = không có |

Giá trị thực (CMP): `07 00 00 00 ff`, `ff 00 01 01 ff`, `ff 00 02 02 ff`,
`0c 08 04 02 ff`, `ff 00 04 02 ff`, `ff 00 04 02 ff`, `0f 08 04 02 ff`.

Đọc được ngay:
- `pstate_level` ∈ {`07`, `0A`, `0C`, `0D`, `0F`} hoặc `0xFF`.
- **`OVOC` (bit3) bật ở `0x0C`/`0x0D`/`0x0F`** (`flags0 = 0x08/0x0c`), tắt ở `07`/`0A`.
  Đây là cờ *cho phép* over-clock/over-volt, **không phải khoá**.
- `CUDA_NOT_SAFE` = 0 ở **mọi** entry của cả 3 ROM.
- `pcie_idx` = 0 ở entry thấp nhất, 2 ở các entry cao ⇒ 3 cấu hình PCIe được tham chiếu.
  Bảng đích chưa decode (§9).

### 3.3 Clock entry 6 byte × 10

```c
param0[13:0]  = NOM_FREQ_MHZ
param1[13:0]  = MIN_FREQ_MHZ
param1[27:14] = MAX_FREQ_MHZ
```

### 3.4 DANH TÍNH 10 CLOCK DOMAIN

`bios.h` khai báo `nvgpu_clockEntry[PERF_CLK_DOMAINS_IDX_MAX]` (=32) nhưng **không đặt
tên index**. Tên lấy từ bảng **CLOCKS v0x35** cùng file header: mỗi row có một
`ordering idx`, thứ tự row là "GV HAL order":

```
0 GPC  1 XBAR  2 DRAM  3 SYS  4 HUB  5 VID  6 PWR  7 DISP  8 PCIEGEN  9 HOST
```

**Ba lớp kiểm chứng độc lập:**
1. Bảng CLOCKS v0x35 trong **cả ba ROM** có đúng 10 row với `ordering idx` =
   `13 24 62 35 71 46 ff 80 08 57` — khớp 10/10 thứ tự trên.
2. Index 2 = `DRAM`: `7001` / `5001` / `6801` = 14,0 / 10,0 / 13,6 Gbps, và
   `7001 = 4 × 1750 MHz` (GDDR6 quad-pumped). Không domain nào khác có thể là bộ nhớ.
3. Index 8 = `PCIEGEN`: CMP = `1`, hai GeForce = `3` — đúng PCIe Gen1 vs Gen3.

⇒ **Thứ tự domain: PROVEN cho TU106.** Chip khác phải kiểm lại (mảng có 32 slot, chỉ
10 dùng).

### 3.5 Toàn bộ 10 domain

`nom` (MHz) ở entry cao nhất (`pstate 0x0F`):

| domain | CMP | 2060S | 2070 | |
|---|---|---|---|---|
| GPC | 645 | 645 | 645 | giống |
| XBAR | 855 | 855 | 855 | giống |
| **DRAM** | **7001** | **7001** | **7001** | 14 Gbps |
| SYS | 855 | 855 | 855 | giống |
| **HUB** | **27** | **540** | **540** | **KHÁC** |
| VID | 555 | 555 | 555 | giống |
| PWR | 540 | 540 | 540 | giống |
| **DISP** | **27** | **1080** | **1080** | **KHÁC** |
| **PCIEGEN** | **1** | **3** | **3** | **KHÁC** |
| HOST | 705 | 705 | 705 | giống |

`max`: GPC 2100 (cả 3) · HUB 27 vs 810 · DISP 27 vs 1330 · PCIEGEN 1 vs 3.

**Ba domain khác, bảy domain giống tuyệt đối.** Không domain nào trong GPC/XBAR/SYS/VID
khác nhau giữa CMP và 2060S.

Ghi chú về đơn vị: GPC `nom = 645`, `min = 300`, `max = 2100` ở **cả ba card** — đây là
*biên lập trình clock*, không phải xung vận hành. Xung thật nằm ở `POWER BASE CLOCK`
(§4). Vì vậy bảng này **không** mang boost clock và **không** phân biệt 1470/1650 với
1410/1620 — đúng như quan sát: ba card có cùng giá trị.

### 3.6 Bốn byte `+0x27/+0x29/+0x2A/+0x2B` — ĐÃ ĐỊNH DANH

Đo thực tế: vùng `+0x26..+0x2B` khác **5 byte** (thêm `+0x28`; `+0x26` giống nhau vì
high byte của `param0` đều là 0). Chúng nằm gọn trong **clock entry của domain HUB**
(index 4, bắt đầu tại offset tương đối `+0x27`):

```
+0x27..+0x28   HUB.param0   nom
+0x29..+0x2C   HUB.param1   min[13:0] + max[27:14]
```

| | HUB nom | HUB min | HUB max |
|---|---|---|---|
| CMP 40HX | **27** | 27 | 27 |
| RTX 2060S / 2070 | **202** (entry `0x07`) / 540 (entry cao) | 202 / 540 | 202 / 810 |

Khối khác thứ hai ở `+0x39..+0x3E` là **DISP** (index 7): CMP `27/27/27` vs GeForce
`1080/1080/1330`.

**Đây không phải cờ RT, không phải "graphics limiter":** đó là clock bound của domain
HUB và DISP. Bản 1 gọi đúng vị trí nhưng **không biết đó là domain nào**; bản 2 đã
định danh.

### 3.7 Vì sao 27 MHz không phải xung vận hành — hai bảng độc lập cùng kết luận

Bảng **CLOCKS v0x35** (§5) khai báo `usage` cho từng domain:

| domain | CMP | 2060S | 2070 |
|---|---|---|---|
| GPC | 1 MASTER | 1 | 1 |
| XBAR | 2 SLAVE | 2 | 2 |
| DRAM | 1 MASTER | 1 | 1 |
| SYS | 2 SLAVE | 2 | 2 |
| **HUB** | **0 FIXED** | 2 SLAVE | 2 SLAVE |
| VID | 2 SLAVE | 2 | 2 |
| PWR | 0 FIXED | 0 | 0 |
| **DISP** | **0 FIXED** | 1 MASTER | 1 MASTER |
| PCIEGEN | 2 SLAVE | 2 | 2 |
| HOST | 2 SLAVE | 2 | 2 |

`USAGE_FIXED` = **không lập trình domain đó**. Đúng hai domain bị đổi sang FIXED ở CMP —
và cũng đúng hai domain mang giá trị `27` trong bảng P-state. Hai bảng khác kiểu dữ
liệu, cùng kết luận.

27 MHz = tần số thạch anh tham chiếu ⇒ đọc tự nhiên nhất: **giá trị giữ chỗ cho domain
không được quản lý**. Nếu HUB thật sự chạy 27 MHz thì L2/uncore sập và card không dùng
được; card chạy bình thường ⇒ đây là **HYPOTHESIS mạnh**, không PROVEN. Cần đọc NV_PCLK
khi có tải (§10).

### 3.8 CMP bỏ 2 bậc P-state

| | `pstate_level` có dữ liệu |
|---|---|
| CMP 40HX | `07`, `0C`, `0F` |
| RTX 2060S / 2070 | `07`, `0A`, `0C`, `0D`, `0F` |

CMP đánh `0xFF` cho `0x0A` và `0x0D`. Ở GeForce, `0x0D` là bậc bộ nhớ **6801 MT/s
(13,6 Gbps)**. Entry cao nhất (`0x0F`, 7001 MT/s) **vẫn còn** ⇒ trần không bị cắt; chỉ
mất độ mịn chuyển mức.

---

## 4. POWER BASE CLOCK v0x20 — BASE/BOOST CLOCK THẬT

Layout từ `envytools/nvbios/power.c` case `0x20`:

```
+0 ver=0x20  +1 hlen=19  +2 rlen=1  +3 entries=17  +4 secount=4  +5 selen=10
entry = 1 + 10*4 = 41 B ;  extent = 19 + 17*41 = 716 B
clock[j] = u16(entry + 1 + j*10 + 2) * 4   [MHz]
```

Extent `716` kết thúc đúng `PERF TEST SPEC` (slot 17) ở cả 3 ROM. **PROVEN.**

| ROM | entry 0 | entry 2 | spec công bố |
|---|---|---|---|
| **CMP 40HX** | **1468 MHz** | **1648 MHz** | 1470 / 1650 |
| **RTX 2060S** | **1468 MHz** | **1648 MHz** | 1470 / 1650 |
| **RTX 2070** | **1408 MHz** | **1620 MHz** | 1410 / 1620 |

Lượng tử hoá `/4` giải thích lệch 2 MHz (367×4 = 1468).
- **Giá trị**: **PROVEN** (u16×4, offset xác định bởi extent khớp).
- **Nhãn "entry 0 = base, entry 2 = boost"**: **STRONGLY SUPPORTED** — 4/4 khớp cặp số
  công bố của hai card khác nhau; không spec nào đặt tên entry.
- **Entry 3..16**: decode theo layout envytools ra giá trị vô lý (`133412`). Parser gắn
  `clocks_valid=False` cho `i > 2`. Bản 1 in các giá trị này mà không cảnh báo — đã sửa.

Khác biệt duy nhất giữa CMP và GeForce ở bảng này: byte `+0x09,+0x0A`
(`FF FF` vs `03 09`) — theo `power.c` v0x20 đó là vùng `vrhot/max_batt/unk15/unk16`.
**UNKNOWN**.

---

## 5. CLOCKS v0x35 — BẢNG 10 DOMAIN (giải mã mới hoàn toàn)

`nvgpu bios.h`: `vbios_clocks_table_35_header` / `..._entry`.
Header 9 byte, signature `35 09 0b 0a`.

Vị trí: `0x2FB80` (CMP) / `0x2FAA0` (2060S) / `0x2FA90` (2070) — trong vùng legacy,
**không** thuộc P2 (không con trỏ P2 nào trỏ tới). Tìm bằng signature.

Header: `ver=0x35`, `header_size=9`, `entry_size=11`, `entry_count=10`,
`clocks_hal=3`, `sampling_ms=1000`, `reference_window=0`.

Row 11 byte: `flags0(usage 1:0) | param0(u16 first/last prog idx) | param1(u32) |
param2(u16) | param3(u16)`

- `param1`: MASTER → OC delta min/max (signed MHz); SLAVE → master domain index;
  FIXED → không dùng.
- `param2` byte `+7` = **ordering idx** (danh tính domain); low nibble = PRE_VOLT idx,
  high nibble = POST_VOLT idx.
- `param3` = ngưỡng clock monitor (`0xffff` = tắt), giống nhau 3 ROM.

10/10 row khớp `ordering idx` ở cả ba ROM. Bảng này là **nguồn định danh domain** cho
§3.4 và là bằng chứng độc lập cho §3.7.

---

## 6. MEMORY

### 6.1 MEMORY TIMINGS MAPPING = Memory Clock Table v0x11

```
ver=0x11 hdr=26 base=60 strap=33 strap_cnt=10 entries=7
extent = 26 + 7*(60 + 33*10) = 2756 B  -> kết thúc đúng MEM TIMINGS
```

`nvgpu` xác nhận `..._HEADER_11_2_SIZE = 26` và base entry `20`; TU106 dùng base 60 —
bản mở rộng Turing, extent xác nhận.

| # | min–max (MHz) | rw0 | rw1 |
|---|---|---|---|
| 0 | 0–540 | `0x7002054d` | `0x4f004402` |
| 1 | 541–1249 | `0x004e274d` | `0x4f88e804` |
| 2 | 2005–4699 | `0xf4201040` | `0xff44e405` |
| 3 | 4700–5500 | `0xf4201040` | `0xff44e405` |
| 4 | 5501–6300 | `0xf4201040` | `0xff44e405` |
| 5 | 6301–6700 | `0xf4201040` | `0xff44e405` |
| 6 | CMP/2060S 6701–16383 · 2070 6701–**9000** | `0xf4201040` | `0xff44e405` |

Lỗ hổng `1250..2004` có thật (giống cả 3 ROM, không phải lỗi parser: max dải 1 = 1249,
max dải 2 = 4699 khớp liền mạch với dải 3). Ý nghĩa: UNKNOWN.

### 6.2 MEMORY TIMINGS = Memory Tweak Table v0x20

```
ver=0x20 hdr=6 base=74 ext=12 ext_cnt=0 entries=60
extent = 6 + 60*74 = 4446 B -> kết thúc đúng LOW POWER (slot 29)
```
Spec nói base **76**; TU106 dùng **74** — extent xác nhận 74 cho ROM này.

Field (CONFIG0..CONFIG4): RC[7:0] RFC[16:8] RAS[23:17] RP[30:24] / CL[6:0] WL[13:7]
RD_RCD[19:14] WR_RCD[25:20] / RPRE WPRE CDLR WR / FAW[16:9] CCDL CCDS / REFRESH[14:3] RRD[20:15].

Strap 0 (14 Gbps): CL=24 WL=5 RC=78 RFC=210 RAS=52 RP=26 RD_RCD=26 WR=27 FAW=16.

### 6.3 Khác biệt timing CMP vs GeForce

| strap | field | CMP | 2060S/2070 |
|---|---|---|---|
| 14 | RFC | 148 | 180 |
| 14 | RAS | 37 | 42 |
| 14 | FAW | 16 | 24 |
| 15 | RFC | 126 | 150 |
| 12–17 | REFRESH | **6** | **4** |
| 46+ | toàn bộ | có dữ liệu | 2070 = 0 (strap không dùng) |

Không biết strap nào active khi chạy 14 Gbps ⇒ **không** suy ra ảnh hưởng hiệu năng.
**HYPOTHESIS**, chờ phép đo bandwidth (§10).

---

## 7. DISPLAY — DCB VÀ TOKEN `U`

### 7.1 DCB 4.x: Type là **nibble**, không phải byte

> DCB 4.x Specification, Display Path Information word (little-endian, byte 0):
> `bits 3:0 = Type` — 0 CRT · 1 TV · 2 TMDS · 3 LVDS · 5 SDI · 6 DisplayPort ·
> **0xE = EOL** (dừng parse) · **0xF = Skip Entry**.

Bản 1 kiểm `t != 0x0F` trên **cả byte** ⇒ đếm `0x7F`, `0x8F` thành connector.
Đúng phải `(t & 0x0F)` và loại cả `0xE`.

| ROM | entry_count | entry hoạt động | type |
|---|---|---|---|
| CMP 40HX | **0** | **0** | — |
| RTX 2060S | 16 | **5** | DP, TMDS×4 |
| RTX 2070 | 16 | **5** | DP, TMDS×4 |

`0x7F/0x7F/0x8F` ở 2060S là **Skip Entry** — chính là 3 entry bản 1 đếm nhầm (ra 8).
`test_tu106_vbios.py::regression_dcb_type_nibble` kiểm trực tiếp từ byte thô.

### 7.2 Kết luận tách bạch

- CMP **không có** script display (ptr = 0), **không có** bảng connector (count = 0),
  **không có** tham số TMDS/DP ⇒ *dữ liệu không tồn tại*, không phải "cờ bị tắt".
  **PROVEN.**
- **Không** suy ra phần cứng display bị fuse-disable. Ba tầng: ROM thiếu cấu hình
  (chứng minh được) → driver/GSP không bật display (chưa chứng minh) → fuse khoá
  (chưa kiểm tra).
- **Không** đề xuất flash chéo / chép DCB: bảng của 2060S và 2070 khác nhau giữa chính
  chúng (thứ tự entry, EDID port) nên không có cơ sở tương thích.

---

## 8. POWER / THERMAL — GIỐNG VÀ KHÁC

| slot | bảng | CMP vs 2060S |
|---|---|---|
| 5 | THERMAL DEVICES | **giống 100%** (58/58) |
| 10 | POWER SENSE | **giống 100%** (351/351) |
| 15 | POWER TOPOLOGY | **giống 100%** (851/851) |
| 18 | THERMAL CHANNEL | **giống 100%** |
| 31 | LOW POWER PCIe-PLATFORM | **giống 100%** |
| 8 | VOLT MAPPING | 100% (2060S) / 96% (2070) |
| 11 | POWER BUDGET | 1739/1743 (`+0x20`: `FF` vs `0E`) |
| 20 | THERMAL POLICY | 168/170 (`+4`: `FF` vs `02`) |
| 32 | LOW POWER GR | 34/35 |

⇒ Cảm biến công suất và topology nguồn **không** phải nguồn gốc khác biệt.

Schema POWER BUDGET / POWER TOPOLOGY / THERMAL POLICY vẫn **UNKNOWN**: envytools có
parser nhưng extent của nó không khớp trên TU106 (`44 + 20*66 = 1364` không rơi vào
bảng nào) ⇒ **không** áp schema mù. TDP 175 vs 185 W **không** đọc được từ ROM ở dạng
đã xác minh.

---

## 9. FECS / GPCCS / GSP VÀ CÁC REGISTER

| address | trong ROM? | trạng thái |
|---|---|---|
| `0x409658`, `0x40965C` | có, token `I` | **literal** trong script, cạnh condition-50 |
| `0x409660` | có, token `I` | **đọc** bit16 (mask `0x10000`) — condition, không phải write |
| `0x409664` (SS0) | có | literal |
| `0x40966C` (SS1) | có | literal |
| `0x021C38` | **không** | live: `STATUS_OPT_TPC_GPC0 = 0x20` (TPC5 tắt) |
| `0x021040` | **không** | live: ghi được = 1, sticky |

Phân biệt bắt buộc: literal ≠ lệnh mã hoá ≠ đường có điều kiện ≠ phép ghi quan sát được.
`0x409660` chỉ được **đọc**; một condition record **không** phải unlock.

Số SM/TPC do **fuse/latch phần cứng → GSP/SEC2 init → driver** quyết định: ghi
`CTRL_OPT_TPC_GPC0 |= 0x20` từ ring-0 qua BAR0 sau khi bật `0x021040` vẫn **bounce**
(`results/TPC5_LIVE/`). ROM không chứa bảng SM/TPC nào (POWER TOPOLOGY giống hệt 3 card).

Compute/Tensor bị giới hạn ở tầng **runtime register** (SS0/SS1/FECS_PLM), không phải
ROM — `Cyridd/cmpunlocker`, mục "how it works".

---

## 11. NHỮNG GÌ ĐÃ BỊ HẠ MỨC SO VỚI BẢN 1

Tự kiểm: field nào từng gắn PROVEN mà thực ra chỉ suy ra từ *trùng khớp số học*, hoặc từ
*tài liệu của phiên bản bảng khác*.

| Nội dung | Bản 1 | Bản 2 | lý do |
|---|---|---|---|
| Perf v0x60 shape | PROVEN nhờ extent arithmetic | **PROVEN theo `nvgpu bios.h`** | giờ có định nghĩa chính thức |
| Perf v0x60 field semantics | STRONGLY SUPPORTED | **PROVEN** | `bios.h` đặt tên từng trường |
| `0xFF = SKIP ENTRY` | STRONGLY SUPPORTED (mượn spec vP-state đời cũ) | **PROVEN** (`VBIOS_PERFLEVEL_SKIP_ENTRY`) | không còn mượn tài liệu bảng khác |
| `0x3FFF` mask + 2 cờ | STRONGLY SUPPORTED (mask của v0x40) | **PROVEN** (`PARAM1_MAX_FREQ_MHZ` bits 27:14) | idem |
| Danh tính 10 domain | (không có) | **PROVEN cho TU106** | 10/10 ordering idx + DRAM + PCIEGEN |
| "27 MHz = domain bị park" | HYPOTHESIS | **HYPOTHESIS (mạnh hơn)** | thêm bằng chứng `usage=FIXED`, vẫn chưa đo |
| PBC entry 0/2 = base/boost | PROVEN | **STRONGLY SUPPORTED** | nhãn entry là suy ra, không có spec |
| Mem clock base 60 / strap 33 | PROVEN | **PROVEN** (giữ) | extent + version/hlen khớp |
| Mem tweak base 74 | PROVEN | **PROVEN** (giữ) | extent; spec 76 → ghi rõ khác biệt |
| DCB "8 / 5 connector" | PROVEN | **SAI → 0/5/5 entry** | đọc sai nibble |
| `image_len` | `0x3000` | **`0xF400` / `0xEC00`** | đọc sai offset `+0x0A` → `+0x10` |
| DCB connector type | "DP/End" | **DP/TMDS/Skip/EOL theo spec** | spec DCB 4.x |

---

## 12. KẾT LUẬN CÓ GIỚI HẠN

Bản 1 kết luận "VBIOS không có giới hạn RT/graphics". Bản 2 **rút lại cách nói đó**:

- **Chứng minh được:** trong ba bảng đã decode (P-STATE v0x60, CLOCKS v0x35, POWER BASE
  CLOCK v0x20), **không trường nào khác nhau giữa CMP và 2060S ở domain
  GPC/XBAR/SYS/VID**, và base/boost clock trong ROM bằng RTX 2060 SUPER.
- **Không chứng minh được:** rằng *không tồn tại* cơ chế giới hạn ở nơi khác — devinit
  script, fuse, GSP/SEC2, hay userspace driver. Vắng bằng chứng không phải bằng chứng
  vắng. Đặc biệt, ROM có **35 bảng chưa decode** (nhóm B) và **19.8 KB legacy code**
  chưa phân tích ở đây.
- **Ba khác biệt ROM thực sự:** HUB `27 MHz + FIXED`, DISP `27 MHz + FIXED`,
  **`PCIEGEN 1 vs 3`**. Cái thứ ba là dữ kiện ROM khớp với quan sát cộng đồng "CMP 40HX
  chạy PCIe Gen1 mặc định" — **khác biệt có khả năng ảnh hưởng hiệu năng cao nhất trong
  toàn bộ ROM**, và nó không liên quan tới RT Core.

---

## 13. TÁI LẬP

```bash
cd TU106_VBIOS_RE
python3 scripts/test_tu106_vbios.py   /path/to/roms   # gồm 2 regression guard độc lập
python3 scripts/export_fields.py      /path/to/roms   # data/*.csv
python3 scripts/tu106_vbios.py dump   /path/to/roms/TU106.rom
python3 scripts/tu106_vbios.py compare /path/to/roms/{TU106,219827,265590}.rom
```

ROM gốc **không** nằm trong repo. Không script nào mở file ở chế độ ghi.
