# VBIOS FIELD REVERSE ENGINEERING — NVIDIA CMP 40HX / TU106

> **Publication edition (V5):** This is a curated ROM/source-analysis extract from the supplied `vbiosrel6(2).zip`. Host telemetry, game tests, benchmark steps and Windows/Linux collectors are intentionally omitted. It is historical research, **not** new hardware verification. See [integrated report](../../../docs/TU106_VBIOS_PHASE4_6.md).


**Phạm vi:** 3 ROM TU106 (1.047.040 B)
**Môi trường:** đọc tĩnh. Không flash, không ghi MMIO, không sửa driver.
**Script:** `scripts/tu106_vbios.py`, `scripts/export_fields.py`, `scripts/test_tu106_vbios.py`
**Dữ liệu:** `data/TU106_DECODED_FIELDS.csv` (5,621 dòng), `data/TU106_UNKNOWN_FIELDS.csv` (13 dòng)
**Bản:** v3 — sửa 3 lỗi export, reverse bảng PCIe, phân tích HUB/DISP

Nhãn: **PROVEN / STRONGLY SUPPORTED / HYPOTHESIS / UNKNOWN**. Xem §12 cho các mức đã đổi.

---

## 0. BA ROM

| | CMP 40HX | RTX 2060 SUPER | RTX 2070 |
|---|---|---|---|
| File | `TU106.rom` | `219827.rom` | `265590.rom` |
| PCI | `10DE:1F0B` | `10DE:1F06` | `10DE:1F07` |
| Class | `0x030200` 3D | `0x030000` VGA | `0x030000` VGA |
| Image 0 (legacy) | `0xF400` | `0xEC00` | `0xEC00` |
| Image 1 (EFI) | `0x11000` | `0x11000` | `0x11000` |
| Image 2 (legacy) | `0xF400` | `0xEC00` | `0xEC00` |
| Image 3 (EFI) | `0x11000` | `0x11000` | `0x11000` |

4 PCIR. `image_len` = **PCIR+0x10** × 512 B. Các bảng P2 nằm trong **image 2**
(`0x48A00..0x57E00` ở CMP), không phải image 0.

---

## 1. SỬA EXPORT (v3) — BA LỖI, ĐỀU CÓ TEST CHỐNG TÁI XUẤT

### 1.1 `BIT 'P'` version: đọc ở `record+1`, không phải ở địa chỉ P2

Bản v2 ghi `file_offset` của trường version bằng `P["file"]` — tức địa chỉ **bảng P2**,
cách byte version hơn 1 KB. Giá trị vẫn đúng (2) vì tình cờ đọc byte version qua
`P["ver"]`, nhưng cột offset trỏ sai chỗ, nên không ai kiểm chứng được nó.

Đúng: record BIT 6 byte nằm ở `P["ent"]`, byte `+1` là version.

```
CMP    : ent 0x287e6 → version @ 0x287e7 = 0x02   (P2 dir @ 0x288d4)
2060S  : ent 0x287e6 → version @ 0x287e7 = 0x02   (P2 dir @ 0x288c4)
```
**PROVEN.** Guard: `regression_p2_pointer_slot` đọc thẳng raw, assert `raw[rec+1] == 2`.

### 1.2 Con trỏ P2 slot N nằm ở `P2 dir + 4*N`, giá trị trỏ sang chỗ khác

v2 ghi `file_offset` = địa chỉ bảng đích. Hệ quả: một lỗi lệch slot (đọc slot N+1) sẽ
*hiện ra y hệt* slot đúng, vì cột offset chỉ in địa chỉ bảng. Giờ tách hai cột:

| cột | nghĩa |
|---|---|
| `file_offset` | nơi **định nghĩa** nằm (con trỏ, byte header, CONFIG word) |
| `target_offset` | nơi cấu trúc **được trỏ tới** nằm |

Đối chiếu nguồn — `nvgpu` `common/vbios/bios.c`, `nvgpu_bios_get_perf_table_ptrs()`
(dòng 676–730):

```c
perf_table_id_offset = *(u32 *)(bios->data + ptoken->data_ptr
                                + table_id * PERF_PTRS_WIDTH);   /* 4 */
...
if (perf_table_id_offset > g->bios->base_rom_size) {
        tmp_index = expansion_rom_offset + perf_table_id_offset;
        perf_table_ptr = &data[tmp_index];
} else {
        perf_table_ptr = &data[perf_table_id_offset];
}
```
Đây **chính xác** là quy tắc của parser: con trỏ tại `dir + 4N`, và `raw > legacy_len`
thì cộng `efi_len`. **PROVEN** cho cả vị trí con trỏ lẫn quy tắc hai ảnh.

Ghi chú biên: nvgpu dùng `>`; parser dùng `>=`. Chỉ khác khi `raw == legacy_len`, không
ROM nào trong bộ này rơi vào đó (`raw` nhỏ nhất `0x232`, lớn nhất `0x1F214`).

Guard: `regression_p2_pointer_slot` tự dựng lại `dir` từ BIT record, tự đọc `u32` tại
`dir+4N`, và assert **đọc tại địa chỉ đích cho ra giá trị khác** — tức nếu ai đảo hai cột
thì test đỏ.

### 1.3 Bitfield Memory Timings: offset của CONFIG word + shift + mask + raw

v2 in giá trị đã giải mã nhưng `raw = "-"`, và không nói field nằm ở word nào. Một shift
sai vẫn cho ra số trông hợp lý. Giờ mỗi field là một dòng:

```
CMP40HX,MEM TIMINGS,e14.RFC,0x554d6,,32,0x174a943c,CONFIG0[16:8] = 148,
        "shift 8, mask 0x1ff, word CONFIG0"
CMP40HX,MEM TIMINGS,e14.CL ,0x554da,,32,0x4125c314,CONFIG1[6:0] = 20,
        "shift 0, mask 0x7f, word CONFIG1"
```
Nguồn duy nhất cho layout là `MEM_TWEAK_FIELDS` trong parser — parser, exporter và test
dùng chung một bảng, nên không có chuyện ba nơi lệch nhau.

Guard: `regression_mem_tweak_bitfield` tự đọc `u32` tại `entry+4k` từ file thô rồi
so với parser bằng shift literal. Đã thử phá: đổi `RFC` từ shift 8 → 7 ⇒ **test đỏ**.
Đã thử phá `DCB` nibble → cả byte ⇒ **đỏ** (`('RTX2060S', 8)`). Đã thử phá con trỏ lệch
1 slot ⇒ **đỏ**.

### 1.4 Kết quả

| | v2 | v3 |
|---|---|---|
| cột | `group,table,field,file_offset,width,raw,value,note,source,evidence` | `rom,table,field,file_offset,target_offset,width,raw,value,note,source,evidence` |
| dòng | 1.526 | 5,621 |
| guard độc lập | 2 | **5** |

Thêm 3.222 dòng chủ yếu từ bitfield Memory Timings (19 field × 60 strap × 3 ROM) và hai
bảng mới (§2, §3).

---

## 2. BẢNG PCIe — REVERSE SÂU

### 2.1 `pcie_idx` trong Performance v0x60: có tên, KHÔNG có consumer

`nvgpu bios.h`:
```c
struct vbios_pstate_entry_6x {
        u8 pstate_level; u8 flags0; u8 lpwr_entry_idx; u8 pcie_idx; u8 nvlink_idx;
        ...
};
```
Giá trị trong ROM (chỉ entry "sống"):

| entry | CMP | 2060S / 2070 |
|---|---|---|
| `0x07` | 0 | 0 |
| `0x0A` | — (bị `0xFF`) | **1** |
| `0x0C` | 2 | 2 |
| `0x0D` | — (bị `0xFF`) | 2 |
| `0x0F` | 2 | 2 |

⇒ **CMP không bao giờ tham chiếu PCIe config entry 1**, vì nó bỏ đúng P-state `0x0A` —
P-state duy nhất dùng `pcie_idx = 1`. Đây là hệ quả trực tiếp của việc CMP bỏ 2 bậc, không
phải một cấu hình riêng. **PROVEN** (dữ liệu), chưa rõ entry 1 khác gì.

Tìm consumer trong 3 nguồn:
- `nvgpu`: `pcie_idx` xuất hiện **2 lần** trong `bios.h` (struct 6x và struct 4x), và
  **0 lần** trong mọi file `.c` — không có ai dereference.
- `NVIDIA/open-gpu-kernel-modules`: `src/nvidia/src/kernel/gpu/vbios/` không có PERF/POWER
  parser (`grep -i perf` = 0 hit).
- nouveau: `nvkm/subdev/bios/perf.c` chỉ tới `ver 0x40`, **không có nhánh 0x60**.

⇒ Đích của `pcie_idx` = **UNKNOWN**.

### 2.2 Ứng viên đích: P2 slot 30 "LOW POWER PCIe"

Slot 30 khớp **chính xác** một bảng `{ver, hlen, entry_size, entry_count}`:

```
CMP   @0x5624b : ver=0x10  hlen=5  esz=12  cnt=5 → 65 B → kết thúc đúng slot 31 @0x5628c
2060S @0x5584b : y hệt
2070  @0x5574b : y hệt
```

5 entry × 12 B, entry 0 của CMP:
```
ff fd ff ff fa 48 1f fd fb 9f f8 ff
```
Của 2060S/2070:
```
ff fd ff ff fa 48 1f fd f8 9f f8 ff
```

**Khác biệt: byte thứ 8, ở CẢ 5 entry.** CMP `0xfb`, GeForce `0xf8`. `0xf8 = 1111_1000`,
`0xfb = 1111_1011` ⇒ CMP **bật bit 0 và bit 1**. Guard test assert đúng điều này
(`diff == [8]` cho cả 5 entry).

Điều **chưa** biết: 12 byte đó là gì. Các byte `ff/fd/fc/f8` trông như bitmask chứ không
phải clock. Không có schema công khai ⇒ **UNKNOWN**, chỉ ghi raw.

### 2.3 PCIe settings script — giải mã được, theo spec chính thức

`nvinit_ptrs.pcie_settings_script_ptr` (offset `+0x12` trong token `I`) trỏ tới một
NVINIT script. Giải mã theo **NVIDIA open-gpu-doc `Devinit/devinit.xml`**:

| opcode | tên | operand |
|---|---|---|
| `0x7A` | `INIT_ZM_REG` | addr(u32) data(u32) — 9 B, `reg = data` |
| `0x6E` | `INIT_NV_REG` | addr(u32) mask(u32) data(u32) — 13 B, `reg = (reg & mask) \| data` |
| `0x75` | `INIT_CONDITION` | condition(u8) — 2 B, phần sau là nhánh có điều kiện |
| `0x5B` | `INIT_SUB_DIRECT` | gọi chương trình con |
| `0xFF` | `EOL` | |

CMP @ `0x3606f`:

| # | op | addr | giá trị |
|---|---|---|---|
| 1 | ZM_REG | `0x00137C00` | `0x180` |
| 2 | NV_REG | `0x0008B900` | `& 0xFFFFFFFF \| 0` → ghi 0 toàn bộ |
| 3 | NV_REG | `0x0008C100` | `& 0xFFFFFFFF \| 0` → ghi 0 toàn bộ |
| 4 | ZM_REG | `0x00088610` | **`0x1`** ← GeForce: **`0x1001`** |
| 5 | NV_REG | `0x0008A088` | `& 0xFFFFFFFC \| 3` → set bit 1:0, giữ phần còn lại |
| 6 | ZM_REG | `0x0008B400` | `0x58E` |
| 7 | NV_REG | `0x00001404` | `& 0xFFFFFBFF \| 0` → **xoá bit 10** |
| 8 | CONDITION | — | **86** (GeForce: **82**) |
| 9 | SUB_DIRECT `0x5B` | — | dừng decode (không đi theo nhánh) |

**So CMP với GeForce: khác đúng 1 bit.** Reg `0x0088610`: `0x1` vs `0x1001` (bit 12).
Ngoài ra condition id khác (86 vs 82) — một điều kiện fuse/strap, không giải mã.

Guard: `regression_pcie_script` tự parse script từ raw, assert danh sách 7 thanh ghi và
assert `diff == {0x88610: (0x1, 0x1001)}` — nếu ai đó sửa kích thước operand (9↔13) thì
test đỏ ngay.

Điều **chưa** biết: Turing không có register map công khai cho `0x008xxxx`
(rnndb chỉ có `PUNITS` tới GM107 và không có `0x88610`). Nên "bit 12 của 0x88610" là
**sự kiện đọc được**, không phải "cờ bật Gen3".

### 2.4 `PCIEGEN = 1` vs `3` — KHÔNG được gọi PROVEN

Câu hỏi: giá trị đó là *thế hệ link* hay chỉ là một con số được diễn giải theo chính sách
clock-domain?

Bằng chứng **ủng hộ "thế hệ link"**:

1. **Không thể là MHz.** `1` và `3` MHz không tồn tại trong cây clock PCIe (refclk 100 MHz,
   link clock 250/500/1000 MHz).
2. **Không có dải.** Cả 3 ROM: `nom = min = max`. Trong khi GPC có `min 300 / max 2100`,
   XBAR `540..2010`, HOST `540..1350` — các domain thật đều có dải. Một domain không có
   dải là một *mã hằng*, không phải tần số lập trình được.
3. **Tương quan đúng chiều.** CMP = 1, và cộng đồng đo `LnkSta 2.5 GT/s` (Gen1);
   GeForce = 3, và Turing tối đa là Gen3.
4. **Tên domain không tự bịa.** `PCIEGEN` lấy từ bảng GV HAL 10 domain
   (`nvidia-vbios-vix-editor`, `TURING_CLOCK_ROWS`, nguồn ghi là GSP-RM 615.78.08), và
   khớp 10/10 `ordering idx` trên cả 3 ROM.

Bằng chứng **chống**:
- Không có. Nhưng cũng **không có consumer** nào định nghĩa đơn vị: `nvgpu` chỉ mask
  trường này bằng macro chung `..._NOM_FREQ_MHZ`, mà macro đó là của *mọi* domain, không
  phải định nghĩa riêng cho PCIEGEN.

⇒ **Kết luận: STRONGLY SUPPORTED cho tương quan "1 ≈ Gen1, 3 ≈ Gen3"; đơn vị vẫn UNKNOWN.**
Không đủ để gọi PROVEN vì thiếu chuỗi VBIOS → consumer → trạng thái GPU.
Phép đo phân biệt: đọc `LnkCap`/`LnkSta` của chính card CMP. Nếu `LnkSta` = 2.5 GT/s khớp
`PCIEGEN = 1`, và một ROM Turing Gen2-only cho ra `2`, thì lúc đó mới đủ.

---

## 3. HUB / DISP — 27 MHz VÀ `FIXED`

### 3.1 Dữ liệu (hai bảng độc lập, cùng kết luận)

**Bảng 1 — Performance v0x60, clock entry index 4 và 7** (entry `0x0F`):

| domain | CMP nom/min/max | 2060S | 2070 |
|---|---|---|---|
| HUB | **27 / 27 / 27** | 540 / 540 / 810 | 540 / 540 / 810 |
| DISP | **27 / 27 / 27** | 1080 / 1080 / 1330 | 1080 / 1080 / 1330 |

**Bảng 2 — CLOCKS v0x35, cột `usage`:**

| domain | CMP | 2060S | 2070 |
|---|---|---|---|
| HUB | **0 = FIXED** | 2 = SLAVE | 2 = SLAVE |
| DISP | **0 = FIXED** | 1 = MASTER | 1 = MASTER |

Hai bảng khác kiểu dữ liệu, khác vị trí trong ROM, khác bảng, nhưng **trùng đúng hai
domain**. Bốn byte từng bị nghi là "RT lock" (`+0x27/+0x29/+0x2A/+0x2B`) nằm gọn trong
clock entry của HUB: `param0 = 0x001B` (nom 27) và `param1` bits 27:14 = 27 (max).
**PROVEN** cho vị trí và giá trị.

### 3.2 `usage = 0` nghĩa là gì — và phần nào là suy luận

`nvgpu bios.h` định nghĩa đúng ba giá trị:

```c
NV_VBIOS_CLOCKS_TABLE_1X_ENTRY_FLAGS0_USAGE_FIXED   0x00U
NV_VBIOS_CLOCKS_TABLE_1X_ENTRY_FLAGS0_USAGE_MASTER  0x01U
NV_VBIOS_CLOCKS_TABLE_1X_ENTRY_FLAGS0_USAGE_SLAVE   0x02U
```
Nhưng: **không có file `.c` công khai nào đọc bảng này**. Enum có tên `FIXED`, driver
không có trong nguồn mở. Vậy:
- "Domain này được khai báo FIXED" — **PROVEN** (byte trong ROM + enum trong header).
- "FIXED nghĩa là driver không lập trình domain đó" — **STRONGLY SUPPORTED** theo tên enum
  và theo đối xứng (`PWR` cũng FIXED ở cả 3 card; `GPC`/`DRAM`/`DISP` là MASTER;
  `XBAR`/`SYS`/`VID`/`PCIEGEN`/`HOST` là SLAVE — đúng mô hình master/slave của cây clock).
- "Vì FIXED nên HUB thật sự chạy 27 MHz" — **KHÔNG**. Đó là nhảy cóc.

### 3.3 Vì sao 27 MHz gần như chắc chắn không phải xung vận hành

- 27 MHz là tần số thạch anh tham chiếu của mọi bảng clock NVIDIA.
- Nếu HUB (khối hub nối L2/XBAR) thật sự chạy 27 MHz thì uncore sập và card không lên
  hình — card chạy bình thường.
- Đọc tự nhiên nhất: **giá trị giữ chỗ** cho domain không được quản lý. **HYPOTHESIS**
  (mạnh), chưa đo.

### 3.4 "HUB" là domain gì

Không có định nghĩa công khai. Nhưng `HUB` **không phải** tên do bảng reverse-engineer
tự đặt: enum clock của NVIDIA (như nouveau phơi ra cho Kepler) có
`nv_clk_src_hubk06`, `nv_clk_src_hubk01`, `nv_clk_src_hubk07`, và bảng domain Kepler là
`gpc=0, hubk07=1, rop=2, mem=3, hubk06=4, hubk01=5, vdec=6, pmu=7` — tức "hub" là một
họ clock domain có từ trước Turing, **không** phải display hub.
⇒ **STRONGLY SUPPORTED**: HUB là domain clock nội bộ, không phải khối display.
Hệ quả: giả thuyết "HUB 27 MHz vì CMP không có display" **không đứng** một mình — DISP
thì đúng là vì không có display, HUB thì cần lý do khác (hoặc HUB được clock chung với
một domain khác trên SKU này).

### 3.5 Cấu hình ROM ≠ trạng thái GPU

Đây là ranh giới phải giữ:

| | biết được từ ROM | cần telemetry |
|---|---|---|
| HUB/DISP khai báo `FIXED`, 27 MHz | ✅ | |
| Driver có lập trình domain đó hay không | | ❓ |
| Xung thật của HUB/DISP khi chạy | | ❓ |

**Không** kết luận HUB bị throttle. Trong phiên này **không có card NVIDIA** để đo
(`lspci` không có thiết bị `10de`), nên mọi phát biểu về trạng thái chạy đều là suy luận.
Xem `GRAPHICS_RT_PERFORMANCE_INVESTIGATION.md` §5 cho phép đo.

---

## 4. PERFORMANCE v0x60 — SCHEMA (giữ nguyên từ v2, đã kiểm lại)

Nguồn: `nvgpu include/nvgpu/bios.h` — `vbios_pstate_header_6x` (10 B),
`vbios_pstate_entry_6x` (5 B), `vbios_pstate_entry_clock_6x` (`u16 param0; u32 param1` = 6 B).

```
10 + 7*(5 + 6*10) = 465 = 0x1D1   → kết thúc đúng POWER BASE CLOCK ở cả 3 ROM
```

| off | field | CMP/2060S/2070 |
|---|---|---|
| +0..+5 | version 0x60, hdr 10, base 5, cnt 7, sup 6, supcnt 10 | giống |
| +6 | flags0 | `0x01` = PSTATES_REQUIRED, ARBITER_LOCK tắt |
| +7 | initial_pstate | `0x07` |
| +8/+9 | cpi_support_level / cpi_features | `0x00` / `0x01` — **ý nghĩa UNKNOWN** |

Base entry: `pstate_level` (`0xFF` = SKIP), `flags0` (PSTATE_CAP 1:0, CUDA 2, OVOC 3,
DECREASE_THRESHOLD 4), `lpwr_entry_idx`, `pcie_idx`, `nvlink_idx` (`0xFF`).

Clock entry: `param0[13:0]` = nom, `param1[13:0]` = min, `param1[27:14]` = max.

### 4.1 10 domain

`0 GPC 1 XBAR 2 DRAM 3 SYS 4 HUB 5 VID 6 PWR 7 DISP 8 PCIEGEN 9 HOST`
(kiểm 10/10 `ordering idx` của bảng v0x35 ở cả 3 ROM; index 2 = DRAM vì `7001 = 4×1750`;
index 8 suy ra PCIEGEN). **PROVEN cho TU106.**

### 4.2 Bảng domain, entry `0x0F`

| domain | CMP | 2060S | 2070 | khác? |
|---|---|---|---|---|
| GPC | 645 | 645 | 645 | — |
| XBAR | 855 | 855 | 855 | — |
| DRAM | 7001 | 7001 | 7001 | — |
| SYS | 855 | 855 | 855 | — |
| **HUB** | **27** | 540 | 540 | **có** |
| VID | 555 | 555 | 555 | — |
| PWR | 540 | 540 | 540 | — |
| **DISP** | **27** | 1080 | 1080 | **có** |
| **PCIEGEN** | **1** | 3 | 3 | **có** |
| HOST | 705 | 705 | 705 | — |

Bảy domain trùng tuyệt đối, trong đó có **GPC** — domain của shader/RT.
`max`: GPC 2100 cả 3; HUB 27 vs 810; DISP 27 vs 1330; PCIEGEN 1 vs 3.

---

## 5. CLOCKS v0x35

Signature `35 09 0b 0a`; header 9 B (`ver, hlen, esz=11, cnt=10, clocks_hal=3,
sampling_ms=1000, ref_window=0`); 10 row × 11 B; `byte+7` = `ordering idx` (danh tính
domain); `usage = flags0 & 0x1F`; `param2` nibble thấp = PRE_VOLT idx, cao = POST_VOLT.

Vị trí: `0x2FB80` (CMP) / `0x2FAA0` (2060S) / `0x2FA90` (2070) — trong vùng legacy,
**không** thuộc P2.

`param1`: MASTER → OC delta min/max (signed MHz); SLAVE → index master; FIXED → không dùng
⇒ với row FIXED của CMP, `param1 = 0x0000001B` **không** mang nghĩa đã biết. UNKNOWN.

---

## 6. POWER BASE CLOCK v0x20

```
+0 ver=0x20  +1 hlen=19  +2 rlen=1  +3 cnt=17  +4 secount=4  +5 selen=10
entry = 41 B ; extent = 19 + 17*41 = 716 B → đúng PERF TEST SPEC (slot 17)
clock[j] = u16(entry + 1 + j*10 + 2) * 4
```
| ROM | entry 0 | entry 2 | spec |
|---|---|---|---|
| CMP | **1468** | **1648** | 1470 / 1650 |
| 2060S | **1468** | **1648** | 1470 / 1650 |
| 2070 | **1408** | **1620** | 1410 / 1620 |

Giá trị **PROVEN**; nhãn "entry0 = base, entry2 = boost" **STRONGLY SUPPORTED**.
Entry 3..16 cho số vô lý (`133412`) ⇒ parser cờ `clocks_valid=False`.

---

## 7. MEMORY

### 7.1 Memory Clock Table v0x11 (slot 1)
`ver 0x11, hlen 26, base 60, strap 33, strap_cnt 10, cnt 7` → `2756 B`, kết thúc đúng
slot 2. Spec ghi base 20 / strap 26 (bản gốc); TU106 dùng 60/33, extent xác nhận.

Dải: `0–540, 541–1249, 2005–4699, 4700–5500, 5501–6300, 6301–6700, 6701–16383`
(2070: dải cuối `6701–9000`). Lỗ hổng `1250..2004` giống cả 3 ROM — ý nghĩa UNKNOWN.

### 7.2 Memory Tweak Table v0x20 (slot 2)
`ver 0x20, hlen 6, base 74, ext 12, ext_cnt 0, cnt 60` → `4446 B`, kết thúc đúng
LOW POWER (slot 29). Spec ghi base 76; TU106 dùng 74.

19 bitfield trên CONFIG0..CONFIG5 (`MEM_TWEAK_FIELDS`), ví dụ strap 0:
`CL=24 WL=5 RC=78 RFC=210 RAS=52 RP=26 RD_RCD=26 WR=27 FAW=16`.

### 7.3 Khác biệt CMP vs GeForce
| strap | field | CMP | GeForce |
|---|---|---|---|
| 14 | RFC | 148 | 180 |
| 14 | RAS | 37 | 42 |
| 14 | FAW | 16 | 24 |
| 14 | CL | 20 | 22 |
| 15 | RFC | 126 | 150 |
| 12–17 | REFRESH | **6** | **4** |

Không biết strap nào active ở 14 Gbps ⇒ ảnh hưởng hiệu năng = **HYPOTHESIS**.

---

## 8. DISPLAY (giữ nguyên từ v2)

DCB 4.x: `Type` = **nibble** thấp của Display Path word; `0xE` = EOL, `0xF` = Skip.
| ROM | entry | hoạt động |
|---|---|---|
| CMP | **0** | **0** |
| 2060S | 16 | **5** |
| 2070 | 16 | **5** |

Token `U`: CMP ptr `0x0000`, flags `0x02`; GeForce ptr `0x4E8F`, flags `0x00`.
`T`/`d` của CMP đều `00 00`.

⇒ CMP **không có** dữ liệu display trong ROM. Đó là *dữ liệu không tồn tại*, **không**
phải "cờ bị tắt", và **không** suy ra fuse.
Không đề xuất flash chéo: bảng DCB của 2060S và 2070 khác nhau giữa chính chúng.

---

## 9. FECS / GSP / REGISTER

| address | trong ROM | trạng thái |
|---|---|---|
| `0x409658`, `0x40965C` | có (token `I`) | literal trong script, cạnh condition |
| `0x409660` | có | **đọc** bit16 — điều kiện, không phải write |
| `0x409664` (SS0), `0x40966C` (SS1) | có | literal |
| `0x021C38` | **không** | live: `0x20` ⇒ TPC5 tắt (đọc trên card, phiên trước) |
| `0x021040` | **không** | live: ghi được, sticky |

Phân biệt: literal ≠ lệnh mã hoá ≠ nhánh có điều kiện ≠ phép ghi đã quan sát.
Script PCIe ở §2.3 là ví dụ đúng: 7 lệnh ghi **vô điều kiện**, rồi `CONDITION`, rồi
`SUB_DIRECT` — phần sau `CONDITION` **không** được tính là đường init chắc chắn.

Số SM/TPC do fuse → GSP/SEC2 → driver. ROM không có bảng SM/TPC (POWER TOPOLOGY giống
hệt 3 card, 851/851 B).

---

## 10. POWER / THERMAL

| slot | bảng | CMP vs 2060S |
|---|---|---|
| 5 | THERMAL DEVICES | giống 100% |
| 10 | POWER SENSE | giống 100% (351/351) |
| 15 | POWER TOPOLOGY | giống 100% (851/851) |
| 18 | THERMAL CHANNEL | giống 100% |
| 31 | LOW POWER PCIe-PLATFORM | giống 100% |
| 11 | POWER BUDGET | 1739/1743 |
| 20 | THERMAL POLICY | 168/170 |
| 32 | LOW POWER GR | 34/35 |

Schema POWER BUDGET / POWER TOPOLOGY / THERMAL POLICY: **UNKNOWN** (envytools extent
không khớp TU106). TDP 175 vs 185 W **không** đọc được từ ROM.

---

## 11. NHỮNG GÌ CÒN UNKNOWN (13 dòng trong CSV)

1. Payload 12 B × 5 của slot 30 (LOW POWER PCIe) — có raw, không có nghĩa.
2. Đích của `pcie_idx`.
3. Đơn vị của `PCIEGEN`.
4. Đích của `lpwr_entry_idx` (slot 29 `esz=7` vs struct nvgpu 5 B).
5. `flags0` bit 2..7 của header P-state.
6. `cpi_support_level` / `cpi_features`.
7. Vì sao HUB/DISP = 27 MHz trên CMP.
8. `param1` của row FIXED trong v0x35.
9. POWER BASE CLOCK entry 3..16 + header `+9..+0x12`.
10. POWER BUDGET / POWER TOPOLOGY / THERMAL POLICY.
11. Strap bộ nhớ nào active.
12. **Tên** các thanh ghi trong PCIe settings script (địa chỉ thì biết).
13. Bảng FALCON UCODE (token `p`).

---

## 12. MỨC BẰNG CHỨNG — ĐÃ ĐỔI GÌ Ở v3

| nội dung | v2 | v3 | lý do |
|---|---|---|---|
| Vị trí con trỏ P2 | ngầm đúng, export sai | **PROVEN** (`nvgpu_bios_get_perf_table_ptrs`) | có source đọc thật |
| Quy tắc hai ảnh | suy từ số học | **PROVEN** (cùng hàm) | idem |
| `PCIEGEN = Gen1/Gen3` | STRONGLY SUPPORTED | **STRONGLY SUPPORTED**, đơn vị **UNKNOWN** | tìm kỹ hơn: không consumer nào |
| `pcie_idx` | UNKNOWN | **UNKNOWN** (đã loại trừ 3 nguồn) | ghi rõ đã tra gì |
| Slot 30 | chưa biết tồn tại | **cấu trúc PROVEN, nghĩa UNKNOWN** | extent khớp |
| PCIe script | chưa giải mã | **operand PROVEN, register name UNKNOWN** | Devinit spec |
| `usage = FIXED` | "domain bị park" (HYPOTHESIS) | **PROVEN là FIXED; hệ quả HYPOTHESIS** | tách hai tầng |
| HUB là gì | chưa rõ | **STRONGLY SUPPORTED: domain clock nội bộ** | enum `hubk06/hubk01` |
| PBC base/boost | STRONGLY SUPPORTED | giữ | — |

---

## 13. TÁI LẬP

```bash
cd TU106_VBIOS_RE
python3 scripts/test_tu106_vbios.py  /path/to/roms    # 5 guard độc lập + toàn bộ assert
python3 scripts/export_fields.py     /path/to/roms    # -> data/*.csv
python3 scripts/tu106_vbios.py dump    /path/to/roms/TU106.rom
python3 scripts/tu106_vbios.py compare /path/to/roms/{TU106,219827,265590}.rom
```

Kiểm chứng guard thật sự bắt lỗi (đã chạy):
```bash
# đổi shift RFC 8 -> 7            => AssertionError trong regression_mem_tweak_bitfield
# đổi DCB nibble 0xF -> 0xFF      => AssertionError ('RTX2060S', 8)
# lệch con trỏ P2 +4 byte         => KeyError/AssertionError
```
ROM gốc không nằm trong repo; không script nào mở file ở chế độ ghi.
